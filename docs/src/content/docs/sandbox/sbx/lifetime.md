---
title: "VM lifetime, reset and policy"
description: "The idle stop and credentials, reproducer VMs, reset and destroy, and the global sbx policy."
---

## Idle stop, sessions and credentials

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

An idle stop is not the kill switch. The API key disappears with it only because the key file
lives on tmpfs, a browser-login credential stays on disk, and nothing is revoked at the
provider. `stop` and `unkey` are the actions that clear the guest of credentials.

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
