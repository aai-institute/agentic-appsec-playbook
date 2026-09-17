---
title: "Validation Loop — Record Template"
---
One record per finding wired through the loop. The filled template is the
organisation's own; the anonymized version (repo descriptor only, no code, no
details of unfixed findings — see
[Sharing results across organisations](/#sharing-results-across-organisations))
is what goes into a cross-organisation loop table.

The loop: **hypothesis → evidence plan → validation → decision → fix
candidate → regression test → human-gated merge.** Every arrow is a place
the agent can be wrong, so every arrow has a field.

## 1. Finding

| Field | Value |
|---|---|
| Finding ID | (from the triage rubric; tool / version / model backend) |
| CWE class + tool severity | |
| Exploitability from triage | `reachable` / `needs-preconditions` |
| Repo descriptor | language(s), kLOC bucket, domain (no name) |

## 2. Hypothesis (write before touching a tool)

- **Claim:** the flaw is … at … and is reachable when … with impact …
- **Confirming evidence would be:** (a test that fails, a request that
  returns X, a reachability path from entry point Y)
- **Refuting evidence would be:** (the path is unreachable because …; input
  is validated at …; the config never admits …)

## 3. Validation design

Pick one. The default is A; B and C are for findings that genuinely need a
proof-of-vulnerability a model has to write.

| | A — deterministic | B — open-weight PoV | C — CVP |
|---|---|---|---|
| Who writes the proof | you (agent may help with the *test*) | tier-B model (GLM-5.3 / DeepSeek V4 Pro) in OpenCode | Opus/Sonnet-class with reduced safeguards |
| What it proves | the path is exercisable and the behaviour is wrong | the flaw is exploitable as the model demonstrates | same as B, frontier-adjacent quality |
| What it can't prove | exploitability in production conditions | anything the model didn't manage — absence of a PoV is not refutation | same; and not available to ZDR orgs |
| Sandbox demands | none beyond the baseline | reproducer runs in `runsc`, **no network**; running target only on the internal bridge | same as B |
| Refusal exposure | none | none (no safeguard layer — note that) | reduced safeguards; log any refusal |
| Cost | your time | model tokens + your time | application (~2 business days) + tokens + your time |

Design chosen: ☐ A ☐ B ☐ C — because: …

## 4. Validation outcome

| Field | Value |
|---|---|
| Outcome | `confirmed` / `refuted` / `cannot-reproduce` |
| Evidence (one line, no code) | |
| Validation time (min) | |
| Refusals / redirects encountered | model, what triggered it, what the fallback did — or "none" |

*Cannot-reproduce* is a valid outcome and ends the loop for this finding.
Do not keep pushing the agent until something "works" — an agent given an
unachievable objective probes its environment instead (the 2026 incidents'
central mechanism).

## 5. Fix candidate

| Field | Value |
|---|---|
| Drafted by | `agentic` (harness + model) / `manual` / `agentic, heavily edited` |
| Regression test | fails before, passes after — ☐ yes ☐ no (why) |
| Existing tests + SAST | ☐ pass ☐ fail (what) |
| Failure modes checked | ☐ scope creep ☐ test gaming ☐ hallucinated API / dependency ☐ weakened validation elsewhere |
| Fix drafting time (min) | |

## 6. Review and merge

| Field | Value |
|---|---|
| Reviewer independent of the agent driver | ☐ yes ☐ no |
| Reviewer changes | none / minor / substantial (what kind) |
| Result | `merged` / `approved, not merged (why)` / `rejected (why)` |
| Review & merge time (min) | |
| "Would you have merged without the regression test?" | |

## 7. Time-to-valid-fix

validation ___ min + fix ___ min + review ___ min = ___ min
(triage time for this finding, from the rubric: ___ min — the baseline)

## 8. Qualitative

- Where the agent helped:
- Where it wasted time or misled:
- **Sandbox friction:** what the baseline blocked that you needed, and the
  workaround (egress, running target, container-in-VM, …)
- Would you run this loop in CI? Under what conditions?

## What "valid fix" means here

A fix counts as valid when a regression test exercises the vulnerable path
and fails before / passes after, the existing suite still passes, and a
human who did not drive the agent approved it. Passing tests alone is not
enough: agentic patches that pass tests can still introduce or hide
vulnerabilities, and iterative self-repair can make things worse (arXiv
2507.02976; arXiv 2509.25894). The human gate is not
ceremony; it is the control.
