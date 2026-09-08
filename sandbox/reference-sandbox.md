# Reference Sandbox: the No-Regret Measures on Colima/Lima (macOS)

**Status:** draft v0.2, 2026-09-08. v0.1 (2026-09-02) validated L1/L2 end to
end on the author's machine (incl. the tinyproxy privilege-drop and two-hop DNS
fixes). v0.2 closes two weaknesses a review found in v0.1: **the agent ran as
the admin user and so inherited passwordless sudo** (one command could flush
the egress rules), and **container traffic bypassed the egress filter** (the
ruleset only had an `output` chain; forwarded packets from a default-runtime
container never met it). Fixes: a separate unprivileged `agent` user, and a
`forward` chain with policy drop. **v0.2 validated 2026-09-08** on a fresh
profile (`make-appsec-vm.sh create`, then an idempotent re-provision with
`REBOOTSTRAP=1`): Colima 0.10.3 / Lima 2.2.0, Apple silicon, guest Ubuntu
24.04.4, kernel 6.8.0-117, Node 24.20.0, OpenCode 1.18.29, gVisor from the
release apt repo. The bootstrap's verification step passed all five checks —
direct egress dropped, unlisted host filtered by the proxy, listed host
reachable, a default-runtime container's connection to a bare IP dropped *by
the forward chain* (kernel log shows `egress-drop-fwd IN=docker0 OUT=eth0`),
and the agent user refused by the Docker socket. Steps marked `checked` were
verified in one of these runs; `to-verify` marks what remains untested. Participants on other stacks (UTM, Parallels,
Hyper-V, a cloud VM) implement the same layers with their own tools — the
[checklist](#self-certification-checklist) at the end is tool-neutral.

## What this protects against, and what it doesn't

The agent gets a shell, the repo, and network egress. The sandbox exists so that
a misbehaving or injected agent **cannot** reach your host filesystem, your
credentials and SSH keys, other machines on your LAN, or arbitrary internet
hosts — and so that a runaway loop cannot spend unbounded money or leave state
behind. It does **not** protect against the model provider seeing your code
(that is the tier A/B decision and the anonymization rules), and a domain
allowlist does not stop exfiltration through an *allowed* host (domain
fronting, benign-SaaS chaining — see `research/sandbox-prior-art.md` §2).

## Framing (vocabulary shared with the CISO-level guidance)

The guide follows the control model of OpenAI's *Agent security in the
enterprise* (Aug 2026, "Agent security series"; see
`research/sandbox-prior-art.md` §5). Three of its terms do real
work here and are the ones to use when a security lead asks what the sandbox
buys:

- **Reachable surface** — the data, systems, actions and destinations the agent
  can touch. L1 (no host mounts, no LAN) and L2 (allowlist egress) shrink it.
- **Effective blast radius** — the harm still possible *after* enforced
  controls. That is what the self-certification checklist actually certifies.
- **Maximum completed effect** — the worst outcome the agent can finish before
  another independent decision is required. For a discovery-only run it should
  be "tokens spent and a findings file written", nothing else; every layer
  below exists to make that true.

Two of its rules restate ours: "Instructions may guide behavior; independent
controls provide containment" (why OpenCode's permission prompts are not the
sandbox), and "Place controls as close as possible to the effect they limit"
(why egress is enforced by nftables in the guest rather than by a harness
setting). Its control-placement rows map onto the layers: *runtime and network
boundary* = L1–L3, *agent and tool boundary* = L4 / harness permissions,
*detection and response* = the proxy and kernel logs plus the kill switch.

## Layers

| Layer | Mechanism | Covers no-regret measure |
|---|---|---|
| L1 | Dedicated Lima/Colima VM (vz), **no host mounts**, own profile; inside it a separate unprivileged **`agent` user** (no sudo, no Docker socket) | isolated VM-based runner; no production credentials in reach; the agent cannot switch the containment off |
| L2 | In-guest nftables default-deny egress — `output` chain for the VM's own traffic **and `forward` chain for containers'** — + tinyproxy domain allowlist | egress default-deny + narrow allowlist |
| L3 | Docker inside the VM; gVisor (`runsc`) + `--network none` for reproducers; internal-only bridge for a dynamic target | contains generated code and offensive-for-defense targets |
| L4 (optional) | Anthropic `sandbox-runtime` (`srt`) around the agent process | per-process filesystem/network limits inside the VM |
| — | Spend cap on the key + provisioning script + disk clone | budget before the run; snapshot/rollback; kill switch |

Why a VM and not "just Docker": both 2026 cyber-eval escapes broke out of
containers (`research/agent-sandboxing-incidents-2026.md`); OpenAI's own
remediation mandated micro-VMs plus two independent network-isolation layers.
L1 + L2 is the SME-sized version of that.

## L1 — the VM

Do **not** reuse a daily-driver Colima profile: the default profile on this
machine mounts `~` *writable* into the guest (`checked`, `~/.colima/_lima/colima/lima.yaml`),
which is precisely the hole we are closing.

```bash
# dedicated profile, no host mounts, does not hijack the host's docker context
colima start appsec --mount none --vm-type vz --cpus 4 --memory 8 --disk 40 --activate=false
colima ssh -p appsec -- sh -c 'mount | grep -E "virtiofs|sshfs|9p" ; ls /Users'   # both must print nothing
```

`--mount none` is Colima's documented way to disable the default `~` and
`/tmp/colima` mounts (`checked`, `colima start --help`). Plain Lima equivalent:
`limactl start --name appsec --mount-none template:docker`. Leave
`--network-address` off (default): it adds a second, LAN-reachable interface
(`col0`, seen on the default profile) that L2 would otherwise have to police.

The guest reaches the host through the user-mode gateway (`192.168.5.2`) and
the LAN via NAT by default (`checked`, `ip route` in guest). L2 closes both.

## Who runs what: admin user vs. agent user

The Lima user you ssh in as has passwordless sudo — Lima needs that for
provisioning, and you need it to operate the sandbox. In v0.1 the agent ran
as that same user, so every containment measure below was one
`sudo nft flush ruleset` away from being switched off by the process it was
meant to contain. v0.2 splits the roles:

| | **admin** (the Lima user) | **agent** (created by the bootstrap) |
|---|---|---|
| sudo | yes, passwordless | **no** — not in `sudo`/`admin`, no sudoers entry (the bootstrap fails if it finds one) |
| Docker socket | yes (`docker` group) | **no** — socket access is root-equivalent (a container can mount `/`), so the agent gets none |
| runs | provisioning, `tail -f` on the proxy log, reproducer containers, the kill switch | OpenCode / Claude Code, the pilot repo clone, the findings export |
| home | `0750`, unreadable by the agent | `0750`, holds `~/target`, nvm + Node + OpenCode |

Work as the agent with `sudo -iu agent` from the admin shell, or
`sandbox/make-appsec-vm.sh agent appsec` from the host. The agent's shell
still carries the proxy environment, but that is a convenience, not the
control: even if the agent unsets `HTTPS_PROXY`, nftables drops its direct
egress, and it has no privilege to change that.

Consequence for L3: **the agent cannot start containers.** Reproducers
(`runsc`, no network) and dynamic targets are launched by the admin, e.g.
`docker run --rm --runtime=runsc -v /home/agent/target:/work:ro <image> …`.
That matches the validation loop, where a human decides what gets reproduced.
A narrow sudoers rule allowing the agent to run one fixed wrapper script is
the way to let it self-launch reproducers; not provided here (`to-verify`,
and easy to get wrong).

## Provisioning (run *before* L2 goes up — afterwards apt only works via the proxy)

**Canonical form: two scripts.**

- [`make-appsec-vm.sh`](make-appsec-vm.sh) runs on the **host**: creates the
  mount-less Colima VM, verifies no host mount exists, pushes and runs the
  guest script, writes the `runsc` runtime into the profile's `colima.yaml` so
  it survives restarts, clones the clean disks as the rollback baseline, and
  offers `snapshot` / `rollback` / `shell` / `stop` / `destroy` actions.
- [`bootstrap-appsec-vm.sh`](bootstrap-appsec-vm.sh) runs **inside** the guest:
  packages, gVisor + runsc, nvm + Node LTS + OpenCode, tinyproxy allowlist,
  proxy env, nftables lockdown, verification — in that order, refusing to run
  on a VM with host mounts. Knobs are env vars (`ALLOWLIST`, `SKIP_EGRESS=1`
  to re-provision, `PREPULL_IMAGES`, …) and pass through the wrapper.

```bash
sandbox/make-appsec-vm.sh create appsec        # ~10 min, mostly apt + Node download
sandbox/make-appsec-vm.sh agent appsec         # shell as the agent user — run OpenCode here
sandbox/make-appsec-vm.sh shell appsec         # admin shell — proxy log, reproducers
sandbox/make-appsec-vm.sh stop appsec          # kill switch
sandbox/make-appsec-vm.sh rollback appsec      # back to the clean clone
```

A throwaway VM is only throwaway if rebuilding it is one command; `create` is
that command. The prose below explains what the scripts do and why.

```bash
colima ssh -p appsec
sudo apt-get update && sudo apt-get install -y git tinyproxy nftables curl jq   # nft 1.0.9 + tinyproxy 1.11.1 in 24.04 apt (checked)
# gVisor (arm64 + x86_64 supported; needs Linux >= 5.6 — 24.04 ships 6.8)
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list >/dev/null
sudo apt-get update && sudo apt-get install -y runsc
# Node (for `npx skills add`, OpenCode); OpenCode itself per its install docs
```

Docker runtime registration: Colima regenerates `/etc/docker/daemon.json` from
the `docker:` key in `~/.colima/appsec/colima.yaml` at every start, so the
runtime the guest script registers must also live there (`make-appsec-vm.sh`
patches it; by hand: `colima start appsec --edit`):

```yaml
docker:
  runtimes:
    runsc:
      path: /usr/bin/runsc
      runtimeArgs: ["--network=none"]      # reproducers never get a network, even if a stage forgets --network none
```

Check: `docker run --rm --runtime=runsc hello-world` (`to-verify` inside vz;
runsc's default `systrap` platform does not need nested KVM).

## L2 — egress: default-deny, allowlist by hostname

Design: **only** the proxy user may open outbound connections; everything else
in the guest — the agent, npm, git, curl, stray reproducers — either goes
through `127.0.0.1:8888` and is matched against an allowlist, or is dropped.
That has to hold for two kinds of traffic: packets the VM itself originates
(`output` hook) **and packets containers originate, which the kernel
forwards** (`forward` hook). v0.1 only had the first; a container on the
default bridge with the default `runc` runtime would have NATed straight out.
The proxy log becomes the evidence for "what the tool demonstrably needs", which
is exactly the allowlist-widening rule in the assignment.

`/etc/tinyproxy/tinyproxy.conf` (relevant lines; `FilterDefaultDeny` semantics
`checked` against the tinyproxy.conf man page):

```
User tinyproxy               # REQUIRED: the nft rules key on this uid. The packaged
Group tinyproxy              # config sets it; a from-scratch config that omits it runs
                             # tinyproxy as root and every rule below misses (seen 2026-09-02)
Port 8888
Listen 127.0.0.1
Allow 127.0.0.1
Allow 172.17.0.0/16          # only if containers (dynamic target) need egress — usually leave out
FilterType fnmatch
FilterDefaultDeny Yes
Filter "/etc/tinyproxy/allowlist"
ConnectPort 443
LogLevel Connect
LogFile "/var/log/tinyproxy/tinyproxy.log"
PidFile "/run/tinyproxy/tinyproxy.pid"
```

After `systemctl restart tinyproxy`, confirm the privilege drop:
`ps -o user=,comm= -C tinyproxy` must print `tinyproxy`, not `root`.

`/etc/tinyproxy/allowlist` — for HTTPS the filter sees the CONNECT **hostname**
only, never the URL (`checked`). Start with the model endpoint you actually use
plus code hosting, nothing else:

```
api.anthropic.com
openrouter.ai
api.z.ai
api.deepseek.com
github.com
*.githubusercontent.com
registry.npmjs.org
```

**DNS in the Lima guest is two hops** (`checked`): `/etc/resolv.conf` points
at a `192.168.5.x` address (`.3` on the 2026-09-02 instance, the guest's own
`.4` on the 2026-09-08 one — read it from the file), which is a **local**
`dnsmasq` (user `dnsmasq`) that forwards upstream to the host gateway. Queries from tinyproxy reach dnsmasq over `lo`;
dnsmasq's *own* upstream query is a separate outbound packet under a different
uid. A ruleset that only lets the tinyproxy uid do port 53 therefore breaks
name resolution with `Temporary failure in name resolution` in the proxy log.
Allow the resolver daemon's uid too.

nftables (`/etc/nftables.conf`, then `systemctl enable --now nftables`;
`output` chain `checked` 2026-09-02, `forward` chain `checked` 2026-09-08 —
both via the bootstrap's verification step):

```
table inet egress {
  chain output {
    type filter hook output priority 0; policy drop;
    oifname "lo" udp dport 53 meta skuid != { "tinyproxy", "dnsmasq" } drop   # optional tightening: agent can't use the stub resolver as a tunnel
    oifname { "lo", "docker0" } accept                 # loopback; agent -> local target container
    oifname "br-*" accept                              # agent -> containers on user-defined (incl. --internal) bridges
    ct state established,related accept
    meta skuid "tinyproxy" tcp dport 443 accept        # only the proxy may leave
    meta skuid { "tinyproxy", "dnsmasq" } udp dport 53 accept   # proxy -> stub, and the stub's upstream hop
    meta skuid { "tinyproxy", "dnsmasq" } tcp dport 53 accept
    meta skuid "systemd-timesync" udp dport 123 accept # keep the clock sane for TLS
    ip daddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16 } log prefix "egress-drop-lan " drop   # host gateway + LAN; logged, or a blocked resolver hop is invisible
    log prefix "egress-drop " drop
  }
  chain forward {
    type filter hook forward priority 0; policy drop;  # containers' traffic never meets the output chain
    ct state established,related accept
    iifname { "docker0", "br-*" } oifname { "docker0", "br-*" } accept   # container <-> container; Docker's own isolation keeps bridges apart
    log prefix "egress-drop-fwd " drop                 # container -> internet / host gateway / LAN
  }
}
```

Why the `forward` chain matters even though `runsc` containers get
`--network=none`: that flag is a property of the *runtime*, and nothing stops
the agent — or a tool it installs — from starting a container with the default
runtime. The chain makes the network outcome independent of which runtime was
used. Container-to-container traffic on the same bridge is bridged, but Docker
loads `br_netfilter`, so it does traverse this hook — hence the explicit
accept.

Debugging order when something can't get out: `ps -o user=,comm= -C tinyproxy`
(uid drop happened?), `sudo journalctl -k | grep egress-drop` (which dst/port is
being dropped — expect NTP and ICMPv6 noise from systemd-timesyncd;
`egress-drop-fwd` lines are containers trying to leave), then the proxy log. Test signal from `curl -x http://127.0.0.1:8888 https://<host>`: a
**403** means the allowlist refused it (good for an unlisted host); a **500**
means the proxy accepted it but could not connect — DNS or the 443 rule. Note that `dockerd` runs as root and is
therefore blocked from pulling images — intended; pre-pull during provisioning
(`PREPULL_IMAGES`) or configure the daemon's own proxy settings if pulls must
happen at run time. Containers themselves are blocked by the `forward` chain;
if a *containerised* agent (Strix, PentAGI) must reach its model endpoint,
`ALLOW_CONTAINER_PROXY=1` makes tinyproxy accept clients from `172.17.0.0/16`
so the container can use `http://172.17.0.1:8888` as its proxy — the
allowlist still applies. `to-verify`. Note that Lima forwards guest ports
listening on localhost to the host's localhost by default (seen in the
`hostagent` log for `127.0.0.1:8888`); that is host→guest reach, not a
containment gap for the agent, but with a proxy bound to all interfaces it
means your Mac can use the sandbox as a proxy — disable with `portForwards`
in the profile if that bothers you.

Shell environment for both users (OpenCode, Claude Code, git and npm all honour
these; the bootstrap writes the block into the admin's and the agent's
`~/.bashrc` **and** into root-owned `/etc/environment`, so non-interactive
logins such as `sudo -iu agent opencode run …` get it too — `checked`):

```bash
export HTTPS_PROXY=http://127.0.0.1:8888 HTTP_PROXY=http://127.0.0.1:8888
export NO_PROXY=localhost,127.0.0.1,172.17.0.0/16
```

Verification (the bootstrap runs all of these at the end; all `checked`,
2026-09-02 / 2026-09-08): `curl -sS https://example.com` must **fail**;
`curl -sS -x http://127.0.0.1:8888 https://example.com` must return
tinyproxy's filtered/403 page;
`curl -sS -x http://127.0.0.1:8888 https://api.anthropic.com/v1/models` must
reach the API (a 401 or 404 is success here);
`docker run --rm curlimages/curl -sS -m 10 https://1.1.1.1` — a
**default-runtime** container, by IP so a DNS failure can't mask a missing
chain — must fail *and* leave an `egress-drop-fwd` line in `journalctl -k`
(the bootstrap checks for the line, not just the failure); `sudo -u agent
docker ps` must fail.
Watch `/var/log/tinyproxy/tinyproxy.log` during the first agent run and widen
the allowlist one hostname at a time.

Containers: reproducers run with `--runtime=runsc` (network already none via
`runtimeArgs`), **started by the admin** — the agent user has no Docker
access. A dynamic target (Juice Shop for the coverage axis) runs on an
internal bridge — `docker network create --internal appsec-target` — so the
agent can hit it from the guest (the `output` chain accepts `br-*`), and it can
reach nothing (`--internal` plus the `forward` chain).

## Credentials and budget

- No host mounts means no `~/.ssh`, no keychain, no `~/.claude` or
  `~/.config/opencode` from your Mac leak in. Keep it that way: clone the pilot
  repo over HTTPS with a read-only, short-lived token or from a public mirror.
- Put the model key into the **agent's** session, not onto disk:
  `export ANTHROPIC_API_KEY=$(cat)` then paste, or `read -s`, inside
  `sudo -iu agent`. Use a key that
  carries the cap: an Anthropic workspace with a spend limit, an OpenRouter key
  with a credit cap, OpenCode Zen prepaid credits. Never a personal
  unlimited key.
- Set the abort threshold *before* the run (wall-clock or visible tokens) and
  keep a second terminal open on the host for the kill switch.

## Snapshot / rollback

`limactl snapshot` is **unimplemented on the vz driver** (`checked`:
`LIMA_HOME=~/.colima/_lima limactl snapshot list colima` → `unimplemented`).
Colima has no snapshot command at all (`checked`). Two working substitutes:

1. **Throwaway by construction (preferred):** `make-appsec-vm.sh destroy appsec`
   then `create`. Rebuild time is dominated by apt and the Node download.
2. **Disk clone while stopped** (`make-appsec-vm.sh snapshot` / `rollback`):
   a profile has **two** disks (`checked`, Colima 0.10.x): the raw sparse root
   disk `~/.colima/_lima/colima-<profile>/disk` (a single file on instances
   created by 0.10.x; older instances have `basedisk` + `diffdisk` instead —
   the script detects both) and the data disk `~/.colima/_lima/_disks/colima-<profile>/datadisk`
   (`--disk` GiB; Docker images live here). Both must be cloned together. APFS
   clones (`cp -c`) are instant and cost no space until blocks diverge.
   `to-verify` that Colima accepts the restored pair without complaint.

If real snapshots matter more than speed, `--vm-type qemu` has them
(`limactl snapshot create/apply`), at a performance cost.

## Kill switch

Two separate operations, per the enterprise guide: "Stopping execution and
revoking authority are separate operations. Terminating a task might not
invalidate a token already issued." Stopping the VM ends the agent's work;
it does not end the model key's validity. The kill switch therefore has two
halves — halt the runtime *and* revoke or rotate the key that was inside it
(OpenRouter: delete the per-participant key; Anthropic: rotate in the console).

`colima stop -p appsec` from the host; `colima stop -f -p appsec` if the guest
hangs (`checked`: `-f, --force  stop without graceful shutdown`);
`colima delete -f -d -p appsec` tears down VM *and* data disk (`-d` — without it
the 40 GB data disk lingers under `_lima/_disks/`). `make-appsec-vm.sh stop` /
`destroy` wrap these. Test it once
before the first agent run — that is the checklist item, not the knowledge that
the command exists.

## L4 (optional) — per-process sandbox inside the VM

`anthropic-experimental/sandbox-runtime` (Apache-2.0) wraps a command with
bubblewrap plus a domain-allowlisting proxy on Linux
(`srt --settings cfg.json opencode`); bubblewrap 0.9 is in 24.04 apt
(`checked`). It adds filesystem `denyRead`/`allowWrite` rules the VM layer does
not have. Its README states the proxy does not inspect TLS and allowlists are
bypassable via domain fronting — same caveat as L2, not a substitute for it.
Nested Docker needs its "weaker nested sandbox" mode, so skip L4 for the
reproduce stage. `to-verify`.

## Self-certification checklist

Tool-neutral; mirrors the gate in the working group's session 1 assignment.

- [ ] VM-based runner, dedicated instance, **zero host mounts** (prove it: mount table empty)
- [ ] The agent runs as an **unprivileged user**: no sudo, no Docker socket (prove it: `sudo -n true` and `docker ps` both fail in the agent's shell)
- [ ] Guest cannot reach host gateway or LAN; only the proxy user can open outbound connections — **including from containers** (prove it: a default-runtime container's `curl https://1.1.1.1` fails and `journalctl -k` shows `egress-drop-fwd`)
- [ ] Allowlist contains the model endpoint + code host and nothing you cannot name a reason for; proxy log kept
- [ ] No long-lived credentials inside; model key carries a hard spend cap or a written abort threshold
- [ ] Generated code and reproducers run in `runsc` with no network; dynamic targets on an internal bridge
- [ ] Rebuild-from-script or disk clone exists and has been restored once
- [ ] Kill switch executed once, VM confirmed down, then brought back — *and* the model key revoked/rotated as the second half of the switch
- [ ] Evidence retained per run: proxy log (tool action + destination), kernel egress-drop log, harness session log — the "what was attempted vs. what completed" record the enterprise guide asks for

## Open items

- Mantis × Juice Shop test drive on a v0.2 VM (agent runs OpenCode + Mantis skills against the example repo; admin launches a `runsc` reproducer) — the end-to-end exercise that flips the remaining `to-verify` marks.
- Confirm `runsc` works under vz without KVM (systrap) for a Node-based reproducer (`hello-world` under `runsc` is `checked`; a real reproducer is not).
- Lima's default port forwarding of guest localhost ports to the host: decide whether the reference profile should set `portForwards` to ignore them.
- `ALLOW_CONTAINER_PROXY=1` path for containerised agents (Strix / PentAGI): does tinyproxy without a `Listen` line bind `172.17.0.1`, and does the agent container honour the proxy env?
- Optional sudoers wrapper so the agent can self-launch `runsc` reproducers without general Docker access.
- Decide whether Docker-Hub pulls belong on the allowlist (`registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com`) or whether images are pre-pulled during provisioning — pre-pulling keeps the runtime allowlist smaller.
- Windows/Linux equivalents for participants (Hyper-V / WSL2-with-caveats, libvirt) — only the L1 command changes.
