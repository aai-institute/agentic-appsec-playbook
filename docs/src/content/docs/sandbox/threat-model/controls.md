---
title: "Control coverage"
description: "Which of the 25 measures the sbx wrapper delivers, and which gaps remain."
---

Of the **25 measures** described here, **9 are delivered, 11 are partial, 3 are open and 2
are deferred**. These counts describe measures, not a percentage of threats
eliminated.

Each `M` identifier names a control and links it to the threats it addresses.

## Reading the status

- **Delivered:** the control or documented operator procedure exists for the
  current workflow. This does not imply complete platform acceptance.
- **Partial:** useful protection exists, but part of the measure or its
  required validation is missing.
- **Open:** the proposed control is absent.
- **Deferred:** a deliberate extension outside the current workflow.

Check the [acceptance requirements](/sandbox/threat-model/acceptance/) on
your own setup. The implementation still has the validation gaps listed below.

## Delivered measures

| ID | Control and current coverage | Threats | Limit |
|---|---|---|---|
| M1 | Run access is limited to the provider profile and selected registries. `--no-registry` removes package access. | [T12](/sandbox/threat-model/catalogue/#t12) [T24](/sandbox/threat-model/catalogue/#t24) | Allowed destinations can still receive data. |
| M2 | One provider profile per VM, stored on the host and checked at entry. | [T12](/sandbox/threat-model/catalogue/#t12) [T27](/sandbox/threat-model/catalogue/#t27) | One provider can use multiple hosts and route to multiple models. |
| M8 | Operator guidance treats exports as untrusted and requires human triage before acting or sharing. | [T05](/sandbox/threat-model/catalogue/#t05) [T30](/sandbox/threat-model/catalogue/#t30) [T31](/sandbox/threat-model/catalogue/#t31) | This is a human procedure, not output sanitisation. |
| M9 | `repro-create` starts a separate VM from the clean template, applies network denies and refuses model keys. | [T19](/sandbox/threat-model/catalogue/#t19) | Optional: the exercises run tests in the review VM. A reproducer cannot install a target's dependencies, so tests that need packages run in the review VM. DNS validation remains incomplete (M5). |
| M14 | `skills` imports operator-selected packs, filters files and records commit, local edits and hashes. URL fetches isolate Git configuration. Archive uploads use binary stdin with a timeout and attempt staging cleanup on failure. | [T24](/sandbox/threat-model/catalogue/#t24) [T33](/sandbox/threat-model/catalogue/#t33) | Pin and review the content. Moving refs, writable guest skills and unbounded host fetch size remain limits. |
| M20 | Entry and key-transfer guards check VM identity, mounts, ports, policy, credentials and management access; inspection errors refuse entry. | [T01](/sandbox/threat-model/catalogue/#t01) [T07](/sandbox/threat-model/catalogue/#t07) | Checks run at entry. Trusted host changes during a session are not continuously monitored. |
| M22 | Host adapters handle import paths, file modes, locking and script line endings across macOS, Linux and Windows. | [T01](/sandbox/threat-model/catalogue/#t01) [T04](/sandbox/threat-model/catalogue/#t04) [T28](/sandbox/threat-model/catalogue/#t28) | The fallback file reader has a documented race window; some Windows actions require a desktop session. |
| M24 | Bootstrap requires HTTPS Ubuntu mirrors before package updates and grants mirror access on port 443. | [T34](/sandbox/threat-model/catalogue/#t34) | This does not pin package contents or replace signature checks. |
| M25 | The wrapper's own sbx calls run without prompts: removals pass `--force`, creation passes `--skills off`, and setup refuses an sbx older than v0.45.0, the release these flags were checked against. | [T01](/sandbox/threat-model/catalogue/#t01) [T11](/sandbox/threat-model/catalogue/#t11) | A later sbx release can rename a flag again; the floor is a minimum, not a pin. Checked with one fresh create on macOS; the full 0.45.0 acceptance matrix is still to be run. |

## Partial measures

| ID | What exists | What remains | Threats |
|---|---|---|---|
| M3 | Filtered import of Git-tracked files, a host-side file list with hashes, and archive export without extraction on the host. Public GitHub imports isolate host Git configuration and record the resolved commit before transferring filtered files. Tracked symlinks are never followed on the host: a link whose index target resolves to an imported file or directory inside the repository is recreated in the guest; any other link is skipped and listed. | Export does not strip terminal controls or validate content. Import exclusions do not find secrets embedded in source. Host Git downloads have no size cap. Synthetic target configuration is an operator task. Link targets come from the Git index, so an unstaged change to a link is not imported. | [T04](/sandbox/threat-model/catalogue/#t04) [T05](/sandbox/threat-model/catalogue/#t05) [T20a](/sandbox/threat-model/catalogue/#t20a) [T22](/sandbox/threat-model/catalogue/#t22) |
| M4 | Creation publishes no ports; entry rejects published ports. | Complete host/LAN listener checks on each supported setup, including running targets. | [T03](/sandbox/threat-model/catalogue/#t03) [T20b](/sandbox/threat-model/catalogue/#t20b) |
| M5 | DNS filtering through the sandbox network policy. | Validate UDP/TCP, alternate resolvers, containers and upstream queries, including reproducer VMs. | [T13](/sandbox/threat-model/catalogue/#t13) |
| M7 | External policy logs, import/skill manifests and manual report export. | Saved logs and reports linked to the same run. `logs` prints only the latest 30 entries; harness transcripts remain workload-writable. | [T10](/sandbox/threat-model/catalogue/#t10) |
| M11 | Root-owned OpenCode settings, settings that disable project configuration, and defaults for each supported harness. | Minimum security settings that the workload cannot disable in any supported harness. The workload can unset environment variables and modify its own settings. | [T22](/sandbox/threat-model/catalogue/#t22) |
| M13 | A clean template saved before code or credentials enter; `reset` recreates the VM; setup refuses to rerun on an already configured guest. | Fresh state is not automatic at run entry. `import --replace` keeps tools, harness state, output and credentials. | [T23](/sandbox/threat-model/catalogue/#t23) [T29](/sandbox/threat-model/catalogue/#t29) |
| M16 | Selected harness/Node versions, disabled routine updates, bootstrap version record and current versions shown by `verify`. | Installer checksums, image digests, remaining package pins and protection against workload tool changes. | [T23](/sandbox/threat-model/catalogue/#t23) [T28](/sandbox/threat-model/catalogue/#t28) |
| M19 | Host-name and direct IPv4/IPv6 address denies. | Controls and tests for allowed hostnames resolving to private, loopback or link-local addresses, including resolution changes. | [T16](/sandbox/threat-model/catalogue/#t16) |
| M21 | Entry assertions, policy-decision checks and operator network-check instructions. | A repeatable full network test suite with correlated denial evidence. `verify` does not perform that suite. | [T11](/sandbox/threat-model/catalogue/#t11) [T13](/sandbox/threat-model/catalogue/#t13) [T16](/sandbox/threat-model/catalogue/#t16) [T18](/sandbox/threat-model/catalogue/#t18) |
| M23 | One selected harness per VM, provider-specific defaults and known credential-store cleanup. The stored API key is removed by `unkey`, `stop`, `reset` and `destroy`, whether or not the VM runs. | Harness login stores are cleaned only from a running VM, and cleanup errors are ignored. Codex API-key use and provider-side seat revocation still need validation. | [T12](/sandbox/threat-model/catalogue/#t12) [T22](/sandbox/threat-model/catalogue/#t22) [T25](/sandbox/threat-model/catalogue/#t25) [T28](/sandbox/threat-model/catalogue/#t28) |
| M17 | API keys stay on the host: `key` stores the key in sbx's credential store scoped to the VM, the VM's kit declares the key variable as proxy-managed, the workload holds a placeholder, and sbx's proxy adds the real value to requests to the provider host. `unkey`, `stop`, `reset` and `destroy` remove the stored key. | The proxy adds the key to every request to that host, so any guest process can still use it, and no API method is restricted. The stored key rests in the host credential store until removed. Injection needs the forward proxy. Seat logins still write tokens to the guest disk. Harness runs against the placeholder are not yet recorded on every provider. | [T24](/sandbox/threat-model/catalogue/#t24) [T25](/sandbox/threat-model/catalogue/#t25) |

## Open and deferred measures

| ID | Status | Missing control | Threats |
|---|---|---|---|
| M6 | Open | Guest patch/refresh policy with an enforced maximum baseline age. Bootstrap installs packages but does not perform a full upgrade. | [T07](/sandbox/threat-model/catalogue/#t07) |
| M12 | Open | Tools installed where the workload cannot modify them. Node and harness binaries currently live under its home. | [T23](/sandbox/threat-model/catalogue/#t23) |
| M15 | Open | A deadline enforced from the host, including child processes and reproducer VMs. Prompt budgets and a guest `timeout` command do not provide this boundary. | [T26](/sandbox/threat-model/catalogue/#t26) |
| M10 | Deferred | TLS inspection, if the use case requires finer control of allowed traffic. | [T14](/sandbox/threat-model/catalogue/#t14) |
| M18 | Deferred | A supported staging-target action with narrow grants, logging, credentials, reset and ownership checks. | [T16](/sandbox/threat-model/catalogue/#t16) [T21](/sandbox/threat-model/catalogue/#t21) |

## Implementation and operating instructions

| Controls | Source and operating instructions |
|---|---|
| Provider and network policy: M1/M2/M5/M19/M21 | [Policy compiler](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/policy.py), [lifecycle](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/lifecycle.py); [provider guide](/sandbox/sbx/providers/). |
| Entry checks and sbx CLI contract: M4/M20/M25 | [sbx adapter](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/sbxcli.py); [command reference](/sandbox/sbx/commands/). |
| Transfer and skills: M3/M8/M14/M22 | [Transfer](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/transfer.py), [GitHub fetch](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/git_source.py), [host adapter](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/hostos.py); [import/export](/sandbox/sbx/import-export/), [skills](/sandbox/sbx/skills/). |
| Guest setup: M6/M11/M12/M16/M23/M24 | [Bootstrap](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/guest/bootstrap.sh); [provider guide](/sandbox/sbx/providers/). |
| Credentials: M17/M23 | [Credentials](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/credentials.py), [providers](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/providers.py); [provider guide](/sandbox/sbx/providers/), [VM lifetime](/sandbox/sbx/lifetime/). |
| Evidence and lifetime: M7/M9/M13/M15 | [Lifecycle](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/sandbox/sbx/appsec_sbx/lifecycle.py); [VM lifetime](/sandbox/sbx/lifetime/), [run report](/exercises/first-discovery-pass/#part-4-write-the-run-report). |

## Mapping the six no-regret measures

The [operator baseline](/sandbox/no-regret-measures/) groups the controls
into six practices. This table preserves their links to the detailed model.

| Practice | Threats | Acceptance | Current implementation and limit |
|---|---|---|---|
| Isolated runner | [T01](/sandbox/threat-model/catalogue/#t01) [T02](/sandbox/threat-model/catalogue/#t02) [T23](/sandbox/threat-model/catalogue/#t23) [T29](/sandbox/threat-model/catalogue/#t29) | [R1](/sandbox/threat-model/acceptance/#r1) [R7](/sandbox/threat-model/acceptance/#r7) | VM, mount guards, clean template and explicit reset; VM escape remains accepted. |
| No unrelated credentials in reach | [T04](/sandbox/threat-model/catalogue/#t04) [T07](/sandbox/threat-model/catalogue/#t07) [T08](/sandbox/threat-model/catalogue/#t08) [T09](/sandbox/threat-model/catalogue/#t09) [T22](/sandbox/threat-model/catalogue/#t22) [T25](/sandbox/threat-model/catalogue/#t25) | [R4](/sandbox/threat-model/acceptance/#r4) [R5](/sandbox/threat-model/acceptance/#r5) | Filtered import, unprivileged entry and no host identity forwarding; the API key stays on the host and the guest holds a placeholder, but any guest process can still use it. |
| Egress denied by default | [T11](/sandbox/threat-model/catalogue/#t11) [T12](/sandbox/threat-model/catalogue/#t12) [T13](/sandbox/threat-model/catalogue/#t13) [T14](/sandbox/threat-model/catalogue/#t14) [T15](/sandbox/threat-model/catalogue/#t15) [T16](/sandbox/threat-model/catalogue/#t16) [T17](/sandbox/threat-model/catalogue/#t17) [T18](/sandbox/threat-model/catalogue/#t18) [T21](/sandbox/threat-model/catalogue/#t21) [T27](/sandbox/threat-model/catalogue/#t27) | [R2](/sandbox/threat-model/acceptance/#r2) [R3](/sandbox/threat-model/acceptance/#r3) | Provider/registry policy and drift checks; DNS and private-address resolution remain incomplete. |
| Short-lived, unshared credentials | [T25](/sandbox/threat-model/catalogue/#t25) [T26](/sandbox/threat-model/catalogue/#t26) | [R4](/sandbox/threat-model/acceptance/#r4) [R7](/sandbox/threat-model/acceptance/#r7) | Dedicated credential or login and explicit `unkey`; the stored key stays until `unkey`, `stop`, `reset` or `destroy`, login stores survive idle stops and are cleaned only from a running VM, and revocation is separate. |
| Budget first | [T26](/sandbox/threat-model/catalogue/#t26) | [R7](/sandbox/threat-model/acceptance/#r7) | Provider cap where available and operator threshold; no host deadline. |
| Kill switch | [T26](/sandbox/threat-model/catalogue/#t26) [T32](/sandbox/threat-model/catalogue/#t32) | [R7](/sandbox/threat-model/acceptance/#r7) | Wrapper stop includes recorded reproducers; revoke credentials and dispose of retained data separately. |
