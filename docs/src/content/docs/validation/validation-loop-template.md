---
title: "Validation loop record"
---
Create one record for each finding you validate. Keep the completed template
in your team's records.

The loop: **hypothesis → evidence plan → validation → decision → fix
candidate → regression test → human-gated merge.** Every arrow is a place
the agent can be wrong, so every arrow has a field.

○ marks a single choice, ☐ a field where several can apply.

| Sections | Stage | Filled in |
|---|---|---|
| 1 to 4 | Finding, hypothesis, validation | [Exercise 2](/exercises/validate-a-finding/) |
| 5 to 8 | Fix, review, time, lessons | [Exercise 3](/exercises/fix-a-finding/) |
| 9 | After the fix | Optional |

## 1. Finding

| Field | Values | Notes |
|---|---|---|
| Finding ID | from the [triage rubric](/triage/triage-rubric/) | tool, version and model backend |
| CWE class and tool severity | free text | |
| Exploitability from triage | <span class="value-chips"><span class="value-chip value-chip--reachable">reachable</span><span class="value-chip value-chip--preconditions">needs-preconditions</span></span> | |
| Repository | free text | internal identifier, languages, approximate lines of code and application type |

## 2. Hypothesis

Write it before touching a tool.

- **Claim:** the flaw is … at … and is reachable when … with impact …
- **Confirming evidence would be:** a test that fails, a request that
  returns X, a reachability path from entry point Y.
- **Refuting evidence would be:** the path is unreachable because …; input
  is validated at …; the config never admits …

## 3. Validation design

Choose how to test the claim. Start with the smallest test that can confirm
or refute it. Record the model and provider if an agent helps write the test;
use an approved route from [Choosing a model](/tools/choosing-a-model/).

| Method | Who prepares the test | What to check |
|---|---|---|
| Human-written test | You write a test or trace the relevant code path. | Show the input, preconditions and result that support or refute the claim. |
| Agent-assisted test | The agent drafts a test or reproducer; you inspect it before execution. | Check that it exercises the reported flaw and that its assertions support the conclusion. Record refusals or changes of approach. |

**Method chosen:** … **because:** …

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

| Field | Values | Notes |
|---|---|---|
| Outcome | <span class="value-chips"><span class="value-chip value-chip--confirmed">confirmed</span><span class="value-chip value-chip--refuted">refuted</span><span class="value-chip value-chip--cannot-reproduce">cannot-reproduce</span></span> | |
| Evidence | one line, no code | |
| Validation time | minutes | |
| Refusals and redirects | free text | model, what triggered it, what the fallback did, or "none" |

<span class="value-chip value-chip--cannot-reproduce">cannot-reproduce</span> is a valid outcome and ends the loop for this finding.
Do not keep pushing the agent until something "works". An agent given an
unachievable objective starts probing its environment instead.

## 5. Fix candidate

| Field | Values | Notes |
|---|---|---|
| Outcome | <span class="value-chips"><span class="value-chip value-chip--fixed">fixed</span><span class="value-chip value-chip--no-change">no change needed</span><span class="value-chip value-chip--blocked">blocked</span></span> | for no change needed, why the code is already safe; for blocked, which evidence or decision is missing |
| Drafted by | <span class="value-chips"><span class="value-chip value-chip--plain">agentic</span><span class="value-chip value-chip--plain">agentic, heavily edited</span><span class="value-chip value-chip--plain">manual</span></span> | for an agent, the harness and model |
| Regression test fails before, passes after | ○ yes<br>○ no | if not, why |
| Existing tests and SAST | ○ pass<br>○ fail | what failed |
| Verification that actually ran | <span class="value-chips"><span class="value-chip value-chip--ran-by-you">tests executed by you</span><span class="value-chip value-chip--ran-by-agent">tests executed by the agent or tool only</span><span class="value-chip value-chip--static-only">static review only</span><span class="value-chip value-chip--ran-nothing">nothing</span></span> | a tool's "verified" label names its process; record what ran |
| Failure modes checked | ☐ scope creep<br>☐ test gaming<br>☐ hallucinated API or dependency<br>☐ weakened validation elsewhere<br>☐ bypass | |
| Bypass attempt by | <span class="value-chips"><span class="value-chip value-chip--plain">you</span><span class="value-chip value-chip--plain">model</span></span> | for a model, the harness and model, and whether it is open-weight; what it tried |
| Bypass result | <span class="value-chips"><span class="value-chip value-chip--no-bypass">none found</span><span class="value-chip value-chip--bypass">bypass found</span></span> | for a bypass, what reached the flaw |
| Fix drafting time | minutes | |

## 6. Review and merge

| Field | Values | Notes |
|---|---|---|
| Reviewed by | <span class="value-chips"><span class="value-chip value-chip--plain">person</span><span class="value-chip value-chip--plain">model</span><span class="value-chip value-chip--plain">none</span></span> | for a model, the harness and model |
| Reviewer independent of the agent driver | ○ yes<br>○ no | |
| What the reviewer saw | ☐ claim<br>☐ diff<br>☐ test results<br>☐ the agent's transcript or rationale | |
| Reviewer's risk call | one word each | impact if wrong, regression likelihood, regression protection, recoverability |
| Reviewer changes | <span class="value-chips"><span class="value-chip value-chip--plain">none</span><span class="value-chip value-chip--plain">minor</span><span class="value-chip value-chip--plain">substantial</span></span> | for substantial, what kind |
| Result | <span class="value-chips"><span class="value-chip value-chip--merged">merged</span><span class="value-chip value-chip--merge-ready">merge-ready</span><span class="value-chip value-chip--rejected">rejected</span></span> | for merge-ready, why not merged; for rejected, why |
| Review and merge time | minutes | |
| Would you have merged without the regression test? | free text | |

## 7. Time-to-valid-fix

| Step | Minutes |
|---|---|
| Validation (section 4) | |
| Fix drafting (section 5) | |
| Review and merge (section 6) | |
| **Time-to-valid-fix** | sum of the three |
| Baseline: triage time for this finding, from the rubric | |

## 8. Qualitative

- **Where the agent helped:**
- **Where it wasted time or misled:**
- **Sandbox friction:** which required capability was unavailable and whether
  you changed the test, stopped, or used a separately assessed setup.
- **CI:** would you run this loop in CI? Under what conditions?

## 9. After the fix (optional)

| Field | Values | Notes |
|---|---|---|
| Root cause | free text | the rule the code failed to enforce, and why nothing forced it |
| Variant search | free text | where else the same rule could break; what you searched and what you found |
| Guardrail | free text | what now keeps the class out: a design change, a rule or a test; it fails on the vulnerable revision and passes on the fixed one |

A fix closes one path. Variants of patched bugs are common, often because
the fix blocked the reported path and left the cause in place. Searching by
the broken rule finds more than searching for code that looks like the fix.
An agent can help with the search and with drafting the guardrail, but every
reported variant and every guardrail needs the same proof as the fix.
Agents have the weakest record on authorisation rules.

## What "valid fix" means here

A fix counts as valid when a regression test exercises the vulnerable path
and fails before and passes after, the existing suite still passes, and a
person who did not drive the agent approved it.

Passing tests alone are not enough. Agentic patches that pass tests can still
introduce or hide vulnerabilities, and iterative self-repair can make things
worse (arXiv 2507.02976; arXiv 2509.25894). Tests lower the likelihood of a
regression, never its impact.

A tool's own "verified" label names the process it ran, which may be a
sandboxed test run or a second static read; the verification row in section 5
records which. A reviewer who sees only the claim and the diff, without the
agent's reasoning, is harder to talk into approving a bad fix. The human gate
is the control.
