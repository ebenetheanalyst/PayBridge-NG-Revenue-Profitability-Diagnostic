"""
transactions.py | the transaction simulator (Step 4)
Works one month at a time and appends to output/fact_Transactions.csv, so memory use stays small.
Every effect is driven by numbers in config.py.
"""
import numpy as np
import pandas as pd
import config as C

FAIL_CODES = ["05", "51", "55", "68", "91", "96", "59"]
FAR = np.datetime64("2100-01-01")


def date_key(d):
    """datetime64[D] array -> YYYYMMDD ints."""
    y = d.astype("datetime64[Y]"); m = d.astype("datetime64[M]")
    return ((y.astype(int) + 1970) * 10000 + (m.astype(int) % 12 + 1) * 100
            + (d - m.astype("datetime64[D]")).astype(int) + 1)


def _fill_nat(a):
    a = a.astype("datetime64[D]")
    return np.where(np.isnat(a), FAR, a).astype("datetime64[D]")


def generate_transactions(t, internal, rng):
    start, end = np.datetime64(C.START_DATE), np.datetime64(C.END_DATE)

    # ---- lookup arrays -------------------------------------------------------------------------------
    plans = t["dim_PricingPlan"].fillna({"fee_pct": 0.0, "flat_fee_ngn": 0.0})
    npl = int(plans.plan_id.max()) + 1
    plan_pct, plan_flat, plan_cap, plan_disc = (np.zeros(npl) for _ in range(4))
    for r in plans.itertuples():
        plan_pct[r.plan_id], plan_flat[r.plan_id] = r.fee_pct, r.flat_fee_ngn
        plan_cap[r.plan_id], plan_disc[r.plan_id] = r.fee_cap_ngn, r.standard_discount_pct

    kidx = {k: i for i, k in enumerate(C.COST_TYPES)}
    P = np.zeros((6, 5, 2, 4)); F = np.zeros((6, 5, 2, 4)); CAP = np.full((6, 5, 2, 4), 1e12)
    for r in t["dim_CostRate"].itertuples():
        v = int(r.effective_from >= pd.Timestamp(C.COST_CHANGE_DATE))
        P[r.channel_id, r.product_id, v, kidx[r.cost_type]] = r.rate_pct
        F[r.channel_id, r.product_id, v, kidx[r.cost_type]] = r.flat_cost_ngn
        CAP[r.channel_id, r.product_id, v, kidx[r.cost_type]] = r.cost_cap_ngn

    base = internal.base.values; g = internal.growth.values
    onb = _fill_nat(internal.onb.values); churn = _fill_nat(internal.churn.values)
    dorm = _fill_nat(internal.dorm.values); switch = _fill_nat(internal.switch.values)
    loc_key = internal.location_key.values; is_new = internal.is_new_market.values
    seg_mult = internal.seg_mult.values; n_term = internal.n_term.values
    plan0, plan1 = internal.plan0.values, internal.plan1.values
    merchant_ids = internal.merchant_id.values
    term_off = np.concatenate([[0], np.cumsum(n_term)[:-1]])
    all_terms = t["dim_Terminal"].terminal_id.values

    bank_w = np.array([b[2] for b in C.BANKS]); bank_w = bank_w / bank_w.sum()
    bank_mult = np.array([0.0] + [b[3] for b in C.BANKS])
    hour_w = np.array([.3] * 6 + [.8] * 2 + [2.0] * 4 + [2.6] * 3 + [2.4] * 3 + [2.8] * 3 + [1.2] * 2 + [.6])
    hour_p = hour_w / hour_w.sum()
    hour_fail = np.ones(24); hour_fail[[12, 13, 14, 18, 19, 20]] = C.FAIL_PEAK_HOUR_MULT
    chan_ids = np.array(list(C.CHANNELS)); non_pos = chan_ids[chan_ids != 1]
    amt_med = np.zeros(6); fail_base = np.zeros(6)
    for c in chan_ids:
        amt_med[c], fail_base[c] = C.AMOUNT_MEDIAN[c], C.FAIL_BASE[c]
    holidays = pd.to_datetime(list(C.HOLIDAYS))
    retryable = [k for k, v in C.RESPONSE_CODES.items() if v[3] == 1 and v[1] != "None"]

    def draw_fail_codes(ch):
        out = np.empty(len(ch), dtype=object)
        for c in chan_ids:
            m = ch == c
            if m.any():
                w = np.array([C.FAIL_CODE_WEIGHTS[c][k] for k in FAIL_CODES]); w = w / w.sum()
                out[m] = rng.choice(FAIL_CODES, size=int(m.sum()), p=w)
        return out

    # ---- month loop ----------------------------------------------------------------------------------
    path = C.OUT_DIR / "fact_Transactions.csv"; first = True
    counter = 1; summaries = []
    for per in pd.period_range(C.START_DATE, C.END_DATE, freq="M"):
        days = pd.date_range(per.start_time.normalize(), per.end_time.normalize(), freq="D")
        days = days[days <= pd.Timestamp(C.END_DATE)]
        d64 = days.values.astype("datetime64[D]")
        yrs = (d64 - start).astype(float) / 365.25
        dayf = (np.array(C.DOW_FACTOR)[days.weekday]
                * np.where((days.day >= 26) | (days.day == 1), C.MONTH_END_FACTOR, 1.0)
                * C.MONTH_FACTOR.get(per.month, 1.0) * np.where(days.isin(holidays), C.HOLIDAY_FACTOR, 1.0))
        active = (d64[None, :] >= onb[:, None]) & (d64[None, :] <= churn[:, None])
        lam = (base[:, None] * dayf[None, :] * (1 + g)[:, None] ** yrs[None, :] * active
               * np.where(d64[None, :] >= dorm[:, None], 0.05, 1.0))
        cnt = rng.poisson(lam)
        mi, di = np.nonzero(cnt); rep = cnt[mi, di]
        mi, di = np.repeat(mi, rep), np.repeat(di, rep); N = len(mi)
        if N == 0:
            continue

        date = d64[di]; yr = yrs[di]; peak = per.month in (11, 12)
        hour = rng.choice(24, size=N, p=hour_p)
        ts = date.astype("datetime64[s]") + (hour * 3600 + rng.integers(0, 3600, N)).astype("timedelta64[s]")

        # H1: channel mix drifts over the 24 months
        f = (d64[len(d64) // 2] - start) / (end - start)
        share = np.array([C.CHANNEL_SHARE_START[c] + (C.CHANNEL_SHARE_END[c] - C.CHANNEL_SHARE_START[c]) * f
                          for c in chan_ids]); share = share / share.sum()
        ch = rng.choice(chan_ids, size=N, p=share)
        nopos = (ch == 1) & (n_term[mi] == 0)
        sh2 = np.array([share[list(chan_ids).index(c)] for c in non_pos]); sh2 = sh2 / sh2.sum()
        ch[nopos] = rng.choice(non_pos, size=int(nopos.sum()), p=sh2)
        prod = np.zeros(N, int)
        for c, pw in C.CHANNEL_PRODUCT.items():
            m = ch == c
            prod[m] = rng.choice(list(pw), size=int(m.sum()), p=list(pw.values()))
        bank = rng.choice(np.arange(1, len(C.BANKS) + 1), size=N, p=bank_w)

        amount = np.clip(amt_med[ch] * seg_mult[mi] * (1 + C.AMOUNT_INFLATION) ** yr
                         * np.exp(rng.normal(0, C.AMOUNT_SIGMA, N)), 100, 5e6).round(2)
        term = np.full(N, None, dtype=object); pos = ch == 1
        term[pos] = all_terms[term_off[mi[pos]] + (rng.random(int(pos.sum())) * n_term[mi[pos]]).astype(int)]

        plan = np.where(date >= switch[mi], plan1[mi], plan0[mi])          # H3: plan in force on the day
        list_fee = np.minimum(amount * plan_pct[plan] + plan_flat[plan], plan_cap[plan]).round(2)

        # H4: failures
        pf = np.clip(fail_base[ch] * bank_mult[bank] * hour_fail[hour] * (C.FAIL_FESTIVE_MULT if peak else 1.0)
                     * (1 + C.FAIL_YEARLY_DRIFT * yr), 0, 0.35)
        failed = rng.random(N) < pf
        rev = (~failed) & (rng.random(N) < C.REVERSAL_RATE)
        status = np.where(failed, "Failed", np.where(rev, "Reversed", "Success")).astype(object)
        code = np.full(N, "00", dtype=object); code[rev] = "RV"
        code[failed] = draw_fail_codes(ch[failed])

        # H2, H5, H6: costs (cost-rate version by date, plus small uplifts and noise)
        ver = (date >= np.datetime64(C.COST_CHANGE_DATE)).astype(int)
        raw = np.zeros((4, N))
        for k in range(4):
            c_ = np.minimum(amount * P[ch, prod, ver, k] + F[ch, prod, ver, k], CAP[ch, prod, ver, k])
            if k < 2:
                c_ = c_ * (1 + C.PEAK_COST_UPLIFT * peak) * (1 + C.NEW_MARKET_COST_UPLIFT * is_new[mi])
            raw[k] = c_ * np.exp(rng.normal(0, C.COST_NOISE_SD, N))

        d = dict(ts=ts, date=date, hour=hour, mi=mi, term=term, prod=prod, ch=ch, bank=bank, plan=plan,
                 code=code, status=status, amount=amount, list_fee=list_fee, raw=raw,
                 is_retry=np.zeros(N, int), orig=np.full(N, None, dtype=object))
        ids = np.char.add("TXN", np.char.zfill(np.arange(counter, counter + N).astype(str), 9))
        counter += N; d["id"] = ids.astype(object)

        # retries of retryable failures
        rm = failed & np.isin(code, retryable) & (rng.random(N) < C.RETRY_RATE)
        nr = int(rm.sum())
        if nr:
            r = {k: (v[:, rm] if k == "raw" else v[rm]) for k, v in d.items()}
            r["orig"] = d["id"][rm]; r["is_retry"] = np.ones(nr, int)
            ok = rng.random(nr) < C.RETRY_SUCCESS_RATE
            r["status"] = np.where(ok, "Success", "Failed").astype(object)
            r["code"] = np.where(ok, "00", "").astype(object)
            if (~ok).any():
                r["code"][~ok] = draw_fail_codes(r["ch"][~ok])
            day_s = r["date"].astype("datetime64[s]")
            r["ts"] = np.minimum(r["ts"] + rng.integers(20, 300, nr).astype("timedelta64[s]"), day_s + 86399)
            r["hour"] = ((r["ts"] - day_s).astype(int) // 3600)
            r["id"] = np.char.add("TXN", np.char.zfill(np.arange(counter, counter + nr).astype(str), 9)).astype(object)
            counter += nr
            d = {k: (np.concatenate([d[k], r[k]], axis=1) if k == "raw" else np.concatenate([d[k], r[k]])) for k in d}
            N += nr

        # fees and costs depend on the final status
        succ, fail_, revd = d["status"] == "Success", d["status"] == "Failed", d["status"] == "Reversed"
        disc = np.where(succ, (d["list_fee"] * plan_disc[d["plan"]] / 100).round(2), 0.0)
        fee = np.where(succ, d["list_fee"] - disc, 0.0)
        bank_c = np.where(succ, d["raw"][2], 0.0)
        other = np.where(succ | revd | (fail_ & (d["ch"] == 4)), d["raw"][3], 0.0)
        sd = d["date"] + 1
        wd = (sd.astype(int) + 3) % 7
        sd = sd + np.where(wd >= 5, 7 - wd, 0).astype("timedelta64[D]")
        settle = pd.array(np.where(succ, date_key(sd), -1), dtype="Int64"); settle[~succ] = pd.NA

        df = pd.DataFrame({
            "transaction_id": d["id"],
            "transaction_ts": pd.Series(d["ts"]).dt.strftime("%Y-%m-%d %H:%M:%S"),
            "date_key": date_key(d["date"]), "txn_hour": d["hour"], "merchant_id": merchant_ids[d["mi"]],
            "terminal_id": d["term"], "location_key": loc_key[d["mi"]], "product_id": d["prod"],
            "channel_id": d["ch"], "issuer_bank_id": d["bank"], "plan_id": d["plan"], "response_code": d["code"],
            "txn_status": d["status"], "transaction_amount_ngn": d["amount"], "list_fee_ngn": d["list_fee"],
            "discount_ngn": disc, "fee_charged_ngn": fee.round(2), "processing_cost_ngn": d["raw"][0].round(2),
            "switching_cost_ngn": d["raw"][1].round(2), "bank_charge_ngn": bank_c.round(2),
            "other_cost_ngn": other.round(2), "is_retry": d["is_retry"], "original_txn_id": d["orig"],
            "settlement_date_key": settle})
        df = df.sort_values("transaction_ts")
        df.to_csv(path, mode="w" if first else "a", header=first, index=False, na_rep="")
        first = False

        tot = df.processing_cost_ngn + df.switching_cost_ngn + df.bank_charge_ngn + df.other_cost_ngn
        summaries.append(pd.DataFrame({
            "year": pd.Series(d["date"]).dt.year.values, "channel_id": df.channel_id.values, "merchant_id": df.merchant_id.values,
            "plan_id": df.plan_id.values, "status": df.txn_status.values, "amount": df.transaction_amount_ngn.values,
            "list_fee": df.list_fee_ngn.values, "discount": df.discount_ngn.values, "fee": df.fee_charged_ngn.values,
            "cost": tot.values, "month": per.month}))
        print(f"  {per}  {N:>7,} rows")
    print(f"  wrote fact_Transactions.csv  ({counter - 1:,} rows)")
    return pd.concat(summaries, ignore_index=True)


def story_check(s, merchants):
    """Does the generated data tell the story we planted? Prints the numbers that answer H1-H6."""
    s = s.copy(); s["net"] = s.fee - s.cost
    ok = s[s.status == "Success"]
    print("\nStory check")
    y = s.groupby("year").agg(txns=("fee", "size"), fee=("fee", "sum"), cost=("cost", "sum"), net=("net", "sum"))
    y["margin"] = y.net / y.fee
    print("  Totals by year (NGN millions)")
    for yr, r in y.iterrows():
        print(f"    {yr}: txns {r.txns:>10,.0f} | fee revenue {r.fee/1e6:>8,.1f} | cost {r.cost/1e6:>8,.1f} | net {r.net/1e6:>8,.1f} | margin {r.margin:.1%}")
    g = lambda c: y.loc[2025, c] / y.loc[2024, c] - 1
    print(f"  YoY: fee revenue {g('fee'):+.1%} | net revenue {g('net'):+.1%} | margin change {100*(y.loc[2025,'margin']-y.loc[2024,'margin']):+.1f} pts")

    names = {1: "POS", 2: "Web", 3: "App", 4: "USSD", 5: "QR"}
    mix = s.groupby(["year", "channel_id"]).size().unstack(0); mix = mix / mix.sum()
    mg = s.groupby(["year", "channel_id"]).apply(lambda d: d.net.sum() / d.fee.sum(), include_groups=False).unstack(0)
    print("  H1  channel share of attempts and net margin (2024 -> 2025)")
    for c in mix.index:
        print(f"    {names[c]:<5} share {mix.loc[c,2024]:.0%} -> {mix.loc[c,2025]:.0%} | margin {mg.loc[c,2024]:.0%} -> {mg.loc[c,2025]:.0%}")
    ck = ok.groupby("year").apply(lambda d: d.cost.sum() / len(d), include_groups=False)
    fk = ok.groupby("year").apply(lambda d: d.fee.sum() / len(d), include_groups=False)
    print(f"  H2  cost per successful txn {ck[2024]:.1f} -> {ck[2025]:.1f} ({ck[2025]/ck[2024]-1:+.0%}) vs fee per txn {fk[2024]:.1f} -> {fk[2025]:.1f} ({fk[2025]/fk[2024]-1:+.0%})")
    tr = ok.groupby("year").apply(lambda d: d.fee.sum() / d.amount.sum(), include_groups=False)
    print(f"  H3  take rate {tr[2024]:.2%} -> {tr[2025]:.2%} | discounts given NGN {s[s.year==2024].discount.sum()/1e6:.1f}m -> {s[s.year==2025].discount.sum()/1e6:.1f}m")
    fl = s[s.status == "Failed"].groupby("year").agg(n=("fee", "size"), lost=("list_fee", "sum"), cost=("cost", "sum"))
    fr = s[s.status != "Success"].groupby("year").size() / s.groupby("year").size()
    print(f"  H4  failure rate {fr[2024]:.1%} -> {fr[2025]:.1%} | fees forgone NGN {fl.lost[2024]/1e6:.1f}m -> {fl.lost[2025]/1e6:.1f}m | cost on failures NGN {fl.cost[2024]/1e6:.1f}m -> {fl.cost[2025]/1e6:.1f}m")
    loc = merchants.set_index("merchant_id").home_location_key
    nm = s.merchant_id.map(loc).isin([11, 12, 13, 14])
    for lab, sub in (("new cities", s[nm & (s.year == 2025)]), ("other cities", s[~nm & (s.year == 2025)])):
        print(f"  H5  2025 net margin, {lab}: {sub.net.sum()/sub.fee.sum():.1%}")
    qm = s[s.year == 2025].groupby(s.month.isin([11, 12])).apply(lambda d: d.net.sum() / d.fee.sum(), include_groups=False)
    print(f"  H6  2025 net margin, Jan-Oct {qm[False]:.1%} vs Nov-Dec {qm[True]:.1%}")
    for yr in (2024, 2025):
        by = s[s.year == yr].groupby("merchant_id").net.sum().sort_values(ascending=False)
        print(f"  Concentration {yr}: top 10 merchants = {by.head(10).sum()/by.sum():.0%} of net revenue")