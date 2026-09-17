"""Command-line entry point: appsec-sbx ACTION [NAME] [options]."""
import argparse
import subprocess
import sys

from . import __version__, providers
from .hostos import host_note, run_interactive
from .git_source import require_git
from .lifecycle import Managed
from .policy import require
from .sbxcli import sbx

ENTRY = {"shell", "agent", "exec", "admin"}

DESCRIPTION = """\
appsec-sbx runs agents in Docker Sandboxes (sbx): a microVM with one
agent harness, one model provider and a filtered copy of your repository. Every action
takes the sandbox name as its first argument (default: appsec-sbx).

Before the first review, create a VM and test stop and provider-side credential
revocation. Start each independent review from a new VM or a clean reset:
  verify -> import -> skills -> shell --key -> (review inside) -> export -> stop
Revoke the review credential at the provider afterwards.
"""

EPILOG = """\
`appsec-sbx ACTION --help` describes one action. Documentation:
https://github.com/aai-institute/agentic-appsec-playbook (docs/)
"""

# (action, one-line help for the action list, description shown by `ACTION --help`)
ACTIONS = {
    "create": (
        "provision a clean workload VM with exactly one model provider",
        "Create the sandbox VM, bootstrap the harness, lock the network policy to the provider's "
        "endpoint plus the chosen package registry, and save a clean template that `reset` and "
        "`repro-create` start from. Takes a few minutes. Provider and harness are fixed for the "
        "life of the VM: to change them, `destroy` and `create` again."),
    "verify": (
        "run the entry guards and print guest versions",
        "Check the mounts, published ports, policy and MCP inventory the wrapper requires, then "
        "print the guest's tool versions and the result of its runsc probe. Run it after `create` "
        "and whenever a run behaves unexpectedly."),
    "import": (
        "import a local checkout or public GitHub repository into ~/target/source",
        "Copy the tracked working-tree contents of a local checkout (edits included, no Git "
        "metadata) into the guest. Untracked files, .env*, common credential files and agent or "
        "editor configuration directories are excluded; symlinks, hardlinks, special files and "
        "traversal paths are rejected; limits are 64 MiB per file and 512 MiB in total. A "
        "manifest with per-file SHA-256 values is written beside host state (import.json). An "
        "existing target is kept unless --replace is given. Public GitHub URLs are fetched "
        "into a temporary host checkout; --ref selects a branch, tag or commit (default: main). "
        "The URL, requested ref and resolved commit are recorded in import.json. The guest "
        "needs no GitHub access. Private repositories require a local checkout. "
        "Use reset before an independent review; --replace only swaps the target files."),
    "skills": (
        "install a skill pack from a local checkout or public GitHub URL",
        "Install the immediate subdirectories of a Git checkout that contain a SKILL.md into the "
        "selected harness's user-level skills directory; everything else in the checkout is "
        "skipped and counted. Records the checkout's commit, a dirty flag and per-file hashes "
        "beside host state (skills.json). Skill names use lowercase letters, digits and single "
        "hyphens. Names already installed are refused unless --replace is given. "
        "GitHub URLs are fetched into a temporary host checkout; --ref defaults to main and "
        "--subdir selects the pack directory. Records the URL, requested ref and resolved commit. "
        "The guest needs no GitHub access. Private repositories require a local checkout."),
    "key": (
        "place the provider key in the guest (prompted, never on the command line)",
        "Read the key from the environment variable named by the provider profile, or prompt "
        "for it without echo, and write it to a tmpfs file the workload can read but not "
        "modify. The file disappears when the VM stops, including sbx's idle stop about a "
        "minute after the last session ends, so `shell --key` (place the key, then enter) is "
        "the usual form."),
    "unkey": (
        "remove the key file and the harness login stores from the guest",
        "Delete the tmpfs key file and the harness credential stores on the workload user's "
        "home (Claude Code, Codex, OpenCode). Running processes keep tokens they already hold; "
        "revoking a key or seat at the provider is a separate action."),
    "shell": (
        "interactive shell in the VM as the unprivileged workload user",
        "Enter the VM as the workload user (no sudo, no Docker, clean environment) in "
        "~/target/source. The VM stops itself about a minute after the last session ends and "
        "takes the tmpfs key with it, so --key is the normal way to enter for a run."),
    "agent": (
        "alias of shell",
        "Same as `shell`."),
    "exec": (
        "run one command in the VM as the workload user",
        "Run a single command as the unprivileged workload user and return its exit status. "
        "Write the command after `--`. An exec that stays open (for example `-- sleep 7200`) "
        "counts as a session and keeps the VM from stopping during an unattended run."),
    "export": (
        "save ~/out as an opaque tar.gz on the host (never extracted)",
        "Archive the workload's ~/out directory into a new file on the host. The wrapper does "
        "not extract or inspect it: treat the archive as untrusted output and open it in an "
        "empty directory with a tool that executes nothing."),
    "put": (
        "copy one host file to a new path under /home/appsec",
        "Copy a single host file into the guest. The destination must be an absolute path under "
        "/home/appsec/ that does not exist yet; directories and traversal are refused."),
    "logs": (
        "print the recent policy log (allowed and denied connections)",
        "Print the last 30 entries of sbx's policy log for this sandbox: which hosts the "
        "workload reached and which requests the profile denied, with timestamps."),
    "status": (
        "print sbx's description of the VM (sbx inspect)",
        "Print `sbx inspect` for this sandbox as JSON: state, sessions, resources, identifiers."),
    "stop": (
        "kill switch: remove the credentials, stop the VM and its reproducers",
        "Stop the reproducer VMs created through this primary, remove the key file and harness "
        "login stores from a running primary, then stop it. Disk contents stay; nothing is "
        "revoked at the provider."),
    "repro-create": (
        "create an offline reproducer VM from this primary's clean template",
        "Create a second VM from the primary's clean template (tools installed, nothing "
        "imported) with no network at all and no model key, recorded as a reproducer of this "
        "primary so that `stop` and `reset` include it. Use `import`, `shell`, `exec` and "
        "`export` on it under its own name; `key` refuses it."),
    "reset": (
        "DELETE the VM's current state and recreate it from the clean template",
        "Remove the primary and its recorded reproducers, then create the primary again from "
        "the template saved by `create`. The installed tools stay; the imported target, ~/out, "
        "installed skills, harness state and login stores are gone. `export` first, run "
        "`skills` again afterwards. Reset is required before each independent review, including "
        "repeat passes and comparisons. Resuming the same interrupted review can keep its state."),
    "destroy": (
        "remove the VM and its reproducers entirely",
        "Remove the primary and its recorded reproducers from sbx. The host state directory and "
        "the saved template are kept."),
    "admin": (
        "root maintenance shell (outside the workload boundary)",
        "Enter the VM as root for trusted setup work. Nothing done here is contained by the "
        "workload boundary; do not run the agent from it."),
}


def build_parser():
    parser = argparse.ArgumentParser(prog="appsec-sbx", description=DESCRIPTION, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"appsec-sbx {__version__}")
    sub = parser.add_subparsers(dest="action", required=True, metavar="ACTION")

    def add(action, name_help="sbx sandbox name (default appsec-sbx)"):
        help_text, description = ACTIONS[action]
        p = sub.add_parser(action, help=help_text, description=description)
        p.add_argument("name", nargs="?", default="appsec-sbx", help=name_help)
        return p

    create = add("create", "name for the new sandbox (default appsec-sbx)")
    provider = create.add_mutually_exclusive_group()
    provider.add_argument("--provider", choices=sorted(providers.PROVIDERS),
                          help=f"model provider preset; decides the allowlist, the key variable and the "
                               f"default harness (default {providers.DEFAULT_PROVIDER})")
    provider.add_argument("--endpoint", metavar="HOST:PORT",
                          help="one exact model endpoint instead of a preset; needs --key-var")
    create.add_argument("--key-var", metavar="NAME",
                        help="with --endpoint: environment variable the harness reads the key from")
    create.add_argument("--harness", choices=providers.HARNESSES,
                        help="agent harness installed by the bootstrap (default follows the provider: "
                             "claude-code for the Claude seat, codex for Codex, otherwise opencode)")
    registry = create.add_mutually_exclusive_group()
    registry.add_argument("--registry", metavar="NAME|HOST:PORT", action="append",
                          help=f"package registry the workload may reach; repeatable; a name "
                               f"({', '.join(sorted(providers.REGISTRIES))}) or an exact HOST:PORT such as "
                               f"an organisation mirror (default npm)")
    registry.add_argument("--no-registry", action="store_true", help="allow no package registry at all")

    add("verify")
    imp = add("import")
    imp.add_argument("source", help="local Git checkout or public https://github.com/OWNER/REPO URL")
    imp.add_argument("--ref", help="GitHub branch, tag or commit (default: main); URLs only")
    imp.add_argument("--replace", action="store_true",
                     help="remove an existing ~/target/source first (harness state, ~/out and the key stay)")
    skills = add("skills")
    skills.add_argument("source", help="local pack directory or public https://github.com/OWNER/REPO URL")
    skills.add_argument("--ref", help="GitHub branch, tag or commit (default: main); URLs only")
    skills.add_argument("--subdir", help="pack directory within the GitHub repository (default: root); URLs only")
    skills.add_argument("--replace", action="store_true", help="overwrite skills of the same name")
    add("key")
    add("unkey")
    execp = add("exec")
    for p in (add("shell"), add("agent"), execp):
        # The VM stops itself about a minute after its last session and the tmpfs key goes with it,
        # so key-then-enter is one step here.
        p.add_argument("--key", action="store_true",
                       help="place the provider key first (as `key`), then enter; for exec, write it before the name")
    execp.add_argument("command", nargs=argparse.REMAINDER, help="the command, written after --")
    add("export").add_argument("archive", help="path of the new archive on the host (must not exist)")
    put = add("put")
    put.add_argument("source", help="host file")
    put.add_argument("destination", help="absolute guest path under /home/appsec/ that does not exist yet")
    add("logs")
    add("status")
    add("stop")
    add("repro-create", "name of the primary VM (default appsec-sbx)").add_argument(
        "new_name", help="name for the new reproducer VM")
    add("reset")
    add("destroy")
    add("admin")
    return parser


def dispatch(args):
    if args.action in {"import", "skills"}:
        require_git()
    vm = Managed(args.name)
    with vm.lock() as lock:
        action = args.action
        if action == "create":
            if args.provider is None and args.endpoint is None:
                args.provider = providers.DEFAULT_PROVIDER
            registry = None if args.no_registry else (args.registry or ["npm"])
            profile = providers.resolve(args.provider, args.endpoint, args.key_var, registry, args.harness)
            vm.create(profile)
        elif action == "reset":
            vm.reset()
        elif action == "repro-create":
            vm.create_reproducer(args.new_name)
        elif action == "stop":
            vm.owned()
            vm.stop()
        elif action == "destroy":
            vm.destroy()
        elif action == "status":
            vm.owned()
            sbx("inspect", vm.name, "--json")
        elif action == "logs":
            vm.owned()
            sbx("policy", "log", vm.name, "--limit", "30")
        else:
            vm.guard()
            if action in ENTRY:
                command = args.command if action == "exec" else ()
                if command[:1] == ["--"]:
                    command = command[1:]
                if getattr(args, "key", False):
                    vm.inject_key()
                if action != "admin":
                    vm.credential_hint()
                cmd = vm.entry_command(action, command)
                lock.release()
                return run_interactive(cmd)
            elif action == "key":
                vm.inject_key()
            elif action == "unkey":
                vm.remove_key()
            elif action == "import":
                vm.import_repo(args.source, replace=args.replace, ref=args.ref)
            elif action == "export":
                vm.export_output(args.archive)
            elif action == "skills":
                vm.install_skills(args.source, replace=args.replace, ref=args.ref, subdir=args.subdir)
            elif action == "put":
                vm.put_file(args.source, args.destination)
            elif action == "verify":
                vm.verify()
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    host_note()
    try:
        sys.exit(dispatch(args))
    except (RuntimeError, providers.ProfileError, subprocess.CalledProcessError, OSError) as error:
        sys.exit(f"ERROR: {error}")
