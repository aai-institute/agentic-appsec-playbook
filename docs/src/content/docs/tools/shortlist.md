---
title: "Tool Shortlist"
---
Open-source candidates per job, with license, maturity, setup effort and
blind spots. The shortlist is a decision basis, not a decision: pick per job
and record what you picked in the run table.

Prior research: `reports/deep-research-report.md`,
`reports/offensive-redteam-tooling-research.md`, `reports/sota-research-update.md`
(not yet public, see the *Background research* convention on the
[start page](/#conventions)).

## Discovery (find)

<!-- TODO: remaining candidates — tool, license, maturity, setup effort, notes -->

### OpenCode + the `security-review` prompt — the reference harness for discovery

| | |
|---|---|
| What | **OpenCode** (`anomalyco/opencode`, MIT, 203k stars, active) running Anthropic's `security-review` prompt (MIT, from `anthropics/claude-code-security-review`) as a custom command in `.opencode/commands/`. Same prompt Claude Code ships as its built-in `/security-review` |
| License | Harness MIT, prompt MIT. Fully open stack; only the model may be closed |
| Maturity | Harness very active. Prompt frozen since 2026-02 (Action repo has open defects; "not designed to be hardened against prompt injection" per Anthropic) |
| Setup effort | Minutes: install OpenCode, drop the command file, `/connect` a provider. **But:** stock prompt scope is *pending changes vs `origin/HEAD`* — needs the whole-repo variant from `research/model-access-tiers-2026-09.md` §2 for a discovery pass. Port `not-yet-tested` |
| Sandboxing | OpenCode `permission` config (bash / edit / webfetch → allow / deny / ask) as a visible second layer; the VM sandbox from the no-regret checklist is the real containment |
| Blind spots by design | DoS, rate limiting, outdated deps, race conditions, memory safety, path-only SSRF, regex DoS, test files; confidence filter > 0.8 |
| Model, tier A1 | **Claude Fable 5.1** (2026-09-01) via Anthropic API key or OpenCode Zen ($10 / $50 per MTok): safeguards now allow vulnerability discovery, dual-use redirected to Opus; not under ZDR |
| Model, tier A2 | Same model on a **Claude seat** — only from **Claude Code** ≥ 2.1.250 with its built-in `/security-review`: Anthropic locked subscription auth to its own products, OpenCode removed the plugin in 1.3.0. Max/premium seats include Fable up to 50% weekly, Pro/standard seats via usage credits |
| Model, tier B | **GLM-5.3** (custom non-OSI license; Z.AI or OpenRouter `z-ai/glm-5.3`) or **DeepSeek V4 Pro** (MIT; DeepSeek or OpenRouter `deepseek/deepseek-v4-pro`) — native OpenCode providers via `/connect` |
| Evidence | arXiv 2605.10834 v3: plain Claude Code > Strix > PentAGI on validated discovery, also cheapest/fastest; arXiv 2607.13085: plain CLI agents incl. OpenCode match specialized-harness scores on XBOW (`followups-batch-2026-09.md` §3, `sota-delta-2026-09.md` §3) |
| Open-harness alternatives | google/mantis skills, `defending-code-reference-harness` `/vuln-scan` — candidates for a second discovery tool; see [skill installation](/sandbox/sbx/skills/) |

Full background, verbatim safeguard quotes, vendor configs and open
verification items: `research/model-access-tiers-2026-09.md`.

## Triage / validation — draft

<!-- TODO: The 2026-09-16 OpenCode/GLM-5.3-Flash run completed with direct
GitHub import at the same skill revision, but took 45m 19s. Review child
tool permissions, blocked fetches, report count errors and budget enforcement
before recommending this configuration for the 20-minute exercise. -->

The default validation design is **A — deterministic** (you write the test;
no tool needed beyond your stack). The entries below are for designs B/C and
for orgs that want agentic help with reproduction. Setup effort is
`not-yet-tested` unless stated; verify in a dry run before the first real finding.

| Candidate | What it does for validation | License / maturity | Notes |
|---|---|---|---|
| **OpenCode + tier-B model** (GLM-5.3, DeepSeek V4 Pro) | Drafts a reproducer / PoV from a finding; runs in the `runsc` lane, no network | Harness MIT; models custom-non-OSI / MIT | Design B. No safeguard layer — note its absence in the loop record. Same setup as for discovery |
| **google/mantis** — reproduce stage | Skill pipeline includes a *reproduce* step (fuzz → reproduce) before patching | Apache-2.0; 3 contributors, no tagged releases (`research/sota-delta-2026-09.md` §2) | If mantis is already your discovery harness, the reproduce skill is the relevant piece |
| **anthropics/defending-code-reference-harness** | Reference find → validate → patch harness | Apache-2.0; self-declared "not maintained" (`sota-delta` §1) | Read as a design reference for the loop as much as a tool |
| **GitHub Security Lab Taskflow Agent** | Agentic triage of CodeQL alerts | MIT (`sota-delta` §1) | Only for orgs already on CodeQL; triage rather than reproduction |
| **CVP access** (Anthropic Cyber Verification Program) | Opus/Sonnet-class with reduced cyber safeguards for the PoV step | Program, not a tool; free, org-scoped, ~2 business days, not for ZDR orgs | Design C. Apply as soon as triage points at a finding that needs it; the lead time is longer than a triage pass. `research/model-access-tiers-2026-09.md` §1 |

## Remediation (fix) — draft

| Candidate | What it does | License / maturity | Notes |
|---|---|---|---|
| **Same harness as discovery** (OpenCode / Claude Code) on a branch | Drafts the fix + regression test from the validated finding | as above | The default: smallest setup delta, fix stays reviewable |
| **google/mantis** — patch stage | Reproduce → patch → posture in one pipeline | Apache-2.0, early | For organisations already running mantis; watch for scope creep in the generated patch |
| **OSS-CRS / Buttercup / ATLANTIS** (AIxCC lineage) | Full cyber-reasoning systems: find, reproduce, patch at scale | Apache-2.0 / various; heavyweight | Not the loop default; a project in its own right, setup measured in days |

Guardrail for every entry: the fix PR carries a regression test that fails
before / passes after, and a human who did not drive the agent approves
([`validation/validation-loop-template.md`](/validation/validation-loop-template/), "What valid fix means").

## Offensive-for-defense — draft

| Candidate | License / maturity | Sandbox delta | Notes |
|---|---|---|---|
| **Strix** (`usestrix/strix`) | Apache-2.0; most active OSS offensive agent by release velocity | Running target on the internal bridge; no egress but the model endpoint; fake responders for callbacks | Only independent number is unflattering and vendor-conflicted — treat capability claims with the `sota-delta` §3 skepticism |
| **PentAGI** (`vxcontrol/pentagi`) | MIT | same | High-severity / high-cost / high-FP profile in arXiv 2605.10834 (`followups-batch-2026-09.md` §3) |
| CAI (`aliasrobotics/cai`) | archived, succeeded by a closed product | — | **Dropped** from the active list; historical reference only |

Policy gate: the org's policy must allow running offensive tooling at all,
and the default target is the example repo, not the pilot repo. The sandbox
requirements are in [`hardening/hardening-checklist.md`](/hardening/hardening-checklist/) §6.
