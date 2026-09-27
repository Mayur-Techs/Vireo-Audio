"""
lot_anomaly.py — Module B.

Generic anomaly rule, not hardcoded to "Pulse 2": for each SKU with tickets in
both halves of the data's date range, compare replacement rate in the first
half (baseline) vs. the second half (current). Flag if current >= 2x baseline
and both halves have at least MIN_N tickets — otherwise a flag is noise, not
a finding.

For any flagged SKU, break down replacement tickets by manufacturing lot_code
(joined via order_id, falling back to customer_id + product_sku per the
README when order_id is blank) to see whether the defect concentrates in
specific production batches.
"""
import pandas as pd

MIN_N = 50
FLAG_MULTIPLE = 2.0


def _replacement_rate(df: pd.DataFrame) -> tuple[float, int]:
    n = len(df)
    if n == 0:
        return 0.0, 0
    rate = (df["replacement_issued"] == "Y").mean()
    return rate, n


def sku_anomaly_scan(clean_tickets: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    tk = clean_tickets.merge(
        products[["sku", "product_name", "family", "unit_cost_inr"]],
        left_on="product_sku", right_on="sku", how="left",
    )
    start, end = tk["created_at"].min(), tk["created_at"].max()
    midpoint = start + (end - start) / 2

    rows = []
    for name, grp in tk.groupby("product_name"):
        baseline = grp[grp["created_at"] < midpoint]
        current = grp[grp["created_at"] >= midpoint]
        base_rate, base_n = _replacement_rate(baseline)
        cur_rate, cur_n = _replacement_rate(current)
        flagged = (
            base_n >= MIN_N and cur_n >= MIN_N
            and base_rate > 0 and cur_rate >= FLAG_MULTIPLE * base_rate
        )
        rows.append({
            "product_name": name,
            "family": grp["family"].iloc[0] if len(grp) else None,
            "unit_cost_inr": grp["unit_cost_inr"].iloc[0] if len(grp) else None,
            "baseline_rate_pct": round(base_rate * 100, 1),
            "baseline_n": base_n,
            "current_rate_pct": round(cur_rate * 100, 1),
            "current_n": cur_n,
            "flagged": flagged,
        })
    out = pd.DataFrame(rows).sort_values("current_rate_pct", ascending=False)
    return out


def excess_cost_for_flagged(clean_tickets: pd.DataFrame, products: pd.DataFrame,
                             product_name: str, replacement_logistics_cost=340) -> dict:
    """Quantifies the excess replacement cost for one flagged SKU: actual
    replacements in the 'current' half minus what baseline rate would predict,
    priced at unit_cost + logistics (policy §5), not any informally-quoted figure."""
    tk = clean_tickets.merge(
        products[["sku", "product_name", "unit_cost_inr"]],
        left_on="product_sku", right_on="sku", how="left",
    )
    sub = tk[tk["product_name"] == product_name]
    start, end = tk["created_at"].min(), tk["created_at"].max()
    midpoint = start + (end - start) / 2
    baseline = sub[sub["created_at"] < midpoint]
    current = sub[sub["created_at"] >= midpoint]

    base_rate, _ = _replacement_rate(baseline)
    cur_rate, cur_n = _replacement_rate(current)
    actual_repl = (current["replacement_issued"] == "Y").sum()
    expected_repl = cur_n * base_rate
    excess = max(actual_repl - expected_repl, 0)
    unit_cost = sub["unit_cost_inr"].dropna().iloc[0] if sub["unit_cost_inr"].notna().any() else None
    true_cost = (unit_cost + replacement_logistics_cost) if unit_cost is not None else None
    window_days = (current["created_at"].max() - current["created_at"].min()).days or 1
    excess_cost = excess * true_cost if true_cost else None
    quarterly_run_rate = excess_cost / window_days * 91 if excess_cost else None

    return {
        "product_name": product_name,
        "baseline_rate_pct": round(base_rate * 100, 1),
        "current_rate_pct": round(cur_rate * 100, 1),
        "current_n": int(cur_n),
        "actual_replacements": int(actual_repl),
        "expected_replacements_at_baseline": round(expected_repl, 0),
        "excess_replacements": round(excess, 0),
        "true_unit_replacement_cost_inr": true_cost,
        "excess_cost_inr": round(excess_cost, 0) if excess_cost else None,
        "quarterly_run_rate_inr": round(quarterly_run_rate, 0) if quarterly_run_rate else None,
    }


def lot_breakdown(clean_tickets: pd.DataFrame, products: pd.DataFrame, orders: pd.DataFrame,
                   product_name: str) -> pd.DataFrame:
    """Lot-code concentration among replacement tickets for one flagged SKU.
    Primary join: order_id. Fallback (per README): customer_id + product_sku,
    matched to the most recent order at/before the ticket's created_at."""
    tk = clean_tickets.merge(
        products[["sku", "product_name"]], left_on="product_sku", right_on="sku", how="left"
    )
    sub = tk[(tk["product_name"] == product_name) & (tk["replacement_issued"] == "Y")].copy()

    has_order = sub[sub["order_id"].notna()]
    via_order = has_order.merge(orders[["order_id", "lot_code"]], on="order_id", how="left")

    no_order = sub[sub["order_id"].isna()]
    fallback_lots = []
    if len(no_order):
        cust_orders = orders[orders["sku"] == via_order["sku"].iloc[0]] if len(via_order) else orders
        for _, row in no_order.iterrows():
            candidates = orders[
                (orders["customer_id"] == row["customer_id"])
                & (orders["sku"] == row["product_sku"])
                & (orders["order_date"] <= row["created_at"])
            ].sort_values("order_date")
            fallback_lots.append(candidates["lot_code"].iloc[-1] if len(candidates) else None)
    no_order = no_order.assign(lot_code=fallback_lots)

    all_lots = pd.concat([via_order[["ticket_id", "lot_code"]], no_order[["ticket_id", "lot_code"]]])
    unresolved = all_lots["lot_code"].isna().sum()
    counts = all_lots["lot_code"].value_counts().reset_index()
    counts.columns = ["lot_code", "replacement_count"]
    counts.attrs["unresolved_lot_joins"] = int(unresolved)
    counts.attrs["total_replacement_tickets"] = int(len(sub))
    return counts


if __name__ == "__main__":
    from clean import get_clean_tickets, attendance_only

    tickets, agents, orders, customers, products = get_clean_tickets()
    att = attendance_only(tickets)

    scan = sku_anomaly_scan(att, products)
    print("SKU anomaly scan (baseline = first half of data, current = second half):")
    print(scan.to_string(index=False))

    flagged = scan[scan["flagged"]]
    for name in flagged["product_name"]:
        print(f"\n--- Excess cost for flagged SKU: {name} ---")
        result = excess_cost_for_flagged(att, products, name)
        for k, v in result.items():
            print(f"  {k}: {v}")

        print(f"\n--- Lot concentration for: {name} ---")
        lots = lot_breakdown(att, products, orders, name)
        print(lots.head(10).to_string(index=False))
        print(f"  (unresolved lot joins: {lots.attrs.get('unresolved_lot_joins')} of "
              f"{lots.attrs.get('total_replacement_tickets')} replacement tickets)")
