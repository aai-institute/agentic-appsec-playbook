---
title: "1 · First discovery pass"
description: Set up a sandbox, run one security discovery pass on a pilot repository, and record the results.
---

:::note[Overlap with Getting started]
You can start here directly. This standalone exercise uses the same setup
and review steps as the [first security review tutorial](/getting-started/)
in Getting started, then asks you to record the results from your pilot repository.

If you already completed the tutorial on that repository, check that your
run meets Parts 1–3 below, then use its findings for
[Part 4: Write the run report](#part-4-write-the-run-report). You do not need
to repeat a completed run that meets those requirements.

The effort estimate below covers the full exercise, including repository
selection, setup checks, the review and the run report. The tutorial's
one-hour estimate covers first-time setup.
:::

**Goal:** Run one contained security review of a pilot repository. Keep the raw findings
and a short run report so you can compare later runs.

**Effort:** about 1–2 person-days, spread over two weeks.

This exercise covers discovery only. Leave triage, proof-of-vulnerability
development and fixes for the next exercises.

## Part 1: Set up the sandbox

Follow [Getting started](/getting-started/) through the setup steps. Use the
[appsec-sbx wrapper](/sandbox/sbx/) to import a sanitised copy of your pilot repo
into a disposable Docker sandbox VM. The agent works on that copy.

Before starting the agent, complete the
[environment self-check](/sandbox/no-regret-measures/#check-your-environment).
The six requirements are:

- [ ] A dedicated, disposable VM with no host directories mounted.
- [ ] No production credentials in reach; scope limited to the pilot repo.
- [ ] Egress default-deny with a narrow allowlist.
- [ ] Short-lived credentials; no shared identity or writable state across runs.
- [ ] A token or spend budget set before the run: a hard cap where supported,
      a manual abort threshold otherwise.
- [ ] A tested kill switch, including credential revocation or rotation.

Complete the [kill-switch rehearsal](/sandbox/sbx/lifetime/#test-the-kill-switch)
before the first discovery pass. It ends with a clean reset; import the
target and skills afterwards and supply a fresh credential for the review.
Record the evidence requested by the self-check. All six measures must hold
before any agent runs.

For each later independent pass, including the optional comparisons below,
export any previous results, stop and revoke the old credential, then reset
and verify the VM before importing the target and reinstalling the skills.
See [Starting another review](/getting-started/#starting-another-review).

## Part 2: Set up your starting tool

Install and configure the tool inside the sandbox, including model access.
The starting path in [Getting started](/getting-started/) uses OpenCode with
this playbook's `security-review-repo` skill. The
[review skills guide](/discovery/review-skills/#full-repo-review-skill)
explains how to install and invoke it.

Choose a provider and credential from
[Providers and credentials](/sandbox/sbx/providers/): an API key or a
supported subscription seat. Use a model your organisation permits for this
code; [Choosing a model](/tools/choosing-a-model/) covers the selection criteria.
Confirm the selected model in the harness before the run, and record
its exact name. For other discovery tools, consult the
[tool shortlist](/tools/shortlist/).

Widen the egress allowlist only by what the tool demonstrably needs. Record
the harness, model and prompt variant so later comparisons can change one
of them at a time.

## Part 3: Run one discovery pass

Set a budget first. If you have a measured demo run, use its token use and
cost as a starting estimate, allowing for repo size. Write down the limit
and how you will enforce it:

- **API billing:** set a spend cap on the key or workspace where supported,
  or use a fixed prepaid balance. Record a manual abort threshold if no hard
  cap is available.
- **Subscription seat:** set an abort threshold in elapsed time or visible
  token count and watch the run. Record any usage or rate limit reached.
  If the account can charge for extra usage, cap that separately.
- **Provided API key:** confirm its spend cap with the key owner before
  starting. If it runs out mid-pass, record that outcome and stop.

Run the review using the
[first-run steps](/getting-started/#5-first-run). Stop after the raw findings
export; leave triage for a later exercise. If the run would exceed the
budget, use the kill switch and record why you stopped.

If the harness exposes reasoning traces (visible chain of thought, or CoT),
follow along during the run or read them afterwards. Watch for unsupported
assumptions, skipped checks, responses to blocked actions, or speculation
that the repository is a benchmark. Note anything that stands out and whether
the agent's actions or findings reflect it.

Compare the visible reasoning with tool calls and inspected code. Treat it as
supporting evidence when interpreting the run. If reasoning is unavailable,
use the tool-call history and final report instead.

With the supplied skill, the report is written to `~/out/findings.md` in the
VM. Export it with `appsec-sbx export`, then stop the VM. Keep the raw report
unchanged and read it as untrusted text. A failed or budget-limited run is
still an outcome to document.

## Part 4: Write the run report

Keep this report alongside the raw export. Use estimates where exact numbers
are unavailable and say how you obtained them.

| Field | Your run |
|---|---|
| Run date | |
| Repo size (estimated KLOC) | |
| Tech stack (languages, main frameworks) | |
| Harness and version, prompt variant, model used | |
| Budget or abort threshold set | |
| Tokens consumed and API cost, or seat usage/rate limit reached | |
| Agent runtime (wall-clock) | |
| Findings total and counts by reported severity | |
| Reasoning visible? Notable observations, with short excerpts or trace references | |
| Run completed? If stopped, why? | |

Add short notes on setup friction, refusals or safeguard interventions,
model redirects, suspected noise, blind spots and anything that surprised
you. Count interventions and note their triggers for whichever model you
used. These are first impressions; grading findings comes later.

Read your prompt's exclusions when interpreting the export. The supplied
review skill filters findings by confidence and excludes classes such as
DoS, rate limiting and outdated dependencies. Record these coverage limits
separately from gaps you noticed during the run.

Use the run report above for this discovery pass; leave triage verdicts for
the next stage.

## Optional challenges

- **Self-hosted model:** repeat the pass with a model hosted on approved
  infrastructure. Keep the harness and prompt fixed, and record setup effort,
  throughput and differences in the findings. Check hardware needs first.
- **Larger framework:** try a heavier tool from the
  [shortlist](/tools/shortlist/) and record what setup took. Keep this exercise
  within discovery scope and the same containment and budget requirements.

## What you should have at the end

- A working sandbox and evidence for the six environment checks.
- A raw findings export, or a record of where the run stopped.
- A run report with budget, runtime, findings counts and setup notes.

These records support later comparisons of tools and models and show where
setup guidance needs work. A later exercise will cover triaging the findings.
