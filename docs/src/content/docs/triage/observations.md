---
title: "Run observations"
draft: true
---
Record the following information for each tool and repository you review.
Use it to compare runs within your team and decide what to investigate next.

One pilot repository and a few hours of triage per tool provide only a small,
selected sample. Record counts, costs and time without treating them as
reliable estimates of a tool's overall accuracy. A rigorous evaluation method
is outside this playbook's scope.

## Record one row per run

| Field | What to record |
|---|---|
| Repository | An internal identifier, languages, approximate lines of code, application type and age. |
| Tool / harness / model | Tool and harness versions, exact model, provider, relevant settings and run date. |
| Findings reported | count after the tool's own dedup, by tool-reported severity |
| Triaged | how many findings you got through, in how many minutes total |
| Rough split | `TP` / `FP` / `needs-investigation` / `duplicate` counts of the *triaged* set (per the [triage rubric](/triage/triage-rubric/)) |
| API cost & runtime | from the tool's own usage reporting where available; otherwise a billing delta, and say so |
| Refusals / interventions | Count and trigger, which model or control intervened, and what happened next. Record “none observed” if applicable. |
| Blind spots | one line: what the tool clearly missed, if you know |

Keep the run table and detailed findings in your team's records. Sharing
outside the organisation is optional and subject to its disclosure rules.
If you share a summary, remove repository names, source code, credentials
and details of unfixed vulnerabilities. Review whether the remaining
description could still identify a sensitive project.

## Record time for each validated finding

Record time spent validating or reproducing the finding, drafting the fix,
and reviewing and merging it. Note whether a person or an agent drafted the
fix. Report each finding separately; use a range when the time is estimated.

## What we deliberately don't compute

- **True-positive rates.** Triage is time-capped and severity-ordered, so the
  triaged set is not a representative sample of the tool's output. Report
  the true-positive and false-positive counts with the number triaged and
  the total number of findings.
- **Severity accuracy.** The rubric uses tool-reported severity to order
  triage and does not assign an independent severity rating.
- **Cost per accepted fix.** One or two fixes cannot establish a typical
  cost. Report cost per review and human time separately.

If your organisation wants these numbers for itself, the rubric and the run
table are the starting point.
