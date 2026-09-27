"""
report.py — assembles everything into one static, self-contained report.html.
No server, no JS framework, no matplotlib — a static file that opens in any
browser, on any machine, with zero extra dependencies beyond pandas.
"""
import pandas as pd
from pathlib import Path

from clean import get_clean_tickets, attendance_only
from agent_scorecard import tier1_scorecard, tier2_summary, naive_bottom10_for_comparison
from lot_anomaly import sku_anomaly_scan, excess_cost_for_flagged, lot_breakdown

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def svg_line_chart(labels, values, width=760, height=220, title="", y_label=""):
    if not values:
        return "<p>(no data)</p>"
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    vmin, vmax = min(values), max(values)
    vmax = vmax if vmax > vmin else vmin + 1
    n = len(values)
    step = plot_w / max(n - 1, 1)

    def x(i):
        return pad_l + i * step

    def y(v):
        return pad_t + plot_h - (v - vmin) / (vmax - vmin) * plot_h

    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    ticks = ""
    tick_every = max(n // 8, 1)
    for i, lab in enumerate(labels):
        if i % tick_every == 0:
            ticks += (f'<text x="{x(i):.1f}" y="{height - pad_b + 15}" '
                      f'font-size="10" text-anchor="middle">{lab}</text>')
    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px">
      <text x="{pad_l}" y="16" font-size="13" font-weight="600">{title}</text>
      <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height - pad_b}" stroke="#999"/>
      <line x1="{pad_l}" y1="{height - pad_b}" x2="{width - pad_r}" y2="{height - pad_b}" stroke="#999"/>
      <text x="14" y="{pad_t + 5}" font-size="10">{vmax:.0f}</text>
      <text x="14" y="{height - pad_b}" font-size="10">{vmin:.0f}</text>
      <polyline fill="none" stroke="#c0392b" stroke-width="2" points="{points}"/>
      {ticks}
    </svg>"""


def df_to_html(df: pd.DataFrame, max_rows=15) -> str:
    return df.head(max_rows).to_html(index=False, border=0, classes="tbl", float_format=lambda x: f"{x:.2f}")


def build():
    tickets, agents, orders, customers, products = get_clean_tickets()
    att = attendance_only(tickets)

    # --- Module A ---
    naive = naive_bottom10_for_comparison(att)
    t1 = tier1_scorecard(att)
    t2 = tier2_summary(att)
    tier2_in_naive = int((naive["tier"] == 2).sum())

    # --- Module B ---
    scan = sku_anomaly_scan(att, products)
    flagged_names = scan[scan["flagged"]]["product_name"].tolist()

    flagged_sections = ""
    for name in flagged_names:
        cost = excess_cost_for_flagged(att, products, name)
        lots = lot_breakdown(att, products, orders, name)

        tk = att.merge(products[["sku", "product_name"]], left_on="product_sku", right_on="sku", how="left")
        sub = tk[tk["product_name"] == name].copy()
        sub["month"] = sub["created_at"].dt.to_period("M").astype(str)
        monthly = sub.groupby("month")["replacement_issued"].apply(lambda s: (s == "Y").mean() * 100)
        chart = svg_line_chart(list(monthly.index), list(monthly.values),
                                title=f"Monthly replacement rate — {name} (%)")

        flagged_sections += f"""
        <h3>Flagged SKU: {name}</h3>
        <p>Baseline (first half of data): <b>{cost['baseline_rate_pct']}%</b> &nbsp;→&nbsp;
           Current (second half): <b>{cost['current_rate_pct']}%</b>
           (n={cost['current_n']})</p>
        {chart}
        <p><b>Excess replacements vs. baseline expectation:</b> {cost['excess_replacements']:.0f}
           &nbsp;·&nbsp; <b>True unit cost</b> (policy §5, unit cost + Rs 340): Rs {cost['true_unit_replacement_cost_inr']}
           &nbsp;·&nbsp; <b>Potential excess cost, this analysis window:</b> Rs {cost['excess_cost_inr']:,.0f}
           &nbsp;·&nbsp; <b>Potential quarterly run-rate:</b> Rs {cost['quarterly_run_rate_inr']:,.0f}</p>
        <p>Lot concentration among replacement tickets (top 10 lots):</p>
        {df_to_html(lots[['lot_code','replacement_count']], 10)}
        <p style="color:#666;font-size:12px">Lot join: {lots.attrs.get('total_replacement_tickets') - lots.attrs.get('unresolved_lot_joins')}
           of {lots.attrs.get('total_replacement_tickets')} replacement tickets resolved to a lot code
           ({lots.attrs.get('unresolved_lot_joins')} unresolved even after the customer_id+SKU fallback join).</p>
        """

    tk_all = att.copy()
    tk_all["month"] = tk_all["created_at"].dt.to_period("M").astype(str)
    csat_monthly = tk_all.groupby("month")["csat_score"].mean()
    csat_chart = svg_line_chart(list(csat_monthly.index), list(csat_monthly.values),
                                 title="Company-wide monthly CSAT (blanks excluded)")

    # Compute the pre-fix negative handle-time count dynamically from the raw CSV,
    # mirroring the logic in clean.py's __main__ block — never hardcode this number.
    from clean import DATA_DIR as _DATA_DIR
    _raw = pd.read_csv(
        _DATA_DIR / "tickets.csv",
        usecols=["first_response_at", "resolved_at"],
        parse_dates=["first_response_at", "resolved_at"],
    )
    neg_before = int(((_raw["resolved_at"] - _raw["first_response_at"]).dt.total_seconds() / 3600 < 0).sum())
    neg_after = int((tickets["handle_time_h"] < 0).sum())
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Vireo CX Signal Report</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color:#222; }}
h1 {{ font-size: 22px; }} h2 {{ font-size: 17px; margin-top: 40px; border-top: 1px solid #ddd; padding-top: 16px; }}
h3 {{ font-size: 15px; color:#a33; }}
.tbl {{ border-collapse: collapse; width: 100%; font-size: 13px; margin: 10px 0; }}
.tbl th {{ background:#f2f2f2; text-align:left; padding:6px 8px; }}
.tbl td {{ padding:6px 8px; border-top:1px solid #eee; }}
.callout {{ background:#fff7e6; border-left:4px solid #e6a817; padding:12px 16px; margin:16px 0; }}
</style></head><body>

<h1>Vireo Audio — CX Signal Report</h1>
<div class="callout">
<b>Headline number:</b> {flagged_names[0] if flagged_names else 'Flagged SKU'} replacement rate rose from
{scan[scan['flagged']]['baseline_rate_pct'].values[0] if len(flagged_names) else 'n/a'}% baseline to
{scan[scan['flagged']]['current_rate_pct'].values[0] if len(flagged_names) else 'n/a'}% —
concentrated in specific manufacturing lots, worth roughly the quarterly run-rate shown below.
This is larger than the Rs 4,00,000 Q3 training budget under discussion.
</div>

<h2>1. Data quality fixes applied</h2>
<ul>
  <li>Legacy (<code>legacy_fd</code>) ticket resolution timestamps corrected by +5:30 (UTC→IST) —
      eliminated {neg_before} impossible negative handle-time rows (before fix: {neg_before}; after fix: {neg_after}).</li>
  <li>All joins to the agent roster use <code>agent_id</code>, never <code>name</code>
      (two agents share the name "Kavya Pandey").</li>
  <li>Blank <code>csat_score</code> excluded from every average (~56% of tickets have no response;
      policy §8 — a blank is "no response," not a 0).</li>
</ul>

<h2>2. Requested analysis — Agent scorecard</h2>
<p>The literal ask (rank everyone, flag the bottom 10) puts
<b>{tier2_in_naive} of 10</b> flagged agents in Escalations & Warranty — the Tier 2 hardware/warranty
team, which policy §6 explicitly says should not be volume/CSAT-compared with Tier 1.</p>
<p><b>Naive bottom 10 (not recommended for training spend as-is):</b></p>
{df_to_html(naive[['agent_id','agent_name','team','tier','csat_avg','csat_responses']])}
<p><b>Fair Tier-1-only bottom 10 (recommended target for the Q3 training budget):</b></p>
{df_to_html(t1[['agent_id','agent_name','team','csat_avg','csat_responses','handle_time_avg_h']].head(10))}
<p><b>Tier 2 summary (reported separately, on resolution-days per policy §6 — not a ranking):</b></p>
{df_to_html(t2[['agent_id','agent_name','team','csat_avg','resolution_days_avg']])}

<h2>3. Additional finding — Product/lot anomaly scan (all SKUs, generic rule)</h2>
<p>Baseline = first half of the 18-month data window; current = second half.
Flag threshold: current rate ≥ 2x baseline, with ≥50 tickets in each half.</p>
{df_to_html(scan)}
{flagged_sections}

<h2>4. Company-wide CSAT trend (context)</h2>
{csat_chart}
<p style="font-size:12px;color:#666">Correlational only — this does not on its own prove the
product defect caused the CSAT dip, but the timing lines up closely with the anomaly window above.</p>

<h2>5. Known gaps — read before presenting this</h2>
<ul>
  <li>Neha's email references a "hardware triage rota (Kavya's four plus the warranty team)" that
      does not map cleanly onto any roster field — this report uses the roster's <code>tier</code>
      and <code>team</code> columns, which is a documented policy-based split, not a re-creation of
      that informal rota.</li>
  <li>"~40 junk IVR tickets" (per Sameer's email) is a narrower claim than a literal
      <code>[IVR transcript]</code> text match, which hits far more rows, most of them legible —
      isolating the true unusable subset needs a text-quality heuristic not yet built here.</li>
  <li>The excess-cost figure is a run-rate estimate based on the assumption that the current-half
      rate elevation continues. It is not a guaranteed saving and does not prove causality — it is
      a signal that warrants investigation.</li>
</ul>

<h2>6. AI usage and runtime cost disclosure</h2>
<ul>
  <li><b>Core analytics runtime cost: Rs 0 paid model cost.</b> All metrics in this report
      (agent scorecard, CSAT averages, handle times, SKU anomaly scan, lot breakdown) are computed
      using pandas only. No paid API call is made during a standard run.</li>
  <li>An <i>optional</i> AI-assist step (<code>src/defect_summarizer.py</code>) can classify failure
      modes on tickets for any flagged SKU if <code>ANTHROPIC_API_KEY</code> is set. This step is
      skipped by default and was not invoked to produce this report. No AI classification accuracy
      number is claimed here.</li>
  <li>This tool uses no external databases, no authentication, no Docker, and no server. The output
      is a single static HTML file reproducible on any machine with Python and pandas.</li>
</ul>

</body></html>"""

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "report.html").write_text(html, encoding="utf-8")
    naive.to_csv(OUT_DIR / "naive_bottom10.csv", index=False)
    t1.to_csv(OUT_DIR / "tier1_scorecard_full.csv", index=False)
    t2.to_csv(OUT_DIR / "tier2_summary.csv", index=False)
    scan.to_csv(OUT_DIR / "sku_anomaly_scan.csv", index=False)
    print(f"Wrote {OUT_DIR / 'report.html'} and 4 CSVs to {OUT_DIR}")


if __name__ == "__main__":
    build()
