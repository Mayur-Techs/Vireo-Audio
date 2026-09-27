"""
defect_summarizer.py — optional AI-assist step.

Scope, deliberately narrow: only summarizes free text for tickets on SKUs
that lot_anomaly.py already flagged as statistically anomalous — a few
hundred tickets, not the full 11,750-row history. This is a direct response
to Arjun Mehta's email ruling out per-ticket model calls at scale across the
full ticket volume.

Requires ANTHROPIC_API_KEY in the environment. If it's not set, this step is
skipped and the report notes that it was skipped — the rest of the tool
(Modules A and B) runs with zero dependency on this.

Cost, for the record (see README): batching 20 tickets per call against a
cheap model runs to a few hundred rupees a month at worst, even at Vireo's
full support volume — nowhere near the Rs-5-per-ticket-times-12,000 figure
Arjun's email explicitly vetoed.
"""
import os
import json
import pandas as pd

BATCH_SIZE = 20
MODEL = "claude-haiku-4-5-20251001"  # cheapest current model; swap freely


def _client():
    try:
        import anthropic
    except ImportError:
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


def _batch_prompt(rows: list[dict]) -> str:
    lines = []
    for i, r in enumerate(rows):
        msg = str(r.get("customer_message", ""))[:200].replace("\n", " ")
        note = str(r.get("agent_notes", ""))[:200].replace("\n", " ")
        lines.append(f"{i}. customer_message: {msg} | agent_notes: {note}")
    body = "\n".join(lines)
    return (
        "Each numbered line below is one support ticket's customer message and "
        "agent closing note, for a single flagged product. Return ONLY a JSON "
        "array, one object per line, in order, each with:\n"
        '  {"index": <int>, "failure_mode": "<3-6 word description>", '
        '"confidence": "high"|"medium"|"low"}\n'
        "No preamble, no markdown fences, JSON array only.\n\n" + body
    )


def summarize_flagged_tickets(clean_tickets: pd.DataFrame, products: pd.DataFrame,
                               flagged_product_name: str) -> pd.DataFrame | None:
    client = _client()
    if client is None:
        return None

    tk = clean_tickets.merge(
        products[["sku", "product_name"]], left_on="product_sku", right_on="sku", how="left"
    )
    sub = tk[
        (tk["product_name"] == flagged_product_name) & (tk["replacement_issued"] == "Y")
    ][["ticket_id", "customer_message", "agent_notes"]].reset_index(drop=True)

    results = []
    for start in range(0, len(sub), BATCH_SIZE):
        batch = sub.iloc[start:start + BATCH_SIZE]
        prompt = _batch_prompt(batch.to_dict("records"))
        resp = client.messages.create(
            model=MODEL, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            parsed = json.loads(text.strip().strip("`"))
        except json.JSONDecodeError:
            continue
        for item in parsed:
            idx = item.get("index")
            if idx is not None and idx < len(batch):
                results.append({
                    "ticket_id": batch.iloc[idx]["ticket_id"],
                    "failure_mode": item.get("failure_mode"),
                    "confidence": item.get("confidence"),
                })

    if not results:
        return None
    out = pd.DataFrame(results)
    return out


def dominant_failure_mode(summary_df: pd.DataFrame) -> pd.DataFrame:
    return summary_df["failure_mode"].value_counts().reset_index().rename(
        columns={"index": "failure_mode", "failure_mode": "count"}
    )


if __name__ == "__main__":
    from clean import get_clean_tickets, attendance_only
    from lot_anomaly import sku_anomaly_scan

    tickets, agents, orders, customers, products = get_clean_tickets()
    att = attendance_only(tickets)
    scan = sku_anomaly_scan(att, products)
    flagged = scan[scan["flagged"]]["product_name"].tolist()

    if not flagged:
        print("No SKU flagged by lot_anomaly.py — nothing to summarize.")
    elif os.environ.get("ANTHROPIC_API_KEY") is None:
        print("ANTHROPIC_API_KEY not set — skipping AI-assist step "
              "(Modules A and B do not depend on this).")
    else:
        for name in flagged:
            result = summarize_flagged_tickets(att, products, name)
            if result is not None:
                print(f"\nDominant failure modes for {name}:")
                print(dominant_failure_mode(result).head(10).to_string(index=False))
