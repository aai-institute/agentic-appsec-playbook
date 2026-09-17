---
title: "Shared Observations"
---
What to record per (tool, repo) run so results can be compared across
organisations.

With one pilot repository per organisation and a triage cap of a few hours
per tool, the sample cannot support rates. Collect estimates and report them
as ranges. A rigorous evaluation method is outside this playbook's scope.

## Per (tool, repo) run — one line in the shared run table

| Field | What to record |
|---|---|
| Repo descriptor | Language(s), kLOC bucket, domain and age bucket; omit the repo name. |
| Tool / harness / model tier | incl. tool version and model backend; run date |
| Findings reported | count after the tool's own dedup, by tool-reported severity |
| Triaged | how many findings you got through, in how many minutes total |
| Rough split | `TP` / `FP` / `needs-investigation` / `duplicate` counts of the *triaged* set (per the [triage rubric](/triage/triage-rubric/)) |
| API cost & runtime | from the tool's own usage reporting where available; otherwise a billing delta, and say so |
| Refusals / interventions | count and trigger (tier A); note the absence and any quality consequence (tier B) |
| Blind spots | one line: what the tool clearly missed, if you know |

Per-finding data stays in the org's own copy; only the run-table line is
shared cross-org.

## Per finding wired through the loop

Time-to-valid-fix, logged as three components: validation/reproduction, fix
drafting (agentic or manual — record which), review & merge. Too few data
points anywhere for averages; report them per finding, as a range.

## What we deliberately don't compute

- **True-positive rates.** Triage is time-capped and severity-ordered, so the
  triaged set is not a sample of the tool's output. The TP/FP split is a
  signal-to-noise impression, and is reported as such.
- **Severity accuracy.** Grader severity was dropped from the rubric; tool
  severity is used for ordering only.
- **Cost per accepted fix.** One or two accepted fixes per org is not a
  denominator. Cost per *pass* and human time are reported separately — orgs
  value time differently.

If your organisation wants these numbers for itself, the rubric and the run
table are the starting point.
