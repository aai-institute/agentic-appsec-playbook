"""Managed sbx VMs: create, policy lock, import, key, export, stop, reset."""
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import tempfile
import uuid

from . import providers
from .hostos import Lock, private_dir
from .policy import DENY, PROBES, canonical, compile_denies, require, validate_policy
from .sbxcli import guest, isolation, js, preflight, sbx
from .transfer import guest_home_path, pack_repository, read_lstat

HERE = Path(__file__).resolve().parent
KIT = HERE / "kit"
BOOTSTRAP = HERE / "guest" / "bootstrap.sh"
COMMANDS = HERE / "guest" / "commands"
# Pre-lockdown provisioning grants only; all are subtracted again by lock_policy().
# github.com is the nvm installer's git clone (seen 2026-09-10 via an inherited
# Balanced grant; a Locked Down global policy would otherwise fail the bootstrap).
BOOTSTRAP_ALLOW = {
    "ports.ubuntu.com:80", "archive.ubuntu.com:80", "security.ubuntu.com:80",
    "github.com:443", "raw.githubusercontent.com:443", "nodejs.org:443", "registry.npmjs.org:443",
    "gvisor.dev:443", "storage.googleapis.com:443", "download.docker.com:443", "auth.docker.io:443",
    "registry-1.docker.io:443", "production.cloudflare.docker.com:443",
    "production.cloudfront.docker.com:443",
    "docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com:443",
}


def claude_code_variant(text):
    """Swap the OpenCode frontmatter for Claude Code's: the `!` shell block needs an explicit tool allowlist."""
    require(text.startswith("---\n"), "command file must start with frontmatter")
    _, front, body = text.split("---\n", 2)
    description = next((line for line in front.splitlines() if line.startswith("description:")), "description: whole-repo review")
    return ("---\n" + description + "\n"
            "allowed-tools: Bash(find:*), Read, Glob, Grep, LS, Task, Write\n"
            "---\n" + body)


def codex_variant(text):
    """Codex custom prompt: description + argument-hint frontmatter; no shell block (support unverified)."""
    require(text.startswith("---\n"), "command file must start with frontmatter")
    _, front, body = text.split("---\n", 2)
    description = next((line for line in front.splitlines() if line.startswith("description:")), "description: whole-repo review")
    start = body.find("REPOSITORY FILES:")
    end = body.find("```", body.find("```", start) + 3) + 3 if start >= 0 else -1
    require(start >= 0 and end > start, "command file: repository listing block not found")
    body = body[:start] + ("REPOSITORY FILES:\n\nBegin by listing every file in the repository (excluding "
                           ".git, node_modules and .venv) with the tools available to you, and keep that "
                           "list in view while reviewing.") + body[end:]
    return "---\n" + description + "\nargument-hint: \"[focus]\"\n---\n" + body


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


class Managed:
    def __init__(self, name):
        require(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,48}", name) is not None,
                "Use a 2–49 character lowercase sbx name")
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
        sbx(*args)
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
            else:
                sbx("policy", "allow", "network", "--sandbox", self.name,
                    ",".join(sorted(BOOTSTRAP_ALLOW)))
                sbx("cp", BOOTSTRAP, f"{self.name}:/tmp/appsec-bootstrap.sh")
                guest(self.name, "bash", "/tmp/appsec-bootstrap.sh", profile.get("harness", "opencode"))
                self.install_commands(profile.get("harness", "opencode"))
            self.lock_policy()
            isolation(self.name)
            if not template:
                template = f"appsec-clean:{uuid.uuid4().hex[:12]}"
                # This is the only snapshot point: before importing files or injecting a key.
                sbx("stop", self.name)
                sbx("template", "save", self.name, template)
                self.data["template"] = template
            self.data["ready"] = True
            self.save()
            print(f"Ready: {self.name} ({providers.describe(profile)}).")
        except BaseException:
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
        self.data["ready"] = False
        self.save()
        self.destroy_children()
        sbx("rm", "--force", self.name)
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
        require(key_var, "Offline reproducer VMs never receive model keys")
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
                           "/home/appsec/.local/share/opencode/auth.json")

    def remove_credentials(self, check=True):
        guest(self.name, "rm", "-f", "/run/appsec/env", check=check)
        guest(self.name, "rm", "-f", *self.HARNESS_CREDENTIALS, user="appsec", check=check)

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

    def install_commands(self, harness="opencode"):
        """Whole-repo review prompt for the one installed harness; import strips project harness dirs."""
        for command in sorted(COMMANDS.glob("*.md")):
            text = command.read_text()
            if harness == "opencode":
                self.put_file(command, f"/home/appsec/.config/opencode/commands/{command.name}")
                continue
            # Distinct name: Claude Code's built-in /security-review stays diff-scoped.
            variant, destination = {
                "claude-code": (claude_code_variant, f"/home/appsec/.claude/commands/{command.stem}-repo.md"),
                "codex": (codex_variant, f"/home/appsec/.codex/prompts/{command.stem}-repo.md"),
            }[harness]
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
                handle.write(variant(text))
            try:
                self.put_file(handle.name, destination)
            finally:
                os.unlink(handle.name)

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
        print(f"Placed {len(data)} bytes at {target} (sha256 {hashlib.sha256(data).hexdigest()[:16]}…)")

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
