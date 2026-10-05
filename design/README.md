# Design notes

Maintainers' working documents: the reasoning behind the user-facing material in
[`docs/`](../docs/), with dates, probes and rejected alternatives. Read them to check a claim
or to change the sandbox; operate the tools from the [site](../docs/src/content/docs/) instead.

| Document | What it settles |
|---|---|
| [docs-review-checklist.md](docs-review-checklist.md) | Running checklist from the September 17 critical reading pass, with issue numbers, affected pages and resolution notes |
| [documentation-notes.md](documentation-notes.md) | Editorial conventions, page maturity and unpublished research provenance; kept outside the published site |
| [Threat model](../docs/src/content/docs/sandbox/threat-model.md) | Public overview, threat catalogue (`T01` …), control coverage (`M1` …) and acceptance requirements (R1 to R8). Cite a `T` row and register an `M` entry before changing any sandbox script |
| [sandbox-backlog.md](sandbox-backlog.md) | Remaining sbx implementation and validation work, with completion criteria; replaces the threat model's versioned implementation plan |
| [sandbox-comparison.md](sandbox-comparison.md) | The Colima prototype, Docker `sbx` and eight open alternatives mapped to the acceptance contract; platform suitability; the acceptance probes a backend has to pass |
| [openshell-evaluation.md](openshell-evaluation.md) | NVIDIA OpenShell read at source on 2026-09-23: components, compute drivers and their boundaries, policy and provider model, the wrapper's sbx contract mapped to OpenShell verbs, drift since the comparison, and four integration options (backend, inner layer, M17 design reference, shared service) with first probes |
| [sbx-kits-for-skills.md](sbx-kits-for-skills.md) | Whether sbx kits (v2, v3 mixins, the shared skills store) can take over skill loading from `appsec-sbx skills`, assessed 2026-09-30: shared store rejected on T01/T23, v3 needs a builder and registry, recommendation is the playbook skill in the wrapper's v2 kit (M27) with v3 as an evaluation (M28) |
| [sbx-docker-profile.md](sbx-docker-profile.md) | Design of 2026-10-05 for `create --docker` (issue #15, M26): rootless Docker for the workload, the guest probe behind it (container egress under sbx policy, data root, per-boot start, shared memory cap), Strix, PentAGI and Mantis requirements, the decisions taken, T08/T18 changes and the implementation plan |
| [sbx-internals.md](sbx-internals.md) | Why the `appsec-sbx` wrapper does what it does: provider presets and the harness investigations, the idle-stop finding, proxy-managed credentials (M17), the reproducer boundary, the admission and transfer contract, the effective-policy narrative, portability |
| [sbx-managed-credentials.md](sbx-managed-credentials.md) | sbx's proxy-managed credentials probed on 0.46.0 (2026-10-02): kit declaration, bindings file, injection and header override, revocation, removal with the VM; the basis of M17 in wrapper 0.4.0, with the remaining risks |
| [reference-sandbox-colima.md](reference-sandbox-colima.md) | The frozen v0 reference implementation on Colima/Lima (macOS) with its self-certification checklist; the scripts are `sandbox/make-appsec-vm.sh` and `sandbox/bootstrap-appsec-vm.sh` |
| [ci-runner-design.md](ci-runner-design.md) | Design for a hardened GitHub Actions job that reviews PR diffs with an agent (design only) |
| [working-group.md](working-group.md) | The appliedAI working group this material was written for: release rule, schedule, provenance, sharing rules |

Evidence from running the wrapper on real hosts is in [`records/`](../records/).
