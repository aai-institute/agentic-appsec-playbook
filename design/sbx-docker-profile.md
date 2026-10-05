# Opt-in Docker for the workload (`create --docker`)

Design for [issue #15](https://github.com/aai-institute/agentic-appsec-playbook/issues/15),
started 2026-10-05. The standard workload has no Docker access (T08, T18). That excludes
every tool that runs its own containers: Strix, PentAGI, and Mantis's reproduce and patch
stages. This note settles the access model, records the guest probe behind it, and lists
the threat-model and wrapper changes. The wrapper side landed the same day; see the
implementation plan for status.

Conclusion: give `appsec` its own **rootless** Docker daemon when the VM is created with
`--docker`. It works in the sbx guest with four guest-specific adjustments (below). Container
traffic leaves through the same sbx policy as the workload's own traffic. sbx's own root daemon
was rejected because guest root reaches the host shares and relay behind sbx's 2026 escapes,
which the wrapper otherwise keeps out of the workload's reach.

## Decisions (2026-10-05)

- The profile registers as **M26**. The kit proposals in
  [sbx-kits-for-skills.md](sbx-kits-for-skills.md) move to M27 and M28.
- Images enter during provisioning (`--image`, digests recorded). Run-time pulls need a named
  registry preset. `--docker` implies no registry.
- Containers run with runc on every host, documented as such. A `--gvisor` option may follow
  where runsc works (see below).
- macOS first: the note, threat-model rows, wrapper, docs and a macOS record with the container
  probes and a Strix smoke run by 2026-10-14. Windows and Linux records and Mantis's reproduce
  stage by 2026-10-28.

## Access model

| Option | Verdict | Reason |
|---|---|---|
| Rootless Docker for `appsec` | **Chosen** | The daemon runs as `appsec`; container root maps to `appsec` and its subordinate IDs. Socket access grants nothing the workload does not already hold, so the workload/admin boundary (R5) stays. |
| `appsec` in the `docker` group | Rejected | sbx's own daemon, and what its default `agent` user gets. The socket is root-equivalent in the guest, and guest root reaches the host interfaces behind sbx's 2026 escapes (below). |
| Filtering socket proxy | Rejected | API filters are not a boundary: privileged containers and host mounts stay reachable. PentAGI's maintainers declined a docker-socket-proxy PR for the same reason ([vxcontrol/pentagi#356](https://github.com/vxcontrol/pentagi/pull/356)). |

The admin daemon that sbx starts stays as it is: owned by root, socket group `docker`, and
denied to `appsec` at entry.

### Rootless, or sbx's own daemon?

sbx's image runs `dockerd` as root, and its default `agent` user has sudo and the `docker`
group. Docker treats the microVM as the boundary. For the wrapper, that daemon would mean no
per-boot setup, per-container limits, container IPs reachable from the guest, runsc on x86_64
and tools behaving as documented. Under sbx, guest root cannot change the network policy, read
the API key (M17) or publish ports; all three live on the host. Rootless costs the
adjustments listed in the probe, UID-mapping friction with mounted source and a workaround
for Strix's networking.

A second probe on 2026-10-05 (same host and sbx release, throwaway VM) and the published
advisories settle what guest root adds:

| Question | Finding |
|---|---|
| Does root reach the host over vsock where `appsec` cannot? | No. `appsec` creates `AF_VSOCK` sockets and reaches the host transport as root does. A scan of host ports 1 to 65535 found one listener, 4424, which accepts `appsec`'s connections and sent nothing within 3 s. |
| Can root load kernel modules? | No. The guest kernel has no module support. |
| What is "guest root"? | Root inside a container in the microVM (own PID namespace, cgroup `/docker/<id>`), in the VM's initial user namespace with all 41 capabilities and no seccomp. `/proc/sys/kernel/core_pattern` is writable, the classic way out of such a container to VM root. Not attempted. |
| Which host interfaces stay closed to root inside the sandbox? | The device cgroup refuses the raw disks and `sailor-uds` (a misc device, mode 0600, root-only by design) even to root. After leaving the sandbox container, VM root would have both, and could mount the two virtiofs shares directly. Inferred. |
| Did the 0.42.0 escapes need guest root? | Not as published. CVE-2026-77179 (macOS virtio-fs server, symlink swap) and CVE-2026-79994 (host Unix-socket relay, path race) are both scored PR:N. Both act on a writable host share; Docker's workaround is no read-write host mounts. [Announcement](https://docs.docker.com/security/security-announcements/#docker-sandboxes-0420-security-update-cve-2026-77179-and-cve-2026-79994) |

In Docker's default setup, with a writable workspace, the agent's privilege would not have
mattered for those escapes. The wrapper removes their precondition instead: no workspace share,
checked at entry (T01, M20). Inside the sandbox only `/etc/resolv.conf` remains, a single
root-owned file bound from a virtiofs share. Guest root restores the precondition: VM root can
mount the shares as directories and open the relay device. With the `docker` group that is one
command away: `docker run --privileged -v /:/host`.

Decision: rootless. It keeps the no-share mitigation effective for a `--docker` VM, and
guest root keeps needing a kernel bug, as in the standard VM. If Strix or a later tool fails
under rootless in a way configuration cannot fix, add `--docker=rootful` as an explicit
downgrade, not a new default. That variant would record T08's residual as the whole guest,
state that the no-share mitigation no longer covers the workload against host-side share and
relay bugs, move the entry checks to the host, and require `reset` before any `admin` use.

Side finding: `kernel.unprivileged_bpf_disabled=0` in the guest, so unprivileged BPF is
open to `appsec` in every profile. Setting it to 1 or 2 at each entry is cheap hardening
against guest privilege escalation (T07), outside this issue.

## Guest probe (2026-10-05)

Throwaway VM on macOS arm64, sbx 0.46.0, the wrapper's kit image
(`docker/sandbox-templates:shell-docker`), Ubuntu 26.04.1, kernel 7.0.14, Docker 29.8.1.
Network policy as the wrapper sets it: the create-time denies, then `openrouter.ai:443` and
`registry.npmjs.org:443` as the only grants. Rootless daemon from Docker's
`docker-ce-rootless-extras`, rootlesskit with slirp4netns, run as a fresh `appsec` user
without groups.

### Guest facts

| Fact | Observed | Consequence |
|---|---|---|
| Init | PID 1 is `tini`; no systemd, no logind | No `systemd --user` unit. The wrapper starts the daemon. Rootless Docker selects the cgroup driver `none`, so per-container `--memory` and `--cpus` have no effect. |
| Security modules | None loaded; `kernel.unprivileged_userns_clone=1` | Ubuntu's AppArmor restriction on user namespaces does not apply. |
| User namespaces | `appsec` without Docker runs `unshare -Urn` and holds every capability in a new user and network namespace | The standard workload already reaches the kernel code that rootless containers use. |
| cgroups | cgroup v2, all controllers enabled at the root | A root-owned cgroup with `memory.max`, entered before the daemon starts, caps the daemon and every container together. A container allocating 900 MB under a 512 MB cap was OOM-killed inside it; `appsec` cannot move itself out. |
| Devices | Minimal tmpfs `/dev` without `/dev/net/tun`; the kernel has TUN built in | Root creates `/dev/net/tun` at every boot; slirp4netns needs it. |
| Root filesystem | overlay, 20 GB | containerd's overlayfs snapshotter fails on it (`invalid argument`). |
| `/var/lib/docker` | Separate ext4 volume, 9.8 GB, not captured by templates | The rootless data root is a bind mount from a subdirectory of this volume. |
| Packages | Docker's apt repository is configured; rootless extras, `uidmap` and slirp4netns are absent | An unpinned install upgraded the image's `docker-ce` and CLI from 29.8.1 to 29.8.2. Pin the extras to the installed engine version. |
| PATH | The entry PATH lacks `/usr/sbin`; `dockerd-rootless.sh` calls `sysctl` | The launcher sets its own PATH. |
| Idle stop | The VM stopped about a minute after the last session, with the daemon running in the background | `/run`, the device node, the bind mount and the daemon disappear. Start the daemon at every entry. Long container runs need an open session. |
| Footprint | About 190 MB resident for dockerd, containerd, rootlesskit and slirp4netns | Fits beside a harness in 8 GB. |

### Container network paths

Rootless containers on the default bridge, without proxy variables unless stated.

| Probe | Result | Policy log |
|---|---|---|
| HTTPS to the allowed `openrouter.ai:443` | 200; the container saw the provider's own certificate | allowed, transparent |
| Same, through `HTTPS_PROXY=http://gateway.docker.internal:3128` | 200 | allowed, `forward-bypass` (tunnelled: this VM declared no credential) |
| HTTPS to `example.com`, denied | name not resolved | `<dns proxy policy>` |
| Same, through the forward proxy | refused | `forward`, no applicable policies |
| HTTPS to `1.1.1.1` | connection cut | transparent, the create-time CIDR deny |
| HTTP to the allowed host on port 80 | connection cut | transparent, no applicable policy |
| DNS through the container resolver (`172.17.0.2`, the guest's) | allowed name answers; denied names get no answer | `<dns proxy policy>` |
| DNS directly to `1.1.1.1:53` | timeout | `<udp proxy policy>` |
| IPv6 to `2606:4700:4700::1111` | fails inside the guest; slirp4netns runs without IPv6 | none |
| `docker pull busybox` at run time | registry name not resolved | `<dns proxy policy>` |
| `--internal` network: peer container | reachable | — |
| `--internal` network: any outside address | no route, no external DNS | — |
| `-p 127.0.0.1:18000:8000` | listens on the guest loopback only; `sbx ports` stays empty | — |
| Bridge container to `10.0.2.2` (slirp's host address) | refused (`--disable-host-loopback`) | — |
| `--network host` | the guest's own network namespace: guest loopback listeners and allowed hosts | as for the workload |
| Admin socket from `appsec` | permission denied | — |
| `--privileged` | full capabilities inside the user namespace; container root is `appsec` | — |

Three properties follow. The sbx policy governs container egress without help from inside the
guest. The transparent path passes TLS through, so containers need no proxy CA for allowed
hosts. Key injection (M17) still needs the forward proxy, and containers can reach it.

The policy log names the sandbox and the path (transparent, forward, DNS, UDP), not the
process or container. A container's request and the harness's request look the same.

Not probed: x86_64 guests (Windows and Linux hosts), pasta instead of slirp4netns, containers
started by `admin` (the probe VM's admin daemon had no images and could no longer pull), key
injection into a container's request, and `reset` of a VM with workload images.

The Docker volume's size is an sbx setting (`sandbox.disk.dockerVolume`, default 10 GB).
`DOCKER_SANDBOXES_DOCKER_SIZE` in the environment of `sbx create` overrides it for one
sandbox: a probe create with `24g` got a 24 GB `/var/lib/docker` and the same 20 GB root
filesystem. The root filesystem has no size setting.

## Open questions from the issue

### 1. Does sbx's policy see container egress from a rootless daemon?

Yes, on macOS arm64 with slirp4netns (probe above). x86_64 guests remain to be probed.

### 2. gVisor on arm64

Decided: run containers with runc on every host and document it. Mantis's skills (pinned at
`f5656dd`, 2026-10-04) ask only for a container runtime; its `README_AGENTS.md` lists gVisor
as optional hardening. Only Mantis's reference harness hardcodes `--runtime=runsc`, and the
playbook installs the skills, not the harness. The threat model credits no gVisor boundary
today (T19): the VM is the boundary on every host.

gVisor would not help on any host. On arm64 with 16 KiB pages runsc stops at start: only 4 KiB
pages are supported, and [google/gvisor#8196](https://github.com/google/gvisor/issues/8196) is
open without plans. Under rootless Docker it also needs `--ignore-cgroups` and a test-only flag
([google/gvisor#12575](https://github.com/google/gvisor/issues/12575)).

### 3. Strix

Read at v1.7.0 (`55bc079`, released 2026-10-05):

- The CLI makes every model call, through LiteLLM or the OpenAI Agents SDK. The container is a
  toolbox driven through `docker exec`. The CLI therefore runs as the workload, and M17 key
  injection works as for a harness: `LLM_API_KEY=proxy-managed` through the forward proxy.
- LiteLLM builds TLS from `SSL_CERT_FILE` and ignores certifi when it is set. Point
  `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` at the guest bundle, which carries sbx's proxy CA.
- Image `ghcr.io/usestrix/strix-sandbox:1.3.0`, index digest `sha256:f6906c31…`, amd64 and
  arm64, 1.41 GB compressed on arm64. `STRIX_IMAGE` overrides it. The CLI pulls only a missing
  image; a never-pull option is an open request
  ([usestrix/strix#1031](https://github.com/usestrix/strix/issues/1031)).
- The container gets `NET_ADMIN` and `NET_RAW`, not `--privileged`. Caido's port is published
  to `127.0.0.1` on the default bridge. `STRIX_DOCKER_SANDBOX_NETWORK` replaces publishing
  with the container's IP, which the guest cannot reach under rootless networking. Keep the
  default bridge and `docker network connect` the container to the target's internal network
  (inferred; part of the smoke run).
- Local targets are rewritten from `localhost` to `host.docker.internal` (`host-gateway`).
  Under rootless networking that is not the guest's loopback. Run the target as a container
  on the internal network instead.
- Egress switches: `STRIX_TELEMETRY=0` (PostHog, Scarf), `STRIX_NO_UPDATE_CHECK=1` (PyPI or
  the GitHub API), `LITELLM_LOCAL_MODEL_COST_MAP=True` (raw.githubusercontent.com). Search
  APIs are contacted only when their keys are set.
- Hosts: the CLI needs the model endpoint only; the tool container needs the target only.
- Install: a release binary from GitHub without checksums, or PyPI with unpinned dependencies.
  Proposed: download and check the binary on the host, then `put` it into the guest.
- The default model in its examples, `openrouter/z-ai/glm-5.3`, works with an OpenRouter key.
- Left for the smoke run: Strix's UID remapping (`STRIX_HOST_UID`) against the rootless
  mapping when the repository is mounted, nmap's file capabilities, Caido's behaviour.

### 4. PentAGI

Read at v2.2.0 (tagged 2026-10-04, `b611fbe`):

- A minimal stack is `pentagi`, `pgvector` and one worker container per flow. The `pentagi`
  container gets the daemon socket and starts workers through it. Under rootless Docker that
  socket carries the workload's authority, not guest root.
- Disk does not fit. The Kali worker image is 5.4 GB compressed on arm64 and about 13 GB
  unpacked; the installer wants 25 GB free. Neither the default 10 GB volume nor an archive
  in the 20 GB root filesystem holds it.
- Model calls go through `PROXY_URL` (no exemptions) with `EXTERNAL_SSL_CA_PATH`. Workers join
  the default bridge unless `DOCKER_NETWORK` names a network, and publish ports on `0.0.0.0`
  unless `DOCKER_PUBLIC_IP` says otherwise. The update check posts to `update.pentagi.com`
  every three hours (`UPDATE_CHECK_INTERVAL=0` stops it). DuckDuckGo search is on by default.
- Workers have no memory limit of their own; the profile's shared cap bounds them together.

Proposed: leave PentAGI out of the first release of the profile. Document the sizing: a
larger Docker volume, a small worker image (`debian` or `kali-linux:test`), an internal
`DOCKER_NETWORK`, `DOCKER_PUBLIC_IP=127.0.0.1`, the update check off.

### 5. Flag name and registry allowance

Decided: `--docker`, with no implied registry. Images enter during provisioning:
`--image REF`, repeatable, pulled by the bootstrap before the policy lock, with each digest
recorded. Run-time pulls need a named registry, as npm and PyPI do today: add `dockerhub` and
`ghcr` presets to `--registry`. A named container registry is reachable by the harness too and
is a data channel (T12).

## Proposed design

### Command line and state

- `create --docker [--image REF]... [--docker-disk SIZE]`. Without `--docker` nothing changes.
- The profile records `docker: {model: rootless, images: [{ref, digest}], disk}`. `reset`
  recreates from the profile and keeps it. Reproducers keep the offline profile, without Docker.
- `create` and `reset` pass `DOCKER_SANDBOXES_DOCKER_SIZE` to `sbx create`. Proposed default
  for `--docker`: 32 GB. Whether sbx allocates the volume sparsely on the host is unchecked.
- Entry, `verify` and `describe` name the profile.

### Bootstrap, only with `--docker`

1. Install `uidmap`, `slirp4netns` and `docker-ce-rootless-extras` at the image's engine
   version. Stop if that version is unavailable.
2. Check that `/etc/subuid` and `/etc/subgid` give `appsec` a range of its own.
3. Install a root-owned `/usr/local/libexec/appsec-docker-start`. On each boot it creates
   `/dev/net/tun` and `/run/user/<uid>`, bind-mounts `/var/lib/docker/appsec-rootless`,
   creates a cgroup with a memory cap (proposed: 6 GB of the VM's 8 GB), and starts
   `dockerd-rootless.sh` inside it as `appsec`, with a fixed environment and PATH.
4. Write `/etc/appsec/docker.env` (`DOCKER_HOST`, `XDG_RUNTIME_DIR`); the login profile
   sources it.
5. Start the daemon, pull each `--image` plus `curlimages/curl` for probes, record digests
   in `versions.txt`, and save the images compressed to `/opt/appsec/workload-images.tar.zst`.
   `BOOTSTRAP_ALLOW` gains `ghcr.io` and `pkg-containers.githubusercontent.com` when a GHCR
   image is named.

The archive follows the admin images' existing pattern: `reset` works without network access
and restores exactly the provisioned images. Its limit is the 20 GB root filesystem shared
with the harness and the template. Pulling by digest during `reset`, before the policy lock,
is the alternative if larger images are needed.

### Create from the template, and reset

After `sbx create --template`, run `appsec-docker-start` and load the archive as `appsec`, as
the admin images are loaded today. The rootless data root lives on the sbx Docker volume,
which templates do not capture. Images built, containers and volumes created during a run
therefore do not survive `reset`. Daemon configuration under `~/.config/docker` sits in the
root filesystem and returns to the template's state.

### Entry guard

`guard()` runs `appsec-docker-start` as root. `isolation()` then checks, for a Docker VM:

- the admin socket is still denied to `appsec`, and `appsec` is not in the `docker` group;
- the daemon behind `DOCKER_HOST` reports `name=rootless` and runs as `appsec`, with user
  namespace root mapped to `appsec`;
- the data root is the bind mount from the Docker volume.

Without `--docker` the check stays as it is.

### Optional `--gvisor`

A possible extension, not in the 2026-10-14 scope. `--gvisor` would require `--docker` and
register runsc as a runtime of the workload daemon, in a root-owned daemon configuration. The
bootstrap would run a runsc container as `appsec` and refuse the VM if that fails, instead of
only recording the result as it does for the admin daemon today. On arm64 hosts with 16 KiB
pages it would always refuse.

Before deciding, probe on an x86_64 host which runsc flags rootless Docker needs, and what
the test-only flag in google/gvisor#12575 disables. If the working configuration depends on a
test-only flag, drop the option. A working runsc layer adds defence in depth and gets no
credit in the threat model, as in T19.

### Operating guidance (docs)

- Run targets on `docker network create --internal`. Connect a tool container to it; only the
  tool container joins the default bridge, and only if the tool requires it.
- Run model clients as the workload where the tool allows it. A container that must call the
  model sets `HTTPS_PROXY=http://gateway.docker.internal:3128` and uses the sentinel key.
- Use named local images with `--pull=never`. Publish ports to `127.0.0.1` only.
- Hold a session open during long runs: an idle stop ends the daemon and every container.
- All containers share one memory cap. A runaway container ends others, not the harness.

### Not in this design

Per-container limits, gVisor, per-container log attribution, transferring images from the host,
enforcing which network a container joins, PentAGI validation.

## Threat-model changes

No new `T` row. Images enter as provisioning inputs (T28) or through a named registry (T12,
T24). User namespaces are already open to the standard workload: `appsec` runs
`unshare -Urn` with every capability in the new namespace (probe above), and Codex's bubblewrap
relies on that. The profile adds the setuid `newuidmap`/`newgidmap` helpers and the TUN
device, not a new class of exposure.

Proposed catalogue rows:

| ID | What could go wrong | Current response | Remaining risk or work |
|---|---|---|---|
| T08 | Docker socket access gives the workload administrator authority (A7). | The admin daemon's socket is denied to the workload and checked on entry. A VM created with `--docker` gives the workload its own rootless daemon: containers run in a user namespace mapped to `appsec`, and the entry check confirms the mapping. M20/M26. | Running an agent from `admin` bypasses the workload user boundary. With `--docker`, a user-namespace kernel bug is a path to guest root, as it already is through `unshare`. Containers share one memory cap and have no CPU limit. |
| T18 | Container traffic bypasses the primary workload's network rules (A5/A9). | Without `--docker` the workload has no container access. With it, container traffic leaves through the same sbx policy as the workload's, DNS and direct-address denies included. Reproducer VMs receive a deny-all policy. M9/M21/M26. | The policy log does not attribute requests to containers. Containers on the default bridge reach every allowed host and the forward proxy; only an `--internal` network keeps a target or tool off them, and the wrapper does not enforce it. Admin-started containers need their own probes. |

Residual additions: T21 (a tool container on the default bridge can reach allowed third-party
hosts), T25 (any container can spend the key through the forward proxy), T26 (containers share one
memory cap, have no CPU limit and end only with the VM), T28 (workload images are provisioning inputs, recorded by
digest).

Proposed control, status *open* until implemented and *partial* until accepted on all three
host platforms:

| ID | Control | Threats | Limit |
|---|---|---|---|
| M26 | `create --docker` gives the workload a rootless Docker daemon. Daemon and containers run as `appsec` in a user namespace. Images enter during provisioning with recorded digests. The data root lives on the sbx Docker volume that `reset` replaces. Entry checks the mapping and the admin-socket denial. | T08 T18 T23 | One memory cap for all containers, no CPU or per-container limits; the log does not attribute requests to containers; container networks are operator choices; no gVisor layer. |

Acceptance additions: R3 repeats the network probes from a rootless container on the default
bridge and on an `--internal` network. R5 adds the admin-socket denial, the daemon's owner and
the container-root mapping. R6 runs targets on an `--internal` network with callbacks reaching
only local stand-ins. R7 records workload image digests, and its reset canary covers images,
containers, volumes and daemon configuration.

The acceptance page's sentence "the standard `appsec-sbx` workload has no Docker access"
becomes conditional on the flag.

## Implementation plan

1. Threat model, done 2026-10-05: M26 registered as open (26 measures: 9 delivered,
   11 partial, 4 open, 2 deferred); T08 and T18 point to it under remaining work; the R3, R5,
   R6 and R7 evidence covers workload container daemons. The public tables describe current
   behaviour, so the full T08 and T18 rows above, and the residual additions, replace the
   current text when the wrapper ships. Done with the wrapper: M26 partial (9 delivered,
   12 partial, 3 open, 2 deferred).
2. Wrapper: profile key and CLI options, `DOCKER_SANDBOXES_DOCKER_SIZE` in `create_command`,
   the bootstrap block, image loading after a template create, the entry checks, `verify`
   output, tests, the regenerated command reference, version 0.5.0. Done 2026-10-05, with two
   bootstrap fixes found live (`iproute2`; no recommends) and one from the Strix run (digest-
   pinned images keep their tag).
3. Docs: providers and commands pages; the acceptance page's note; the hardening checklist row
   "Docker or other container tooling"; the validation template's "no automatic application
   setup or container access for the workload"; the lifetime page's container section; the
   review-skills page's Mantis paragraph; the shortlist's Strix, PentAGI and Mantis lines.
   Done 2026-10-05, plus a new guide page, "Containers for the workload".
4. Acceptance records, macOS by 2026-10-14, Windows and Linux by 2026-10-28. macOS done
   2026-10-05 except Mantis, IPv6 and the virtiofs listing
   ([record](../records/sbx-acceptance.md#workload-docker-on-0460-2026-10-05)):
   - `create --docker`, `verify`, entry after an idle stop (the daemon restarts);
   - the container network probes above, with IPv6;
   - a rootless build of the demo target with `--registry pypi` and pre-pulled base images;
   - a reset canary: a built image, a container, a volume and a daemon configuration change
     gone, the provisioned images present;
   - a Strix smoke run against the seeded demo app on an internal network;
   - Mantis's reproduce stage on the same target with runc (by 2026-10-28);
   - as root in a throwaway VM, mount each virtiofs share read-only by tag and list what it
     exports, without writing, to size what guest root would reach.
5. After the x86_64 records: the `--gvisor` probe and the decision on that option.
