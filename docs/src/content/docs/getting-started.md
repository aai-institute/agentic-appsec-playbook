---
title: Getting started
description: From an empty machine to a first contained security review of your own repository.
---

The [baseline](/sandbox/no-regret-measures/) says what has to hold before an
agent runs on your code. This page builds that environment and takes it
through one review.

You need about an hour the first time. Most of it is installing Docker
Sandboxes and waiting for the sandbox VM to bootstrap. Later runs take a few
minutes of setup.

## 1. Read the baseline

Six measures have to be in place before the first agent run:

1. A dedicated, disposable VM.
2. No production credentials in reach.
3. Egress default-deny.
4. Short-lived, unshared credentials.
5. A budget set before the run.
6. A kill switch, tested.

`appsec-sbx` implements all six. Two of them need something from you
as well. You set the spend cap at the provider, and the kill switch counts as
tested once you have run it yourself. Both happen in the steps below.

Read [the full page](/sandbox/no-regret-measures/) once so you know what the
wrapper does on your behalf, and what it leaves open. The largest gap is that
your model provider still sees your code.

## 2. Install Docker Sandboxes

`appsec-sbx` uses Docker Sandboxes, the `sbx` CLI. Install it for your
platform from the [Docker Sandboxes
documentation](https://docs.docker.com/ai/sandboxes/) and log in. Docker
Desktop is not required. Tested versions and hosts: sbx `0.42.1` on macOS
(Apple silicon), Windows 11 x64 and Linux x86_64.

One-time host settings, in this order:

```sh
sbx login
sbx policy init deny-all                              # fresh installation only; see the note
sbx settings set ssh.agentForwardingEnabled false     # global; the wrapper checks it
sbx daemon restart                                    # picks up the setting
sbx diagnose
```

`sbx policy init` is one-time. On an installation that already has a policy,
`sbx policy reset` deletes the local policy store, stops running sandboxes and
asks which preset to initialise. Choose `deny-all`. The wrapper adds its own
scoped rules for downloads and the model endpoint, so `deny-all` is sufficient
and the better choice for a pilot machine.

Platform notes:

- **Windows.** Run everything below from a desktop session, either Windows
  Terminal or PowerShell.
- **Linux.** Expect keyring unlock prompts on the desktop when the daemon
  first starts.

## 3. Install the wrapper

The wrapper is a Python package with no dependencies. With
[uv](https://docs.astral.sh/uv/):

```sh
uv tool install 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx'
appsec-sbx --version
```

To run it without installing, prefix every command with
`uvx --from 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx' appsec-sbx`.
From a checkout of this repository, run `uv run appsec-sbx` from `sandbox/sbx`
with the same arguments. The alternatives are `./sandbox/make-appsec-sbx.sh`
(macOS, Linux, from the repo root) or `python -m appsec_sbx` (from `sandbox/sbx`).

## 4. Clone this repository

The review prompt is a skill in this repository and is installed into the VM
from a Git checkout, so clone it once:

```sh
git clone https://github.com/aai-institute/agentic-appsec-playbook.git
```

## 5. Get a model credential

Pick a provider from the [providers table](/sandbox/sbx/providers/) and get one
credential for it. The choices are an OpenRouter, Anthropic or DeepSeek API
key, a Claude subscription seat, or a ChatGPT seat. The default is OpenRouter.

Set the spend cap at the provider now, before the key exists on your machine.
That is measure 5, and no wrapper can set it for you.

Keep the key in your password manager. You paste it into a prompt, never into
a command line.

## 6. First run

From any directory, with your repository checked out somewhere on the host:

```sh
appsec-sbx create appsec-sbx --provider openrouter
appsec-sbx verify appsec-sbx
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
appsec-sbx shell --key appsec-sbx      # paste the key at the prompt; you are now inside the VM
```

`create` takes two to four minutes, first the bootstrap and then a template
snapshot. Inside the VM:

```sh
cd ~/target/source
opencode
# pick a model, then ask: "Use the security-review-repo skill to review this repository."
```

The skill writes its report to `~/out/findings.md`. Leave the harness, exit the
shell, and from the host:

```sh
appsec-sbx export appsec-sbx ./findings.tar.gz
appsec-sbx stop appsec-sbx
```

`stop` is the kill switch. It removes the key, stops the VM and stops any
reproducer. Running it here is what makes measure 6 tested rather than
assumed.

Extract the archive into an empty directory and read the report as untrusted
text.

## 7. Triage, record, repeat

- Triage the report with the [triage rubric](/triage/triage-rubric/):
  time-capped, severity first, one verdict per finding.
- Record the run in the [observations table](/triage/observations/): model,
  wall clock, spend, denied hosts from `appsec-sbx logs appsec-sbx`, findings
  by verdict.
- For the next run on the same VM, `import --replace` swaps the target. Use
  `reset` to return to the clean template when you want a clean slate, and
  reinstall the skills afterwards.

## Where to go next

- The [appsec-sbx user guide](/sandbox/sbx/) covers providers and seats, the VM's
  idle stop and what it does to credentials, skills from third parties,
  reproducer VMs and reset.
- The [tool shortlist](/tools/shortlist/) compares harnesses and prompts for
  discovery, triage and remediation.
- [Choosing a model](/tools/choosing-a-model/) covers privacy, hosting,
  monitoring, cyber benchmarks and cost.
- The [validation loop](/validation/validation-loop-template/) turns a triaged
  finding into a proof, a fix and a regression test.
- The [hardening checklist](/hardening/hardening-checklist/) is what has to be
  true before the loop runs in CI without someone watching.
