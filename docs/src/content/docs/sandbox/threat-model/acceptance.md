---
title: "Acceptance requirements"
description: "The outcomes and evidence required to rely on a sandbox setup, plus conditions for staging access."
---

These requirements define what a sandbox setup must achieve, regardless of
which VM or network technology implements it. They cover every entry in the
[threat catalogue](/sandbox/threat-model/catalogue/), including T20a/T20b and
T34. The [current coverage](/sandbox/threat-model/controls/) remains partial.

Meeting a requirement needs both the configured system and its operating
workflow. A product feature or a successful `appsec-sbx verify` is not enough:
that command checks entry conditions and prints versions, not every scenario
below.

## Requirements

| ID | Required outcome | Threats | Evidence needed |
|---|---|---|---|
| R1 · Host data | Only approved project data enters. No ambient host folders, identity services or shared writable stores. A VM or equivalent independent boundary surrounds execution. | T01 T02 T06 | Actual mount inspection; test files outside the intended import stay unreadable; host identity and forwarding checks. Record the accepted escape risk. |
| R2 · Reachability | No implicit guest listeners on the host, access to host services, LAN/VPN reach or third-party targets. Any staging exception meets the conditions below. | T03 T15 T16 T17 T20b T21 | Host/LAN listener tests and direct/private-address probes, including allowed hostnames resolving internally and changing addresses. |
| R3 · Network policy | Only the selected model service and necessary registries are reachable. Policy covers direct TCP, UDP, DNS, IPv4/IPv6 and container paths. | T11 T12 T13 T14 T18 T27 | Workload and container probes with proxy variables removed; upstream DNS observations; matched enforcement logs. Record what allowed APIs can still receive or do. |
| R4 · Data and credentials | Filtered import, synthetic target configuration, no code-host or registry write authority, and narrowly scoped model authority. Prefer credentials held outside the workload. | T04 T24 T25 | Import fixtures, credential-read tests, authority limits, cleanup and revocation checks. Current raw-key exposure must be recorded explicitly. |
| R5 · Independent controls | The workload cannot relax containment or carry modified configuration and tools into the next independent run. Skills enter by operator choice with recorded origin. | T07 T08 T09 T22 T23 T33 | Privilege/socket denial, effective harness settings, marker hooks/plugins, and clean-reset tests covering writable tools, settings and skill stores. |
| R6 · Safe test execution | Reproducers and targets have separate execution boundaries, restricted networks and synthetic integrations. | T19 T20a | Separate VM identity; no model key; denied network tests; target callbacks reach only local stand-ins. Do not infer an escape-proof boundary from a smoke test. |
| R7 · Bounded lifetime | Known provisioning inputs, clean starts, external stop/deadline, provider usage controls, credential revocation and deliberate retention/disposal. Provisioning uses authenticated encrypted downloads. | T23 T26 T28 T29 T32 T34 | Input versions/digests, HTTPS-only provisioning, reset canaries, deadline/stop with child workloads, spend controls and separate revocation observations. |
| R8 · Evidence and review | Containment logs are retained outside workload authority. Outputs are labelled agent-generated and reviewed before use or sharing. | T05 T10 T30 T31 | An evidence bundle with run identity, timestamps, policy, versions and hashes; untrusted-export handling; human review of findings and patches. |

Use harmless test files and dummy credentials when probing these boundaries.
Record the OS, architecture, backend, wrapper/harness versions, network setup,
command, expected result and actual result. A denial needs enough evidence
to distinguish policy enforcement from a broken test server or network outage.

Detailed commands and results belong in the
[acceptance records](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/records/sbx-acceptance.md).
Outstanding probe design is tracked in the
[backlog](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/sandbox-backlog.md#network-validation).

## Staging access: a future extension

Dynamic testing against an existing staging environment can be legitimate.
It spends some of the host's network authority, potentially including VPN
access, on a specific target. **The current wrapper has no staging-target
action (M18).** These are design requirements for adding one, not instructions
to widen today's model or registry allowlist.

| Condition | Required protection |
|---|---|
| Named target | One host and port, added and removed through a supported action; no ranges or ad hoc policy edits. |
| Scoped credentials | Staging-only, short-lived credentials for the run, revoked afterwards. Network reach is not authentication. |
| Connection evidence | Each connection recorded outside workload authority and retained with the run. |
| Safe target state | Reset/redeploy tested in advance; synthetic data and integrations; no production backend. |
| Ownership | Environment owner approves the scope and time window; monitoring staff know the test is running. |
| Limited tooling | Rate and time limits, narrow test scope, no broad scanning. |
| Complete stop procedure | Stop VMs, revoke model and staging credentials, and reset the target. Stopping cannot undo earlier side effects. |

A target sharing a production backend or requiring a jump host or access to
another network needs a separate design review. The
[dynamic testing checklist](/hardening/hardening-checklist/#6-the-intentionally-offensive-agent-open-problem--state-it-honestly)
provides further operating controls.

## When to repeat the review

- The host OS, CPU architecture, VM backend, VPN, DNS or proxy setup changes.
- The harness version or its configuration, plugin, login or update behavior changes.
- A model host, registry, skill pack or other permitted capability is added.
- A running target, containerised agent or staging environment enters the workflow.
- A new incident exposes a missing threat or a test contradicts a prior result.

Keep threat and requirement IDs stable. Update the control mapping and record
new evidence for the affected requirements. Changes to the underlying
technology can satisfy a requirement differently, but cannot silently remove it.
