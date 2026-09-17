---
title: "Validation Loop — Record Template"
draft: true
---
Create one record for each finding you validate. Keep the completed template
in your team's records. If you choose to share a summary outside your
organisation, follow its disclosure rules and remove code, project
identifiers and details of unfixed vulnerabilities.

The loop: **hypothesis → evidence plan → validation → decision → fix
candidate → regression test → human-gated merge.** Every arrow is a place
the agent can be wrong, so every arrow has a field.

## 1. Finding

| Field | Value |
|---|---|
| Finding ID | (from the triage rubric; tool / version / model backend) |
| CWE class + tool severity | |
| Exploitability from triage | `reachable` / `needs-preconditions` |
| Repository | internal identifier, languages, approximate lines of code and application type |

## 2. Hypothesis (write before touching a tool)

- **Claim:** the flaw is … at … and is reachable when … with impact …
- **Confirming evidence would be:** (a test that fails, a request that
  returns X, a reachability path from entry point Y)
- **Refuting evidence would be:** (the path is unreachable because …; input
  is validated at …; the config never admits …)

## 3. Validation design

Choose how to test the claim. Start with the smallest test that can confirm
or refute it. Record the model and provider if an agent helps write the test;
use an approved route from [Choosing a model](/tools/choosing-a-model/).

| Method | Who prepares the test | What to check |
|---|---|---|
| Human-written test | You write a test or trace the relevant code path. | Show the input, preconditions and result that support or refute the claim. |
| Agent-assisted test | The agent drafts a test or reproducer; you inspect it before execution. | Check that it exercises the reported flaw and that its assertions support the conclusion. Record refusals or changes of approach. |

Method chosen: … — because: …

A reproducer demonstrates behavior under the tested conditions. It does not
establish exploitability in production. Failure to produce a working test
also does not refute the finding.

Run tests that execute project code or generated code in a
[separate reproducer VM](/sandbox/sbx/lifetime/#reproducers-reset-and-destroy).
It has no model credential and a network policy that denies external
destinations. Complete the network checks before execution. Use synthetic
data and local test doubles for services such as email, payments or databases.

If validation needs a running application, keep it inside that VM, with no
published ports or connections to production services. The wrapper provides
no automatic application setup or container access for the workload. If the
test needs capabilities this setup cannot provide, record the limitation and
assess a separate setup before proceeding. Access to an existing staging
environment remains a [future extension](/sandbox/threat-model/acceptance/#staging-access-a-future-extension).

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
- **Sandbox friction:** which required capability was unavailable and whether
  you changed the test, stopped, or used a separately assessed setup.
- Would you run this loop in CI? Under what conditions?

## What "valid fix" means here

A fix counts as valid when a regression test exercises the vulnerable path
and fails before / passes after, the existing suite still passes, and a
human who did not drive the agent approved it. Passing tests alone is not
enough: agentic patches that pass tests can still introduce or hide
vulnerabilities, and iterative self-repair can make things worse (arXiv
2507.02976; arXiv 2509.25894). The human gate is not
ceremony; it is the control.
