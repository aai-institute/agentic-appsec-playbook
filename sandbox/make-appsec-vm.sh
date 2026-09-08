#!/usr/bin/env bash
# Host-side meta-bootstrap for the WG reference sandbox (macOS + Colima/Lima).
# Creates a dedicated, mount-less Colima VM, runs bootstrap-appsec-vm.sh inside
# it, persists the gVisor runtime in Colima's config, and clones the clean disks
# as the rollback baseline. Companion to reference-sandbox.md.
#
#   make-appsec-vm.sh create   [profile]   # VM + guest bootstrap + docker runtime + clean snapshot (default action)
#   make-appsec-vm.sh snapshot [profile]   # stop, clone disks -> *.clean, start
#   make-appsec-vm.sh rollback [profile]   # stop, restore *.clean, start
#   make-appsec-vm.sh start    [profile]   # start an EXISTING profile and re-check it has no host mounts (never creates one)
#   make-appsec-vm.sh shell    [profile]   # ssh in as the admin user (sudo, docker)
#   make-appsec-vm.sh agent    [profile]   # shell as the unprivileged agent user (no sudo, no docker) — run the agent here
#   make-appsec-vm.sh key      [profile] [VAR ...]  # put model API key(s) into the guest's tmpfs (/run/appsec/env): from the host env
#                                                  #   if VAR is set, else prompted. Default VAR: OPENROUTER_API_KEY. Never on disk, gone on stop
#   make-appsec-vm.sh unkey    [profile]   # remove them again
#   make-appsec-vm.sh stop     [profile]   # kill switch (graceful, then forced)
#   make-appsec-vm.sh destroy  [profile]   # colima delete incl. data disk
#
# Env knobs: CPUS (4) MEMORY (8) DISK (40) ROOT_DISK (20) NO_SNAPSHOT (0) AGENT_USER (agent);
# everything the guest script accepts (ALLOWLIST, SKIP_EGRESS, PREPULL_IMAGES, ...) is passed through.
#
# Layout Colima 0.10.x uses for a profile P (checked 2026-09-02):
#   ~/.colima/P/colima.yaml                    profile config (docker: key -> /etc/docker/daemon.json in the guest)
#   ~/.colima/_lima/colima-P/disk              root disk (raw, sparse; --root-disk GiB). Older instances have basedisk+diffdisk instead
#   ~/.colima/_lima/_disks/colima-P/datadisk   data disk (--disk GiB; docker images live here)
set -euo pipefail

ACTION="${1:-create}"; PROFILE="${2:-appsec}"
CPUS="${CPUS:-4}"; MEMORY="${MEMORY:-8}"; DISK="${DISK:-40}"; ROOT_DISK="${ROOT_DISK:-20}"; NO_SNAPSHOT="${NO_SNAPSHOT:-0}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUEST_SCRIPT="$HERE/bootstrap-appsec-vm.sh"
CFG="$HOME/.colima/$PROFILE/colima.yaml"
INSTDIR="$HOME/.colima/_lima/colima-$PROFILE"
DATADISK="$HOME/.colima/_lima/_disks/colima-$PROFILE/datadisk"
rootdisk() {  # Colima 0.10.x: single raw 'disk' file; older instances: basedisk + diffdisk (with 'disk' a symlink)
  if [ -f "$INSTDIR/disk" ] && [ ! -L "$INSTDIR/disk" ]; then echo "$INSTDIR/disk"
  elif [ -f "$INSTDIR/diffdisk" ]; then echo "$INSTDIR/diffdisk"
  else die "no root disk found in $INSTDIR"; fi
}
PASSTHRU=(ALLOWLIST SKIP_EGRESS TIGHTEN_LO_DNS ALLOW_CONTAINER_PROXY PREPULL_IMAGES PROXY_PORT NVM_VERSION NODE_VERSION OPENCODE_PKG AGENT_USER)
AGENT_USER="${AGENT_USER:-agent}"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
running() { colima list 2>/dev/null | awk -v p="$PROFILE" '$1==p && $2=="Running"' | grep -q .; }
exists()  { colima list 2>/dev/null | awk -v p="$PROFILE" '$1==p' | grep -q .; }
guest()   { colima ssh -p "$PROFILE" -- "$@"; }

need_tools() {
  [ "$(uname -s)" = "Darwin" ] || die "this wrapper is for macOS; on Linux create the VM with your tool of choice and run bootstrap-appsec-vm.sh inside"
  command -v colima >/dev/null || die "colima not found (brew install colima)"
  command -v limactl >/dev/null || die "limactl not found (brew install lima)"
  [ -f "$GUEST_SCRIPT" ] || die "guest script missing: $GUEST_SCRIPT"
}

assert_no_mounts() {
  if guest sh -c 'mount | grep -E "virtiofs|sshfs|9p"' 2>/dev/null | grep -q .; then
    die "host filesystem is mounted in the guest — this VM is not the sandbox we want. destroy it and recreate with --mount none"
  fi
  log "no host mounts in the guest (checked)"
}

patch_docker_runtime() {
  # Colima regenerates /etc/docker/daemon.json from the docker: key at every start,
  # so the runsc runtime registered by the guest script has to live here too.
  [ -f "$CFG" ] || die "profile config not found: $CFG"
  if grep -q 'runsc' "$CFG"; then log "docker runtimes.runsc already in $CFG"; return; fi
  python3 - "$CFG" <<'PY'
import sys, re, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
block = ('docker:\n'
         '  runtimes:\n'
         '    runsc:\n'
         '      path: /usr/bin/runsc\n'
         '      runtimeArgs: ["--network=none"]   # reproducers never get a network (appsec sandbox)\n')
if re.search(r'^docker:\s*\{\}\s*$', s, re.M):
    s = re.sub(r'^docker:\s*\{\}\s*$', block.rstrip('\n'), s, count=1, flags=re.M)
elif re.search(r'^docker:\s*$', s, re.M):
    s = re.sub(r'^docker:\s*$', block.rstrip('\n'), s, count=1, flags=re.M)   # existing keys follow; runtimes: inserted first
else:
    sys.exit("could not find a 'docker:' key to patch — add the runtimes block by hand (colima start --edit)")
p.write_text(s); print("patched", p)
PY
}

clone_disks() {  # APFS copy-on-write clones: instant, no extra space until blocks diverge
  local suffix="$1"
  for d in "$(rootdisk)" "$DATADISK"; do
    [ -f "$d" ] || die "disk not found: $d"
    cp -c "$d" "$d.$suffix" && log "cloned $(basename "$d") -> $(basename "$d").$suffix"
  done
}
restore_disks() {
  for d in "$(rootdisk)" "$DATADISK"; do
    [ -f "$d.clean" ] || die "no clean clone for $d — run 'snapshot' first"
    cp -c "$d.clean" "$d" && log "restored $(basename "$d") from .clean"
  done
}
stop_vm() {
  running || { log "$PROFILE already stopped"; return; }
  colima stop -p "$PROFILE" || { log "graceful stop failed, forcing"; colima stop -f -p "$PROFILE"; }
}

case "$ACTION" in
  create)
    need_tools
    if exists; then
      log "profile '$PROFILE' already exists — resuming: skipping VM creation, re-running the guest bootstrap (idempotent)"
      running || colima start -p "$PROFILE"
    else
      log "creating Colima VM '$PROFILE' (vz, no host mounts, ${CPUS} CPU, ${MEMORY} GiB, ${DISK} GiB data / ${ROOT_DISK} GiB root)"
      colima start "$PROFILE" --mount none --vm-type vz --cpus "$CPUS" --memory "$MEMORY" --disk "$DISK" --root-disk "$ROOT_DISK" --activate=false
    fi
    assert_no_mounts
    if [ "${REBOOTSTRAP:-0}" != "1" ] && guest systemctl is-active --quiet tinyproxy nftables 2>/dev/null; then
      log "guest already bootstrapped (tinyproxy + nftables active) — skipping; REBOOTSTRAP=1 to force"
    else
      guest sudo systemctl stop nftables 2>/dev/null || true   # re-provisioning needs the open internet; the script re-enables the lockdown at the end
      log "copying and running the guest bootstrap"
      guest sh -c 'cat > bootstrap-appsec-vm.sh' < "$GUEST_SCRIPT"     # stdin passes through colima ssh; a bare 'cat > f' would be one argv word
      envs=(); for v in "${PASSTHRU[@]}"; do [ -n "${!v:-}" ] && envs+=("$v=${!v}"); done
      guest env ${envs[@]+"${envs[@]}"} bash bootstrap-appsec-vm.sh   # empty-array-safe under set -u on macOS bash 3.2
    fi
    log "persisting the runsc runtime in Colima's config and taking the clean snapshot"
    stop_vm
    patch_docker_runtime
    if [ "$NO_SNAPSHOT" = "1" ]; then :; elif [ -f "$(rootdisk).clean" ]; then log "clean clone already exists — keeping it ('snapshot' to refresh)"; else clone_disks clean; fi
    colima start -p "$PROFILE"
    guest docker run --rm --runtime=runsc hello-world >/dev/null && log "runsc runtime survived the restart"
    log "done. agent shell:  $0 agent $PROFILE     admin shell:  $0 shell $PROFILE     kill switch:  $0 stop $PROFILE     rollback:  $0 rollback $PROFILE"
    ;;
  snapshot) need_tools; exists || die "no such profile"; stop_vm; clone_disks clean; colima start -p "$PROFILE" ;;
  rollback) need_tools; exists || die "no such profile"; stop_vm; restore_disks; colima start -p "$PROFILE"; assert_no_mounts ;;
  # NOTE: a bare `colima start <name>` on a profile that does not exist silently CREATES a default VM — 2 CPU, 2 GiB,
  # 100 GiB, and your home directory mounted writable (seen 2026-09-08). Every action here therefore checks `exists`
  # first and re-asserts the mount table after starting; use `create` to make a sandbox, never `colima start` by hand.
  start)    exists || die "no such profile '$PROFILE' — use 'create' (a bare 'colima start' would build a default VM with ~ mounted)"; running || colima start -p "$PROFILE"; assert_no_mounts ;;
  key)      # Keys travel host -> guest over ssh stdin (never argv, never a file on the host or the guest's disk) into
            # /run/appsec/env, a tmpfs file owned root:agent 0640: the agent can read it, cannot change it, and it
            # vanishes when the VM stops (the kill switch). Login shells of the agent source it via /etc/profile.d.
            exists || die "no such profile '$PROFILE'"; running || die "'$PROFILE' is not running"
            shift 2 2>/dev/null || shift $#; VARS=("$@"); [ ${#VARS[@]} -gt 0 ] || VARS=(OPENROUTER_API_KEY)
            payload=""
            for v in "${VARS[@]}"; do
              val="${!v:-}"
              if [ -z "$val" ]; then printf '%s: ' "$v" >&2; IFS= read -rs val </dev/tty; printf '\n' >&2; fi
              [ -n "$val" ] || die "empty value for $v"
              payload+="export $v=$(printf '%q' "$val")"$'\n'
            done
            printf '%s' "$payload" | guest sudo sh -c 'install -d -m 0750 -o root -g '"$AGENT_USER"' /run/appsec && umask 027 && cat > /run/appsec/env && chown root:'"$AGENT_USER"' /run/appsec/env && chmod 0640 /run/appsec/env'
            log "wrote ${VARS[*]} to /run/appsec/env in '$PROFILE' (tmpfs; cleared on stop). New agent login shells pick it up: $0 agent $PROFILE" ;;
  unkey)    exists || die "no such profile '$PROFILE'"; running || die "'$PROFILE' is not running"; guest sudo rm -f /run/appsec/env; log "removed /run/appsec/env from '$PROFILE'" ;;
  shell)    exists || die "no such profile '$PROFILE' — use 'create'"; running || { colima start -p "$PROFILE"; assert_no_mounts; }; exec colima ssh -p "$PROFILE" ;;
  agent)    exists || die "no such profile '$PROFILE' — use 'create'"; running || { colima start -p "$PROFILE"; assert_no_mounts; }; exec colima ssh -p "$PROFILE" -- sudo -iu "$AGENT_USER" ;;
  stop)     stop_vm ;;
  destroy)  exists || die "no such profile"; rm -f "$INSTDIR"/*.clean "$DATADISK.clean"; colima delete -f -d -p "$PROFILE"; log "deleted profile '$PROFILE' incl. data disk and clones" ;;
  *) die "unknown action '$ACTION' (create|start|snapshot|rollback|shell|agent|key|unkey|stop|destroy)" ;;
esac
