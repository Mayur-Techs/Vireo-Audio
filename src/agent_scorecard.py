"""
agent_scorecard.py — Module A.

Policy §6: Tier 2 (Escalations & Warranty) is not to be compared with Tier 1
on volume/CSAT metrics — their cases are multi-touch by design and measured
in resolution-days, not tickets/week. Neha's email makes the same point about
the hardware triage rota getting the hardest cases by design.

So: Tier 1 gets a ranked bottom-10 list. Tier 2 gets a separate summary table,
never ranked against Tier 1, on a metric that actually fits their work.

MIN_RESPONSES gates out agents with too few CSAT responses to rank fairly.
"""
import pandas as pd

MIN_RESPONSES = 10


def tier1_scorecard(clean_tickets: pd.DataFrame) -> pd.DataFrame:
    t1 = clean_tickets[clean_tickets["tier"] == 1]
    agg = t1.groupby("agent_id").agg(
        agent_name=("name", "first"),
        team=("team", "first"),
        tickets_handled=("ticket_id", "count"),
        csat_responses=("csat_score", "count"),
        csat_avg=("csat_score", "mean"),
        handle_time_avg_h=("handle_time_h", "mean"),
        handle_time_median_h=("handle_time_h", "median"),
    ).reset_index()
    eligible = agg[agg["csat_responses"] >= MIN_RESPONSES].copy()
    return eligible.sort_values("csat_avg")


def tier2_summary(clean_tickets: pd.DataFrame) -> pd.DataFrame:
    """Reported separately, on resolution time in days (policy §6: 'measured
    on resolution in days, not tickets closed per week')."""
    t2 = clean_tickets[clean_tickets["tier"] == 2]
    agg = t2.groupby("agent_id").agg(
        agent_name=("name", "first"),
        team=("team", "first"),
        cases_handled=("ticket_id", "count"),
        csat_responses=("csat_score", "count"),
        csat_avg=("csat_score", "mean"),
        resolution_days_avg=("handle_time_h", lambda s: s.mean() / 24),
        resolution_days_median=("handle_time_h", lambda s: s.median() / 24),
    ).reset_index()
    return agg.sort_values("resolution_days_avg", ascending=False)


def naive_bottom10_for_comparison(clean_tickets: pd.DataFrame) -> pd.DataFrame:
    """Included ONLY to show the confound in the report — this is the ranking
    Priya's literal ask produces, and why we didn't ship it as-is."""
    agg = clean_tickets.groupby("agent_id").agg(
        agent_name=("name", "first"),
        team=("team", "first"),
        tier=("tier", "first"),
        csat_responses=("csat_score", "count"),
        csat_avg=("csat_score", "mean"),
        handle_time_avg_h=("handle_time_h", "mean"),
    ).reset_index()
    eligible = agg[agg["csat_responses"] >= MIN_RESPONSES]
    return eligible.sort_values("csat_avg").head(10)


if __name__ == "__main__":
    from clean import get_clean_tickets, attendance_only

    tickets, *_ = get_clean_tickets()
    att = attendance_only(tickets)

    naive = naive_bottom10_for_comparison(att)
    print("Naive bottom 10 (what Priya's literal ask produces):")
    print(naive[["agent_id", "agent_name", "team", "tier", "csat_avg", "csat_responses"]].to_string(index=False))
    print(f"\nTier 2 count in naive bottom 10: {(naive['tier'] == 2).sum()} / 10")

    print("\nFair Tier-1-only bottom 10:")
    t1 = tier1_scorecard(att).head(10)
    print(t1[["agent_id", "agent_name", "team", "csat_avg", "csat_responses", "handle_time_avg_h"]].to_string(index=False))

    print("\nTier 2 summary (separate metric, not ranked against Tier 1):")
    t2 = tier2_summary(att)
    print(t2[["agent_id", "agent_name", "team", "csat_avg", "resolution_days_avg"]].to_string(index=False))
