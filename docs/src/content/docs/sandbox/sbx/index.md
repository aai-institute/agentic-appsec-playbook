---
title: "appsec-sbx: run agents in a sandbox"
description: "Operate the appsec-sbx wrapper on your own machine, from create to export and stop."
---

`appsec-sbx` manages a Docker Sandboxes (`sbx`) microVM with one agent harness, one model
provider and a copy of your repository inside. The wrapper owns the VM's lifecycle
from your machine: it provisions the VM, restricts its network policy to the provider profile and
selected registries, imports tracked source files, installs the review prompt, places the key,
and exports results as an opaque archive. It checks for unwanted host shares and published
ports on entry. DNS isolation and allowed hostnames resolving to private addresses remain
[validation gaps](/sandbox/threat-model/controls/).

It supports the [no-regret measures](/sandbox/no-regret-measures/) on sbx.
You remain responsible for checking source for secrets, approving provider
access, managing credentials and budgets, testing the kill switch and
resetting between independent reviews. Allowed services can still receive
data the agent can read; see the [remaining risks](/sandbox/threat-model/#accepted-risks).

## Before the first run

Complete [Getting started, steps 2–4](/getting-started/#2-install-docker-sandboxes)
once per host: install and log in to sbx, initialise a fresh global policy with
`deny-all`, disable SSH agent forwarding, restart the daemon and run its
diagnostics. Then install the wrapper and prepare a model credential with a
budget. The review skill is fetched directly from GitHub during the run setup.

The commands below assume `appsec-sbx` is on your `PATH`. See
[Install the wrapper](/getting-started/#3-install-the-wrapper) for the `uv`
installation command and checkout-based alternatives on each platform.

Supported hosts: macOS on Apple silicon, Windows 11 x64 and Linux x86_64, each with a working
`sbx` installation. On other hosts the wrapper prints an untested-host note and continues.
Platform specifics are at the [end of this page](#platform-notes).

## Run a review

This is the same OpenRouter API-key workflow as
[Getting started](/getting-started/#5-first-run). For another provider or a
subscription login, follow [Providers and credentials](/sandbox/sbx/providers/).
Run these commands on the host for a new VM. For an existing VM, follow
[Starting another review](/getting-started/#starting-another-review).

The `import` source can also be a public GitHub repository URL, with optional
`--ref <branch, tag or commit>` (default: `main`). See
[Import and export](/sandbox/sbx/import-export/).

```sh
appsec-sbx create appsec-sbx --provider openrouter
appsec-sbx verify appsec-sbx
```

Before importing code or starting an agent, complete the
[kill-switch rehearsal](/sandbox/sbx/lifetime/#test-the-kill-switch).
It tests stopping a running command, revoking the credential at the provider
and restoring the clean VM. Then continue on the host:

```sh
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
appsec-sbx skills appsec-sbx https://github.com/aai-institute/agentic-appsec-playbook --subdir sandbox/skills
appsec-sbx shell --key appsec-sbx      # paste the key at the prompt; you are now inside the VM
```

`skills` fetches `main` into a temporary host checkout. Add `--ref <commit>`
to repeat a reviewed revision; see [Skills](/sandbox/sbx/skills/#full-repo-review-skill).

`shell --key` places the API key and enters in one step. The VM stops itself
about a minute after the last session ends, which clears the key from tmpfs.
Use `shell --key` again when you return to the same review.

Inside the VM you are the unprivileged `appsec` user. Start OpenCode:

```sh
cd ~/target/source
opencode
# pick a model, then ask: "Use the security-review-repo skill to review this repository."
```

The skill writes its report to `~/out/findings.md`. Leave the harness, exit the
shell, and from the host:

```sh
appsec-sbx export appsec-sbx ./findings.zip
appsec-sbx stop appsec-sbx
```

Choose a new archive filename for each run; export refuses to overwrite an
existing file. Use `.zip` for ZIP or `.tar.gz` for gzip-compressed tar.
On Windows, inspect the ZIP with File Explorer and extract into a new, empty
directory. Read the report as untrusted text and keep it for later triage;
findings still need human review before you act on them. See
[export formats](/sandbox/sbx/import-export/#export).

`stop` is the kill switch: it stops the VM and its reproducers and attempts
credential cleanup while the VM is running. For subscription logins, run
`appsec-sbx unkey appsec-sbx` before `stop` to remove known login files
explicitly. Revoke or rotate credentials at the provider separately; see
[credential cleanup limits](/sandbox/sbx/lifetime/#idle-stop-sessions-and-credentials).

Reset before every independent review, including another pass on the same
target. Export first, stop and revoke the old credential, then run `reset`
and `verify`, import the target and reinstall the skills. Supply a fresh
credential with a budget. `import --replace` only swaps source files and
retains other state. See
[reset and reproducers](/sandbox/sbx/lifetime/#reproducers-reset-and-destroy)
for the distinction between resuming a review and starting a new one.

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

Record the run with the [discovery run report](/exercises/first-discovery-pass/#part-4-write-the-run-report):
provider, model, runtime, spend, denied hosts and what the report contained.

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
