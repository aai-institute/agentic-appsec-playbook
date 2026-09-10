#!/usr/bin/env bash
# Runs as root in a NEW, workspace-free sbx shell sandbox, before importing code.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[ "$(id -u)" = 0 ] || { echo 'bootstrap requires guest root' >&2; exit 1; }
[ ! -e /etc/appsec/ready ] || { echo 'already provisioned; recreate to bootstrap' >&2; exit 1; }
AGENT_USER=appsec
HARNESS="${1:-opencode}"   # opencode | claude-code | both; chosen by the host wrapper from the provider
case "$HARNESS" in opencode|claude-code|both) ;; *) echo "unknown harness: $HARNESS" >&2; exit 1;; esac
NODE_VERSION=24.20.0
NVM_VERSION=v0.40.7
OPENCODE_VERSION=1.18.29
CLAUDE_CODE_VERSION=2.1.267   # tier A2 harness; first exercised 2026-09-10
apt-get update -q
apt-get install -y -q git curl jq unzip ca-certificates gnupg python3 sudo procps

id "$AGENT_USER" >/dev/null 2>&1 || useradd -m -U -s /bin/bash "$AGENT_USER"
chmod 750 /home/agent /home/appsec
install -d -o root -g root -m 0755 /etc/appsec /usr/local/libexec
install -d -o appsec -g appsec -m 0750 /home/appsec/target /home/appsec/out
install -d -o root -g appsec -m 0750 /run/appsec
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
# Root-owned managed harness config (threat model M11/M16). The variables below are
# `checked` against the OpenCode 1.18.30 binary's string table on 2026-09-10; the
# workload can unset them, so they stop drift, not a hostile agent.
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
cat > /etc/profile.d/appsec.sh <<'PROFILE'
if [ "$(id -un)" = appsec ]; then
  . /etc/appsec/proxy.env
  export NVM_DIR=/home/appsec/.nvm
  [ ! -s "$NVM_DIR/nvm.sh" ] || . "$NVM_DIR/nvm.sh"
  [ ! -r /run/appsec/env ] || . /run/appsec/env
  # OpenCode: no self-update through the registry grant (seen 2026-09-10), no
  # session sharing, no catalogue/LSP downloads, no repo-supplied config (T22).
  export OPENCODE_CONFIG=/etc/appsec/opencode.json
  export OPENCODE_DISABLE_AUTOUPDATE=1 OPENCODE_DISABLE_SHARE=1
  export OPENCODE_DISABLE_MODELS_FETCH=1 OPENCODE_DISABLE_LSP_DOWNLOAD=1
  export OPENCODE_DISABLE_PROJECT_CONFIG=1
  # Claude Code (tier A2): no self-update, telemetry, error reports or bug command.
  # Deliberately NOT the blanket CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: that also
  # suppresses the GrowthBook feature-flag fetch that decides which models the seat
  # may pick (Fable 5.1 is flag-gated; seen hidden in /model on 2026-09-10). The
  # flag CDN is on the claude-code profile's allowlist for the same reason (M23).
  export DISABLE_AUTOUPDATER=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 DISABLE_BUG_COMMAND=1
fi
PROFILE
cat > /usr/local/libexec/appsec-enter <<'ENTER'
#!/bin/bash
set -euo pipefail
[ "$(id -un)" = appsec ] || exit 1
exec env -i HOME=/home/appsec USER=appsec LOGNAME=appsec \
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
  case "$4" in opencode|both)
    npm install -g --allow-scripts=opencode-ai "opencode-ai@$2"
    opencode --version;;
  esac
  case "$4" in claude-code|both)
    # The package places its platform binary in a postinstall step (install.cjs); allow
    # scripts for this one package only, as for opencode-ai. Seen failing with
    # --ignore-scripts on 2026-09-10 ("claude native binary not installed").
    npm install -g --allow-scripts=@anthropic-ai/claude-code "@anthropic-ai/claude-code@$3"
    claude --version;;
  esac
' bootstrap "$NODE_VERSION" "$OPENCODE_VERSION" "$CLAUDE_CODE_VERSION" "$HARNESS"
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

{
  cat /etc/os-release
  uname -a
  echo "harness: $HARNESS"
  sudo -u appsec /usr/local/libexec/appsec-enter -c 'node --version; npm --version; opencode --version 2>/dev/null || true; claude --version 2>/dev/null || true'
  runsc --version
  docker version --format '{{json .Server}}'
  docker image inspect hello-world curlimages/curl --format '{{json .RepoDigests}}'
} > /etc/appsec/versions.txt
date -u +%FT%TZ > /etc/appsec/ready
echo 'AppSec bootstrap complete; apply host policy before entering a workload shell.'
