---
title: "Command reference"
description: "Every appsec-sbx action with its options, generated from the wrapper's own help output."
---

Generated from `appsec-sbx --help` and `appsec-sbx ACTION --help` by
`sandbox/sbx/gen_command_reference.py`; a unit test keeps this page and the CLI in step, so
edit the help strings in the wrapper, not this file. Every action takes the sandbox name as
its first argument and defaults to `appsec-sbx`. From a checkout,
`./sandbox/make-appsec-sbx.sh` and `python -m appsec_sbx` take the same arguments.

```text
usage: appsec-sbx [-h] [--version] ACTION ...

appsec-sbx runs agents in Docker Sandboxes (sbx): a microVM with one
agent harness, one model provider and a filtered copy of your repository. Every action
takes the sandbox name as its first argument (default: appsec-sbx).

A run, in order:
  create -> verify -> import -> skills -> shell --key -> (review inside) -> export -> stop

positional arguments:
  ACTION
    create        provision a clean workload VM with exactly one model provider
    verify        run the entry guards and print guest versions
    import        copy the tracked files of a host Git checkout into ~/target/source
    skills        install a skill pack from a local checkout or public GitHub URL
    key           place the provider key in the guest (prompted, never on the command
                  line)
    unkey         remove the key file and the harness login stores from the guest
    exec          run one command in the VM as the workload user
    shell         interactive shell in the VM as the unprivileged workload user
    agent         alias of shell
    export        save ~/out as an opaque tar.gz on the host (never extracted)
    put           copy one host file to a new path under /home/appsec
    logs          print the recent policy log (allowed and denied connections)
    status        print sbx's description of the VM (sbx inspect)
    stop          kill switch: remove the credentials, stop the VM and its reproducers
    repro-create  create an offline reproducer VM from this primary's clean template
    reset         DELETE the VM's current state and recreate it from the clean
                  template
    destroy       remove the VM and its reproducers entirely
    admin         root maintenance shell (outside the workload boundary)

options:
  -h, --help      show this help message and exit
  --version       show program's version number and exit

`appsec-sbx ACTION --help` describes one action. Documentation:
https://github.com/aai-institute/agentic-appsec-playbook (docs/)
```

## Actions

| Action | Purpose |
|---|---|
| [`create`](#create) | provision a clean workload VM with exactly one model provider |
| [`verify`](#verify) | run the entry guards and print guest versions |
| [`import`](#import) | copy the tracked files of a host Git checkout into ~/target/source |
| [`skills`](#skills) | install a skill pack from a local checkout or public GitHub URL |
| [`key`](#key) | place the provider key in the guest (prompted, never on the command line) |
| [`unkey`](#unkey) | remove the key file and the harness login stores from the guest |
| [`exec`](#exec) | run one command in the VM as the workload user |
| [`shell`](#shell) | interactive shell in the VM as the unprivileged workload user |
| [`agent`](#agent) | alias of shell |
| [`export`](#export) | save ~/out as an opaque tar.gz on the host (never extracted) |
| [`put`](#put) | copy one host file to a new path under /home/appsec |
| [`logs`](#logs) | print the recent policy log (allowed and denied connections) |
| [`status`](#status) | print sbx's description of the VM (sbx inspect) |
| [`stop`](#stop) | kill switch: remove the credentials, stop the VM and its reproducers |
| [`repro-create`](#reprocreate) | create an offline reproducer VM from this primary's clean template |
| [`reset`](#reset) | DELETE the VM's current state and recreate it from the clean template |
| [`destroy`](#destroy) | remove the VM and its reproducers entirely |
| [`admin`](#admin) | root maintenance shell (outside the workload boundary) |

### create

Create the sandbox VM, bootstrap the harness, lock the network policy to the provider's endpoint plus the chosen package registry, and save a clean template that `reset` and `repro-create` start from. Takes a few minutes. Provider and harness are fixed for the life of the VM: to change them, `destroy` and `create` again.

```text
usage: appsec-sbx create [-h]
                         [--provider {anthropic,claude-code,codex,deepseek,openrouter} |
                         --endpoint HOST:PORT] [--key-var NAME]
                         [--harness {opencode,claude-code,codex}]
                         [--registry NAME|HOST:PORT | --no-registry]
                         [name]

positional arguments:
  name                  name for the new sandbox (default appsec-sbx)

options:
  -h, --help            show this help message and exit
  --provider {anthropic,claude-code,codex,deepseek,openrouter}
                        model provider preset; decides the allowlist, the key variable
                        and the default harness (default openrouter)
  --endpoint HOST:PORT  one exact model endpoint instead of a preset; needs --key-var
  --key-var NAME        with --endpoint: environment variable the harness reads the
                        key from
  --harness {opencode,claude-code,codex}
                        agent harness installed by the bootstrap (default follows the
                        provider: claude-code for the Claude seat, codex for Codex,
                        otherwise opencode)
  --registry NAME|HOST:PORT
                        package registry the workload may reach; repeatable; a name
                        (npm, pypi) or an exact HOST:PORT such as an organisation
                        mirror (default npm)
  --no-registry         allow no package registry at all
```

### verify

Check the mounts, published ports, policy and MCP inventory the wrapper requires, then print the guest's tool versions and the result of its runsc probe. Run it after `create` and whenever a run behaves unexpectedly.

```text
usage: appsec-sbx verify [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### import

Copy the tracked working-tree contents of a Git checkout (edits included, no Git metadata) into the guest. Untracked files, .env*, common credential files and agent or editor configuration directories are excluded; symlinks, hardlinks, special files and traversal paths are rejected; limits are 64 MiB per file and 512 MiB in total. A manifest with per-file SHA-256 values is written beside host state (import.json). An existing target is kept unless --replace is given.

```text
usage: appsec-sbx import [-h] [--replace] [name] source

positional arguments:
  name        sbx sandbox name (default appsec-sbx)
  source      path of the Git checkout on the host

options:
  -h, --help  show this help message and exit
  --replace   remove an existing ~/target/source first (harness state, ~/out and the
              key stay)
```

### skills

Install the immediate subdirectories of a Git checkout that contain a SKILL.md into the selected harness's user-level skills directory; everything else in the checkout is skipped and counted. Records the checkout's commit, a dirty flag and per-file hashes beside host state (skills.json). Skill names use lowercase letters, digits and single hyphens. Names already installed are refused unless --replace is given. GitHub URLs are fetched into a temporary host checkout; --ref defaults to main and --subdir selects the pack directory. Records the URL, requested ref and resolved commit. The guest needs no GitHub access. Private repositories require a local checkout.

```text
usage: appsec-sbx skills [-h] [--ref REF] [--subdir SUBDIR] [--replace] [name] source

positional arguments:
  name             sbx sandbox name (default appsec-sbx)
  source           local pack directory or public https://github.com/OWNER/REPO URL

options:
  -h, --help       show this help message and exit
  --ref REF        GitHub branch, tag or commit (default: main); URLs only
  --subdir SUBDIR  pack directory within the GitHub repository (default: root); URLs
                   only
  --replace        overwrite skills of the same name
```

### key

Read the key from the environment variable named by the provider profile, or prompt for it without echo, and write it to a tmpfs file the workload can read but not modify. The file disappears when the VM stops, including sbx's idle stop about a minute after the last session ends, so `shell --key` (place the key, then enter) is the usual form.

```text
usage: appsec-sbx key [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### unkey

Delete the tmpfs key file and the harness credential stores on the workload user's home (Claude Code, Codex, OpenCode). Running processes keep tokens they already hold; revoking a key or seat at the provider is a separate action.

```text
usage: appsec-sbx unkey [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### exec

Run a single command as the unprivileged workload user and return its exit status. Write the command after `--`. An exec that stays open (for example `-- sleep 7200`) counts as a session and keeps the VM from stopping during an unattended run.

```text
usage: appsec-sbx exec [-h] [--key] [name] ...

positional arguments:
  name        sbx sandbox name (default appsec-sbx)
  command     the command, written after --

options:
  -h, --help  show this help message and exit
  --key       place the provider key first (as `key`), then enter; for exec, write it
              before the name
```

### shell

Enter the VM as the workload user (no sudo, no Docker, clean environment) in ~/target/source. The VM stops itself about a minute after the last session ends and takes the tmpfs key with it, so --key is the normal way to enter for a run.

```text
usage: appsec-sbx shell [-h] [--key] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
  --key       place the provider key first (as `key`), then enter; for exec, write it
              before the name
```

### agent

Same as `shell`.

```text
usage: appsec-sbx agent [-h] [--key] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
  --key       place the provider key first (as `key`), then enter; for exec, write it
              before the name
```

### export

Archive the workload's ~/out directory into a new file on the host. The wrapper does not extract or inspect it: treat the archive as untrusted output and open it in an empty directory with a tool that executes nothing.

```text
usage: appsec-sbx export [-h] [name] archive

positional arguments:
  name        sbx sandbox name (default appsec-sbx)
  archive     path of the new archive on the host (must not exist)

options:
  -h, --help  show this help message and exit
```

### put

Copy a single host file into the guest. The destination must be an absolute path under /home/appsec/ that does not exist yet; directories and traversal are refused.

```text
usage: appsec-sbx put [-h] [name] source destination

positional arguments:
  name         sbx sandbox name (default appsec-sbx)
  source       host file
  destination  absolute guest path under /home/appsec/ that does not exist yet

options:
  -h, --help   show this help message and exit
```

### logs

Print the last 30 entries of sbx's policy log for this sandbox: which hosts the workload reached and which requests the profile denied, with timestamps.

```text
usage: appsec-sbx logs [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### status

Print `sbx inspect` for this sandbox as JSON: state, sessions, resources, identifiers.

```text
usage: appsec-sbx status [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### stop

Stop the reproducer VMs created through this primary, remove the key file and harness login stores from a running primary, then stop it. Disk contents stay; nothing is revoked at the provider.

```text
usage: appsec-sbx stop [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### repro-create

Create a second VM from the primary's clean template (tools installed, nothing imported) with no network at all and no model key, recorded as a reproducer of this primary so that `stop` and `reset` include it. Use `import`, `shell`, `exec` and `export` on it under its own name; `key` refuses it.

```text
usage: appsec-sbx repro-create [-h] [name] new_name

positional arguments:
  name        name of the primary VM (default appsec-sbx)
  new_name    name for the new reproducer VM

options:
  -h, --help  show this help message and exit
```

### reset

Remove the primary and its recorded reproducers, then create the primary again from the template saved by `create`. The installed tools stay; the imported target, ~/out, installed skills, harness state and login stores are gone. `export` first, run `skills` again afterwards.

```text
usage: appsec-sbx reset [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### destroy

Remove the primary and its recorded reproducers from sbx. The host state directory and the saved template are kept.

```text
usage: appsec-sbx destroy [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```

### admin

Enter the VM as root for trusted setup work. Nothing done here is contained by the workload boundary; do not run the agent from it.

```text
usage: appsec-sbx admin [-h] [name]

positional arguments:
  name        sbx sandbox name (default appsec-sbx)

options:
  -h, --help  show this help message and exit
```
