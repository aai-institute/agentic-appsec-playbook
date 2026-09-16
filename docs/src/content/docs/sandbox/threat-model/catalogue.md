---
title: "Threat catalogue"
description: "Stable threat identifiers, the current sbx controls, and the risks that remain."
---

Read the [scope and terms](/sandbox/threat-model/) first. Each row names a
failure, the assets at risk, and the current response in `appsec-sbx`.
Measure IDs link the catalogue to the [control coverage](/sandbox/threat-model/controls/).
Implementation and test status are assessed as of 16 September 2026.

Controls reduce risk. A row with a control is not automatically a closed
threat; the final column records its limits. Asset IDs refer to the
[asset table](/sandbox/threat-model/#assets).

## B0: Host and guest

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T01 | Shared host folders expose unrelated files or credentials (A1). | Creation omits workspace and skill shares; entry checks inspect actual mounts. M20. | sbx-generated hosts and resolver files remain shared. Checks run on entry, not continuously. |
| T02 | A hypervisor or guest-kernel bug permits escape (A1/A2). | A VM provides the outer execution boundary. | Accepted risk; patching and baseline refresh remain necessary. M6. |
| T03 | A guest listener becomes reachable from host tools or browsers (A1/A9). | Entry checks refuse published ports. M4. | Repeat listener tests from host and LAN on each supported setup. An empty port inventory alone is not a reachability test. |
| T04 | Import carries secrets or unrelated data into the review (A1/A3/A4). | Tracked-file import excludes common secret files, Git metadata and agent settings; it records file hashes. M3/M22. | Exclusions are not a secret scanner. A tracked source file may contain credentials; `put` is also an explicit data grant. |
| T05 | Output attacks the terminal, viewer or next tool (A1/A6). | Export saves an archive without extracting it; the operator must review it as untrusted. M3/M8. | No content sanitisation. Interactive terminal output and manually extracted files remain attack paths. |
| T06 | Host identity is copied into the guest (A1). | Neutral workload account, clean entry environment, no host home share or SSH-agent forwarding. M20. | Source, skills and explicit copies may contain identity. A full identity-canary check remains part of R1. |

## B1: Administrator and workload

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T07 | The workload disables containment (A7). | No workload sudo; network policy and its management remain outside the guest. Entry checks reject policy drift. M20. | Guest privilege escalation still threatens guest data and tools. Host administration is trusted. M6. |
| T08 | Docker socket access gives the workload administrator authority (A7). | Workload Docker access is denied and checked on entry. | Running an agent from `admin` bypasses the workload user boundary. |
| T09 | Operator runs the harness with administrator rights (A7). | `shell`, `agent` and `exec` enter as `appsec` with a clean environment. | `admin` remains available for trusted maintenance. Keep agents out of that shell. M12. |
| T10 | The workload alters or selectively presents evidence (A10). | sbx policy logs are outside the workload; import and skill manifests live on the host. M7. | Reports and harness transcripts are workload-writable. No complete evidence bundle is collected automatically. |

## B2: Workload and network

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T11 | Direct outbound traffic leaks data or fetches code (A3/A5). | Policy admits the provider profile and chosen registries; direct-IP and unlisted-host probes have recorded denials. M1/M2/M21. | Full transport, address-family and container-path coverage remains incomplete. |
| T12 | Allowed services receive data or provide unwanted code (A3/A5). | One provider profile; optional named registries; no general GitHub grant. M1/M2. | Model APIs and registries remain data channels. No publish credential does not imply read-only requests. A mirror is still an allowed recipient. |
| T13 | DNS queries carry data outside the allowlist (A3/A5). | Recorded Windows/Linux tests blocked unlisted names; allowed names resolved. M5. | Earlier results differed. Upstream observation, TCP/UDP, alternate resolvers and container paths remain unverified. This also applies to reproducer VMs. |
| T14 | TLS or hostname tricks conceal the actual recipient or request (A5). | Hostname policy narrows destinations. | TLS opacity is accepted for this design; it is not proof against domain fronting or mismatched request hostnames. TLS inspection, M10, is deferred. |
| T15 | The workload reaches host services, LAN or VPN destinations directly (A1/A2). | Explicit host-name and IPv4/IPv6 address denies; tested direct private-address requests were blocked. | Host network and VPN changes require new probes. See T16 for access through an allowed hostname. |
| T16 | An allowed hostname resolves to a private or host address (A2). | Direct address denies exist. M19. | These do not establish denial after an allowed hostname resolves. Private-address resolution and address changes need dedicated tests and enforcement. |
| T17 | Connections from the LAN reach the guest (A9). | No published ports are admitted. M4. | Verify both host and LAN paths for the actual backend and network. |

## B3: Generated code and targets

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T18 | Container traffic bypasses the primary workload's network rules (A5/A9). | Workload has no Docker access. Separate reproducer VMs receive a deny-all network policy. M9/M21. | Admin-started containers require their own probes; ordinary workload tests do not establish container-path coverage. |
| T19 | Generated reproducer code escapes its execution environment (A7). | Host-created reproducer VM, separate from the review VM, without a model key. M9. | VM escape remains T02. Code run in the primary review shell shares its data and authority. No additional gVisor boundary is credited. |
| T20a | Testing triggers real mail, payments, database writes or webhooks (A2/A8/A9). | Import excludes common environment files; a reproducer can run under network denies. M3/M9. | Synthetic configuration and local service stand-ins are still required. No general dynamic-target workflow enforces these today; allowed APIs remain reachable in the primary. |
| T20b | A vulnerable target is exposed outside the VM (A2/A9). | Entry checks refuse published ports. M4. | Recheck after target setup; inbound probes remain required. |
| T21 | A test tool is pointed at an unintended real system (A2/A9). | The standard profile grants model and registry services only. | No staging-target action exists. M18 is deferred; adding an arbitrary endpoint is not an approved staging workflow. |

## B4: Workload and its configuration

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T22 | Repository or account settings activate unwanted tools, hooks or plugins (A7). | Import filters agent settings; bootstrap seeds harness defaults; host MCP inventory must be empty. M3/M11/M23. | Settings and environment variables are not an immutable permission boundary. Files created later, account settings and new harness versions need review. |
| T23 | Changed tools or configuration persist into the next review (A7). | `reset` recreates the VM from the template saved before import and credentials. M13. | Reset is explicit. Home directories and the installed toolchain remain workload-writable; `import --replace` does not clear them. M12/M16. |
| T24 | Dependency installation runs code that reads credentials or changes tools (A3/A7). | Registry access can be narrowed or removed. Skills enter by an operator action. M1/M14. | Dependencies run with workload authority, including access to model credentials. M17. |
| T33 | A skill pack introduces unsafe instructions or scripts (A6/A7). | Host-side `skills` import filters files and records the source commit and hashes without granting guest GitHub access. M14. | Instructions and support files remain untrusted. Branches can move, local edits are allowed, and the host URL fetch has no size cap. Review and pin the pack. |

## B5: Workload and model provider

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T25 | A process steals or uses the model credential (A3/A4). | API keys use a memory-backed file; `unkey` removes known stores; `stop` attempts cleanup on running VMs. SSH forwarding is refused. | Keys remain readable. Idle stop retains login stores; a later `stop` skips their cleanup. Cleanup errors during `stop` are ignored. Copied credentials retain authority. Revocation is separate. M17/M23. |
| T26 | A loop exceeds time or spending limits (A8). | Operator stop, provider budgets where available, and documented run limits. | No independent deadline. Recent runs exceeded their manual budgets. A subscription rate limit is not a per-run spend cap. M15. |
| T27 | Code reaches an unintended model service (A5). | One provider profile per VM, checked against recorded policy. M2. | A profile may require several login/API hosts. Routing and model selection within a gateway remain provider/account decisions. |

## B6: Provisioning and review time

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T28 | A compromised install source alters the baseline (A7). | Harness and Node versions are selected explicitly; versions are recorded; routine self-updates are disabled. M16/M23. | Installer checksum, image digests and all package versions are not pinned. Installed tools remain writable. |
| T29 | Re-provisioning opens network access on a used VM (A5/A7). | `create` refuses an existing VM. `reset` recreates from the clean template; it does not bootstrap the used workload. M13. | A saved template ages and must be refreshed deliberately. Reset must happen between independent runs. |
| T34 | Provisioning downloads packages over plain HTTP (A8; A7 if signature checks are bypassed). | Bootstrap requires HTTPS Ubuntu mirrors before its first package update; grants use port 443. M24. | HTTPS does not establish package freshness or eliminate supply-chain risk (T28). |

## B7: Output and organisational decisions

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T30 | Unfixed findings are shared outside the organisation (A5). | Export and sharing are deliberate operator actions. M8. | Review and redact before sharing; the sandbox cannot govern later copies. |
| T31 | A reviewer or downstream agent trusts a poisoned finding or patch (A6). | Human triage and validation before acting. M8. | Agent output is a claim, not evidence of correctness. No automatic handoff to another agent or fix pipeline. |
| T32 | Sensitive files remain on VM or host disks (A5). | Reset/destroy remove workload state; host disk encryption is an operating requirement. | Stop retains disks. Exports, backups and retained host records need their own retention policy; deletion is not secure erasure. |
