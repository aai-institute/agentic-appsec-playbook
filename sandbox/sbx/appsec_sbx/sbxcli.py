"""Thin wrappers around the sbx CLI and the in-guest entry checks."""
import json
import shlex
import subprocess
import sys

from .policy import require


def run(args, *, capture=False, check=True, **kwargs):
    if capture:
        kwargs["stdout"] = subprocess.PIPE
    return subprocess.run([str(a) for a in args], check=check, **kwargs)


def sbx(*args, **kwargs):
    return run(["sbx", *args], **kwargs)


def js(*args):
    """One sbx --json call, or a RuntimeError naming the command and what it actually printed.

    A bare JSONDecodeError hid the first Linux failure (2026-09-11: `policy ls --json` returned
    exit 0 with empty stdout). sbx's own diagnostics stay visible on stderr.
    """
    command = ["sbx", *(str(a) for a in args), "--json"]
    done = run(command, capture=True, stderr=subprocess.PIPE, check=False)
    if done.stderr:
        sys.stderr.buffer.write(done.stderr)
        sys.stderr.flush()
    text = done.stdout.decode(errors="replace")
    try:
        if done.returncode == 0:
            return json.loads(text)
    except json.JSONDecodeError:
        pass
    shown = text.strip()
    shown = (shown[:400] + "...") if len(shown) > 400 else (shown or "<empty>")
    raise RuntimeError(f"{shlex.join(command)} exited {done.returncode} without a JSON document "
                       f"(stdout: {shown}). Run it by hand and check `sbx version`; the wrapper's "
                       "acceptance record is for sbx v0.42.1 on macOS (README.md)")


def guest(name, *args, user="root", **kwargs):
    # sbx 0.42.1 does not resolve guest-added usernames with -u in this test,
    # and can even return success after "user ... not found". Resolve in-guest.
    prefix = [] if user == "root" else ["sudo", "-H", "-u", user, "--"]
    return sbx("exec", "-u", "root", name, *prefix, *args, **kwargs)


def preflight():
    require(js("settings", "get", "ssh.agentForwardingEnabled")["value"] is False,
            "Disable SSH forwarding and restart the daemon first; see README.md")
    require(js("mcp", "ls").get("servers") == [],
            "MCP servers are configured; this workflow requires an empty MCP inventory")


def isolation(name):
    details = js("inspect", name)
    require(not details.get("workspaces") and not details.get("ports"),
            "Unexpected workspace or published port")
    require(js("ports", name) == [], "Unexpected published port")
    require(all(s["name"] == "mcpgateway" for s in details.get("secrets", [])),
            "Unexpected sbx credential binding")
    # Starts the VM. Run before any binary stdout transfer.
    guest(name, "true", capture=True)
    mounts = guest(name, "findmnt", "-rn", "-o", "TARGET,FSTYPE", capture=True).stdout.decode()
    for line in mounts.splitlines():
        target, fs = line.split()
        require(fs not in {"virtiofs", "9p", "fuse.sshfs"} or
                (fs == "virtiofs" and target in {"/etc/hosts", "/etc/resolv.conf"}),
                f"Unexpected host mount: {line}")
    guest(name, "sh", "-ec", "test ! -S /run/ssh-agent.sock; "
          "test -f /etc/appsec/ready; "
          "! sudo -u appsec sudo -n true 2>/dev/null; "
          "! sudo -u appsec docker ps >/dev/null 2>&1")
