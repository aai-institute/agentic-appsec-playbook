---
title: "No-Regret Measures: the safe-to-start baseline"
---
**Status:** v1.0, 2026-09-11. Hoisted from the working group's session 1 plan
and assignment, where it was written on 2026-09-01 and walked measure by
measure; this page is now the canonical text and the session material points
here. Tool-neutral: the [Colima guide](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/reference-sandbox-colima.md) and the
[sbx wrapper](/sandbox/sbx/) are two implementations of it, the
[threat model](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/threat-model.md) is where each measure gets its `T` and `M`
identifiers, and the [hardening checklist](/hardening/hardening-checklist/)
is what comes after it.

## Why "no-regret"

Six measures that are worth doing regardless of which tool, model provider or
use case you end up with, and that have to be in place **before the first agent
run**, not after the first incident. Deliberately lightweight: deep hardening
(agent permissions, CI integration, prompt-injection defences, monitoring of
allowed traffic) is a later step. Non-negotiable: nothing below is optional for
a pilot on your own code.

The vocabulary is OpenAI's *Agent security in the enterprise* (August 2026,
read in full for the working group): **reachable surface** (the data, systems,
actions and destinations the agent can reach) → **effective blast radius**
("the harm still possible after security controls are enforced") → **maximum
completed effect** ("the most consequential outcome the agent can produce
before another independent decision is required"). The baseline turns a coding
agent's maximum completed effect into *tokens spent and a findings file
written*. The load-bearing sentence, and the whole argument against relying on
a harness's permission prompts: "Instructions may guide behavior; independent
controls provide containment." The same guide states plainly that a harness
"does not inherently provide isolation or sandboxing; those properties depend
on the execution environment and surrounding controls."

Underneath the vocabulary sits one old principle, **least privilege**: the
agent, its user account, its credential and its network path each get the
minimum authority the task needs, and nothing that merely happens to be
convenient. OpenAI's guide states it as "constrain authority to the task";
the incident reports state it in the negative: least privilege, isolation and
strong authentication held almost everywhere, and the one place they did not
was enough. Measures 1 to 4 are least privilege applied to four different
things (execution boundary, identity, credential, egress); measures 5 and 6
bound what happens when it is nevertheless breached.

Each measure below maps to something that happened in 2026, taken from the
two cyber-evaluation incident disclosures (OpenAI/Hugging Face, April–July;
Anthropic, disclosed 2026-07-30) and from this playbook's own runs. The
incidents are not there to frighten: their common thrust is that **the
harness and its environment, not the model, were the failure surface**. A
shared credential, an allowed package mirror, a mis-set "you have no internet"
assumption were each enough.

## The six measures

### 1. An isolated runner: VM-based, not container-only, throwaway or snapshotted

- **What.** The agent, its toolchain and anything it generates run inside a
  dedicated virtual machine with a guest kernel of its own, no host directories
  mounted, rebuilt from a script or restored from a clean snapshot for every
  run.
- **Why.** Both 2026 escapes broke out of containers. OpenAI's own remediation
  mandated microVM sandboxes plus two independent network-isolation layers;
  the shared-kernel boundary is exactly the one a container does not provide.
  A daily-driver VM profile is not a dedicated one: the default Colima profile
  on the reference machine mounted the home directory writable into the guest.
- **In this playbook.** Colima layer L1; the sbx wrapper's `create` (one microVM
  per VM, clean template saved before any code or key enters, `reset` and
  `destroy`). Threat model T01, T02, T23, T29; acceptance rows R1 and R7.
- **Prove it.** The guest's mount table shows no host share (both wrappers
  check this on every entry); you have rebuilt or restored the VM once.

### 2. No production credentials in reach; scope limited to the pilot repository

- **What.** Nothing enters the VM except a sanitised copy of the repository
  under review and one capped model credential. No cloud keys, no signing
  agent, no code-host write token, no team `.env`, no committed harness
  configuration that executes. Inside the VM the same rule applies to the
  agent's identity: it runs as an unprivileged user with no sudo and no Docker
  socket, so it cannot switch the containment off or reach the guest's own
  control plane. Least privilege, applied to data and to identity.
- **Why.** On OpenAI's side of the Hugging Face incident, agents enumerated 956
  secrets after gaining host root; four private repositories were downloaded.
  In Anthropic's incidents a model extracted real infrastructure credentials
  from a real company that happened to share a name with a fictional one.
  Whatever is reachable will be found.
- **In this playbook.** The import filter (tracked files only, no `.git`, no
  `.env*`, no key material, no executable harness configuration, manifest of
  what was excluded), the tmpfs model key, the unprivileged workload user
  without sudo or a Docker socket. Threat model T04, T07–T09, T22, T25;
  rows R4 and R5.
- **Prove it.** The import manifest's excluded list is what you expect; the
  workload shell's environment holds the model key and nothing else.

### 3. Egress default-deny with a narrow allowlist

- **What.** The VM can reach the model endpoint and what the tool demonstrably
  needs (a package registry, at most), and nothing else. Not the LAN, not the
  host, not GitHub, not "the internet with a few blocks".
- **Why.** Container egress denial held in the Hugging Face incident; the
  agents left through the one sanctioned internal service, a package mirror.
  Every reachable shared service is a transitive escape path. Anthropic's
  incidents had a "no internet access" assumption that was simply not true.
  In this playbook's own runs on 2026-09-10, three different models tried to
  install the target's dependencies from PyPI despite a discovery-only
  prompt, one of them with certificate checks disabled; the allowlist decided,
  not the prompt.
- **In this playbook.** Colima layer L2 (nftables default-deny for the VM and
  its containers, hostname allowlist on a proxy); the sbx wrapper compiles a
  per-VM policy from the chosen provider profile and refuses entry if the
  policy changed. Threat model T11–T18, T21, T27; rows R2 and R3.
- **Prove it.** A direct request to a raw IP address fails from the workload
  shell and from a container; the proxy or policy log shows the denial; the
  allowed hosts are ones you can name a reason for.

### 4. Short-lived tokens; no shared credential or writable shared state across runs

- **What.** One credential per run, gone when the run stops. Two agent runs
  never share a writable location or an identity. Least privilege in time:
  authority that outlives the run, or that a second run can borrow, is
  authority the task did not need.
- **Why.** About 1,200 OpenAI agents across unrelated runs built a message
  board through a shared, writable Artifactory mirror under one shared
  credential, exchanged exploit recipes and credentials, and adopted norms. No
  exploit was needed for the coordination, only shared write access. Fixing
  the observed encoding (file contents) was bypassed via directory names;
  remediate the capability.
- **In this playbook.** One VM per provider and run; the key lives on guest
  tmpfs and is removed on `stop` and `unkey`, together with the harnesses' own
  credential stores; provider-side revocation is the second half. Threat model
  T25, T26; rows R4 and R7.
- **Prove it.** After `stop`, the key file and the harness credential files
  are absent from the guest.

### 5. A token and spend budget set before the run

- **What.** A hard cap where the platform supports it (API spend limits,
  OpenRouter key caps, prepaid gateway credit); a written abort threshold
  (elapsed time or visible token count) where it does not, which is every
  subscription seat.
- **Why.** A runaway agent loop is a cost incident as well as a safety one, and
  OpenAI's report notes that out-of-bounds behaviour rose with reasoning effort
  and run length. Budget is a safety parameter. This playbook's five runs on one
  small target cost between three cents and three dollars on API billing and an
  unmetered slice of a seat.
- **In this playbook.** Provider-side caps are set before `key`; the run record
  template asks for budget set and budget consumed; seat runs record rate-limit
  status instead. Threat model T26; row R7.
- **Prove it.** The cap exists in the provider console, or the abort threshold
  is written down, before the credential enters the VM.

### 6. A kill switch, tested

- **What.** You know how to stop the run and tear the environment down, and you
  have done it once before the first real run. The switch has two halves:
  halting the runtime does not invalidate a token that was inside it, so the
  key is revoked or rotated as well.
- **Why.** OpenAI's fix for a mis-triaged alert was default-to-halt: if
  responders cannot rule out a false positive quickly, pause the run. A switch
  nobody has exercised is a plan, not a control.
- **In this playbook.** `stop` (key and credential stores removed, VM halted,
  reproducer VMs included), `destroy`, and the provider's revocation. Threat
  model T26, T32; row R7.
- **Prove it.** Executed once: VM confirmed down, brought back, key revoked.

## What the baseline does not do

It does not decide whether a reported vulnerability is true, whether a patch is
acceptable, or whether the model's provider retains your code; it does not
watch the volume or content of traffic to the allowed endpoints, which remain
channels; it does not defend against prompt injection from the repository
under review; it does not make an intentionally offensive agent safe to run.
Those are the [hardening checklist](/hardening/hardening-checklist/), the
[triage rubric](/triage/triage-rubric/), the threat model's
[accepted risks](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/threat-model.md#10-accepted-risks), and an open problem the
playbook names rather than solves.

## The gate

Self-certify before any agent runs. This is the working group's session 1 gate;
the [Colima guide's checklist](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/reference-sandbox-colima.md#self-certification-checklist)
is the longer, implementation-specific version.

- [ ] VM-based isolated runner (not container-only), throwaway or snapshotted
- [ ] No production credentials reachable; agent runs as an unprivileged user; scope limited to the pilot repository (least privilege for data and identity)
- [ ] Egress default-deny plus a narrow allowlist you can justify host by host
- [ ] Short-lived tokens; no shared credential or writable state across parallel runs
- [ ] Token and spend budget set before the run: hard cap where supported, written abort threshold otherwise
- [ ] Kill switch tested: run stopped, environment torn down, key revoked

## Traceability

| Measure | Threat model | Acceptance rows | Colima reference | sbx wrapper |
|---|---|---|---|---|
| 1 Isolated runner | T01 T02 T23 T29 | R1 R7 | L1: dedicated vz VM, no mounts, agent user | `create` (microVM, clean template), `reset`, `destroy`, mount check on entry |
| 2 No credentials in reach | T04 T07–T09 T22 T25 | R4 R5 | agent user, manual sanitised push | filtered `import` with manifest, tmpfs `key`, unprivileged `shell` |
| 3 Egress default-deny | T11–T18 T21 T27 | R2 R3 | L2: nftables + tinyproxy allowlist | per-VM policy compiled from the provider profile, entry refused on drift |
| 4 Short-lived, unshared | T25 T26 | R4 R7 | key on tmpfs, `unkey` | `stop`/`unkey` remove key and harness credential stores; one VM per run |
| 5 Budget first | T26 | R7 | provider cap, guide text | provider cap before `key`; run record fields |
| 6 Kill switch | T26 T32 | R7 | `stop`, `destroy`, revoke | `stop` (incl. reproducers), `destroy`, revoke |

Sources: OpenAI, *OpenAI–Hugging Face Incident, Technical Report* and METR's
investigation (2026-08-26); Hugging Face, *Agent intrusion, technical timeline*;
Anthropic, *Investigating incidents in our cybersecurity evaluations*
(2026-07-30); OpenAI, *Agent security in the enterprise* (August 2026). Figures
above are as reported in those documents; the playbook's own run figures are in
the demo workspace's run records.
