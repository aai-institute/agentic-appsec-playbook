# Can sbx kits take over skill loading from `appsec-sbx skills`?

**Status:** assessment, 2026-09-30, no script change. Host: macOS, `sbx version` = v0.46.0
(991967dc), wrapper at `main` 0b33c88. Only read-only sbx commands ran; the v3 probe was
built with host `docker buildx` (29.8.1 / buildx 0.37.1), never with the sbx daemon, and its
files are not kept in the repository. Companion to [sandbox-comparison.md](sandbox-comparison.md)
and the skills sections of [sbx-internals.md](sbx-internals.md).

Tags: `verified-at-source` (docs, spec or release note read), `checked` (command run here),
`not-found` (looked for, not established).

Sources read: docs.docker.com/ai/sandboxes/{customize/, customize/use-kits/, customize/author/,
customize/author/kit-sets/, customize/kits-v2/, workflows/agent-skills/, security/};
github.com/docker/sandbox-kit-spec at v3.0.0-m.6 (2026-09-24): `docs/spec/SPEC-v3.md`,
capability pages `agent-skills@1`, `agent-context@1`, `lifecycle@1`, `network-policy@2`,
`kit-registry@1`, `examples/{claude-mixin,gh,hello,motd,tool}`, `skills/create-kit-v3/SKILL.md`;
`gh api repos/docker/sbx-releases/releases` v0.39.0 (08-19) to v0.46.0 (09-28);
github.com/snyk/evo-ads-sbx-kit `spec.yaml` at 0a1db8cf (09-17).

## 1. What sbx offers today

### Shared skills store and `--skills`

- Host store, one per daemon: `~/Library/Application Support/com.docker.sandboxes/sandboxes/agent-skills`
  on this Mac, currently empty (`sbx skills ls --json`, checked). Filled by `sbx skills add
  <git-url|owner/repo> [--skill name]` and `sbx skills import` (host `~/.agents/skills`,
  `~/.claude/skills`, `~/.config/opencode/skills`, `~/.copilot/skills`, `~/.cursor/skills`,
  `~/.factory/skills`, first copy wins) (checked, `--help`). `add` has no ref or commit flag;
  `update` "downloads the latest versions" (checked). Whether `ls --json` records a commit:
  not-found (store empty).
- `sbx create --skills off|readonly|readwrite` (checked, `create --help`): `readonly` links
  the store entries read-only into the agent's skills directory and "the directory stays
  writable"; `readwrite` mounts the store over the directory so the sandbox's writes are
  shared; `off` mounts nothing. Default `readonly`, or `skills.defaultMode` (checked:
  `readonly` on this host). Linking happens at container start; the mode is fixed at
  creation (`sbx skills --help`, checked; agent-skills docs page, verified-at-source).
- Where each agent reads the store (docs page, verified-at-source): Claude Code
  `/home/agent/.claude/skills`; Codex and Devin `/home/agent/.agents/skills`; Copilot,
  Cursor, Droid under their own homes. OpenCode is named as a supported import target
  (checked, `import --help`) but has no row in the docs table: not-found. The wrapper's
  Codex path is `~/.codex/skills`, which Codex also reads (records, 2026-09-11); the
  published Codex v3 kit creates `~/.agents` for "the cross-agent skills tree" (checked,
  `kit inspect docker.io/docker/sbx-kit-codex:0.155.1 --json`).
- The security page (verified-at-source): the store is "a narrow exception to cross-sandbox
  isolation"; a `readwrite` sandbox can change what a `readonly` sandbox later reads.
  The spec adds that a runtime "MUST NOT treat the store's contents as trusted input"
  (`agent-skills@1`, verified-at-source).
- 0.46.0 (2026-09-28, verified-at-source): "Kits can install files in the agent's skills
  directory when shared skills are read-only. The shared skills store remains read-only,
  while kit installation and startup commands can write their own skills."

### Kits, v2

- Descriptor `spec.yaml`, `schemaVersion: "2"`, `kind: sandbox|mixin`. Files ship from
  `files/home/` (to `/home/agent/`) and `files/workspace/`, written at creation as uid 1000;
  `setup.install` commands run once at create (root unless `user` says otherwise);
  `setup.startup` every start; `setup.files` written at start; `permissions.network.allow`;
  `agentInstructions.content`, written for a mixin to `kits-memory/<kit>.md` with a pointer
  in the base AI file; `args`, `extends`, `requires.agent` (kits-v2 page, verified-at-source).
  The page names `files/workspace/.claude/skills/<NAME>/SKILL.md` as the place for Claude
  Code skills in a v2 kit (verified-at-source).
- Kit install commands "run with root privileges inside the sandbox"; installs are limited
  to `kit.allowedSources`, default Docker Hub (security page, verified-at-source; checked:
  `["docker.io/"]`, `kit.allowLocalKits true`, `kit.requireSignature false`).
- Signing and provenance: `sbx kit sign|verify|provenance`, `kit.trustedSigners`,
  `kit.requireSignature` (0.39.0 note and use-kits page, verified-at-source). Git kits pinned
  by commit resolve from a content-addressed cache with per-file manifest checks; signed git
  kits are materialised from blobs so host git config cannot alter bytes (0.43.0,
  verified-at-source; the same class of fix the wrapper's `git_source.py` carries).
- The wrapper's kit: `kind: sandbox`, schema v2, template `docker/sandbox-templates:shell-docker`,
  no policies, no files (checked, `kit validate` valid, `kit inspect`). Snyk's mixin is v2:
  `agentInstructions.content`, `permissions.network.allow`, six `setup.install` steps
  (root and uid 1000) that download binaries at create, one background `startup` loop,
  `files/home/` (checked, spec.yaml at 0a1db8cf).

### Kits, v3 (sbx >= 0.45.0, 2026-09-21)

- One OCI image per kit; the descriptor rides as a manifest annotation; sources are staged
  at `/usr/share/sandbox/kit/<stem>/kit.yaml` and `kit.dockerfile` (SPEC §10,
  verified-at-source; checked in the probe output below). `kind: workload|mixin|set`.
  A mixin is an overlay landing on a workload; it may be declaration-only.
- Capabilities are typed requests: `network-policy@1|@2` with separate `install` and
  `runtime` phases, `@2` bounding hosts by HTTP `methods` and `paths`; `credential@1` by
  phase; `lifecycle@1` (install once at create, root by default, env deny-by-default,
  "hold the network policy's install phase open while install hooks run and close it before
  the entrypoint starts"; `files` written at start, owned by the agent); `agent-context@1`
  (`contentFile` or inline `content`; `filename` is workload-only); `agent-skills@1`
  (`path` where the agent reads the shared store, `mode` default `readonly`, effective
  access is the narrower of host setting and kit mode; a required entry refuses to start
  when the host is `off`); `kit-registry@1`, the only route to the runtime's kit registry,
  "the typed request literally is the enforcement" (all verified-at-source).
- Docker's own guidance for shipping skills in a kit: declare `agent-skills@1` "only where
  the agent really reads skills from that path, and never where the kit ships content
  there — the mount would hide it" (`create-kit-v3/SKILL.md`, verified-at-source). So a kit
  that ships `SKILL.md` files copies them into the directory by Dockerfile `COPY` or an
  install hook, and leaves the store declaration out for that path.
- Pinning: a set's members carry `ref` plus `digest` ("REQUIRED when published"); local
  paths and git URLs are refused as set members (SPEC §3.4, verified-at-source). `kit
  inspect` resolves a published v3 kit to `@sha256:…` (checked, codex 0.155.1). Consumers
  that gate updates diff the permission surface; any widening "MUST stop for approval"
  (SPEC §7.4, verified-at-source).
- v3 cannot mix with v1/v2 in one sandbox; the built-in `claude`, `codex` and `opencode`
  agents are v2 (customize page and 0.45.0 note, verified-at-source). `sbx kit add` cannot
  add mixins to an existing v3 sandbox (use-kits page, verified-at-source). `sbx create`
  takes `--kit <ref>` repeatedly, "must be a mixin; directory, ZIP, git, or OCI" (checked).
- Local v3 builds: `sbx kit validate ./appsec-skills` (companion pair) fails with "is a v3
  source kit and this load path has no kit builder configured" (checked). Source-form
  builds run inside a shared builder sandbox `sbx-kit-builder`, created on first use, whose
  engine store is the build cache (checked, `kit builder --help`; not run). The 2026-09-22
  record's `supported: [1 2]` error came from a v2 `spec.yaml` layout carrying
  `schemaVersion: "3"`; 0.46.0 gives the same error for that layout (checked) and the
  builder error for the v3 layout. The 09-22 record also saw a host kit-registry listener
  at 127.0.0.1:5411 reported by `kit builder status`; not re-run here.
- Host-side build without sbx: `docker buildx build -f appsec-skills.yaml --output
  type=local` through the `docker/sandbox-kit:3` frontend accepted the descriptor and
  produced `/home/agent/.claude/skills/security-review-repo/SKILL.md` plus the staged
  `kit.yaml`/`kit.dockerfile` (checked; probe files kept outside the repository).
  Ownership trap: `COPY --chown=1000:1000` also chowns every parent it creates, so `/home`
  ends up uid 1000; the spec's `overlay-home-ownership` check fails that (RECIPES.md,
  verified-at-source). The probe Dockerfile has this bug and is not shippable as is.
- Kit content lands under `/home/agent` (platform floor: user `agent`, uid 1000). The
  wrapper's workload user `appsec` and `/home/appsec` are created by `bootstrap.sh` after
  `sbx create` returns (line 29), so no kit phase can write the wrapper's skill directories
  directly; the bootstrap would have to copy from a kit-staged path (checked, code read).

## 2. What the wrapper does today and why

- `create` passes `--skills off` (M25, T01): no host store reaches the guest, so a store
  filled on the host by other work, or made `readwrite` by another sandbox, cannot inject
  instructions (`lifecycle.create_command`; catalogue T01 "creation omits workspace and
  skill shares").
- `skills <vm> <source>` is the only admission path for instructions; the bootstrap installs
  no prompts (sbx-internals §"Admission and transfer contract"; memory note 2026-09-11).
  Source is a local Git checkout or a public `https://github.com/OWNER/REPO` URL fetched on
  the host into a disposable repository with no inherited Git config, `protocol.allow=never`
  except HTTPS, redirects off, depth 1, no tags, no submodules; symlinks and submodules in
  the index are refused before checkout; attributes are overridden so no smudge, EOL or
  ident filter changes bytes (`git_source.fetch_checkout`). Only immediate subdirectories
  holding `SKILL.md` are packed; anything else is listed as skipped; the import exclusion
  filter applies (`transfer.pack_skills`). The guest never contacts a code host.
- Per-harness install: `~/.config/opencode/skills`, `~/.claude/skills`, `~/.codex/skills`
  as `appsec`, over `sbx exec -i` binary stdin with timeouts; existing names refuse unless
  `--replace` (`lifecycle.install_skills`).
- Record: `skills.json` beside host state with source, requested ref, resolved commit,
  dirty flag, harness, directory and per-file SHA-256 (M7/M14; R5 "skills enter by operator
  choice with recorded origin"; R8 evidence).
- T rows answered: T33 (unsafe pack instructions or scripts), T24 (installation runs code),
  T01/T06 (no host store or identity share), T10 (manifest outside the workload). Known
  limits (controls M14, backlog): moving refs, guest-writable skills, no fetch size cap,
  SHA-shaped `--ref` not compared with the resolved commit (backlog M14, 2026-09-17).

## 3. Options

### (a) Keep the wrapper's `skills`, no change

Gains: nothing new to trust; symlink/submodule/filter defences and the host record exist
and are exercised (Mantis, Defending Code, playbook skill on all three harnesses).
Loses: a create needs a second step; participants type a URL per pack; no OCI digest.
Risk: none new. First probe: none.

### (b) Carry the playbook skill in the wrapper's own v2 kit image

Descriptor sketch (the kit spec, which wrapper 0.4.0 renders per VM in `credentials.render_kit`, plus `files/home/.appsec/skills/…`):

```yaml
schemaVersion: "2"
kind: sandbox
name: appsec-shell
sandbox: {image: docker/sandbox-templates:shell-docker, entrypoint: [bash, -l]}
# files/home/.appsec/skills/security-review-repo/SKILL.md -> /home/agent/.appsec/skills/…
```

The bootstrap copies `/home/agent/.appsec/skills` into the harness directory of `appsec`
and the wrapper writes the same `skills.json` entry from the checkout it created from.
Gains: prompt-free create with the skill present; no host Git fetch for the playbook pack;
the pack travels with the wrapper version. Loses: the per-commit record becomes "the
wrapper's own checkout", which is what `create` already records for the bootstrap; the
"bootstrap installs no prompts" invariant (sbx-internals, memory 2026-09-11) is dropped and
T33's "instructions enter by one operator action" narrows to "by the operator's choice of
wrapper version". No new host listener, no registry, no builder: files ship from the local
kit directory, which `kit.allowLocalKits` (true here) permits. Third-party packs still need
`skills`. Risk: kit files are written as uid 1000 into `/home/agent`, readable by `agent`,
which the bootstrap already treats as the administrative home; harmless for a public
prompt. First probe: add the file, `sbx kit validate`, one create, verify the copy and hash.

### (c) A v3 mixin per skill pack, composed at create

Requires a v3 workload: the wrapper's shell kit would move to v3 (`kind: workload`, `sbx@1`,
`agent-context@1 filename`), because v3 mixins cannot join a v2 sandbox kit. Sketch, as
built in the probe:

```yaml
# syntax=docker/sandbox-kit:3
schemaVersion: "3"
kind: mixin
version: "0.1.0"
provides: ["appsec-review-skills@0.1.0"]
capabilities:
  - type: com.docker.sandbox/agent-context@1
    config: {content: "The security-review-repo skill reviews the imported target."}
# appsec-skills.dockerfile: FROM scratch; COPY files/skills/ /home/agent/.appsec/skills/
```

`sbx create ./kit --kit docker.io/<ns>/appsec-review-skills@sha256:…`. Gains: OCI digest
pinning and signatures (`kit sign`, `kit.requireSignature`, `kit.trustedSigners`); a pack
as an immutable artifact participants pull by one reference; install-phase network closed
before the agent starts; no host checkout. Loses and risks:
- New supply chain: BuildKit frontend `docker/sandbox-kit:3` (floating tag), a registry
  namespace someone must own and be able to push to, and either the `sbx-kit-builder`
  sandbox with its host registry listener (127.0.0.1:5411 in the 09-22 record; R2 "no
  implicit guest listeners on the host") or host `docker buildx`. `kit.allowedSources`
  defaults to `docker.io/`, so a GHCR reference needs an `sbx settings set`, a host
  configuration change the wrapper does not make today (M25 scope).
- Third-party packs (Mantis, Defending Code) would have to be repackaged by the playbook,
  which moves the review-and-pin duty from the participant's `--ref` to a maintainer's
  build; the per-file hash record would come from the build, not the guest.
- Kit content still lands in `/home/agent`; the bootstrap copy remains.
- `sbx kit add` cannot add mixins to a v3 sandbox after create, so late installs need
  `skills` anyway; `--skills off` still holds (the mixin declares no `agent-skills@1`).
- A v3 workload kit changes what `template save` snapshots, the reproducer path (R6) and
  the whole acceptance matrix; entry guards read `inspect --json` fields that may differ.
First probe: build the probe with the ownership fix (`chown` starting at `/home/agent`),
push to a throwaway namespace, run the spec `tck` overlay check; only then a create on a
non-demo host.

### (d) Shared store in `readonly` instead of `off`

`sbx skills add <repo>` on the host, `--skills readonly` at create. Gains: one host command,
live edits through the link, Docker-maintained. Loses: no commit pin in `add`; `update`
moves to latest; the store is shared with every sandbox on the host and writable from any
`readwrite` sandbox, which reintroduces T01/T06 (host store leakage) and T23 (state carried
between runs) that `--skills off` closes; the store mounts at Docker's per-agent paths under
`/home/agent`, not under `/home/appsec`, so the wrapper's harnesses would not see it without
a further link; OpenCode's path is undocumented. Record would be `sbx skills ls`, outside
`skills.json`. Rejected on the threat model as it stands. First probe: none.

### (e) Hybrid: kit for the playbook pack, `skills` for third-party packs

(b) now, (c) later if v3 stabilises. The playbook's own prompt arrives with the wrapper
version; participants' packs keep the host fetch, filter and record. The single-path
invariant becomes "two admitted paths, both recorded in `skills.json`".

## 4. Recommendation

Adopt (e) with (b) as the only script change now; keep (c) as a tracked evaluation, not a
migration. Rationale: v3 is nine days old on the release channel, the spec is at milestone
m.6 with a stable target of Q4 2026, `sbx kit validate` cannot check a v3 source kit without
the builder sandbox, and every v3 gain (digest, signature) buys the playbook's one public
prompt little while costing a registry, a builder and a rewrite of the workload kit that
the acceptance matrix has not seen. (d) contradicts T01/T23.

Before any script change, register in `design/threat-model.md` and the controls page:

- **M26** Playbook skill shipped in the wrapper's kit image, copied by the bootstrap into
  the harness skills directory of `appsec`, recorded in `skills.json` with the wrapper's
  commit and file hash. Answers T33 (origin is the wrapper checkout), T10/R8 (record).
  Limit: the "bootstrap installs no prompts" statement in sbx-internals, docs
  `sandbox/sbx/skills.md` ("The VM starts without review skills") and
  `discovery/review-skills.md` change; guest copy remains workload-writable (M14 limit).
- **M27** (evaluation only) v3 kit packaging: names the frontend image, registry namespace,
  signer identity, builder sandbox and its listener as inputs; ties to T28 (compromised
  install source), T11 (install-phase egress), R2 (host listener), R7 (provisioning inputs
  by digest). No script change until a record exists.

Acceptance rows touched by (b): R1 (mount inspection unchanged; kit files are not a mount),
R5 (skill store contents at reset: the template now contains the skill, so "clean reset"
means "wrapper skill present, nothing else"), R7 (provisioning inputs: kit files are part of
the wrapper's own checkout), R8 (evidence: `skills.json` entry written at create). R3, R4, R6
unaffected. Rows touched by (c) in addition: R2, R3 (install-phase grants), R6 (reproducer
template).

## 5. Open questions and what was not verified

- Whether `sbx skills ls --json` records a source commit for `add`-installed skills
  (store empty here).
- OpenCode's store path in the shared-skills mount; the docs table omits it.
- Whether 0.46.0 still reports the 127.0.0.1:5411 listener without a builder sandbox
  (`kit builder status` not run; read-only rule).
- Whether kit `files/home/` in a v2 `kind: sandbox` kit are applied when the template is a
  plain shell image without an agent profile (docs describe agent images; not run).
- Whether the `docker/sandbox-kit:3` frontend tag is what sbx's builder uses, and its digest.
- The spec's `FIELD-MAPPING.md` (v2 to v3) was not read; `create-kit-v3/SKILL.md` covered
  the skills rule.
- No `sbx create`, `kit add`, `kit builder` or template operation ran; every runtime claim
  above is from docs, spec, release notes or code, not from a sandbox.
