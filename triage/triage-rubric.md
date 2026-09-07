# Triage Rubric

How participants triage the findings from a discovery tool.
**Status: draft — to be agreed in session 2.** Purpose: find the 2–3 findings
worth proving in session 3, and put a number on what manual triage costs. It
is deliberately *not* a grading scheme for computing rates — see
[observations.md](observations.md) for what is and isn't collected.

**Budget:** ≤ 10 minutes per finding, **~3 hours per tool in total**. Go
highest tool-reported severity first; stop at the cap or once you have your
candidates and a feel for the noise, whichever comes first. If a finding can't
be decided in 10 minutes, mark it *needs-investigation* and move on.

## Per-finding fields

| Field | Values | Notes |
|---|---|---|
| Finding ID | tool's ID or hash | stable reference for the full-loop exercise |
| Tool / version | free text | include model/backend used |
| Verdict | `TP` / `FP` / `needs-investigation` / `duplicate` | see decision rules below |
| Tool severity | as reported | used for ordering only — no re-rating |
| Exploitability | `reachable` / `needs-preconditions` / `theoretical` | TPs only, one line of reasoning — this is what picks the loop candidates |
| Triage time | minutes | feeds the human-cost picture |
| Notes | free text | anything the cross-org comparison should know |

## Decision rules

- **TP** — the flaw exists in the code as described and is a security issue
  in this codebase's context (not necessarily exploitable today).
- **FP** — the described flaw is not present, or the "vulnerable" path cannot
  be reached by any input/config the codebase admits.
- **needs-investigation** — plausible but not decidable within the time box.
  Not a failure verdict; the rate of these is itself a usability signal.
- **duplicate** — same root cause and location as an already-triaged finding
  (including across tools, when triaging the second tool).
- Code-quality findings with no security relevance are **FP** for our
  purposes — note "quality-only" in Notes so they're distinguishable from
  hallucinations.

## Procedure

1. Export the tool's findings (one row each).
2. Triage in the tool's reported-severity order, highest first, until the cap.
3. Triage solo; findings that stay *needs-investigation* are candidates for
   group discussion in the next session.
4. Record for the run table: findings triaged / findings total, total
   minutes, the rough verdict split, and your 2–3 "would most want proven"
   candidates.
