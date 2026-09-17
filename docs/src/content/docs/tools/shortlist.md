---
title: "Tool Shortlist"
description: "Freely available security tools, their capabilities, setup effort and limits."
---

Start with a tool that fits the job, then use [Choosing a model](/tools/choosing-a-model/)
to select its model and hosting route.
The shortlist below covers the main open contenders from the masterclass and
follow-up research. Their code or prompts are freely available; model usage
and infrastructure may still cost money.

For a first discovery pass, start with **Anthropic's `security-review`**.
Try **Defending Code** for a structured scan and triage workflow, or
**Google Mantis** for a modular review pipeline. The specialist options below
need more setup.

## Core tools

### Anthropic security-review

[Repository and prompt](https://github.com/anthropics/claude-code-security-review)
· MIT

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Discovery</span>
  <span class="tool-chip tool-chip--review">PR review</span>
</div>

A lightweight security review prompt, also shipped as Claude Code's
`/security-review` command and a GitHub Action. It examines code changes and
filters findings by confidence. Choose it for a small, inspectable starting
point or a baseline to compare with larger tools.

- **Setup:** the playbook supplies `security-review-repo`, a whole-repository
  adaptation of the prompt. Follow [Getting started](/getting-started/) and
  the [skills guide](/sandbox/sbx/skills/). The upstream command reviews
  pending changes; use the adaptation for an imported repository.
- **Maturity:** an established prompt with a small setup burden. September
  research flagged maintenance drift and reported defects in the Action;
  test that integration separately before relying on it in CI.
- **Limits:** the supplied prompt excludes classes such as DoS, rate limiting,
  outdated dependencies and memory-safety issues in languages it treats as
  memory safe. Read these exclusions before assessing coverage. Its confidence
  filter can hide real findings, and it does not require reproduction.

### Anthropic Defending Code Reference Harness

[Repository](https://github.com/anthropics/defending-code-reference-harness)
· Apache-2.0

<div class="tool-categories">
  <span class="tool-chip tool-chip--review">Threat modeling</span>
  <span class="tool-chip tool-chip--discovery">Discovery</span>
  <span class="tool-chip tool-chip--review">Triage</span>
  <span class="tool-chip tool-chip--repair">Patching</span>
</div>

Skills for each review stage, plus an autonomous find → verify → patch
pipeline. Choose it when you want explicit stages and structured reports.
The full pipeline starts with C/C++ memory bugs, Docker and sanitizers;
other stacks need adaptation.

- **Setup:** start with the skills and `/vuln-scan`. The
  [installation guide](/sandbox/sbx/skills/#defending-code-reference-harness)
  covers the tested revision and report export. Importing skills does not
  install the autonomous pipeline or its runtime.
- **Maturity:** Anthropic explicitly labels the repository unmaintained.
  Treat it as a reference implementation that your team will need to own.
- **Local evidence:** discovery runs completed in the playbook sandbox. The
  September 16 OpenCode run took 45m 19s against a 20-minute budget, miscounted
  parts of its report and attempted blocked web fetches. Allow time for a
  dry run; completion alone does not establish correct behavior.

### Google Mantis

[Repository](https://github.com/google/mantis)
· Apache-2.0

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Discovery</span>
  <span class="tool-chip tool-chip--validation">Reproduction</span>
  <span class="tool-chip tool-chip--repair">Patching</span>
</div>

A toolkit of review skills with a reference harness built on Google's Agent
Development Kit (ADK). Its stages map the code and threats, explore possible
bugs, check and merge findings, then reproduce and patch them. Choose it when you want
to inspect or adapt individual stages of a broader review.

- **Setup:** import a pinned skill pack using the
  [skills guide](/sandbox/sbx/skills/). Running the upstream reference harness
  requires its own setup and model configuration.
- **Maturity:** Google describes it as a demonstration project without
  official product support. Budget for tuning it to your stack.
- **Limits in this sandbox:** the tested reproduce and patch skills expect
  Docker inside the agent environment, which this guest does not provide.
  Use the text-only stages and record what you skipped. Mantis also writes
  working files into the target tree; reset the imported source before a
  comparison run. Local skill runs do not validate its full pipeline.

## Specialist options

These tools are candidates for a separate experiment once their setup fits
your target. Their integration with the playbook sandbox has not been tested.

### GitHub Security Lab Taskflow Agent

[Repository](https://github.com/GitHubSecurityLab/seclab-taskflow-agent)
· MIT

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Code auditing</span>
  <span class="tool-chip tool-chip--review">Alert triage</span>
</div>

A framework for repeatable agent workflows, including CodeQL-assisted review
and alert triage. A useful candidate if you already have CodeQL databases or
scan results. Setup includes taskflows and any required analysis services;
the framework's license does not cover separate CodeQL access requirements.

### OpenSSF OSS-CRS

[Repository](https://github.com/ossf/oss-crs)
· MIT framework; component licenses vary

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Discovery</span>
  <span class="tool-chip tool-chip--repair">Repair</span>
</div>

An orchestration framework for cyber-reasoning systems, including work from
the AIxCC ecosystem. Consider it for sustained fuzzing and repair campaigns,
especially on OSS-Fuzz-compatible targets. Choose and configure a CRS as
well as the target build; this is a larger integration project than adding
a review skill.

### Trail of Bits Buttercup

[Repository](https://github.com/trailofbits/buttercup)
· AGPL-3.0

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Fuzzing</span>
  <span class="tool-chip tool-chip--repair">Repair</span>
</div>

A system from the AI Cyber Challenge (AIxCC) that combines fuzzing, analysis and patches.
Consider it when your project can support a fuzzing campaign and you have
capacity to operate its services. It has been tested in competition; setup
effort and patch quality still need testing on your code.

### Strix

[Repository](https://github.com/usestrix/strix)
· Apache-2.0

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Discovery</span>
  <span class="tool-chip tool-chip--review">PR review</span>
  <span class="tool-chip tool-chip--validation">Reproduction</span>
  <span class="tool-chip tool-chip--repair">Patching</span>
  <span class="tool-chip tool-chip--offensive">Offensive testing for defense</span>
</div>

An agentic security tool for source-code review and live application testing.
It documents reconnaissance, vulnerability discovery, PoC validation and
reporting, plus reviews scoped to PR changes in CI. With source access, its
[fix workflow](https://github.com/usestrix/strix/blob/main/skills/fix-security-vulnerabilities-with-strix/SKILL.md)
covers triage, patching and rescanning findings from the open-source CLI.
URL-only testing stops at findings and reports; patching needs the code.

Setup needs Docker, model access and a local codebase or reachable target.
Start with an isolated demo application. Check PoCs and patches yourself;
these are documented capabilities, not results validated in this playbook.

### PentAGI

[Repository](https://github.com/vxcontrol/pentagi)
· MIT

<div class="tool-categories">
  <span class="tool-chip tool-chip--discovery">Discovery</span>
  <span class="tool-chip tool-chip--validation">Reproduction</span>
  <span class="tool-chip tool-chip--review">Reporting</span>
  <span class="tool-chip tool-chip--offensive">Offensive testing for defense</span>
</div>

A multi-agent pentesting system for reconnaissance, vulnerability discovery
and exploit attempts. Its
[example workflow](https://github.com/vxcontrol/pentagi/blob/master/examples/prompts/base_web_pentest.md)
maps endpoints and tests suspected bugs; the documented output includes
reproduction steps and vulnerability reports, with Markdown and PDF export.
The reviewed documentation does not establish a patch-generation and
verification workflow, so patching is not tagged here.

Its service stack includes persistent memory and optional monitoring and
knowledge-graph services. Expect more setup than a single review prompt.
Measure runtime, cost and false positives, and verify reported reproductions
before accepting findings.

For Strix and PentAGI, confirm your organisation permits offensive tooling
and start with the example application. Isolate the target from production
systems and the internet. Check the sandbox's
[acceptance requirements](/sandbox/threat-model/acceptance/) before extending
its network access; the discovery setup alone does not establish that an
offensive workflow is safe.

## Validating results

For validation, a deterministic test remains the default. Every fix needs a
regression test that fails before and passes after, plus approval by a human
who did not drive the agent. The validation exercise will cover this process
in a later working-group session.
