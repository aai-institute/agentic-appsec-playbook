---
title: "Skills"
description: "How the review prompt and third-party skill packs enter the guest."
---

The bootstrap installs no prompt content. Instructions enter through one action, `skills`,
which installs a skill pack from a local Git checkout or public GitHub URL: this repository's review prompt
([`sandbox/skills/security-review-repo`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/sandbox/skills/security-review-repo),
adapted from Anthropic's MIT-licensed [`security-review` command](https://github.com/anthropics/claude-code-security-review) with the diff scoping removed) and third-party packs
alike.

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
does not search deeper or install one selected skill from a pack. For example,
pass `.claude/skills` for the Defending Code Reference Harness. For a URL,
select it with `--subdir .claude/skills`; the default is the repository root.
For a local checkout, pass the pack's full path. `--ref` and `--subdir` apply
only to URLs.

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

| Harness | Skills directory in the guest | Invocation |
|---|---|---|
| Claude Code | `~/.claude/skills/<name>/SKILL.md` | `/<name> [focus]` |
| Codex | `~/.codex/skills/<name>/SKILL.md` | `$<name>` in the composer |
| OpenCode | `~/.config/opencode/skills/<name>/SKILL.md` | model-invoked through its `skill` tool: ask for the skill by name; no slash command |

## Full-repo review skill

Install this playbook's `security-review-repo` skill directly from GitHub:

```sh
appsec-sbx skills appsec-sbx https://github.com/aai-institute/agentic-appsec-playbook --subdir sandbox/skills
```

`sandbox/skills` is the pack directory containing `security-review-repo`.
The wrapper fetches it on the host using a temporary checkout, which is
removed after packing. The guest does not need GitHub access. The default ref
is `main`; add `--ref <commit>` to pin the revision recorded in `skills.json`.

For local edits or a private repository, pass a checkout path instead:

```sh
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
```

## Mantis

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

## Defending Code Reference Harness

Install directly from GitHub using the default `main`:

```sh
appsec-sbx skills appsec-sbx https://github.com/anthropics/defending-code-reference-harness --subdir .claude/skills
```

To use the revision from the completed September 16 Claude Code discovery
run, add `--ref d3bea6b5793b5f3d59a75ebe69a58efa88383145`. That run used a local
skill checkout on sbx 0.43.0 on macOS. Direct URL installation into OpenCode
1.18.29 also passed on that setup: nine skills and 19 files. With GLM-5.3-Flash
through OpenRouter, skill loading, six review tasks, seven scoring tasks and
both report files completed in 45m 19s. The run exceeded its 20-minute budget.
Its low-confidence count and template count were wrong, and usage stats showed
web fetches despite the static-only prompt; the VM denied external hosts.
This validates the import and basic workflow, not full adherence to the skill.

In Claude Code inside the VM, invoke:

```text
/vuln-scan /home/appsec/target/source
```

The command is `/vuln-scan` at this revision. It performs static discovery and
writes `VULN-FINDINGS.json` and `VULN-FINDINGS.md` in the target directory. After
the scan, exit Claude Code and copy both reports into `~/out` from the guest
shell so `appsec-sbx export` includes them:

```sh
cp ~/target/source/VULN-FINDINGS.json ~/target/source/VULN-FINDINGS.md ~/out/
```

Installing the skills does not install the reference harness's autonomous
pipeline or its Docker setup. For the discovery exercise, stop after the raw
reports; triage, reproduction and patching are later stages.

## Update an installed pack

Updating the host checkout does not update the guest. Fetch on the host, select
the new commit, then import again with `--replace`:

```sh
git -C /path/to/defending-code-reference-harness fetch origin
git -C /path/to/defending-code-reference-harness checkout --detach <reviewed-commit>
appsec-sbx skills appsec-sbx /path/to/defending-code-reference-harness/.claude/skills --replace
```

For a URL source, repeat the install with `--replace` and, if needed, `--ref`:

```sh
appsec-sbx skills appsec-sbx https://github.com/anthropics/defending-code-reference-harness --subdir .claude/skills --replace
```

Without `--replace`, an existing skill name stops the install. With it, each
incoming skill directory is replaced, including local edits in the guest.
Skills omitted from the new pack remain installed. Use a fresh Claude Code
session for the next run and record the new commit.

`skills --replace` changes skills; `import --replace` replaces the target source.
After a VM reset, install the skills again.

## Copy another file

`put <vm> <host-file> /home/appsec/<path>` copies one further host file to a new path; it
refuses traversal, directories and existing targets.
