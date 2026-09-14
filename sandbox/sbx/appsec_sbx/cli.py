"""Command-line entry point: appsec-sbx ACTION [NAME] [options]."""
import argparse
import subprocess
import sys

from . import __version__, providers
from .hostos import host_note, run_interactive
from .lifecycle import Managed
from .policy import require
from .sbxcli import sbx

ENTRY = {"shell", "agent", "exec", "admin"}


def build_parser():
    parser = argparse.ArgumentParser(prog="appsec-sbx", description=__doc__)
    parser.add_argument("--version", action="version", version=f"appsec-sbx {__version__}")
    sub = parser.add_subparsers(dest="action", required=True, metavar="ACTION")

    def add(action, help_text, **kwargs):
        p = sub.add_parser(action, help=help_text, **kwargs)
        p.add_argument("name", nargs="?", default="appsec-sbx", help="sbx sandbox name (default appsec-sbx)")
        return p

    create = add("create", "provision a clean workload VM with exactly one model provider")
    provider = create.add_mutually_exclusive_group()
    provider.add_argument("--provider", choices=sorted(providers.PROVIDERS),
                          help=f"preset (default {providers.DEFAULT_PROVIDER})")
    provider.add_argument("--endpoint", metavar="HOST:PORT", help="custom model endpoint; needs --key-var")
    create.add_argument("--key-var", metavar="NAME", help="environment variable the harness reads the key from")
    create.add_argument("--harness", choices=providers.HARNESSES,
                        help="tool installed by the bootstrap (default follows the provider: "
                             "claude-code for the Claude seat, otherwise opencode)")
    registry = create.add_mutually_exclusive_group()
    registry.add_argument("--registry", metavar="NAME|HOST:PORT", action="append",
                          help=f"package registry allowed during the run; repeatable; names: "
                               f"{', '.join(sorted(providers.REGISTRIES))} (default npm)")
    registry.add_argument("--no-registry", action="store_true", help="allow no package registry")

    for action, text in [("shell", "interactive unprivileged workload shell"),
                         ("agent", "alias of shell"),
                         ("admin", "root maintenance shell (outside the workload boundary)"),
                         ("key", "place the provider key in guest tmpfs (stdin, never argv)"),
                         ("unkey", "remove the key file"),
                         ("verify", "run the entry guards and print guest versions"),
                         ("status", "sbx inspect"), ("logs", "recent policy log"),
                         ("stop", "kill switch: remove key, stop VM and its reproducers"),
                         ("reset", "DELETE current state, recreate from the clean template"),
                         ("destroy", "remove the VM and its reproducers")]:
        add(action, text)
    execp = add("exec", "run one command as the workload user")
    execp.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    imp = add("import", "filtered copy of a host Git checkout into ~/target/source")
    imp.add_argument("source")
    imp.add_argument("--replace", action="store_true",
                     help="remove an existing ~/target/source first (harness state and ~/out stay)")
    add("export", "opaque tar.gz of ~/out to a new host file").add_argument("archive")
    skills = add("skills", "install the skills of a host Git checkout (top-level dirs with SKILL.md) "
                           "into the harness's skills directory; nothing else from the checkout")
    skills.add_argument("source", help="checkout root, e.g. a pinned clone of google/mantis")
    skills.add_argument("--replace", action="store_true", help="overwrite skills of the same name")
    put = add("put", "copy one host file to a new path under /home/appsec (e.g. a command prompt)")
    put.add_argument("source")
    put.add_argument("destination", help="absolute guest path under /home/appsec/")
    add("repro-create", "offline reproducer VM from the primary's clean template").add_argument("new_name")
    return parser


def dispatch(args):
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
                cmd = vm.entry_command(action, command)
                lock.release()
                return run_interactive(cmd)
            elif action == "key":
                vm.inject_key()
            elif action == "unkey":
                vm.remove_key()
            elif action == "import":
                vm.import_repo(args.source, replace=args.replace)
            elif action == "export":
                vm.export_output(args.archive)
            elif action == "skills":
                vm.install_skills(args.source, replace=args.replace)
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
