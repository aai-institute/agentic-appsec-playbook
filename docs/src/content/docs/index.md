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

**Status:** pre-release working material. Each page carries a status line saying how settled
it is, and operational claims are tagged (see [Conventions](#conventions)).

New here? Start with [Getting started](/getting-started/).

## The five steps

| Step | Pages |
|---|---|
| 1. Contain the agent before it touches your code | [No-regret measures](/sandbox/no-regret-measures/), the six things that must hold before the first run; [AppSec shell](/sandbox/sbx/), the wrapper that implements them on Docker sbx |
| 2. Pick a tool for the job | [Tool shortlist](/tools/shortlist/): open-source candidates per job, with license, maturity, setup effort, blind spots and model-access tiers |
| 3. Triage what the tool reports, and know what it cost | [Triage rubric](/triage/triage-rubric/), time-capped and severity-first; [Observations](/triage/observations/), the per-run record |
| 4. Prove it, fix it, gate it | [Validation loop](/validation/validation-loop-template/): hypothesis, validation, fix, regression test, human-gated merge |
| 5. Run it unattended | [Hardening checklist](/hardening/hardening-checklist/): what has to be true before the loop runs in CI without someone watching |

## Conventions

- **Status lines** at the top of each page say how settled it is.
- **Tags on claims and commands:** `verified-at-source` (read the primary source),
  `reported-but-unverified` (secondary coverage only), `checked` (command run and output
  confirmed), `to-verify` / `not-yet-tested` (written, not yet exercised). Treat untagged
  operational detail as `to-verify`.
- **Model and tool versions are dated.** The landscape moves monthly; every version, price
  and safeguard statement carries the date it was true.
- **Background research.** References of the form `research/<note>.md` or `reports/<report>.md`
  point to research notes that are not yet public. Treat them as citations you cannot follow
  yet, not as broken links.

## Design notes and evidence

The threat model, the sandbox backend comparison, the Colima reference implementation and the
wrapper's design notes live in the repository's
[`design/`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/design) directory;
platform acceptance records in
[`records/`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/records). They
are the maintainers' working documents: read them to check a claim, not to operate the tools.

## Sharing results across organisations

The triage and validation records are designed so that a group of organisations can compare
notes without exposing code: repositories appear as a descriptor (languages, size bucket,
domain, age bucket), findings as CWE class, severity and verdict, and no detail of an unfixed
vulnerability leaves the organisation until it is fixed or the risk is accepted in writing.

## License

Documentation is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
code under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0). Maintained by the
appliedAI Institute for Europe gGmbH.
