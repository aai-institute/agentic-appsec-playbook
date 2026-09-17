---
title: Agentic AppSec Pilot Playbook
description: Run open-source, AI-agent-based application security tooling on your own code, safely, and decide from your own evidence.
---

:::note[Work in progress]
This playbook is a living document. We update it as tools change and we learn
from hands-on use. Sandboxing and discovery are available now; triage,
validation and hardening content will follow.
:::

Hands-on material for running open-source, AI-agent-based application security tooling on
your own code: contained first, then measured, so that a local go/no-go decision comes from
your own evidence rather than from public leaderboards.

**For:** AppSec and DevSecOps engineers, security engineers and senior developers who own
security tooling in an organisation, are comfortable with Git and CI, and can run CLI tools
against a test repository. No machine-learning background needed.

New here? The [first security review tutorial](/getting-started/) walks through tool and model
choices, privacy checks, sandbox setup and a first review. It links to
detailed comparisons when you need them.
The [glossary](/glossary/) explains the terminology used throughout the playbook.
Then work through the [Exercise: first discovery pass](/exercises/first-discovery-pass/) to capture
raw findings and a run report from your own pilot repository.

## The five steps

| Step | Pages |
|---|---|
| 1. Choose a tool, model and hosting route | [Tool shortlist](/tools/shortlist/): capabilities, license, maturity, setup effort and limits; [Choosing a model](/tools/choosing-a-model/): privacy, hosting, monitoring, cyber benchmarks and cost |
| 2. Contain the agent and run a first review | [A safe environment for experiments](/sandbox/no-regret-measures/): the six measures required before a run; [First security review tutorial](/getting-started/): setup and review; [appsec-sbx](/sandbox/sbx/): operating reference |
| 3. Triage what the tool reports, and know what it cost | Coming soon: time-capped triage and shared observations. |
| 4. Prove it, fix it, gate it | Coming soon: validation, fixes, regression tests and human review. |
| 5. Run it unattended | Coming soon: hardening for CI and unattended runs. |

## Exercises

Apply the playbook to your pilot repository in sequence. The first exercise
is available now; the remaining exercises will be added here.

| Exercise | What you'll produce |
|---|---|
| [1 · First discovery pass](/exercises/first-discovery-pass/) | A contained security scan, raw findings and a run report. |
| 2 · Triage and compare (coming soon) | Time-capped triage, a second discovery pass with one comparison variable, and 2–3 findings to validate. |
| 3 · Validate and fix one finding (coming soon) | A validation outcome and, if confirmed, a fix with a regression test and human review, recorded in the loop template. |
| 4 · Hardening and results review (optional; coming soon) | A hardening self-assessment and a review of your pilot results. |

## Sandbox limits

The [threat model](/sandbox/threat-model/) explains the sandbox's scope,
controls and remaining risks. Review the
[coverage limits](/sandbox/threat-model/controls/) before relying on the setup
for more sensitive work.

## License

Documentation is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
code under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0). Maintained by the
appliedAI Institute for Europe gGmbH.

## Data freshness

Tool descriptions, model availability and benchmark methodology were checked
on **September 17, 2026**. Models, prices, access requirements and retention
terms change quickly; verify the linked sources before selecting a tool or
model.

---

**AI assistance:** Parts of this documentation were generated or edited with
AI assistance. The playbook's maintainers are responsible for its content.
