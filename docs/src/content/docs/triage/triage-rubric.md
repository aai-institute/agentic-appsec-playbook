---
title: "Triage rubric"
---
Use this rubric to select two or three findings worth checking in a
validation loop and measure the time spent on manual triage. The
[run observations guide](/triage/observations/) explains which conclusions
this limited sample can support. The
[Validate a finding exercise](/exercises/validate-a-finding/) applies the
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
| Notes | free text | what decided the verdict and who produced it; for an FP, the [reason](#decision-rules); assumptions, uncertainties and context needed by another reviewer |

## Decision rules

- <span class="value-chip value-chip--tp">TP</span> **True positive** — the
  flaw exists in the code as described and is a security issue in this
  codebase's context (not necessarily exploitable today). A real but minor
  flaw is still a TP; how urgent it is gets decided in prioritisation.
- <span class="value-chip value-chip--fp">FP</span> **False positive** — the
  finding is not a security issue in this codebase. Note one reason:
  - _not present_: the described flaw is not in the code.
  - _unreachable_: the flaw is in the code, but no input or configuration
    the codebase admits reaches it.
  - _mitigated_: a control elsewhere, such as upstream validation or a
    framework default, defends the path.
  - _quality-only_: a code-quality finding with no security relevance.
  - _test-only_: the code runs only in tests or fixtures.

  The reason keeps hallucinated findings apart from real but defended code,
  and the first three match the dismissal reasons in
  [GitLab](https://docs.gitlab.com/user/application_security/vulnerabilities/#vulnerability-dismissal-reasons)
  and [GitHub](https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-code-scanning-alerts/resolve-alerts#dismissing-alerts),
  so a row transfers to either platform.
- <span class="value-chip value-chip--investigate">needs-investigation</span>
  — plausible but not decidable within the time box. Not a failure verdict;
  the rate of these is itself a usability signal.
- <span class="value-chip value-chip--duplicate">duplicate</span> — same root
  cause and location as an already-triaged finding (including across tools,
  when triaging the second tool).

Deployment context decides a verdict where it decides whether attacker input
reaches the flaw:

- configuration and feature flags: <span class="value-chip value-chip--fp">FP</span>
  _unreachable_, or <span class="value-chip value-chip--preconditions">needs-preconditions</span>;
- who can send the input, given what the system is for;
- controls in front of the code: <span class="value-chip value-chip--fp">FP</span> _mitigated_.

How critical the system is, how sensitive its data is and how exposed it is
decide how urgent a fix is. Leave those to prioritisation.

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

### Kinds of evidence

A **witness** shows that a flaw is real. An **exploit** shows what an attacker
gains. A fix decision needs the first.

| Evidence | Produced by | Shows | Doesn't show |
|---|---|---|---|
| Traced path | Reading the code, or a data-flow query | The flaw is plausibly reachable | That the code behaves as read |
| Witness | A failing test, a crash, or a request and its response from the real application, with harmless input | The flaw is real and reachable, as tested | Impact in production |
| Counterexample | A fuzzer, symbolic execution or a model checker | The property fails for one concrete input | Anything beyond the inputs explored |
| Proof | Formal verification | The property holds or fails for every input, in the model | Whether the model matches the deployed system |
| Exploit | Turning the flaw into an attack | What an attacker gains | More than a fix decision needs |

Validation needs a witness. The evidence rules above apply to every row an
agent produces. A witness shows behaviour under the tested conditions only,
and failing to produce one does not refute the finding.

Exploit development is also the step model providers gate
([gated access](/tools/choosing-a-model/#gated-cyber-models-and-access)). The
EU Cyber Resilience Act defines an exploitable vulnerability by its "potential
to be effectively used by an adversary under practical operational conditions"
([Art. 3(41)](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202402847)).
Calling a vulnerability exploitable needs no working exploit.

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
