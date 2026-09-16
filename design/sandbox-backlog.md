# Sandbox implementation backlog

Reconciled on 2026-09-16 against the current `sandbox/sbx/appsec_sbx` source
and `records/sbx-acceptance.md`. No new VM validation was performed.
The public [control register](../docs/src/content/docs/sandbox/threat-model/controls.md)
owns M1–M24 status and residual risks. This file owns remaining implementation
work and completion criteria; it replaces the threat model's old versioned
implementation cut and effort estimates.

The count is 8 delivered, 10 partial, 4 open, 2 deferred. Delivered measures
are M1, M2, M8, M9, M14, M20, M22 and M24. “Delivered” is scoped to the
current workflow, not full R1–R8 acceptance. In particular, M9 uses a separate
VM and M8 is an operator procedure.

## Network validation

M4/M5/M19/M21; T03/T11/T13/T16/T17/T18/T20b; R2/R3/R6.

Build a repeatable probe suite with controlled destinations and correlated
external logs. It must cover direct traffic with proxy variables removed,
IPv4/IPv6, DNS over UDP/TCP, alternate resolvers, container paths and the
reproducer profile. Observe queries upstream; a client error or proxy denial
alone cannot establish DNS confidentiality. Reconcile the earlier Windows
DNS result with later denials in the acceptance record.

Test allowed hostnames resolving to private, loopback, link-local and host
addresses, then changing resolution on reconnect. Direct-IP denies do not
establish this control. Test CONNECT destinations, TLS server names, HTTP
Host mismatches and redirects against controlled servers. Establish the
required enforcement before marking M19 complete.

Exercise actual guest/target listeners from host and LAN. Record listener
health as well as failed connections, so a stopped listener cannot produce
a false pass. Repeat on the supported platform/backend combinations.

Completion: dated per-platform results for every path, explicit failures or
unverified cases, and assertions that distinguish policy denial from an
unreachable upstream. Keep `verify` described as an entry check unless it
actually gains this coverage.

## Run lifetime and persistence

M6/M12/M13/M15/M16; T07/T23/T26/T28/T29; R5/R7.

- **M15:** add a host-controlled deadline that stops the primary and recorded
  reproducers, including detached work. Test it with the terminal closed and
  with child processes running. Manual budgets were exceeded in the September
  16 runs; a prompt instruction is not the control.
- **M13:** make the clean-start decision explicit and hard to omit. Preserve
  export before reset and distinguish continuing a review from starting a new
  independent run. Test dirty settings, tools, caches and skills disappearing.
- **M12:** install the toolchain under root ownership outside the workload
  home. Preserve normal unprivileged execution without putting the harness
  on the maintenance shell's normal path. Verify attempted workload changes fail.
- **M6:** define a patch/refresh policy and maximum template age. `reset`
  returns to the saved baseline; it does not update that baseline. Validate
  refresh without reopening install access over imported data.
- **M16:** verify the nvm installer checksum; pin base/runtime/test images by
  digest and remaining provisioning packages as appropriate. Keep the input
  manifest and compare live tool versions. Update-disabling environment
  variables alone do not prevent deliberate mutation.

## Credentials and harness settings

M11/M17/M23; T22/T24/T25/T26; R4/R5/R7.

- **M17:** design a credential-holding proxy outside workload authority. Test
  with dummy keys that files, environment, process views and proxy responses
  reveal no raw secret while permitted API calls work. Scope requests and
  account authority; hiding a key does not prevent its authorised use or spend.
- **M11:** define and test the minimum effective settings for each harness.
  Include project/account hooks, plugins and local tool servers; try unsetting
  environment controls and changing user settings. Record what is enforced
  outside the workload and what merely supplies a safe default.
- **M23 cleanup:** make credential removal work for already-stopped VMs and
  report failures. Source review found `Managed.stop` only calls cleanup when
  status is `running`, with `check=False`. Test stop after idle stop and injected
  deletion failures; preserve the ability to stop execution even if deletion
  fails. This gap was found in code review, not a new live probe.
- **M23 validation:** exercise the Codex API-key path and provider-side seat
  revocation. Preserve the distinction between wrapper cleanup, sbx idle stop
  and provider validity in all operating instructions.

## Export and evidence

M3/M7 and the delivered M8 procedure; T04/T05/T10/T20a/T30/T31; R4/R8.

- **M7:** collect run identity, times, effective policy, versions, import/skill
  hashes and complete relevant enforcement logs into a host evidence bundle.
  Label reports and harness sessions as workload-writable. The current `logs`
  command returns 30 recent entries, which can omit earlier run evidence.
- **M3:** decide whether to add a safe text-preview/export path that escapes
  terminal controls. Preserve raw evidence separately and keep archive
  extraction explicit. Test adversarial archive entries and text before
  claiming safe viewing. Keep import exclusions described as filters, not a
  secret scanner; running targets need synthetic configuration.
- **M8:** operator review rules belong in the import/export guide, triage rubric
  and hardening checklist. Keep the control register's link and residual risk;
  do not turn the threat model into an extraction or triage manual.

## Deferred extensions

- **M18:** staging access requires a real use case and the
  [staging acceptance conditions](../docs/src/content/docs/sandbox/threat-model/acceptance.md#staging-access-a-future-extension).
  No current `target add/remove` action exists. Do not implement staging as an
  undocumented model/registry grant.
- **M10:** TLS inspection needs a separate design and cost assessment if
  hostname filtering is insufficient. It does not eliminate all misuse of
  permitted services.

## Where further detail belongs

The [operator guide](../docs/src/content/docs/sandbox/sbx/index.md) owns commands,
credential handling, reset, import/export and skill use. The
[internals](sbx-internals.md) own implementation rationale and harness
investigations. [Acceptance records](../records/sbx-acceptance.md) own platform
results, versions, timings and limitations. Future completion updates both
the public control status and its dated evidence; tasks stay here.

M14's URL-fetch size bound and immutable skill selection are follow-ups to a
delivered capability. M22's fallback file-reader race and untested host/session
combinations also remain explicit limits. Track those without reopening the
entire measure or losing its existing evidence.
