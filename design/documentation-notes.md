# Documentation maintenance notes

This file holds editorial notes outside the published Astro content tree.
Keep page status and evidence labels here. Explain limitations that affect
readers' decisions in plain language on the relevant page, and retain public
source links and dated run evidence there.

## Editorial status

### Session-based publication

Sandboxing, tool/model selection and the first discovery exercise are
published. Triage, shared observations, validation and hardening are held
for the relevant working-group sessions. Their source files remain under
`docs/src/content/docs/` with `draft: true`, so production builds exclude
their routes, search entries and sitemap entries. Astro's dev server can
still show drafts by direct URL for editing.

Starlight has no native disabled sidebar item. These sections are omitted
from `docs/astro.config.mjs`; Home retains a plain-text coming-soon outline.
Public pages use the discovery exercise's run report while later templates
are unavailable.

To release a section:

1. Review its content for the session and remove `draft: true`.
2. Restore its sidebar group (3 · Triage, 4 · Validation or 5 · Hardening).
3. Update Home's outline and relevant cross-references to link to the released pages.
4. Build the site and check internal links, search and sitemap output.

### Page maturity

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
