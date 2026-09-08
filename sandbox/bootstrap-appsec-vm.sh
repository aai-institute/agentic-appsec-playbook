#!/usr/bin/env bash
# Bootstrap the WG reference sandbox inside a fresh Colima/Lima guest (Ubuntu 24.04).
# Companion to reference-sandbox.md — read that first; this script is the L2/L3
# provisioning it describes, condensed. Run INSIDE the guest as the normal Lima
# user (passwordless sudo — the *admin* user), on a VM created with --mount none:
#
#   colima start appsec --mount none --vm-type vz --cpus 4 --memory 8 --disk 40 --activate=false
#   colima ssh -p appsec -- sh -c 'cat > bootstrap-appsec-vm.sh' < sandbox/bootstrap-appsec-vm.sh
#   colima ssh -p appsec -- bash bootstrap-appsec-vm.sh
#
# (Two steps on purpose: `bash -s < script` would let any stdin-reading command eat the script.)
#
# Two users, by design (v0.2):
#   admin  — the Lima user you ssh in as: passwordless sudo, docker group. Provisions, operates, kills.
#   agent  — created here: NO sudo, NO docker group, own home. OpenCode/Claude Code and the pilot
#            repo live here; `sudo -iu agent` to work as it. The agent cannot flush nftables, edit
#            the allowlist, or reach the Docker socket (socket access is root-equivalent).
#
# Order matters: everything that needs the open internet (apt, gVisor repo, nvm,
# Node, OpenCode, image pulls) runs BEFORE the egress lockdown. Afterwards only
# the proxy user can leave the VM, and only to ALLOWLIST hosts. Re-running is
# safe: package installs are idempotent, config files are overwritten, the
# bashrc blocks are guarded.
#
# Status: v0.1 (single user, output-chain egress) validated 2026-09-02; v0.2 (agent user,
# forward-chain drop for containers, /etc/environment proxy env, container-egress + agent-docker
# verification) validated 2026-09-08 — fresh create plus REBOOTSTRAP=1 re-provision — on Colima
# 0.10.3 / Lima 2.2.0, Apple silicon, Ubuntu 24.04.4, kernel 6.8.0-117, Node 24.20.0, OpenCode 1.18.29.
set -euo pipefail

### ---- knobs -----------------------------------------------------------------
AGENT_USER="${AGENT_USER:-agent}"                # unprivileged user the agent runs as
PROXY_PORT="${PROXY_PORT:-8888}"
NVM_VERSION="${NVM_VERSION:-v0.40.7}"            # nvm-sh/nvm release tag (2026-08-18)
NODE_VERSION="${NODE_VERSION:---lts}"            # nvm target; LTS was v24 on 2026-09-02
OPENCODE_PKG="${OPENCODE_PKG:-opencode-ai@latest}"   # docs: npm install -g opencode-ai
SKIP_EGRESS="${SKIP_EGRESS:-0}"                  # 1 = provision only, leave the network open
TIGHTEN_LO_DNS="${TIGHTEN_LO_DNS:-0}"            # 1 = only proxy/dnsmasq may talk to the stub resolver (untested)
ALLOW_CONTAINER_PROXY="${ALLOW_CONTAINER_PROXY:-0}"  # 1 = containers on docker0 may use the proxy (for containerised agents like Strix); to-verify
PREPULL_IMAGES="${PREPULL_IMAGES:-hello-world curlimages/curl}"  # space-separated; pulled before lockdown (dockerd is root -> blocked later). curl image is used by the verification step
# Hostnames the proxy may CONNECT to after lockdown. Model endpoint(s) + code hosting. Nothing else.
ALLOWLIST="${ALLOWLIST:-$(cat <<'LIST'
api.anthropic.com
openrouter.ai
api.z.ai
api.deepseek.com
github.com
*.githubusercontent.com
registry.npmjs.org
LIST
)}"
### ---------------------------------------------------------------------------

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
# ssh forwards the host's TERM (e.g. xterm-ghostty); the guest has no terminfo for it and nvm/npm call tput
tput -T"${TERM:-dumb}" colors >/dev/null 2>&1 || export TERM=xterm-256color
die()  { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
as_agent() { sudo -u "$AGENT_USER" -H env HOME="/home/$AGENT_USER" TERM="$TERM" "$@"; }

### 0. sanity
[ "$(id -u)" -ne 0 ] || die "run as the normal Lima user, not root"
sudo -n true 2>/dev/null || die "passwordless sudo required (Lima default) for the admin user"
grep -q 'ID=ubuntu' /etc/os-release || die "expected an Ubuntu guest (Colima >= 0.6 ships Ubuntu)"
if mount | grep -qE 'virtiofs|sshfs|9p'; then die "host mounts present — recreate the VM with --mount none"; fi
curl -fsS -o /dev/null https://github.com || die "no internet from the guest; provisioning must run before the lockdown (SKIP_EGRESS=1 to re-provision after 'sudo systemctl stop nftables')"
log "sanity ok: admin=$(id -un), $(. /etc/os-release; echo "$PRETTY_NAME"), kernel $(uname -r), $(uname -m)"

### 1. base packages
log "apt: base packages"
sudo apt-get update -q
sudo apt-get install -y -q git curl jq unzip ca-certificates gnupg tinyproxy nftables

### 2. gVisor + Docker runtime (network already none at the runtime level)
log "gVisor (runsc) — arm64/x86_64, Linux >= 5.6"
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor --yes -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" \
  | sudo tee /etc/apt/sources.list.d/gvisor.list >/dev/null
sudo apt-get update -q && sudo apt-get install -y -q runsc
sudo runsc install -- --network=none          # writes runtimes.runsc into /etc/docker/daemon.json (merges existing keys)
sudo systemctl restart docker
for img in $PREPULL_IMAGES; do docker pull -q "$img"; done
docker run --rm --runtime=runsc hello-world >/dev/null && log "runsc runtime works (systrap platform, no nested KVM needed)"
echo "NOTE: Colima regenerates daemon.json from the 'docker:' key of ~/.colima/appsec/colima.yaml on restart."
echo "      To make the runtime survive 'colima restart', mirror it there (colima start appsec --edit):"
echo '        docker: { runtimes: { runsc: { path: /usr/bin/runsc, runtimeArgs: ["--network=none"] } } }'

### 3. the unprivileged agent user
log "agent user '$AGENT_USER': no sudo, no docker group, home 0750"
id -u "$AGENT_USER" >/dev/null 2>&1 || sudo useradd -m -U -s /bin/bash "$AGENT_USER"
for g in sudo admin adm docker lxd; do sudo gpasswd -d "$AGENT_USER" "$g" >/dev/null 2>&1 || true; done
sudo chmod 750 "/home/$AGENT_USER" "$HOME"           # agent cannot read the admin home and vice versa (root excepted)
if sudo -u "$AGENT_USER" sudo -n true 2>/dev/null; then die "'$AGENT_USER' can sudo — check /etc/sudoers.d and group membership"; fi
if grep -rl "$AGENT_USER" /etc/sudoers /etc/sudoers.d 2>/dev/null | grep -q .; then die "'$AGENT_USER' appears in sudoers"; fi
log "agent user cannot sudo (checked)"

### 4. Node via nvm + OpenCode — installed FOR THE AGENT USER (the admin never runs the agent)
log "nvm ${NVM_VERSION} + Node ${NODE_VERSION} + ${OPENCODE_PKG} for '$AGENT_USER'"
AGENT_SETUP="$(mktemp)"
cat > "$AGENT_SETUP" <<'AGENT'
set -euo pipefail
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
  curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" | PROFILE=/dev/null bash
  grep -q 'NVM_DIR' "$HOME/.bashrc" || cat >> "$HOME/.bashrc" <<'RC'
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
RC
fi
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
nvm install "$NODE_VERSION" >/dev/null
nvm alias default "$(nvm current)" >/dev/null          # 'nvm version --lts' resolves to N/A; the just-installed version is what we want
# npm >= 11.19 blocks package install scripts by default; opencode-ai's postinstall fetches its platform binary
npm install -g --allow-scripts="${OPENCODE_PKG%%@*}" "$OPENCODE_PKG" >/dev/null
opencode --version >/dev/null 2>&1 || { echo "opencode installed but does not run" >&2; exit 1; }
echo "node $(node --version), npm $(npm --version), opencode $(opencode --version)"
AGENT
sudo install -m 0644 -o "$AGENT_USER" "$AGENT_SETUP" "/home/$AGENT_USER/.agent-setup.sh"; rm -f "$AGENT_SETUP"
as_agent env NVM_VERSION="$NVM_VERSION" NODE_VERSION="$NODE_VERSION" OPENCODE_PKG="$OPENCODE_PKG" bash "/home/$AGENT_USER/.agent-setup.sh"
sudo rm -f "/home/$AGENT_USER/.agent-setup.sh"

### 5. tinyproxy: default-deny hostname allowlist, listens on loopback only (or docker0 too, if asked)
log "tinyproxy on 127.0.0.1:${PROXY_PORT} with default-deny allowlist"
printf '%s\n' "$ALLOWLIST" | sed '/^\s*$/d' | sudo tee /etc/tinyproxy/allowlist >/dev/null
if [ "$ALLOW_CONTAINER_PROXY" = "1" ]; then
  LISTEN_BLOCK=$'# no Listen line: bind all guest interfaces so containers can reach the proxy via the docker0 gateway; Allow restricts clients\nAllow 127.0.0.1\nAllow 172.17.0.0/16'
else
  LISTEN_BLOCK=$'Listen 127.0.0.1\nAllow 127.0.0.1'
fi
sudo tee /etc/tinyproxy/tinyproxy.conf >/dev/null <<CONF
User tinyproxy
Group tinyproxy
Port ${PROXY_PORT}
${LISTEN_BLOCK}
Timeout 600
FilterType fnmatch
FilterDefaultDeny Yes
Filter "/etc/tinyproxy/allowlist"
ConnectPort 443
LogLevel Connect
LogFile "/var/log/tinyproxy/tinyproxy.log"
PidFile "/run/tinyproxy/tinyproxy.pid"
CONF
sudo systemctl enable -q tinyproxy
sudo systemctl restart tinyproxy
sleep 1
[ "$(ps -o user= -C tinyproxy | head -1)" = "tinyproxy" ] || die "tinyproxy did not drop privileges to user 'tinyproxy' — the nft rules key on that uid"

### 6. proxy environment for everything the agent (and the admin's curl tests) runs
log "proxy env in both users' ~/.bashrc (guarded block)"
PROXY_RC="$(cat <<RC
# appsec-sandbox-proxy — all egress via the allowlisting proxy; git, npm, curl, OpenCode, Claude Code honour these
export HTTPS_PROXY=http://127.0.0.1:${PROXY_PORT} HTTP_PROXY=http://127.0.0.1:${PROXY_PORT}
export https_proxy=\$HTTPS_PROXY http_proxy=\$HTTP_PROXY
export NO_PROXY=localhost,127.0.0.1,172.17.0.0/16 no_proxy=localhost,127.0.0.1,172.17.0.0/16
RC
)"
grep -q '# appsec-sandbox-proxy' "$HOME/.bashrc" || printf '%s\n' "$PROXY_RC" >> "$HOME/.bashrc"
sudo grep -q '# appsec-sandbox-proxy' "/home/$AGENT_USER/.bashrc" || printf '%s\n' "$PROXY_RC" | sudo tee -a "/home/$AGENT_USER/.bashrc" >/dev/null
# ...and in /etc/environment (PAM applies it to every login, interactive or not — e.g. `sudo -iu agent opencode run ...`);
# root-owned, so the agent cannot edit it. Not a control (nftables is), a convenience that survives non-interactive shells.
sudo sed -i '/^# appsec-sandbox-proxy/,/^NO_PROXY=/d;/^no_proxy=/d' /etc/environment
sudo tee -a /etc/environment >/dev/null <<ENV
# appsec-sandbox-proxy
HTTPS_PROXY=http://127.0.0.1:${PROXY_PORT}
HTTP_PROXY=http://127.0.0.1:${PROXY_PORT}
https_proxy=http://127.0.0.1:${PROXY_PORT}
http_proxy=http://127.0.0.1:${PROXY_PORT}
NO_PROXY=localhost,127.0.0.1,172.17.0.0/16
no_proxy=localhost,127.0.0.1,172.17.0.0/16
ENV

### 7. nftables: default-deny egress — output (the VM's own traffic) AND forward (containers' traffic)
if [ "$SKIP_EGRESS" = "1" ]; then log "SKIP_EGRESS=1 — leaving the network open"; else
log "nftables default-deny egress (output + forward chains)"
for u in tinyproxy dnsmasq systemd-timesync; do getent passwd "$u" >/dev/null || die "expected system user '$u' missing"; done
LO_DNS_RULE=""
[ "$TIGHTEN_LO_DNS" = "1" ] && LO_DNS_RULE='    oifname "lo" udp dport 53 meta skuid != { "tinyproxy", "dnsmasq" } drop   # agent cannot use the stub resolver as a tunnel'
sudo tee /etc/nftables.conf >/dev/null <<NFT
#!/usr/sbin/nft -f
flush ruleset
table inet egress {
  chain output {
    type filter hook output priority 0; policy drop;
${LO_DNS_RULE}
    oifname { "lo", "docker0" } accept                                   # loopback; agent -> local target container
    oifname "br-*" accept                                                # agent -> containers on user-defined (incl. --internal) bridges
    ct state established,related accept
    meta skuid "tinyproxy" tcp dport 443 accept                          # only the proxy may leave
    meta skuid { "tinyproxy", "dnsmasq" } udp dport 53 accept            # proxy -> local dnsmasq stub (the address in /etc/resolv.conf) and the stub's upstream hop
    meta skuid { "tinyproxy", "dnsmasq" } tcp dport 53 accept
    meta skuid "systemd-timesync" udp dport 123 accept                   # keep the clock sane for TLS
    ip daddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16 } log prefix "egress-drop-lan " drop   # host gateway + LAN
    log prefix "egress-drop " drop
  }
  chain forward {
    # Container traffic is FORWARDED, not output: without this chain a container on the default
    # bridge (runc runtime) NATs straight to the internet, untouched by the rules above.
    type filter hook forward priority 0; policy drop;
    ct state established,related accept
    iifname { "docker0", "br-*" } oifname { "docker0", "br-*" } accept   # container <-> container (Docker's own isolation still separates bridges)
    log prefix "egress-drop-fwd " drop                                   # container -> eth0 (internet, host gateway, LAN): never
  }
}
NFT
sudo nft -c -f /etc/nftables.conf
sudo systemctl enable -q nftables
sudo systemctl restart nftables

### 8. verify
log "verification"
code() { curl -sS -o /dev/null -m 15 -w '%{http_code}' "$@" 2>/dev/null || true; }
direct=$(code https://example.com)
via_denied=$(code -x "http://127.0.0.1:${PROXY_PORT}" https://example.com)
first_allowed=$(printf '%s\n' "$ALLOWLIST" | sed '/^\s*$/d' | grep -v '^\*' | head -1)
via_allowed=$(code -x "http://127.0.0.1:${PROXY_PORT}" "https://${first_allowed}/")
# container on the DEFAULT runtime and bridge (the case the forward chain exists for). By IP, so a failing DNS
# lookup cannot mask a missing forward chain; the kernel log must show an egress-drop-fwd line for it.
container=$(timeout 30 docker run --rm curlimages/curl -sS -o /dev/null -m 10 -w '%{http_code}' https://1.1.1.1 2>/dev/null || true)
fwd_logged=$(sudo journalctl -k --no-pager --since '-2min' 2>/dev/null | grep -c 'egress-drop-fwd' || true)
agent_docker="blocked"; as_agent docker ps >/dev/null 2>&1 && agent_docker="ALLOWED"
printf '  direct  https://example.com                 -> %s (want 000: dropped)\n' "$direct"
printf '  proxied https://example.com                 -> %s (want 000 with CONNECT 403: filtered; check the log)\n' "$via_denied"
printf '  proxied https://%s -> %s (want 2xx-4xx from the site: reachable)\n' "$first_allowed" "$via_allowed"
printf '  runc container -> https://1.1.1.1            -> %s (want 000/empty: forward chain dropped it; %s egress-drop-fwd lines in the kernel log)\n' "${container:-000}" "$fwd_logged"
printf '  agent user -> docker socket                  -> %s (want blocked)\n' "$agent_docker"
[ "$direct" = "000" ] || die "direct egress still works — nftables not effective"
case "$via_allowed" in 000|5??) die "allowlisted host not reachable via proxy — check 'sudo journalctl -k | grep egress-drop' and /var/log/tinyproxy/tinyproxy.log";; esac
case "${container:-000}" in 000|"") ;; *) die "a default-runtime container reached the internet — forward chain not effective";; esac
[ "${fwd_logged:-0}" -gt 0 ] || die "container egress was not dropped BY THE FORWARD CHAIN (no egress-drop-fwd log line) — something else blocked it; check 'sudo nft list chain inet egress forward'"
[ "$agent_docker" = "blocked" ] || die "agent user can talk to the Docker socket (root-equivalent) — remove it from the docker group"
fi

log "done. Work as the agent user, in a NEW login shell (so its proxy env is loaded):"
cat <<NEXT
  sudo -iu ${AGENT_USER}                                             # the agent's shell: no sudo, no docker
  git clone https://github.com/<org>/<pilot-repo> ~/target          # over HTTPS, read-only token if private
  export ANTHROPIC_API_KEY="\$(read -rs k; echo "\$k")"               # paste; key must carry a spend cap
  opencode                                                          # /connect provider, /models, /status before touching the repo
  npx skills add google/mantis                                      # optional: Mantis skills (interactive)
Operate from the admin shell (this one):
  sudo tail -f /var/log/tinyproxy/tinyproxy.log                     # widen /etc/tinyproxy/allowlist one hostname at a time
  docker run --rm --runtime=runsc -v /home/${AGENT_USER}/target:/work:ro <image> ...   # reproducers: admin starts them, agent cannot
  colima stop appsec                                                # kill switch, from the host
NEXT
