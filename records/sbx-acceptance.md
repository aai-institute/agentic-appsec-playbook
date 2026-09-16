# Acceptance record: AppSec shell on Docker sbx

Evidence file for the [sbx user guide](../docs/src/content/docs/sandbox/sbx/index.md) and
the [design notes](../design/sbx-internals.md). Each section records one host platform
against the [platform acceptance checks](../design/sandbox-comparison.md#additional-platform-acceptance-checks)
of the backend comparison: what ran, on which versions, what passed and what is not covered.
Dated figures are what was measured on that day; nothing here is a guarantee for another host.

The Windows and Linux rows were driven mostly over SSH from the maintainer's Mac. That was a
convenient way to validate the wrapper on a second machine, not the intended way to operate
it: the operator on their own machine is the primary use case, and the
[SSH-driven operation](#ssh-driven-operation) notes at the end record only what that
validation setup revealed about each platform.

## Windows 11 x64, 2026-09-14

Host: Windows 11 Education 25H2, build 26200.9445, x64 (AMD Ryzen 5 2600X, 32 GB), sbx
**v0.42.1**, backend **Windows Hypervisor Platform** (`sbx diagnose`:
`WHvCapabilityCodeHypervisorPresent`), Hyper-V and WSL services present, no Docker Desktop
process. Guest: Ubuntu 26.04, kernel 7.0.12, x86_64, Node 24.20.0, npm 11.19.0, OpenCode
1.18.29, gVisor 20260907.0. Operator account is an administrator; standard-user daily
operation is untested. Steps up to `skills` were run by the operator at the console, the
rest by Claude over SSH (see [SSH-driven operation](#ssh-driven-operation)), with `repro-create` and `reset` from
the operator's desktop session because `sbx create` and `sbx rm` need the login service.

Passed:

- `create` twice (first attempt failed on CRLF, see the design notes, *Portability*): `Phases: sbx create 4s,
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
  (record: demo workspace, not public, `runs/opencode-deepseek-v4flash-sbx-win-01.md`).
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
  state. sbx printed its nominal template-agent warning (see the design notes, *Reproducer boundary and reset*).

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
also that headless operation over key-based SSH is partial: see [SSH-driven operation](#ssh-driven-operation). Attempted over SSH on 2026-09-14:
`repro-create` failed in 3 s at `sbx create` (`docker login service unavailable`), and
`reset` failed at `sbx rm --force` (`list credential metadata: logon session does not
exist`), which left the primary refused as "Provisioning incomplete" until a reset from the
desktop; the wrapper now restores its state when `sbx rm` fails without removing the VM.

## Linux x86_64, 2026-09-14

Host: Manjaro Linux, kernel 6.18.50-1-MANJARO, x86_64 (the same machine as the Windows record,
AMD Ryzen 5 2600X, 32 GB, booted into Linux), sbx **v0.42.1**, backend **KVM** (`sbx diagnose`:
`/dev/kvm is accessible`), Docker Engine 29.7.2 installed on the host but unused by sbx, uv 0.12.10,
Python 3.14.7. Guest: Ubuntu 26.04, kernel 7.0.12, x86_64, Node 24.20.0, npm 11.19.0, OpenCode
1.18.29, gVisor 20260907.0. Operator account is a `wheel`/`docker`/`libvirt` member with a
GNOME keyring in an autologin desktop session; standard-user daily operation is untested. Every
step was run by Claude over key-based SSH (zsh login shell) except `key`, which the operator ran
in the same way; the desktop was needed only to answer the keyring unlock prompts (see
[SSH-driven operation](#ssh-driven-operation)).

Passed:

- `destroy` of the VM from the 2026-09-11 `create` trial (1 s, headless) and a fresh `create`:
  `Phases: sbx create 4s, grants 2s, bootstrap 36s, policy lock 10s, isolation 2s, template
  save 62s`, 119 s wall, all mirror lines `https://`; the bootstrap's one denied request was
  nvm probing `iojs.org:443`.
- `verify`: versions as above, runsc probe `available`, entry guards passed, 7 s including the
  auto-start of the stopped VM.
- `import` of the seeded-v2 demo target from `/work/app` on the `seeded` branch (`core.autocrlf`
  unset): 34 files, 0 excluded, **all 34 manifest hashes equal the Mac tree**, 6 s.
- `skills` with `sandbox/skills` alone: 1 skill from commit `918643c`, into
  `~/.config/opencode/skills`, 7 s.
- `key` by the operator over SSH while an `exec ... sleep` keep-alive session held the VM, then
  a non-interactive review run driven over SSH: OpenCode `run` with the
  `security-review-repo` skill, DeepSeek V4 Flash via OpenRouter, 9 min 9 s, the report written to
  `~/out` without a prompt, **no denied request in the policy log**, the same three seeds reported
  as on Windows (record: demo workspace, not public, `runs/opencode-deepseek-v4flash-sbx-linux-01.md`).
- `export` to a host path, 3,766-byte archive holding `findings.md`, copied to the Mac and
  listed there; `put` of three scripts (the review launcher, the review
  command and the probe set).
- `stop` from a second session while the keep-alive `exec` session was open: that session
  ended (exit 137), the reproducer stopped first, then the VM, 9 s; `/run/appsec` was gone on
  re-entry and the credential note printed.
- Network probes from the workload user: HTTPS to `api.anthropic.com` 403 (`No matching allow
  rule (default deny)`); direct-IP TLS to `1.1.1.1` 403 through the proxy env and, with the
  proxy variables cleared, cut by the transparent proxy (TLS `unexpected eof`), both logged
  against the local CIDR rule, as was `192.168.1.1:443`; `npm install --ignore-scripts
  is-number@7.0.0` succeeded through the registry grant; the Docker socket (`permission
  denied`) and `sudo` (`a password is required`) were refused; no `/run/appsec` before `key`.
  **DNS:** `github.com`, `api.anthropic.com` and an invalid name got no answer and each shows
  as `DNS lookup blocked by proxy policy`; `registry.npmjs.org` and `openrouter.ai` answered.
  Same results as the Windows row.
- Import edge cases from a checkout under `/tmp/linux-acc/edge ünïcode/` (space and umlaut in
  the path): a symlink index entry was refused by name (`Symlink in the Git index is not
  imported: linked`), with and without `--replace`, and the previous target stayed untouched;
  with the symlink dropped, `import --replace` brought three files, `größe.txt` arrived with its
  name intact in the guest and the manifest, and `run me.sh` kept its `100755` index mode (`755`
  in the guest, ran directly).
- A `runsc` container in the primary (`docker run --rm --runtime=runsc --network=none
  curlimages/curl --version`, as root via `sbx exec`, outside the workload boundary) ran.
- `stop` after terminal closure mid-session: a pty SSH session held `exec ... sh -c "sleep 900
  & sleep 900"` in the guest and was hung up (SIGHUP to the ssh client, the remote equivalent of
  closing the window); the guest session ended at once while the VM kept running, and `stop`
  from a fresh session 4 s later took 8 s and cascaded to the reproducer. No lock left (the
  wrapper's lock file unchanged); the re-entry booted a fresh guest with no surviving `sleep`,
  no `/run/appsec`, and the credential note.
- `reset`, headless, with the reproducer running: the reproducer was deleted, the VM removed
  and recreated from `appsec-clean:038811f492fd` in `sbx create 4s, image load 2s, policy lock
  4s, isolation 3s`, 18 s wall; `verify` passed with the same tool versions; `~/target` and
  `~/out` empty; the installed skill gone with the rest of the post-template state and the
  host's `import.json` removed, while `skills.json` stayed on the host (a stale record after
  reset). sbx printed its nominal template-agent warning. The final `stop` left one stopped
  sandbox; the reproducer's host state directory is kept, as on the Mac and Windows.
- Reproducer, headless: `repro-create appsec-sbx-repro` from `appsec-clean:038811f492fd` in
  17 s (`sbx create 4s, image load 2s, policy lock 2s, isolation 2s`, offline profile, sbx's
  nominal template-agent warning); inside it a fixture wrote `~/out/repro-result.txt` on
  x86_64, HTTPS to `registry.npmjs.org` and `openrouter.ai` were denied by the reproducer's
  local rule (403, logged), the Docker socket was refused, no key file, no skills directory and
  an empty `~/target`; `key` on the reproducer was refused (`Offline reproducer VMs never
  receive model keys`); `export` saved a 212-byte archive holding the result file, verified on
  the Mac. The primary's `stop` stopped the reproducer first, then itself, in both stop
  tests; the primary's `reset` deleted the reproducer before recreating the primary.
- Observed on the way: a `repro-create` call without the new name failed at argument parsing
  and still left `~/.local/state/agentic-appsec/sbx/appsec-sbx-repro/` with an empty `lock`
  file behind, the parked state-directory ordering item; the following call reused it.

Not covered: standard-user daily operation; entry from a desktop terminal (every step ran over
SSH); a host without a desktop session or keyring (see [SSH-driven operation](#ssh-driven-operation)).

## macOS

### Discovery flow on 0.43.0 (2026-09-16)

Apple silicon, CLI and daemon both v0.43.0, wrapper 0.2.0, Ubuntu 26.04
arm64, kernel 7.0.12. All 13 host diagnostics passed; SSH forwarding remained
disabled and the MCP server inventory was empty.

Fresh `create --provider claude-code --no-registry`, policy lock, isolation,
template save, `verify`, target import, local skill installation and
`skills --replace` passed. Claude Code 2.1.267 completed a discovery pass with
the reference harness's `/vuln-scan` skill at `d3bea6b5793b`, using an Opus 5
Team seat. Both report files exported successfully; final wrapper stop
succeeded. The operator ran the commands in the Codex sidebar terminal.

Before discovery, wrapper stop halted a VM with a background test process;
inspection showed stopped, zero sessions and no runtime mounts. A second stop
after subscription login removed the credential file; after restart,
`claude auth status` reported `loggedIn: false`. Provider-side revocation was
not tested.

The gVisor probe still failed with the known ARM page-size warning. Bootstrap
also emitted `tput: unknown terminal "unknown"` twice and completed. Policy
logs showed model/login hosts after setup and bootstrap hosts at earlier
timestamps. Auxiliary Claude and GitHub requests were denied; discovery
completed without widening the allowlist.

No sbx regression was observed in this discovery flow. This does not repeat
the full 0.42.1 acceptance matrix: reset, reproducers and other providers were
not retested. The 20-minute manual threshold was exceeded by 1 minute 16
seconds with the operator's decision to retain the completed report. Raw
findings and the detailed run record remain in the private demo workspace.

The next run used a fresh OpenCode 1.18.29 VM with OpenRouter and no registry.
Create, verify, import, direct GitHub skill installation, export and stop all
passed. The target's 34 file hashes matched the Claude run. The same pinned
skill pack installed nine skills and 19 files into OpenCode. The parent trace
confirms skill loading, six review tasks and seven scoring tasks, using
`openrouter/z-ai/glm-5.3-flash` (parent variant `max`). Both reports were saved.

That run took 45m 19s, exceeding the manual budget by 25m 19s. The storage
review task took 31m 42s. The user reported $0.13 in OpenRouter; OpenCode's
all-session stats showed $0.0893 and the parent session $0.02042441. The
provider difference remains unexplained. Basic report checks found a wrong
low-confidence count and template count; findings remain untriaged.

OpenCode stats recorded four web fetches despite the prompt's network ban.
The log shows denied PyPI, Python file-host, Starlette and GitHub requests.
Only OpenRouter appears as an allowed workload host; other allowed traffic
is dated to bootstrap. Child transcripts were not in the parent export, so
exact commands and fetch results are not available. No allowlist was widened.
The workflow passed, but the skill's prompt restrictions were not fully
followed. No new sbx regression was observed; the ARM gVisor limit remains.

### Prior 0.42.1 acceptance

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

This evidence advances the [backend comparison](../design/sandbox-comparison.md); it is
not full R1–R8 certification. The [threat model](../docs/src/content/docs/sandbox/threat-model.md) remains the
acceptance contract.

## SSH-driven operation

What driving the wrapper from another machine over SSH showed about each host. Portability
facts that hold for the operator at the console are in the design notes.

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
- **Linux over SSH (2026-09-14, Manjaro, GNOME keyring):** everything ran headless from a
  key-authenticated SSH logon, `sbx daemon start`, `sbx create` and `sbx rm` included, because
  the daemon reaches the operator's session keyring over the user D-Bus bus
  (`/run/user/1000/bus`), which the SSH session shares. Unlock prompts appeared on the desktop
  and the operator answered them. When nobody does (2026-09-11 and early 2026-09-14 starts),
  the daemon logs `the OS keychain is locked; unlock your keyring and retry ... prompt
  dismissed` to its stderr log and still starts, and that day's `create` succeeded: on Linux a
  locked keyring degrades sbx to warnings and deferred analytics uploads, unlike Windows'
  Credential Manager refusal. Not tested: a host with no desktop session at all.
