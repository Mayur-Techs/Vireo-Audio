"""
defect_summarizer.py — optional AI-assist step.

Scope, deliberately narrow: only summarizes free text for tickets on SKUs
that lot_anomaly.py already flagged as statistically anomalous — a few
hundred tickets, not the full 11,750-row history. This is a direct response
to Arjun Mehta's email ruling out per-ticket model calls at scale across the
full ticket volume.

Supports two AI providers (checked in order):
  1. Groq   — set GROQ_API_KEY in environment (or in a .env file, which is
               .gitignore'd and never committed).
  2. Anthropic — set ANTHROPIC_API_KEY as a fallback.

If neither key is set, this step is skipped automatically and the report
notes that it was skipped. Modules A and B run fine with zero dependency
on this file.

Cost, for the record (see README): batching 20 tickets per call against a
cheap/fast model runs to a few hundred rupees a month at worst, even at
Vireo's full support volume — nowhere near the Rs-5-per-ticket figure Arjun's
email explicitly vetoed.
"""
import os
import json
import pandas as pd

BATCH_SIZE = 20

# Groq model — llama3 is fast and has a free tier
GROQ_MODEL = "llama3-8b-8192"

# Anthropic model — haiku is the cheapest Claude model
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"


def _load_dotenv():
    """Load a .env file from the project root if present (never required)."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_path = os.path.normpath(env_path)
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def _groq_client():
    """Returns a Groq client if groq is installed and GROQ_API_KEY is set."""
    _load_dotenv()
    try:
        from groq import Groq  # type: ignore
    except ImportError:
        return None
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    return ("groq", Groq(api_key=key))


def _anthropic_client():
    """Returns an Anthropic client if anthropic is installed and ANTHROPIC_API_KEY is set."""
    _load_dotenv()
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    return ("anthropic", anthropic.Anthropic(api_key=key))


def _get_client():
    """Returns the first available (provider, client) pair, or None."""
    return _groq_client() or _anthropic_client()


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


def _call_api(provider: str, client, prompt: str) -> str:
    """Unified call that works for both Groq and Anthropic."""
    if provider == "groq":
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return resp.choices[0].message.content or ""
    elif provider == "anthropic":
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return ""


def summarize_flagged_tickets(clean_tickets: pd.DataFrame, products: pd.DataFrame,
                               flagged_product_name: str) -> "pd.DataFrame | None":
    provider_client = _get_client()
    if provider_client is None:
        return None

    provider, client = provider_client
    print(f"  (AI-assist: using {provider})")

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
        try:
            text = _call_api(provider, client, prompt)
            parsed = json.loads(text.strip().strip("`"))
        except Exception:
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
    return pd.DataFrame(results)


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
    elif _get_client() is None:
        print(
            "No AI key found — set GROQ_API_KEY or ANTHROPIC_API_KEY (or put them in a .env file).\n"
            "Modules A and B do not depend on this step."
        )
    else:
        for name in flagged:
            result = summarize_flagged_tickets(att, products, name)
            if result is not None:
                print(f"\nDominant failure modes for {name}:")
                print(dominant_failure_mode(result).head(10).to_string(index=False))
