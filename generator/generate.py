"""
generate.py | PayBridge NG synthetic data generator
Step 3: build every dimension, merchant, terminal and pricing-bridge table and write them to CSV.
Step 4: simulate the transactions (transactions.py) and check that the planted story is visible.

Run from the generator folder:   python generate.py
"""
import numpy as np
import pandas as pd
import config as C
import dimensions as D
import transactions as T


def fmt(df):
    """Dates as YYYY-MM-DD, so SQL Server reads them without conversion."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
    return df


def write_csv(df, name):
    C.OUT_DIR.mkdir(exist_ok=True)
    fmt(df).to_csv(C.OUT_DIR / f"{name}.csv", index=False, na_rep="", encoding="utf-8")
    print(f"  wrote {name}.csv  ({len(df):,} rows)")


def build_all():
    """Builds every non-transaction table. Same seed, same result, every run."""
    rng = np.random.default_rng(C.SEED)
    t = {
        "dim_Date": D.build_date(), "dim_Location": D.build_location(), "dim_Product": D.build_product(),
        "dim_Channel": D.build_channel(), "dim_Bank": D.build_bank(), "dim_SalesRep": D.build_salesrep(),
        "dim_ResponseCode": D.build_response_code(), "dim_PricingPlan": D.build_pricing_plan(),
        "dim_CostRate": D.build_cost_rate(),
    }
    merchant, terminal, bridge, internal = D.build_merchants(rng, t["dim_Location"])
    t["dim_Merchant"], t["dim_Terminal"], t["bridge_MerchantPricing"] = merchant, terminal, bridge
    return t, internal, rng


def check_step3(t, internal):
    m, loc = t["dim_Merchant"], t["dim_Location"]
    print("\nChecks")
    assert m.home_location_key.isin(loc.location_key).all(), "merchant location missing from dim_Location"
    assert m.sales_rep_id.isin(t["dim_SalesRep"].sales_rep_id).all(), "sales rep missing"
    assert t["dim_Terminal"].merchant_id.isin(m.merchant_id).all(), "terminal merchant missing"
    assert t["bridge_MerchantPricing"].plan_id.isin(t["dim_PricingPlan"].plan_id).all(), "plan missing"
    launch = m.home_location_key.map(loc.set_index("location_key").launch_date)
    assert (m.onboarding_date >= launch).all(), "a merchant was onboarded before its city launched"
    assert ((m.churn_date.isna()) | (m.churn_date >= m.onboarding_date)).all(), "churn before onboarding"
    print("  all relationship checks passed")

    share = internal.base.sort_values(ascending=False).head(10).sum() / internal.base.sum()
    print(f"  top 10 merchants = {share:.0%} of expected volume (target 35-45%)")
    print("  merchants by segment:", m.merchant_segment.value_counts().to_dict())
    print("  merchants by status :", m.merchant_status.value_counts().to_dict())
    print("  onboarded before 2024:", int((m.onboarding_date < "2024-01-01").sum()),
          "| during 2024-25:", int((m.onboarding_date >= "2024-01-01").sum()))
    mk = m.home_location_key.map(loc.set_index("location_key").market_type).value_counts().to_dict()
    print("  merchants by market type:", mk)
    print(f"  POS merchants: {(internal.n_term > 0).sum()} | terminals: {len(t['dim_Terminal'])}")
    print(f"  repriced Enterprise merchants (H3): {(internal.plan1 != internal.plan0).sum()}")


if __name__ == "__main__":
    print("Building tables...")
    tables, internal, rng = build_all()
    for name, df in tables.items():
        write_csv(df, name)
    check_step3(tables, internal)
    print("\nStep 3 complete.\n\nSimulating transactions (this takes a few minutes)...")
    summary = T.generate_transactions(tables, internal, rng)
    T.story_check(summary, tables["dim_Merchant"])
    print("\nStep 4 complete.")