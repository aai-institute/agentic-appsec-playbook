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

```sh
appsec-sbx create appsec-sbx --provider openrouter
appsec-sbx verify appsec-sbx
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
appsec-sbx skills appsec-sbx https://github.com/aai-institute/agentic-appsec-playbook --subdir sandbox/skills
appsec-sbx shell --key appsec-sbx      # paste the key at the prompt; you are now inside the VM
```

`skills` fetches `main` into a temporary host checkout and records the resolved
commit in `skills.json`. For repeatable runs, add `--ref <commit>`; see
[Skills](/sandbox/sbx/skills/#full-repo-review-skill).

`create` takes two to four minutes, first the bootstrap and then a template
snapshot. `shell --key` places the API key and enters in one step. The VM stops
itself about a minute after the last session ends, which clears the key from
tmpfs. Use `shell --key` again when you return.

Inside the VM you are the unprivileged `appsec` user. Start OpenCode:

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

`stop` is the kill switch: it stops the VM and its reproducers and attempts
credential cleanup while the VM is running. Running it here tests measure 6.
For subscription logins, run `appsec-sbx unkey appsec-sbx` before `stop` to
remove known login files explicitly. Revoke or rotate credentials at the
provider separately; see
[credential cleanup limits](/sandbox/sbx/lifetime/#idle-stop-sessions-and-credentials).

Choose a new archive filename for each run; export refuses to overwrite an
existing file. Inspect it with `tar -tzf`, then extract into an empty directory
and read the report as untrusted text.

## 6. Record the run

- Use the [discovery run report](/exercises/first-discovery-pass/#part-4-write-the-run-report)
  to record the model, runtime, spend and raw findings. Include denied hosts
  from `appsec-sbx logs appsec-sbx` and any setup failures.
- Keep the raw export for later triage. The triage exercise will follow in a
  later working-group session.
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
