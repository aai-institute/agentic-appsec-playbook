# AppSec shell with Docker sbx

This is the executable successor to the [Colima prototype](../reference-sandbox.md),
which stays frozen as the measured v0 reference. It installs the same Node/OpenCode
toolchain in a dedicated sbx VM, enters it as an unprivileged user, copies selected
source in, and exports results explicitly. The implementation is the Python package
[`appsec_sbx`](appsec_sbx/) (stdlib only, Python 3.9+): [cli.py](appsec_sbx/cli.py),
[lifecycle.py](appsec_sbx/lifecycle.py), [policy.py](appsec_sbx/policy.py),
[providers.py](appsec_sbx/providers.py), [transfer.py](appsec_sbx/transfer.py),
[hostos.py](appsec_sbx/hostos.py) and [sbxcli.py](appsec_sbx/sbxcli.py); the guest side is
[guest/bootstrap.sh](appsec_sbx/guest/bootstrap.sh) plus a small
[shell kit](appsec_sbx/kit/spec.yaml). [make-appsec-sbx.sh](../make-appsec-sbx.sh) is a
macOS/Linux shim around `python3 -m appsec_sbx`; `pyproject.toml` provides the
`appsec-sbx` entry point for `uv tool install` / `pipx install` (installation
itself `not-yet-tested`).

**Tested locally on 2026-09-09 (v0.1, single file) and 2026-09-10 (package,
existing VM):** Apple silicon, sbx **v0.42.1**, Ubuntu 26.04 guest, Node **24.20.0**,
npm **11.19.0**, OpenCode **1.18.29**. The host side is written to run on Linux and
Windows as well ([portability](#portability)). Windows 11 x64 has an
[acceptance record](#windows-11-x64-2026-09-14) since 2026-09-14; Linux has run `create`
only, and the wrapper says so on every entry there.

There is one material architecture change. Installed gVisor **20260831.0** failed
its hello-world smoke test in this sbx guest, both with its default platform and
with `--platform=ptrace`. The ARM guest reports a **16384-byte page size**; runsc
warns about a non-4K host and fails with a sandbox-start EOF. The page size is a
suspected compatibility factor, not an established diagnosis. The bootstrap
records the failure instead of silently substituting an ordinary nested container.
On the first Windows create (2026-09-14, **x86_64** guest, kernel 7.0.12, gVisor
**20260907.0**, Docker 29.7.2) the same probe **passed**: `verify` printed `available`
from `/etc/appsec/runsc-status`, so the arm64 guest is the only one where runsc is
known to fail, consistent with the page-size suspicion and still not a diagnosis.
Reproducer work uses a **separate sbx VM**, created and stopped by the host wrapper.

## Start from a host shell

Prerequisites: macOS, Python 3.9+, Git, and an authenticated, healthy local sbx
installation. Docker Desktop and Colima are not used by this workflow. The
following SSH setting is global and requires a daemon restart; arrange that
restart around any other active sandboxes. It was disabled on the development
machine during this trial. The wrapper checks the setting and actual socket.

```sh
sbx login
sbx settings set ssh.agentForwardingEnabled false
sbx daemon restart
sbx diagnose

# From this repository's root. No host workspace argument is passed to sbx.
# Exactly one model provider per VM (threat model M2); the default is OpenRouter.
./sandbox/make-appsec-sbx.sh create appsec-sbx --provider openrouter
./sandbox/make-appsec-sbx.sh verify appsec-sbx
./sandbox/make-appsec-sbx.sh skills appsec-sbx sandbox/skills   # the review prompt
./sandbox/make-appsec-sbx.sh shell --key appsec-sbx             # places OPENROUTER_API_KEY, then enters
```

**The VM stops itself about a minute after your last session ends, and the key goes with
it.** Place the key as part of entering (`shell --key`), not as a separate step; see
[VM lifetime](#vm-lifetime-idle-stop-sessions-and-credentials) for what survives a stop and
what does not.

The provider decides the workload allowlist and the key variable, and is recorded
in host state; changing it means a new VM (`destroy`, then `create`). Presets and
the assignment tiers they serve:

| `create` option | Allowlist (plus the registry) | Key variable | Assignment tier |
|---|---|---|---|
| `--provider openrouter` (default) | `openrouter.ai:443` | `OPENROUTER_API_KEY` | B via the WG OpenRouter key |
| `--provider anthropic` | `api.anthropic.com:443` | `ANTHROPIC_API_KEY` | A1, Claude API key |
| `--provider deepseek` | `api.deepseek.com:443` | `DEEPSEEK_API_KEY` | B, direct DeepSeek key |
| `--provider claude-code` | `api.anthropic.com:443`, `platform.claude.com:443` | `CLAUDE_CODE_OAUTH_TOKEN` | A2, Claude seat via Claude Code (see below) |
| `--provider codex` | `api.openai.com:443`, `auth.openai.com:443`, `chatgpt.com:443` | `OPENAI_API_KEY`, or `codex login --device-auth` in the guest | OpenAI models via the Codex CLI, API key or ChatGPT seat (outside the assignment's Claude tiers; seat path `checked` 2026-09-11, API-key path not yet) |
| `--endpoint HOST:PORT --key-var NAME` | that one exact endpoint | `NAME` | anything else (Z.ai, Zen, a gateway) |

**One harness per VM**, chosen from the provider unless `--harness` says otherwise:
`claude-code` installs Claude Code, `codex` installs the Codex CLI, every other provider
installs OpenCode. Only that harness, its whole-repository review prompt, its managed
configuration and its environment variables are placed in the guest (`/etc/appsec/harness.env`
holds the harness-specific variables; the login profile sources it). A `both` option
existed for a few hours on 2026-09-10 and was dropped to keep the in-guest surface to
what the run needs.

Wildcards are refused. `--registry` is repeatable and takes a name (`npm`, `pypi`,
the latter two hosts) or an exact `HOST:PORT` such as an organisation mirror;
`--no-registry` allows none. Pick the registry the
*target* needs if the agent is meant to install its dependencies: on 2026-09-10 a GLM-5.3 run on a Python target
tried `uv sync` and then `pip install --trusted-host ...` against PyPI, which the
npm-only profile denied 46 times. A discovery-only prompt is not a control; the
allowlist is.

**Tier A2, Claude Code on a subscription seat** (threat model M23). First exercised
2026-09-10 with Claude Code 2.1.267: authenticating made requests to
`platform.claude.com` and `api.anthropic.com` and nothing else, so the preset names
both hosts. The seat's Fable quota is reachable only from Claude Code, and
zero-data-retention organisations cannot use the API-key path at all.

```sh
./sandbox/make-appsec-sbx.sh create appsec-sbx --provider claude-code
./sandbox/make-appsec-sbx.sh verify appsec-sbx
./sandbox/make-appsec-sbx.sh import appsec-sbx /absolute/path/to/git-repository
./sandbox/make-appsec-sbx.sh skills appsec-sbx sandbox/skills
./sandbox/make-appsec-sbx.sh shell appsec-sbx
# Inside (Claude Code is installed and pinned by the bootstrap):
cd ~/target/source && claude
# /login -> "Claude account with subscription": open the printed URL in a browser on
# the HOST, paste the one-time code back. Then /model -> Claude Fable 5.1, and
# /security-review-repo (whole-repo variant, installed by `skills`). The built-in
# /security-review stays diff-scoped and has nothing to review here.
```

The browser login is the default credential path: the code you paste is single-use
and short-lived, and the token exchange goes to `platform.claude.com`, already in
the profile. The resulting access and refresh tokens live in
`~/.claude/.credentials.json` on the agent-writable home for the life of the run;
`stop` and `unkey` delete that file together with the tmpfs key. The alternative
is `key` with a `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` on the host,
which avoids the browser and suits headless use, but it is a months-long bearer token
that travels through a terminal and needs revoking afterwards, and on the 2026-09-10
trial it was **rejected with HTTP 401** by the API after `claude auth status` had
accepted it locally; the cause was not determined (`not-yet-working`). Either
way the VM runs with the whole seat's authority, and the budget is the seat's rate
limit, not a spend cap. Claude Code's first-start onboarding (theme, then the login-method
chooser) *is* the browser login, so the bootstrap does not pre-mark it complete. It
did on 2026-09-10 for a few hours, to serve the token path: the effect on a fresh VM
was a harness that skipped the account step and started in API-key mode by default,
with no key present, so it opened at its prompt and only the first request would have
failed. A fresh VM never has a credential; if `claude` does not
ask you to log in, run `claude auth status` before trusting it. The login profile sets `DISABLE_AUTOUPDATER`, `DISABLE_TELEMETRY`,
`DISABLE_ERROR_REPORTING` and `DISABLE_BUG_COMMAND`, deliberately not the blanket
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`: that variable also suppresses the
post-login fetch of the seat's additional model options from the API host, which is
how Fable 5.1 reaches `/model` (`additionalModelOptionsCache` in `~/.claude.json`). No
extra host is needed; a flag-CDN allow tried for one VM generation was never contacted
and was withdrawn (threat model M23). Count every safeguard intervention or redirect to an
Opus model for the run report. Expect these denials in the policy log at every start, all
harmless (checked 2026-09-10 with a process-level trace in the guest): a `git` clone
of `github.com/anthropics/claude-plugins-official` (the plugin marketplace
auto-install, with an SSH fallback to a GitHub address on port 22),
`downloads.claude.ai`, and a dozen attempts at `mcp-proxy.anthropic.com`; the harness
records the marketplace failure and retries hours later. Which models `/model` offers
is decided by the seat and by a post-login fetch from the API host: on 2026-09-10 the
same `team_tier_1` account saw Fable 5.1 on the host and not in a guest running with
the blanket nonessential-traffic variable; with the individual switches the guest
offered Fable and ran on it. The untested fallback when a picker hides a model is
typing it: `/model claude-fable-5-1`.

**Codex CLI** (`--provider codex`; seat path exercised end to end on 2026-09-11, API-key path not yet). The
bootstrap pins `@openai/codex@0.154.0` (no install scripts; the platform binary is an
optional dependency, Linux arm64 included) and seeds `~/.codex/config.toml` with
`check_for_update_on_startup = false`, `[analytics] enabled = false` and a trusted entry
for `~/target/source`; all three keys were read from the 0.154.0 binary, and its update
check targets the GitHub releases API, which the policy denies anyway. Both credential forms
share the one preset, since the extra hosts are the same vendor: an API key through
`key` (`OPENAI_API_KEY`, inference at `api.openai.com`), or a ChatGPT seat by running
`codex login --device-auth` inside the workload shell, opening the URL it prints in a
browser on the host and entering the code; the OAuth exchange goes to `auth.openai.com`
and inference on a ChatGPT plan to `chatgpt.com/backend-api`, both read from the binary.
The seat credential lands in `~/.codex/auth.json` on the agent-writable home and is
deleted by `stop` and `unkey`. The review prompt arrives through `skills` as
`~/.codex/skills/security-review-repo/SKILL.md` (the prompt asks the model to list the
files itself; there is no shell-injection block). Codex 0.154
has no custom-prompt directory any more; skills are what it discovers (checked in the
guest on 2026-09-11, where it had seeded `~/.codex/skills/.system/`). Invoke it by
typing `$security-review-repo` in the composer, optionally followed by a focus; there
is no slash command for it. Codex keeps its own inner sandbox on top of the VM
(workspace-write, network off for commands, approvals on request); the seeded config
declares `~/out` writable so the report does not end in an approval prompt. First run
on 2026-09-11 (ChatGPT seat, model `gpt-6-astra`): the harness first refused the
skill because it read the filter block's "do not use the bash tool" as a rule for the
whole review; the skill variant now scopes that block. Network during the run:
`chatgpt.com` and `auth.openai.com` only on the allowed side; on the denied side,
repeated attempts to `*.oaiusercontent.com` and one to `files.openai.com`. Codex's log
identifies them: `remote_installed_plugin_sync` downloading bundles for the plugins
installed on the ChatGPT account (a GitHub connector among them) from vendor storage,
retried through the run, and the curated-plugins `git` sync to GitHub. Account-level
plugin state flowing into the sandbox, blocked by the profile; with it allowed, the
harness would install those plugins into the guest unasked (T22/T28). A further denied host, `raw.githubusercontent.com` (six attempts within a second of each Codex start, seen 2026-09-11), is the binary's own fetch of `openai/codex/main/announcement_tip.toml`, the startup tip banner; the 0.154.0 string table shows no configuration key for it, so the allowlist is its only layer. Neither host was asked for by a skill: the Mantis skill texts contain no URLs. The seeded
config now turns the feature off (`[features] plugins = false`, the line
`codex features disable plugins` writes; verified in the guest), so a fresh VM makes
no such attempts. On a VM created before that, run `codex features disable plugins`
in the workload shell. If a participant genuinely needs an account plugin inside the
sandbox: the bundles come from regional `*.oaiusercontent.com` hosts named by the
server, which only a wildcard allow could admit, and the profile compiler refuses
wildcards by design; plugins therefore stay outside the sandbox, and the harness's
`plugin list` still shows the account inventory read-only through `chatgpt.com`. The device-code login had to be enabled in the ChatGPT
account settings first. Whether this version has a response-storage setting for
zero-data-retention organisations (the older `disable_response_storage` key is absent
from the binary) is still open.

## VM lifetime: idle stop, sessions and credentials

sbx v0.42.1 **stops a local VM by itself about a minute after its last session ends.**
Checked on macOS on 2026-09-14 with a throwaway sandbox (running to stopped between 21 and
82 s after its last `exec`), after the Windows run had hit it first: `key`, a shell that had
the key, a `skills` install some minutes later whose output began with
`Sandbox appsec-sbx started successfully`, then a shell without the key. The behaviour is
sbx's own: `sbx settings ls` has no knob for it and the Docker Sandboxes documentation
(overview, usage, architecture, troubleshooting) does not describe it. A *session* is what
`sbx inspect` counts under `sessions`: an interactive shell or a running `exec`. Whether a
background process inside the guest alone keeps the VM up is untested; hold a session open.

**Every wrapper action restarts a stopped VM silently.** `sbx exec` and `sbx cp` start a
stopped sandbox and print `Sandbox <name> started successfully`; against a running one they
print nothing. That line in an action's output therefore means the VM had stopped in between.

What a stop does and does not change:

| | sbx idle stop, or `sbx stop` | wrapper `stop` / `unkey` |
|---|---|---|
| Disk: installed tools, imported target, `~/out`, skills, harness state and databases | kept | kept; `reset` returns to the clean template, which keeps the tools and drops the target, `~/out`, installed skills, harness state and any login store (reinstall skills after a reset) |
| Tmpfs key file `/run/appsec/env` (`key`) | **gone** | removed |
| Harness login stores on the agent's home (`~/.claude/.credentials.json`, `~/.codex/auth.json`, OpenCode's `auth.json`) | **kept**: a seat's refresh token stays in the VM | removed |
| Reproducer VMs | untouched | stopped with the primary |
| Server-side validity of the key or seat | unchanged | unchanged; revocation is a separate action |

So an idle stop is **not** the kill switch: it takes the API key with it by accident of tmpfs,
leaves a browser-login credential in place, and revokes nothing. `stop` and `unkey` remain the
actions that clear the guest of credentials (threat model T25, M23).

Consequences for operating the wrapper:

- **Interactive runs:** `shell --key` (also `agent --key`, `exec --key`; for `exec` the flag
  precedes the sandbox name) places the key and enters in one step. A `key` that is not
  followed at once by an entry evaporates. Every workload entry on a provider profile prints
  `NOTE: the guest holds no model credential ...` when the guest has neither the key file nor
  a harness login store, instead of dropping into a keyless shell.
- **Unattended runs** (`exec` of a harness command, a detached process started inside the
  guest): hold one session open for the duration, for example `exec <vm> -- sleep 7200` in a
  second terminal, across `key`, the start and the run. The Windows record's review run was
  driven this way over SSH.
- **Seat-tier profiles** (Claude Code, Codex login): the login store survives idle stops, so a
  VM that "went to sleep" still authenticates as the seat when it wakes. End a working
  session with the wrapper's `stop`, not by walking away.
- **Reading records:** phase timings and policy-log timestamps are unaffected; the VM's
  `uptime` in `sbx inspect` restarts at every wake and says nothing about the run.

## Reproducer boundary and reset

`reset` and `repro-create` restore the clean template with `sbx create --template`; sbx then
warns that the template "was built for the `shell` agent but you are using `appsec-shell`".
The template is this wrapper's own snapshot of the `appsec-shell` kit on the `shell-docker`
image, and sbx infers the agent name from the image flavour, so the warning is nominal; the
restored VM passes `verify`. Seen on Windows 2026-09-14, expected everywhere.

```sh
# Starts from the clean tools template, not the primary VM's current filesystem.
./sandbox/make-appsec-sbx.sh repro-create appsec-sbx appsec-sbx-repro
./sandbox/make-appsec-sbx.sh import appsec-sbx-repro /absolute/path/to/git-repository
./sandbox/make-appsec-sbx.sh shell appsec-sbx-repro

# Or run a bounded command without an interactive shell:
./sandbox/make-appsec-sbx.sh exec appsec-sbx-repro -- timeout 60 python3 /home/appsec/target/source/reproduce.py

./sandbox/make-appsec-sbx.sh export appsec-sbx-repro ./reproducer-results.tar.gz
./sandbox/make-appsec-sbx.sh stop appsec-sbx

# DELETES the primary's current state and its recorded reproducer VMs.
# Export anything needed first. Recreates the primary from the clean template.
./sandbox/make-appsec-sbx.sh reset appsec-sbx

# Removes the primary and its recorded reproducer VMs entirely.
./sandbox/make-appsec-sbx.sh destroy appsec-sbx
```

The reproducer has scoped denies for `**`, IPv4 and IPv6 address space, no model
key, and the same absence of workspace/skills shares. `key` refuses this role.
Its execution boundary is a separate sbx VM; the primary workload has no sbx
management client or host socket. Host `admin` can use its private Docker daemon
and the preloaded hello-world/curl images for trusted setup. Neither a default
Docker container nor runsc (failing on the arm64 guest, probe passed on x86_64) is credited as an additional
working isolation boundary.

`stop PRIMARY` also stops reproducers created through that primary. Each can be
stopped independently. Reset a primary to clear the whole run; to replace one
reproducer, destroy it and call `repro-create` again. The wrapper records VM IDs
and refuses to operate on a different VM that happens to reuse a recorded name.

The only template save point is immediately after provisioning and policy
verification, **before source import or key injection**. Local sbx requires the
VM to be stopped for this snapshot. Reset recreates a VM, rather than treating
stop/start as rollback. Docker's data volume is separate from the root filesystem,
so the bootstrap embeds a `docker save` archive in the clean root filesystem and
reset/reproducer creation reloads it. This was tested through actual recreation.
Templates remain in sbx's local image store after VM destruction; the wrapper
does not remove potentially shared baselines.

## Admission and transfer contract

| Concern | What this implementation does | Limit |
|---|---|---|
| Host files / R1 | Creates without a workspace; passes `--no-share-skills`; checks mounts on entry | Generated `/etc/hosts` and `/etc/resolv.conf` are still virtiofs mounts. No hypervisor escape claim |
| Host services / R2 | No published ports; explicit localhost/host-service and direct-IP denies; checks port inventory | Allowed hostname resolution into private addresses is not proved safe |
| Egress / R3 | Workload allows `openrouter.ai:443` and `registry.npmjs.org:443`; subtracts inherited development grants with scoped denies | Allowed services remain exfiltration/spend channels. DNS confidentiality remains unresolved |
| Credentials / R4 | Tracked regular-file import, common secret/config exclusions, no SSH agent, tmpfs model key | Exclusions are not a secret scanner; the workload can read its model key |
| Workload privilege / R5 | Separate `appsec` user, no sudo/Docker, clean entry environment; empty host MCP inventory required | Root/admin, host CLI and local state are trusted. Guards run on entry, not continuously |
| Reproducers / R6 | Separate VM from clean baseline; network-deny policy and key prohibition | Different mechanism from Colima's gVisor layer; DNS caveat still applies |
| Lifecycle / R7 | ID ownership, stop including recorded reproducers, clean recreate, CPU/memory limits | No independent host watchdog, provider cap automation, or verified disk quota |
| Evidence / R8 | Host policy logs, import hash manifest, exclusive opaque archive export | No complete evidence bundle, output-content validation, or automatic safe extraction |

The custom shell kit inherits no built-in agent kit. sbx's default agent user has
administrative privileges, so the bootstrap creates a separate user. On this
installation, `sbx exec -u appsec` reported “user appsec not found” **with exit
status zero**. Numeric `-u 1001` selected GID 1001 (Docker), whereas the intended
AppSec group was GID 1002. Entry therefore uses guest root only to execute
`sudo -H -u appsec -- /usr/local/libexec/appsec-enter`; this drops groups and clears
the environment before Bash runs. Identity, sudo denial and Docker denial were
checked through that actual path.

The MCP gateway itself is generated by sbx even for this shell kit. No MCP servers
are registered in this profile, the wrapper rejects a nonempty global server
inventory, the administrative home is private, and the workload entry strips
gateway and other inherited credential variables. This is not a claim that the
gateway feature has been disabled at the daemon level.

The bootstrap installs **no prompt content**. Instructions enter the guest through one
action, `skills`, which installs a **skill pack** from a host Git checkout (threat model
T33, M14): this repository's review prompt and third-party packs alike. The review prompt
is [sandbox/skills/security-review-repo/SKILL.md](../skills/security-review-repo/SKILL.md),
adapted from Anthropic's MIT `security-review` with the diff scoping removed, one
Agent-Skills file for all three harnesses (no shell-injection block, so the model lists
the files itself; `allowed-tools` for Claude Code). Until 2026-09-11 `create` wrote a
per-harness command variant of it into the guest; the acceptance passes below used
those. `put` still copies one further host file to a new path under `/home/appsec/`;
it refuses traversal, directories and existing targets. Pasting long prompts through
a shell heredoc needs a quoted delimiter (`<<'EOF'`), or backticks in the prompt
are executed.

`skills <dir>` takes the checkout root or a directory inside it. Only the immediate
subdirectories that contain a `SKILL.md` go in; frameworks, install scripts, tests and
READMEs in the same checkout are skipped and counted, the import filter's exclusions
and readers apply, and the checkout's commit, a dirty flag for the pack directory and
per-file hashes are recorded beside host state in `skills.json`. Skill names follow
OpenCode's rule, the strictest of the three (lowercase, digits, single hyphens). Names
already present are refused unless `--replace`. The destination is the selected
harness's user-level skills directory:

| Harness | Skills directory in the guest | Invocation |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` | `/<name> [focus]`; commands and skills are one mechanism |
| Codex | `~/.codex/skills/<name>/SKILL.md` | `$<name>` in the composer |
| OpenCode | `~/.config/opencode/skills/<name>/SKILL.md` (`checked` 2026-09-11, OpenCode 1.18.29: `opencode debug skill` lists it at that path; it also reads `~/.claude/skills`) | model-invoked through its `skill` tool: ask for the skill by name; no slash command, and `$ARGUMENTS` stays literal text |

The motivating case is Google's Mantis review pipeline. Its published install,
`npx skills add google/mantis` inside the guest, downloads the `skills` CLI from the npm
registry and then fails at the GitHub fetch, which the run allowlist denies on purpose.
Instead:

```sh
git clone https://github.com/google/mantis /path/to/mantis   # on the host; pin a commit
./sandbox/make-appsec-sbx.sh skills appsec-sbx /path/to/mantis
```

The checkout's nineteen top-level `mantis-*` directories each hold a `SKILL.md` and
nothing but Markdown (tree at the 2026-09-03 head read through the GitHub API on
2026-09-11); the two further skills under `reference/skills/` are nested and stay out with
the rest of `reference/`, as does the top-level `schema.json`. Two of the stages,
`/mantis-reproduce` and `/mantis-patch`, expect Docker with the gVisor runtime inside the
agent's own environment; this guest does not provide that, so a first pass runs the
text-only stages (architecture, threat model, plan, research, dedupe, review, critic,
report) and says so in the run record. First Mantis pass 2026-09-11 on the Codex VM
(`checked`): the 19 skills from a pinned clone installed in one call, discovered by Codex
0.154 and invoked as `$mantis-*`; nine stages ran (index through critic, no report
stage); the pack made no network request of its own. Mantis writes its working files
into the target tree (`workspace/`, per-directory `mantis-summary.md`) and executes
helper scripts the model writes there, inside the harness's inner sandbox, so a second
run on the same VM needs `import --replace`. Run record:
`agentic-appsec-demo/runs/codex-mantis-sbx-01.md`.

The action itself was exercised on 2026-09-11 against a fresh Codex VM on macOS (`checked`):
the bootstrap left no skills directory behind; `skills sandbox/skills` installed the review
prompt as `~/.codex/skills/security-review-repo/SKILL.md`, owned by `appsec`, with the
SHA-256 in `skills.json` equal to the host file and the guest file; the staging archive
was gone from `/tmp` afterwards; a second install stopped with one line (`Already
installed: security-review-repo; pass --replace to overwrite`), also from a stopped VM;
`--replace` reinstalled. Codex 0.154 lists the skill by name and description in its
rendered prompt without a login: `codex debug prompt-input` prints the
`<skills_instructions>` block with `r0 = /home/appsec/.codex/skills` as a skill root,
which is the offline way to confirm discovery in a new guest. The same install into a fresh
OpenCode VM landed at `~/.config/opencode/skills/security-review-repo/SKILL.md` and
`opencode debug skill` listed it (name, description, location) next to the built-in
`customize-opencode`, again without a key.

Import uses **tracked working-tree contents**, including edits, without Git
metadata. Untracked files, `.env*`, common credential files, `.sbxenv.yaml` and
agent/editor configuration directories are excluded. Symlinks (including parent
components), hardlinks, special files and traversal paths are rejected; limits
are 64 MiB per file and 512 MiB total. Submodules require a separate, explicit
import strategy. Target instructions and source remain untrusted after import.
The manifest lives beside host state. Imports create `~/target/source` once;
`import --replace` swaps the target tree in place (harness state, `~/out` and the
key stay), `reset` is the clean-slate alternative. A Git worktree
(`git worktree add /tmp/x <ref>`) is the way to import a specific revision without
touching the working checkout. Export produces an opaque tar.gz from
`~/out` and **never extracts it on the host**. Inspect it as untrusted output.

Host state defaults to `~/.local/state/agentic-appsec/sbx/NAME`; use
`APPSEC_SBX_STATE` consistently to select another directory. State contains IDs,
template references, creation/version metadata and the admitted policy, not keys.
It is outside the guest. Do not edit it to bypass a failed guard.

## Effective policy, not just two allow rules

The existing development machine used sbx's **Balanced** global policy. The
wrapper leaves that policy and unrelated sandboxes intact. During fresh bootstrap,
it adds scoped download grants before any target or key is present. All of them are
`:443`: since 2026-09-11 the bootstrap rewrites the image's `http://` Ubuntu mirror URIs to
HTTPS before its first `apt-get update` and stops if one remains (threat model T34/M24). The
same day every `archive`/`security.ubuntu.com` address took 30 s to answer plain HTTP from
three networks while HTTPS answered in under a second, which turned a Linux x86_64 bootstrap
into 396 s; the arm64 guest's `ports.ubuntu.com` was unaffected. With the rewrite the same Linux host's bootstrap
took 136 s the same afternoon (`Phases: sbx create 3s, grants 2s, bootstrap 136s, policy lock 10s,
isolation 2s, template save 61s`), the rest being the mirrors' uneven HTTPS front ends that day; a retry on the
same host on 2026-09-14 gave `Phases: sbx create 4s, grants 2s, bootstrap 35s, policy lock 10s, isolation 2s,
template save 62s`, so the bootstrap itself is on a par with the Mac once the mirrors answer normally;
the Mac's arm64 create on 2026-09-11: `bootstrap 27s, template save 32s`, all mirror lines `https://`;
the first completed Windows create on 2026-09-14 (after the CRLF fix, OpenCode profile): `Phases: sbx create 4s,
grants 2s, bootstrap 45s, policy lock 8s, isolation 2s, template save 91s`. At admission,
it temporarily denies `**`, removes bootstrap grants, adds scoped denies for all
inherited allows except the admitted endpoints, adds those endpoints, and removes
the temporary guard. It validates the result before permitting entry.

This cannot safely narrow every possible global configuration: an inherited `**`
or another grant overlapping a desired endpoint cannot be carved up using a
narrower allow, because deny wins. The wrapper refuses such a configuration.
Central organisation governance is also outside this implementation. On a fresh
sbx installation, initialise the global policy first with `sbx policy init deny-all`
(the docs call this preset Locked Down) or `balanced`; the wrapper does not silently
reset it. The bootstrap adds its own sandbox-scoped download grants, so `deny-all`
is sufficient and is the better choice for a pilot machine. `init` is one-time:
to switch an existing installation, run `sbx policy reset`; it deletes the local
policy store, stops running sandboxes, drops every sandbox-scoped rule (wrapper VMs
created before it must be recreated) and then asks interactively which preset to
initialise, so choose `deny-all` there (checked 2026-09-11).
Balanced overlaps some profiles: on 2026-09-11 its `default-ai-services` rule with
`**.openai.com:443` made `create --provider codex` refuse, because denying the
wildcard would deny `api.openai.com` as well. The message names the rule; the
surgical alternative to re-initialising is `sbx policy rm network --id
default-ai-services`, which also drops that rule's Anthropic, Google and other
vendor hosts for every sandbox on the machine. `sbx policy profile` is unrelated:
it lists profiles pushed by remote organisation governance. Subsequent global or scoped policy edits
cause workload entry to fail and stop the affected VM family; reset recompiles
policy from the clean baseline. Host policy changes during an already running
session are trusted administration, not continuously monitored here.

Docker documents that allowed hostnames are not subsequently denied by CIDR rules
for their resolved IP. Therefore direct-IP denies do **not** establish protection
against every private-address resolution/rebinding case. Likewise, the earlier
Windows trial observed DNS answers for some allowed-kit names despite TCP denies.
Neither a denial in the HTTP proxy nor the name “offline” proves that no DNS query
can leave the host resolver. Resolve this before relying on the profile for strict
network confidentiality. [Local policy semantics](https://docs.docker.com/ai/sandboxes/governance/access-controls/local/)

## Portability

Containment is sbx's and lives outside the guest; the guest is Ubuntu on every host.
Only the wrapper's host side had to become portable (threat model **M22**):

- **Locking:** `fcntl.flock` on POSIX, `msvcrt.locking` on Windows, one file per VM.
- **Import reader:** POSIX walks every path component with `O_NOFOLLOW` relative to a
  directory descriptor (race-free). Hosts without `dir_fd` fall back to `lstat` per
  component, rejecting symlinks and NTFS reparse points, then open; that path has a
  documented race window. Both readers refuse traversal, FIFOs, devices and hardlinks.
- **Modes from the Git index**, not host `st_mode`: a Windows checkout yields the
  same file set and modes as a macOS one. Symlink (`120000`) and submodule (`160000`)
  index entries are refused by name instead of failing on a directory open.
- **`core.autocrlf=true`** prints a note: the working tree's CRLF content is what
  gets imported, so the SHA-256 values in `import.json` differ from those of an LF
  checkout for every text file. To compare content across hosts, clone the target with
  `core.autocrlf=false` on Windows; Git's index blob ids are the line-ending-independent
  identity and are a candidate second column for `import.json`.
- **Guest scripts are staged with LF endings** before `sbx cp`, and a root
  `.gitattributes` pins `eol=lf` for the guest, kit and skills files. The first Windows
  `create` (2026-09-14, `sbx create` 8 s, grants 2 s) stopped at bootstrap line 3
  because Git for Windows' default `core.autocrlf=true` had turned `set -euo pipefail`
  into `pipefail\r`; the terminal showed it as `: invalid option name.sh: line 3`. The retry
  with the staged copy ran through to `Ready` (bootstrap 45 s, template save 91 s), and
  `verify` passed: Ubuntu 26.04, x86_64 guest, Node 24.20.0, npm 11.19.0, OpenCode 1.18.29,
  runsc probe `available`, entry guards passed. `import` of the seeded-v1 demo target:
  34 tracked files, 0 excluded, the same set as the Mac record; the autocrlf note fired,
  so the guest copy is CRLF and its hashes are not comparable to the Mac's.
  `skills` with a Mantis clone at `48e00247` (2026-09-12): 19 skills, 24 files, 76 skipped, into
  `~/.config/opencode/skills`, the same skill and file counts as the Mac's Codex install
  from `d13c93fb`; first Mantis install on OpenCode, record in `skills.json`. The shell after
  it had no key: the VM had stopped itself in between (see [VM lifetime](#vm-lifetime-idle-stop-sessions-and-credentials)); not a
  Windows fault, reproduced on macOS the same day.
- **Entry** uses `subprocess.call` with the console inherited (Windows has no
  `exec`), and `sbx exec -it` needs a real console.
- **Windows over SSH (2026-09-14):** sandboxd cannot be started from a key-authenticated
  SSH logon; it fails loading its OAuth tokens with "logon session does not exist or there
  is no credential set associated with this logon session" (Windows Credential Manager has
  no credentials for a public-key logon). Started once from a desktop session, the daemon
  serves SSH clients over its named pipe; every sbx call then prints `WARN: failed to list
  stored credentials; continuing without them`, and `exec`, `cp`, `stop`, `ls`, `inspect`,
  `policy` and `template` work. **`sbx create` and `sbx rm` do not** (`docker login service
  unavailable`; `list credential metadata`), so `create`, `repro-create`, `reset` and `destroy`
  are desktop-session actions on Windows; the wrapper's other actions can be driven remotely. Such a session is elevated for an
  administrator account. Windows OpenSSH's default shell is PowerShell, which parses the
  command line before `cmd` or the wrapper sees it: pass guest commands as plain words, or
  `put` a script and `exec sh` it. Printed messages are ASCII since the console rendered a
  Unicode ellipsis as a replacement character.
- Host state directory defaults to `~/.local/state/agentic-appsec/sbx` on every OS;
  on Windows the profile ACL, not `0700`, is the boundary.

State written by the single-file v0.1 wrapper is migrated on first use (OpenRouter
or offline profile). Windows and Linux hosts still need the
[platform acceptance checks](../sandbox-comparison.md#additional-platform-acceptance-checks)
before a recipe is published for them.

## Acceptance record

### Windows 11 x64, 2026-09-14

Host: Windows 11 Education 25H2, build 26200.9445, x64 (AMD Ryzen 5 2600X, 32 GB), sbx
**v0.42.1**, backend **Windows Hypervisor Platform** (`sbx diagnose`:
`WHvCapabilityCodeHypervisorPresent`), Hyper-V and WSL services present, no Docker Desktop
process. Guest: Ubuntu 26.04, kernel 7.0.12, x86_64, Node 24.20.0, npm 11.19.0, OpenCode
1.18.29, gVisor 20260907.0. Operator account is an administrator; standard-user daily
operation is untested. Steps up to `skills` were run by the operator at the console, the
rest by Claude over SSH (see the portability notes), with `repro-create` and `reset` from
the operator's desktop session because `sbx create` and `sbx rm` need the login service.

Passed:

- `create` twice (first attempt failed on CRLF, see portability): `Phases: sbx create 4s,
  grants 2s, bootstrap 45s, policy lock 8s, isolation 2s, template save 91s`, then on the
  recreated VM `3.3 / 1.5 / 37.8 / 7.0 / 1.8 / 76.8` s.
- `verify`: versions as above, runsc probe `available` (the first x86_64 guest; the arm64
  guest fails it), entry guards passed.
- `import` of the seeded-v2 demo target from an autocrlf-off clone: 34 files, 0 excluded,
  **all 34 manifest hashes equal the Mac tree**. An earlier import from an autocrlf checkout
  imported CRLF copies with different hashes, as documented.
- `skills` with a Mantis clone (19 skills / 24 files, as on the Mac) and, on the recreated
  VM, `sandbox/skills` alone (1 skill).
- `key` from the console, then a non-interactive review run driven over SSH: OpenCode
  `run` with the `security-review-repo` skill, DeepSeek V4 Flash via OpenRouter, 27 min, the
  report written to `~/out` without a prompt, **no denied request in the policy log**
  (record: `agentic-appsec-demo/runs/opencode-deepseek-v4flash-sbx-win-01.md`).
- `export` to a host path, 4,415-byte archive holding `findings.md`, copied to the Mac and
  listed there; `put` of three scripts.
- `stop` from a second session while an `exec` session was open: the open session ended,
  the VM stopped, and `/run/appsec` was gone on re-entry.
- Idle stop observed from the operator's console: after the VM stopped itself following a
  `key`, the next `shell` held no key and printed the entry note about the missing
  credential (the `credential_hint` added the same day).
- Network probes from the workload user (the Mac record's set, on this host's network): HTTPS
  to `api.anthropic.com` returned the proxy's 403 and the log shows `No matching allow rule
  (default deny)`; direct-IP TLS to `1.1.1.1` was denied through the proxy env (403) and,
  with the proxy variables cleared, cut by the transparent proxy (TLS EOF), both logged
  against the local CIDR rule, as was a private address (`192.168.1.1:443`); `npm install
  --ignore-scripts is-number@7.0.0` succeeded through the registry grant; the Docker socket
  and `sudo` were refused. **DNS:** denied names (`github.com`, `api.anthropic.com`, an
  invalid name) got no answer and each shows as `DNS lookup blocked by proxy policy` in the
  log, allowed names answered. The earlier Windows trial's DNS discrepancy (answers for
  denied names) did not reproduce with this profile.
- Import edge cases from a checkout under `work\edge ünïcode\` (space and umlaut in the path):
  a tracked file behind an NTFS junction was refused by name (`Symlink or reparse point in
  path: linked/inside.txt`); with the junction dropped, three files imported, `größe.txt`
  arrived with its name intact in the guest and the manifest, and `run me.sh` kept its
  `100755` index mode (`755` in the guest, ran directly).
- A `runsc` container in the primary (`docker run --rm --runtime=runsc --network=none
  curlimages/curl --version`, as root via `sbx exec`, outside the workload boundary) ran on
  the x86_64 guest.
- `stop` after closing the console window mid-session: the operator opened `shell --key`,
  started `sleep 900 & sleep 900` in the guest, closed the window, and ran `stop` from a
  fresh console within the minute. Verified over SSH afterwards: VM stopped, no lock left
  (the wrapper's lock file unchanged), and the re-entry booted a fresh guest with no
  surviving `sleep`, no `/run/appsec`, and the credential note.

- `reset` from a desktop session (after the SSH attempt below had been refused cleanly:
  `sbx rm failed and the VM is unchanged; nothing was reset`, primary still usable): the
  VM was removed and recreated from `appsec-clean:0a70d32d8c6d` in `sbx create 3.7s, image
  load 1.6s, policy lock 2.9s, isolation 1.6s`; `verify` passed with the same tool versions;
  `~/target` and `~/out` empty; the installed skill gone with the rest of the post-template
  state. sbx printed its nominal template-agent warning (see the reset section).

- Reproducer, from the desktop session: `repro-create` from the clean template in 13 s
  (`sbx create 4s, image load 2s, policy lock 2s, isolation 2s`, offline profile); inside it
  a fixture wrote `~/out/repro-result.txt` on x86_64, HTTPS to `registry.npmjs.org` and
  `openrouter.ai` were both denied by the reproducer's local rule (403, logged), the Docker
  socket was refused and no key file existed; `key` on the reproducer was refused (`Offline
  reproducer VMs never receive model keys`); `export` saved a 212-byte archive holding the
  result file, verified on the Mac. The primary's `stop` stopped the reproducer first, then
  itself; the primary's `reset` deleted the reproducer and recreated the primary in 13 s;
  final `stop` left one stopped sandbox. The reproducer's host state directory is kept, as
  on the Mac.

Not covered: entry from a plain conhost window (the console tests used pwsh in Windows
Terminal); standard-user daily operation (the operator account is an administrator). Note
also that headless operation over key-based SSH is partial: see the portability notes. Attempted over SSH on 2026-09-14:
`repro-create` failed in 3 s at `sbx create` (`docker login service unavailable`), and
`reset` failed at `sbx rm --force` (`list credential metadata: logon session does not
exist`), which left the primary refused as "Provisioning incomplete" until a reset from the
desktop; the wrapper now restores its state when `sbx rm` fails without removing the VM.

### macOS

The following passed on the development Mac with sbx v0.42.1:

- Fresh shell-kit provisioning; actual mount inspection showed only sbx-generated
  hosts/resolver shares, with no workspace, skills share or SSH-agent socket.
- Interactive and noninteractive entry as `appsec`, expected tool versions,
  sudo denial and Docker-socket denial.
- A synthetic tracked Git fixture imported one script while excluding its `.env`;
  the script ran and its exported archive contained the expected output.
- HTTPS to `api.anthropic.com` returned a local-rule denial. A direct-IP TLS probe
  to `1.1.1.1` failed and appeared in the transparent-proxy deny log. npm metadata
  retrieval and an actual `npm install --ignore-scripts` of `is-number@7.0.0`
  succeeded through the intended registry grant.
- A **synthetic** key was readable but not writable by the workload, then absent
  after host stop and automatic restart. No real model call was made.
- A separate reproducer booted from the clean template, ran the copied fixture,
  denied the tested npm HTTPS request, rejected key injection, and exported output.
- Adding a scoped policy rule caused the next workload entry to refuse and stop
  the primary. Clean reset removed the imported target and a dirty canary, while
  retaining the installed Node/OpenCode tools.
- Primary stop also stopped a recorded reproducer. Primary reset deleted that
  reproducer and removed the dependency-install canary. Disposable test VMs were
  removed; the final primary was left clean and stopped, and the unrelated demo
  sandbox retained its original identity and stopped state.
- **2026-09-11, sixth pass, Codex CLI 0.154.0 on a ChatGPT seat (`--provider codex`,
  device-code login inside the guest, model `gpt-6-astra`):** create, verify, import,
  shell, login, the skill `$security-review-repo`, export all worked; the report write to
  `~/out` needed an approval in the harness UI (the VM predated the `writable_roots`
  seed; Codex's rollout transcript does not record approvals, the operator does). Hosts used: `chatgpt.com` and `auth.openai.com`;
  `api.openai.com` never. Denied and harmless at startup: GitHub hosts (skill installer,
  update check); denied during the run: 40 attempts by the `codex` binary (traced) to download the
  account's installed plugin bundles from server-named `*.oaiusercontent.com` hosts,
  plus one to `files.openai.com` (per Codex's own log, `remote_installed_plugin_sync`). Two harness-side corrections came out of it: the prompt is a skill
  (not a prompt file), and its filter block is scoped so the review does not stop to
  ask about shell use.
- **2026-09-10, fifth pass, tier A2 with the frontier model (Claude Fable 5.1 on a
  Team seat, browser login, profile with the individual `DISABLE_*` switches):** Fable
  appeared in `/model` and ran the whole-repo review in eight minutes with no
  safeguard intervention or forced redirect; three verification subagents were sent to
  Opus 5 by the model's own choice. Traffic: the two Anthropic hosts and the known
  startup denials only. The run record and export live in the demo workspace.
- **2026-09-10, fourth pass, tier A2 (`--provider claude-code`, Claude Code 2.1.267
  pinned by the bootstrap, browser login from the guest, Opus 5 on a Team seat):**
  create, verify, import, shell, `/login`, `/security-review-repo`, export all
  worked; the report was written to `~/out` without a prompt. Denied at startup and
  harmless: plugin-marketplace clone from GitHub (traced to `git-remote-https`),
  `downloads.claude.ai`, `mcp-proxy.anthropic.com`; denied during the run: PyPI,
  from the agent's `uv sync` (traced to the `uv` process). Two corrections came out
  of it: `platform.claude.com` joined the profile after a 403, and the flag CDN
  joined it after Fable 5.1 was missing from `/model` while present on the host with
  the same account. The setup-token path returned HTTP 401 and is recorded as not
  working. No GitHub attempt followed the report write with this harness.
- **2026-09-10, third pass, Claude Opus 5 via OpenRouter, same VM as the second:**
  the agent copied the target to `/tmp/opencode/src` and ran `uv sync` there
  (denied at PyPI, 62 attempts); the imported tree stayed unmodified. Denied
  `github.com:443` connections again clustered at the session's end (35 this time);
  a process-level connection trace is armed in the guest for the next exit. A
  Fable 5.1 attempt through OpenRouter was refused by the gateway's data-policy
  setting before the first token (ZDR), which is how tier A1's ZDR caveat shows
  up in practice.
- **2026-09-10, second complete pass on a VM created by the updated bootstrap
  (GLM-5.3 via OpenRouter):** `create` installed the command file, the managed
  config and the profile variables itself; OpenCode stayed at 1.18.29 through the
  run; the `~/out` write needed no prompt; `import`, `key`, `shell`, `export` as
  before. Policy log during the run: OpenRouter, plus 46 denied PyPI connections
  from the agent's own dependency-install attempts. A burst of 2,328 denied
  `github.com:443` connections at the end of the *previous* VM's session remains
  unexplained (not from a logged tool call; VM destroyed before diagnosis).
- **2026-09-10, first complete assignment pass (OpenRouter preset, DeepSeek V4 Flash):**
  fresh `create` (bootstrap about one minute), `verify`, `import` of a 34-file Git
  worktree, `key`, `shell`, the installed whole-repo `/security-review`, `put`,
  `import --replace`, and `export` of `~/out` were all exercised on this day by the
  operator with the wrapper. The review wrote `~/out/findings.md` (three findings,
  see the demo workspace's run record) after an OpenCode `external_directory`
  permission prompt for `~/out`, which the managed config now pre-answers. Policy
  log during the run: OpenRouter only. Session titling used a second model through
  the same provider (one `google/gemini-3.8-flash` request in the guest log); the
  endpoint allowlist cannot distinguish models behind a gateway (T27 residual).
- **2026-09-10, package refactor:** against the existing primary, v0.1 state migrated
  to the OpenRouter profile; `verify`, non-interactive `exec` as `appsec` (uid 1001,
  no key present, prior import intact) and `stop` behaved as before. No `create`,
  `import` or `key` was repeated against a VM on this date; those paths are covered
  by the unit tests and the unchanged sbx calls.

Host regression tests cover policy overlap/drift and import path/file attacks:

```sh
python3 -m unittest discover -s sandbox/sbx -p 'test_*.py' -v
bash -n sandbox/make-appsec-sbx.sh sandbox/sbx/appsec_sbx/guest/bootstrap.sh
```

They also cover provider profiles (one exact endpoint, no wildcards, registry
distinct from the model endpoint), the v0.1 state migration, and both import
readers.

This evidence advances the [backend comparison](../sandbox-comparison.md); it is
not full R1–R8 certification. The [threat model](../threat-model.md) remains the
acceptance contract.
