---
title: Agentic AppSec Pilot Playbook
description: Run open-source, AI-agent-based application security tooling on your own code, safely, and decide from your own evidence.
---

Hands-on material for running open-source, AI-agent-based application security tooling on
your own code: contained first, then measured, so that a local go/no-go decision comes from
your own evidence rather than from public leaderboards.

**For:** AppSec and DevSecOps engineers, security engineers and senior developers who own
security tooling in an organisation, are comfortable with Git and CI, and can run CLI tools
against a test repository. No machine-learning background needed.

New here? Start with [Getting started](/getting-started/).
Then work through the [Exercise: first discovery pass](/exercises/first-discovery-pass/) to capture
raw findings and a run report from your own pilot repository.

## The five steps

| Step | Pages |
|---|---|
| 1. Contain the agent before it touches your code | [A safe environment for experiments](/sandbox/no-regret-measures/), the six things that must hold before the first run; [appsec-sbx](/sandbox/sbx/), the wrapper that implements them on Docker sbx |
| 2. Pick a tool for the job | [Tool shortlist](/tools/shortlist/): capabilities, license, maturity, setup effort and limits; [Choosing a model](/tools/choosing-a-model/): privacy, hosting, monitoring, cyber benchmarks and cost |
| 3. Triage what the tool reports, and know what it cost | [Triage rubric](/triage/triage-rubric/), time-capped and severity-first; [Observations](/triage/observations/), the per-run record |
| 4. Prove it, fix it, gate it | [Validation loop](/validation/validation-loop-template/): hypothesis, validation, fix, regression test, human-gated merge |
| 5. Run it unattended | [Hardening checklist](/hardening/hardening-checklist/): what has to be true before the loop runs in CI without someone watching |

## Exercises

Apply the playbook to your pilot repository in sequence. The first exercise
is available now; the remaining working-group exercises will be added here.

| Exercise | What you'll produce |
|---|---|
| [1 · First discovery pass](/exercises/first-discovery-pass/) | A contained security scan, raw findings and a run report. |
| 2 · Triage and compare (coming soon) | Time-capped triage, a second discovery pass with one comparison variable, and 2–3 findings to validate. |
| 3 · Validate and fix one finding (coming soon) | A validation outcome and, if confirmed, a fix with a regression test and human review, recorded in the loop template. |
| 4 · Hardening and results review (optional; coming soon) | A hardening self-assessment and feedback on the shared experience report. |

## Design notes and evidence

The [threat model](/sandbox/threat-model/) explains the sandbox's scope,
controls and remaining risks. The backend comparison, implementation backlog and
wrapper's design notes live in the repository's
[`design/`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/design) directory;
platform acceptance records in
[`records/`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/records). They
are the maintainers' working documents: read them to check a claim, not to operate the tools.

## License

Documentation is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
code under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0). Maintained by the
appliedAI Institute for Europe gGmbH.

## Data freshness

Tool descriptions, model availability and benchmark methodology were checked
on **September 17, 2026**. Models, prices, access requirements and retention
terms change quickly; verify the linked sources before selecting a tool or
model. Local run evidence and sandbox implementation assessments carry their
own dates.
