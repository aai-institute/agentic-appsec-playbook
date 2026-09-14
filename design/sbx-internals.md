# AppSec shell on Docker sbx: design notes

**Audience:** maintainers and reviewers. Operators use the
[user guide](../docs/src/content/docs/sandbox/sbx/index.md); the per-platform evidence is in
the [acceptance record](../records/sbx-acceptance.md). This file keeps the rationale behind the
wrapper's decisions, the investigations that produced them (dated, with what was observed), and
the contract tables that the user guide summarises. It grew as the wrapper's README between
2026-09-09 and 2026-09-14 and keeps that order.

The wrapper is the executable successor to the [Colima prototype](reference-sandbox-colima.md),
which stays frozen as the measured v0 reference. It installs the same Node/OpenCode toolchain in
a dedicated sbx VM, enters it as an unprivileged user, copies selected source in, and exports
results explicitly. The implementation is the Python package
[`appsec_sbx`](../sandbox/sbx/appsec_sbx/) (stdlib only, Python 3.9+): `cli.py`, `lifecycle.py`,
`policy.py`, `providers.py`, `transfer.py`, `hostos.py` and `sbxcli.py`; the guest side is
`guest/bootstrap.sh` plus a small shell kit (`kit/spec.yaml`). `sandbox/make-appsec-sbx.sh` is a
macOS/Linux shim around `python3 -m appsec_sbx` for use from a checkout; `pyproject.toml`
provides the `appsec-sbx` entry point (installation with `uvx` from the Git repository `checked`
2026-09-14).

**Tested locally on 2026-09-09 (v0.1, single file) and 2026-09-10 (package,
existing VM):** Apple silicon, sbx **v0.42.1**, Ubuntu 26.04 guest, Node **24.20.0**,
npm **11.19.0**, OpenCode **1.18.29**. The host side is written to run on Linux and
Windows as well ([portability](#portability)). Windows 11 x64 and Linux x86_64 have
[acceptance records](../records/sbx-acceptance.md) since 2026-09-14, so the wrapper announces
itself as untested only on other hosts.

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

## Provider profiles and harnesses

The operating steps (one-time host setup, install, create, verify, import, skills, shell,
export, stop) are in the [user guide](../docs/src/content/docs/sandbox/sbx/index.md) and
[Getting started](../docs/src/content/docs/getting-started.md). This section keeps what was
learned while defining the provider presets.

The provider decides the workload allowlist and the key variable, and is recorded
in host state; changing it means a new VM (`destroy`, then `create`). Presets and
the assignment tiers they serve:

(The preset table is in the user guide.)

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

(Commands: user guide, *Claude Code on a subscription seat*.)

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

The stop table (what an idle stop, `sbx stop`, wrapper `stop` and `unkey` each keep or remove) is
in the user guide.

So an idle stop is **not** the kill switch: it takes the API key with it by accident of tmpfs,
leaves a browser-login credential in place, and revokes nothing. `stop` and `unkey` remain the
actions that clear the guest of credentials (threat model T25, M23).

The operating consequences (enter with `shell --key`, hold a session open for unattended runs,
end seat-tier sessions with `stop`) are in the user guide.

## Reproducer boundary and reset

`reset` and `repro-create` restore the clean template with `sbx create --template`; sbx then
warns that the template "was built for the `shell` agent but you are using `appsec-shell`".
The template is this wrapper's own snapshot of the `appsec-shell` kit on the `shell-docker`
image, and sbx infers the agent name from the image flavour, so the warning is nominal; the
restored VM passes `verify`. Seen on Windows 2026-09-14, expected everywhere.

(Commands: user guide, *Reproducers, reset and destroy*.)

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
is [sandbox/skills/security-review-repo/SKILL.md](../sandbox/skills/security-review-repo/SKILL.md),
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

(The per-harness skills directory table is in the user guide.)

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
an uncommitted note in the demo workspace (not public).

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

The import rules (tracked working-tree contents, exclusions, size limits, `--replace`), the
export rule (opaque archive, never extracted on the host) and the host state directory are
described in the user guide; the threat-model rows behind them are R4 and R8 above.

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
  it had no key: the VM had stopped itself in between (see the VM lifetime section of the user guide); not a
  Windows fault, reproduced on macOS the same day.
- **Entry** uses `subprocess.call` with the console inherited (Windows has no
  `exec`), and `sbx exec -it` needs a real console.
- Host state directory defaults to `~/.local/state/agentic-appsec/sbx` on every OS;
  on Windows the profile ACL, not `0700`, is the boundary.

State written by the single-file v0.1 wrapper is migrated on first use (OpenRouter
or offline profile). The
[platform acceptance checks](sandbox-comparison.md#additional-platform-acceptance-checks)
are recorded in the [acceptance record](../records/sbx-acceptance.md) for macOS, Windows 11 x64
and Linux x86_64 (standard-user operation excepted); other hosts still need them before a
recipe is published for them.
