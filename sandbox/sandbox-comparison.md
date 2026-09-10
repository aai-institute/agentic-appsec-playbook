# Sandbox comparison against the AppSec threat model

**Status:** draft v0.4, 2026-09-09; includes platform suitability, Windows
acceptance criteria, user-run Windows sbx probes, and a locally exercised
[macOS sbx shell workflow](sbx/README.md). Primary-source research and review of the
Colima v0.2 scripts at repository commit `3aac034`. Product capabilities below
are `verified-at-source` on this date; conclusions are our assessment, not
vendor guarantees. Local `sbx version` and CLI help were `checked`: v0.42.1,
build `cc6e400a4a3ce3ce5e0b2b77b8ee352aac854c64`. The Windows trial in §4
records commands run by the user on a separate machine and the outputs they
supplied; it includes sandbox creation and configuration changes. Those
observations are distinct from source-verified claims and the Colima guide's
historical evidence. The macOS recipe has its own acceptance record; runtime
claims beyond these recorded trials remain `not-yet-tested`.

## 1. Decision and scope

**Keep Colima as the measured reference while closing its documented gaps;
evaluate a constrained Docker `sbx` profile as the next local backend.**
Docker's external policy enforcement and credential injection could remove
custom security code and make containerised AppSec tools easier to operate.
Its convenience defaults need deliberate restrictions before it fits our
threat model. For an open-source local alternative, prioritise **Microsandbox**;
for richer policy enforcement, evaluate **NVIDIA OpenShell**, explicitly
selecting and testing its compute driver. The evidence behind these
recommendations is in §3–§5. The initial Windows trial confirms selected TCP
denials and one nested-workload stop/restart case. DNS policy behaviour and
shared host resources remain unresolved; no alternative has completed the
acceptance contract.

**Audience portability is a second selection axis.** Continue Windows
validation of sbx alongside macOS and Linux, with Microsandbox as
the open-source challenger. Platform support in upstream docs is not evidence
that our import, policy, credentials and teardown workflow works there. See
[cross-platform suitability](#cross-platform-suitability) for prerequisites,
the WSL2 distinction and a fallback for laptops that cannot run local VMs.

This keeps the [design case](threat-model.md#1-design-case-and-scope): one
engineer, owned code, interactive defensive AppSec, ordinary dependency
installation, generated reproducers and optionally a synthetic local target
or one sanctioned staging target. It does not expand the pilot to hostile
repositories, multi-tenant execution or unattended production access.

“Openly available” includes publicly obtainable proprietary software and
open-source software. We label those separately. Local execution, source
availability, self-hostability and free use are different properties.
Remote hosting introduces another operator with access to A5 and a different
network position for A2; it needs its own deployment assessment.

The [threat model](threat-model.md) owns assets, boundaries, T/M identifiers
and the [R1–R8 acceptance contract](threat-model.md#12-portable-acceptance-contract).
The [Colima guide](reference-sandbox.md) owns the operating instructions.
This document owns backend selection and the evidence required to substitute
one implementation for another. A feature score cannot replace a failed
acceptance requirement.

## 2. What Colima v0.2 actually enforces

These observations come from [the host wrapper](make-appsec-vm.sh) and
[guest bootstrap](bootstrap-appsec-vm.sh), read on 2026-09-09. Earlier VM
checks are recorded in the guide; this review did not repeat them.

| Area / threats | Implemented now | Gap or correction |
|---|---|---|
| Host files — T01 T02 T06 | Dedicated vz VM, `--mount none`, mount-type checks; VM is the outer execution boundary | `shell`/`agent` skip the check for an already-running VM. `key` does not check mounts. A failed SSH inspection falls through as “no mounts”. Neutral host identity is not established. M20 |
| Guest privilege — T07 T08 T09 | Separate agent uid, no sudo or Docker group, restricted homes; admin launches containers | Essential because the firewall and trusted logs live in this guest. This also limits agents that expect to operate Docker themselves |
| Network — T11 T12 T15 T16 T18 T21 T27 | nftables `output` and `forward` policy drop; tinyproxy hostname filtering; direct container egress check recorded | Seven default allowlist entries include four model services, GitHub and npm. Proxy 443 accept precedes the private-range drop. IPv6 and loopback/bridge accepts also need consideration; merely moving the last IPv4 rule is insufficient. M1/M2/M19 |
| DNS — T13 | Resolver exceptions for proxy/dnsmasq; optional tightening knob | Off by default and UDP-only. TCP to the local resolver remains accepted. Container DNS paths were not validated. M5 |
| Inbound and targets — T03 T17 T19 T20a T20b | User-mode NAT; admin can launch an internal target or networkless `runsc` reproducer | Lima auto-forwards listeners to host localhost. `runsc` is registered, not the default. Internal target setup is an operator instruction, not a wrapper action. M4/M9 |
| Import and keys — T04 T24 T25 | Manual SSH transfer; root-owned but agent-readable tmpfs key file, sourced into login environments | Manual tar excludes only `.git`. No automated secret/config filtering. Dependencies can read the raw model key. `unkey` does not erase existing process environments. M3/M17 |
| Config and clean start — T22 T23 T28 T29 T32 | Snapshot/rollback/destroy actions; bootstrap skips active services unless forced | Agent owns toolchain/config; reset is optional. Rebootstrap can reopen networking on used state. Mutable package/image references; no complete manifest. M11–M16 |
| Budget and evidence — T05 T10 T26 T30 T31 | External VM stop; root/proxy-owned network logs; human review and provider-cap instructions | No wrapper-enforced deadline, evidence export or output sanitisation. Agent session logs remain writable by the agent. M7/M8/M15 |
| Verification — T11 T13 T16 T18 | Bootstrap prints direct/denied/allowed/container/socket results and asserts some | Direct curl does not force proxy bypass; denied CONNECT is not asserted; allowed response can be a proxy error; any recent forward-drop line can satisfy the log check. M21 |

**Consequence:** Colima is an inspectable, partially exercised baseline with
known gaps. The proposed implementation-v0.3 measures are not implemented
merely because they appear in the model. Apply the same distinction between
documented, configured and demonstrated controls to every candidate.

## 3. How Docker sbx would fare

### Product and version boundary

This comparison concerns **local Docker Sandboxes using `sbx` v0.42.1**.
The release notes date that version to 2026-09-07 and put mountless creation
in v0.42.0. Older `docker sandbox` instructions and `sbx --cloud` have
different deployment assumptions. Local CLI version/help match the version
used here. [Docker release notes](https://docs.docker.com/ai/sandboxes/release-notes/)

Docker lists macOS 14+ on Apple silicon, Windows 11 with WHP, and Ubuntu 24.04+
with KVM on amd64/arm64. The standalone CLI needs neither Docker Desktop nor
a host Docker Engine. [Installation](https://docs.docker.com/ai/sandboxes/install/)

The release repository labels `sbx` **proprietary**. Docker says local use is
free, including commercial work, with a Docker login; organisation governance
and its audit capabilities require a paid subscription. Free local policy
controls should not be confused with that paid enforcement tier.
[Release repository](https://github.com/docker/sbx-releases),
[Docker FAQ](https://docs.docker.com/ai/sandboxes/faq/)

### The architectural improvement

Each sandbox has a microVM and its own Docker daemon. TCP egress crosses a
host-side proxy, using either explicit forward-proxy or transparent routing.
The MCP gateway is another host-side service; registered local stdio MCP
servers execute on the host. Deleting a sandbox removes its guest state;
stopping preserves it. [Architecture](https://docs.docker.com/ai/sandboxes/architecture/)

Our assessment: guest sudo need not defeat **external** network enforcement.
This could resolve the Colima tension between T07/T08 and tools needing
Docker. However, guest-root ownership can still defeat guest-local config,
logs and reproducer restrictions. Treat those as separate requirements.

### Mapping to the acceptance contract

The references in this section describe available mechanisms. Every
“candidate” entry still needs §6 tests on the configured local installation.

| Requirement / threats | sbx mechanism and assessment | Work still needed |
|---|---|---|
| R1 — T01 T02 T06 | **Candidate:** microVM and mountless creation | Sanitised copy-in, no extra host shares; verify neutral paths/identity. Hypervisor escape remains accepted residual risk |
| R2 — T03 T15 T16 T17 T20b T21 | **Candidate:** explicit port publishing and network destination rules | No published ports or host-service allows; test private-address resolution and IPv6. A staging exception must stay one host:port |
| R3 — T11 T12 T13 T14 T18 T27 | **Candidate:** proxy enforcement across TCP; documented resolver policy and blocked external UDP/ICMP | Inspect all effective policy sources; one model service and required registry. Test nested containers, DNS and TLS routing. No credit for preventing exfiltration over an allowed API |
| R4 — T04 T24 T25 | **Improvement:** proxy-managed model credentials can remain outside the workload | Sanitise inputs, remove signing authority and unrelated service credentials; prove actual harness auth uses the managed path |
| R5 — T07 T08 T09 T22 T23 | **Mixed:** outer controls can survive guest root; guest configuration is mutable | Disable shared state and host tools, govern setup inputs, reset each run. Root-owned files inside this VM alone cannot enforce M11/M12 against guest sudo |
| R6 — T19 T20a | **Partial:** private daemon enables AppSec tools to build/run targets | No demonstrated equivalent of our separately administered, networkless reproducer. Use a separately controlled execution sandbox if this boundary must survive a compromised harness |
| R7 — T23 T26 T28 T29 T32 | **Partial:** explicit stop/remove/recreate lifecycle | Pin templates/kits, fresh instance per run, independent deadline and provider cap/revocation. Local `--ttl` is unavailable: installed help marks it cloud-only |
| R8 — T05 T10 T30 T31 | **Partial:** host-side policy inspection/logging and explicit copy-out primitives | Collect correlated enforcement evidence outside the VM; retain raw records safely, label agent output and review before use |

### Defaults and integrations that matter

**Workspace selection is a security decision.** `sbx run` shares the current
directory writable; `sbx create` without a path can avoid that share.
Clone mode prevents host writes but still exposes the source tree, including
ignored and untracked files. It is not a sanitiser for `.env` or metadata.
Direct mounts also allow hard-link writes to affect another path to the same
file. Local sandboxes can write host clipboard text. SSH-agent forwarding is
enabled by default, granting signing/authentication use even though private
keys stay on the host. These are T01/T04/T05/T25 capabilities to exclude or
explicitly accept. [Isolation](https://docs.docker.com/ai/sandboxes/security/isolation/)

**Network default-deny does not mean a minimal effective allowlist.**
The first-use policy choices include Open, Balanced and Locked Down; Balanced
permits broad development services. Global, sandbox and kit rules contribute
to effective access. Organisation governance changes precedence. Use a
dedicated pilot configuration and inspect it; adding two narrow sandbox
allows does not remove inherited broad allows. Do not reset an operator's
existing global policy as a side effect of a pilot wrapper.
[Local policy](https://docs.docker.com/ai/sandboxes/governance/access-controls/local/)

**Mountless is not necessarily without shared state.** Supported agent
templates share a persistent, writable skills store by default; removing a
sandbox does not remove that store. Docker documents `--no-share-skills` as
the opt-out. However, the installed v0.42.1 `sbx create --help` and
`sbx create opencode --help` do not list it. The subsequent macOS shell trial
successfully passed the flag to v0.42.1 with a custom shell kit; mount inspection
showed no skills share or workspace. The help omission remains, but this tested
profile now provides a working recipe. Recheck actual mounts for every kit.
[Default posture](https://docs.docker.com/ai/sandboxes/security/defaults/),
[Shared skills](https://docs.docker.com/ai/sandboxes/workflows/agent-skills/)

**Credential injection is narrower than credential safety.** Built-in
OpenRouter support is documented. Service secrets default to global scope;
use sandbox-scoped credentials and review other services available to the
template. The forward proxy substitutes authentication, while explicit
environment secrets or OAuth passthrough can expose raw values. Disable
`ssh.agentForwardingEnabled` in the dedicated pilot setup and account for
the documented daemon restart requirement. A dependency able to call the
credential proxy can still spend the key's budget. It should never gain a
GitHub write token merely because that token stays outside the VM.
[Credentials](https://docs.docker.com/ai/sandboxes/configuration/credentials/)

**Inbound access is separate from egress.** Ordinary sandbox listeners are
not host-accessible until published. Keep port mappings empty and review
kit-declared publishing. Host-service access can be granted through
`host.docker.internal`; exclude it from the baseline. Restart can restore
published ports, so recheck on entry.
[Local development](https://docs.docker.com/ai/sandboxes/workflows/development/),
[Port publishing](https://docs.docker.com/reference/cli/sbx/ports/)

**Host automation is outside the VM boundary.** Reject project-supplied
`.sbxenv.yaml` lifecycle/credential commands during import unless separately
reviewed; Docker documents host execution and an approval plan. Do not
register host stdio MCP servers for this pilot. Guest network policy cannot
by itself contain effects performed by a host tool. This is the same T22/T31
problem through a new execution path.
[Environment-file isolation](https://docs.docker.com/ai/sandboxes/security/isolation/#sandbox-environment-files),
[MCP architecture](https://docs.docker.com/ai/sandboxes/architecture/#mcp-gateway)

### Pilot profile and implemented shell workflow

The [sbx wrapper](sbx/README.md), a stdlib-only Python package since 2026-09-10,
implements provisioning, an unprivileged shell, one admitted model provider per
VM (M2), narrowed effective policy, filtered copy-in, tmpfs keys, opaque copy-out,
stop and clean recreation. Its acceptance record distinguishes passed probes
from remaining gaps; only macOS has one. It currently uses Colima-style raw model
keys rather than proxy-managed provider authentication. Installed gVisor failed in the tested
16K-page ARM guest, so a separate sbx VM supplies the reproducer boundary.
The following broader profile remains the design target:

1. Record local CLI/build, template digest, kit/config revisions, effective
   policy and host integration settings. Use a dedicated configuration with
   narrow egress; establish policy before admitting project data or credentials.
2. Create without a workspace path. Resolve the shared-skills opt-out and
   verify no host shares, SSH-agent socket, host MCP tools, clipboard image
   access or published ports. Assess clipboard text writes as an output channel.
3. Copy a sanitised repository with `sbx cp`; the installed CLI documents this
   primitive, but neither copying nor clone mode performs M3 sanitisation.
   Retain instruction files while stripping executable harness/environment
   config. Supply synthetic integration settings separately.
4. Attach only a sandbox-scoped, capped model credential through the proxy.
   Check the harness and dependency subprocesses for raw-key exposure using a
   disposable test secret. Test service access and policy with the selected
   provider and registry.
5. Permit Docker only inside the VM. Run a target with synthetic config and
   no outside integrations; use a separately administered sandbox for
   reproducers needing an independent no-network guarantee.
6. Collect host-side policy evidence and explicit output exports, stop and
   revoke, then remove the instance. Create the next run from the pinned
   clean template. Verify no shared store or volume carries prior state.

`sbx policy check` is useful configuration evidence, not proof that packets
take the checked path. The actual harness, dependency subprocess and container
must all pass the network probes. Local copying and lifecycle commands are
documented in [Usage](https://docs.docker.com/ai/sandboxes/usage/).

## 4. Open alternatives and where they fit

This is a deliberately varied shortlist: agent environments, platforms that
manage environments, and execution runtimes. They are not interchangeable.
All project license labels below refer to the named core repository; bundled
images, dependencies and hosted services may have their own terms.

| Candidate | Availability / deployment | Documented capability and our fit assessment |
|---|---|---|
| **Microsandbox** | Apache-2.0; local microVM runtime and SDK/CLI; Apple-silicon macOS, Linux/KVM, Windows/WHP; beta | OCI images, host/port network configuration and secrets kept outside the VM are documented. Closest open-source local candidate for R1/R3/R4. Requires our import, reset, evidence and budget workflow; beta status warrants release-specific tests. [Project](https://github.com/superradcompany/microsandbox) |
| **NVIDIA OpenShell** | Apache-2.0; alpha; local or operator-hosted gateway | Filesystem/process/network policies and inference routing address R3–R5. Docker, Podman, Kubernetes and MicroVM drivers are documented; choose the driver explicitly instead of assuming every OpenShell sandbox is a VM. [Project](https://github.com/NVIDIA/OpenShell), [support matrix](https://docs.nvidia.com/openshell/reference/support-matrix) |
| **OpenSandbox** | Apache-2.0; self-hosted server, Docker or Kubernetes | Lifecycle, command/file APIs, egress controls and optional stronger container runtimes. Suitable for an eventual shared service; default Docker deployment must not inherit the rating of an optional Kata/gVisor backend. Credential Vault is an explicit capability, not an environment-variable convention. [Project](https://github.com/opensandbox-group/OpenSandbox) |
| **Anthropic Sandbox Runtime (`srt`)** | Apache-2.0; beta research preview; native process restrictions, including macOS Seatbelt and Linux bubblewrap | Useful as our optional L4: read/write/socket restrictions and proxy filtering. Default filesystem reads are broad; configure explicit exclusions. It supplies neither a separate guest kernel nor safe key brokerage. Domain-fronting and permissive-socket risks are documented. Retain the outer VM for this pilot. [Project and limitations](https://github.com/anthropics/sandbox-runtime) |
| **gVisor (`runsc`)** | Apache-2.0; Linux OCI runtime, Docker/Kubernetes integration | Userspace application kernel reduces the interface exposed to Linux; compatibility differs from a full Linux VM. Already our L3 reproducer layer. It needs an operator-owned network/credential/lifecycle design to become a complete agent environment. [Architecture](https://gvisor.dev/docs/), [source/license](https://github.com/google/gvisor) |
| **Kata Containers** | Apache-2.0; hardware-virtualised OCI workloads, containerd/Kubernetes integration | Guest-kernel boundary fits R1/R6 for a future Linux service. Runtime support does not supply our hostname policy, model credential proxy or review workflow. Hardware virtualisation and cluster integration make it a larger deployment task than the laptop pilot. [Project](https://github.com/kata-containers/kata-containers) |
| **Firecracker** | Apache-2.0; Linux/KVM VMM | MicroVM execution plus production jailer and host-hardening guidance. Strong building block for R1/R6; image building, networking, secret brokerage, evidence and orchestration remain integration work. Not a direct macOS replacement for Colima. [Project](https://github.com/firecracker-microvm/firecracker) |
| **E2B infrastructure** | Apache-2.0 core; self-hostable infrastructure behind E2B's cloud service | Firecracker-based service architecture is relevant to remote runs. Upstream lists Terraform deployment on GCP and AWS beta; general Linux self-hosting remains unchecked in its support list. Assess policy, credentials and exposure on the chosen deployment; hosted feature parity is not established here. Higher operations burden than the local pilot. [Infrastructure](https://github.com/e2b-dev/infra), [Firecracker build integration](https://github.com/e2b-dev/fc-versions) |

### Important configuration qualifications

**OpenShell:** require blocking enforcement, not just logged decisions.
The security guide documents L7 `enforcement: audit` as the default and
Landlock `compatibility: best_effort` as capable of continuing without the
intended restrictions; use `enforce` and `hard_requirement` for the relevant
controls. Exact declared hostnames can resolve to private addresses, so review
R2 separately. [Security controls](https://docs.nvidia.com/openshell/security/best-practices)

Current provider docs describe placeholder substitution and endpoint-bound
credential use; the README's shorter environment-injection description is
insufficient to decide R4. Prefer the detailed provider contract and verify
the selected release. Plain `--env` secrets remain readable. Managed
`inference.local` routing is a separate path to test against the one-provider
requirement. [Providers](https://docs.nvidia.com/openshell/sandboxes/manage-providers),
[inference routing](https://docs.nvidia.com/openshell/sandboxes/inference-routing),
[sandbox environment](https://docs.nvidia.com/openshell/latest/sandboxes/manage-sandboxes)

**OpenSandbox:** Credential Vault requires the egress sidecar, `dns+nft`
enforcement, an outbound policy and credential proxy enablement. DNS-only
mode is rejected because direct IP traffic could bypass it. Bind credentials
to scheme/host/port/method/path; use default-deny explicitly. The guide warns
about transparent service-mesh conflicts and loss of in-memory vault state on
sidecar replacement. This is promising R3/R4 machinery, with deployment work
still needed to protect its control plane and enforce R2/R6.
[Credential Vault guide](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/guides/credential-vault.md)

**Microsandbox:** network/secret configuration and Docker-in-sandbox workflows
are described upstream. They warrant a local spike, but do not establish DNS
tunnel resistance, private-address resolution safety, credential response
handling, or independent nested-workload policy. Those are explicit unknowns
in §6, not inferred missing features.
[Configuration and examples](https://github.com/superradcompany/microsandbox#readme)

### Cross-platform suitability

All platform claims below were read at primary sources on **2026-09-09**;
none was exercised on Windows or Linux for this comparison. “Native host”
means the sandbox runtime runs on that OS without WSL2; it does **not** mean
that the sandbox runs applications native to the host OS. The Linux guest
used by our AppSec tools is a separate compatibility requirement.

Colima upstream supports Linux and Intel/Apple-silicon macOS. **Our wrapper**
is Mac-specific: it requires Darwin, selects vz, and uses APFS disk clones.
Its recorded validation covers Apple silicon. The guest bootstrap is potentially
reusable on another Ubuntu VM, but depends on its users, Docker, resolver and
network interfaces. A port needs more than different VM-creation commands.
[Colima platforms](https://github.com/abiosoft/colima),
[our wrapper](make-appsec-vm.sh), [guest assumptions](bootstrap-appsec-vm.sh)

| Candidate | macOS host | Linux host | Windows host | Audience implication |
|---|---|---|---|---|
| Colima reference | Apple silicon exercised; upstream also supports Intel | Upstream supported; our host wrapper refuses Linux | No native Windows route documented upstream | Retain as reference; separate host adapters and evidence required |
| Docker sbx | 14+, Apple silicon | Ubuntu 24.04+, amd64/arm64, KVM | Native Windows 11, Intel/AMD x64, WHP | First Windows trial; no WSL2 or Docker Desktop prerequisite listed. Windows ARM64 and Intel Mac are outside the published prerequisites. [Install matrix](https://docs.docker.com/ai/sandboxes/install/) |
| Microsandbox | Apple silicon | KVM | Native WHP route; Windows x64 and arm64 runtime assets published | Promising common local workflow; beta. Published assets do not establish tested OS-edition/architecture parity. [Requirements](https://github.com/superradcompany/microsandbox), [release artifacts](https://github.com/superradcompany/microsandbox/releases) |
| OpenShell | Apple-silicon Docker route; MicroVM driver also documented | Debian/Ubuntu amd64/arm64; choose compute driver | **Experimental WSL2 + Docker Desktop**, x64 | More prerequisites on Windows; no native Windows MicroVM-driver parity established. [Support matrix](https://docs.nvidia.com/openshell/reference/support-matrix) |
| OpenSandbox | Linux runtime through a VM or remote server; local parity untested | Docker/Kubernetes server; configure chosen isolation runtime | Linux runtime through a VM or remote server; Windows-host recipe unvalidated here | Prefer an operator-managed Linux service over assuming Docker Desktop implies secure-runtime support. [Runtime requirements](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/guides/secure-container.md) |
| srt | Native Seatbelt process controls | Native bubblewrap process controls | Native Windows **alpha**, x64/arm64 helper, dedicated user + WFP/ACLs | Executes Windows processes; different boundary from a Linux microVM. One-time elevated installation; not our L1 replacement. [Platform support](https://github.com/anthropics/sandbox-runtime#platform-support) |
| gVisor | Inside Linux VM or remote Linux host | Native `runsc` | Inside Linux VM or remote Linux host | L3 component; installing Docker on the laptop does not install `runsc` in its daemon environment. [Docker setup](https://gvisor.dev/docs/user_guide/quick_start/docker/) |
| Kata | Linux VM with suitable virtualization, or remote service | Hardware-virtualised runtime on compatible hosts | Linux VM with suitable virtualization, or remote service | Nested virtualization and runtime integration need proof; remote deployment is simpler for participants. [Requirements](https://github.com/kata-containers/kata-containers) |
| Firecracker | Remote Linux/KVM, or separately validated nested setup | Native Linux/KVM | Remote Linux/KVM, or separately validated nested setup | Infrastructure component, not a native Windows/macOS install. [VMM requirements](https://github.com/firecracker-microvm/firecracker) |
| E2B infrastructure | Remote client | Self-hosted cloud infrastructure or remote client | Remote client; client tooling still needs testing | Moves VM prerequisites to the service operator. Upstream self-hosting targets GCP/AWS, not a generic laptop installation. [Deployment scope](https://github.com/e2b-dev/infra) |

**Windows installation friction:** sbx's per-user installer does not require
administrator privileges, but enabling WHP uses elevated PowerShell; a
machine-wide MSI is also available. Separate application installation from
permission to enable virtualization. Confirm Windows edition/build, firmware
virtualization, corporate software policy and VDI constraints before the
session. Do not infer a Pro-edition requirement merely from the use of WHP;
the Docker requirements do not specify an edition. Its Windows x64 route is
the proposed first test target, not a Windows support claim for this playbook.
[Windows installation](https://docs.docker.com/ai/sandboxes/install/#windows)

**Windows trial observations (2026-09-09, user-run commands):** WinGet installed
v0.39.0; reinstalling from the official per-user MSI produced v0.42.1. This is
one installation observation, not a claim about all WinGet sources. Diagnostics
reported matching healthy CLI/daemon versions and WHP hypervisor availability.
The Windows edition/build and CPU model were not recorded. The first diagnostic
run was signed out, so authenticated daemon diagnostics were skipped.

The user then successfully created `win-isolation-test` with the OpenCode
template, no workspace argument, 2 CPUs, 4 GiB RAM, the Locked Down preset,
and sandbox-scoped denies for `**`, `0.0.0.0/0`, and `::/0`:

- **R1, mounts:** creation reported no workspace bind mount. Guest `findmnt`
  nevertheless showed the empty host skills directory mounted at
  `/home/agent/.config/opencode/skills` through virtiofs, alongside generated
  `/etc/hosts` and `/etc/resolv.conf` mounts. Mount options and resistance to
  traversal have not been tested. No-workspace creation does not mean zero
  host-backed mounts.
- **R2, host-service route:** requests to
  `http://host.docker.internal:18080` returned a local-rule HTTP 403 through
  the forward proxy and an empty reply (curl exit 52) with explicit proxy
  bypass. Correlated logs recorded both paths as denied by the sandbox's
  wildcard rule, after translation to `localhost:18080`, with `forward` and
  `transparent` proxy types respectively. Host-side canary response and
  listener request logs were requested but not supplied, so listener health
  and absence of guest requests at the listener are not independently
  established. Raw host/LAN addresses and other host-service paths remain
  untested.
- **R3, initial network probes:** the policy listing included broad kit network
  allows plus all three explicit local denies. `sbx policy check` denied
  `api.anthropic.com:443`, citing the sandbox's local wildcard deny. An actual
  HTTPS request through the configured forward proxy received CONNECT 200,
  completed TLS with a Docker Sandboxes Proxy CA-issued certificate, then
  received HTTP 403. CONNECT success and that certificate do not establish
  upstream access. A repeat request returned the body `Blocked by local rule
  for api.anthropic.com:443`; the policy log recorded both requests as blocked
  through the forward proxy by the sandbox's wildcard deny. Direct
  IPv4 (`1.1.1.1`) and IPv6 (`2606:4700:4700::1111`) HTTPS attempts using
  `curl --noproxy "*"` both ended in TLS unexpected EOF (curl exit 35), without
  a completed handshake or HTTP response. Correlated policy log entries
  recorded both IP destinations as blocked through the transparent proxy,
  also by the wildcard deny. This establishes enforcement for these three
  tested HTTPS paths; it does not independently exercise either CIDR deny.
  The log also recorded blocked Ubuntu repository and Docker download
  requests; the processes responsible were not identified. Positive
  controls, non-HTTP traffic, and raw host/LAN reachability remain untested.
- **R3, name resolution (unresolved):** `/etc/resolv.conf` listed the internal
  IPv4 and IPv6 gateways as nameservers, with a sandbox-specific search
  suffix. `getent ahosts gateway.docker.internal` returned both gateway
  addresses. A lookup of `example.com` printed nothing (exit status was not
  captured), while `api.anthropic.com` returned `160.79.104.10` despite its
  confirmed HTTPS deny. This establishes name-resolution success for that
  blocked destination, not an upstream DNS exchange or an exfiltration path.
  A follow-up inspection found no external names in `/etc/hosts`. Explicit
  DNS-backend lookups (`getent -s dns ahostsv4`, with absolute names) resolved
  both `api.anthropic.com.` and `github.com.`, while `example.com.` again
  printed nothing. Thus a hosts-file entry does not explain the result.
  A later policy log attributed queries for `example.com` and its
  search-suffixed variant to `DNS lookup blocked by proxy policy`, with
  `<dns proxy policy>` in the rule column. The negative lookup therefore
  has explicit policy-denial evidence.
  Both successful names appear in the kit allowlist, making different
  resolver/TCP rule evaluation a hypothesis; resolver caches and upstream
  behaviour remain unexamined. DNS isolation is not yet accepted. Use fresh
  labels beneath a controlled domain with authoritative query logs, and a
  positive control, to determine whether denied queries leave the boundary.
  Such logs were unavailable during this trial, so that check is deferred.
- **R4, SSH-agent access:** the evaluated forwarding setting was an explicit
  `false` override. Although `SSH_AUTH_SOCK` had printed `/run/ssh-agent.sock`,
  a later exec that reported starting the sandbox found no socket, and
  `ssh-add -l` failed with `No such file or directory`. No usable agent
  connection was observed in that attempt. A controlled test with a known
  host agent and a disposable key has not been performed.
- **R5, guest-root probes:** `sbx exec -u root` reported uid/gid 0. Its
  forward-proxy HTTPS request to `api.anthropic.com` returned the local-rule
  403; its direct IPv4 request to `1.1.1.1` ended in TLS EOF. Updated policy
  log timestamps and counts attributed both to the same wildcard deny.
  Merely changing the workload uid to root did not bypass these two tested
  restrictions. Attempts to alter enforcement or use management interfaces
  have not been performed.
- **R3/R6, nested-container probes:** the private Docker daemon initially
  listed no images. Subsequent runs used a local `sbx-netprobe:local` curl
  image on its default container network. Direct IPv4 HTTPS to `1.1.1.1`
  ended in TLS EOF; the corresponding transparent-proxy deny count advanced
  from two to three with a matching new timestamp. This confirms denial for
  that nested-container path. Direct IPv6 to `2606:4700:4700::1111` failed
  immediately with `Network is unreachable` (curl exit 7), and its earlier
  proxy log entry did not advance. That attempt did not exercise IPv6 policy
  enforcement. A repeat using the private daemon's `--network=host` reached
  TLS, then failed with EOF; the IPv6 transparent-proxy deny count advanced
  from one to two at the matching new timestamp. This confirms IPv6 denial
  for that additional configuration. It does not validate an IPv6-enabled
  bridge network or all container network modes.
- **R7, nested-workload stop/restart:** a networkless container named
  `sbx-stop-canary`, with restart policy `no`, used the curl probe image plus
  a copied `/usr/bin/sleep` executable. It exited with code 127 approximately
  80 ms after startup, before any requested `sbx stop`. Its required runtime
  dependencies were not checked during preparation. Container logs then
  identified missing `libselinux.so.1`; guest `ldd` also listed libgcc_s,
  libm, libc, libpcre2-8, and the ELF loader. This initial setup failure was
  not a lifecycle result. After copying the dependency set, inspection showed
  the 600-second sleep running from `08:40:17Z`. Host `sbx stop` reported the
  sandbox stopped, and `sbx ls` confirmed that state. A subsequent `sbx exec`
  restarted the sandbox; inspection showed the canary exited, with the same
  start timestamp, finish time `08:40:47Z`, and exit code 255. The running
  canary was interrupted and did not resume with restart policy `no` in this
  test. This does not establish graceful shutdown, behaviour under other
  restart policies, clean deletion/recreation, or credential revocation.

These observations cover initial Windows startup, configuration, selected
network paths, and one stop/restart case; they do not complete the R1–R8
acceptance probes.

**WSL2 needs its own boundary review.** By default, fixed Windows drives are
mounted under `/mnt`, Windows executable interop is enabled, and Windows PATH
entries are imported. Disabling automount alone does not prohibit manual
mounts. A daily-use WSL distribution therefore does not meet R1 simply because
it runs Linux. Inspect what the actual workload can reach through its inner
sandbox, including Windows processes and management sockets. Avoid changes
to a participant's existing global WSL configuration as an onboarding step.
[WSL settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)

WSL networking also varies: NAT and mirrored mode have different host/LAN
reachability, and DNS tunneling delegates resolution to Windows. Repeat R2/R3
under the actual networking/VPN setup; a Linux UDP/53 test alone is insufficient.
These host integration paths do not prove an inner container sandbox fails,
but they must be outside its permitted reach.
[WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking)

**Native Windows execution is a separate need.** A Windows laptop running a
Linux sandbox does not validate a Windows-only target or reproducer. srt's
Windows alpha can restrict Windows processes, but its README documents system
resolver DNS outside the egress fence, certificate-revocation limitations and
different filesystem-rule behaviour. Do not inherit the Linux rating or make
disabling certificate checks a baseline workaround.
[Windows security limitations](https://github.com/anthropics/sandbox-runtime#windows-alpha)

Microsoft **Windows Sandbox** is another Windows-workload candidate, outside
the Linux-agent shortlist: a disposable Windows environment using hypervisor
isolation, unavailable on Home edition. Its configuration supports disabling
networking/clipboard and controlling mapped folders, but networking and
clipboard sharing are enabled by default. It could help R1/R7 for Windows-only
reproducers; an online agent still needs our R3 egress and R4 credential design,
and R8 controlled export before disposal. It is not a ready-made substitute
for the Ubuntu/Docker/gVisor stack.
[Overview and editions](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/),
[Configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)

**Proposed audience coverage:** first validate Windows 11 x64, Apple-silicon
macOS and Ubuntu 24.04+ x64. Add Linux arm64, Windows ARM64 and Intel Mac when
audience demand and candidate support justify separate tests. For managed
laptops or VDI without usable virtualization, provide an operator-managed
remote Linux sandbox with the same acceptance contract. That fallback is
still to be built: it requires explicit handling of code residency, service
operator access, network position and upload/download credentials (A2/A4/A5),
plus a working client workflow. Do not fall back to unrestricted host execution.

## 5. Capability-to-threat matrix

**D** = relevant documented mechanism, requiring configuration and testing;
**P** = partial or backend-dependent; **W** = our workflow/integration must
supply it; **?** = not established by the reviewed sources. These marks are
our assessment of the sources in §3/§4, **not pass/fail results**. A cell can
address only part of its requirement; qualifications above take precedence.
No alternative earns full acceptance from this table.

| Backend | R1 host data / outer boundary | R2 reachability | R3 egress | R4 import / credentials | R5 control plane | R6 reproducers / targets | R7 lifecycle / budget | R8 evidence / review |
|---|---|---|---|---|---|---|---|---|
| Colima v0.2 scripts | P: VM, launch gaps | P: direct blocks; forwarding/proxy gaps | P: DNS/allowlist gaps | P: manual import, raw key | P: uid split, mutable home | P: admin-run `runsc`, manual target | P: manual reset/cap | P: trusted network logs; manual export |
| Docker sbx, macOS shell trial | P: VM; no workspace/skills shares tested | P: ports checked; hostname/private-IP gap | P: TCP denies and npm access tested; DNS unresolved | P: filtered import tested; raw tmpfs key | P: external policy and unprivileged entry | P: separate VM tested; gVisor failed | P: stop/reset tested; cap/deadline W | P: logs and opaque export; review W |
| Microsandbox | D: microVM | P: test private/host paths | D: network configuration; DNS ? | P: secret mechanism; import W | P: host controls; guest config W | P: execution/Docker; independent policy ? | P: lifecycle; budgets W | P: inspection; trusted evidence ? |
| OpenShell, selected driver | P: VM option, filesystem rules | P: exact internal-host exceptions | D: proxy + optional L7 | P: provider/routing; import W | D: static/dynamic policy split | P: process policy; target topology W | P: lifecycle; budgets W | P: denial logs; review W |
| OpenSandbox + selected runtime | P: selected runtime determines boundary | P: configure ingress/egress | D: sidecar, use `dns+nft` | P: Vault; import W | P: server/sidecar isolation W | P: workload runtime/topology W | P: timeout/lifecycle; spend W | P: execution logs; external retention W |
| srt inside our VM | P: process restrictions; outer VM retained | P: proxy/socket policy | P: domain policy; platform DNS ? | W: imports/key broker | P: filesystem restrictions | P: process layer; no separate kernel | W: clean environment/budget | P: violation monitoring; review W |
| gVisor + operator platform | P: application-kernel boundary | W | W | W | P: runtime boundary; policy W | D: generated-code isolation | W | W |
| Kata + operator platform | D: guest kernel | W | W | W | P: external runtime; policy W | D: VM-backed containers | W | W |
| Firecracker + operator platform | D: microVM | W | W | W | P: host VMM/jailer; policy W | D: separate microVMs | P: VM controls; workflow W | P: VMM logs; run evidence W |
| E2B self-hosted deployment | D: Firecracker integration | ? | ? | W: verify chosen deployment | P: service control plane | P: workload environment; topology W | P: platform lifecycle; budgets W | ?: deployment-specific |

R1–R8 cover every threat identifier, including T20a/T20b, through the model's
§12 mapping. Particularly important shared residuals are T12/T14/T27 (allowed
recipients), T22/T23 (loaded config and persistent state), T25/T26 (authority
and spend), and T31 (finding integrity). Neither a VM nor a proxy decides
whether a reported vulnerability is true or a generated patch is acceptable.

**Selection by next use case:** sbx and Microsandbox for local backend
evaluation; OpenShell for granular process/API policy; OpenSandbox or Kata
with a surrounding platform for a future internal service; Firecracker/E2B
when operating microVM infrastructure is itself in scope. Keep gVisor as a
reproducer component and srt as optional process-level defence in depth.
This ordering reflects fit and integration work, not measured security or
performance superiority.

## 6. Acceptance probes before substitution

Run in a fresh disposable environment with synthetic data and disposable
credentials. Use an operator-controlled endpoint for network observations;
do not send real secrets or repository contents in probes. A failed client
request alone is not evidence that the intended boundary blocked it.

| Probe / mapped threats | Required evidence |
|---|---|
| Host-data canaries — T01 T04 T06 | Only the intentionally imported canary is readable. Outside-workspace paths, ignored `.env`, Git metadata, hard links/symlinks, skills stores and host identity are checked separately; inspect actual mounts |
| Privilege and policy — T07 T08 T09 | As the actual workload uid, attempt to alter enforcement or access management sockets. For sbx, repeat as guest root; outside policy must remain effective. Never mount the host Docker socket |
| Direct egress — T11 T15 T16 T18 T21 | Actual harness subprocess and default-runtime container try controlled disallowed destinations with proxy variables removed and explicit bypass, over both IP families. Correlated host/proxy/firewall evidence shows denial |
| DNS and address resolution — T13 T16 | UDP and TCP resolver queries, alternate resolvers, container DNS, unlisted DoH and allowed hostnames resolving to test private/link-local addresses. Upstream observations demonstrate no unintended lookup or connection; test resolution changes on reconnect |
| Allowed API paths — T12 T14 T24 T27 | Selected model and registry work; second provider, code host and unrelated endpoints fail. Test CONNECT destination, TLS SNI and HTTP Host mismatches and redirects with controlled servers. Record what remains possible on allowed APIs |
| Credential authority — T24 T25 T26 | Dummy raw secret absent from env/files/process views and client-visible proxy responses; permitted API request authenticates. A dependency cannot use an unrelated service credential or SSH signing agent. Spend limit and revocation tested separately |
| Inbound and target effects — T03 T17 T20a T20b T21 | Guest/target listeners are unreachable from host and LAN unless explicitly sanctioned. Target can reach only local stand-ins; no real integration creds. Run a separate §9 staging test if needed |
| Configuration and host integrations — T05 T22 T23 T28 T31 | Harmless marker hooks/plugins/environment files are stripped or cannot execute outside the workload. No host MCP, lifecycle hook or shared-store path grants authority. Inspect resulting effective harness config |
| Reproducer containment — T19 | Generated code is launched by the intended independent controller/runtime, with no credential and no network. Show the harness cannot widen that policy. Do not equate a smoke test with proof against kernel/hypervisor escape (T02) |
| Clean reset and failure — T01 T23 T26 T29 T32 | Plant markers in writable home/tool/config/cache locations, then exercise the clean-start workflow. Markers disappear. Inspection/transport failure refuses launch. Stop kills remaining processes/containers; state disposal and secret revocation are separate observations |
| Evidence/export — T05 T10 T30 T31 | Workload cannot rewrite enforcement records. Host exports carry run identity, timestamps, policy/version references and hashes; session logs remain labelled agent-writable. Control-character output and findings are reviewed without automatic execution |

Record platform/architecture, backend and guest versions, image digests,
effective policies, exact probes, observed outcomes and residual-risk
acceptances alongside the [run record](../triage/observations.md). Recheck after
an upgrade, changed kit/template, auth mode, mount, network policy or workload
type. Preserve earlier Colima evidence as historical, not a substitute for
this backend-specific acceptance record.

### Additional platform acceptance checks

These extend R1–R8; they do not create a separate threat model for Windows.
Record pass/fail **per host OS, architecture and execution backend**. A Mac
pass is not a Windows pass, and a WSL2 pass is not a native-WHP pass.

| Check | Evidence required before publishing a platform recipe |
|---|---|
| Installation and support | Exact OS edition/build, architecture, backend release, guest image and prerequisites; test standard-user daily operation after any documented admin setup. Fail clearly on unsupported virtualization/VDI |
| Files and identity — R1/R4/R5 | Exercise imports from paths with spaces and non-ASCII names; CRLF/scripts, executable bits and case differences; test NTFS reparse points/junctions, links, UNC/SMB paths, user-profile data, credential stores, named pipes and any WSL drive/interop path for unintended access |
| Network and auth — R2/R3/R4 | Repeat direct/container/DNS/private-address tests on the actual VPN, DNS and corporate proxy configuration; verify TLS trust and credential injection without exposing host secrets or disabling certificate validation |
| Workload compatibility — R6 | One real harness, dependency install, containerised AppSec tool, synthetic target and isolated reproducer on the guest architecture; record unavailable syscall/runtime/image combinations and Windows-only target needs |
| Lifecycle — R7 | A host-side stop works after terminal closure and workload failure, kills descendants/containers, and leaves unrelated environments running. Test clean reset and credential revocation; closing a PowerShell window or WSL shell is not sufficient evidence |
| Evidence and onboarding — R8 | Export logs/findings without unsafe terminal rendering; verify Unicode/path handling. A participant can follow the platform-specific create/import/run/export/stop steps without translating Bash commands or editing firewall rules manually |

For a Windows wrapper, choose PowerShell or a genuinely cross-platform CLI;
retain the same workflow and data contract. Do not present Git Bash as a port
of the current Darwin/vz/APFS wrapper. The initial Windows observations in §4
do not complete platform acceptance; the minimum useful deliverable is a
tested recipe plus its acceptance record.

## 7. Next implementation work

1. Close Colima's near-term M3/M1/M2/M19/M13/M5/M4/M20/M21 gaps and repeat
   the affected probes. This gives the pilot a usable baseline independent
   of which alternative succeeds.
2. Extend the [implemented macOS sbx shell workflow](sbx/README.md).
   Resolve the DNS-policy discrepancy and private-address hostname cases;
   exercise an authenticated OpenCode run and a containerised AppSec tool,
   and evaluate managed credentials against the current raw-key path.
   Prioritise Windows 11 x64 alongside macOS and Ubuntu; publish a Windows
   operating recipe and independent stop action after the platform checks pass.
3. Run the same acceptance suite against Microsandbox. Investigate OpenShell
   if method/path enforcement or process-specific policy is needed; require
   explicit blocking and kernel-support settings.
   Compare its Windows installation and workflow directly with sbx, and define
   the remote Linux fallback for participants unable to enable virtualization.
4. Adopt another backend only when its acceptance record covers the required
   rows and documents any deliberate relaxation. Publish the wrapper,
   configuration and evidence together.
