# Documentation maintenance notes

This file holds editorial notes outside the published Astro content tree.
Keep page status and evidence labels here. Explain limitations that affect
readers' decisions in plain language on the relevant page, and retain public
source links there. Keep local-run narratives, measurements and platform test
history in `design/` and `records/`, including references to unpublished runs.
The [local evidence archive](local-evidence-archive.md) preserves material
removed from reader-facing pages during the September 17 editorial pass.

## Editorial status

### Publication status

Sandboxing, tool/model selection, the first discovery exercise and the
Triage section (rubric and run observations) are published. Validation and
hardening remain unpublished pending content review. Their source files
remain under `docs/src/content/docs/` with `draft: true`, so production builds exclude
their routes, search entries and sitemap entries. Astro's dev server can
still show drafts by direct URL for editing.

Starlight has no native disabled sidebar item. These sections are omitted
from `docs/astro.config.mjs`; Home retains a plain-text coming-soon outline.
Public pages use the discovery exercise's run report while later templates
are unavailable.

To release a section:

1. Review its content and remove `draft: true`.
2. Add its sidebar group (Triage, Validation or Hardening).
3. Update Home's outline and relevant cross-references to link to the released pages.
4. Build the site and check internal links, search and sitemap output.

### Page maturity

Status recorded when the public markers were removed on September 17, 2026.
Removing a marker does not establish that a page or workflow was validated.

| Page | Editorial status and follow-up |
|---|---|
| Landing page | Pre-release working material. |
| First discovery pass | Draft exercise. |
| Triage and compare (exercise 2) | Bootstrapped 2026-10-06 from the session 2 assignment; in the sidebar and Home's exercise table. Linked from the first exercise's closing line, the shortlist intro, the rubric's purpose line and the observations intro. Open: the coverage change (Strix or PentAGI against the example application) once the Docker profile is merged. |
| Triage overview | Added 2026-10-06: why triage comes before proving (note aside), what each of the two records is for, and the reading order. |
| Triage rubric | Released with the Triage section. Evidence rules and exploitability values added 2026-10-06 from four preprints read in full (all agent or benchmark studies, none of human triage). FP reasons (not present, unreachable, mitigated, quality-only, test-only) added 2026-10-06 after reading the GitLab and GitHub vulnerability docs, `verified-at-source`; the first three mirror both platforms' dismissal reasons, and exercise 2 asks for them. The page names no purpose beyond picking loop candidates and measuring triage time; the stated purpose is under review. The validation loop is mentioned without a link until it is released. |
| Run observations | Released with the Triage section. Field alignment with the discovery exercise's run report is open. |
| Validation loop | Draft record template. |
| Hardening checklist | Draft; refine using access needs recorded during completed validation loops. |
| Tool shortlist: specialist options | Integration with the playbook sandbox has not been tested. Keep this limitation visible to readers. |

The September 7, 2026 revision of Shared observations replaced the earlier
shared metrics definition: true-positive rate, severity accuracy, cost per
accepted fix and minimum-aggregation rules. A single pilot repo and capped
triage do not support those rates. The public page retains that rationale.

The September 17 editorial pass removed model-tier labels and assumptions
about cross-organisation reporting from the drafts. Validation and hardening
now describe the separate reproducer VM and identify capabilities requiring
additional assessment. All four pages remain drafts. This pass did not
recheck external incident claims or validate an unattended workflow.

## Maintaining the command reference and threat model

The published command reference is generated from the wrapper's argparse help.
Edit the help strings in `sandbox/sbx/appsec_sbx/cli.py`, or the page
introduction in `sandbox/sbx/gen_command_reference.py`, then regenerate from
the repository root:

```sh
python3 sandbox/sbx/gen_command_reference.py > docs/src/content/docs/sandbox/sbx/commands.md
python3 -m unittest discover -s sandbox/sbx -p 'test_appsec_sbx.py'
```

The command-reference test checks that the generated page matches the CLI.
Keep editing instructions here rather than in the reader-facing reference.

Track implementation choices and completion criteria in the
[sandbox backlog](sandbox-backlog.md). Public control tables should describe
current behavior, limitations and the checks readers need for their setup.
Keep historical rationale and implementation task lists in `design/`.
Keep threat and requirement IDs stable when updating their mappings and
evidence. A technology change may satisfy a requirement differently; it
does not remove the requirement.

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

The Codex Security entry (added September 25, 2026) is `verified-at-source`
against the repository and SDK READMEs, the GitHub Actions example, the CLI
documentation at learn.chatgpt.com/docs/security/cli, the March 6, 2026
announcement and the help-center article. The sandbox statements are `checked`
against the September 25, 2026 runs in `records/sbx-acceptance.md` (macOS, sbx
0.45.1); the idle-timeout override and `patch` inside the guest remain
`not-yet-tested`.

The September 30, 2026 refresh (session 1 moved to October 1) draws on
`sota-delta-2026-09-30.md`, which merges four primary-source passes (vendor
access, tool status, incidents and policy, arXiv). Public-page changes from
it are `verified-at-source`: Opus 5.5 / Sonnet 5.5 and their fallback
targets, GPT-6 Astra and the four Daybreak levels (help centre and DevDay
recap read in a browser on September 30), Gemini 3.8 Flash Cyber's model
page, CAISI's GLM-5.3 assessment, AISI's Astra evaluation, DeepSeek's V4 Pro
routing, Codex Security releases 0.1.25–0.1.31, Strix 1.6 and its telemetry
setting, PentAGI's September triage, Mantis commits, Docker's 0.42.0
security announcement, CVE-2026-80521, Plugin4Shell and the arXiv
identifiers cited on the hardening page. The sbx 0.46.0 statements are
`checked` (records, September 30). The Qwen3.8-Max row and the Qwen3.8-27B
CyberGym baseline (added September 30) are `verified-at-source` against the
Z.ai GLM-5.3 post and footnotes, the Alibaba Security model-track write-up,
the Hugging Face model cards and licence, Alibaba Cloud's model page and the
official CyberGym data file; the 78.5 figure circulating in comparison blogs
is Z.ai's competitor-run number, not an Alibaba or leaderboard figure. Kept off the pages as
`reported-but-unverified`: CodeMender CLI 0.10, the Codex Security 0.1.32
default-model change (tag only), GLM-5.3-FlashX, Qwen 4, the Bedrock
AgentCore CVEs, GitHub's agentic autofix items, Aikido Altar.

The Gemini 4 Argon entries (added October 1, 2026, the day of session 1)
are `verified-at-source` against Google's September 30 announcement and the
Fairwind Program page (Argon as the program's model, no cyber guardrails for
participants, ZDR for direct managed-model access on Gemini Enterprise). The
four pre-release safeguard areas come from the announcement; its benchmark
figures (DeepSWE v1.1 77.9%, CWE-bench v1 68%) and pricing ($2 / $10 per
million tokens introductory, $4 / $20 after) are kept here only, since the
page compares on CyberGym and ExploitGym. `checked` on October 1: the
Gemini API models page lists no Argon model ID. `reported-but-unverified`
and kept off the page: the 18-benchmark comparison and the claim that no
Argon model report exists (press coverage only; Google's safety-report page
was not re-read), the Wiz healthcare finding, and the standard-price start
date, which Google has not published. Replace the Fairwind-only framing when
Google publishes a model page or opens paid API access.

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
