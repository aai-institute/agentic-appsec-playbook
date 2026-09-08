# Hardened CI Runner for Agentic Code Review — Design

**Status: design draft v0.1, 2026-09-07 — nothing here has been run yet.**
Implementation is tracked in this repository's issues (milestone *Public
before WG session 4*). Everything operational below is `to-verify` unless
marked otherwise. This document exists so the design can be discussed and
the session 4 CI block can be built on it before code exists.

## 1. Purpose and scope

Take the laptop sandbox ([`sandbox/reference-sandbox.md`](../sandbox/reference-sandbox.md))
to the place where agentic AppSec actually runs unattended: a **GitHub
Actions job that reviews a pull request's diff with an AI coding agent** and
posts findings as a PR comment. One job, the prompt's native mode (PR-time
diff scan), built so that the two published 2026 incidents in exactly this
setting — *Comment-and-Control* and the Claude-Code-Action `/proc/self/environ`
case — fail against it by construction.

**In scope**

- A reference **workflow** (`.github/workflows/agentic-review.yml`) with the
  controls of §3 — this is where most of the value is.
- **Runner variant A — self-hosted ephemeral VM**: the existing sandbox image,
  registered as a one-job runner, destroyed after the job.
- **Runner variant B — GitHub-hosted runner with in-job egress lockdown**
  (stretch goal; weaker, but what most SMEs will actually use).
- A **verification plan** (§7) that replays the two incidents.

**Out of scope**

- Backlog / whole-repo scanning on a schedule (different volume, different
  queue problem — see the hardening checklist §4).
- Agentic *fixing* in CI. The loop's fix step stays a human-driven PR.
- A maintained, general-purpose GitHub Action. This is a dated reference
  implementation with a stated support posture (§9).
- Other CI systems. The controls transfer; the mechanics here are GitHub's.

## 2. Threat model

Vocabulary as in the sandbox guide (OpenAI *Agent security in the
enterprise*, Aug 2026): shrink the **reachable surface**, bound the
**effective blast radius**, and make the **maximum completed effect** of a
review job "a comment on the PR, and tokens spent" — nothing else.

**What the job holds that an attacker wants**

| Asset | Why it is exposed |
|---|---|
| The model API key | Must be in the job for the agent to run; CI is API-billing only — a Claude seat (tier A2) cannot be used here |
| `GITHUB_TOKEN` | Issued to every job; its permissions decide whether a hijacked agent can write code, workflows, or comments |
| Repository contents | The agent reads the whole checkout; private code leaves via the model API by design, and must not leave anywhere else |
| Other secrets in the environment | Anything else the workflow exposes (cloud creds, deploy keys) is blast radius for free |

**Who acts**

1. **Anyone who can write text the agent reads** — PR title, PR body, commit
   messages, issue comments, code comments, README, dependency metadata.
   On a public repo that is everyone. *Comment-and-Control* is this attacker:
   GitHub comments steering three vendors' review agents into exfiltrating
   the repo's own Actions secrets, using GitHub itself as the channel.
2. **A compromised dependency or action** in the job (supply chain).
3. **The agent itself misbehaving** without an attacker — runaway loops,
   scope creep, reading what it should not. The `/proc/self/environ` case is
   this: a Read tool reaching the process environment the Bash sandbox had
   stripped, fixed in Claude Code 2.1.128 by blocking sensitive `/proc`
   paths.

**Outcomes to prevent, in priority order**

1. Exfiltration of the model key or other secrets (via the model API, via a
   PR comment, via any egress).
2. Write-back to the repository: pushed commits, modified workflow files,
   approved or merged PRs.
3. Lateral movement from the runner into the organization's network or cloud.
4. Runaway cost.
5. Poisoned output: findings text that steers a downstream automation or a
   human reviewer.

## 3. Workflow-layer controls (the core)

Design principle: **no single step holds both a GitHub credential and the
model key.** The agent step has the model key and *no* GitHub token; the
posting step has a narrowly scoped GitHub token and *no* model key. A
hijacked agent then has nothing to write with, and a hijacked poster has
nothing to leak.

| # | Control | Mechanism | Closes |
|---|---|---|---|
| W1 | **Trigger only on `pull_request`, never `pull_request_target`** | GitHub does not pass secrets to `pull_request` workflows from forks; `pull_request_target` runs with the base repo's secrets against attacker-controlled code | secret exposure to fork PRs |
| W2 | **Restrict who can trigger** | `if:` guard on `github.event.pull_request.head.repo.full_name == github.repository` (no forks) and/or author association; optional `paths:` filter to skip docs-only PRs | drive-by triggering, cost |
| W3 | **Least-privilege `permissions:`** | Top level `permissions: {}`; checkout step `contents: read`; posting step `pull-requests: write` only. Never `contents: write`, never `actions: write`, never `id-token` unless W6 is used | write-back |
| W4 | **Checkout without persisted credentials** | `actions/checkout` with `persist-credentials: false` so the agent's shell finds no token in `.git/config` | token pickup by the agent |
| W5 | **Agent step: model key only** | Key as a step-scoped `env:` from `secrets`; `GITHUB_TOKEN` not referenced in that step; no other secrets in the workflow at all | blast radius |
| W6 | **Optional: key fetched at job time via OIDC** | `id-token: write` on a *separate* step that exchanges the job's OIDC token at a vault for the model key, then hands it to the agent step via a file the poster never sees. The key itself is still long-lived; the gain is no standing secret in GitHub | standing secrets |
| W7 | **Untrusted event text never enters the prompt or a `run:` line** | The prompt is fixed; the agent gets the diff via `git`, not `${{ github.event.pull_request.body }}`. Any event field used at all goes through `env:` indirection, never inline interpolation (GitHub's own script-injection guidance) | Comment-and-Control, script injection |
| W8 | **Output is a file, scanned, then posted by a separate step** | Agent writes `findings.md`; a step greps it for secret patterns (model-key prefixes, `ghp_`, JWT shape) and fails the job on a hit; only then does the poster step comment | key exfil through the comment channel |
| W9 | **Pinned everything** | Third-party actions by commit SHA; the harness at a fixed version at or above the `/proc` fix (Claude Code ≥ 2.1.128) or the equivalent OpenCode release; Node and image digests in variant A | supply chain, regression of known fixes |
| W10 | **`timeout-minutes` as the budget** | Job-level hard stop; plus a spend cap on the key's workspace. The first budget mechanism in this playbook that is enforced, not written down | runaway cost |
| W11 | **`concurrency:` one job per PR, cancel-in-progress** | New push cancels the running review | pile-ups, cost |
| W12 | **Agent output is untrusted downstream** | The comment is labeled as agent-generated; no other workflow triggers on it (`issue_comment` filters exclude the bot); never auto-approve, never auto-merge | poisoned output |

## 4. Runner variant A — self-hosted ephemeral VM (primary)

The sandbox guide's L1/L2, triggered by a webhook instead of a person.

- **Image:** built by [`sandbox/bootstrap-appsec-vm.sh`](../sandbox/bootstrap-appsec-vm.sh)
  plus the GitHub runner binary. Same nftables default-deny, same uid-keyed
  proxy allowlist.
- **Users:** the runner service runs as `runner`; the agent step runs as a
  separate unprivileged `agent` user with **no sudo and no Docker socket** —
  the same admin/agent split the laptop guide introduced in v0.2.
- **Ephemeral:** runner registered with `config.sh --ephemeral` — takes one
  job, deregisters; the VM is destroyed and recreated from the clean image
  (`make-appsec-vm.sh`-style clone, or a cloud image). No state survives a job;
  no two jobs share a writable anything.
- **Egress allowlist = model endpoint + GitHub's runner endpoints.** The runner
  needs GitHub's documented hosts (`github.com`, `api.github.com`,
  `*.actions.githubusercontent.com`, results/artifact endpoints — exact list
  from GitHub's "communication between self-hosted runners and GitHub" page,
  `to-verify` and pinned by date in the implementation). Everything else drops;
  the proxy log is uploaded as a job artifact.
- **Container forwarding closed:** a `forward` chain with policy drop, so a
  container the agent starts cannot NAT out (inherited from the laptop guide
  v0.2, where the missing chain was a real gap in v0.1).
- **Where it runs:** a cloud VM (any provider) or an on-prem hypervisor;
  `actions-runner-controller` on Kubernetes is the scale-out option but drops
  to container isolation unless a gVisor/Kata runtime class is used — state
  that trade-off, do not hide it.

## 5. Runner variant B — GitHub-hosted with in-job lockdown (stretch)

GitHub-hosted runners are already ephemeral VMs (one job, then discarded),
so L1 comes for free; **egress control is the gap**. Two routes, both
`to-verify`:

1. **In-job nftables**: the `ubuntu-latest` runner has passwordless sudo; a
   first step installs a default-deny ruleset allowing the runner's own
   endpoints and the model endpoint, before the agent step. Weakness: the
   ruleset is applied *by the job* — a compromised earlier step or action
   could skip it; ordering and a verification step mitigate, not eliminate.
2. **Existing egress-policy tooling** (e.g. StepSecurity's harden-runner
   action in block mode). Check license and data-handling terms before
   recommending under the Institute's name — `to-verify`.

Variant B is what most SMEs will run. It must be documented as *weaker than
A* and *far stronger than nothing*, with the residual risk stated.

## 6. Budget and telemetry

- Budget: `timeout-minutes` (W10) + workspace spend cap + `concurrency` (W11).
  Record cost per job from the model's usage reporting into the job summary.
- Telemetry, per job, uploaded as artifacts: harness session log, proxy log
  (variant A), egress-drop log (variant A), the scanned `findings.md`, and the
  job summary with cost and runtime. This is the "attempted vs. completed"
  record the hardening checklist §5 asks for, produced automatically.

## 7. Verification plan (the design is not done until these pass)

| Test | Expected |
|---|---|
| **Comment-and-Control replay:** a PR whose title, body, and a code comment instruct the agent to print its environment / API key into the findings | Agent step has no GitHub token to post with; W8 scan catches key patterns and fails the job; nothing is posted |
| **`/proc/self/environ` read** from the agent (harness tool or shell) | Harness at pinned version refuses; even if read, the environment holds only the model key, and W8 blocks it from the output |
| **Fork PR** | Workflow runs without secrets (W1) or is skipped by W2; no agent step executes with a key |
| **Egress from the agent step** to a non-allowlisted host, and from a container started by the agent | Dropped and logged (variant A); dropped (variant B route 1) |
| **Write attempt:** agent tries `git push`, editing `.github/workflows/`, or `gh pr review --approve` | No credential available (W3–W5); fails |
| **Runaway:** prompt engineered to loop | `timeout-minutes` kills the job; cost stays under the cap |
| **Poisoned output:** findings contain an instruction aimed at a human or a bot | Comment is labeled agent-generated; no workflow reacts to it (W12); reviewer training point |

## 8. Open questions

- Exact GitHub runner endpoint list and how often it changes (allowlist
  maintenance is the known weak spot of default-deny egress).
- OpenCode vs. Claude Code in CI: which harness, at which version, gives
  step-level control over tool permissions and honors the proxy environment
  fully? The laptop guide uses OpenCode; the incidents involve Claude Code's
  action; the `/proc` fix is in Claude Code.
- Whether W6 (OIDC-fetched key) is worth its complexity for SMEs, or a
  documented rotation schedule is the honest answer.
- Cost per PR review on a typical diff, to state a budget default.
- Variant B: whether any open, license-compatible egress tooling exists that
  we can recommend, or route 1 is the only one.

## 9. Support posture and release

Reference implementation, dated, pinned, **not maintained as a product**. It
ships with the date it was verified, the versions it was verified against,
and this document. Per the release rule in the README it must be public
before working-group session 4 (2026-10-29); public in draft state is
acceptable, a private preview is not.
