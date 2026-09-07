#!/usr/bin/env bash
# Bootstrap the WG reference sandbox inside a fresh Colima/Lima guest (Ubuntu 24.04).
# Companion to reference-sandbox.md — read that first; this script is the L2/L3
# provisioning it describes, condensed. Run INSIDE the guest as the normal Lima
# user (passwordless sudo), on a VM created with --mount none:
#
#   colima start appsec --mount none --vm-type vz --cpus 4 --memory 8 --disk 40 --activate=false
#   colima ssh -p appsec -- sh -c 'cat > bootstrap-appsec-vm.sh' < sandbox/bootstrap-appsec-vm.sh
#   colima ssh -p appsec -- bash bootstrap-appsec-vm.sh
#
# (Two steps on purpose: `bash -s < script` would let any stdin-reading command eat the script.)
#
# Order matters: everything that needs the open internet (apt, gVisor repo, nvm,
# Node, OpenCode, image pulls) runs BEFORE the egress lockdown. Afterwards only
# the proxy user can leave the VM, and only to ALLOWLIST hosts. Re-running is
# safe: package installs are idempotent, config files are overwritten, the
# bashrc block is guarded.
#
# Status: validated 2026-09-02 on Colima 0.10.3 / Lima 2.2.0, Apple silicon
# (tinyproxy + nftables + DNS hop); gVisor/OpenCode steps as documented upstream.
set -euo pipefail

### ---- knobs -----------------------------------------------------------------
PROXY_PORT="${PROXY_PORT:-8888}"
NVM_VERSION="${NVM_VERSION:-v0.40.7}"            # nvm-sh/nvm release tag (2026-08-18)
NODE_VERSION="${NODE_VERSION:---lts}"            # nvm target; LTS was v24 on 2026-09-02
OPENCODE_PKG="${OPENCODE_PKG:-opencode-ai@latest}"   # docs: npm install -g opencode-ai
SKIP_EGRESS="${SKIP_EGRESS:-0}"                  # 1 = provision only, leave the network open
TIGHTEN_LO_DNS="${TIGHTEN_LO_DNS:-0}"            # 1 = only proxy/dnsmasq may talk to the stub resolver (untested)
PREPULL_IMAGES="${PREPULL_IMAGES:-hello-world}"  # space-separated; pulled before lockdown (dockerd is root -> blocked later)
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

### 0. sanity
[ "$(id -u)" -ne 0 ] || die "run as the normal Lima user, not root (nvm/OpenCode are per-user)"
sudo -n true 2>/dev/null || die "passwordless sudo required (Lima default)"
grep -q 'ID=ubuntu' /etc/os-release || die "expected an Ubuntu guest (Colima >= 0.6 ships Ubuntu)"
if mount | grep -qE 'virtiofs|sshfs|9p'; then die "host mounts present — recreate the VM with --mount none"; fi
curl -fsS -o /dev/null https://github.com || die "no internet from the guest; provisioning must run before the lockdown (SKIP_EGRESS=1 to re-provision after 'sudo systemctl stop nftables')"
log "sanity ok: user=$(id -un), $(. /etc/os-release; echo "$PRETTY_NAME"), kernel $(uname -r), $(uname -m)"

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

### 3. Node via nvm + OpenCode
log "nvm ${NVM_VERSION} + Node ${NODE_VERSION} + ${OPENCODE_PKG}"
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
opencode --version >/dev/null 2>&1 || die "opencode installed but does not run — check 'npm install -g --allow-scripts=opencode-ai opencode-ai' output"
log "node $(node --version), npm $(npm --version), opencode $(opencode --version)"

### 4. tinyproxy: default-deny hostname allowlist, listens on loopback only
log "tinyproxy on 127.0.0.1:${PROXY_PORT} with default-deny allowlist"
printf '%s\n' "$ALLOWLIST" | sed '/^\s*$/d' | sudo tee /etc/tinyproxy/allowlist >/dev/null
sudo tee /etc/tinyproxy/tinyproxy.conf >/dev/null <<CONF
User tinyproxy
Group tinyproxy
Port ${PROXY_PORT}
Listen 127.0.0.1
Allow 127.0.0.1
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

### 5. proxy environment for everything the agent runs
log "proxy env in ~/.bashrc (guarded block)"
if ! grep -q '# appsec-sandbox-proxy' "$HOME/.bashrc"; then
  cat >> "$HOME/.bashrc" <<RC
# appsec-sandbox-proxy — all egress via the allowlisting proxy; git, npm, curl, OpenCode, Claude Code honour these
export HTTPS_PROXY=http://127.0.0.1:${PROXY_PORT} HTTP_PROXY=http://127.0.0.1:${PROXY_PORT}
export https_proxy=\$HTTPS_PROXY http_proxy=\$HTTP_PROXY
export NO_PROXY=localhost,127.0.0.1,172.17.0.0/16 no_proxy=localhost,127.0.0.1,172.17.0.0/16
RC
fi

### 6. nftables: default-deny egress, only proxy (+ resolver hop, + NTP) may leave
if [ "$SKIP_EGRESS" = "1" ]; then log "SKIP_EGRESS=1 — leaving the network open"; else
log "nftables default-deny egress"
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
    ct state established,related accept
    meta skuid "tinyproxy" tcp dport 443 accept                          # only the proxy may leave
    meta skuid { "tinyproxy", "dnsmasq" } udp dport 53 accept            # proxy -> local stub (192.168.5.3) and the stub's upstream hop
    meta skuid { "tinyproxy", "dnsmasq" } tcp dport 53 accept
    meta skuid "systemd-timesync" udp dport 123 accept                   # keep the clock sane for TLS
    ip daddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16 } log prefix "egress-drop-lan " drop   # host gateway + LAN
    log prefix "egress-drop " drop
  }
}
NFT
sudo nft -c -f /etc/nftables.conf
sudo systemctl enable -q nftables
sudo systemctl restart nftables

### 7. verify
log "verification"
code() { curl -sS -o /dev/null -m 15 -w '%{http_code}' "$@" 2>/dev/null || true; }
direct=$(code https://example.com)
via_denied=$(code -x "http://127.0.0.1:${PROXY_PORT}" https://example.com)
first_allowed=$(printf '%s\n' "$ALLOWLIST" | sed '/^\s*$/d' | grep -v '^\*' | head -1)
via_allowed=$(code -x "http://127.0.0.1:${PROXY_PORT}" "https://${first_allowed}/")
printf '  direct  https://example.com        -> %s (want 000: dropped)\n' "$direct"
printf '  proxied https://example.com        -> %s (want 000 with CONNECT 403: filtered; check the log)\n' "$via_denied"
printf '  proxied https://%s -> %s (want 2xx-4xx from the site: reachable)\n' "$first_allowed" "$via_allowed"
[ "$direct" = "000" ] || die "direct egress still works — nftables not effective"
case "$via_allowed" in 000|5??) die "allowlisted host not reachable via proxy — check 'sudo journalctl -k | grep egress-drop' and /var/log/tinyproxy/tinyproxy.log";; esac
fi

log "done. Next, in a NEW shell (so the proxy env is loaded):"
cat <<'NEXT'
  git clone https://github.com/<org>/<pilot-repo> ~/target        # over HTTPS, read-only token if private
  export ANTHROPIC_API_KEY="$(read -rs k; echo "$k")"              # paste; key must carry a spend cap
  opencode                                                          # /connect provider, /models, /status before touching the repo
  npx skills add google/mantis                                      # optional: Mantis skills (interactive)
  sudo tail -f /var/log/tinyproxy/tinyproxy.log                     # widen /etc/tinyproxy/allowlist one hostname at a time
  colima stop appsec                                                # kill switch, from the host
NEXT
