---
title: "Triage rubric"
---
Use this rubric to select two or three findings worth checking in a
validation loop and measure the time spent on manual triage. The
[run observations guide](/triage/observations/) explains which conclusions
this limited sample can support. The
[Triage and compare exercise](/exercises/triage-and-compare/) applies the
rubric to a first discovery pass.

**Budget:** ≤ 10 minutes per finding, **~3 hours per tool in total**. Go
highest tool-reported severity first; stop at the cap or once you have your
candidates and a feel for the noise, whichever comes first. If a finding can't
be decided in 10 minutes, mark it <span class="value-chip value-chip--investigate">needs-investigation</span> and move on.

## Per-finding fields

| Field | Values | Notes |
|---|---|---|
| Finding ID | tool's ID or hash | stable reference for the full-loop exercise |
| Tool / version | free text | include model/backend used |
| Verdict | <span class="value-chips"><span class="value-chip value-chip--tp">TP</span><span class="value-chip value-chip--fp">FP</span><span class="value-chip value-chip--investigate">needs-investigation</span><span class="value-chip value-chip--duplicate">duplicate</span></span> | see decision rules below |
| Tool severity | as reported | used for ordering only — no re-rating |
| Exploitability | <span class="value-chips"><span class="value-chip value-chip--reachable">reachable</span><span class="value-chip value-chip--preconditions">needs-preconditions</span><span class="value-chip value-chip--theoretical">theoretical</span></span> | TPs only, one line naming what you checked (see [exploitability](#exploitability)) — this is what picks the loop candidates |
| Triage time | minutes | feeds the human-cost picture |
| Notes | free text | what decided the verdict and who produced it; assumptions, uncertainties and context needed by another reviewer |

## Decision rules

- <span class="value-chip value-chip--tp">TP</span> **True positive** — the
  flaw exists in the code as described and is a security issue in this
  codebase's context (not necessarily exploitable today).
- <span class="value-chip value-chip--fp">FP</span> **False positive** — the
  described flaw is not present, or the "vulnerable" path cannot be reached by
  any input/config the codebase admits.
- <span class="value-chip value-chip--investigate">needs-investigation</span>
  — plausible but not decidable within the time box. Not a failure verdict;
  the rate of these is itself a usability signal.
- <span class="value-chip value-chip--duplicate">duplicate</span> — same root
  cause and location as an already-triaged finding (including across tools,
  when triaging the second tool).
- Code-quality findings with no security relevance are
  <span class="value-chip value-chip--fp">FP</span> for our purposes — note
  "quality-only" in Notes so they're distinguishable from hallucinations.

## Evidence rules

Tool reports often state their own confidence: "confirmed", "verified",
"reproduced". These rules decide what supports a verdict. They come from
studies of automated pipelines and benchmarks, not of people triaging
findings, so treat them as cautious defaults.

1. **A tool's label is not evidence.** Base the verdict on evidence you can
   check yourself, such as the code. Evidence counts only if neither the
   tool's own output nor data an attacker controls decided it. Record in
   Notes what decided the verdict and who produced it. If the code doesn't
   decide it within the time box, mark the finding <span class="value-chip value-chip--investigate">needs-investigation</span>.
   Agents that check their own work have accepted their own echoed output as
   proof of success ([Lohrasbi et al.](https://arxiv.org/abs/2609.28572)).
   Automated checks that read what the target returns can be forged by
   whoever controls the target ([Fujiyama and Shamim](https://arxiv.org/abs/2609.24200)).
2. **A reproduction needs the real application.** Count a reported
   reproduction only if its artifact comes from the real, unmodified
   application: a request and the response it produced, a crash, or a
   callback. A mock server, a harness the tool built, or a re-run of the
   tool's own script doesn't count. In one benchmark, close to half of the
   agent runs produced such a stand-in, with convincing output that re-ran
   cleanly ([He et al.](https://arxiv.org/abs/2609.34450)). Without a
   qualifying artifact, triage the finding from the code.
3. **Trace the path yourself.** Agents' reports cite the flawed lines more
   reliably than the path from attacker input to them or the point where
   harm occurs ([Li et al.](https://arxiv.org/abs/2609.32601)). For a TP,
   check that path in the code and name it in the Exploitability line.

### Exploitability

| Value | What the line names |
|---|---|
| <span class="value-chip value-chip--reachable">reachable</span> | The path from attacker input to the flaw, traced in the code |
| <span class="value-chip value-chip--preconditions">needs-preconditions</span> | The path, and the configuration, role or state it depends on |
| <span class="value-chip value-chip--theoretical">theoretical</span> | The flaw, and why you found no attacker path within the time box |

## Procedure

1. Export the tool's findings (one row each).
2. Triage in the tool's reported-severity order, highest first, until the cap.
3. Triage solo; findings that stay <span class="value-chip value-chip--investigate">needs-investigation</span> are candidates for
   a second look with a colleague.
4. Fill in the [run observations](/triage/observations/) row for the run,
   and note your 2–3 "would most want proven" candidates.

## Sources

- Fujiyama and Shamim, [_Forgeable Confirmation in Automated Computer Security
  Testing: Deterministic Rules versus AI Judges_](https://arxiv.org/abs/2609.24200)
  (preprint, 2026-09-21)
- He et al., [_ReproBench: Benchmarking LLM Agents on Reproducing Vulnerability
  From Scratch_](https://arxiv.org/abs/2609.34450) (preprint, 2026-09-28)
- Li et al., [_VulContextBench: A Benchmark for Security Context Retrieval in
  Coding Agents_](https://arxiv.org/abs/2609.32601) (preprint, 2026-09-26)
- Lohrasbi et al., [_Where Cyber Agents Struggle: Bottleneck Analysis of
  Multi-Stage LLM Agents_](https://arxiv.org/abs/2609.28572) (FPS 2026;
  preprint, 2026-09-23)
