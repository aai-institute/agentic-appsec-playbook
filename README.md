# Agentic AppSec Pilot Playbook

Hands-on material for running open-source, AI-agent-based application
security tooling on your own code — safely, and with enough rigor to make a
local go/no-go decision from your own evidence rather than from public
leaderboards.

Built for and used in the appliedAI Institute working group *Practical
application of AI-powered open-source AppSec tooling* (four bi-weekly online
sessions, Q3/Q4 2026). Extracted into this repository so it can be released
and maintained independently of the working group's internal planning.

**Status: pre-release working material.** Documents carry their own status
lines; commands and claims are tagged (see *Conventions*). Nothing here has
been through a public release review yet.

## Who this is for

AppSec / DevSecOps engineers, security engineers, and senior developers who
own security tooling in an organization — comfortable with Git and CI, able
to run CLI tools against a test repository. No ML background needed.

## What's here, in the order you use it

| Step | Directory | Contents |
|---|---|---|
| 1. Contain the agent before it touches your code | [`sandbox/`](sandbox/) | [`reference-sandbox.md`](sandbox/reference-sandbox.md) — the *no-regret* baseline (isolated VM, default-deny egress, capped credentials, kill switch) as a reference implementation on Colima/Lima for macOS, with a tool-neutral self-certification checklist; [`make-appsec-vm.sh`](sandbox/make-appsec-vm.sh) (host) and [`bootstrap-appsec-vm.sh`](sandbox/bootstrap-appsec-vm.sh) (guest) automate it |
| 2. Pick a tool for the job | [`tools/`](tools/) | [`shortlist.md`](tools/shortlist.md) — open-source candidates per job (discovery, triage/validation, remediation, offensive-for-defense), with license, maturity, setup effort, blind spots, and model-access tiers |
| 3. Triage what the tool reports, and know what it cost you | [`triage/`](triage/) | [`triage-rubric.md`](triage/triage-rubric.md) — a time-capped, severity-first triage rubric (TP / FP / needs-investigation / duplicate) whose job is to find the findings worth proving and to put a number on manual triage time; [`observations.md`](triage/observations.md) — the per-run record (volume, cost, triage time, refusals) and what it deliberately does *not* compute |
| 4. Prove it, fix it, gate it | [`validation/`](validation/) | [`validation-loop-template.md`](validation/validation-loop-template.md) — the per-finding record for hypothesis → validation → fix → regression test → human-gated merge, with three validation designs (deterministic, open-weight PoV, vendor verification program) compared |
| 5. Run it unattended | [`hardening/`](hardening/) | [`hardening-checklist.md`](hardening/hardening-checklist.md) — what has to be true before the loop runs in CI without someone watching: five control rows (runtime/network, agent/tool boundary, identity, untrusted input + CI, detection & response), each measure tied to a 2026 incident, plus the open problem of the intentionally offensive agent; [`ci-runner-design.md`](hardening/ci-runner-design.md) — design for a hardened GitHub Actions job that reviews PR diffs with an agent: credential separation per step, least-privilege token, untrusted event text, ephemeral self-hosted runner variant, verification plan replaying the 2026 incidents (design only so far) |

Browse it as a site with [Zensical](https://zensical.org/): `uvx zensical serve`.

## Release rule and schedule

The appliedAI Institute publishes this material under its non-profit mandate.
To keep that clean, **every document here is released publicly before the
working-group session that first references it** — the working group uses
the public artifact, it never gets a private preview. Documents may still be
marked *draft* when they go public; what matters is that they are public.

| Must be public before | Session | Documents first referenced |
|---|---|---|
| **2026-09-17** | 1 · Landscape & setup | `sandbox/` (guide + scripts), `tools/shortlist.md` |
| 2026-10-01 | 2 · Discovery in practice | `triage/triage-rubric.md`, `triage/observations.md`, shortlist's second-tool sections |
| 2026-10-15 | 3 · Validation & triage | `validation/validation-loop-template.md` |
| 2026-10-29 | 4 · Operationalization & hardening | `hardening/hardening-checklist.md`, `hardening/ci-runner-design.md` (+ its implementation, if ready) |

Since repository visibility is all-or-nothing, the first row sets the date:
the repository goes public before 2026-09-17, with later documents present
in draft state. Blocking items for that date are tracked as issues.

## Conventions

- **Status lines** at the top of each document say how settled it is.
- **Tags on claims and commands:** `verified-at-source` (read the primary
  source), `reported-but-unverified` (secondary coverage only), `checked`
  (command run and output confirmed), `to-verify` / `not-yet-tested`
  (written, not yet exercised). Treat untagged operational detail as
  `to-verify`.
- **Model and tool versions are dated.** The landscape moves monthly; every
  version, price, and safeguard statement carries the date it was true.
- **Background research.** References of the form `research/<note>.md` or
  `reports/<report>.md` point to the working group's research notes and
  deep-research reports, which are not yet public. They will be released
  alongside the working group's whitepaper; until then treat them as
  citations you cannot follow, not as broken links.

## Sharing results across organizations

The triage and validation records are designed so that a group of
organizations can compare notes without exposing code: repos appear as a
*descriptor* (languages, size bucket, domain, age bucket), findings as CWE
class + severity + verdict, and **no detail of an unfixed vulnerability
leaves the organization** until it is fixed or the risk is accepted in
writing. The working group's full sharing rules (Chatham House in sessions,
pseudonyms, review-and-veto before publication) live with the working group;
adopt or adapt them if you run a similar exchange.

## Provenance

Extracted on 2026-09-07 from the working group's internal planning repository
(commit `2e25355`), where these documents were developed between 2026-09-01
and 2026-09-07. The working group's session plans reference this repository
as `playbook/<path>`.

## Licensing — proposed, not yet applied

Intended: **CC BY 4.0** for the documents, **Apache-2.0** for the scripts.
No `LICENSE` file is present yet; until one is added this repository is
all-rights-reserved by default. The decision and the release checklist are
tracked in [issue #1](https://github.com/aai-institute/agentic-appsec-playbook/issues/1),
which blocks making the repository public.

## Maintainer

appliedAI Institute for Europe gGmbH — Adrian Rumpold. The repository is
private during the working group; collaborators use issues and pull requests
here, everyone else reaches the maintainer directly. Participant or
organization data from the working group is never committed here.
