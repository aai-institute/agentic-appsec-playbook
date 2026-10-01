---
title: "1 · First discovery pass"
description: Set up a sandbox, run one security discovery pass on a pilot repository, and record the results.
---

:::note[If you have used Getting started]
You can start with this exercise. It uses the same setup and review steps as
the [first security review tutorial](/getting-started/), then asks you to
record the results from your pilot repository.

If you already completed that tutorial on the same repository, check your
run against Parts 1–3 below. If it meets those requirements, use its findings
for [Part 4: Write the run report](#part-4-write-the-run-report). You do not
need to repeat the run.
:::

**Goal:** Run one security review inside a sandbox. Keep the raw findings
and a short run report so you can compare later runs.

This exercise covers discovery only. Leave triage, testing whether findings
are real vulnerabilities, and fixes for later exercises.

## Part 1: Set up the sandbox

Follow the setup steps in [Getting started](/getting-started/). Use the
[appsec-sbx wrapper](/sandbox/sbx/) to import a copy of your pilot repo into
a disposable Docker sandbox VM. Check the copy for secrets and unrelated
files before importing it. The agent works on that copy.

Before starting the agent, complete the
[environment self-check](/sandbox/no-regret-measures/#check-your-environment).

The provided `appsec-sbx` wrapper incorporates these principles through VM
isolation, filtered imports, network policies and stop/reset commands.

Complete the [kill-switch rehearsal](/sandbox/sbx/lifetime/#test-the-kill-switch)
before the first discovery pass. It ends with a clean reset. Then import the
target and skills, and supply a fresh credential for the review. Record the
evidence requested by the self-check. Complete all six checks before running
any agent.

Before each later independent pass, including the optional comparisons below:

1. Export any previous results.
2. Stop the run and revoke the old credential.
3. Reset and check the VM.
4. Import the target and reinstall the skills.

See [Starting another review](/getting-started/#starting-another-review).

## Part 2: Set up your starting tool

Install and configure the tool inside the sandbox, including model access.
[Getting started](/getting-started/) uses OpenCode with this playbook's
`security-review-repo` skill. The
[review skills guide](/discovery/review-skills/#full-repo-review-skill)
explains how to install and use it. For other discovery tools, see the
[tool shortlist](/tools/shortlist/).

Choose a provider and an API key or supported subscription seat from
[Providers and credentials](/sandbox/sbx/providers/). Use a model your
organisation permits for this code. See
[Choosing a model](/tools/choosing-a-model/) for help choosing one.
Confirm the model in the review tool before the run, and record its exact name.

Allow extra network destinations only when the tool needs them. Record the
review tool (harness), model and prompt variant. In later comparisons,
change one of these at a time.

## Part 3: Run one discovery pass

Set a budget first. If you have measured a demo run, use its token count and
cost to estimate your budget. Account for the size of your repo. Write down
the limit and how you will enforce it:

- **API billing:** set a spending cap on the key or workspace where supported,
  or use a fixed prepaid balance. If there is no hard cap, write down a limit
  for stopping the run.
- **Subscription seat:** set a limit in elapsed time or visible token count,
  and watch the run. Record any usage or rate limit reached. If the account
  can charge for extra usage, cap that separately.
- **Provided API key:** check the spending cap with the key owner before you
  start. If the key runs out mid-pass, stop and record that outcome.

Follow the [first-run steps](/getting-started/#5-first-run). Stop after
exporting the raw findings; leave triage for a later exercise. If the run
would exceed the budget, use the kill switch and record why you stopped.

If the tool shows reasoning traces, follow them during the run or read them
afterwards. Watch for:

- Assumptions without evidence.
- Skipped checks.
- How the agent responds to blocked actions.
- Guesses that the repository is a benchmark.

Note anything that stands out. Does it show up in the agent's actions or
findings? Compare the visible reasoning with tool calls and the code the
agent inspected. Use it as supporting evidence when you review the run.
If reasoning is unavailable, use the tool-call history and final report.

The supplied skill writes its report to `~/out/findings.md` in the VM.
Export it with `appsec-sbx export`, then stop the VM. Keep the raw report
unchanged and read it as untrusted text. Record the outcome even if the run
fails or stops at the budget limit.

## Part 4: Write the run report

Open the Report Template panel below to add notes, or print it and write
by hand. Keep a copy alongside the raw export. If you estimate a number,
say how you obtained it.

<details class="run-report-panel">
  <summary>Report Template</summary>
<figure class="run-report-template" aria-labelledby="run-report-caption">
  <div class="run-report-fields">
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-1">Run date</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-1"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-2">Repo size (estimated thousands of lines of code, or KLOC)</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-2"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-3">Tech stack: languages and main frameworks</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-3"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-4">Review tool (harness) and version</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-4"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-5">Prompt variant and exact model name</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-5"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-6">Budget or limit for stopping</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-6"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-7">Tokens used and API cost, or seat usage/rate limit reached</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-7"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-8">Elapsed time for the agent run</div>
      <div class="run-report-entry" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-8"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-9">Total findings and counts by reported severity</div>
      <div class="run-report-entry run-report-entry--roomy" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-9"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-10">Reasoning visible? Notes with short excerpts or trace references</div>
      <div class="run-report-entry run-report-entry--roomy" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-10"></div>
    </div>
    <div class="run-report-field">
      <div class="run-report-label" id="run-report-field-11">Run completed? If stopped, why?</div>
      <div class="run-report-entry run-report-entry--roomy" contenteditable="plaintext-only" role="textbox" aria-multiline="true" aria-labelledby="run-report-field-11"></div>
    </div>
  </div>
  <figcaption id="run-report-caption">Run report · Fill in online or print and write by hand.</figcaption>
</figure>
</details>

Add short notes on:

- Setup problems.
- Refusals, safeguard actions and model redirects. Count these events and
  note what triggered them, whichever model you used.
- Suspected noise, blind spots and anything that surprised you.

These are first impressions. Grading findings comes later.

Check what your prompt excludes before you interpret the export. The supplied
review skill filters findings by confidence. It excludes classes such as
denial of service (DoS), rate limiting and outdated dependencies. Record these
limits separately from gaps you noticed during the run.

Use this report for the discovery pass. Leave triage verdicts for the next stage.

## Optional challenges

- **Self-hosted model:** repeat the pass with a model hosted on approved
  infrastructure. Keep the review tool and prompt fixed. Record setup effort,
  throughput and differences in the findings. Check hardware needs first.
- **Larger framework:** try a heavier tool from the
  [shortlist](/tools/shortlist/) and record what setup took. Stay within
  discovery scope and follow the same sandbox and budget requirements.
- **Adapt the review skill:** read the skill's
  [instructions](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/skills/security-review-repo/SKILL.md).
  Note its confidence threshold, exclusions, vulnerability categories and
  output format. Write down what your repository needs that the prompt misses.
  This could be a framework the categories miss or an excluded class you
  want to review.

  To test an idea, pass extra focus, for example
  `/security-review-repo focus on the payment service`. Or copy the skill
  under a new name and change one part. Use
  [`appsec-sbx skills`](/sandbox/sbx/commands/#skills) to install the modified
  skill in the sandbox. Keep the original unchanged so you can compare runs.
  Record the variant in the run report.

## What you should have at the end

- A working sandbox and evidence for the six environment checks.
- A raw findings export, or a record of where the run stopped.
- A run report with budget, runtime, findings counts and setup notes.

These records help you compare tools and models in later runs. They also show
where the setup guidance needs work. A later exercise will cover triage.
