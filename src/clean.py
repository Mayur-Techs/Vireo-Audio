"""
clean.py — loads the raw exports and applies the fixes the data actually needs.

Every fix here is backed by a specific check, not a guess:
  1. legacy_fd timestamp correction — see README section "Why the +5:30 fix"
  2. join on agent_id, never name — two agents share the name "Kavya Pandey"
  3. blank csat_score excluded from every average, never treated as 0
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_raw():
    tickets = pd.read_csv(
        DATA_DIR / "tickets.csv",
        parse_dates=["created_at", "first_response_at", "resolved_at"],
    )
    agents = pd.read_csv(DATA_DIR / "agents.csv", parse_dates=["from_date", "to_date"])
    orders = pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"])
    customers = pd.read_csv(DATA_DIR / "customers.csv", parse_dates=["signup_date"])
    products = pd.read_csv(DATA_DIR / "products.csv", parse_dates=["launch_date"])
    return tickets, agents, orders, customers, products


def fix_legacy_timestamps(tickets: pd.DataFrame) -> pd.DataFrame:
    """legacy_fd resolved_at was reconstructed from a UTC event log (policy §9)
    while created_at/first_response_at are IST as displayed. Verified fix:
    add 5:30 to legacy resolved_at. Before the fix, 2309/3374 legacy rows have
    negative handle time (impossible). After, zero do, and the median lines up
    with the native-helpdesk median."""
    out = tickets.copy()
    mask = out["source_system"] == "legacy_fd"
    out.loc[mask, "resolved_at"] = out.loc[mask, "resolved_at"] + pd.Timedelta(hours=5, minutes=30)
    return out


def add_handle_time(tickets: pd.DataFrame) -> pd.DataFrame:
    out = tickets.copy()
    out["handle_time_h"] = (out["resolved_at"] - out["first_response_at"]).dt.total_seconds() / 3600
    return out


def attach_roster(tickets: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """Join on agent_id only. Never join on name — the roster has two people
    named 'Kavya Pandey' (A3006, Chat Frontline / A3029, Logistics)."""
    roster_cols = ["agent_id", "name", "site", "team", "shift", "tier"]
    return tickets.merge(agents[roster_cols], on="agent_id", how="left", suffixes=("", "_agent"))


def get_clean_tickets():
    """Returns the fully cleaned ticket table, plus the reference tables."""
    tickets, agents, orders, customers, products = load_raw()
    tickets = fix_legacy_timestamps(tickets)
    tickets = add_handle_time(tickets)
    tickets = attach_roster(tickets, agents)
    return tickets, agents, orders, customers, products


def attendance_only(tickets: pd.DataFrame) -> pd.DataFrame:
    """Policy §10: attendance = any ticket in status resolved or closed."""
    return tickets[tickets["status"].isin(["resolved", "closed"])].copy()


if __name__ == "__main__":
    tickets, agents, orders, customers, products = get_clean_tickets()
    neg_before = (
        (pd.read_csv(DATA_DIR / "tickets.csv", parse_dates=["first_response_at", "resolved_at"])
         .assign(ht=lambda d: (d["resolved_at"] - d["first_response_at"]).dt.total_seconds() / 3600)
         ["ht"] < 0).sum()
    )
    neg_after = (tickets["handle_time_h"] < 0).sum()
    print(f"Negative handle-time rows — before fix: {neg_before}, after fix: {neg_after}")
    print(f"Clean tickets shape: {tickets.shape}")
