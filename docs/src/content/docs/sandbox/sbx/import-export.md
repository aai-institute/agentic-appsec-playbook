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

## Copy a single file

Use `appsec-sbx put` to copy an extra file into the VM, such as notes defining
the scope of a review. From the host, with `review-notes.md` in your current
directory:

```sh
appsec-sbx put appsec-sbx ./review-notes.md /home/appsec/review-notes.md
```

The destination must be a new file at an absolute path under `/home/appsec/`.
The command refuses directories, traversal paths and existing targets. The
file does not need to be tracked by Git. Check its contents before copying:
the agent can read it and send it to allowed services.

For skill packs, use the [skills installer](/sandbox/sbx/skills/).

## Export

Export archives `~/out` inside the VM and copies the result to a new host
file. The filename selects the format, regardless of the host OS:

```sh
appsec-sbx export appsec-sbx ./findings.zip
# Or, for gzip-compressed tar:
appsec-sbx export appsec-sbx ./findings.tar.gz
```

Use `.zip`, `.tar.gz` or `.tgz`; suffixes are case-insensitive. Other suffixes
are rejected. ZIP works with File Explorer on Windows and needs no additional
guest package. It includes regular files and directories, including empty
directories, and rejects symlinks and special files. Use tar if you need to
preserve Unix file metadata or symlinks.

Choose a new filename for every export. Existing files are never overwritten;
a failed export removes its incomplete output so you can retry.

The wrapper **never extracts the archive on the host**. For ZIP, inspect its
contents with an archive viewer such as File Explorer, then extract into a
new, empty directory. For tar, list with `tar -tzf` before extracting into a
new, empty directory.

Archive contents are agent-generated. The wrapper does not check them for
unsafe content or remove characters that can control a terminal. Review them
with a viewer that does not execute content; do not print raw report text to a
terminal or feed it into another agent before human review. Assess findings
and patches before acting on them, and redact sensitive details before sharing.

## Host state

The wrapper stores its VM records under
`~/.local/state/agentic-appsec/sbx/NAME` on the host. These records include
VM identifiers, template names, the expected network policy, and lists of
imported files and installed skills. They do not contain model keys.

Set `APPSEC_SBX_STATE` to use another directory, and use the same value for
every wrapper command. Do not edit the records to bypass a failed safety
check.
