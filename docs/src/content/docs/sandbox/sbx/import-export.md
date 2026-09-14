---
title: "Import, export and host state"
description: "What goes into the VM, what comes out, and where the manifests live."
---

Import copies **tracked working-tree contents**, including edits, without Git metadata.
Untracked files, `.env*`, common credential files, `.sbxenv.yaml` and agent/editor
configuration directories are excluded. Symlinks (including parent components), hardlinks,
special files and traversal paths are rejected; limits are 64 MiB per file and 512 MiB total.
Submodules need a separate, explicit import. Target instructions and source remain untrusted
after import.

Imports create `~/target/source` once; `import --replace` swaps the target tree in place
(harness state, `~/out` and the key stay). A Git worktree (`git worktree add /tmp/x <ref>`)
is the way to import a specific revision without touching your working checkout. The exclusion
list is not a secret scanner: check the manifest (`import.json` beside host state) if the
repository may carry credentials in tracked files.

Export produces an opaque tar.gz from `~/out` to a new host file and **never extracts it on
the host**. Inspect it as untrusted output.

Host state defaults to `~/.local/state/agentic-appsec/sbx/NAME` on every OS; set
`APPSEC_SBX_STATE` consistently to select another directory. It holds VM IDs, template
references, the admitted policy, the import manifest and the skills manifest, never keys. Do
not edit it to bypass a failed guard.
