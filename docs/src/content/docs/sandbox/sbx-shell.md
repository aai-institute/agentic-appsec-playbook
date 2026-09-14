---
title: AppSec shell (Docker sbx)
description: Operate the appsec-sbx wrapper on your own machine, from create to export and stop.
---

The AppSec shell is a Docker Sandboxes (`sbx`) microVM with one agent harness, one model
provider and a copy of your repository inside. The `appsec-sbx` wrapper owns its lifecycle
from the host: it provisions the VM, locks its network policy to one model endpoint plus one
package registry, imports tracked source files, installs the review prompt, places the key,
and exports results as an opaque archive. Nothing in the guest can reach your host files,
your other sandboxes or the LAN.

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
appsec-sbx shell --key appsec-sbx                    # prompts for the key, then enters
```

Inside the shell you are the unprivileged `appsec` user in `~/target/source`. Start the
harness (`opencode`, `claude` or `codex`, depending on the provider) and ask for the
`security-review-repo` skill; it writes its report to `~/out/findings.md`. Then, from the
host:

```sh
appsec-sbx export appsec-sbx ./findings-$(date +%F).tar.gz   # opaque archive of ~/out
appsec-sbx stop appsec-sbx                                   # kill switch: key removed, VM stopped
```

Open the archive as untrusted output, on the host, with a tool that does not execute anything
(`tar -tzf` first, then extract into an empty directory). Triage the report with the
[triage rubric](/triage/triage-rubric/).

**The VM stops itself about a minute after your last session ends, and the key goes with it.**
Place the key as part of entering (`shell --key`), never as a separate step. See
[VM lifetime](#vm-lifetime-idle-stop-sessions-and-credentials).

## Providers and harnesses

Exactly one model provider per VM. The provider decides the workload allowlist, the key
variable and, unless `--harness` says otherwise, the installed harness: `claude-code` installs
Claude Code, `codex` installs the Codex CLI, every other provider installs OpenCode. Changing
the provider means a new VM (`destroy`, then `create`).

| `create` option | Allowlist (plus the registry) | Credential | Harness |
|---|---|---|---|
| `--provider openrouter` (default) | `openrouter.ai:443` | `OPENROUTER_API_KEY` via `shell --key` | OpenCode |
| `--provider anthropic` | `api.anthropic.com:443` | `ANTHROPIC_API_KEY` via `shell --key` | OpenCode |
| `--provider deepseek` | `api.deepseek.com:443` | `DEEPSEEK_API_KEY` via `shell --key` | OpenCode |
| `--provider claude-code` | `api.anthropic.com:443`, `platform.claude.com:443` | browser login from the guest (`/login`), or `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code |
| `--provider codex` | `api.openai.com:443`, `auth.openai.com:443`, `chatgpt.com:443` | `OPENAI_API_KEY` via `shell --key`, or `codex login --device-auth` in the guest | Codex CLI |
| `--endpoint HOST:PORT --key-var NAME` | that one exact endpoint | `NAME` via `shell --key` | OpenCode |

Wildcards are refused. `--registry` is repeatable and takes `npm`, `pypi` or an exact
`HOST:PORT` such as an organisation mirror; `--no-registry` allows none. Pick the registry the
*target* needs if the agent is meant to install its dependencies: a Python target under an
npm-only profile will show dozens of denied PyPI connections in the log and no installed
dependencies. A discovery-only prompt is not a control; the allowlist is.

### API key (OpenRouter, Anthropic, DeepSeek, custom endpoint)

`shell --key` (also `agent --key`, `exec --key`) prompts for the key without echo, or takes
it from the environment variable of the same name, writes it to a tmpfs file the workload can read but not modify, and enters. `key` alone does the same
without entering, and `unkey` removes the file. The workload can read its key; the budget is
whatever cap the key carries at the provider.

### Claude Code on a subscription seat

```sh
appsec-sbx create appsec-sbx --provider claude-code
appsec-sbx verify appsec-sbx
appsec-sbx import appsec-sbx /absolute/path/to/git-repository
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
appsec-sbx shell appsec-sbx
# Inside:
cd ~/target/source && claude
# /login -> "Claude account with subscription": open the printed URL in a browser on
# the HOST, paste the one-time code back. Then /model, and /security-review-repo.
# The built-in /security-review is diff-scoped and has nothing to review here.
```

The browser login is the intended path: the pasted code is single-use and the tokens land in
the agent's home for the life of the run; `stop` and `unkey` delete them. The alternative,
`shell --key` with a `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`, is a months-long
bearer token and was rejected by the API in the one trial so far. Either way the VM runs with
the whole seat's authority and the budget is the seat's rate limit, not a spend cap. A fresh VM
never has a credential: if `claude` does not ask you to log in, run `claude auth status`
before trusting it.

Expect these denials in the policy log at every Claude Code start, all harmless: a clone of
the plugin marketplace from GitHub, `downloads.claude.ai`, and a dozen attempts at
`mcp-proxy.anthropic.com`.

### Codex CLI on an API key or a ChatGPT seat

Both credential forms share the `codex` preset. API key: `shell --key` with
`OPENAI_API_KEY`. Seat: inside the workload shell run `codex login --device-auth`, open the
printed URL in a browser on the host and enter the code (device-code login must be enabled in
the ChatGPT account first). The credential lands in `~/.codex/auth.json` and is deleted by
`stop` and `unkey`. Invoke the review skill by typing `$security-review-repo` in the composer.

Codex keeps its own inner sandbox on top of the VM; the seeded configuration declares `~/out`
writable so the report write does not stop for approval, and turns account plugins off so the
VM makes no attempts to download plugin bundles. Expect denied GitHub attempts at startup
(update check, tip banner); they are harmless.

## VM lifetime: idle stop, sessions and credentials

sbx stops a local VM by itself about a minute after its last *session* ends, where a session
is an interactive shell or a running `exec`. Every wrapper action restarts a stopped VM
silently; a line `Sandbox <name> started successfully` in an action's output means the VM had
stopped in between.

| | sbx idle stop, or `sbx stop` | wrapper `stop` / `unkey` |
|---|---|---|
| Disk: installed tools, imported target, `~/out`, skills, harness state and databases | kept | kept; `reset` returns to the clean template, which keeps the tools and drops the target, `~/out`, installed skills, harness state and any login store (reinstall skills after a reset) |
| Tmpfs key file `/run/appsec/env` (`key`) | **gone** | removed |
| Harness login stores on the agent's home (`~/.claude/.credentials.json`, `~/.codex/auth.json`, OpenCode's `auth.json`) | **kept**: a seat's refresh token stays in the VM | removed |
| Reproducer VMs | untouched | stopped with the primary |
| Server-side validity of the key or seat | unchanged | unchanged; revocation is a separate action |

An idle stop is not the kill switch: it takes the API key with it by accident of tmpfs, leaves a
browser-login credential in place, and revokes nothing. `stop` and `unkey` are the actions
that clear the guest of credentials.

- **Interactive runs:** `shell --key` places the key and enters in one step. A `key` that is
  not followed at once by an entry evaporates. Every workload entry on a provider profile
  prints `NOTE: the guest holds no model credential ...` when the guest has neither the key
  file nor a harness login store.
- **Unattended runs** (`exec` of a harness command, a detached process started inside the
  guest): hold one session open for the duration, for example `appsec-sbx exec appsec-sbx --
  sleep 7200` in a second terminal, across `key`, the start and the run.
- **Seat-tier profiles** (Claude Code, Codex login): the login store survives idle stops, so a
  VM that went to sleep still authenticates as the seat when it wakes. End a working session
  with `stop`, not by walking away.
- **Reading records:** phase timings and policy-log timestamps are unaffected; the VM's
  `uptime` in `sbx inspect` restarts at every wake and says nothing about the run.

## Skills: how instructions enter the guest

The bootstrap installs no prompt content. Instructions enter through one action, `skills`,
which installs a skill pack from a host Git checkout: this repository's review prompt
([`sandbox/skills/security-review-repo`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/sandbox/skills/security-review-repo),
Anthropic's MIT `security-review` prompt with the diff scoping removed) and third-party packs
alike.

`skills <vm> <dir>` takes the checkout root or a directory inside it. Only the immediate
subdirectories that contain a `SKILL.md` go in; frameworks, install scripts, tests and READMEs
in the same checkout are skipped and counted, and the checkout's commit, a dirty flag and
per-file hashes are recorded beside host state in `skills.json`. Names already present are
refused unless `--replace`. The destination is the selected harness's user-level skills
directory:

| Harness | Skills directory in the guest | Invocation |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` | `/<name> [focus]` |
| Codex | `~/.codex/skills/<name>/SKILL.md` | `$<name>` in the composer |
| OpenCode | `~/.config/opencode/skills/<name>/SKILL.md` | model-invoked through its `skill` tool: ask for the skill by name; no slash command |

Third-party example, Google's Mantis review pipeline (its own `npx skills add` installer
needs GitHub, which the run allowlist denies on purpose):

```sh
git clone https://github.com/google/mantis /path/to/mantis   # on the host; pin a commit
appsec-sbx skills appsec-sbx /path/to/mantis                  # 19 text-only skills
```

Mantis's reproduce and patch stages expect Docker inside the agent's own environment, which
this guest does not provide; run the text-only stages and say so in the run record. Mantis
writes working files into the target tree, so a second run on the same VM needs
`import --replace`.

`put <vm> <host-file> /home/appsec/<path>` copies one further host file to a new path; it
refuses traversal, directories and existing targets.

## Import and export

Import copies **tracked working-tree contents**, including edits, without Git metadata.
Untracked files, `.env*`, common credential files, `.sbxenv.yaml` and agent/editor
configuration directories are excluded. Symlinks (including parent components), hardlinks,
special files and traversal paths are rejected; limits are 64 MiB per file and 512 MiB total.
Submodules need a separate, explicit import. Target instructions and source remain untrusted
after import.

Imports create `~/target/source` once; `import --replace` swaps the target tree in place
(harness state, `~/out` and the key stay). A Git worktree (`git worktree add /tmp/x <ref>`)
is the way to import a specific revision without touching your working checkout. The exclusion
list is not a secret scanner: check the manifest (`import.json` beside host state) if the
repository may carry credentials in tracked files.

Export produces an opaque tar.gz from `~/out` to a new host file and **never extracts it on
the host**. Inspect it as untrusted output.

Host state defaults to `~/.local/state/agentic-appsec/sbx/NAME` on every OS; set
`APPSEC_SBX_STATE` consistently to select another directory. It holds VM IDs, template
references, the admitted policy, the import manifest and the skills manifest, never keys. Do
not edit it to bypass a failed guard.

## Reproducers, reset and destroy

A reproducer is a second VM, created from the primary's clean template (tools installed,
nothing imported), with no network at all and no model key. Use it to run a proof of concept
the agent wrote without giving it the model or the internet.

```sh
appsec-sbx repro-create appsec-sbx appsec-sbx-repro
appsec-sbx import appsec-sbx-repro /absolute/path/to/git-repository
appsec-sbx shell appsec-sbx-repro
# Or a bounded command without an interactive shell:
appsec-sbx exec appsec-sbx-repro -- timeout 60 python3 /home/appsec/target/source/reproduce.py
appsec-sbx export appsec-sbx-repro ./reproducer-results.tar.gz

appsec-sbx stop appsec-sbx      # also stops the reproducers created through this primary
appsec-sbx reset appsec-sbx     # DELETES the primary's state and its reproducers, recreates from the clean template
appsec-sbx destroy appsec-sbx   # removes the primary and its reproducers entirely
```

`reset` is the clean slate between runs: it removes the target, `~/out`, installed skills,
harness state and login stores, and keeps the installed tools. Export first; reinstall skills
afterwards. sbx prints a warning that the template "was built for the `shell` agent" on
`reset` and `repro-create`; it is nominal, the restored VM passes `verify`.

## Global sbx policy

The wrapper adds sandbox-scoped rules and leaves your global policy and other sandboxes
alone. It needs a global policy it can narrow: initialise a fresh installation with
`sbx policy init deny-all` (Docker calls this preset Locked Down). `balanced` also works but
its `default-ai-services` rule overlaps the Codex preset, and `create` then refuses with the
rule's name; the fix is `sbx policy rm network --id default-ai-services`, which affects every
sandbox on the machine. An inherited `**` allow cannot be narrowed and is refused.

Any later edit to the global or scoped policy makes the next workload entry fail and stops the
affected VM family; `reset` recompiles the policy from the clean baseline.

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

## Command reference

```text
appsec-sbx ACTION [NAME] [options]

create        provision a clean workload VM with exactly one model provider
admin         root maintenance shell (outside the workload boundary)
key           place the provider key in guest tmpfs (stdin, never argv)
unkey         remove the key file
verify        run the entry guards and print guest versions
status        sbx inspect
logs          recent policy log
stop          kill switch: remove key, stop VM and its reproducers
reset         DELETE current state, recreate from the clean template
destroy       remove the VM and its reproducers
exec          run one command as the workload user
shell         interactive unprivileged workload shell
agent         alias of shell
import        filtered copy of a host Git checkout into ~/target/source
export        opaque tar.gz of ~/out to a new host file
skills        install the skills of a host Git checkout (top-level dirs
              with SKILL.md) into the harness's skills directory
put           copy one host file to a new path under /home/appsec
repro-create  offline reproducer VM from the primary's clean template
```

`appsec-sbx ACTION --help` lists the options of each action.
