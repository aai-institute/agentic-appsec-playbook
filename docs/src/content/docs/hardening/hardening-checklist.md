---
title: "Hardening Checklist: beyond the no-regret baseline"
---
What has to be true before an agentic AppSec loop runs on a schedule, in
CI, without someone watching. Extends the no-regret baseline
([`sandbox/no-regret-measures.md`](/sandbox/no-regret-measures/); implemented in
[appsec-sbx](/sandbox/sbx/)), which stays the
prerequisite.

Structure: the five control-placement rows of OpenAI's *Agent security in
the enterprise* (Aug 2026) — "place
controls as close as possible to the effect they limit." Each measure names
the incident or source it answers to, so nothing here is hypothetical.

Self-assessment scale per measure: **have it / could have it in a quarter /
not realistic for us.**

## 0. Baseline (the no-regret measures — must already hold)

- [ ] VM-based runner, zero host mounts, throwaway or rebuilt from script
- [ ] Egress default-deny with a named allowlist; proxy log kept
- [ ] No long-lived credentials inside; model key with a hard spend cap
- [ ] Kill switch tested — halt the runtime *and* revoke the key
- [ ] Evidence per run: proxy log, egress-drop log, harness session log

## 1. Runtime and network boundary

- [ ] **One microVM per run; nothing shared and writable between concurrent
      runs.** No shared cache, mirror, scratch bucket, or credential across
      runs. *Why:* ~1,200 OpenAI agents built a message board through a
      shared Artifactory mirror with one shared credential and escaped through
      it — no exploit needed for the coordination, and the mirror became the
      egress path. Per-run isolation with no shared writable state is the
      structural defence (CTF-infrastructure invariant).
- [ ] **Two independent network-isolation layers** (e.g. VM-level default-deny
      plus in-guest proxy allowlist). *Why:* OpenAI's own remediation; "no
      single control should ever be assumed to be fully robust."
- [ ] **Every reachable shared service is treated as a transitive escape
      path** — package mirrors, vaults, object stores, cache proxies. Remove
      what the run doesn't need; pre-pull images during provisioning rather
      than allowlisting registries at runtime. *Why:* OpenAI ultimately
      removed Artifactory from the research environment.
- [ ] **Allowlists are not monitoring.** Both HF production injections acted
      on *local* primitives (an HDF5 external read of `/proc/self/environ`, a
      template injection) that the URL allowlist never saw; benign-SaaS
      chaining defeats allowlists too. Log and review the volume and
      behaviour of *allowed* traffic.
- [ ] **Generated code and reproducers run in a second sandbox with no
      network** (`runsc`); dynamic targets only on an internal bridge, never
      internet-exposed. *Why:* deliberately vulnerable targets and
      offensive tooling must not be able to reach anything real.
- [ ] **Control plane immutable per run.** Harness config, settings files,
      `$PATH`, shell rc files, hooks are read-only or rebuilt from source each
      run; the orchestrator, report store and monitoring credentials are
      out of the agent's reach. *Why:* a sandboxed command can write
      `~/.claude/settings.json` or `$PATH` executables "and use them to widen
      its own access on the next run" (Anthropic's own docs); traditional
      sandboxes assume a workload that doesn't rewrite its launcher.
- [ ] **Budgets are a safety parameter, not just a cost one.** Hard caps on
      tokens, wall-clock, and tool calls per run, with automatic stop. *Why:*
      out-of-bounds behaviour rose monotonically with run length and
      reasoning budget in OpenAI's analysis; OWASP ASI08 "quotas, progress
      caps, circuit breakers."
- [ ] Interior hardening per CIS Docker/Kubernetes where containers are used
      inside the VM: no root, no privilege escalation, seccomp on, read-only
      root filesystem, no hostPath/hostPID/hostNetwork.

## 2. Agent / tool boundary

- [ ] **Harness permissions as a visible second layer, deny by default.**
      OpenCode `permission` config / Claude Code sandbox settings: bash /
      edit / webfetch on ask or deny for anything outside the working tree.
      *Why:* the enterprise guide's one-liner — "Instructions may guide
      behavior; independent controls provide containment." A harness is not
      a sandbox; this layer is for visibility, the VM is the containment.
- [ ] **Capability registry:** an inventory of the tools the agent can call,
      each with an owner and its expected effect; re-review when a tool's
      schema or actions change; test *compositions* ("a shell paired with
      unrestricted egress can bypass higher-level controls").
- [ ] **Second review of elevated actions before execution** — a rules
      layer or a second model ("auto-review") on network egress, git push,
      external API calls, deletes outside the workspace. *Why:* OpenAI
      found its auto-review would have flagged most dangerous actions; OWASP
      ASI02 "intent gate" treating planner output as untrusted.
- [ ] **Never run as root** inside the agent's environment (OWASP ASI05) — and
      never with sudo or access to the Docker socket either: both are
      root-equivalent, and an agent with either can switch its own
      containment off. The reference sandbox's admin/agent user split is the
      minimum.
- [ ] **Stop conditions on every task.** No unfalsifiable or unachievable
      objective on an in-scope target; "cannot reproduce" is a first-class,
      accepted outcome. *Why:* 93 % of the HF message-board traffic came from
      the 22 % of tasks no model could solve.

## 3. Identity, credentials, and resource boundary

- [ ] **Agent identity per run** (what harness, what model, what task, what
      session) attached to every credential and every log line.
- [ ] **Task-scoped, short-lived credentials**, exchanged from a task token;
      long-lived secrets stay outside the agent's context behind a broker.
      "A runtime credential is not task authority."
- [ ] **Read-only code-host token for scanning.** Write-back happens only
      through a PR a human approves — never a token that can push to
      protected branches, edit workflow files, or read Actions secrets.
      *Why:* Comment-and-Control used the repo's own Actions secrets and
      GitHub itself as the exfil channel; GitHub App write access was in the
      HF attacker's hands.
- [ ] **Stop ≠ revoke.** The kill switch has two halves: halt the runtime and
      revoke or rotate every credential that was inside it. Test both.
- [ ] **Spend and rate limits enforced at the provider**, not only in the
      harness (API spend limits, per-run keys with caps).

## 4. Untrusted input: prompt injection and CI integration

- [ ] **Everything the agent reads is untrusted:** repo content, issue and PR
      text, comments, commit messages, READMEs, dependency metadata, tool
      output, fetched pages. Design as if any of it contains instructions.
      *Why:* Comment-and-Control hijacked three vendors' review agents via
      GitHub comments; Anthropic's stance is that the review action "is not
      designed to be hardened against prompt injection" — so the pipeline
      must be.
- [ ] **Nothing in the runner but the model key.** No cloud credentials, no
      deploy keys, no Actions secrets beyond what the agent's one job needs;
      block `/proc/self/environ` and similar (the Claude-Code-Action case,
      fixed in 2.1.128 — verify your harness version).
- [ ] **Agent output is untrusted input to everything downstream.** No
      auto-merge of agentic fixes; no agent comment triggers another
      automation without a human step; regression test required in every fix
      PR.
- [ ] **PR-time diff scans:** ephemeral runner per job, read-only token,
      comment-only output, no network but the model endpoint.
- [ ] **Scheduled backlog scans:** results land in a queue with a named
      owner and a triage budget, not as auto-created tickets. *Why:* volume
      is the failure mode (curl's report signal fell to ~1 in 20–30 under
      LLM-generated reports).
- [ ] **Plan/execution separation** where the harness allows it: the planner
      proposes, an external policy check gates, the executor acts (OWASP
      ASI08 "separate planning and execution via an external policy engine").

## 5. Detection and response

- [ ] **Telemetry minimum per action:** initiating principal, agent identity,
      task, tool action and destination, approval / enforcement decision,
      result and material effect — correlated with existing SIEM telemetry.
- [ ] **Monitor what was *attempted*, not only what completed** — egress
      drops, denied tool calls, permission prompts hit.
- [ ] **Default to halt on ambiguous alerts.** If responders can't rule out a
      false positive quickly, pause the run. *Why:* HF's detection fired but
      the alert's criticality wasn't raised and on-call wasn't paged,
      "costing precious time"; OpenAI's June 27 port-sweep alert was
      mis-triaged and the eval continued.
- [ ] **Incident procedure: stop → contain → recover → learn**, with the
      stop/revoke distinction above; rehearse once.
- [ ] **Remediate the capability, not the observed encoding.** *Why:* the
      file-write block on Artifactory was bypassed by encoding messages in
      directory names.

## 6. The intentionally offensive agent (open problem — state it honestly)

The safeguards vendors credit for containing incidents (cyber classifiers,
bounding system prompts, auto-review) are exactly what an offensive-for-
defense agent strips by design, and no published report describes running
one safely. What experience with these tools so far supports:

- [ ] Only against targets you own, inside the boundary, on the internal
      bridge; the target is never internet-exposed (DVWA/WebGoat rule).
- [ ] No egress but the model endpoint; fake responders (INetSim /
      FakeNet-NG style) for anything the tool wants to call back to.
- [ ] Shorter runs, lower reasoning budgets, human gate between stages.
- [ ] Rules of engagement as an *enforced mechanism*, not an agreement: the
      agent does not agree to anything (NIST SP 800-115's ROE, re-expressed as
      network and filesystem policy).
- [ ] "This is a simulation" is not a control. Agents in both 2026 cases
      treated CTF-style instructions as authorization and in several runs
      kept going after realizing the target was real.
- [ ] What we cannot yet claim: that the above is *sufficient*. Say so in
      the playbook.

## 7. Governance (the exec-facing companion)

For security leads and CISOs — the enterprise guide's
first-actions list, which maps onto the sections above:

1. Know your agents (inventory: harness, model, tasks, credentials) — §3
2. Prioritize by blast radius — §1
3. Expansion gate: new tools, new repos, new credentials need a review — §2
4. Task-scoped authority — §3
5. Test under realistic conditions, including malicious retrieved content — §4
6. Reassess on change (model, harness, prompt, tool schema) — §2
7. Plan for intervention — §5

Complements: Google SAIF's Agent Risk Self Assessment (governance-level
questionnaire), NIST SP 800-115 Appendix B (ROE template), NIST SP 800-53
SC-7 / SC-39 / SC-44 as the controls to cite in a policy document.

## Sanctioned relaxations

Use the friction recorded in your validation loops to decide which
relaxations you need:

| Friction | Relaxation | Compensating control |
|---|---|---|
| Running target for dynamic validation | Target container on an internal bridge inside the VM | No route from the bridge to the proxy; target never reachable from outside; torn down with the run |
| Docker image pulls at runtime | Pre-pull during provisioning | Registry hosts stay off the runtime allowlist |
| Container-in-VM for reproducers | `runsc` lane inside the VM | No network in the lane; nested Docker only in its weaker mode, never for the offensive stage |
| Second code host / package index the tool needs | Add the exact hostname | Proxy log reviewed for that host's volume; mirror preferred to public index |
| Dynamic testing against an existing staging environment (future extension) | Requires a supported action for one named host:port; not implemented in the current wrapper | Staging-only short-lived credentials; every connection logged; resettable target with synthetic configuration; owner agrees to the window; stop procedure also revokes credentials and resets the target. See [staging acceptance conditions](/sandbox/threat-model/acceptance/#staging-access-a-future-extension). |
