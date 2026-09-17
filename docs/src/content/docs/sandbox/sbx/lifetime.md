---
title: "VM lifetime, reset and policy"
description: "The idle stop and credentials, reproducer VMs, reset and destroy, and the global sbx policy."
---

## Idle stop, sessions and credentials

sbx stops a local VM by itself about a minute after its last *session* ends, where a session
is an interactive shell or a running `exec`. Workload entry and transfer actions restart a stopped VM
silently; a line `Sandbox <name> started successfully` in an action's output means the VM had
stopped in between.

| | sbx idle stop, or `sbx stop` | wrapper `stop` / `unkey` |
|---|---|---|
| Disk: installed tools, imported target, `~/out`, skills, harness state and databases | kept | kept; `reset` returns to the clean template, which keeps the tools and drops the target, `~/out`, installed skills, harness state and any login store (reinstall skills after a reset) |
| Tmpfs key file `/run/appsec/env` (`key`) | **gone** | removed |
| Harness login stores on the agent's home (`~/.claude/.credentials.json`, `~/.codex/auth.json`, OpenCode's `auth.json`) | **kept**: a seat's refresh token stays in the VM | `unkey` removes them; `stop` attempts removal only while the VM is running |
| Reproducer VMs | untouched | stopped with the primary |
| Server-side validity of the key or seat | unchanged | unchanged; revocation is a separate action |

An idle stop is not the kill switch. The API key disappears with it only because the key file
lives on tmpfs, a browser-login credential stays on disk, and nothing is revoked at the
provider. `unkey` clears known credential files. `stop` attempts that cleanup only when
the VM is running and ignores deletion errors. If the VM has already stopped,
use `unkey` (which starts it and checks entry conditions), then `stop`, and
revoke credentials at the provider. See [M23](/sandbox/threat-model/controls/#partial-measures)
for this remaining cleanup gap.

- **Interactive runs:** `shell --key` places the key and enters in one step. A `key` that is
  not followed at once by an entry evaporates. Every workload entry on a provider profile
  prints `NOTE: the guest holds no model credential ...` when the guest has neither the key
  file nor a harness login store.
- **Unattended runs** (`exec` of a harness command, a detached process started inside the
  guest): hold one session open for the duration, for example `appsec-sbx exec appsec-sbx --
  sleep 7200` in a second terminal, across `key`, the start and the run.
- **Seat-tier profiles** (Claude Code, Codex login): the login store survives idle stops, so a
  VM that went to sleep still authenticates as the seat when it wakes. End a working session
  with `unkey` followed by `stop`, and revoke the login at the provider.
- **Reading records:** phase timings and policy-log timestamps are unaffected; the VM's
  `uptime` in `sbx inspect` restarts at every wake and says nothing about the run.

## Test the kill switch

Complete this rehearsal on a newly created VM before importing project code
or asking an agent to do any work. Repeat it if you change the credential
type, provider or stop procedure. Keep the provider's credential-management
page available on the host.

For an API key, use a temporary, capped key that you can revoke after the
test. In the first host terminal, start a harmless command:

```sh
appsec-sbx exec --key appsec-sbx -- sleep 600
```

For a subscription login, enter with `appsec-sbx shell appsec-sbx`. From the
guest home directory, start `claude` and use `/login`, or run
`codex login --device-auth`. Submit no review prompt. Exit the harness and
run `sleep 600` in the guest shell. Keep that session open for the test.
See [Providers and credentials](/sandbox/sbx/providers/) for login details.

While the command is still running, use a second host terminal:

```sh
appsec-sbx stop appsec-sbx
appsec-sbx status appsec-sbx
```

Confirm that the first terminal's command ended and the VM status is stopped.
If you use reproducer VMs, repeat the test with a harmless command running in
one and check its status too; stopping the primary must stop its reproducers.

Revoke the test API key or subscription login at the provider. Record the
provider's confirmation; deleting a local credential file does not revoke it.
Then restore the clean VM and check that it can start again:

```sh
appsec-sbx reset appsec-sbx
appsec-sbx verify appsec-sbx
```

Record the stop result, credential revocation and successful reset. Resolve
any failed step before the first review. Supply a fresh capped key or a new
login when you start that review, after importing the target and skills.

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
appsec-sbx export appsec-sbx-repro ./reproducer-results.zip

appsec-sbx stop appsec-sbx      # also stops the reproducers created through this primary
appsec-sbx reset appsec-sbx     # DELETES the primary's state and its reproducers, recreates from the clean template
appsec-sbx destroy appsec-sbx   # removes the primary and its reproducers entirely
```

Reset is required before every independent review: a new target, a repeat
discovery pass, or a comparison with another model, prompt or skill pack.
Resuming an interrupted review of the same target can retain its state.

Export any results you need, stop the run and revoke its credential before
resetting. `reset` removes the target, `~/out`, installed skills, harness state
and login stores, and removes associated reproducers. It restores the tools
from the clean template. Run `verify`, import the target, reinstall skills
and supply a fresh credential with a budget before the next review.
`import --replace` keeps tools, harness state, output and credentials; it
cannot provide a clean start for an independent review.

sbx prints a warning that the template "was built for the `shell` agent" on
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
