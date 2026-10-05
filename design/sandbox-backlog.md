# Sandbox implementation backlog

Reconciled on 2026-09-16 against the current `sandbox/sbx/appsec_sbx` source
and `records/sbx-acceptance.md`; M17 and M23 updated on 2026-10-02 for wrapper 0.4.0.
The public [control register](../docs/src/content/docs/sandbox/threat-model/controls.md)
owns M1–M26 status and residual risks. This file owns remaining implementation
work and completion criteria; it replaces the threat model's old versioned
implementation cut and effort estimates.

The count is 9 delivered, 11 partial, 4 open, 2 deferred. Delivered measures
are M1, M2, M8, M9, M14, M20, M22, M24 and M25 (added 2026-09-22 for sbx 0.45.0). “Delivered” is scoped to the
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

## Entry guards across sbx upgrades

M20; T07/T26; R5.

- **M20:** the policy entry guard compares the whole rule objects from
  `policy ls --json` against the snapshot taken at `create`. Any sbx release
  that adds a field to the rule shape (0.45.0 added `provenance` and
  `actions`) makes every VM created earlier fail entry until `reset`, with
  the same message as a real policy edit (2026-09-30 record). Compare the
  fields that carry the decision (scope, resource type, decision, resources,
  status, editable, and `actions` where present) and report an unchanged
  policy under a changed release as a distinct condition. Keep refusing on
  any change to those fields. Test with a snapshot taken on the previous
  release.

## Skill and import pins across ref names

M3/M14; T04/T33.

- **M14:** `git_source.fetch_checkout` fetches `--ref` by name and records
  `FETCH_HEAD^{commit}`; it never compares that commit with a `--ref` given
  as a full SHA. Plugin4Shell (2026-09-17) showed that a remote branch named
  with the 40-hex SHA wins such a checkout in four agents. Reproduce against
  a throwaway repository with a branch named like a commit, then refuse the
  install when a SHA-shaped `--ref` resolves to a different commit, and
  print the resolved commit next to the requested one in every case.

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

- **M17 (partial since wrapper 0.4.0, 2026-10-02):** sbx's proxy-managed
  credentials hold the API key on the host; see
  [sbx-managed-credentials.md](sbx-managed-credentials.md). Remaining: run each
  harness against the placeholder on its provider and record it (OpenCode on
  OpenRouter, Claude Code with a seat token, Codex with an API key; Pi on
  OpenRouter done 2026-10-02); exercise
  the bindings path and credential store on Windows and Linux; evaluate the kit
  `oauth` declaration for seat logins so their tokens leave the guest disk too;
  hiding the key does not limit its use or spend, which needs provider caps or
  an L7 proxy.
- **M11:** define and test the minimum effective settings for each harness.
  Include project/account hooks, plugins and local tool servers; try unsetting
  environment controls and changing user settings. Record what is enforced
  outside the workload and what merely supplies a safe default.
- **M23 cleanup:** since wrapper 0.4.0 the stored key is removed on a stopped VM
  too; the harness login stores on the guest disk are still deleted only when
  `stop` finds the VM running, with `check=False`. Make that removal work after
  an idle stop and report failures; test injected deletion failures; preserve
  the ability to stop execution even if deletion fails.
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

## Workload containers

M26; T08/T18/T21/T23/T25/T26/T28; R3/R5/R6/R7. Registered as open on 2026-10-05;
design, guest probe and decisions in [sbx-docker-profile.md](sbx-docker-profile.md).

- **Wrapper:** `create --docker [--image REF]... [--docker-disk SIZE]`, `dockerhub` and
  `ghcr` presets for `--registry`, the bootstrap block (pinned rootless packages, per-boot
  start script, shared memory cap, image archive with digests), image loading after a
  template create, entry checks, `verify` output, tests and the regenerated command
  reference. Without `--docker` nothing changes.
- **Threat model:** when the wrapper ships, replace T08 and T18 with the rows in the design
  note and add the residuals for T21, T25, T26 and T28.
- **Docs:** the pages listed in the design note's implementation plan.
- **Acceptance per platform:** create and `verify` with the flag, entry after an idle stop,
  the container network probes from the default bridge and an `--internal` network, a
  rootless image build, a reset canary (built image, container, volume and daemon
  configuration gone; provisioned images present), a Strix smoke run against the demo
  target on an internal network, Mantis's reproduce stage with runc, and, as root in a
  throwaway VM, a read-only listing of what each virtiofs share exports (the surface guest
  root would reach; the design note's access-model section).
- **`--gvisor`:** decide after an x86_64 probe; drop the option if runsc needs its
  test-only flag under rootless Docker.

Completion: partial once the wrapper ships with the macOS record (target 2026-10-14);
delivered once Windows and Linux records exist (target 2026-10-28).

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
