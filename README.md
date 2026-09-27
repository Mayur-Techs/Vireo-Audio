# Vireo Audio — CX Signal Tool

**What it does:** Answers two questions from the same support-ticket data:
1. **(Requested)** Who are the fair candidates for the Q3 training budget? — Agent scorecard with CSAT and handle time per agent, plus a corrected bottom-10 list that respects the Tier 1 / Tier 2 policy split.
2. **(Additional finding)** What is actually driving the CSAT slide? — A generic SKU anomaly detector that independently flagged Pulse 2 True Wireless Earbuds with a 3.6× replacement-rate rise concentrated in specific manufacturing lots.

---

## How to run it

```
pip install -r requirements.txt
python run.py
```

Put `tickets.csv`, `agents.csv`, `orders.csv`, `customers.csv`, `products.csv` in `data/` first
(already there if you cloned this with the sample data).

Output: `outputs/report.html` — opens in any browser, no server needed.

**No API key required for the core run.** The report is fully reproducible with zero paid model calls.

---

## Key metric definitions

| Metric | Definition |
|---|---|
| `csat_avg` | Mean of non-blank `csat_score` values only. Blank = no response (policy §8), never treated as 0. |
| `csat_responses` | Count of non-blank CSAT scores for the agent. Agents with <10 responses are excluded from ranking (too few to be meaningful). |
| `handle_time_avg_h` | Mean hours from `first_response_at` to `resolved_at`. Only computed on resolved/closed tickets (`attendance_only`). |
| `resolution_days_avg` | Tier 2 only: mean handle time converted to days (policy §6 says Tier 2 is measured in days, not hours). |
| Replacement rate | Fraction of tickets for a SKU where `replacement_issued == "Y"`. |
| Baseline / Current | First half / second half of the 18-month date range in the data. |

---

## Why legacy timestamps are corrected

`legacy_fd` tickets had their `resolved_at` reconstructed from a UTC event log (policy §9) while
`created_at` and `first_response_at` were stored as IST as displayed. Without correction, 2,309 of
3,374 legacy rows have negative handle times (resolved before first response — impossible).

**Fix:** add 5:30 to `legacy_fd.resolved_at`. After the fix, zero rows have negative handle time and
the corrected median lines up with the native-helpdesk median.

This count is computed dynamically at runtime from the raw CSV — it is never hardcoded.

---

## Why `agent_id` is used for all joins, never `name`

The agent roster contains two people both named **"Kavya Pandey"** — agent A3006 (Chat Frontline,
Bangalore) and agent A3029 (Logistics, Hyderabad). A join on `name` would merge their records.
All joins use `agent_id` exclusively to avoid this.

---

## Why Tier 2 is reported separately

Policy §6 says Escalations & Warranty agents should be measured on **resolution time in days**,
not tickets closed per week. Their cases are multi-touch hardware/warranty escalations that take
5–6 days on average by design. A naive combined CSAT ranking puts 6 of the "worst" 10 agents in
Tier 2 — that reflects the queue type, not individual agent performance.

The report shows:
- **Naive bottom 10** — for transparency, to show the confound.
- **Tier-1-only bottom 10** — the recommended target for the training budget.
- **Tier 2 summary** — separate table on resolution days, not ranked against Tier 1.

---

## What the anomaly detector does

`src/lot_anomaly.py` runs a generic rule against **all** SKUs — it does not hardcode "Pulse 2":

1. Splits the data at the midpoint of the date range.
2. Computes `replacement_issued == "Y"` rate in each half.
3. Flags any SKU where: current rate ≥ 2× baseline rate **and** both halves have ≥ 50 tickets.

On this dataset it independently flags exactly one SKU: **Pulse 2 True Wireless Earbuds**
(7.6% baseline → 27.5% current). For the flagged SKU, replacement tickets are joined to
manufacturing `lot_code` via `order_id`, with a fallback join on `customer_id + product_sku` for
tickets without a direct order reference.

The excess-cost figure is a **run-rate estimate**, not a guaranteed saving. It assumes the
current-half rate elevation continues, and does not prove a manufacturing defect as the cause.

---

## AI usage and cost disclosure

| Item | Detail |
|---|---|
| **Core run cost** | **Rs 0 paid model cost.** All analytics (scorecard, anomaly scan, lot breakdown) use pandas only. |
| Optional AI step (Groq) | `src/defect_summarizer.py` uses Groq (`GROQ_API_KEY`) if available — checked first. |
| Optional AI step (Anthropic) | Falls back to `ANTHROPIC_API_KEY` if Groq key is not set. |
| AI accuracy claim | None. The AI step was not invoked in the final submission, and no accuracy number is claimed. |
| Key safety | API keys go in a `.env` file (project root) which is in `.gitignore` and **never committed**. |

### To enable the optional AI step with Groq (recommended):

1. Create a `.env` file in the project root (already in `.gitignore` — safe to create):
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
2. Install the Groq library:
   ```
   pip install groq>=0.9
   ```
3. Run as normal:
   ```
   python run.py
   ```
   The step will activate automatically when it detects the key.

### To use Anthropic Claude instead:

```
# In .env:
ANTHROPIC_API_KEY=sk-ant-your_key_here
```
```
pip install anthropic>=0.40
python run.py
```


---

## Known limitations (stated, not hidden)

- **Informal hardware triage rota:** Neha's email references "Kavya's four plus the warranty team."
  This informal grouping does not map onto any roster column. The tool uses the documented
  `tier`/`team` split instead.
- **IVR junk tickets:** The ~40 "junk IVR" tickets are a narrower set than a literal
  `[IVR transcript]` text match (which hits many legible rows). Isolating the true unusable subset
  needs a text-quality heuristic not yet built here.
- **Lot join:** 1 of 1,101 replacement tickets on the flagged SKU cannot be resolved to a lot code
  even with the `customer_id + SKU` fallback. Reported, not silently dropped.
- **CSAT response rate:** ~56% of tickets have no CSAT response. Averages are computed on responders
  only (policy §8). Low-response agents are excluded from ranking.

---

## File structure

```
vireo_cx_tool/
├── README.md
├── run.py                  # entry point
├── requirements.txt
├── verify.py               # one-off verification script (optional)
├── data/
│   ├── tickets.csv
│   ├── agents.csv
│   ├── orders.csv
│   ├── customers.csv
│   └── products.csv
├── src/
│   ├── clean.py            # data-quality fixes
│   ├── agent_scorecard.py  # Module A: agent ranking
│   ├── lot_anomaly.py      # Module B: SKU anomaly detection
│   ├── defect_summarizer.py # optional AI step (requires API key)
│   └── report.py           # HTML report assembly
└── outputs/
    └── report.html         # generated output (open in browser)
```
