"""check_step2.py | run after config.py and dimensions.py are in place:  python check_step2.py"""
import numpy as np
import generator.dimensions as D

tables = {
    "Date": D.build_date(), "Location": D.build_location(), "Product": D.build_product(),
    "Channel": D.build_channel(), "Bank": D.build_bank(), "SalesRep": D.build_salesrep(),
    "ResponseCode": D.build_response_code(), "PricingPlan": D.build_pricing_plan(), "CostRate": D.build_cost_rate(),
}
print(f"{'table':<14}{'rows':>6}   columns with missing values")
for name, df in tables.items():
    miss = [c for c in df.columns if df[c].isna().any()]
    print(f"{name:<14}{len(df):>6}   {', '.join(miss) if miss else '-'}")

cr = tables["CostRate"]
print("\nCost rates, processing, channel 4 (USSD), bank transfer:")
print(cr[(cr.cost_type == "Processing") & (cr.channel_id == 4) & (cr.product_id == 2)].to_string(index=False))

d = tables["Date"]
print("\nDate range:", d.full_date.min().date(), "to", d.full_date.max().date())
print("Holidays flagged:", int(d.is_public_holiday.sum()), "| peak-season days:", int(d.is_peak_season.sum()))