---
title: "Control coverage"
description: "Which of the 24 measures the sbx wrapper delivers, and which gaps remain."
---

The current `appsec-sbx` workflow covers much of the original implementation
plan. Of its **24 measures, 8 are delivered, 10 are partial, 4 are open and 2
are deferred** as of 16 September 2026. These counts describe measures,
not a percentage of threats eliminated.

The IDs are retained so existing code and records still refer to the same
measure. M9 now uses a separate VM to provide the intended execution boundary.
M2 selects one provider profile, which may need several API and login hosts.

## Reading the status

- **Delivered:** the control or documented operator procedure exists for the
  current workflow. This does not imply complete platform acceptance.
- **Partial:** useful protection exists, but part of the measure or its
  required validation is missing.
- **Open:** the proposed control is absent.
- **Deferred:** a deliberate extension outside the current workflow.

Source review establishes what the code does. A recorded test establishes
what ran on a named host and version. Neither establishes all eight
[acceptance requirements](/sandbox/threat-model/acceptance/).

## Delivered measures

| ID | Control and current coverage | Threats | Limit |
|---|---|---|---|
| M1 | Run access is limited to the provider profile and selected registries. `--no-registry` removes package access. | [T12](/sandbox/threat-model/catalogue/#t12) [T24](/sandbox/threat-model/catalogue/#t24) | Allowed destinations can still receive data. |
| M2 | One provider profile per VM, stored on the host and checked at entry. | [T12](/sandbox/threat-model/catalogue/#t12) [T27](/sandbox/threat-model/catalogue/#t27) | One provider can use multiple hosts and route to multiple models. |
| M8 | Operator guidance treats exports as untrusted and requires human triage before acting or sharing. | [T05](/sandbox/threat-model/catalogue/#t05) [T30](/sandbox/threat-model/catalogue/#t30) [T31](/sandbox/threat-model/catalogue/#t31) | This is a human procedure, not output sanitisation. |
| M9 | `repro-create` starts a separate VM from the clean template, applies network denies and refuses model keys. | [T19](/sandbox/threat-model/catalogue/#t19) | Replaces the proposed nested-container mechanism. DNS validation remains M5; generated code must actually be moved to this VM. |
| M14 | `skills` imports operator-selected packs, filters files and records commit, local edits and hashes. URL fetches isolate Git configuration and clean up temporary files. | [T24](/sandbox/threat-model/catalogue/#t24) [T33](/sandbox/threat-model/catalogue/#t33) | Pin and review the content. Moving refs, writable guest skills and unbounded host fetch size remain limits. |
| M20 | Entry and key-transfer guards check VM identity, mounts, ports, policy, credentials and management access; inspection errors refuse entry. | [T01](/sandbox/threat-model/catalogue/#t01) [T07](/sandbox/threat-model/catalogue/#t07) | Checks run at entry. Trusted host changes during a session are not continuously monitored. |
| M22 | Host adapters handle import paths, file modes, locking and script line endings across macOS, Linux and Windows. | [T01](/sandbox/threat-model/catalogue/#t01) [T04](/sandbox/threat-model/catalogue/#t04) [T28](/sandbox/threat-model/catalogue/#t28) | Acceptance applies to the recorded platforms. The fallback file reader has a documented race window; some Windows actions require a desktop session. |
| M24 | Bootstrap requires HTTPS Ubuntu mirrors before package updates and grants mirror access on port 443. | [T34](/sandbox/threat-model/catalogue/#t34) | This does not pin package contents or replace signature checks. |

## Partial measures

| ID | What exists | What remains | Threats |
|---|---|---|---|
| M3 | Filtered tracked-file import, host manifest, opaque archive export. | Export does not strip terminal controls or validate content. Import exclusions do not find secrets embedded in source. Synthetic target configuration is an operator task. | [T04](/sandbox/threat-model/catalogue/#t04) [T05](/sandbox/threat-model/catalogue/#t05) [T20a](/sandbox/threat-model/catalogue/#t20a) [T22](/sandbox/threat-model/catalogue/#t22) |
| M4 | Creation publishes no ports; entry rejects published ports. | Complete host/LAN listener checks on each supported setup, including running targets. | [T03](/sandbox/threat-model/catalogue/#t03) [T20b](/sandbox/threat-model/catalogue/#t20b) |
| M5 | Policy-based DNS denials observed in the Windows/Linux acceptance runs. | Resolve earlier conflicting observations; test UDP/TCP, alternate resolvers, containers and upstream queries, including reproducer VMs. | [T13](/sandbox/threat-model/catalogue/#t13) |
| M7 | External policy logs, import/skill manifests and manual report export. | A retained, correlated evidence bundle. `logs` prints only the latest 30 entries; harness transcripts remain workload-writable. | [T10](/sandbox/threat-model/catalogue/#t10) |
| M11 | Root-owned OpenCode configuration, project-config suppression and selected harness defaults. | An enforced configuration floor across harnesses. The workload can unset environment variables and modify its own settings. | [T22](/sandbox/threat-model/catalogue/#t22) |
| M13 | Clean template saved before import/key; `reset` recreates; bootstrap refuses a provisioned guest. | Fresh state is not automatic at run entry. `import --replace` keeps tools, harness state, output and credentials. | [T23](/sandbox/threat-model/catalogue/#t23) [T29](/sandbox/threat-model/catalogue/#t29) |
| M16 | Selected harness/Node versions, disabled routine updates, bootstrap version record and current versions shown by `verify`. | Installer checksums, image digests, remaining package pins and protection against workload tool changes. | [T23](/sandbox/threat-model/catalogue/#t23) [T28](/sandbox/threat-model/catalogue/#t28) |
| M19 | Host-name and direct IPv4/IPv6 address denies. | Controls and tests for allowed hostnames resolving to private, loopback or link-local addresses, including resolution changes. | [T16](/sandbox/threat-model/catalogue/#t16) |
| M21 | Entry assertions, policy-decision checks and dated live network probes. | A repeatable full network test suite with correlated denial evidence. `verify` does not perform that suite. | [T11](/sandbox/threat-model/catalogue/#t11) [T13](/sandbox/threat-model/catalogue/#t13) [T16](/sandbox/threat-model/catalogue/#t16) [T18](/sandbox/threat-model/catalogue/#t18) |
| M23 | One selected harness per VM, provider-specific defaults and known credential-store cleanup. | `stop` skips cleanup for an already-stopped VM and ignores cleanup errors. Codex API-key use and provider-side seat revocation still need validation. | [T12](/sandbox/threat-model/catalogue/#t12) [T22](/sandbox/threat-model/catalogue/#t22) [T25](/sandbox/threat-model/catalogue/#t25) [T28](/sandbox/threat-model/catalogue/#t28) |

## Open and deferred measures

| ID | Status | Missing control | Threats |
|---|---|---|---|
| M6 | Open | Guest patch/refresh policy with an enforced maximum baseline age. Bootstrap installs packages but does not perform a full upgrade. | [T07](/sandbox/threat-model/catalogue/#t07) |
| M12 | Open | Toolchain installed outside the workload's write authority. Node and harness binaries currently live under its home. | [T23](/sandbox/threat-model/catalogue/#t23) |
| M15 | Open | A deadline enforced from the host, including child processes and reproducer VMs. Prompt budgets and a guest `timeout` command do not provide this boundary. | [T26](/sandbox/threat-model/catalogue/#t26) |
| M17 | Open | A credential-holding proxy that authenticates approved calls without exposing the raw key to the workload. Delegated API use would still need limits. | [T24](/sandbox/threat-model/catalogue/#t24) [T25](/sandbox/threat-model/catalogue/#t25) |
| M10 | Deferred | TLS inspection, if the use case requires finer control of allowed traffic. | [T14](/sandbox/threat-model/catalogue/#t14) |
| M18 | Deferred | A supported staging-target action with narrow grants, logging, credentials, reset and ownership checks. | [T16](/sandbox/threat-model/catalogue/#t16) [T21](/sandbox/threat-model/catalogue/#t21) |

The [maintainer backlog](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/sandbox-backlog.md)
holds implementation choices and completion criteria. The threat catalogue
keeps each open risk visible even when the work is tracked elsewhere.

## Evidence and implementation

The [acceptance record](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/records/sbx-acceptance.md)
covers sbx 0.42.1 on macOS, Windows 11 x64 and Linux x86_64. The macOS 0.43.0
discovery runs cover a narrower workflow; they did not repeat reset,
reproducer and full network checks. No record establishes complete [R1–R8](/sandbox/threat-model/acceptance/#requirements)
acceptance.

| Controls | Source and operating instructions |
|---|---|
| Provider and network policy: M1/M2/M5/M19/M21 | [Policy compiler](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/policy.py), [lifecycle](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/lifecycle.py); [provider guide](/sandbox/sbx/providers/). |
| Entry checks: M4/M20 | [sbx adapter](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/sbxcli.py); [command reference](/sandbox/sbx/commands/). |
| Transfer and skills: M3/M8/M14/M22 | [Transfer](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/transfer.py), [URL skill fetch](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/skill_source.py), [host adapter](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/hostos.py); [import/export](/sandbox/sbx/import-export/), [skills](/sandbox/sbx/skills/). |
| Guest setup: M6/M11/M12/M16/M23/M24 | [Bootstrap](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/guest/bootstrap.sh); [provider guide](/sandbox/sbx/providers/). |
| Evidence and lifetime: M7/M9/M13/M15/M17 | [Lifecycle](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/lifecycle.py); [VM lifetime](/sandbox/sbx/lifetime/), [triage](/triage/triage-rubric/). |

## Mapping the six no-regret measures

The [operator baseline](/sandbox/no-regret-measures/) groups the controls
into six practices. This table preserves their links to the detailed model.

| Practice | Threats | Acceptance | Current implementation and limit |
|---|---|---|---|
| Isolated runner | [T01](/sandbox/threat-model/catalogue/#t01) [T02](/sandbox/threat-model/catalogue/#t02) [T23](/sandbox/threat-model/catalogue/#t23) [T29](/sandbox/threat-model/catalogue/#t29) | [R1](/sandbox/threat-model/acceptance/#r1) [R7](/sandbox/threat-model/acceptance/#r7) | VM, mount guards, clean template and explicit reset; VM escape remains accepted. |
| No unrelated credentials in reach | [T04](/sandbox/threat-model/catalogue/#t04) [T07](/sandbox/threat-model/catalogue/#t07) [T08](/sandbox/threat-model/catalogue/#t08) [T09](/sandbox/threat-model/catalogue/#t09) [T22](/sandbox/threat-model/catalogue/#t22) [T25](/sandbox/threat-model/catalogue/#t25) | [R4](/sandbox/threat-model/acceptance/#r4) [R5](/sandbox/threat-model/acceptance/#r5) | Filtered import, unprivileged entry and no host identity forwarding; the model credential remains readable. |
| Egress denied by default | [T11](/sandbox/threat-model/catalogue/#t11) [T12](/sandbox/threat-model/catalogue/#t12) [T13](/sandbox/threat-model/catalogue/#t13) [T14](/sandbox/threat-model/catalogue/#t14) [T15](/sandbox/threat-model/catalogue/#t15) [T16](/sandbox/threat-model/catalogue/#t16) [T17](/sandbox/threat-model/catalogue/#t17) [T18](/sandbox/threat-model/catalogue/#t18) [T21](/sandbox/threat-model/catalogue/#t21) [T27](/sandbox/threat-model/catalogue/#t27) | [R2](/sandbox/threat-model/acceptance/#r2) [R3](/sandbox/threat-model/acceptance/#r3) | Provider/registry policy and drift checks; DNS and private-address resolution remain incomplete. |
| Short-lived, unshared credentials | [T25](/sandbox/threat-model/catalogue/#t25) [T26](/sandbox/threat-model/catalogue/#t26) | [R4](/sandbox/threat-model/acceptance/#r4) [R7](/sandbox/threat-model/acceptance/#r7) | Dedicated credential or login and explicit `unkey`; stop cleanup has M23 limits, idle stop retains login stores, and revocation is separate. |
| Budget first | [T26](/sandbox/threat-model/catalogue/#t26) | [R7](/sandbox/threat-model/acceptance/#r7) | Provider cap where available and operator threshold; no host deadline. |
| Kill switch | [T26](/sandbox/threat-model/catalogue/#t26) [T32](/sandbox/threat-model/catalogue/#t32) | [R7](/sandbox/threat-model/acceptance/#r7) | Wrapper stop includes recorded reproducers; revoke credentials and dispose of retained data separately. |
