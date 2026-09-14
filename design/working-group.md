# The working group behind this material

Context for maintainers. The playbook was built for and is used in the appliedAI Institute
working group *Practical application of AI-powered open-source AppSec tooling* (four bi-weekly
online sessions, Q3/Q4 2026) and extracted into its own repository so it can be released and
maintained independently of the working group's internal planning.

## Release rule and schedule

The appliedAI Institute publishes this material under its non-profit mandate. To keep that
clean, **every document here is released publicly before the working-group session that first
references it**: the working group uses the public artifact, it never gets a private preview.
Documents may still be marked *draft* when they go public; what matters is that they are
public.

| Must be public before | Session | Documents first referenced |
|---|---|---|
| **2026-09-17** | 1 · Landscape & setup | the sandbox pages and scripts, the tool shortlist |
| 2026-10-01 | 2 · Discovery in practice | triage rubric, observations table, the shortlist's second-tool sections |
| 2026-10-15 | 3 · Validation & triage | validation-loop template |
| 2026-10-29 | 4 · Operationalization & hardening | hardening checklist, CI runner design (and its implementation, if ready) |

Since repository visibility is all-or-nothing, the first row sets the date: the repository goes
public before 2026-09-17, with later documents present in draft state. Blocking items for that
date are tracked as issues.

## Sharing rules

The triage and validation records are designed so that a group of organisations can compare
notes without exposing code: repositories appear as a *descriptor* (languages, size bucket,
domain, age bucket), findings as CWE class, severity and verdict, and **no detail of an unfixed
vulnerability leaves the organisation** until it is fixed or the risk is accepted in writing.
The working group's full sharing rules (Chatham House in sessions, pseudonyms, review-and-veto
before publication) live with the working group; adopt or adapt them if you run a similar
exchange.

## Background research

References of the form `research/<note>.md` or `reports/<report>.md` in the documents point to
the working group's research notes and deep-research reports, which are not yet public. They
will be released alongside the working group's whitepaper; until then they are citations that
cannot be followed, not broken links. Resolving them before publication is
[issue #2](https://github.com/aai-institute/agentic-appsec-playbook/issues/2).

## Provenance

Extracted on 2026-09-07 from the working group's internal planning repository (commit
`2e25355`), where these documents were developed between 2026-09-01 and 2026-09-07. The
working group's session plans reference this repository as `playbook/<path>`. Participant or
organisation data from the working group is never committed here.

## Maintainer

appliedAI Institute for Europe gGmbH, Adrian Rumpold. The repository is private during the
working group; collaborators use issues and pull requests here, everyone else reaches the
maintainer directly.
