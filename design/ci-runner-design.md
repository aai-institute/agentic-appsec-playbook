# Hardened CI Runner for Agentic Code Review — Design

**Status: design draft v0.2, 2026-11-09 — nothing here has been run yet.**
v0.2 moves the credential split from steps to jobs (§3), adds W13 and W14, a workflow sketch
(§3.1) and three verification tests (§7). v0.1 was dated 2026-09-07.
Implementation is tracked in this repository's issues (milestone *Public
before WG session 4*). Everything operational below is `to-verify` unless
marked otherwise. This document exists so the design can be discussed and
the session 4 CI block can be built on it before code exists.

## 1. Purpose and scope

Take the laptop sandbox ([`sandbox/reference-sandbox.md`](reference-sandbox-colima.md))
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

The laptop sandbox's full catalogue (assets, boundaries, threats `T01`–`T32`)
is [the threat model](../docs/src/content/docs/sandbox/threat-model.md); this section keeps
only what changes when the operator is a webhook. Three rows from it carry
over unchanged and are easy to forget in CI: committed developer configuration
in the repository is loaded by the review run (`T22`), every allowlisted host
beyond the model endpoint is a channel (`T12`), and the unit under test's own
dependencies can harvest the job's environment when the agent installs them
(`T24`/`T25`).

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

Design principle: **no single job holds both a GitHub write credential and the
model key.** The review job has the model key and a read-only token; the post
job, on its own runner, has a token that can comment and *no* model key. A
hijacked agent then has nothing to write with, and a hijacked poster has
nothing to leak.

The boundary is the job, not the step. Steps of one job share the runner, its
user and its filesystem, and give no isolation:

- Token permissions are set per workflow or per job. GitHub has no step-level
  `permissions` ([secure use reference][gh-secure-use]).
- The runner receives every secret of the job when the job starts. Code in any
  step can read them from the `Runner.Worker` process's memory; the
  tj-actions/changed-files payload did this with `sudo` on GitHub-hosted
  runners ([GHSA-mrrh-fwg8-r2c3][tj-ghsa]; [Unit 42][unit42-worm]).
- Values a step writes to `GITHUB_ENV` and `GITHUB_PATH` reach all later steps
  of the job. An `LD_PRELOAD` or a shadowed binary there runs inside the next
  step ([secure use reference][gh-secure-use]; [zizmor `github-env`][zizmor-github-env]).

On GitHub-hosted runners each job runs on a fresh VM
([GitHub-hosted runners][gh-hosted]). The review job hands its findings to the
post job as an artifact, and the post job treats that artifact as untrusted
data. GitHub Security Lab recommends this split for untrusted pull request code
([Preventing pwn requests][seclab-pwn]); GitHub's own Agentic Workflows runs
the agent in a read-only job and writes from separate jobs
([security architecture][gh-aw]).

One workflow with two jobs is enough while W2 keeps fork PRs out. Reviewing
fork PRs needs two workflows: `pull_request` for the review, `workflow_run` for
the comment ([Preventing pwn requests][seclab-pwn]).

| # | Control | Mechanism | Closes |
|---|---|---|---|
| W1 | **Trigger only on `pull_request`, never `pull_request_target`** | GitHub does not pass secrets to `pull_request` workflows from forks; `pull_request_target` runs with the base repo's secrets against attacker-controlled code | secret exposure to fork PRs |
| W2 | **Restrict who can trigger** | `if:` guard on `github.event.pull_request.head.repo.full_name == github.repository` (no forks) and/or author association; optional `paths:` filter to skip docs-only PRs | drive-by triggering, cost |
| W3 | **Least-privilege `permissions:` per job** | Top level `permissions: {}`; review job `contents: read`; post job `pull-requests: write` only. Never `contents: write`, never `actions: write`, never `id-token` unless W6 is used. Every job gets a `GITHUB_TOKEN`, referenced or not, so set each job's permissions | write-back |
| W4 | **Checkout without persisted credentials** | `actions/checkout` with `persist-credentials: false` so the agent's shell finds no token in `.git/config` | token pickup by the agent |
| W5 | **Review job: model key only** | Key as `env:` from `secrets` in the agent step; no other secrets in the job or the workflow. Step scope only limits the environment: every step of the job can read the key from runner memory. Stronger: the key in a proxy process the agent's user cannot read, as openai/codex-action and GitHub Agentic Workflows do | blast radius |
| W6 | **Optional: key fetched at job time via OIDC** | `id-token: write` on the review job; a step exchanges the job's OIDC token at a vault for the model key and hands it to the agent step. The fetched key is as readable inside the job as a secret (W5). The key itself is still long-lived; the gain is no standing secret in GitHub | standing secrets |
| W7 | **Untrusted event text never enters the prompt or a `run:` line** | The prompt is fixed; the agent gets the diff via `git`, not `${{ github.event.pull_request.body }}`. Any event field used at all goes through `env:` indirection, never inline interpolation (GitHub's own script-injection guidance). `env:` stops shell injection, not prompt injection: the diff itself stays untrusted input | Comment-and-Control, script injection |
| W8 | **Output is an artifact, scanned and posted by the post job** | The agent writes `findings.md`; the review job uploads it. The post job downloads it to `runner.temp`, greps it for secret patterns (model-key prefixes, `ghp_`, JWT shape), fails on a hit, and only then comments. The scan runs in the post job because a hijacked review job could tamper with a scan in its own job. It is a tripwire: base64 got past secret scanning in Comment-and-Control | key exfil through the comment channel |
| W9 | **Pinned everything** | Third-party actions by commit SHA; the harness at a fixed version at or above the `/proc` fix (Claude Code ≥ 2.1.128) or the equivalent OpenCode release; Node and image digests in variant A | supply chain, regression of known fixes |
| W10 | **`timeout-minutes` as the budget** | Job-level hard stop; plus a spend cap on the key's workspace. The first budget mechanism in this playbook that is enforced, not written down | runaway cost |
| W11 | **`concurrency:` one job per PR, cancel-in-progress** | New push cancels the running review | pile-ups, cost |
| W12 | **Agent output is untrusted downstream** | The comment is labeled as agent-generated; no other workflow triggers on it (`issue_comment` filters exclude the bot); never auto-approve, never auto-merge | poisoned output |
| W13 | **Agent configuration from the base branch** | The harness reads project configuration from the checkout: `CLAUDE.md`, `.claude/`, `.mcp.json`, `AGENTS.md`, `opencode.json`, `.codex/`. Restore these paths from the base branch before the agent runs, or start the harness with project configuration off. anthropics/claude-code-action restores them from the base branch | PR-supplied hooks, tools and instructions (`T22`) |
| W14 | **No `sudo` for the agent** | Variant A: the `agent` user (§4). Variant B: remove `sudo` in a step before the agent runs, as openai/codex-action's default `drop-sudo` and harden-runner's `disable-sudo-and-containers` do. Without `sudo` the agent cannot read runner memory or change the egress rules | key read from runner memory, egress bypass |

### 3.1 Workflow shape

A sketch of the reference workflow, not yet run. Pins are placeholders, and the
harness call stands for any harness started non-interactively with a fixed
prompt.

```yaml
name: agentic-review
on:
  pull_request:                       # W1
    types: [opened, synchronize, reopened]
permissions: {}                       # W3
concurrency:                          # W11
  group: agentic-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:                             # model key, read-only token
    if: github.event.pull_request.head.repo.full_name == github.repository  # W2
    runs-on: ubuntu-24.04
    timeout-minutes: 15               # W10
    permissions:
      contents: read                  # W3
    steps:
      - uses: actions/checkout@<sha>  # W9
        with:
          fetch-depth: 0
          persist-credentials: false  # W4
      - name: Agent configuration from the base branch   # W13
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
        run: |
          for p in CLAUDE.md AGENTS.md .claude .mcp.json opencode.json .codex; do
            rm -rf -- "$p"
            git checkout "$BASE_SHA" -- "$p" 2>/dev/null || true
          done
      # Variant B: egress lockdown and sudo removal (W14) go here
      - name: Review
        env:
          MODEL_API_KEY: ${{ secrets.REVIEW_MODEL_KEY }}  # W5
          BASE_SHA: ${{ github.event.pull_request.base.sha }}  # W7
        run: |
          git diff "$BASE_SHA"...HEAD > "$RUNNER_TEMP/pr.diff"
          <harness> --prompt-file .github/agentic-review/prompt.md \
            --input "$RUNNER_TEMP/pr.diff" --output findings.md
      - uses: actions/upload-artifact@<sha>
        with: { name: findings, path: findings.md, retention-days: 7 }

  post:                               # comment token, no model key, fresh VM
    needs: review
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions:
      pull-requests: write            # W3
    steps:
      - uses: actions/download-artifact@<sha>
        with: { name: findings, path: ${{ runner.temp }}/findings }
      - name: Scan for secret patterns                     # W8
        run: |
          if grep -Eq 'sk-ant-|sk-or-|ghp_|github_pat_|eyJ[A-Za-z0-9_-]+\.eyJ' \
               "$RUNNER_TEMP/findings/findings.md"; then
            echo "::error::findings match a secret pattern"; exit 1
          fi
      - name: Comment                                      # W12
        env:
          GH_TOKEN: ${{ github.token }}
          PR: ${{ github.event.pull_request.number }}
        run: |
          { echo '> Agent-generated review, not an approval.'; echo
            cat "$RUNNER_TEMP/findings/findings.md"; } > "$RUNNER_TEMP/body.md"
          gh pr comment "$PR" --repo "$GITHUB_REPOSITORY" --body-file "$RUNNER_TEMP/body.md"
```

On `pull_request`, the workflow file and the prompt file come from the PR's
merge commit, so a PR author with write access can change both. W2 limits runs
to people who could edit workflows anyway; W13 keeps the harness configuration
on the base branch.

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
   The ruleset only holds if the agent cannot undo it, so this route needs
   W14: `sudo` removed after the ruleset is in place.
2. **Existing egress-policy tooling** (e.g. StepSecurity's harden-runner
   action in block mode). Check license and data-handling terms before
   recommending under the Institute's name — `to-verify`. Its free tier covers
   public repositories on GitHub-hosted runners only, and telemetry goes to
   the vendor ([harden-runner README][harden-runner]).

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
| **Comment-and-Control replay:** a PR whose title, body, and a code comment instruct the agent to print its environment / API key into the findings | Review job has no write token to post with; the post job's W8 scan catches plain key patterns and fails the job; nothing is posted. An encoded key passes the scan (tripwire only) |
| **`/proc/self/environ` read** from the agent (harness tool or shell) | Harness at pinned version refuses; even if read, the environment holds only the model key, and W8 blocks it from the output |
| **Fork PR** | Workflow runs without secrets (W1) or is skipped by W2; no agent step executes with a key |
| **Egress from the agent step** to a non-allowlisted host, and from a container started by the agent | Dropped and logged (variant A); dropped (variant B route 1) |
| **Write attempt:** agent tries `git push`, editing `.github/workflows/`, or `gh pr review --approve` | The review job's token is read-only (W3, W4); fails |
| **Runaway:** prompt engineered to loop | `timeout-minutes` kills the job; cost stays under the cap |
| **Poisoned output:** findings contain an instruction aimed at a human or a bot | Comment is labeled agent-generated; no workflow reacts to it (W12); reviewer training point |
| **Environment-file tampering:** the agent writes `LD_PRELOAD` to `GITHUB_ENV` and a fake `grep` and `gh` to a directory added to `GITHUB_PATH` | Post job runs on a fresh VM and is unaffected; the scan and the comment use the real binaries |
| **Runner memory read:** the agent dumps `Runner.Worker` memory, with `sudo` where available | Variant B with W14 and variant A: refused. Otherwise only the model key and the review job's read-only token are found, no write token |
| **PR-supplied agent configuration:** the PR adds a hook in `.claude/settings.json`, an MCP server in `.mcp.json` and instructions in `AGENTS.md` | W13 restores them from the base branch; the hook does not run, the server does not start |

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
- Per-job secret scope on GitHub-hosted runners is observed in published
  research, not documented by GitHub.
- Whether a step with `sudo` can disable in-job egress lockdown, and whether
  reading `Runner.Worker` memory needs root on hosted Ubuntu. Variant B's
  verification answers both.
- Whether to keep the model key in a proxy outside the agent's user (W5), as
  openai/codex-action does, or accept the key as readable inside the review job.

## 9. Support posture and release

Reference implementation, dated, pinned, **not maintained as a product**. It
ships with the date it was verified, the versions it was verified against,
and this document. Per the release rule in the README it must be public
before working-group session 4 (2026-11-12); public in draft state is
acceptable, a private preview is not.

[gh-secure-use]: https://docs.github.com/en/actions/reference/security/secure-use
[gh-hosted]: https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
[tj-ghsa]: https://github.com/advisories/GHSA-mrrh-fwg8-r2c3
[unit42-worm]: https://www.paloaltonetworks.com/blog/cloud-security/github-actions-worm-dependencies/
[zizmor-github-env]: https://docs.zizmor.sh/audits/#github-env
[seclab-pwn]: https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/
[gh-aw]: https://github.blog/2026/03/09/under-the-hood-security-architecture-of-github-agentic-workflows/
[harden-runner]: https://github.com/step-security/harden-runner
