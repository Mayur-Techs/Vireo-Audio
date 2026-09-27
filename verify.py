"""Verification script — run once, then delete or keep for CI."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from clean import get_clean_tickets, attendance_only, DATA_DIR
from agent_scorecard import naive_bottom10_for_comparison, tier1_scorecard, tier2_summary
from lot_anomaly import sku_anomaly_scan, excess_cost_for_flagged, lot_breakdown
import pandas as pd

tickets, agents, orders, customers, products = get_clean_tickets()
att = attendance_only(tickets)

print("=== Core Metrics Verification ===")
print(f"1. Total ticket count (all statuses):  {len(tickets)}")
print(f"   Attendance-only (resolved/closed):  {len(att)}")
unique_ids = att["ticket_id"].nunique()
print(f"   Ticket IDs unique in att:            {unique_ids == len(att)} (unique={unique_ids}, total={len(att)})")

blank_pct = tickets["csat_score"].isna().mean() * 100
print(f"2. CSAT blank percentage:              {blank_pct:.1f}%")

# Negative handle time
raw = pd.read_csv(
    DATA_DIR / "tickets.csv",
    usecols=["first_response_at", "resolved_at"],
    parse_dates=["first_response_at", "resolved_at"],
)
neg_before = int(((raw["resolved_at"] - raw["first_response_at"]).dt.total_seconds() / 3600 < 0).sum())
neg_after = int((tickets["handle_time_h"] < 0).sum())
print(f"3. Negative handle-time BEFORE fix:    {neg_before}")
print(f"   Negative handle-time AFTER fix:     {neg_after}")

# Agent scorecard
naive = naive_bottom10_for_comparison(att)
t1 = tier1_scorecard(att)
t2 = tier2_summary(att)
tier2_in_naive = int((naive["tier"] == 2).sum())
t1_bottom10_count = len(t1.head(10))
print(f"4. Tier-2 agents in naive bottom 10:   {tier2_in_naive}")
print(f"   Tier-1 bottom 10 row count:         {t1_bottom10_count}")

# Anomaly scan
scan = sku_anomaly_scan(att, products)
flagged = scan[scan["flagged"]]
print(f"5. Flagged SKUs:                       {flagged['product_name'].tolist()}")
if len(flagged):
    print(f"   Baseline rate:                     {flagged['baseline_rate_pct'].values[0]}%")
    print(f"   Current rate:                      {flagged['current_rate_pct'].values[0]}%")

# Excess cost
for name in flagged["product_name"].tolist():
    cost = excess_cost_for_flagged(att, products, name)
    print(f"   Excess replacements:               {cost['excess_replacements']:.0f}")
    print(f"   True unit cost (Rs):               {cost['true_unit_replacement_cost_inr']}")
    print(f"   Potential excess cost (Rs):        {cost['excess_cost_inr']:,.0f}")
    print(f"   Potential quarterly run-rate (Rs): {cost['quarterly_run_rate_inr']:,.0f}")

# Lot breakdown
lots = lot_breakdown(att, products, orders, "Pulse 2 True Wireless Earbuds")
total = lots.attrs["total_replacement_tickets"]
unresolved = lots.attrs["unresolved_lot_joins"]
print(f"6. Total replacement tickets:          {total}")
print(f"   Resolved to lot code:              {total - unresolved}")
print(f"   Unresolved lot joins:              {unresolved}")

print("\n=== All checks complete ===")
