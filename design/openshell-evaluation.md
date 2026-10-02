# OpenShell as a backend, inner layer or design reference for appsec-sbx

**Status:** draft v0.1, 2026-09-23. Source review only; nothing was installed or run. Product claims are
`verified-at-source` against the OpenShell repository at commit [`d3480d2`][head] (main, 2026-09-23), the
tag [`v0.0.116`][v116] (latest GitHub release, 2026-08-28) and the documentation channels
`docs.nvidia.com/openshell/latest` (matches v0.0.116) and `/dev` (matches main). Everything about running
OpenShell on our hosts is `not-yet-tested`. This deepens the OpenShell rows of the
[sandbox comparison](sandbox-comparison.md) (§4, §5, §7 item 3; 2026-09-09); §7 records their drift. The
wrapper contract in §6 was read from `sandbox/sbx/appsec_sbx/` on branch `sbx-045-compat`.
2026-10-02: wrapper 0.4.0 adopted sbx's proxy-managed credentials, which answer recommendation
1 (C) for the placeholder and revocation parts; M17 is partial, see
[sbx-managed-credentials.md](sbx-managed-credentials.md). §6's key-file rows describe the earlier wrapper.

## 1. Summary

OpenShell is a control plane (the gateway) plus a per-sandbox trusted supervisor that runs outside the
workload and enforces a YAML policy: Landlock filesystem rules, one non-root process identity under
seccomp, and allow-only egress with optional HTTP method/path inspection, TLS termination and
endpoint-bound credential substitution. Compute is pluggable: Docker, Podman, Kubernetes and a libkrun
microVM driver exist; a native Windows driver is an RFC. [readme] [how]

Three findings decide the fit.

1. The boundary depends on the driver. Docker and Podman sandboxes share one kernel (on macOS, Docker
   Desktop's single Linux VM). Only the `vm` driver gives a kernel per sandbox; it is opt-in, has no
   Windows build and its own README calls it experimental. sbx gives every sandbox its own microVM on
   all three hosts. [matrix] [drivers] [vm-readme]
2. The provider contract is the design our open measure M17 asks for: an opaque placeholder in the
   workload, substitution at the proxy only after network policy and profile binding both admit the
   request, fail-closed mismatches. It presupposes TLS termination (our deferred M10). [providers] [bp]
3. The project is alpha and mid-migration. The 0.1.0 prerelease removed the `inference.local` router,
   made provider profiles import-only, replaced the default image and renamed CLI verbs; `latest`
   documentation still describes the old behaviour. [rel-notes] [inference-latest]

Recommendation (§9): take the provider contract as the M17 design reference first (C), run one bounded
probe of OpenShell inside the sbx guest (B), defer the backend swap (A) until the `vm` driver is stable
on our three hosts, and list the shared-service option (D) beside OpenSandbox and Kata in the comparison.

## 2. What OpenShell is now

| Component | Role | Where it runs | Source |
|---|---|---|---|
| `openshell` CLI, TUI, SDKs (Python, TypeScript, Go, Rust) | User interface to the gateway over gRPC/HTTP | Workstation | [how] [readme] |
| `openshell-gateway` | Control plane: sandbox records, policy revisions, provider credentials, settings, relays; SQLite by default | Local systemd/Homebrew service on `127.0.0.1:17670` with generated mTLS, a container, or Kubernetes | [how] [install] |
| Compute driver | Provisions the workload, the supervisor, their protected channel and an outer network fence | In the gateway process, as a subprocess (`vm`) or behind an extension socket | [runtimes] [drivers] |
| `openshell-supervisor` | Trusted side: gateway session, OPA policy engine, CONNECT proxy, interception CA, credentials, DNS, SSH relay, logs. Never executes inside the workload | Companion container (Docker/Podman), separate pod (Kubernetes), host process (`vm`) | [sandbox-arch] [docker-readme] |
| `openshell-sandbox` | PID 1 inside the workload, same UID as the agent: seccomp broker, Landlock baseline, exec/PTY, binary identity | Workload container or guest | [sandbox-arch] |
| `openshell-prover` | Standalone Z3-backed check that a candidate policy is contained in a boundary policy; needs no gateway | Workstation or CI | [prover] |

**Release and maturity.** The README badge says alpha. `v0.0.116` (2026-08-28) is the newest GitHub
release; prerelease tags `v0.1.0-pre.1` to `pre.7` (`pre.7` at [`f8002d1`][pre7], 2026-09-22) publish only
as GitHub Actions artifacts behind `gh auth`. The 0.1.0 milestone is due 2026-09-29 (9 open, 41 closed).
Its release notes list breaking changes: default image `nvcr.io/nvidia/base/ubuntu:24.04` without agent
CLIs, no catalog names or Dockerfile builds in `--from`, import-only provider profiles, no
command-to-provider inference, `tls` reduced to omit-or-`skip`. [readme] [v116] [milestone] [rel-notes]

**Licence, NVIDIA dependencies, telemetry.** Apache-2.0. No GPU is required; passthrough is experimental.
The CLI needs no NVIDIA account. The default workload image comes from NVIDIA's registry `nvcr.io`, the
gateway image from `ghcr.io`; an anonymous `nvcr.io` pull is `not-yet-tested`. The installer is `curl |
sh` into Homebrew, Debian or RPM packages, with a separate Snap; the Homebrew formula is a release asset,
consistent with `brew info openshell` finding nothing in the default taps on 2026-09-23. Release assets
cover macOS arm64 and Linux x86_64/arm64 only. Telemetry is on by default in the gateway and propagated
to sandboxes (anonymous categories and counts); `OPENSHELL_TELEMETRY_ENABLED=false` disables it and a
build flag compiles it out. [readme] [install] [v116] [telemetry]

**NemoClaw and OpenClaw** (secondary). NemoClaw is NVIDIA's reference stack running OpenClaw, Hermes or
LangChain Deep Agents inside OpenShell with managed inference, presets and snapshots; the OpenShell
README defers OpenClaw support to it. [readme] [nemoclaw]

## 3. Compute drivers and the isolation boundary

| Driver | Boundary | Egress fence | Hosts | Status label |
|---|---|---|---|---|
| Docker | Two capability-free containers per sandbox on the host kernel; on macOS inside Docker Desktop's one Linux VM | Workload `network_mode=none`; supervisor on host networking. Docker Desktop must enable host networking, incompatible with Enhanced Container Isolation | Linux, macOS (Docker Desktop), Windows via WSL 2 + Docker Desktop | Supported; Windows route experimental |
| Podman | Rootless paired containers, host kernel | Workload `network=none` | Linux (Podman 5, cgroups v2); macOS via `podman machine` | Supported |
| `vm` (MicroVM) | One libkrun VM per sandbox, own kernel; guest boots with no NIC; workload syscalls mediated over vsock to a host supervisor | Absent NIC | macOS Hypervisor.framework, Linux KVM; no Windows | "Supported" in the support matrix, "Experimental" in the architecture table and driver README; never auto-detected; `--cpu`/`--memory` ignored, sizing is gateway-wide |
| Kubernetes | Pod pair; optional `runtime_class_name` such as `kata-containers` | Namespace-wide empty-egress NetworkPolicy; operator must confirm CNI enforcement | Cluster 1.29+ via Helm | Supported; deployment path "experimental" in the README |
| `mxc` (native Windows) | Microsoft Execution Container (AppContainer) with a host-side CONNECT proxy in the gateway process; no OpenShell binary inside | MXC `network.proxy` redirect | Windows 11 preview builds, x64/ARM64 | RFC 0013 in review; config documented; no release asset |

**Kernel requirements apply to every Linux driver, including inside a VM:** Landlock ABI 3 (Linux 6.2)
enabled, seccomp user-notification with `SECCOMP_IOCTL_NOTIF_ADDFD`, and same-UID task-memory access;
the sandbox probes them and fails closed. `WAIT_KILLABLE_RECV` (5.19) is recommended. The `latest` matrix
still lists Landlock as "Recommended"; main lists it as "Required". Against sbx's one microVM per sandbox
on macOS, Windows (WHP) and Ubuntu (KVM), OpenShell reaches a per-sandbox kernel only through `vm` on
macOS and Linux; the documented Windows route is a shared Docker Desktop VM under WSL 2, and native MXC
would give an AppContainer. Table sources: [drivers] [runtimes] [matrix] [vm-readme] [docker-readme]
[rfc13] [gw-config] [readme]; kernel: [matrix] [matrix-latest].

## 4. Policy model

**Static and dynamic.** `filesystem_policy`, `landlock` and `process` are locked at creation;
`network_policies` and `network_middlewares` hot-reload through `policy update` (merge) or `policy set`
(replace), closing connections pinned to the previous generation. A gateway-global policy replaces every
sandbox policy, rejects sandbox-level updates and suppresses provider-derived rules. [policies] [schema]

**Filesystem.** A mandatory Landlock baseline hides the supervisor channel and bootstrap files and
requires ABI 3; startup fails without it. The configured policy adds read-only and read-write paths;
anything unlisted is inaccessible. `compatibility: best_effort` (default) skips paths it cannot apply and
emits a High-severity finding; `hard_requirement` aborts startup. The default grants `/usr`, `/lib`,
`/etc`, `/proc`, `/var/log` read-only and `/tmp` plus the working directory read-write; that directory is
also `HOME`: harness state, skills and target share one writable tree. [bp] [default-policy] [drivers]

**Process.** One immutable non-root UID/GID for the sandbox and every child, zero capabilities,
`no_new_privs`, `RLIMIT_CORE=0`. The runtime seccomp filter blocks `mount`, the new mount API,
`pivot_root`, `setns`, `unshare`/`clone` with `CLONE_NEWUSER`, `ptrace`, `process_vm_*`, `bpf`,
`io_uring_setup`, `memfd_create` and nested `seccomp` filters. No root exec, no sudo path. [bp] [sandbox-arch]

**Network.** Egress is denied unless a `network_policies` block names the host, port and calling binary.
Binaries are identified by `/proc/<pid>/exe` and hashed on first use. Endpoints without `protocol` are L4
passthrough through the explicit proxy; `protocol: tcp` gives mediated DNS plus transparent TCP for
native clients (Docker/Podman only, IPv4 only); `rest`, `websocket`, `graphql`, `mcp` and `json-rpc`
enable L7 rules. Presets `read-only`, `read-write` and `full` expand to method sets; `deny_rules` exist
only at L7. Host wildcards are limited to the first DNS label. There is no L4 deny rule: denial is the
absence of an allow, per sandbox, so nothing corresponds to the inherited global grants our sbx compiler
subtracts. L7 `enforcement` defaults to `audit` (violations logged and forwarded); `enforce` returns 403;
other values are rejected. The example profiles set `enforce`; the docs still advise starting in `audit`.
[bp] [schema] [policies] [profiles-dir]

**TLS.** The proxy peeks each tunnel, terminates TLS with a per-sandbox ephemeral CA and injects that CA
through `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `CURL_CA_BUNDLE`, `REQUESTS_CA_BUNDLE`, `GIT_SSL_CAINFO`
and `DENO_CERT`. `tls: skip` disables inspection and credential rewriting for that endpoint; a
credentialed endpoint rejects `skip` and L4 mode unless `allow_uninspected_credentials: true`. [bp] [schema]

**Who can change policy.** Policy lives at the gateway and is applied by the supervisor; the workload has
no network route to the gateway and no gateway credential. Two paths widen a running sandbox from
outside: operator approval of blocked endpoints in the TUI (on by default, persists until recreation) and
the policy advisor, off by default, where the agent proposes a rule through `policy.local` and a human
approves it; an opt-in auto mode approves only proposals with an empty prover delta and no security
notes, and proposals can never request `protocol: tcp`, `tls: skip` or private addresses. `policy list`
records every revision with provenance. [bp] [advisor] [sec-arch] [docker-readme]

**DNS.** The workload has no network interface. DNS goes to a sandbox-local resolver at `127.0.0.53` and
is mediated over the supervisor channel; UDP other than DNS is unsupported. The supervisor resolves names
and applies hostname policy; resolution never grants access. Wildcard `tcp` hostnames are a documented
DNS-label exfiltration channel. [sandbox-arch] [bp] [policies]

**Private and loopback addresses.** After policy admits a connection the proxy resolves and checks the
address. Exact hostnames declared in user policy may resolve to RFC 1918 space; wildcard, hostless and
advisor-proposed endpoints need `allowed_ips`. `127.0.0.0/8`, `169.254.0.0/16` and `0.0.0.0` are always
blocked. IPv6 appears only as advisory prover notes (`fc00::/7`, `fe80::/10`); `::1` is not named.
`host.openshell.internal` is the sanctioned route to gateway-host services. [bp] [sec-arch] [inference]

**Decision logs.** Network, HTTP, process, filesystem and configuration events are OCSF records in a
dated file inside the sandbox (`/var/log/openshell.<date>.log`), pushed to a bounded in-memory gateway
buffer that a restart discards, and optionally exported as OCSF JSONL; `openshell logs` reads the buffer.
Durable retention outside workload authority means shipping the JSONL to a collector. [logging] [ocsf]

## 5. Providers and credentials (M17, R4)

A **provider** is a credential record at the gateway. A **profile** declares the credential variables,
the endpoints they may reach, the client binaries and optional refresh. Since 0.1.0 a gateway serves only
imported profiles; `providers/` holds examples for Anthropic, OpenAI, Claude Code, Codex, Copilot,
Cursor, DeepInfra, GitHub, Google Cloud/Vertex, NVIDIA, AWS and PyPI. There is no OpenRouter or DeepSeek
example, so both of our OpenCode presets need a short custom profile. [providers] [profiles-dir] [rel-notes]

**Injection.** The agent environment carries an opaque placeholder per credential. On an HTTP request
the proxy substitutes the value in a header, Basic-auth blob, query parameter or path segment; in request
bodies (bounded at 256 KiB) and WebSocket text only when the endpoint opts in; or by SigV4 signing. Two
checks must pass: network policy admits binary and destination, and the profile binds that host, port
and path; otherwise 403 `credential_endpoint_mismatch` and a finding. A placeholder printed into a
request body is forwarded as text. `provider list` prints key names only; stored values are never
exported. `--env` values are plain and trigger a warning. Rotation and detach apply at the next
resolution; a new variable needs a new process. The docs state the agent process never sees the real
value and the workload receives neither the interception CA key nor the gateway credential. This holds
only on inspected paths: `tls: skip` and non-HTTP tunnels cannot carry a managed credential. sbx's managed
credentials rest on the same premise; its proxy CA appeared in the Windows trial. [providers] [policies]
[sandboxes] [docker-readme] [bp]

**One provider, one endpoint.** `inference.local` and `openshell inference set` are removed on main; the
workload calls the provider's native URL and the profile supplies the allowlist. The one-provider
requirement (M2) becomes: attach exactly one provider, add no other `network_policies`, and confirm with
`policy get --full` and `openshell-prover check` against a boundary listing only that host. Subscription
seats (Claude Code browser login, Codex device auth) are outside the profile model; those tokens would
land in the writable workdir as they do today. [inference] [providers] [prover]

## 6. Lifecycle primitives against the wrapper's sbx contract

Primitives from `sbxcli.py`, `lifecycle.py` and `policy.py`; OpenShell verbs: [man] [sandboxes] [policies].

| sbx primitive (wrapper use) | OpenShell equivalent | Gap |
|---|---|---|
| `sbx version` floor v0.45.0 (`preflight`) | `openshell --version`, `openshell status` for the gateway | CLI and gateway version separately; pin both |
| `settings get ssh.agentForwardingEnabled`, `mcp ls` (preflight) | No agent forwarding or MCP gateway feature; `connect` is gateway-brokered SSH to a Unix socket | Confirm `connect` forwards no agent (`not-yet-tested`) |
| `create <kit> --skills off --cpus --memory --deny-network …` | `sandbox create --from <image> --policy <yaml> --cpu --memory --name` | No kit or in-guest bootstrap: the toolchain goes into an image; denies are absence; `vm` ignores `--cpu`/`--memory` |
| `ls --json`, `inspect --json`, `ports --json` (`owned`, `isolation`) | `sandbox list -o json`, `sandbox get -o json` (phase, policy source, revision), `service list`, `forward list` | Mount inspection via `exec findmnt`; host mounts are off unless an operator disables admission |
| `exec -u root …` (bootstrap, guards, key file, cleanup) | None: every process runs as the one workload identity | Provisioning moves to the image build; guards run as the workload or via `sandbox get` |
| `exec -i` binary stdin (archive upload), `exec -it` (shell) | `sandbox exec -n … --no-login-shell` with piped stdin; `--tty`; `connect` attaches to the main process | Binary stdin fidelity `not-yet-tested`; the default login shell sources profile files |
| `cp` (bootstrap script, `put`) | `sandbox upload SRC DST`; `--upload` at create | Preserves symlinks and honours `.gitignore`; keep our host-side packer |
| `exec tar … > archive` (opaque export) | `sandbox download` extracts on the host, sources limited to the workdir | Opaque archive needs `exec` with binary stdout or download of one archive file; `not-yet-tested` |
| `policy allow/deny/rm --force`, `policy check --json`, `policy ls --json` (`lock_policy`, `validate_policy`) | `policy set --wait`, `policy update`, `policy get --full/--base`, `policy list`, `openshell-prover check` | Allow-only per sandbox: no inherited grants to subtract; provider-derived rules and TUI approvals can widen a running sandbox; compare revisions |
| `policy log --limit 30` (`logs`) | `openshell logs --since --source sandbox`, OCSF JSONL | Gateway buffer is not durable |
| `stop`, `rm --force` | `sandbox stop`, `sandbox delete` (`deletion accepted`, may complete later) | Stop keeps state; delete purges credentials; poll until gone |
| `template save` on a stopped VM, `create --template` (`reset`, `repro-create`) | None. Workload templates store image, env and resources; state is not snapshotted | Reset = delete and recreate from a digest-pinned image; the clean template is the image |
| runsc probe, `docker load` (reproducer boundary) | Not possible inside a sandbox: seccomp blocks `mount`, `unshare`, `setns`; zero capabilities; no network | Reproducer = a second sandbox with an empty policy, same boundary class as the primary |
| Idle stop (credential hint) | None documented; `--no-keep`, `exec --timeout`, 300 s provisioning window, 24 h SSH session TTL | No sandbox deadline: M15 stays wrapper work |

## 7. Drift since the 2026-09-09 comparison

| Comparison claim | On `latest` (v0.0.116) [bp-latest] [matrix-latest] [inference-latest] | On main (`d3480d2`) [bp] [bp-dev] [matrix] [inference] [schema] [readme] [rfc13] | Verdict |
|---|---|---|---|
| L7 `enforcement: audit` is the default | Yes | Yes; the schema keeps "the audit default" and the docs still advise starting in audit | Holds; profiles set `enforce` explicitly |
| Landlock `best_effort` can continue without the intended restrictions | Yes: "continues without those restrictions" on unsupported kernels; Landlock "Recommended" | Superseded: a mandatory ABI 3 baseline fails startup; `best_effort` can only skip additional paths; Landlock "Required" | Rewrite when the comparison is next revised |
| Exact declared hostnames can resolve to private addresses | Yes | Yes; loopback, link-local and `0.0.0.0` always blocked; IPv6 loopback not named | Holds; R2 review still required |
| README "environment injection" vs provider docs' placeholder substitution | README: "injected as environment variables at runtime" | Same README sentence; provider docs and the README's "How it works" both describe placeholders bound to endpoints | The README sentence is loose; the mechanism is placeholder substitution |
| "Managed `inference.local` routing is a separate path to test" | Present, with `openshell inference set` | Removed; native endpoints through profiles | No longer applicable on main |
| Docker, Podman, Kubernetes, MicroVM drivers documented | Yes | Plus `mxc` in gateway config and RFC 0013 | Holds; add Windows native as an RFC |
| Windows: experimental WSL 2 + Docker Desktop | Yes | Unchanged | Holds |

## 8. Integration options

### A. Alternative backend behind the wrapper

**Buys.** By construction: one non-root identity with no sudo or Docker (R5, T07–T09), toolchain in
read-only image layers (M12), a digest-pinned image as the clean baseline (M13, M16), method/path rules
per binary (finer than M1), credentials outside the workload (M17, R4), no host mounts by default (R1).
The `vm` driver would keep a kernel per sandbox on macOS and Linux.

**Costs.** No root exec, so `bootstrap.sh` becomes a Dockerfile; no state snapshot, so `reset` becomes
delete plus recreate; no in-sandbox Docker or runsc, so reproducers become sibling sandboxes; no idle
stop or sandbox deadline; Windows has no per-sandbox kernel and `vm` ignores `--cpu`/`--memory`; a
gateway service and a second policy language to operate; prerelease churn until 0.1.0 settles. R6 is
weaker than today's separate sbx VM unless `vm` is used everywhere.

**First probe.** `compute_driver = "vm"` on the Mac: create from a local image, `exec` a binary stdin
round trip, `download` a `tar` produced by `exec`, delete and recreate from the same digest, and confirm
`sandbox get -o json` reports the VM generation. A failure on the stdin or export path falsifies A.

### B. Inner layer inside the sbx VM

Run the OpenShell gateway with the Docker driver inside our Ubuntu guest, with the harness image as the
workload. sbx keeps the VM and the outer network policy; OpenShell adds L7 method/path rules,
binary-scoped egress, Landlock and seccomp around the harness process, and the credential proxy.

**Buys.** L7 control over the model API (the T12/T14 residual the comparison lists), process policy
(M11, M12 by construction), an M17 proxy without writing one, decision logs the harness cannot edit.

**Costs.** The guest needs Landlock ABI 3 and the seccomp features. The acceptance records show kernel
7.0.12 on both the x86_64 and the arm64 guest, above the 6.2 floor, but whether Landlock is in the
guest's LSM list is unrecorded. Two proxies in
series: OpenShell's supervisor resolves names and dials out through sbx's transparent proxy, so DNS and
IPv6 need re-probing at both layers (M5, M19). The gateway runs as `admin` with the guest Docker socket;
`appsec` drives `openshell` against the local mTLS gateway. The supervisor and workload images add
`ghcr.io` and `nvcr.io` to the bootstrap allowlist (M24); overhead inside an 8 GiB VM is unknown.

**First probe.** In a fresh guest as `admin`: `cat /sys/kernel/security/lsm` and `uname -r`; run the
container gateway with the guest Docker socket; create a sandbox from `nvcr.io/nvidia/base/ubuntu:24.04`;
read the qualification output for `seccomp_listener_mode`. A missing Landlock LSM or a failed seccomp
probe falsifies B on that guest. Second probe: with only an OpenRouter profile attached and
`enforcement: enforce`, `GET /api/v1/models` succeeds, a request from a binary outside `binaries` is
denied, and `printenv` shows the placeholder, all visible in `openshell logs`. [container-gw] [matrix]

### C. Design reference for M17

Adopt the contract, not the software, for our credential-holding proxy:

- placeholder in the workload environment, real value only on the host side;
- resolution bound to host, port and path of one declared endpoint, evaluated after the network
  decision, failing closed with a distinct error and a logged finding that excludes secret and placeholder;
- substitution in headers, query and path by default; body rewriting as an explicit opt-in with a size
  bound; no rewriting of cookies, responses or binary frames;
- placeholder text inside bodies forwarded unchanged, so a leaked placeholder is harmless;
- rotation and revocation at the proxy, immediate for new requests;
- TLS termination with a per-run CA injected through the standard trust variables, which makes M10 a
  prerequisite of M17.

**Buys.** Closes M17's design, gives R4 its "credentials held outside the workload" evidence, and removes
the raw key from `/run/appsec/env`. **Costs.** A proxy to build and validate on sbx, or a check whether
sbx's own proxy-managed credentials already meet this contract (work item 2 of the comparison), plus
acceptance of TLS interception for the model host.

**First probe.** With a dummy key and a controlled endpoint: the harness authenticates; `printenv`,
`/proc/*/environ` and the filesystem show only the placeholder; the same placeholder sent to a second
allowed host is refused. [providers] [policies]

### D. Operator-hosted gateway as a future shared service

The Kubernetes driver places the supervisor in its own pod, fences workloads with a namespace-wide
NetworkPolicy, supports `runtime_class_name` for Kata, scopes providers and policies per workspace with
OIDC roles, and exports OCSF JSONL. Against the comparison's OpenSandbox and Kata rows it supplies the
policy language, credential proxy and operator-approval workflow those rows mark "W". It needs a cluster
with an enforcing CNI, the Agent Sandbox controller and, for a guest kernel, Kata; the default pod boundary
must not inherit the Kata rating. Revisit with the remote Linux fallback. [drivers] [workspaces] [ocsf]

### Coverage summary (comparison legend: D documented, P partial, W our work)

| Option | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | Open measures touched |
|---|---|---|---|---|---|---|---|---|---|
| A, `vm` driver | D | P: exact-host private resolution | D: allow-only, L7, binary-scoped; DNS mediated | D: placeholders | D: single identity, static policy | P: sibling sandbox, no runsc | P: no deadline, no idle stop | P: file plus volatile buffer | M11 M12 M13 M16 M17; M15 stays W |
| B, inside sbx VM | sbx | sbx plus OpenShell SSRF | D at L7 inside sbx's fence | D | D for the harness process | sbx repro VM | sbx | P: two log sources to correlate | M11 M12 M17 M7; M5 M19 re-probe |
| C, design only | – | – | – | D once built | – | – | – | P: proxy findings | M17, reopens M10 |
| D, Kubernetes | P: Kata optional | P | D | D | D | P | P | D with a collector | Shared-service list |

## 9. Recommendation

1. **Spike C now.** M17 is open and the contract is fully specified in the provider docs; check first
   whether sbx's managed credentials already satisfy the same probe (comparison work item 2).
2. **One bounded probe of B** on the Linux x86_64 guest, where runsc already passes and the kernel is
   recent: the kernel and seccomp qualification, then the one-provider L7 probe. Stop if Landlock is
   absent or the two-proxy DNS path cannot be observed upstream.
3. **Defer A** until OpenShell 0.1.0 is released, the `vm` driver drops its experimental label, and a
   Windows route with a per-sandbox kernel exists.
4. **Record D** in the comparison's §4 table as the policy-and-credential layer for a Kubernetes
   service, alongside OpenSandbox and Kata.

**Minimal spike for B**, run as `admin` in the guest (`not-yet-tested`; expected observations in brackets;
full gateway `docker run` in [container-gw]):

```sh
cat /sys/kernel/security/lsm; uname -r            # [contains landlock; >= 6.2]
docker run -d --group-add docker -p 127.0.0.1:8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock ghcr.io/nvidia/openshell/gateway:<pinned>
openshell gateway add http://127.0.0.1:8080 --local          # [openshell status: healthy]
openshell provider profile import -f openrouter.yaml --global   # custom profile, one endpoint
openshell provider create --name or --type openrouter --credential OPENROUTER_API_KEY
openshell sandbox create --name h --from <harness-image> --provider or --policy policy.yaml
openshell sandbox exec -n h --no-login-shell -- printenv OPENROUTER_API_KEY   # [placeholder]
openshell sandbox exec -n h -- curl -sS https://openrouter.ai/api/v1/models    # [200]
openshell sandbox exec -n h -- curl -sS -X POST https://openrouter.ai/api/v1/x # [403 policy_denied]
openshell logs h --source sandbox                 # [ALLOWED GET, DENIED POST, no secret]
appsec-sbx logs appsec-sbx                        # [sbx saw only openrouter.ai:443]
```

**Acceptance probes that must pass** before any option changes the pilot (comparison §6, in a disposable
environment with synthetic data): host-data canaries with mount inspection; privilege and policy as the
workload uid; direct egress with proxy variables removed over both IP families; upstream-observed DNS,
including an allowed hostname resolving privately; allowed API paths with SNI and Host mismatches; a
dummy secret absent from env, files, process views and proxy responses; clean reset with planted markers;
evidence export the workload cannot rewrite. For B, each network probe runs against both logs.

**Risks.** Alpha churn: the two documentation channels disagree today and CLI verbs changed between
v0.0.116 and main, so pin a release and re-read the release notes before each upgrade. NVIDIA
dependencies are image registries and default-on telemetry, both configurable. Windows means a shared
Docker Desktop VM until MXC ships, and MXC would be an AppContainer, so the comparison's platform checks
apply per host. The `enforcement: audit` default and TUI approvals can silently widen a sandbox; a
wrapper must set `enforce` and refuse entry when `policy list` shows an unexpected revision.

## Sources

Repository files are at commit `d3480d2a7efab3fd0217ab67828655617b9af777` unless noted.

[head]: https://github.com/NVIDIA/OpenShell/commit/d3480d2a7efab3fd0217ab67828655617b9af777
[v116]: https://github.com/NVIDIA/OpenShell/releases/tag/v0.0.116
[pre7]: https://github.com/NVIDIA/OpenShell/commit/f8002d19ad2f948abf48bd2f5ca4f8ebd388e3c8
[milestone]: https://github.com/NVIDIA/OpenShell/milestone/10
[readme]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/README.md
[rel-notes]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/about/release-notes.mdx
[how]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/about/how-it-works.mdx
[install]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/about/installation.mdx
[container-gw]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/about/container-gateway.mdx
[matrix]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/reference/support-matrix.mdx
[matrix-latest]: https://docs.nvidia.com/openshell/latest/reference/support-matrix.html
[drivers]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/reference/sandbox-compute-drivers.mdx
[runtimes]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/architecture/compute-runtimes.md
[sandbox-arch]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/architecture/sandbox.md
[sec-arch]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/architecture/security-policy.md
[docker-readme]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/crates/openshell-driver-docker/README.md
[vm-readme]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/crates/openshell-driver-vm/README.md
[rfc13]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/rfc/0013-native-windows-mxc/README.md
[bp]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/security/best-practices.mdx
[bp-latest]: https://docs.nvidia.com/openshell/latest/security/best-practices.html
[bp-dev]: https://docs.nvidia.com/openshell/dev/security/best-practices.html
[schema]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/reference/policy-schema.mdx
[policies]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/sandboxes/policies.mdx
[default-policy]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/reference/default-policy.mdx
[advisor]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/sandboxes/policy-advisor.mdx
[prover]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/reference/policy-prover.mdx
[providers]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/sandboxes/manage-providers.mdx
[inference]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/sandboxes/inference-routing.mdx
[inference-latest]: https://docs.nvidia.com/openshell/latest/sandboxes/inference-routing.html
[profiles-dir]: https://github.com/NVIDIA/OpenShell/tree/d3480d2a7efab3fd0217ab67828655617b9af777/providers
[sandboxes]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/sandboxes/manage-sandboxes.mdx
[workspaces]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/sandboxes/manage-workspaces.mdx
[man]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/deploy/man/openshell.1.md
[gw-config]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/reference/gateway-config.mdx
[logging]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/observability/logging.mdx
[ocsf]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/docs/observability/ocsf-json-export.mdx
[telemetry]: https://github.com/NVIDIA/OpenShell/blob/d3480d2a7efab3fd0217ab67828655617b9af777/telemetry/README.md
[nemoclaw]: https://github.com/NVIDIA/NemoClaw
