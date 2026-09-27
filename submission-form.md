# Vireo Audio — CX Assessment Submission Form

**Submitted by:** [Your Name]
**Date:** September 2026
**Project:** Vireo Audio CX Signal Tool

---

## Q1. What is the CSAT per agent?

The full Tier-1 agent scorecard is in `outputs/tier1_scorecard_full.csv` and displayed in Section 2
of `outputs/report.html`.

Key figures from the final run (11,750 tickets; 11,183 resolved/closed):

- CSAT averages are computed on **non-blank responses only** (policy §8; ~56% of tickets have no
  CSAT response — blanks are "no response," never treated as 0).
- Agents with fewer than 10 CSAT responses are excluded from ranking (too few to be meaningful).
- Bottom performer (Tier 1): **A3004 — Siddharth Kapoor**, CSAT avg 2.96 (122 responses).

---

## Q2. What is the handle time per agent?

Handle time = hours from `first_response_at` to `resolved_at`, computed on resolved/closed tickets
only.

- Legacy `legacy_fd` timestamps were corrected by +5:30 (UTC→IST) before computing handle time.
  This eliminated **2,309** impossible negative handle-time rows (verified dynamically at runtime).
- Handle time per agent is in the `handle_time_avg_h` column of `outputs/tier1_scorecard_full.csv`
  and shown in the Tier-1 bottom-10 table in Section 2 of the report.

---

## Q3. Who are the bottom ten flagged agents?

**Important caveat communicated to client:** A naive combined ranking puts **6 of 10** "worst"
agents in the Tier 2 Escalations & Warranty team. Policy §6 says Tier 2 should not be compared
with Tier 1 on volume/CSAT metrics. Showing that list as-is would misdirect the training budget.

The report therefore provides **two** bottom-10 lists:

1. **Naive bottom 10** (all tiers combined) — shown for transparency so the client can see the
   confound themselves.
2. **Fair Tier-1-only bottom 10** — the recommended list for the Q3 training budget:

| Rank | Agent ID | Agent Name | Team | CSAT avg |
|---|---|---|---|---|
| 1 | A3004 | Siddharth Kapoor | Chat Frontline | 2.96 |
| 2 | A3005 | Zaid Khanna | Chat Frontline | 3.00 |
| 3 | A3007 | Siddharth Trivedi | Chat Frontline | 3.01 |
| 4 | A3006 | Kavya Pandey | Chat Frontline | 3.03 |
| 5 | A3029 | Kavya Pandey | Logistics | 3.11 |
| 6 | A3028 | Vivaan Pandey | Logistics | 3.12 |
| 7 | A3030 | Geeta Iyer | Logistics | 3.18 |
| 8 | A3038 | Varun Reddy | Returns Desk | 3.19 |
| 9 | A3036 | Divya Tiwari | Returns Desk | 3.28 |
| 10 | A3037 | Mohammed Desai | Returns Desk | 3.29 |

---

## Q4. What is the business outcome as a number + money?

**Flagged SKU:** Pulse 2 True Wireless Earbuds (independently flagged by generic anomaly rule —
not hardcoded).

| Metric | Value |
|---|---|
| Baseline replacement rate (first half of data) | 7.6% (n = 288 tickets) |
| Current replacement rate (second half of data) | 27.5% (n = 3,918 tickets) |
| Excess replacements vs. baseline expectation | 780 |
| True unit replacement cost (unit cost + Rs 340 logistics per policy §5) | Rs 1,820 |
| **Potential excess cost, this analysis window** | **Rs 14,19,069** |
| **Potential quarterly run-rate** | **Rs 4,74,762** |

This run-rate exceeds the Rs 4,00,000 Q3 training budget under discussion.

> **Honest caveat:** "Potential" is used deliberately. This is a run-rate estimate assuming the
> current-half rate continues. It does not prove a manufacturing defect as the sole cause. It is
> a signal warranting investigation, not a guaranteed saving.

Lot-code concentration: the top 8 lots (all PL2-2510-x and PL2-2511-x) account for the majority
of replacement tickets. 1,100 of 1,101 replacement tickets resolved to a lot code (1 unresolved
after customer_id + SKU fallback join).

---

## Q5. Evidence that the tool works

- `outputs/report.html` — generated output, opens in any browser.
- `report_sample.html` — reference sample from an earlier run showing matching numbers.
- `verify.py` — reproducible verification script; run `python verify.py` to re-check all core
  numbers against the raw data.
- The tool runs to completion with `python run.py` from a clean install with no API key.
  Zero crashes observed on the final run.

---

## Q6. One-page memo to Priya

See `memo.md` in the project root.

---

## Q7. Screen recording

[Attach screen recording separately — shows `python run.py` completing and `outputs/report.html`
opening in a browser, with all sections visible.]

---

## Q8. Completed submission form

This document.

---

## Q9. Honest AI / cost disclosure

| Item | Detail |
|---|---|
| **Core run cost** | **Rs 0 paid model cost.** All analytics use pandas only. No API call is made during a standard run. |
| Optional AI step (Groq) | `src/defect_summarizer.py` supports Groq (`GROQ_API_KEY`) to classify failure modes on flagged-SKU tickets. Skipped by default if key is not set. |
| Optional AI step (Anthropic) | Same file also supports `ANTHROPIC_API_KEY` as an alternative. Also skipped if key not set. |
| AI accuracy claim | **None.** The AI step was not invoked in the final submission. No accuracy number is claimed. |
| Key protection | `.env` and all `*_API_KEY` environment variables are in `.gitignore` and are never committed to the repository. |
