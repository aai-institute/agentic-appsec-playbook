---
title: "Skill installation"
description: "Command syntax, file selection, installation paths and updates for skill packs."
---

`appsec-sbx skills` installs instruction packs from a local Git checkout or
public GitHub URL. The VM starts without review skills. For specific packs
and how to use them, see [Review skills](/discovery/review-skills/).

## Install a pack

`appsec-sbx skills <vm> <source>` accepts a local Git checkout, a directory
inside it, or a public `https://github.com/OWNER/REPO` URL. URL imports fetch a
temporary checkout on the host and remove it after packing, including on
failure. The guest's run allowlist still blocks GitHub.

System Git must be installed and available on `PATH`. Before touching the
sandbox, the wrapper checks `git --version` with a 10-second timeout and
stops with installation guidance if Git is unavailable or fails the check.

For a URL, `--ref` defaults to `main` and accepts a branch, tag or commit. If
the repository has no `main`, supply its branch with `--ref`. The wrapper
records both the requested ref and the resolved commit. Use that commit for
`--ref` when repeating a run; branch and tag names can move.

Private repositories, SSH URLs and other Git hosts require a local checkout.
URL imports ignore host Git configuration, including credential helpers and
URL rewrites; Git redirects are disabled. Use the repository's current URL.
Each fetch or checkout command has a 120-second timeout. The later import
size limits do not bound the size of the Git download or checkout.

Pass the directory whose immediate children contain `SKILL.md`. The command
does not search deeper or install one selected skill from a pack. For a URL,
select the pack directory with `--subdir <path>`; the default is the repository
root. For a local checkout, pass the pack's full path. `--ref` and `--subdir`
apply only to URLs.

The wrapper copies tracked files inside each skill directory, including support
files that pass the import filter. Files outside those directories are skipped
and counted. Installation does not run the pack's scripts, but a skill may ask
the agent to use them later. Review the pack before installing it.

Local checkouts must have a commit. Tracked local edits are included; untracked
files are omitted. The wrapper records the commit, a dirty flag and per-file
hashes beside host state in `skills.json`. Use a clean checkout at a fixed commit
to make the run repeatable.

The command reports preparation, upload and installation progress. It sends
the archive through `sbx exec -i` using binary stdin. Upload, collision checks
and extraction each have a 120-second timeout. On failure, no success record
is written; cleanup is attempted for up to 15 seconds and warns if it fails.
If a step times out, check `sbx diagnose` and
`sbx exec -u root <vm> true` before retrying.

From `sandbox/sbx` in a playbook checkout, use `uv run appsec-sbx` in place of
`appsec-sbx` in these examples. The destination is the harness's user-level
skills directory:

| Harness | Skills directory in the guest |
|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` |
| Codex | `~/.codex/skills/<name>/SKILL.md` |
| OpenCode | `~/.config/opencode/skills/<name>/SKILL.md` |

Invoke a skill in Claude Code with `/<name> [focus]`, or in Codex with
`$<name>` in the composer. In OpenCode, type `/<name>`, then Space, then
Enter, or ask the model to load the skill by name.

OpenCode 1.18.29–1.18.31 hide skills from slash autocomplete.
Type the full skill name yourself. The trailing space closes autocomplete so
Enter can submit the command. For example, type `/security-review-repo`, press
Space, then Enter, or submit `/security-review-repo this repo`.
You can also ask: "Load the security-review-repo skill and review this repository."

### Check OpenCode discovery

After installing skills, restart OpenCode if it was already running. From
the same VM shell where you launch it, check:

```sh
whoami
echo "$HOME"
opencode --version
opencode debug skill
```

The wrapper's workload user is `appsec`, with home `/home/appsec`.
`opencode debug skill` should include `security-review-repo` and its path.
If it does, installation and parsing worked; use either invocation above.
If it does not, check that `SKILL.md` is readable by `appsec` and starts with
valid YAML containing `name` and `description`. Check custom skill permissions
if discovery succeeds but the agent cannot use it.

## Update an installed pack

Updating the host checkout does not update the guest. Fetch on the host, select
the new commit, then import again with `--replace`:

```sh
git -C /path/to/skill-repository fetch origin
git -C /path/to/skill-repository checkout --detach <reviewed-commit>
appsec-sbx skills appsec-sbx /path/to/skill-repository/path/to/skills --replace
```

For a URL source, repeat the install with `--replace` and, if needed, `--ref`:

```sh
appsec-sbx skills appsec-sbx https://github.com/OWNER/REPO --subdir path/to/skills --ref <reviewed-commit> --replace
```

Without `--replace`, an existing skill name stops the install. With it, each
incoming skill directory is replaced, including local edits in the guest.
Skills omitted from the new pack remain installed. Restart your agent
session before using the updated skills and record the new commit.

`skills --replace` changes skills; `import --replace` replaces the target source.
After a VM reset, install the skills again.
