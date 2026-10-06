---
title: "Triage: decide which findings matter"
description: "How the triage rubric and run observations fit together, and in which order to use them."
---

A discovery run leaves you with a raw list of findings. Triage turns that
list into decisions: which findings are real, how exploitable they are, and
which are worth proving and ultimately fixing. Each verdict comes from reading the
code within a fixed time box. Proving a finding with a test or a working
reproduction comes later, in a validation loop.

:::note[Why triage before proving?]

A proof costs far more than a verdict: agent time, model budget and a sandbox
that can run the application. Something has to choose the few findings worth
that cost.

Several frontier models allow discovery but restrict exploit
development without [gated access](/tools/choosing-a-model/#gated-cyber-models-and-access),
so triage also shows whether a tool finds real vulnerabilities when no model
will write a proof.

Lastly, an agent's proof still needs checking. In benchmark
studies, agents often demonstrated a vulnerability on a stand-in they had
built, or accepted their own output as proof of success; the rubric's
[evidence rules](/triage/triage-rubric/#evidence-rules) cover both cases.
Even when an agent proves a finding, a person checks the proof against the
real application and decides on the fix.
:::

## Two records

This section keeps two records. The rubric describes one row per finding;
run observations describe one row per run.

|               | [Triage rubric](/triage/triage-rubric/)           | [Run observations](/triage/observations/)                                 |
| ------------- | ------------------------------------------------- | ------------------------------------------------------------------------- |
| _One row per_ | Finding                                           | Run: one tool, harness and model on one repository                        |
| _Answers_     | Is this finding real, and how exploitable is it?  | What did the run produce, and what did it cost?                           |
| _You record_  | Verdict, exploitability, what decided it, minutes | Findings reported and triaged, verdict split, cost, refusals, blind spots |
| _When_        | While you triage                                  | After you finish triaging a run                                           |

The run row summarises the finding rows. Its triaged count, total minutes and
verdict split are totals over the rubric's records for that run.

## Reading order

1. Read the [triage rubric](/triage/triage-rubric/) before you start: the
   verdicts, the evidence rules and the time box.
2. Triage the run's findings and record one rubric row for each.
3. Fill in one [run observations](/triage/observations/) row for the run.
   Its last section explains which numbers a small sample can't support.
4. For a second run, repeat steps 2 and 3 and compare the two rows.

The [Triage and compare exercise](/exercises/triage-and-compare/) takes you
through these steps on your pilot repository.
