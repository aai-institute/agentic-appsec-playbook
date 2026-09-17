# Documentation maintenance notes

This file holds editorial notes outside the published Astro content tree.
Keep page status and evidence labels here. Explain limitations that affect
readers' decisions in plain language on the relevant page, and retain public
source links and dated run evidence there.

## Editorial status

Status recorded when the public markers were removed on September 17, 2026.
Removing a marker does not establish that a page or workflow was validated.

| Page | Editorial status and follow-up |
|---|---|
| Landing page | Pre-release working material. |
| First discovery pass | Draft exercise. |
| Triage rubric | Draft. |
| Shared observations | Draft. |
| Validation loop | Draft record template. |
| Hardening checklist | Draft; refine using sandbox friction from completed validation-loop records, including the sanctioned relaxations. |
| Tool shortlist: specialist options | Integration with the playbook sandbox has not been tested. Keep this limitation visible to readers. |

The September 7, 2026 revision of Shared observations replaced the earlier
shared metrics definition: true-positive rate, severity accuracy, cost per
accepted fix and minimum-aggregation rules. A single pilot repo and capped
triage do not support those rates. The public page retains that rationale.

## Evidence labels for working notes

| Label | Meaning |
|---|---|
| `verified-at-source` | A primary source was read; this does not establish local execution. |
| `reported-but-unverified` | Secondary coverage only. |
| `checked` | A command was run and its output confirmed. Record the environment and date. |
| `to-verify` / `not-yet-tested` | Written but not yet exercised. |

Treat operational detail without supporting evidence as pending verification.
Do not add these labels or draft-status banners to published pages. Keep the
general data-freshness note at the bottom of the landing page; specific run
dates and implementation assessments remain with their evidence.

## Unpublished research provenance

References beginning with `research/` or `reports/` identify background notes
that are not yet public. Preserve them for maintainers without presenting
them as reader-accessible links. Prefer public primary sources on the site.

The tool shortlist draws on the masterclass market survey and these reports:

- `deep-research-report.md`
- `offensive-redteam-tooling-research.md`
- `sota-research-update.md`
- `sota-delta-2026-09.md`
- `followups-batch-2026-09.md`

The Choosing a model page also draws on `model-access-tiers-2026-09.md`.
Its public provider links support the availability and retention guidance.

The Hardening checklist draws on:

- `research/agent-sandboxing-incidents-2026.md`: HF and Anthropic incidents.
- `research/sota-delta-2026-09.md` §4: Comment-and-Control and the `/proc` case.
- `research/sandbox-prior-art.md` §5: OpenAI's *Agent security in the enterprise*
  and CIS control IDs; §6: AI-specific differences and OWASP Agentic Top 10 2026.

The Validation loop's discussion of patches that pass tests draws on
`reports/limitations-skeptical-agentic-appsec.md` §3. The public page retains
the arXiv identifiers 2507.02976 and 2509.25894.
