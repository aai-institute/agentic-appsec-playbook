#!/usr/bin/env bash
# Runs as root in a NEW, workspace-free sbx shell sandbox, before importing code.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Non-interactive provisioning: `sbx exec` without a terminal passes TERM=unknown, which makes
# every tput call in the installers print `tput: unknown terminal "unknown"`. Harmless, but noisy.
export TERM=dumb
[ "$(id -u)" = 0 ] || { echo 'bootstrap requires guest root' >&2; exit 1; }
[ ! -e /etc/appsec/ready ] || { echo 'already provisioned; recreate to bootstrap' >&2; exit 1; }
AGENT_USER=appsec
HARNESS="${1:-opencode}"   # opencode | claude-code | codex | pi; one per VM, chosen by the host wrapper from the provider
case "$HARNESS" in opencode|claude-code|codex|pi) ;; *) echo "unknown harness: $HARNESS" >&2; exit 1;; esac
# The provider's key variable, or empty for a seat login. The key itself never enters the guest
# (threat model M17): the VM's kit declares the variable as proxy-managed, the workload sees the
# constant below, and sbx's host-side proxy puts the stored value into the request header.
KEY_VAR="${2:-}"
[[ -z "$KEY_VAR" || "$KEY_VAR" =~ ^[A-Z][A-Z0-9_]{2,63}$ ]] || { echo "bad key variable: $KEY_VAR" >&2; exit 1; }
# Workload Docker (threat model M26): "rootless" for `create --docker`, then the images to pull.
DOCKER_MODE="${3:-}"
case "$DOCKER_MODE" in ''|rootless) ;; *) echo "unknown Docker access model: $DOCKER_MODE" >&2; exit 1;; esac
WORKLOAD_IMAGES=("${@:4}")
for image in "${WORKLOAD_IMAGES[@]}"; do
  [[ "$image" =~ ^[a-z0-9][a-z0-9._/-]*(:[A-Za-z0-9_][A-Za-z0-9_.-]*)?(@sha256:[a-f0-9]{64})?$ ]] \
    || { echo "bad image reference: $image" >&2; exit 1; }
done
[ -n "$DOCKER_MODE" ] || [ "${#WORKLOAD_IMAGES[@]}" -eq 0 ] || { echo 'images need a Docker access model' >&2; exit 1; }
NODE_VERSION=24.20.0
NVM_VERSION=v0.40.7
OPENCODE_VERSION=1.18.33
CLAUDE_CODE_VERSION=2.1.285   # tier A2 harness; first exercised 2026-09-10 on 2.1.267; bumped 2026-09-30 (Opus 5.5 needs >=2.1.280, sandbox fixes through 2.1.285; same postinstall/prepare scripts as 2.1.267)
CODEX_VERSION=0.159.2         # OpenAI Codex CLI; package has no install scripts (rechecked 2026-09-30); 0.155-0.159 carry sandbox fixes; 0.154.0 ran in the guest 2026-09-25, 0.159.2 not-yet-tested
PI_VERSION=1.0.0              # Pi coding agent (@earendil-works/pi-coding-agent, released 2026-10-01); no install scripts (checked 2026-10-02)
# Ubuntu mirrors over HTTPS (threat model T34 / M24). apt verifies signatures either way; this
# removes the bootstrap's only plain-HTTP transfer and its dependence on the mirrors' port-80 path
# (2026-09-11: 30 s to first byte on every archive/security.ubuntu.com address from three networks,
# HTTPS to the same addresses under a second; a Linux x86_64 bootstrap took 396 s instead of ~60).
# The host wrapper grants these hosts on 443 only, so a remaining http:// URI could not be reached.
test -s /etc/ssl/certs/ca-certificates.crt || { echo 'ca-certificates missing; apt over HTTPS needs them' >&2; exit 1; }
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*; do
  if [ -f "$f" ]; then sed -i -E 's#http://(archive|security|ports)\.ubuntu\.com/#https://\1.ubuntu.com/#g' "$f"; fi
done
! grep -rhE '^[^#]*http://[a-z0-9.-]*ubuntu\.com/' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null \
  || { echo 'a plain-HTTP Ubuntu mirror is still configured' >&2; exit 1; }
apt-get update -q
apt-get install -y -q git curl jq unzip ca-certificates gnupg python3 sudo procps

id "$AGENT_USER" >/dev/null 2>&1 || useradd -m -U -s /bin/bash "$AGENT_USER"
chmod 750 /home/agent /home/appsec
install -d -o root -g root -m 0755 /etc/appsec /usr/local/libexec
install -d -o appsec -g appsec -m 0750 /home/appsec/target /home/appsec/out
for group in sudo admin adm docker lxd; do
  gpasswd -d appsec "$group" >/dev/null 2>&1 || true
done
if sudo -u appsec sudo -n true 2>/dev/null; then
  echo 'appsec unexpectedly has sudo access' >&2; exit 1
fi
if sudo -u appsec docker ps >/dev/null 2>&1; then
  echo 'appsec unexpectedly has Docker access' >&2; exit 1
fi

# Preserve only proxy convenience variables, not sbx/MCP credentials or host env.
python3 - <<'PY'
import os, shlex
from pathlib import Path
names = ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy')
Path('/etc/appsec/proxy.env').write_text(''.join(
    f'export {k}={shlex.quote(os.environ[k])}\n' for k in names if k in os.environ))
PY
# Login profile: common part, then only the block for the selected harness (M23: the
# guest carries no configuration for tools it does not have). Variables are `checked`
# against the respective binaries' string tables; the workload can unset them, so
# they stop drift, not a hostile agent.
cat > /etc/profile.d/appsec.sh <<'PROFILE'
if [ "$(id -un)" = appsec ]; then
  . /etc/appsec/proxy.env
  export NVM_DIR=/home/appsec/.nvm
  [ ! -s "$NVM_DIR/nvm.sh" ] || . "$NVM_DIR/nvm.sh"
  # The key variable appears only in sessions the host wrapper enters while a key is stored
  # for this VM (APPSEC_KEYED, carried through appsec-enter); its value is always the sentinel.
  [ -z "${APPSEC_KEYED:-}" ] || . /etc/appsec/credential.env
  unset APPSEC_KEYED
  [ ! -r /etc/appsec/harness.env ] || . /etc/appsec/harness.env
  [ ! -r /etc/appsec/docker.env ] || . /etc/appsec/docker.env
fi
PROFILE
case "$HARNESS" in
opencode)
  # Root-owned managed config (M11/M16): no self-update through the registry grant
  # (seen 2026-09-10), no session sharing, ~/out pre-allowed.
  cat > /etc/appsec/opencode.json <<'CONFIG'
{
  "$schema": "https://opencode.ai/config.json",
  "autoupdate": false,
  "share": "disabled",
  "permission": {
    "external_directory": { "/home/appsec/out/*": "allow" }
  }
}
CONFIG
  chmod 644 /etc/appsec/opencode.json
  # No catalogue/LSP downloads, no repo-supplied config (T22).
  cat > /etc/appsec/harness.env <<'ENV'
export OPENCODE_CONFIG=/etc/appsec/opencode.json
export OPENCODE_DISABLE_AUTOUPDATE=1 OPENCODE_DISABLE_SHARE=1
export OPENCODE_DISABLE_MODELS_FETCH=1 OPENCODE_DISABLE_LSP_DOWNLOAD=1
export OPENCODE_DISABLE_PROJECT_CONFIG=1
ENV
  ;;
claude-code)
  # No self-update, telemetry, error reports or bug command. Deliberately NOT the
  # blanket CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: it also suppresses the post-login
  # fetch of the seat's additional model options (Fable 5.1 hidden with it, 2026-09-10).
  cat > /etc/appsec/harness.env <<'ENV'
export DISABLE_AUTOUPDATER=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 DISABLE_BUG_COMMAND=1
ENV
  ;;
codex)
  # Codex reads ~/.codex/config.toml (agent-writable; drift prevention, not enforcement).
  # Keys checked in the 0.154.0 binary: check_for_update_on_startup (the check targets the
  # GitHub releases API, denied anyway), [analytics] enabled, projects.<path>.trust_level.
  # History persistence stays at its default so session transcripts remain as evidence.
  install -d -o appsec -g appsec -m 0700 /home/appsec/.codex
  # Codex keeps its own inner sandbox (workspace-write, no network for commands) on top
  # of the VM; ~/out is outside the workspace, so it is declared writable here rather
  # than prompted for at the end of every run (field names read from the 0.154.0 binary).
  # [features] plugins = false: without it Codex syncs the ChatGPT account's installed
  # plugins (connectors) into the guest from server-named vendor storage hosts at every
  # start and retries through the run (seen 2026-09-11, denied by the profile). The flag is
  # what `codex features disable plugins` writes (checked in the guest).
  cat > /home/appsec/.codex/config.toml <<'TOML'
check_for_update_on_startup = false

[analytics]
enabled = false

[features]
plugins = false

[sandbox_workspace_write]
writable_roots = ["/home/appsec/out"]

[projects."/home/appsec/target/source"]
trust_level = "trusted"
TOML
  chown appsec:appsec /home/appsec/.codex/config.toml
  : > /etc/appsec/harness.env
  ;;
pi)
  # Pi's `find` tool wraps fd and downloads it at first start when missing, which the offline
  # setting below blocks ("fd not found. Offline mode enabled", seen 2026-10-02); Ubuntu ships
  # it as fd-find with the binary named fdfind. ripgrep for the `grep` tool is in the image.
  apt-get install -y -q fd-find
  ln -sf /usr/bin/fdfind /usr/local/bin/fd
  # Pi reads ~/.pi/agent (agent-writable; drift prevention, not enforcement). Project `.pi`
  # configuration and `.agents/skills` under the target never load: trust is "never" and print
  # mode cannot ask (T22). Keys from settings.md and environment-variables.md, Pi 1.0.0.
  install -d -o appsec -g appsec -m 0700 /home/appsec/.pi /home/appsec/.pi/agent
  cat > /home/appsec/.pi/agent/settings.json <<'JSON'
{
  "defaultProjectTrust": "never",
  "defaultProvider": "openrouter",
  "enableInstallTelemetry": false,
  "enableAnalytics": false
}
JSON
  chown appsec:appsec /home/appsec/.pi/agent/settings.json
  # No automatic network activity besides the model API: no pi.dev version check, no model
  # catalog refresh, no telemetry. Deliberately not --offline, which the policy enforces anyway.
  cat > /etc/appsec/harness.env <<'ENV'
export PI_OFFLINE=1 PI_SKIP_VERSION_CHECK=1 PI_TELEMETRY=0
ENV
  ;;
esac
chmod 644 /etc/appsec/harness.env
# The sentinel the harness reads as its key. The entry below clears the environment, so sbx's
# own copy of the variable (set whether or not a value is stored) never reaches the workload;
# the login profile sources this root-owned file instead, and only when the wrapper says a key
# is stored, so a session entered after `unkey` has no key variable at all.
if [ -n "$KEY_VAR" ]; then
  printf 'export %s=proxy-managed\n' "$KEY_VAR" > /etc/appsec/credential.env
else
  : > /etc/appsec/credential.env
fi
chmod 644 /etc/appsec/credential.env
cat > /usr/local/libexec/appsec-enter <<'ENTER'
#!/bin/bash
set -euo pipefail
[ "$(id -un)" = appsec ] || exit 1
exec env -i HOME=/home/appsec USER=appsec LOGNAME=appsec ${APPSEC_KEYED:+APPSEC_KEYED=1} \
  TERM=xterm-256color PATH=/usr/local/bin:/usr/bin:/bin bash -l "$@"
ENTER
chmod 755 /usr/local/libexec/appsec-enter

curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/${NVM_VERSION}/install.sh" -o /tmp/appsec-nvm.sh
sudo -u appsec -H env PROFILE=/dev/null bash /tmp/appsec-nvm.sh
sudo -u appsec -H bash -c '
  set -euo pipefail
  . /etc/appsec/proxy.env
  export NVM_DIR=/home/appsec/.nvm
  . "$NVM_DIR/nvm.sh"
  nvm install "$1"
  nvm alias default "$1"
  case "$4" in opencode)
    npm install -g --allow-scripts=opencode-ai "opencode-ai@$2"
    opencode --version;;
  esac
  case "$4" in claude-code)
    # The package places its platform binary in a postinstall step (install.cjs); allow
    # scripts for this one package only, as for opencode-ai. Seen failing with
    # --ignore-scripts on 2026-09-10 ("claude native binary not installed").
    npm install -g --allow-scripts=@anthropic-ai/claude-code "@anthropic-ai/claude-code@$3"
    claude --version;;
  esac
  case "$4" in codex)
    # No install scripts in the package; the platform binary is an optional dependency.
    npm install -g --ignore-scripts "@openai/codex@$5"
    codex --version;;
  esac
  case "$4" in pi)
    # Pure JavaScript bundle with a WASM asset; no install scripts.
    npm install -g --ignore-scripts "@earendil-works/pi-coding-agent@$6"
    pi --version;;
  esac
' bootstrap "$NODE_VERSION" "$OPENCODE_VERSION" "$CLAUDE_CODE_VERSION" "$HARNESS" "$CODEX_VERSION" "$PI_VERSION"
rm -f /tmp/appsec-nvm.sh

curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor --yes -o /usr/share/keyrings/gvisor-archive-keyring.gpg
printf 'deb [arch=%s signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main\n' \
  "$(dpkg --print-architecture)" > /etc/apt/sources.list.d/gvisor.list
apt-get update -q
apt-get install -y -q runsc
runsc install -- --network=none
# sbx owns dockerd's lifecycle. Reload its runtime configuration in place.
pkill -HUP -x dockerd
for attempt in {1..20}; do
  docker info --format '{{json .Runtimes}}' | jq -e 'has("runsc")' >/dev/null && break
  sleep 1
done
docker info --format '{{json .Runtimes}}' | jq -e 'has("runsc")' >/dev/null
docker pull hello-world
docker pull curlimages/curl
if docker run --rm --runtime=runsc --network=none hello-world > /etc/appsec/runsc-probe.txt 2>&1; then
  echo available > /etc/appsec/runsc-status
else
  echo unavailable > /etc/appsec/runsc-status
  echo 'gVisor probe failed; use a separate offline sbx VM for reproducers.' >&2
fi
# Templates capture the root filesystem, not the private Docker data volume.
install -d -m 0755 /opt/appsec
docker save hello-world curlimages/curl -o /opt/appsec/images.tar

if [ "$DOCKER_MODE" = rootless ]; then
  # The workload's own daemon (M26), rootless: it and its containers run as appsec in a user
  # namespace, so its socket grants nothing the workload lacks; the admin daemon above stays
  # root's. Each step answers a guest fact from the 2026-10-05 probe (design/sbx-docker-profile.md).
  # Pinned to the image's engine: unpinned, the extras package upgraded docker-ce under sbx. Without
  # recommends: systemd's pull in systemd-resolved, which tries to replace /etc/resolv.conf, and
  # sysctl defaults (seen 2026-10-05). slirp4netns calls `ip` from iproute2 to set up the TAP device.
  ENGINE=$(dpkg-query -W -f='${Version}' docker-ce)
  apt-get install -y -q --no-install-recommends uidmap slirp4netns iproute2 zstd "docker-ce-rootless-extras=$ENGINE"
  [ "$(dpkg-query -W -f='${Version}' docker-ce)" = "$ENGINE" ] \
    || { echo 'docker-ce changed during the rootless install' >&2; exit 1; }
  # useradd gave appsec a subordinate ID range; it must be its own.
  for f in /etc/subuid /etc/subgid; do
    awk -F: -v f="$f" '
      { u[NR] = $1; s[NR] = $2; e[NR] = $2 + $3 }
      $1 == "appsec" { n++; a = $2; b = $2 + $3 }
      END {
        if (n != 1 || b - a < 65536) { print f ": appsec needs one range of at least 65536 IDs" > "/dev/stderr"; exit 1 }
        for (i in u) if (u[i] != "appsec" && s[i] < b && a < e[i]) { print f ": appsec range overlaps " u[i] > "/dev/stderr"; exit 1 }
      }' "$f"
  done
  # Per boot, as root: /run, /dev and mounts do not survive an idle stop, so the entry guard runs
  # this before every entry. No systemd in the guest: the daemon starts here, inside a cgroup that
  # caps all containers together (rootless Docker has no per-container limits without systemd).
  cat > /usr/local/libexec/appsec-docker-start <<'START'
#!/bin/bash
set -euo pipefail
MEMORY_MAX=6G   # of the VM's 8 GB; the rest stays for the harness
U=$(id -u appsec)
RUN=/run/user/$U
as_appsec() {
  sudo -u appsec -H -- env -i HOME=/home/appsec USER=appsec LOGNAME=appsec XDG_RUNTIME_DIR="$RUN" \
    DOCKER_HOST="unix://$RUN/docker.sock" PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin "$@"
}
as_appsec docker info >/dev/null 2>&1 && exit 0
# slirp4netns needs the TUN device; the guest's minimal /dev lacks the node.
mkdir -p /dev/net
[ -c /dev/net/tun ] || mknod -m 0666 /dev/net/tun c 10 200
install -d -o appsec -g appsec -m 0700 "$RUN" /var/lib/docker/appsec-rootless
# The overlay root cannot hold overlayfs layers; the ext4 Docker volume can, and templates skip it.
sudo -u appsec mkdir -p /home/appsec/.local/share/docker
findmnt -n /home/appsec/.local/share/docker >/dev/null \
  || mount --bind /var/lib/docker/appsec-rootless /home/appsec/.local/share/docker
mkdir -p /sys/fs/cgroup/appsec-docker
echo "$MEMORY_MAX" > /sys/fs/cgroup/appsec-docker/memory.max
echo 0 > /sys/fs/cgroup/appsec-docker/memory.swap.max 2>/dev/null || true
echo $$ > /sys/fs/cgroup/appsec-docker/cgroup.procs
as_appsec setsid dockerd-rootless.sh > "$RUN/dockerd.log" 2>&1 < /dev/null &
for attempt in $(seq 1 60); do
  as_appsec docker info >/dev/null 2>&1 && exit 0
  sleep 0.5
done
echo "the workload Docker daemon did not start; see $RUN/dockerd.log" >&2
exit 1
START
  chmod 755 /usr/local/libexec/appsec-docker-start
  U=$(id -u appsec)
  printf 'export XDG_RUNTIME_DIR=/run/user/%s DOCKER_HOST=unix:///run/user/%s/docker.sock\n' "$U" "$U" \
    > /etc/appsec/docker.env
  chmod 644 /etc/appsec/docker.env
  /usr/local/libexec/appsec-docker-start
  # Images enter here only, while the provisioning grants are open; the run allowlist has no
  # container registry unless --registry names one. The archive restores them after `reset`.
  as_workload_docker() { sudo -u appsec env DOCKER_HOST="unix:///run/user/$U/docker.sock" docker "$@"; }
  for image in "${WORKLOAD_IMAGES[@]}"; do as_workload_docker pull -q "$image"; done
  as_workload_docker image inspect --format '{{index .RepoDigests 0}}' "${WORKLOAD_IMAGES[@]}" \
    > /etc/appsec/workload-images.txt
  install -d -m 0755 /opt/appsec
  as_workload_docker save "${WORKLOAD_IMAGES[@]}" | zstd -q -T0 -o /opt/appsec/workload-images.tar.zst
  chmod 644 /opt/appsec/workload-images.tar.zst /etc/appsec/workload-images.txt
fi

{
  cat /etc/os-release
  uname -a
  echo "harness: $HARNESS"
  echo "key variable: ${KEY_VAR:-none} (proxy-managed)"
  sudo -u appsec /usr/local/libexec/appsec-enter -c 'node --version; npm --version; opencode --version 2>/dev/null || true; claude --version 2>/dev/null || true; codex --version 2>/dev/null || true; pi --version 2>/dev/null || true'
  runsc --version
  docker version --format '{{json .Server}}'
  docker image inspect hello-world curlimages/curl --format '{{json .RepoDigests}}'
  if [ "$DOCKER_MODE" = rootless ]; then
    echo "workload Docker: $DOCKER_MODE"
    rootlesskit --version
    slirp4netns --version | head -1
    cat /etc/appsec/workload-images.txt
  fi
} > /etc/appsec/versions.txt
date -u +%FT%TZ > /etc/appsec/ready
echo 'AppSec bootstrap complete; apply host policy before entering a workload shell.'
