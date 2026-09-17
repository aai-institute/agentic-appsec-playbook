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
as well. You set the spend cap at the provider and test the kill switch,
including credential revocation, before launching the agent. Both happen in
the steps below.

Read [the full page](/sandbox/no-regret-measures/) once so you know what the
wrapper does on your behalf, and what it leaves open. The largest gap is that
your model provider still sees your code.

## 2. Install Docker Sandboxes

`appsec-sbx` uses Docker Sandboxes, the `sbx` CLI. Install it for your
platform from the [Docker Sandboxes
documentation](https://docs.docker.com/ai/sandboxes/install/) and log in. Docker
Desktop is not required. Tested versions and hosts: sbx `0.42.1` and `0.43.0` on
macOS (Apple silicon), Windows 11 x64 and Linux x86_64.

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

Install Git on the host and check that `git --version` works in your terminal.
On Windows, use Git for Windows with Git available on `PATH`. The wrapper
checks Git before importing a repository or installing skills.

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

## 4. Get a model credential

Pick a provider from the [providers table](/sandbox/sbx/providers/) and get one
credential for it. The choices are an OpenRouter, Anthropic or DeepSeek API
key, a Claude subscription seat, or a ChatGPT seat. The default is OpenRouter.

For an API key, set a provider spend cap or use a fixed prepaid balance before
the run. For a subscription seat, set an elapsed-time or usage abort threshold
and monitor it. That is measure 5, and no wrapper can set it for you.

Keep the key in your password manager. You paste it into a prompt, never into
a command line.

## 5. First run

The example below uses OpenRouter with an API key and OpenCode. For another
provider or a subscription login, use the matching steps in
[Providers and credentials](/sandbox/sbx/providers/).

Run these commands on the host, from any directory, with your target
repository checked out. The review skill is fetched directly from GitHub;
you do not need a local playbook clone. `create` is needed only once per VM:

For a public GitHub target, the `import` source can also be a repository URL,
with optional `--ref <branch, tag or commit>` (default: `main`). See
[Import and export](/sandbox/sbx/import-export/).

```sh
appsec-sbx create appsec-sbx --provider openrouter
appsec-sbx verify appsec-sbx
```

`create` takes two to four minutes, first the bootstrap and then a template
snapshot. If this VM has already been used for a review, follow
[Starting another review](#starting-another-review) instead of running `create`.

### Test the kill switch

Before importing code or launching an agent, complete the
[kill-switch rehearsal](/sandbox/sbx/lifetime/#test-the-kill-switch).
It uses a harmless running command to test stopping the VM from a second
terminal, then covers provider-side credential revocation and a clean reset.
Record the results. Use a fresh capped key or a new login for the review.

### Import and review

After the rehearsal, the VM is clean and ready for these host commands:

```sh
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
appsec-sbx skills appsec-sbx https://github.com/aai-institute/agentic-appsec-playbook --subdir sandbox/skills
appsec-sbx shell --key appsec-sbx      # paste the key at the prompt; you are now inside the VM
```

`skills` fetches `main` into a temporary host checkout and records the resolved
commit in `skills.json`. For repeatable runs, add `--ref <commit>`; see
[Skills](/sandbox/sbx/skills/#full-repo-review-skill).

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

`stop` is the kill switch: it stops the VM and its reproducers and attempts
credential cleanup while the VM is running. This ends the review; the
rehearsal above must already be complete before the agent starts.
For subscription logins, run `appsec-sbx unkey appsec-sbx` before `stop` to
remove known login files explicitly. Revoke or rotate credentials at the
provider separately; see
[credential cleanup limits](/sandbox/sbx/lifetime/#idle-stop-sessions-and-credentials).

Choose a new archive filename for each run; export refuses to overwrite an
existing file. The `.zip` suffix selects ZIP, which you can inspect and
extract with File Explorer on Windows. Extract into a new, empty directory
and read the report as untrusted text. For a gzip-compressed tar archive,
use `.tar.gz` instead; see [export formats](/sandbox/sbx/import-export/#export).

## 6. Record the run

- Use the [discovery run report](/exercises/first-discovery-pass/#part-4-write-the-run-report)
  to record the model, runtime, spend and raw findings. Include denied hosts
  from `appsec-sbx logs appsec-sbx` and any setup failures.
- Keep the raw export for later triage. A triage exercise will be added later.

## Starting another review

Reset before each independent review, including a repeat pass on the same
repository or a comparison with another model or prompt. Export any results
you need, stop the run and revoke its credential, then run on the host:

```sh
appsec-sbx reset appsec-sbx
appsec-sbx verify appsec-sbx
```

Reset deletes the target, output, installed skills, harness state and login
stores, and removes associated reproducer VMs. Repeat
[Import and review](#import-and-review), reinstalling the skills and supplying
a fresh credential with a budget. If you need a different provider or
harness, create a new VM with that configuration.

Resuming an interrupted review of the same target can keep its existing
state. `import --replace` only replaces the target files; it leaves other
state in place and does not satisfy the reset requirement for a new review.
See [VM lifetime](/sandbox/sbx/lifetime/#reproducers-reset-and-destroy).

## Where to go next

- The [appsec-sbx user guide](/sandbox/sbx/) covers providers and seats, the VM's
  idle stop and what it does to credentials, skills from third parties,
  reproducer VMs and reset.
- The [tool shortlist](/tools/shortlist/) compares harnesses and prompts for
  discovery, triage and remediation.
- [Choosing a model](/tools/choosing-a-model/) covers privacy, hosting,
  monitoring, cyber benchmarks and cost.
