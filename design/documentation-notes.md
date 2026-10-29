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

Sandboxing, tool/model selection, both exercises, the Triage section (rubric
and run observations) and the validation loop record are published. Hardening
remains unpublished pending content review. Their source files
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
| Validate a finding (exercise 2) | Reworked 2026-10-08 from "Triage and compare" (route `/exercises/validate-a-finding/`; the old route was never released): time-capped triage until one finding is worth proving, claim with confirming and refuting criteria, a regression test written or drafted by an agent and run in the review VM, grading with the evidence rules. Optional challenges: a second model for the same test; a tool's own validation step (Codex Security, Defending Code's scan and triage skills) graded with the evidence rules, with Strix waiting on Docker in the workload. Validation means a witness with harmless input, not an exploit. In the sidebar and Home's exercise table; linked from the first exercise, the rubric and the Triage overview. Part 2 links the validation loop record (sections 2 and 3) and still lists the fields inline. |
| Triage overview | Added 2026-10-06: why triage comes before proving (note aside), what each of the two records is for, and the reading order. |
| Triage rubric | Released with the Triage section. Evidence rules and exploitability values added 2026-10-06 from four preprints read in full (all agent or benchmark studies, none of human triage). FP reasons (not present, unreachable, mitigated, quality-only, test-only) added 2026-10-06 after reading the GitLab and GitHub vulnerability docs, `verified-at-source`; deployment context, the minor-flaw rule and the kinds-of-evidence table added 2026-10-09 from the working group's pipeline deck; the CRA Art. 3(41) quote `verified-at-source` (Official Journal text, via the WG research wiki); the first three mirror both platforms' dismissal reasons, and exercise 2 asks for them. The page names no purpose beyond picking loop candidates and measuring triage time; the stated purpose is under review. Links the validation loop record since its release on 2026-10-14. |
| Run observations | Released with the Triage section. Field alignment with the discovery exercise's run report is open. |
| Validation loop | Released 2026-10-14 for working-group session 2, which uses sections 1 to 4. Sections 5 to 8 (fix, review, time, qualitative) reviewed 2026-10-20 against exercise 3: a "verification that actually ran" row added to section 5 after a harness trial whose scan validation was a second static read while its patch stage executed the suite; the valid-fix paragraph says a tool's "verified" names a process. Same day, from the harness's fix and patch-risk skills: an outcome row (fixed / no change needed / blocked), a bypass row and checkbox (2026-10-22), "what the reviewer saw" and a four-word risk call in section 6, and an optional section 9 (root cause, variant search, guardrail) from the working group's research synthesis on the step after a fix (SSDF RV.3, Project Zero variant data, Google class elimination, agent variant-analysis papers; unpublished WG research, see the release note in `design/working-group.md`). |
| Fix a validated finding (exercise 3) | Added 2026-10-20 for working-group session 3 (2026-10-29), route `/exercises/fix-a-finding/`. Slim by design: brief a patch agent with the claim and the failing test only, verify the fix yourself with one check per failure mode, review by someone who did not drive the agent, sections 5 to 8. Fallback target: the example application's attachment download with a published regression test, checked 2026-10-20 to fail on `seeded` (guest receives 200) and pass on `main`. Optional challenges: a tool's own patch stage graded with the evidence rules; section 9 after the fix; an SBOM and known-vulnerability scan of the pilot repository (outside the sandbox, whose policy blocks the advisory databases). Part 3 gives the reviewer the claim, diff and test results without the agent's transcript. A fifth failure-mode check (bypass test) and an optional challenge (a second model, open-weight if the provider declines, tries to break the fix) added 2026-10-22, after the php2shell coordinators described adversarial testing for bypasses and variants before release; the 60 %/15 % patch-survival figure comes from the Defending Code harness's own docs and stays off the page. In the sidebar and Home's exercise table; linked from exercise 2. On 2026-10-29 the section 9 and SBOM challenges were dropped to keep the exercise to the fix itself (section 9 stays in the loop record template), and the outcome values became value chips. Same day, the second-model challenge became a model review (the reviewer's inputs and questions plus one bypass test), also the option when no person can review; a model review caps the result at merge-ready, and section 6 of the template gained a "Reviewed by" row. |
| Hardening checklist | Draft; refine using access needs recorded during completed validation loops. |
| Securing the agent's context | Added 2026-10-21 for working-group session 3 (2026-10-29), route `/sandbox/agent-context/`. The same day both it and the no-regret measures moved into a new sidebar section, *Securing the agent* (routes unchanged under `/sandbox/`, so existing links keep working); *Getting started* points there with a first entry, and the hardening checklist joins the section when it is released. Linked from the no-regret page and Home's step 2. Written from the session 3 context deck and the working group's research wiki (three passes on 2026-10-21: context gaps, guardrails, techniques); the page cites only the public primary sources. Sandbox statements checked against `transfer.py`, `guest/bootstrap.sh` and `sbxcli.py` at `e51a2c2`. It names four open gaps in plain language: root instruction files and `.mcp.json` reach the VM, Claude Code auto memory stays on, no per-tool allowlist in the harnesses, no output sanitisation. Close them through threat-model rows first, then update the page. Vendor documentation (Claude Code, NeMo Guardrails, ToolHive) read October 2026; behaviour not tested in the VM. Since 2026-10-23 the techniques table lists names only, without OWASP or ATLAS identifiers: the catalogues do not map one to one, and a crosswalk belongs to a team that has settled on one of them. The session 3 deck keeps the identifiers in its speaker notes. On 2026-10-29 the guardrails section was cut to the agent's scope: limits versus text checks and where to set them for a coding agent; the product table (Prompt Guard 2, LLM Guard) and the CaMeL/Progent research designs belong to securing AI applications and left the page. The page links the OWASP GenAI Crosswalk instead (About page read 2026-10-23: classifier-assisted mappings, 34 ATLAS rows marked draft, LLM Top 10 2026 renumbers the entries; the page's sources still cite the 2025 list). |
| Tool shortlist: specialist options | Integration with the playbook sandbox has not been tested. Keep this limitation visible to readers. |
| Tool shortlist: Codex Security | Provider paragraph corrected 2026-10-20 from a host trial (cs 0.5.0, Codex 0.163.0): sub-agent briefs travel as encrypted content only OpenAI's API unwraps, so other providers get a solo pass at best (Codex issues 34833, 37237); the earlier sentence about the screening model staying on an OpenAI model through other providers came from a September sandbox run and was not seen in the October logs, so it was dropped rather than repeated. Added: the scan reads ignored files. `--create-pr` paragraph added 2026-10-27, `verified-at-source` from cs 0.5.1's `dist/cli.js` and `dist/patch-publication.js` (branch `codex-security/patch-<scanId>`, one commit and PR per invocation, publisher runs `gh pr list --head … --state all` before pushing) and observed on the private stand-in repository the same day (second PR collided on 10-20; after a branch rename closed PR 1, the harness reported the closed PR and pushed nothing). Record in the demo repository's `runs/codex-security-e2e-host-2026-10-20.md`, unpublished. |

The September 7, 2026 revision of Shared observations replaced the earlier
shared metrics definition: true-positive rate, severity accuracy, cost per
accepted fix and minimum-aggregation rules. A single pilot repo and capped
triage do not support those rates. The public page retains that rationale.

The September 17 editorial pass removed model-tier labels and assumptions
about cross-organisation reporting from the drafts. Validation and hardening
now describe the separate reproducer VM and identify capabilities requiring
additional assessment. All four pages remain drafts. This pass did not
recheck external incident claims or validate an unattended workflow.

## Candidate exercise targets

The exercises use the playbook's demo forum as the example application. A second
candidate, noted 2026-10-08, is **Invoice Desk** in OpenAI's Codex Security repository
([`examples/invoice-desk`](https://github.com/openai/codex-security/tree/main/examples/invoice-desk),
Apache-2.0 like the rest of the repository). `verified-at-source`, from the repository
page:

- A deliberately insecure invoice application for Codex Security QA, with ten seeded
  scenarios and synthetic data. Node.js 22.13 or later, in-memory storage, no
  dependencies, no build; it binds to loopback and makes no outbound requests.
- The answer key sits outside the scanned code: `app/` is the scan input, while `qa/`
  holds the scenario guide, `expected-findings.json` and behaviour tests that pass while
  the weaknesses are present. `SECURITY.md` carries a threat model.

Why it is interesting: a second language and framework next to the Python forum, and an
answer key kept apart from the target, as the forum's seeds are.

Caveats before using it:

- It is Codex Security's own QA target, so Codex Security's results on it are not
  independent of the tool's tuning. Compare other tools on it, or say so when quoting
  Codex Security.
- Import only `app/`; the wrapper imports a repository, so `app/` becomes its own local
  repository first. `checked` 2026-10-08 on macOS, sbx v0.47.0, wrapper 0.4.0: 11 files
  imported from `openai/codex-security@5ebe48db0585`; the VM has Node.js 24.20.
- Added on 2026-10-01 (commit `619d389c`, `verified-at-source`), so it postdates current
  models' training cutoffs and cannot have been memorised. That holds only
  until models trained on it appear; record the model's release date with each result.

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
