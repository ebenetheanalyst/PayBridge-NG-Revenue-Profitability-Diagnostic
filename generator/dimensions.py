"""dimensions.py | builds every small table plus the merchant, terminal and pricing-bridge tables."""
import numpy as np
import pandas as pd
import config as C


def build_date():
    d = pd.DataFrame({"full_date": pd.date_range(C.START_DATE, C.DATE_TABLE_END, freq="D")})
    f = d.full_date.dt
    d["date_key"] = f.strftime("%Y%m%d").astype(int)
    d["year"], d["quarter"], d["month_num"] = f.year, f.quarter, f.month
    d["month_name"], d["year_month"] = f.strftime("%B"), f.strftime("%Y-%m")
    d["week_of_year"] = f.isocalendar().week.astype(int)
    d["day_of_week"] = f.weekday + 1
    d["is_weekend"] = (d.day_of_week >= 6).astype(int)
    d["is_month_end"] = f.is_month_end.astype(int)
    d["holiday_name"] = d.full_date.dt.date.map(C.HOLIDAYS)
    d["is_public_holiday"] = d.holiday_name.notna().astype(int)
    d["is_peak_season"] = d.month_num.isin([11, 12]).astype(int)
    d["fiscal_year"], d["fiscal_quarter"] = d.year, d.quarter
    d["same_date_py"] = d.full_date - pd.DateOffset(years=1)
    return d[["date_key", "full_date", "year", "quarter", "month_num", "month_name", "year_month", "week_of_year",
              "day_of_week", "is_weekend", "is_month_end", "is_public_holiday", "holiday_name", "is_peak_season",
              "fiscal_year", "fiscal_quarter", "same_date_py"]]


def build_location():
    rows = [(i + 1, c, s, z, la, lo, mt, pd.Timestamp(ld)) for i, (c, s, z, la, lo, mt, ld, _) in enumerate(C.LOCATIONS)]
    return pd.DataFrame(rows, columns=["location_key", "city", "state", "geopolitical_zone", "latitude", "longitude",
                                       "market_type", "launch_date"])


def build_product():
    return pd.DataFrame([(k, n, c, pd.Timestamp(d)) for k, (n, c, d) in C.PRODUCTS.items()],
                        columns=["product_id", "product_name", "product_category", "product_launch_date"])


def build_channel():
    return pd.DataFrame([(k, n, t) for k, (n, t) in C.CHANNELS.items()], columns=["channel_id", "channel_name", "channel_type"])


def build_bank():
    return pd.DataFrame([(i + 1, n, t) for i, (n, t, _, _) in enumerate(C.BANKS)],
                        columns=["issuer_bank_id", "bank_name", "bank_type"])


def build_salesrep():
    return pd.DataFrame(C.SALES_REPS, columns=["sales_rep_id", "rep_name", "team", "region"])


def build_response_code():
    return pd.DataFrame([(k, *v) for k, v in C.RESPONSE_CODES.items()],
                        columns=["response_code", "description", "failure_category", "is_platform_fault", "is_retryable"])


def build_pricing_plan():
    return pd.DataFrame([(k, *v) for k, v in C.PLANS.items()],
                        columns=["plan_id", "plan_name", "fee_model", "fee_pct", "flat_fee_ngn", "fee_cap_ngn",
                                 "standard_discount_pct"])


def build_cost_rate():
    """Two versions per channel/product/cost type: 2024 rates, then inflated rates from COST_CHANGE_DATE."""
    rows, i = [], 1
    for ch, prods in C.CHANNEL_PRODUCT.items():
        for pr in prods:
            for ct in C.COST_TYPES:
                pct, flat, cap = C.COSTS[ch][ct]
                m = C.COST_INFLATION[ct]
                end_old = pd.Timestamp(C.COST_CHANGE_DATE) - pd.Timedelta(days=1)
                rows.append((i, ct, ch, pr, pct, flat, cap, pd.Timestamp(C.START_DATE), end_old)); i += 1
                rows.append((i, ct, ch, pr, round(pct * m, 5), round(flat * m, 2), round(cap * m, 2),
                             pd.Timestamp(C.COST_CHANGE_DATE), pd.NaT)); i += 1
    return pd.DataFrame(rows, columns=["cost_rate_id", "cost_type", "channel_id", "product_id", "rate_pct",
                                       "flat_cost_ngn", "cost_cap_ngn", "effective_from", "effective_to"])


def build_merchants(rng, loc):
    """Returns (merchant_df, terminal_df, bridge_df, internal) where internal holds generator-only columns."""
    n = C.N_MERCHANTS
    start, end = pd.Timestamp(C.START_DATE), pd.Timestamp(C.END_DATE)
    size = rng.lognormal(0, C.SIZE_SIGMA, n)
    rank = np.empty(n, int); rank[np.argsort(-size)] = np.arange(n)
    c1, c2, c3 = (int(x * n) for x in C.SEGMENT_SPLIT)
    seg = np.where(rank < c1, "Enterprise", np.where(rank < c2, "Mid-market", np.where(rank < c3, "SME", "Micro")))

    # location (large merchants stay out of brand-new markets)
    lw = np.array([x[7] for x in C.LOCATIONS]); new_mkt = (loc.market_type == "New market").values
    loc_idx = np.empty(n, int)
    for i in range(n):
        w = lw.copy()
        if seg[i] in ("Enterprise", "Mid-market"):
            w[new_mkt] = 0
        loc_idx[i] = rng.choice(len(w), p=w / w.sum())
    loc_key = loc.location_key.values[loc_idx]
    is_new = new_mkt[loc_idx]
    launch = loc.launch_date.values[loc_idx]

    # onboarding
    existing = rng.random(n) < C.EXISTING_SHARE
    old_start = pd.Timestamp("2021-01-01")
    d_old = rng.integers(0, (start - old_start).days, n)
    d_new = rng.integers(0, (pd.Timestamp(C.NEW_ONBOARDING_END) - start).days, n)
    onb = pd.DatetimeIndex(np.where(existing, old_start + pd.to_timedelta(d_old, unit="D"),
                                    start + pd.to_timedelta(d_new, unit="D")))
    launch = pd.to_datetime(launch)
    late = onb < launch
    onb = pd.Series(np.where(late, launch + pd.to_timedelta(rng.integers(0, 120, n), unit="D"), onb))
    onb = onb.clip(upper=end - pd.Timedelta(days=45))

    # churn and dormant (never Enterprise)
    elig = np.where(seg != "Enterprise")[0]; rng.shuffle(elig)
    n_ch, n_do = int(C.CHURN_SHARE * n), int(C.DORMANT_SHARE * n)
    churn = pd.Series([pd.NaT] * n, dtype="datetime64[ns]"); dorm = churn.copy()
    for i in elig[:n_ch]:
        lo = max(onb[i] + pd.Timedelta(days=120), pd.Timestamp("2024-09-01"))
        hi = pd.Timestamp("2025-11-30")
        if lo < hi:
            churn[i] = lo + pd.Timedelta(days=int(rng.integers(0, (hi - lo).days)))
    for i in elig[n_ch:n_ch + n_do]:
        lo = max(onb[i] + pd.Timedelta(days=60), pd.Timestamp("2025-01-01"))
        dorm[i] = lo + pd.Timedelta(days=int(rng.integers(0, 240)))
    status = np.where(churn.notna(), "Churned", np.where(dorm.notna(), "Dormant", "Active"))

    # names, industry, reps
    inds = list(C.INDUSTRIES); iw = np.array([C.INDUSTRIES[k][0] for k in inds]); iw = iw / iw.sum()
    ind = rng.choice(inds, size=n, p=iw)
    names, seen = [], set()
    for i in range(n):
        base = f"{rng.choice(C.NAME_PREFIXES)} {rng.choice(C.INDUSTRIES[ind[i]][1])}"
        nm, k = base, 2
        while nm in seen:
            nm = f"{base} {k}"; k += 1
        seen.add(nm); names.append(nm)
    reps = pd.DataFrame(C.SALES_REPS, columns=["id", "name", "team", "region"])
    rep_id = np.array([rng.choice(reps[reps.team == C.REP_TEAM[s]].id.values) for s in seg])

    ids = np.array([f"M{i + 1:04d}" for i in range(n)])
    merchant = pd.DataFrame({
        "merchant_id": ids, "merchant_name": names, "merchant_segment": seg, "industry": ind,
        "is_key_account": (seg == "Enterprise").astype(int), "onboarding_date": onb.values,
        "acquisition_channel": rng.choice(C.ACQUISITION_CHANNELS, size=n), "home_location_key": loc_key,
        "sales_rep_id": rep_id, "merchant_status": status, "churn_date": churn.values})

    # terminals
    trows, n_term = [], np.zeros(n, int)
    for i in range(n):
        if rng.random() < C.POS_PROB[seg[i]]:
            lo, hi = C.TERMINALS[seg[i]]; k = int(rng.integers(lo, hi + 1)); n_term[i] = k
            for t in range(k):
                tt = rng.choice(list(C.TERMINAL_TYPES))
                st = "Retired" if status[i] == "Churned" else ("Idle" if rng.random() < 0.08 else "Active")
                trows.append((f"{ids[i]}-T{t + 1:02d}", ids[i], tt, onb[i], st, C.TERMINAL_TYPES[tt]))
    terminal = pd.DataFrame(trows, columns=["terminal_id", "merchant_id", "terminal_type", "deployment_date",
                                            "terminal_status", "monthly_terminal_cost_ngn"])

    # pricing bridge: everyone starts on their segment plan; some Enterprise merchants are repriced (H3)
    plan0 = np.array([C.SEGMENT_PLAN[s] for s in seg]); plan1 = plan0.copy()
    sw = pd.Series([pd.NaT] * n, dtype="datetime64[ns]")
    ent = np.where(seg == "Enterprise")[0]; rng.shuffle(ent)
    w0, w1 = pd.Timestamp(C.REPRICE_WINDOW[0]), pd.Timestamp(C.REPRICE_WINDOW[1])
    for i in ent[:C.N_ENTERPRISE_REPRICED]:
        sw[i] = w0 + pd.Timedelta(days=int(rng.integers(0, (w1 - w0).days)))
        plan1[i] = 5
    brows = []
    for i in range(n):
        if pd.isna(sw[i]):
            brows.append((ids[i], plan0[i], onb[i], pd.NaT))
        elif sw[i] <= onb[i]:
            # the repricing date fell before this merchant joined, so it starts on the new plan
            brows.append((ids[i], plan1[i], onb[i], pd.NaT))
        else:
            brows.append((ids[i], plan0[i], onb[i], sw[i] - pd.Timedelta(days=1)))
            brows.append((ids[i], plan1[i], sw[i], pd.NaT))
    bridge = pd.DataFrame(brows, columns=["merchant_id", "plan_id", "effective_from", "effective_to"])

    # generator-only columns
    vol = size * np.where(is_new, C.NEW_MARKET_VOLUME_MULT, 1.0)
    internal = pd.DataFrame({
        "merchant_id": ids, "base": vol / vol.sum() * C.TARGET_DAILY_TXNS, "onb": onb.values,
        "churn": churn.values, "dorm": dorm.values, "location_key": loc_key, "is_new_market": is_new,
        "seg_mult": [C.SEGMENT_AMT_MULT[s] for s in seg], "n_term": n_term, "plan0": plan0, "plan1": plan1,
        "switch": sw.values, "growth": rng.normal(C.MERCHANT_GROWTH_MEAN, C.MERCHANT_GROWTH_SD, n)})
    return merchant, terminal, bridge, internal