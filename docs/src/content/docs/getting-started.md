---
title: Getting started
description: From an empty machine to a first contained security review of your own repository.
---

You need about an hour the first time: most of it is installing Docker Sandboxes and letting
the sandbox VM bootstrap. Later runs take a few minutes of setup.

## 1. Read the baseline

The [no-regret measures](/sandbox/no-regret-measures/) are six things that must hold before the
first agent run: an isolated VM, default-deny egress, a capped credential, explicit file
transfer, a kill switch, and a reset discipline. The AppSec shell below implements all six;
read the page once so you know what the wrapper is doing on your behalf and what it does not
cover (the model provider still sees your code).

## 2. Install Docker Sandboxes

The AppSec shell runs on Docker Sandboxes, the `sbx` CLI. Install it for your platform from
the [Docker Sandboxes documentation](https://docs.docker.com/ai/sandboxes/) and log in. Docker
Desktop is not required. Tested versions and hosts: sbx `0.42.1` on macOS (Apple silicon),
Windows 11 x64 and Linux x86_64.

One-time host settings, in this order:

```sh
sbx login
sbx policy init deny-all                              # fresh installation only; see the note
sbx settings set ssh.agentForwardingEnabled false     # global; the wrapper checks it
sbx daemon restart                                    # picks up the setting
sbx diagnose
```

`sbx policy init` is one-time. On an installation that already has a policy, `sbx policy
reset` deletes the local policy store, stops running sandboxes and asks which preset to
initialise; choose `deny-all`. The wrapper adds its own scoped rules for downloads and the model
endpoint, so `deny-all` is sufficient and the better choice for a pilot machine.

Windows: run everything below from a desktop session (Windows Terminal or PowerShell). Linux:
expect keyring unlock prompts on the desktop when the daemon first starts.

## 3. Install the wrapper

The wrapper is a Python package with no dependencies. With [uv](https://docs.astral.sh/uv/):

```sh
uv tool install 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx'
appsec-sbx --version
```

Or run it without installing, prefixing every command with
`uvx --from 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx' appsec-sbx`.
From a checkout of this repository, `./sandbox/make-appsec-sbx.sh` (macOS, Linux) or
`python -m appsec_sbx` run from `sandbox/sbx` (any OS) take the same arguments.

## 4. Clone this repository

The review prompt is a skill in this repository and is installed into the VM from a Git
checkout, so clone it once:

```sh
git clone https://github.com/aai-institute/agentic-appsec-playbook.git
```

## 5. Get a model credential

Pick a provider from the [providers table](/sandbox/sbx/providers/) and
get one credential for it: an OpenRouter, Anthropic or DeepSeek API key with a spend cap set at
the provider, a Claude subscription seat, or a ChatGPT seat. The default is OpenRouter. Keep the
key in your password manager; you will paste it into a prompt, never into a command line.

## 6. First run

From any directory, with your repository checked out somewhere on the host:

```sh
appsec-sbx create appsec-sbx --provider openrouter
appsec-sbx verify appsec-sbx
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
appsec-sbx shell --key appsec-sbx      # paste the key at the prompt; you are now inside the VM
```

`create` takes two to four minutes (bootstrap, then a template snapshot). Inside the VM:

```sh
cd ~/target/source
opencode
# pick a model, then ask: "Use the security-review-repo skill to review this repository."
```

The skill writes its report to `~/out/findings.md`. Leave the harness, exit the shell, and
from the host:

```sh
appsec-sbx export appsec-sbx ./findings.tar.gz
appsec-sbx stop appsec-sbx
```

`stop` is the kill switch: it removes the key, stops the VM and any reproducer. Extract the
archive into an empty directory and read the report as untrusted text.

## 7. Triage, record, repeat

- Triage the report with the [triage rubric](/triage/triage-rubric/): time-capped, severity
  first, one verdict per finding.
- Record the run in the [observations table](/triage/observations/): model, wall clock, spend,
  denied hosts from `appsec-sbx logs appsec-sbx`, findings by verdict.
- For the next run on the same VM, `import --replace` swaps the target; `reset` returns to the
  clean template when you want a clean slate (reinstall skills afterwards).

## Where to go next

- The [AppSec shell page](/sandbox/sbx/) covers providers and seats, the VM's idle stop
  and what it does to credentials, skills from third parties, reproducer VMs and reset.
- The [tool shortlist](/tools/shortlist/) compares harnesses and prompts for discovery, triage
  and remediation.
- The [validation loop](/validation/validation-loop-template/) turns a triaged finding into a
  proof, a fix and a regression test.
- The [hardening checklist](/hardening/hardening-checklist/) is what has to be true before the
  loop runs in CI without someone watching.
