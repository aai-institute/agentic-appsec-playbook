"""Opt-in rootless Docker for the workload (threat model M26; T08 T18 T23).

`create --docker` gives `appsec` its own rootless daemon. The daemon and its containers run as the
workload user in a user namespace, so the socket grants nothing the workload does not already
hold; the admin daemon that sbx starts stays root's and denied to the workload. Images enter
during provisioning, before the policy lock, and are recorded by digest; run-time pulls need a
named registry preset. sbx's own root daemon was rejected because guest root reaches the host
shares and relay behind sbx's 0.42.0 escapes. Design, guest probe and decisions:
design/sbx-docker-profile.md.
"""
import os
import re

from .providers import ProfileError

MODEL = "rootless"
DEFAULT_DISK = "32g"
# Pulled into every Docker VM for the container network probes (R3), as the admin daemon does.
PROBE_IMAGES = ("curlimages/curl",)
# Docker Hub's hosts are already provisioning grants (the admin images); GHCR's are added only
# when a ghcr.io image is named. GHCR redirects blob downloads to the second host.
GHCR_HOSTS = {"ghcr.io:443", "pkg-containers.githubusercontent.com:443"}
REGISTRIES = ("docker.io", "ghcr.io")

START = "/usr/local/libexec/appsec-docker-start"
ARCHIVE = "/opt/appsec/workload-images.tar.zst"
CGROUP = "/sys/fs/cgroup/appsec-docker"

_COMPONENT = r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*"
IMAGE = re.compile(rf"^{_COMPONENT}(?:/{_COMPONENT})*(?::[A-Za-z0-9_][A-Za-z0-9_.-]{{0,127}})?"
                   r"(?:@sha256:[a-f0-9]{64})?$")
DISK = re.compile(r"^[1-9][0-9]{0,3}g$")


def check_image(ref):
    """An image the bootstrap may pull: Docker Hub (implicit or docker.io/) or ghcr.io."""
    if not IMAGE.match(ref or ""):
        raise ProfileError(f"--image must be a lowercase image reference with an optional tag or "
                           f"sha256 digest: {ref!r}")
    first = ref.split("/", 1)[0]
    if "/" in ref and ("." in first or ":" in first or first == "localhost") and first not in REGISTRIES:
        raise ProfileError(f"--image registry must be one of {', '.join(REGISTRIES)}: {ref!r}")
    return ref


def profile(images=(), disk=None):
    """The `docker` entry of a VM profile; `reset` recreates the VM from it."""
    disk = disk or DEFAULT_DISK
    if not DISK.match(disk):
        raise ProfileError(f"--docker-disk must be a size in gigabytes such as 48g: {disk!r}")
    refs = list(dict.fromkeys(list(PROBE_IMAGES) + [check_image(i) for i in images]))
    return {"model": MODEL, "images": refs, "disk": disk}


def bootstrap_hosts(profile):
    """Provisioning grants the profile's images need beyond the wrapper's standing set."""
    docker = profile.get("docker") or {}
    return set(GHCR_HOSTS) if any(i.startswith("ghcr.io/") for i in docker.get("images", [])) else set()


def create_env(profile):
    """Environment for `sbx create`: sbx sizes one sandbox's /var/lib/docker volume from it.

    The workload daemon's data lives on that volume (the overlay root cannot hold overlayfs
    layers), so a Docker VM gets a larger one. None keeps the caller's environment.
    """
    docker = profile.get("docker")
    if not docker:
        return None
    return {**os.environ, "DOCKER_SANDBOXES_DOCKER_SIZE": docker["disk"]}


def bootstrap_args(profile):
    """Arguments after harness and key variable: the access model, then the images to pull."""
    docker = profile.get("docker")
    return [docker["model"], *docker["images"]] if docker else []


# Entry checks for a Docker VM, run as guest root after the start script (M20, M26). The admin
# daemon stays denied; the workload daemon must run as appsec, with user-namespace root mapped to
# appsec, inside the capped cgroup, on the Docker volume, and report itself as rootless.
GUARD = r"""
fail() { echo "workload Docker: $*" >&2; exit 1; }
U=$(id -u appsec)
! id -nG appsec | tr ' ' '\n' | grep -qx docker || fail "appsec is in the docker group"
! sudo -u appsec docker -H unix:///var/run/docker.sock version >/dev/null 2>&1 || fail "admin socket reachable"
P=$(pgrep -u appsec -x dockerd) || fail "no daemon owned by appsec"
[ "$(printf '%s\n' "$P" | wc -l)" -eq 1 ] || fail "more than one daemon"
awk -v u="$U" 'NR == 1 { ok = ($1 == 0 && $2 == u && $3 == 1) } END { exit !ok }' "/proc/$P/uid_map" \
  || fail "user namespace root is not appsec"
grep -qx "$P" CGROUP/cgroup.procs || fail "daemon outside the capped cgroup"
[ "$(cat CGROUP/memory.max)" != max ] || fail "no memory cap"
findmnt -n -o SOURCE /home/appsec/.local/share/docker | grep -q '\[/appsec-rootless\]' \
  || fail "data root is not on the Docker volume"
sudo -u appsec env DOCKER_HOST="unix:///run/user/$U/docker.sock" docker info --format '{{json .SecurityOptions}}' \
  | grep -q 'name=rootless' || fail "daemon does not report rootless mode"
""".replace("CGROUP", CGROUP)

# Reload the provisioned images after a create from the template: templates capture the root
# filesystem, not the Docker volume the daemon keeps them on.
LOAD = (f'zstd -dc {ARCHIVE} | sudo -u appsec env DOCKER_HOST="unix:///run/user/$(id -u appsec)/docker.sock" '
        'docker load -q')

# What `verify` prints about the daemon and its images.
REPORT = (f'U=$(id -u appsec); echo "memory cap shared by all containers: $(numfmt --to=iec $(cat {CGROUP}/memory.max))"; '
          'sudo -u appsec env DOCKER_HOST="unix:///run/user/$U/docker.sock" docker version '
          "--format 'workload daemon: Docker {{.Server.Version}}, rootless'; "
          'echo "provisioned images:"; sed "s/^/  /" /etc/appsec/workload-images.txt')
