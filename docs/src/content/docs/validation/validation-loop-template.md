---
title: "Validation loop record"
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

Method chosen: … because: …

A reproducer demonstrates behavior under the tested conditions. It does not
establish exploitability in production. Failure to produce a working test
also does not refute the finding.

Run tests that execute project code or generated code yourself, in the review
VM, and read the result there. An agent's report of its own run is not
evidence. Install the target's dependencies from its lockfile. Use synthetic
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
| Refusals / redirects encountered | model, what triggered it, what the fallback did, or "none" |

*Cannot-reproduce* is a valid outcome and ends the loop for this finding.
Do not keep pushing the agent until something "works". An agent given an
unachievable objective starts probing its environment instead.

## 5. Fix candidate

| Field | Value |
|---|---|
| Outcome | `fixed` / `no change needed` (why the code is already safe) / `blocked` (which evidence or decision is missing) |
| Drafted by | `agentic` (harness + model) / `manual` / `agentic, heavily edited` |
| Regression test | fails before, passes after: ☐ yes ☐ no (why) |
| Existing tests + SAST | ☐ pass ☐ fail (what) |
| Verification that actually ran | `tests executed by you` / `tests executed by the agent or tool only` / `static review only` / `nothing` |
| Failure modes checked | ☐ scope creep ☐ test gaming ☐ hallucinated API / dependency ☐ weakened validation elsewhere |
| Fix drafting time (min) | |

## 6. Review and merge

| Field | Value |
|---|---|
| Reviewer independent of the agent driver | ☐ yes ☐ no |
| What the reviewer saw | ☐ claim ☐ diff ☐ test results ☐ the agent's transcript or rationale |
| Reviewer's risk call | impact if wrong / regression likelihood / regression protection / recoverability: one word each |
| Reviewer changes | none / minor / substantial (what kind) |
| Result | `merged` / `approved, not merged (why)` / `rejected (why)` |
| Review & merge time (min) | |
| "Would you have merged without the regression test?" | |

## 7. Time-to-valid-fix

validation ___ min + fix ___ min + review ___ min = ___ min
(triage time for this finding, from the rubric, as the baseline: ___ min)

## 8. Qualitative

- Where the agent helped:
- Where it wasted time or misled:
- **Sandbox friction:** which required capability was unavailable and whether
  you changed the test, stopped, or used a separately assessed setup.
- Would you run this loop in CI? Under what conditions?

## 9. After the fix (optional)

| Field | Value |
|---|---|
| Root cause | the rule the code failed to enforce, and why nothing forced it |
| Variant search | where else the same rule could break; what you searched and what you found |
| Guardrail | what now keeps the class out: a design change, a rule or a test; it fails on the vulnerable revision and passes on the fixed one |

A fix closes one path. Variants of patched bugs are common, often because
the fix blocked the reported path and left the cause in place. Searching by
the broken rule finds more than searching for code that looks like the fix.
An agent can help with the search and with drafting the guardrail, but every
reported variant and every guardrail needs the same proof as the fix.
Agents have the weakest record on authorisation rules.

## What "valid fix" means here

A fix counts as valid when a regression test exercises the vulnerable path
and fails before / passes after, the existing suite still passes, and a
human who did not drive the agent approved it. Passing tests alone is not
enough: agentic patches that pass tests can still introduce or hide
vulnerabilities, and iterative self-repair can make things worse (arXiv
2507.02976; arXiv 2509.25894). A tool's own "verified" label names the
process it ran, which may be a sandboxed test run or a second static read;
the verification row records which. A reviewer who sees only the claim and
the diff, without the agent's reasoning, is harder to talk into approving a
bad fix. Tests lower the likelihood of a regression, never its impact. The human gate is not
ceremony; it is the control. [Exercise 3](/exercises/fix-a-finding/) walks
sections 5 to 9 on one finding.
