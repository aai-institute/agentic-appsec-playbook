---
title: "Sandbox threat model"
description: "What the sandbox protects, where its limits are, and how to assess its controls."
---

The sandbox limits what an AI coding agent can read, change and contact while
reviewing your code. This model explains the risks it addresses and the risks
that remain. It covers the [AppSec shell](/sandbox/sbx/), operated through
the `appsec-sbx` command on your own machine.

The central limit is simple: **the model service can receive anything the
agent can read.** Isolation keeps unrelated host data out of reach. It cannot
keep the imported repository private from the service used to analyse it.

Reviewed against the wrapper source and recorded tests on **16 September
2026**. This review adds no new VM test evidence. Platform and version limits
are in the [acceptance record](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/records/sbx-acceptance.md).

## How to use this section

| Page | Question it answers |
|---|---|
| This overview | What are we protecting, and under which assumptions? |
| [Threat catalogue](/sandbox/threat-model/catalogue/) | What could go wrong at each boundary? |
| [Control coverage](/sandbox/threat-model/controls/) | Which protections exist in the current tool, and what remains open? |
| [Acceptance requirements](/sandbox/threat-model/acceptance/) | What evidence is needed before relying on a setup or changing it? |

For commands, use the [operator guide](/sandbox/sbx/). Implementation tasks
live in the [maintainer backlog](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/sandbox-backlog.md).

Identifiers let code, tests and docs refer to the same concern: `A` names an
asset, `S` a threat source, `B` a boundary, `T` a threat, `M` a measure and `R`
an acceptance requirement. Their numbers are stable references, not severity
scores or an order in which to read them.

## Scope and assumptions

One application security engineer runs an agent interactively against a
repository their organisation owns. The operator and project authors are
trusted. Dependencies, retrieved content and generated code may still cause
harm. The operator can stop the VM from a second host terminal.

The workload receives a deliberate copy of project data, a model credential
or subscription login, and access to the selected model service. Package
registry access is optional. The goal is to keep all other host files,
credentials and network access outside its reach.

This model does not cover deliberate analysis of hostile repositories, a
hostile operator, a compromised host, or unattended CI operation. Provider
retention settings and permission to send code to that provider are decisions
the organisation must make before running the tool.

## Terms used here

| Term | Meaning |
|---|---|
| Host / guest | Your computer / the Linux virtual machine (VM) running the review. |
| Harness | The program that connects the model to files and commands, such as OpenCode, Claude Code or Codex CLI. |
| Workload | The harness and everything it starts, including dependency installers and generated code. |
| Target | The repository or application being reviewed. |
| Skill | An instruction pack the operator installs for the harness to use. It may include scripts and other support files. |
| MCP | Model Context Protocol, an interface through which an agent can use tool servers. Host-connected servers can grant access beyond the VM. |
| Reproducer | A small program used to check whether a reported vulnerability is real. The wrapper provides a separate VM for running it. |
| Egress / allowlist | Outbound network traffic / the destinations that traffic is permitted to reach. |
| Control plane | The settings and services that enforce permissions, network rules and VM lifetime. |
| Provisioning / clean template | Installing tools before project data arrives / a saved VM baseline used by `reset`. |
| Residual risk | A risk that remains after a control is applied. |

## A run and its boundaries

The host wrapper creates a VM, installs one harness, restricts its network,
then saves a clean template. Only after that do you import source, install
review skills and provide credentials. Export saves an untrusted archive.
`stop` ends execution; `reset` restores the clean template for another run.
Credential revocation at the provider is a separate step.

The boundaries below describe the intended separation. DNS and destination
checks are still incomplete; see [R2 and R3](/sandbox/threat-model/acceptance/#requirements).

| Boundary | What must stay separate | Current approach |
|---|---|---|
| B0 | Host data and guest workload | VM, no project folder shares, filtered copies and mount checks. |
| B1 | Administrator and workload | An unprivileged `appsec` user with no sudo or Docker socket access. |
| B2 | Workload and external network | sbx policy outside the guest; selected destinations only. |
| B3 | Review process and generated test code | A separate reproducer VM with network denies and no model credential. |
| B4 | Workload and its own configuration | Import filtering and harness defaults; the workload can still change its home and toolchain. |
| B5 | Workload and model provider | An explicit provider profile; readable credentials and provider-side usage limits. |
| B6 | Provisioning and review time | Broader install access ends before source or credentials enter; reset uses the clean template. |
| B7 | Sandbox output and organisational decisions | Deliberate export, human triage and review before acting on findings. |

## Assets

| ID | What needs protection | Example of loss |
|---|---|---|
| A1 | Host files, credentials and identity | SSH keys, browser profiles or another repository enter a prompt. |
| A2 | Host network access | The agent reaches internal services through your LAN or VPN. |
| A3 | Model credentials | Someone else uses the API key or subscription account. |
| A4 | Code-host and registry credentials | A workload publishes a package or changes a repository. |
| A5 | Project code and vulnerability details | Unfixed findings reach an unapproved recipient. |
| A6 | Finding integrity | A reviewer trusts a fabricated finding or unsafe patch. |
| A7 | Sandbox integrity | A changed tool or setting affects this run or a later one. |
| A8 | Budget and human time | A loop consumes spend or floods the review queue. |
| A9 | Third parties and connected systems | A test sends real mail, charges a card or scans a live system. |
| A10 | Evidence | A decision relies on logs the workload changed or omitted. |

## Threat sources and priorities

These priorities reflect the interactive, owned-code use case. They are
qualitative judgments, not measured probabilities.

| Source | Why it matters here |
|---|---|
| S5 · Operator error | Importing a secret, using an admin shell or reusing a dirty VM can defeat the intended workflow. Committed developer settings can also enable tools that are inappropriate for a security run. |
| S3 · Supply chain | Project dependency installers can read credentials. Harness packages, images and skill packs also bring third-party code or instructions into the run. |
| S8 · Normal application side effects | An application may send mail, call a payment API or write to a real database when tested. |
| S2 · Content the agent reads | Dependency source, documentation and fetched pages can contain instructions that redirect the agent. |
| S1 · Agent autonomy | Scope expansion, unnecessary commands and long loops can cause harm without an attacker. |
| S6 · Offensive tooling | A wrong target address can direct a legitimate testing tool at a real system. |
| S7 · Inbound connections | A guest listener or published target may become reachable from the host or LAN. |

Import filtering and policy checks already reduce common operator mistakes.
The most consequential open work is credential exposure (T25), DNS and
private-address reachability (T13/T16), persistence in a reused VM (T23),
and a time limit enforced outside the workload (T26). Dynamic testing adds
the application's side effects (T20a) to that list.

## Accepted risks

For this design case, the following risks remain with the operator and organisation:

- A hypervisor or kernel vulnerability may break isolation (T02). Keep hosts
  and guest baselines current.
- Approved model and registry connections can carry readable project data
  (T12/T14/T27). A hostname allowlist does not restrict API methods, accounts
  or the models a gateway uses. TLS encryption also limits traffic inspection.
- Credentials available to the workload can be copied or used (T25). Use
  limited authority, provider-side budgets where available, and revocation.
  A proxy that hides the key would still delegate some authority.
- Project data and findings persist on VM disk until reset or destruction
  (T32). Host disk encryption and deliberate disposal are required; deletion
  is not proof of secure erasure and does not remove host exports or backups.
- The provider sees submitted code. Its retention policy, account settings,
  refusals and outages are outside sandbox enforcement.

Unresolved network checks are validation gaps, not accepted proof of
containment. Review the [coverage limits](/sandbox/threat-model/controls/)
before relying on this setup for more sensitive work.
