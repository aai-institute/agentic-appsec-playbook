---
title: "Skills"
description: "How the review prompt and third-party skill packs enter the guest."
---

The bootstrap installs no prompt content. Instructions enter through one action, `skills`,
which installs a skill pack from a host Git checkout: this repository's review prompt
([`sandbox/skills/security-review-repo`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/sandbox/skills/security-review-repo),
adapted from Anthropic's MIT-licensed [`security-review` command](https://github.com/anthropics/claude-code-security-review) with the diff scoping removed) and third-party packs
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
