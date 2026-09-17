---
title: "Import, export and host state"
description: "What goes into the VM, what comes out, and where the manifests live."
---

Import accepts a local Git checkout or a public GitHub repository URL.
System Git must be installed and available on `PATH`. The wrapper checks
`git --version` before touching the sandbox and stops if Git fails to run
or does not respond within 10 seconds.

Local imports copy **tracked working-tree contents**, including edits,
without Git metadata:

```sh
appsec-sbx import appsec-sbx /absolute/path/to/your/git-checkout
```

For a public repository, the wrapper fetches a temporary checkout on the host:

```sh
appsec-sbx import appsec-sbx https://github.com/OWNER/REPO --ref main
```

`--ref` accepts a branch, tag or commit and defaults to `main`. Supply another
branch if the repository has no `main`. `import.json` records the repository
URL, requested ref, resolved commit and per-file hashes. Use the recorded
commit as `--ref` to repeat the same revision. The guest receives filtered
files and needs no GitHub access; the temporary checkout is removed after
packing, including on failure.

URL imports accept public GitHub HTTPS URLs only. Private repositories and
other Git hosts require a local checkout. The fetch ignores host Git config,
credentials, hooks and checkout filters. Each fetch or checkout command has
a 120-second timeout. Git download and checkout sizes are not capped by the
archive limits below.

Both forms use the same file filters:
Untracked files, `.env*`, common credential files, `.sbxenv.yaml` and agent/editor
configuration directories are excluded. Symlinks (including parent components), hardlinks,
special files and traversal paths are rejected; limits are 64 MiB per file and 512 MiB total.
Submodules need a separate, explicit import. Target instructions and source remain untrusted
after import.

Imports create `~/target/source` once; `import --replace` swaps the target tree in place
(harness state, `~/out` and the key stay). Before an independent review, use
[`reset`](/sandbox/sbx/lifetime/#reproducers-reset-and-destroy), then import
the target and reinstall the skills. `--replace` is for replacing source
within the same review, including retrying a failed import.

For local imports, a Git worktree
(`git worktree add /tmp/x <ref>`) selects a revision without touching your
working checkout; `--ref` applies only to URLs. The exclusion
list is not a secret scanner: check the manifest (`import.json` beside host state) if the
repository may carry credentials in tracked files.

Preparation, upload and extraction print progress messages. Import sends the
archive through binary stdin to `sbx exec -i`. Upload and extraction each
have a 120-second timeout; staging cleanup is attempted for up to 15 seconds.
Failed imports leave the previous host manifest unchanged. Extraction
failures may leave a partial target directory; use `--replace` to retry once
the underlying error is resolved.

Export produces an opaque tar.gz from `~/out` to a new host file and **never extracts it on
the host**. Its contents are agent-generated and are not sanitised. Review them
with a viewer that does not execute content; do not print raw report text to a
terminal or feed it into another agent before human review. Assess findings
and patches before acting on them, and redact sensitive details before sharing.

Host state defaults to `~/.local/state/agentic-appsec/sbx/NAME` on every OS; set
`APPSEC_SBX_STATE` consistently to select another directory. It holds VM IDs, template
references, the admitted policy, the import manifest and the skills manifest, never keys. Do
not edit it to bypass a failed guard.
