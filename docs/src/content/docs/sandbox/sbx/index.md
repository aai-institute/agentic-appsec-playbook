---
title: "AppSec shell (Docker sbx)"
description: "Operate the appsec-sbx wrapper on your own machine, from create to export and stop."
---

The AppSec shell is a Docker Sandboxes (`sbx`) microVM with one agent harness, one model
provider and a copy of your repository inside. The `appsec-sbx` wrapper owns its lifecycle
from the host: it provisions the VM, restricts its network policy to the provider profile and
selected registries, imports tracked source files, installs the review prompt, places the key,
and exports results as an opaque archive. It checks for unwanted host shares and published
ports on entry. DNS isolation and allowed hostnames resolving to private addresses remain
[validation gaps](/sandbox/threat-model/controls/).

It implements the [no-regret measures](/sandbox/no-regret-measures/) on sbx. The reasoning
behind each decision, with the incidents and probes that shaped it, is in the maintainers'
[design notes](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/design/sbx-internals.md);
what was verified on which host is in the
[acceptance record](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/records/sbx-acceptance.md).

## Before the first run

Follow [Getting started](/getting-started/) once per host: install sbx, initialise its global
policy with `deny-all`, disable SSH agent forwarding, install the wrapper, clone this
repository for the review skill. This page assumes `appsec-sbx` is on your `PATH`; from a
checkout, `./sandbox/make-appsec-sbx.sh` takes the same arguments.

Supported hosts: macOS on Apple silicon, Windows 11 x64 and Linux x86_64, each with a working
`sbx` installation. On other hosts the wrapper prints an untested-host note and continues.
Platform specifics are at the [end of this page](#platform-notes).

## The daily loop

```sh
appsec-sbx create appsec-sbx --provider openrouter   # once per VM; picks harness and allowlist
appsec-sbx verify appsec-sbx                         # entry guards and guest versions
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
appsec-sbx key appsec-sbx                            # prompts for the key, places it in guest tmpfs
appsec-sbx shell appsec-sbx                          # enters as the workload user
```

`key` and `shell` are separate actions; `shell --key appsec-sbx` does both in one step, and is
the form to use in practice because the key does not survive an idle stop of the VM (below).
`unkey` removes the key again.

Inside the shell you are the unprivileged `appsec` user in `~/target/source`. Start the
harness (`opencode`, `claude` or `codex`, depending on the provider) and ask for the
`security-review-repo` skill; it writes its report to `~/out/findings.md`. Then, from the
host:

```sh
appsec-sbx export appsec-sbx ./findings-$(date +%F).tar.gz   # opaque archive of ~/out
appsec-sbx stop appsec-sbx                                   # kill switch: stop execution
```

Open the archive as untrusted output, on the host, with a tool that does not execute anything
(`tar -tzf` first, then extract into an empty directory). Triage the report with the
[triage rubric](/triage/triage-rubric/).

For subscription logins, run `unkey` before the final `stop` to remove known
login files explicitly. `stop` alone skips cleanup on an already-stopped VM
and ignores cleanup errors. Provider revocation remains separate; see
[VM lifetime](/sandbox/sbx/lifetime/).

**The VM stops itself about a minute after your last session ends, and the key goes with it.**
Place the key as part of entering (`shell --key`), never as a separate step. See
[VM lifetime](/sandbox/sbx/lifetime/).

## On these pages

- [Providers and credentials](/sandbox/sbx/providers/): the `create` presets, API keys,
  Claude Code and Codex seats, what to expect in the policy log.
- [VM lifetime, reset and policy](/sandbox/sbx/lifetime/): the idle stop and what it does to
  credentials, reproducer VMs, `reset` and `destroy`, the global sbx policy the wrapper needs.
- [Skills](/sandbox/sbx/skills/): how the review prompt and third-party packs enter the guest.
- [Import, export and host state](/sandbox/sbx/import-export/): what goes in, what comes out,
  where the manifests live.
- [Command reference](/sandbox/sbx/commands/): every action with its options, generated from
  the wrapper's own help.

## Evidence after a run

- `appsec-sbx logs <vm>` prints the recent policy log: allowed and denied connections with
  timestamps. Denied bursts name what the harness or the agent tried to reach.
- `import.json` and `skills.json` beside host state record what went in, with SHA-256 per file.
- The export archive is the only thing that comes out.

Record the run with the [observations table](/triage/observations/): provider, model, wall
clock, spend, denied hosts, and what the report contained.

## Platform notes

- **macOS (Apple silicon):** nested gVisor does not work in the arm64 guest, which is why
  reproducers are separate VMs rather than containers. No user-visible difference.
- **Windows 11:** run the wrapper from a desktop session (Windows Terminal or PowerShell);
  `create`, `reset`, `repro-create` and `destroy` need the sbx daemon's credential access,
  which a desktop logon provides. Clone the target with `core.autocrlf=false` if you want the
  import hashes to match a Linux or macOS checkout. Windows console: pass guest commands as
  plain words, or `put` a script and `exec sh` it.
- **Linux:** sbx stores its login in the session keyring; expect unlock prompts on the desktop
  the first time the daemon starts. A locked keyring only produces warnings.
