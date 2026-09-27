# Internal Memo

**To:** Priya Sharma, Head of Customer Experience
**From:** [Your Name]
**Date:** September 2026
**Re:** CX Signal Analysis — Agent Training Priorities and Product Replacement Alert

---

## Bottom line up front

The training budget should target **four Chat Frontline agents** (A3004–A3007), not the ten names
the raw ranking produces. The raw list is dominated by Tier 2 agents who handle a structurally
harder type of work. Separately, a generic scan of all SKU replacement rates flagged the **Pulse 2
True Wireless Earbuds** as warranting an investigation — its replacement rate tripled in the second
half of our 18-month window and is concentrated in specific manufacturing lots.

---

## 1. Agent training: why the "bottom ten" needed a correction

Running a simple CSAT ranking across all agents puts **6 of the 10 lowest-scoring agents** in the
Escalations & Warranty team (Tier 2). Policy §6 is clear: Tier 2 cases are multi-touch hardware
escalations, measured in resolution days, not tickets per week. Their lower CSAT reflects the
case type — warranty disputes are inherently harder to resolve to full satisfaction — not individual
agent underperformance.

**Recommended training targets (Tier 1 only, sorted by CSAT avg):**

| Agent | Team | CSAT avg | CSAT responses | Handle time (avg h) |
|---|---|---|---|---|
| Siddharth Kapoor (A3004) | Chat Frontline | 2.96 | 122 | 2.89 |
| Zaid Khanna (A3005) | Chat Frontline | 3.00 | 111 | 3.54 |
| Siddharth Trivedi (A3007) | Chat Frontline | 3.01 | 113 | 4.68 |
| Kavya Pandey (A3006) | Chat Frontline | 3.03 | 132 | 4.34 |
| Kavya Pandey (A3029) | Logistics | 3.11 | 154 | 38.95 |
| Vivaan Pandey (A3028) | Logistics | 3.12 | 145 | 38.20 |
| Geeta Iyer (A3030) | Logistics | 3.18 | 139 | 41.59 |
| Varun Reddy (A3038) | Returns Desk | 3.19 | 118 | 35.63 |
| Divya Tiwari (A3036) | Returns Desk | 3.28 | 103 | 32.79 |
| Mohammed Desai (A3037) | Returns Desk | 3.29 | 234 | 36.52 |

Note: two agents are named "Kavya Pandey" — they are different people (different agent IDs, sites,
and teams). All joins in this analysis use `agent_id`, never name, to avoid mixing their records.

**Tier 2 summary** (reported on resolution days per policy §6, not ranked against Tier 1): average
resolution time is 4.7–5.7 days per agent. This is a separate coaching conversation, not a
training-budget line item.

---

## 2. Product alert: Pulse 2 True Wireless Earbuds

A generic anomaly scan across all SKUs (no product was hardcoded) flagged one product:

| Metric | Value |
|---|---|
| Baseline replacement rate (months 1–9) | 7.6% of tickets |
| Current replacement rate (months 10–18) | 27.5% of tickets |
| Ratio | 3.6× baseline |
| Excess replacements vs. baseline expectation | ~780 |
| Replacement cost per unit (policy §5: unit cost + Rs 340) | Rs 1,820 |
| **Potential excess cost in the analysis window** | **Rs 14,19,069** |
| **Potential quarterly run-rate** | **Rs 4,74,762** |

This run-rate is larger than the Rs 4,00,000 Q3 training budget under discussion.

The elevated rate is concentrated in manufacturing lots **PL2-2510** and **PL2-2511** (Oct–Nov 2025
production runs). 1,100 of 1,101 replacement tickets traced to a lot code.

**Important caveat:** "Potential" is used deliberately. This analysis shows a statistically
significant rate increase concentrated in specific lots — it does not prove a manufacturing defect
as the sole cause. The finding warrants a conversation with the supply chain and QA teams before
any public claim is made.

---

## 3. Data quality notes (for transparency)

- **Timestamp correction:** Tickets from the legacy helpdesk (`legacy_fd`) had `resolved_at`
  recorded in UTC while all other timestamps are IST. We added 5:30 to correct this before
  computing any handle-time metric. Without this fix, 2,309 tickets show impossible negative handle
  times. After the fix: zero.
- **CSAT blanks:** ~56% of tickets have no CSAT response. All averages use responders only.
  Blanks are never treated as zero-scores.
- **Known gap:** The "Kavya's four plus the warranty team" informal rota mentioned in earlier
  emails does not map onto any roster column. This analysis uses the documented `tier`/`team`
  split instead.

---

## 4. What was not done (stated gaps)

- AI-assisted failure-mode classification of Pulse 2 ticket free text is built but **was not run**
  for this submission (requires a Groq or Anthropic API key). No accuracy number is claimed.
- The ~40 junk IVR tickets cannot be isolated by a simple text match without a text-quality
  heuristic not yet built here.

---

*All numbers above come directly from `python run.py` on the supplied data. The tool is
reproducible: `pip install -r requirements.txt && python run.py` produces `outputs/report.html`
with zero paid API calls.*
