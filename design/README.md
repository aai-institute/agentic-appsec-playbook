# Design notes

Maintainers' working documents: the reasoning behind the user-facing material in
[`docs/`](../docs/), with dates, probes and rejected alternatives. Read them to check a claim
or to change the sandbox; operate the tools from the [site](../docs/src/content/docs/) instead.

| Document | What it settles |
|---|---|
| [threat-model.md](threat-model.md) | Assets, trust boundaries, the numbered threat catalogue (`T01` …), measures (`M1` …) and the portable acceptance contract (R1 to R8). Cite a `T` row and register an `M` entry before changing any sandbox script |
| [sandbox-comparison.md](sandbox-comparison.md) | The Colima prototype, Docker `sbx` and eight open alternatives mapped to the acceptance contract; platform suitability; the acceptance probes a backend has to pass |
| [sbx-internals.md](sbx-internals.md) | Why the `appsec-sbx` wrapper does what it does: provider presets and the harness investigations, the idle-stop finding, the reproducer boundary, the admission and transfer contract, the effective-policy narrative, portability |
| [reference-sandbox-colima.md](reference-sandbox-colima.md) | The frozen v0 reference implementation on Colima/Lima (macOS) with its self-certification checklist; the scripts are `sandbox/make-appsec-vm.sh` and `sandbox/bootstrap-appsec-vm.sh` |
| [ci-runner-design.md](ci-runner-design.md) | Design for a hardened GitHub Actions job that reviews PR diffs with an agent (design only) |
| [working-group.md](working-group.md) | The appliedAI working group this material was written for: release rule, schedule, provenance, sharing rules |

Evidence from running the wrapper on real hosts is in [`records/`](../records/).
