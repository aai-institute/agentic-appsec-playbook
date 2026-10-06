---
title: "2 · Triage and compare"
description: Triage the first pass's findings, run a second pass that changes one thing, and pick the findings worth proving.
---

**Goal:** Triage the raw findings from your
[first discovery pass](/exercises/first-discovery-pass/) with the
[triage rubric](/triage/triage-rubric/). Then run a second pass that changes
one thing, triage it the same way, and pick two or three findings worth
proving.

This exercise covers triage and comparison only. Leave proofs of
vulnerability and fixes for later exercises. The triage time you record here
is the baseline that a validation loop has to improve on.

**You need:** the raw findings export and run report from the first
discovery pass. If that run failed or its export is unusable, repeat the
first pass, then choose the [model change](#change-the-model) below, which
reuses the same setup.

## Part 1: Triage the first-pass findings

Apply the [triage rubric](/triage/triage-rubric/) to the raw export. Work in
the tool's reported-severity order, highest first. For each finding, record:

- The verdict: <span class="value-chip value-chip--tp">TP</span>, <span class="value-chip value-chip--fp">FP</span>, <span class="value-chip value-chip--investigate">needs-investigation</span> or <span class="value-chip value-chip--duplicate">duplicate</span>.
- For a <span class="value-chip value-chip--tp">TP</span>, one exploitability line that names the path you checked.
- The minutes it took.
- What decided the verdict, following the
  [evidence rules](/triage/triage-rubric/#evidence-rules).

Read the export as untrusted text. A finding the tool calls "confirmed" still
needs your own check.

Stop after about three hours, or once you have two or three findings you
would want proven and a feel for the noise, whichever comes first. This is
deliberately not a complete grading pass. Triage on your own; findings that
stay <span class="value-chip value-chip--investigate">needs-investigation</span> are candidates for a second look with a colleague.

Record the total triage time and how many findings you got through, out of
how many.

## Part 2: Run a second pass that changes one thing

Change exactly one of the harness, the model or the prompt, so that the two
runs can be compared. Keep the repository, the sandbox setup and the budget
rules from the first pass.

### Change the harness

Keep the model and change the tool that drives it. The
[providers page](/sandbox/sbx/providers/) lists which harness each
`create` option installs:

- OpenCode and [Pi](/sandbox/sbx/providers/#pi-on-an-api-key) on the same
  API key and model.
- OpenCode on an Anthropic key and Claude Code on a seat, with the same
  Claude model.

Changing the harness means a new VM: `destroy`, then `create`.

### Change the prompt or skill

Keep the harness and model and replace the review skill:

- The [Mantis](/discovery/review-skills/#mantis) text-only stages. Record the
  stages you skipped.
- The [Defending Code reference harness](/discovery/review-skills/#defending-code-reference-harness)
  skills with `/vuln-scan`.

See the [tool shortlist](/tools/shortlist/) for what each one covers.

### Change the model

Keep the harness and prompt and switch the model, for example from a
closed frontier model to an open-weight one. See
[Choosing a model](/tools/choosing-a-model/) for the options and what your
organisation must permit.

### Run and triage the second pass

Before the pass, export the earlier results, revoke the old credential, and
reset and check the VM. See
[Starting another review](/getting-started/#starting-another-review). Set the
budget and kill switch as in the
[first pass](/exercises/first-discovery-pass/#part-3-run-one-discovery-pass).

Run one pass, export the raw findings and write a run report for it. Then
triage the export with the same rubric and the same time cap. Mark a finding
<span class="value-chip value-chip--duplicate">duplicate</span> when it matches one from the first pass: same root cause and
location.

## Part 3: Record and choose

Record one [run observations](/triage/observations/) row per pass, and
compare the two.

Then choose the **two or three findings you would most want proven**:
<span class="value-chip value-chip--reachable">reachable</span> or <span class="value-chip value-chip--preconditions">needs-preconditions</span> TPs of real consequence. For each, keep
the path you named and what a proof would have to show. These are the
candidates for a validation loop.

Also note:

- Findings still marked <span class="value-chip value-chip--investigate">needs-investigation</span>, with the weakness class and
  one line each.
- Any rubric rule that did not work in practice, with a proposed fix. Send
  these through the [feedback channel](/#feedback-and-questions).

## What you should have at the end

- Triage records for both passes, with time per finding.
- Two run observations rows, one per pass, that differ in one stated way.
- Two or three findings worth proving, each with the path you checked.
- A short list of unresolved findings and rubric problems.
