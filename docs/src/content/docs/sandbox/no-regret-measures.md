---
title: "A safe environment for experiments"
description: The six measures that must hold before an agent runs on your code, and the two principles behind them.
---

A security agent wants the same access an attacker would. It runs shell
commands, reads every file it can reach, installs what it needs and sends
parts of your code to a model provider. On a laptop it does all of that as
you, with your keys, your other repositories and your network.

A short local experiment is no exception. Agents routinely install a
repository's dependencies before they read it, which reaches the internet and
runs package install hooks under your account. Ordinary behaviour is enough to
cost you a bad afternoon: a wrong path in a cleanup command, a dependency
pulled from the wrong index, a loop that spends the month's budget overnight.

Six measures reduce the risks of a first run. They apply regardless of tool,
model provider or use case, which is what makes them **no-regret**. On a fresh
machine they cost about an hour, most of it waiting for an install. All six
have to be in place before the first agent run, and none is optional for a
pilot on your own code.

The baseline is deliberately lightweight. Guidance on deeper hardening will
follow: agent permissions, CI integration, prompt-injection defences and
monitoring of allowed traffic.

The [sbx wrapper](/sandbox/sbx/) provides VM isolation, filtered import,
network policies and stop/reset commands. You must check imported code for
secrets, approve the provider's access to it, manage credentials and budgets,
test the kill switch and reset between independent reviews. The
[control mapping](/sandbox/threat-model/controls/#mapping-the-six-no-regret-measures)
details what the wrapper checks and where its coverage remains incomplete.

The text below is tool-neutral. Each measure says what must hold and why, and
the self-check at the end names the evidence you gather on any implementation.

## Why these six

The vocabulary comes from OpenAI's _Agent security in the enterprise_ (August
2026), which is worth reading in full:

- **Reachable surface**: the data, systems, actions and destinations the agent
  can reach.
- **Effective blast radius**: "the harm still possible after security controls
  are enforced".
- **Maximum completed effect**: "the most consequential outcome the agent can
  produce before another independent decision is required".

The baseline limits the agent's access to host files, credentials and network
destinations. Within those limits, the agent can still change VM files, use
its model credential to make billable requests and send readable data to
allowed services. Findings and generated code can also be wrong or harmful;
review them before acting on them. These effects remain possible without
another approval from you. See the
[remaining risks](/sandbox/threat-model/#accepted-risks).

The same guide explains why a harness's permission prompts cannot replace
these measures: "Instructions may guide behavior; independent controls provide
containment." A harness "does not inherently provide isolation or sandboxing;
those properties depend on the execution environment and surrounding
controls."

One old principle underlies the vocabulary: **least privilege**. The agent, its
user account, its credential and its network path each get the minimum
authority the task needs. OpenAI's guide states it as "constrain authority to
the task". The incident reports show the cost of a single gap. Least
privilege, isolation and strong authentication held almost everywhere, and the
one place they did not was enough.

A second principle shapes how that authority arrives: **limit ambient
authority**. Authority is ambient when a program holds it by virtue of where it
runs. A process on your laptop reads every file your account can read and opens
a socket to any address your network can reach, without being granted either.
Least privilege decides how much authority the agent gets. Limiting ambient
authority decides how it gets there, by explicit handover of one resource at a
time.

Measures 1 to 4 apply both principles to four things: execution boundary,
identity, credential, egress. Each converts what the agent could reach by
default into what someone handed it deliberately. Measures 5 and 6 limit
spend and let you stop a run. They cannot undo data disclosure or other
effects that have already occurred.

Each measure maps to something that happened in 2026: the cyber-evaluation
incidents disclosed by OpenAI and Hugging Face (April to July) and by
Anthropic (2026-07-30), and this playbook's own runs. Their common thrust is
that the harness and its environment were the failure surface. A shared
credential, an allowed package mirror and a mistaken "you have no internet"
assumption were each enough.

The threat model's
[control mapping](/sandbox/threat-model/controls/#mapping-the-six-no-regret-measures)
maps each measure to the threats it answers, the acceptance rows that test it,
and the current implementation's limits.

## The six measures

### 1. A dedicated, disposable VM

#### What

The agent, its toolchain and everything it generates run inside a dedicated
virtual machine with its own guest kernel. No host directories are mounted.

The VM is rebuilt from a script or restored from a clean snapshot before
every independent review, including repeat discovery passes and tool/model
comparisons. An interrupted review of the same target may resume with its
existing state. With `appsec-sbx`, use `reset` before a new review; replacing
the imported source alone leaves other state in place. See
[reset requirements](/sandbox/sbx/lifetime/#reproducers-reset-and-destroy).

#### Why

Both 2026 escapes broke out of containers, which share the host kernel.
OpenAI's remediation mandated microVM sandboxes plus two independent
network-isolation layers.

A daily-driver VM does not qualify either. The default profile of a common
desktop VM tool mounted the home directory writable into the guest.

### 2. No production credentials in reach

#### What

Two things enter the VM: a sanitised copy of the repository under review and
one capped model credential. No cloud keys, signing agent, code-host write
token, team `.env` or committed harness configuration that executes.

Inside the VM the agent runs as an unprivileged user with no sudo and no
Docker socket, so it cannot switch the containment off or reach the guest's
control plane. This is least privilege applied to data and to identity.

#### Why

In the Hugging Face incident, OpenAI's agents enumerated 956 secrets after
gaining host root and downloaded four private repositories.

In Anthropic's incidents a model extracted real infrastructure credentials
from a real company that shared a name with a fictional one. Whatever is
reachable will be found.

### 3. Egress default-deny

#### What

The VM reaches the model endpoint and what the tool demonstrably needs, at
most a package registry. The LAN, the host, GitHub and the rest of the
internet stay out of reach.

#### Why

Container egress denial held in the Hugging Face incident. The agents left
through the one sanctioned internal service, a package mirror. Every
reachable shared service is a transitive escape path. Anthropic's incidents
rested on a "no internet access" assumption that was false.

In this playbook's own runs on 2026-09-10, three models tried to install the
target's dependencies from PyPI despite a discovery-only prompt, one of them
with certificate checks disabled. The allowlist blocked them.

### 4. Short-lived, unshared credentials

#### What

One credential per run, gone when the run stops. Two agent runs never share a
writable location or an identity.

Authority that outlives the run, or that a second run can borrow, exceeds what
the task needed.

#### Why

About 1,200 OpenAI agents across unrelated runs built a message board on a
shared, writable Artifactory mirror under one shared credential. They
exchanged exploit recipes and credentials and adopted norms. The coordination
needed only shared write access.

A fix that blocked the observed channel, file contents, was bypassed through
directory names. Remove the capability itself.

### 5. A budget set before the run

#### What

A hard cap where the platform supports one: API spend limits, OpenRouter key
caps, prepaid gateway credit.

No subscription seat supports such a cap. There you write down an abort
threshold instead, in elapsed time or visible token count.

#### Why

A runaway agent loop is a cost incident and a safety incident. OpenAI's report
notes that out-of-bounds behaviour rose with reasoning effort and run length,
so budget is a safety parameter.

This playbook's five runs on one small target cost between three cents and
three dollars on API billing, plus an unmetered slice of a seat.

### 6. A kill switch, tested

#### What

You know how to stop the run and tear the environment down, and you have done
it once before the first real run.

The switch has two halves. Halting the runtime leaves a token that was inside
it valid, so the key is revoked or rotated as well.

With `appsec-sbx`, complete the
[kill-switch rehearsal](/sandbox/sbx/lifetime/#test-the-kill-switch) before
importing code for the first review. Test stopping a harmless command and
revoking its credential, then reset before supplying the review credential.

#### Why

OpenAI's fix for a mis-triaged alert was default-to-halt: if responders cannot
rule out a false positive quickly, pause the run. Until someone has exercised
the switch, it is only a plan.

## Out of scope

The baseline leaves these questions open:

- Whether a reported vulnerability is true and whether a patch is acceptable.
- Whether the model's provider retains your code, and the volume or content
  of traffic to the allowed endpoints, which remain channels: the threat
  model's [accepted risks](/sandbox/threat-model/#accepted-risks).
- Prompt injection from the repository under review. The baseline does not
  prevent it. Removing ambient authority bounds the effective blast radius of
  an injection that succeeds.
- Making an intentionally offensive agent safe to run remains an open problem.

## Check your environment

Self-certify before any agent runs. Each line names a measure and the
evidence that it holds.

- [ ] **A dedicated, disposable VM.** The runner is a VM with its own kernel.
      The guest's mount table shows no host share. You have rebuilt or restored
      the VM once.
- [ ] **No production credentials in reach.** The list of what the import
      excluded matches what you expect. The agent's shell environment holds the
      model key and nothing else. The agent has no sudo and no Docker socket.
- [ ] **Egress default-deny.** A request to a raw IP address fails from the
      agent's shell and from a container. The proxy or policy log shows the
      denial. You can name a reason for every allowed host.
- [ ] **Short-lived, unshared credentials.** After the run stops, the key file
      and the harness's own credential files are absent from the guest. Parallel
      runs share no credential and no writable state.
- [ ] **A budget set before the run.** The cap exists in the provider console,
      or the abort threshold is written down, before the credential enters the
      VM.
- [ ] **A kill switch, tested.** Executed once: VM confirmed down, brought
      back, key revoked.

## Sources

- OpenAI, [_OpenAI – Hugging Face Incident Technical Report_](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf)
  (2026-08-26)
- METR, [_Brief independent investigation of agents' behavior, reasoning and
  collaboration in the OpenAI / Hugging Face hacking incident_](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/)
  (2026-08-26)
- Hugging Face, [_Anatomy of a Frontier Lab Agent Intrusion: A Technical
  Timeline of the July 2026 Incident_](https://huggingface.co/blog/agent-intrusion-technical-timeline)
  (2026-07-27)
- Anthropic, [_Investigating three real-world incidents in our cybersecurity
  evaluations_](https://www.anthropic.com/research/investigating-incidents-cybersecurity-evals)
  (2026-07-30)
- OpenAI, [_Agent security in the enterprise_](https://openai.com/business/learn/agent-security-enterprise/)
  (August 2026, sign-up required)

Figures above are as reported in those documents. The playbook's own run
figures are in the demo workspace's run records.
