"""Managed sbx VMs: create, policy lock, import, skills, key, export, stop, reset."""
import contextlib
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

from . import providers
from .hostos import Lock, private_dir
from .policy import DENY, PROBES, canonical, compile_denies, require, validate_policy
from .sbxcli import guest, isolation, js, preflight, sbx
from .skill_source import pack_skill_source
from .transfer import guest_home_path, pack_repository, read_lstat

HERE = Path(__file__).resolve().parent
KIT = HERE / "kit"
BOOTSTRAP = HERE / "guest" / "bootstrap.sh"
# Where each harness discovers user-level skills (<dir>/<name>/SKILL.md). Claude Code and
# Codex and OpenCode paths checked in the guest 2026-09-11 (`codex debug prompt-input` and
# `opencode debug skill` list the installed skill); Claude Code's is documented, not exercised.
SKILL_DIRS = {
    "opencode": "/home/appsec/.config/opencode/skills",
    "claude-code": "/home/appsec/.claude/skills",
    "codex": "/home/appsec/.codex/skills",
}
# Pre-lockdown provisioning grants only; all are subtracted again by lock_policy().
# github.com is the nvm installer's git clone (seen 2026-09-10 via an inherited
# Balanced grant; a Locked Down global policy would otherwise fail the bootstrap).
# Ubuntu mirrors on 443 only (T34 / M24): the bootstrap rewrites the image's http:// sources first
# and stops if a plain-HTTP mirror remains, so no provisioning transfer runs in the clear.
BOOTSTRAP_ALLOW = {
    "ports.ubuntu.com:443", "archive.ubuntu.com:443", "security.ubuntu.com:443",
    "github.com:443", "raw.githubusercontent.com:443", "nodejs.org:443", "registry.npmjs.org:443",
    "gvisor.dev:443", "storage.googleapis.com:443", "download.docker.com:443", "auth.docker.io:443",
    "registry-1.docker.io:443", "production.cloudflare.docker.com:443",
    "production.cloudfront.docker.com:443",
    "docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com:443",
}


class Phases:
    """Wall-clock per create phase; printed on exit and kept in state.json (acceptance records).

    Added 2026-09-11 after a Linux x86_64 create took about ten minutes against about one on the
    Mac, with the guest's own timestamps clearing everything after the first package install.
    """

    def __init__(self):
        self.durations = {}
        self.mark = time.monotonic()

    def lap(self, name):
        now = time.monotonic()
        self.durations[name] = round(now - self.mark, 1)
        self.mark = now

    def report(self, prefix="Phases"):
        if self.durations:
            print(prefix + ": " + ", ".join(f"{k} {v:.0f}s" for k, v in self.durations.items()))


def policy(name):
    rules = js("policy", "ls")["rules"]
    return canonical([r for r in rules if r["scope"] in ("global", f"sandbox:{name}")])


def state_root():
    return Path(os.environ.get("APPSEC_SBX_STATE", "~/.local/state/agentic-appsec/sbx")).expanduser()


def migrate(data):
    """State written by control.py (v0.1) had no profile: OpenRouter or offline."""
    if data and "profile" not in data:
        data["profile"] = dict(providers.OFFLINE) if data.get("offline") else providers.resolve(
            providers.DEFAULT_PROVIDER)
    data.pop("offline", None)
    if data.get("profile") and data["profile"].get("endpoints"):
        # VMs before 2026-09-10 carried OpenCode; "both" (2026-09-10 only) installed OpenCode too.
        if data["profile"].get("harness") in (None, "both"):
            data["profile"]["harness"] = "opencode"
    return data


@contextlib.contextmanager
def lf_bootstrap():
    """The bootstrap staged with LF endings, whatever the host checkout carries (M22).

    Git for Windows defaults to core.autocrlf=true; the CRLF copy made bash reject
    `set -o pipefail\r` on the first Windows create (2026-09-14). `.gitattributes` pins
    LF for the guest files, this covers checkouts made before that pin.
    """
    fd, path = tempfile.mkstemp(prefix="appsec-bootstrap-", suffix=".sh")
    try:
        with os.fdopen(fd, "wb") as staged:
            staged.write(BOOTSTRAP.read_bytes().replace(b"\r\n", b"\n"))
        yield Path(path)
    finally:
        os.unlink(path)


class Managed:
    def __init__(self, name):
        require(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,48}", name) is not None,
                "Use a 2-49 character lowercase sbx name")
        self.name = name
        self.directory = state_root() / name
        private_dir(self.directory)
        self.path = self.directory / "state.json"
        stored = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.data = migrate(dict(stored))
        if self.data != stored:
            self.save()

    def lock(self, blocking=True):
        return Lock(self.directory / "lock", blocking)

    @property
    def profile(self):
        return self.data.get("profile") or providers.OFFLINE

    @property
    def allowed(self):
        return providers.allowed(self.profile)

    def save(self):
        temporary = self.directory / "state.tmp"
        temporary.write_text(json.dumps(self.data, indent=2) + "\n")
        if os.name != "nt":
            temporary.chmod(0o600)
        temporary.replace(self.path)

    def lookup(self):
        return next((s for s in js("ls")["sandboxes"] if s["name"] == self.name), None)

    def owned(self):
        current = self.lookup()
        require(current and current["id"] == self.data.get("id"),
                f"{self.name}: missing or not the VM recorded by this wrapper")
        require(not current.get("workspaces"), "Unexpected workspace mount")
        return current

    def guard(self):
        self.owned()
        try:
            require(self.data.get("ready"), "Provisioning incomplete; reset or destroy")
            preflight()
            require(policy(self.name) == self.data["policy"],
                    "Policy changed since provisioning; entry refused (reset to recompile)")
            isolation(self.name)
        except Exception:
            self.stop()
            raise

    def lock_policy(self):
        # VM has not accepted target files or keys at this point.
        allowed = self.allowed
        sbx("policy", "deny", "network", "--sandbox", self.name, "**")
        rules = policy(self.name)
        scoped = [r for r in rules if r["scope"] == f"sandbox:{self.name}"]
        for rule in scoped:
            if rule["resource_type"] == "network" and rule["decision"] == "allow":
                require(rule["editable"], "Unexpected non-editable kit grant")
                sbx("policy", "rm", "network", "--sandbox", self.name, "--id", rule["id"])
        if allowed:
            denies = compile_denies([r for r in rules if r["scope"] == "global"], allowed)
            sbx("policy", "deny", "network", "--sandbox", self.name, ",".join(sorted(denies)))
            sbx("policy", "allow", "network", "--sandbox", self.name, ",".join(sorted(allowed)))
            sbx("policy", "rm", "network", "--sandbox", self.name, "--resource", "**")
        for endpoint in sorted(allowed | PROBES):
            check = sbx("policy", "check", "network", "--sandbox", self.name,
                        endpoint, "--json", capture=True, check=False)
            result = json.loads(check.stdout)
            require(not result.get("governance", {}).get("active"),
                    "Central governance is outside this wrapper's policy compiler")
            require(result["allowed"] == (endpoint in allowed),
                    f"Unexpected policy decision: {endpoint}: {result}")
        self.data["policy"] = policy(self.name)
        validate_policy(self.data["policy"], self.name, allowed)

    def create(self, profile, template=None):
        preflight()
        require(self.lookup() is None, "Sandbox already exists; use shell, reset or destroy")
        # Validate the policy *before* installing anything or deleting a reset target.
        compile_denies([r for r in policy(self.name) if r["scope"] == "global"],
                       providers.allowed(profile))
        args = ["create", str(KIT), "--name", self.name, "--no-share-skills",
                "--cpus", "4", "--memory", "8g"]
        for resource in sorted(DENY | ({"**"} if template else set())):
            # The IP-wide denies also allow hostname-based bootstrap requests.
            args += ["--deny-network", resource]
        if template:
            args += ["--template", template]
        phases = Phases()
        sbx(*args)
        phases.lap("sbx create")
        # A new VM has no import; drop a manifest left by a destroyed predecessor.
        (self.directory / "import.json").unlink(missing_ok=True)
        self.data = {"id": self.lookup()["id"], "ready": False, "profile": profile}
        self.save()
        try:
            self.data["created_from"] = js("inspect", self.name)
            self.data["sbx_version"] = sbx("version", capture=True).stdout.decode().strip()
            if template:
                self.data["template"] = template
                guest(self.name, "docker", "load", "-i", "/opt/appsec/images.tar")
                phases.lap("image load")
            else:
                sbx("policy", "allow", "network", "--sandbox", self.name,
                    ",".join(sorted(BOOTSTRAP_ALLOW)))
                with lf_bootstrap() as staged:
                    sbx("cp", staged, f"{self.name}:/tmp/appsec-bootstrap.sh")
                phases.lap("grants")
                guest(self.name, "bash", "/tmp/appsec-bootstrap.sh", profile.get("harness", "opencode"))
                phases.lap("bootstrap")
            self.lock_policy()
            phases.lap("policy lock")
            isolation(self.name)
            phases.lap("isolation")
            if not template:
                template = f"appsec-clean:{uuid.uuid4().hex[:12]}"
                # This is the only snapshot point: before importing files or injecting a key.
                sbx("stop", self.name)
                sbx("template", "save", self.name, template)
                self.data["template"] = template
                phases.lap("template save")
            self.data["ready"] = True
            self.data["timing"] = phases.durations
            self.save()
            phases.report()
            print(f"Ready: {self.name} ({providers.describe(profile)}).")
        except BaseException:
            phases.report("Phases before failure")
            self.save()
            sbx("stop", self.name, check=False)
            raise

    def reset(self):
        self.owned()
        require(not self.data.get("parent"),
                "Reset the primary VM, or destroy this reproducer and create a new one")
        preflight()
        profile = self.profile
        compile_denies([r for r in policy(self.name) if r["scope"] == "global"],
                       providers.allowed(profile))
        template = self.data.get("template")
        require(template, "No clean template; destroy then create")
        self.destroy_children()
        # Down before the removal so a half-removed VM never looks ready; restored if sbx rm
        # failed without touching the VM (Windows over SSH, 2026-09-14: `sbx rm` needs the
        # login service that a key-based logon cannot reach, and the primary was left refused).
        self.data["ready"] = False
        self.save()
        try:
            sbx("rm", "--force", self.name)
        except subprocess.CalledProcessError:
            current = self.lookup()
            if current is not None and current["id"] == self.data.get("id"):
                self.data["ready"] = True
                self.save()
                raise RuntimeError(f"{self.name}: sbx rm failed and the VM is unchanged; nothing was reset "
                                   "(on Windows, run reset from a desktop session: sbx rm needs the login service)")
            raise
        (self.directory / "import.json").unlink(missing_ok=True)
        self.create(profile, template)

    def children(self):
        for name, identity in self.data.get("children", {}).items():
            child = Managed(name)
            require(child.data.get("id") == identity, f"Reproducer identity changed: {name}")
            current = child.lookup()
            if current is not None:
                require(current["id"] == identity, f"Reproducer name reused: {name}")
                yield child

    def stop(self):
        current = self.owned()
        errors = []
        try:
            for child in self.children():
                try:
                    child.stop()
                except Exception as error:
                    errors.append(str(error))
        finally:
            if current["status"] == "running":
                self.remove_credentials(check=False)
            sbx("stop", self.name)
        require(not errors, "Some reproducers could not be stopped: " + "; ".join(errors))

    def destroy_children(self):
        for child in self.children():
            child.destroy_children()
            sbx("rm", "--force", child.name)
            child.data["ready"] = False
            child.save()

    def destroy(self):
        self.owned()
        self.destroy_children()
        sbx("rm", "--force", self.name)
        self.data["ready"] = False
        self.save()

    def create_reproducer(self, name):
        self.guard()
        child = Managed(name)
        with child.lock(blocking=False):
            require(child.lookup() is None, "Reproducer name already exists")
            try:
                child.create(dict(providers.OFFLINE), self.data["template"])
            finally:
                current = child.lookup()
                if current is not None and child.data.get("id") == current["id"]:
                    child.data["parent"] = self.name
                    child.save()
                    self.data.setdefault("children", {})[child.name] = child.data["id"]
                    self.save()

    def inject_key(self):
        key_var = self.profile.get("key_var")
        require(self.profile.get("endpoints"), "Offline reproducer VMs never receive model keys")
        require(key_var, "This profile authenticates with the harness's own login inside the guest; "
                         "there is no key variable to inject")
        value = os.environ.get(key_var) or getpass.getpass(f"{key_var}: ")
        require(value and "\x00" not in value, "Invalid empty/NUL key")
        payload = f"export {key_var}={shlex.quote(value)}\n".encode()
        sbx("exec", "-i", "-u", "root", self.name, "sh", "-ec",
            "install -d -o root -g appsec -m 0750 /run/appsec; "
            "umask 027; cat > /run/appsec/env; chown root:appsec /run/appsec/env; chmod 640 /run/appsec/env",
            input=payload)
        print(f"{key_var} placed in guest tmpfs; new workload shells receive it")

    # Harness-written credential stores: Claude Code's browser login (access + refresh
    # token) and OpenCode's /connect. Both persist in the agent's home, so the wrapper
    # removes them together with the tmpfs key (threat model M23, T25).
    HARNESS_CREDENTIALS = ("/home/appsec/.claude/.credentials.json",
                           "/home/appsec/.local/share/opencode/auth.json",
                           "/home/appsec/.codex/auth.json")

    def remove_credentials(self, check=True):
        guest(self.name, "rm", "-f", "/run/appsec/env", check=check)
        guest(self.name, "rm", "-f", *self.HARNESS_CREDENTIALS, user="appsec", check=check)

    def credential_hint(self):
        """Say so before entry when the guest holds no model credential (T25: gone on every stop).

        sbx v0.42.1 stops a local VM about a minute after its last session ends (checked on macOS
        2026-09-14) and `sbx exec` restarts it silently, so a `key` that is not followed at once by
        an entry evaporates: on Windows that day a shell ran keyless after a `skills` install.
        """
        if not self.profile.get("endpoints"):
            return
        probe = guest(self.name, "sh", "-c", 'for f in "$@"; do test -e "$f" && exit 0; done; exit 1',
                      "probe", "/run/appsec/env", *self.HARNESS_CREDENTIALS, capture=True, check=False)
        if probe.returncode != 0:
            print("NOTE: the guest holds no model credential; the key file and harness login stores do "
                  "not survive a VM stop, and the VM stops itself about a minute after the last session "
                  "ends. Run `key` right before entering, or use `shell --key`.", file=sys.stderr)

    def remove_key(self):
        self.remove_credentials()
        print("Key file and harness credential stores removed; existing processes retain "
              "their tokens until stopped, and server-side revocation is a separate action")

    def import_repo(self, source, replace=False):
        with tempfile.TemporaryDirectory(prefix="appsec-import-") as temporary:
            archive = Path(temporary) / "source.tar.gz"
            manifest = pack_repository(source, archive)
            remote = f"/tmp/appsec-import-{uuid.uuid4().hex}.tar.gz"
            sbx("cp", archive, f"{self.name}:{remote}")
            guest(self.name, "chmod", "644", remote)
            try:
                # Extract without root privileges. Never overwrite an earlier import
                # unless asked; --replace removes only the target tree, not ~/out or state.
                clear = 'rm -rf /home/appsec/target/source; ' if replace else ''
                guest(self.name, "sh", "-ec", clear + 'mkdir /home/appsec/target/source; '
                      'tar --no-same-owner -xzf "$1" -C /home/appsec/target/source',
                      "import", remote, user="appsec")
            finally:
                guest(self.name, "rm", "-f", remote)
            (self.directory / "import.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"Imported {len(manifest['files'])} tracked working-tree files; "
                  f"excluded {len(manifest['excluded'])}. Guest: /home/appsec/target/source")

    def install_skills(self, source, replace=False, *, ref=None, subdir=None):
        """Skill pack from a host checkout into the harness skills directory (M14).

        The only way instructions enter the guest: the review prompt in sandbox/skills and
        third-party packs alike; the bootstrap installs no prompts. The guest never contacts a
        code host for this; the pack is pinned by the commit recorded in host state with
        per-file hashes. Skills already present are refused unless --replace names them.
        """
        harness = self.profile.get("harness")
        require(harness in SKILL_DIRS, f"No skills directory known for harness {harness!r}")
        skills_dir = SKILL_DIRS[harness]
        with tempfile.TemporaryDirectory(prefix="appsec-skills-") as temporary:
            archive = Path(temporary) / "skills.tar.gz"
            manifest = pack_skill_source(source, archive, ref=ref, subdir=subdir)
            remote = f"/tmp/appsec-skills-{uuid.uuid4().hex}.tar.gz"
            sbx("cp", archive, f"{self.name}:{remote}")
            guest(self.name, "chmod", "644", remote)
            try:
                if not replace:
                    # sbx exec may print its own lines (e.g. "Sandbox ... started successfully") on
                    # stdout, so only names from the pack count.
                    present = guest(self.name, "sh", "-c",
                                    'dir=$1; shift; for s in "$@"; do test ! -e "$dir/$s" || echo "$s"; done',
                                    "skills", skills_dir, *manifest["skills"], user="appsec", capture=True)
                    taken = [s for s in present.stdout.decode().split() if s in manifest["skills"]]
                    require(not taken, f"Already installed: {', '.join(taken)}; pass --replace to overwrite")
                guest(self.name, "sh", "-ec",
                      'dir=$1; archive=$2; shift 2; mkdir -p "$dir"; for s in "$@"; do rm -rf "$dir/$s"; done; '
                      'tar --no-same-owner -xzf "$archive" -C "$dir"',
                      "skills", skills_dir, remote, *manifest["skills"], user="appsec")
            finally:
                guest(self.name, "rm", "-f", remote)
        record_path = self.directory / "skills.json"
        records = json.loads(record_path.read_text()) if record_path.exists() else {}
        for name in manifest["skills"]:
            records[name] = {
                "source": manifest["source"], "commit": manifest["commit"], "dirty": manifest["dirty"],
                "subdirectory": manifest["subdirectory"],
                "harness": harness, "directory": f"{skills_dir}/{name}",
                "files": {k: v for k, v in manifest["files"].items() if k.split("/", 1)[0] == name},
            }
            if "requested_ref" in manifest:
                records[name]["requested_ref"] = manifest["requested_ref"]
        record_path.write_text(json.dumps(records, indent=2) + "\n")
        state = " (working tree has uncommitted changes)" if manifest["dirty"] else ""
        print(f"Installed {len(manifest['skills'])} skills from commit {manifest['commit'][:12]}{state} "
              f"into {skills_dir}: {', '.join(manifest['skills'])}")
        print(f"{len(manifest['files'])} files; skipped {len(manifest['skipped'])} outside skill "
              f"directories, excluded {len(manifest['excluded'])}. Record: {record_path}")

    def put_file(self, source, destination):
        """Copy one host file into the workload home (harness commands, prompts)."""
        path = Path(source).expanduser()
        data = read_lstat(path.parent, path.name)
        target = guest_home_path(destination)
        remote = f"/tmp/appsec-put-{uuid.uuid4().hex}"
        sbx("cp", path, f"{self.name}:{remote}")
        guest(self.name, "chmod", "644", remote)
        try:
            guest(self.name, "sh", "-ec", 'mkdir -p "$(dirname "$2")"; test ! -e "$2"; cat "$1" > "$2"',
                  "put", remote, target, user="appsec")
        finally:
            guest(self.name, "rm", "-f", remote)
        print(f"Placed {len(data)} bytes at {target} (sha256 {hashlib.sha256(data).hexdigest()[:16]}...)")

    def export_output(self, destination):
        path = Path(destination).expanduser().absolute()
        # Exclusive creation; output remains an opaque untrusted archive on the host.
        with path.open("xb") as stream:
            guest(self.name, "tar", "-czf", "-", "-C", "/home/appsec/out", ".",
                  user="appsec", stdout=stream)
        with path.open("rb") as stream:
            require(stream.read(2) == b"\x1f\x8b", "Export was not a gzip stream")
        print(f"Saved untrusted output archive (not extracted): {path}")

    def verify(self):
        guest(self.name, "cat", "/etc/appsec/versions.txt", "/etc/appsec/runsc-status")
        # Bootstrap-time versions can drift (harness self-update); report what runs now.
        guest(self.name, "/usr/local/libexec/appsec-enter", "-c",
              'printf "running now: node %s, opencode %s, claude %s, codex %s\\n" "$(node --version)" "$(opencode --version 2>/dev/null || echo -)" "$(claude --version 2>/dev/null | head -1 || echo -)" "$(codex --version 2>/dev/null | head -1 || echo -)"',
              user="appsec")
        print(f"Profile: {providers.describe(self.profile)}")
        print("Entry guards passed; this is not a complete threat-model certification")

    def entry_command(self, action, command=()):
        if action == "admin":
            # Root is deliberately outside the unprivileged workload boundary.
            return ["sbx", "exec", "-it", "-u", "root", self.name, "bash", "-l"]
        cmd = ["sbx", "exec", "-u", "root"]
        if action in {"shell", "agent"}:
            cmd += ["-it"]
        cmd += ["-w", "/home/appsec", self.name, "sudo", "-H", "-u", "appsec", "--",
                "/usr/local/libexec/appsec-enter"]
        if action == "exec":
            require(command, "exec requires a command")
            cmd += ["-c", 'exec "$@"', "appsec", *command]
        return cmd
