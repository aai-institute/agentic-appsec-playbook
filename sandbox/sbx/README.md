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
Windows as well ([portability](#portability)); neither has an acceptance record, and
the wrapper says so on every entry there.

There is one material architecture change. Installed gVisor **20260831.0** failed
its hello-world smoke test in this sbx guest, both with its default platform and
with `--platform=ptrace`. The ARM guest reports a **16384-byte page size**; runsc
warns about a non-4K host and fails with a sandbox-start EOF. The page size is a
suspected compatibility factor, not an established diagnosis. The bootstrap
records the failure instead of silently substituting an ordinary nested container.
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
./sandbox/make-appsec-sbx.sh shell appsec-sbx
```

The provider decides the workload allowlist and the key variable, and is recorded
in host state; changing it means a new VM (`destroy`, then `create`). Presets and
the assignment tiers they serve:

| `create` option | Allowlist (plus the registry) | Key variable | Assignment tier |
|---|---|---|---|
| `--provider openrouter` (default) | `openrouter.ai:443` | `OPENROUTER_API_KEY` | B via the WG OpenRouter key |
| `--provider anthropic` | `api.anthropic.com:443` | `ANTHROPIC_API_KEY` | A1, Claude API key |
| `--provider deepseek` | `api.deepseek.com:443` | `DEEPSEEK_API_KEY` | B, direct DeepSeek key |
| `--provider claude-code` | `api.anthropic.com:443`, `platform.claude.com:443`, `cdn.growthbook.io:443` | `CLAUDE_CODE_OAUTH_TOKEN` | A2, Claude seat via Claude Code (see below) |
| `--endpoint HOST:PORT --key-var NAME` | that one exact endpoint | `NAME` | anything else (Z.ai, Zen, a gateway) |

Wildcards are refused. `--registry` is repeatable and takes a name (`npm`, `pypi`,
the latter two hosts) or an exact `HOST:PORT` such as an organisation mirror;
`--no-registry` allows none. (Keep `npm` on the `claude-code` profile: the harness
is installed from the registry inside the workload shell.) Pick the registry the
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
./sandbox/make-appsec-sbx.sh shell appsec-sbx
# Inside (Claude Code is installed and pinned by the bootstrap):
cd ~/target/source && claude
# /login -> "Claude account with subscription": open the printed URL in a browser on
# the HOST, paste the one-time code back. Then /model -> Claude Fable 5.1, and
# /security-review-repo (whole-repo variant, installed by create). The built-in
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
was a harness that opened at its prompt with no credential at all and looked logged
in until the first request. A fresh VM never has a credential; if `claude` does not
ask you to log in, run `claude auth status` before trusting it. The login profile sets `DISABLE_AUTOUPDATER`, `DISABLE_TELEMETRY`,
`DISABLE_ERROR_REPORTING` and `DISABLE_BUG_COMMAND`, deliberately not the blanket
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`: that variable also suppresses the
GrowthBook feature-flag fetch that decides which models a seat may pick, and Fable 5.1
is flag-gated. That is why the profile allows `cdn.growthbook.io:443` (threat model
M23, a recorded T12 relaxation). Count every safeguard intervention or redirect to an
Opus model for the run report. Expect these denials in the policy log at every start, all
harmless (checked 2026-09-10 with a process-level trace in the guest): a `git` clone
of `github.com/anthropics/claude-plugins-official` (the plugin marketplace
auto-install, with an SSH fallback to a GitHub address on port 22),
`downloads.claude.ai`, and a dozen attempts at `mcp-proxy.anthropic.com`; the harness
records the marketplace failure and retries hours later. Which models `/model` offers
is decided by the seat *and* by remote feature flags: on 2026-09-10 the same
`team_tier_1` account saw Fable 5.1 on the host and not in a guest whose profile
still denied the flag CDN; the host's `~/.claude.json` carried the gate in
`cachedGrowthBookFeatures`. Hence the CDN in the profile. The untested fallback when a
picker hides a model is typing it: `/model claude-fable-5-1`.

## Reproducer boundary and reset

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
Docker container nor the installed but failing runsc is credited as an additional
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

`create` installs the whole-repository review prompt
([guest/commands/security-review.md](appsec_sbx/guest/commands/security-review.md),
adapted from Anthropic's MIT `security-review` with the diff scoping removed) into
`~/.config/opencode/commands/`, because the import filter strips a repository's own
`.opencode/`. `put` copies one further host file to a new path under `/home/appsec/`;
it refuses traversal, directories and existing targets. Pasting long prompts through
a shell heredoc needs a quoted delimiter (`<<'EOF'`), or backticks in the prompt
are executed.

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
it adds scoped download grants before any target or key is present. At admission,
it temporarily denies `**`, removes bootstrap grants, adds scoped denies for all
inherited allows except the admitted endpoints, adds those endpoints, and removes
the temporary guard. It validates the result before permitting entry.

This cannot safely narrow every possible global configuration: an inherited `**`
or another grant overlapping a desired endpoint cannot be carved up using a
narrower allow, because deny wins. The wrapper refuses such a configuration.
Central organisation governance is also outside this implementation. On a fresh
sbx installation, initialise global policy first, choosing Locked Down or Balanced;
the wrapper does not silently reset it. Subsequent global or scoped policy edits
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
- **Modes from the Git index**, not host `st_mode`: a Windows checkout produces the
  same archive as a macOS one. Symlink (`120000`) and submodule (`160000`) index
  entries are refused by name instead of failing on a directory open.
- **`core.autocrlf=true`** prints a note: the working tree's CRLF content is what
  gets imported.
- **Entry** uses `subprocess.call` with the console inherited (Windows has no
  `exec`), and `sbx exec -it` needs a real console.
- Host state directory defaults to `~/.local/state/agentic-appsec/sbx` on every OS;
  on Windows the profile ACL, not `0700`, is the boundary.

State written by the single-file v0.1 wrapper is migrated on first use (OpenRouter
or offline profile). Windows and Linux hosts still need the
[platform acceptance checks](../sandbox-comparison.md#additional-platform-acceptance-checks)
before a recipe is published for them.

## Acceptance record

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
