# Docs review checklist

Critical reading pass: **17 September 2026**. Original issue numbers are
preserved so we can work through them in any order. Check an item when its
changes are verified, and add a short resolution note. This checklist stays
outside the published site.

- [x] **1. Test the kill switch before the first agent run.**
  Completed 17 September 2026: added a rehearsal using a harmless running
  command, a second host terminal, provider-side revocation and a clean
  reset. Setup, provider, baseline and exercise guidance now require it
  before the first review. Checked commands against the CLI and source;
  the rehearsal was not executed against a live VM or provider account.
  Pages: [Getting started](../docs/src/content/docs/getting-started.md#5-first-run),
  [baseline](../docs/src/content/docs/sandbox/no-regret-measures.md#6-a-kill-switch-tested),
  [exercise](../docs/src/content/docs/exercises/first-discovery-pass.md#part-1-set-up-the-sandbox),
  [operating guide](../docs/src/content/docs/sandbox/sbx/index.md#run-a-review).

- [x] **2. Make reset requirements consistent.**
  Completed 17 September 2026: require reset before independent reviews,
  repeat passes and comparisons. Resuming the same interrupted review can
  retain state. Document export, stop/revoke, reset/verify, import, skill
  reinstall and fresh credentials. Updated Mantis guidance, transfer docs
  and CLI help; regenerated the command reference.
  Pages: [baseline](../docs/src/content/docs/sandbox/no-regret-measures.md#1-a-dedicated-disposable-vm),
  [Getting started](../docs/src/content/docs/getting-started.md#6-record-the-run),
  [VM lifetime](../docs/src/content/docs/sandbox/sbx/lifetime.md#reproducers-reset-and-destroy).

- [x] **3. Qualify the opening safety claims.**
  Completed 17 September 2026: replaced “implements all six” and the claim
  that effects are limited to tokens and findings. The introductions now
  distinguish VM/policy controls from operator duties: checking source for
  secrets, approving provider access, managing credentials and budgets,
  rehearsing stop/revoke and resetting between reviews. They explain data
  disclosure through allowed services, credential use, changes inside the VM
  and untrusted findings, with links to existing risks and coverage gaps.
  Checked against wrapper source and the threat model; docs build, internal
  links and whitespace checks passed. Readability thresholds remain flagged.
  Pages: [Getting started](../docs/src/content/docs/getting-started.md#1-read-the-baseline),
  [baseline](../docs/src/content/docs/sandbox/no-regret-measures.md#why-these-six),
  [wrapper introduction](../docs/src/content/docs/sandbox/sbx/index.md),
  [accepted risks](../docs/src/content/docs/sandbox/threat-model.md#accepted-risks).

- [x] **4. Make the self-check usable with the supplied environment.**
  Completed 17 September 2026: replaced the mandatory container probe with
  workload-user HTTPS checks for a raw IP and denied hostname, including
  curl proxy bypass. Added bounded commands, immediate log inspection and
  expected denial evidence; a failed request alone is inconclusive. Setup
  guides link to these checks before credentials or code enter. Container
  probes now apply when containers are used, and reproducers need their own
  checks. Broader network validation gaps remain explicit. Checked command
  parsing, wrapper source, docs build, links/anchors and whitespace; the
  probes were not run against a live VM. Readability thresholds remain flagged.
  Pages: [environment self-check](../docs/src/content/docs/sandbox/no-regret-measures.md#check-your-environment),
  [network denial checks](../docs/src/content/docs/sandbox/sbx/lifetime.md#check-network-denial),
  [acceptance requirements](../docs/src/content/docs/sandbox/threat-model/acceptance.md#requirements).

- [x] **5. Put tool, model and privacy decisions before execution.**
  Completed 17 September 2026: the sidebar now puts the baseline, tool
  shortlist and model guide before Getting started, with sandbox references
  after the exercise. Step 4 covers the review tool, model/provider route
  and code-handling permission before credentials and VM creation. Detailed
  comparisons remain optional; their introductions link back to setup.
  Step 5 selects the previously chosen model. Home reflects the revised
  order. Docs build, rendered navigation order, internal links/anchors and
  whitespace checks passed. Readability thresholds remain flagged.
  Files: [navigation](../docs/astro.config.mjs),
  [Getting started](../docs/src/content/docs/getting-started.md),
  [tool shortlist](../docs/src/content/docs/tools/shortlist.md),
  [model selection](../docs/src/content/docs/tools/choosing-a-model.md).

- [ ] **6. Remove the loop between Getting started and the exercise.**
  Home sends readers through Getting started, then an exercise that repeats
  setup and the same review. Say whether these describe one run or two and
  give an exact handoff. Reconcile the one-hour estimate with the exercise's
  1–2 person-days spread over two weeks.
  Pages: [Home](../docs/src/content/docs/index.md),
  [Getting started](../docs/src/content/docs/getting-started.md),
  [first discovery pass](../docs/src/content/docs/exercises/first-discovery-pass.md).

- [ ] **7. Define essential terms early and simplify unusual wording.**
  Define harness, skill, workload and reproducer when readers first need
  them; their glossary currently appears deep in the threat model. Replace
  phrases such as “unmetered slice of a seat,” “opaque tar.gz,” “it is
  nominal” and “configuration floor” with concrete explanations.
  Pages: [glossary](../docs/src/content/docs/sandbox/threat-model.md#terms-used-here),
  [baseline](../docs/src/content/docs/sandbox/no-regret-measures.md),
  [import/export](../docs/src/content/docs/sandbox/sbx/import-export.md),
  [VM lifetime](../docs/src/content/docs/sandbox/sbx/lifetime.md),
  [control coverage](../docs/src/content/docs/sandbox/threat-model/controls.md).

- [ ] **8. Lead the skills guide with its main task.**
  Show how to install and invoke the supplied review skill first. Follow
  with third-party packs, reference details and troubleshooting. Git
  filtering, transfer timeouts and binary stdin currently precede the main
  installation example.
  Page: [skills guide](../docs/src/content/docs/sandbox/sbx/skills.md).

- [x] **9. Remove session and workshop assumptions.**
  Completed 17 September 2026: session-specific release promises now say
  content will follow. Removed masterclass, organiser and shared-report
  assumptions from Home, Getting started, the baseline, shortlist and
  exercise. The demo fallback now says a public application and setup
  instructions will follow. Build and whitespace checks passed; no matching
  workshop/session references remained in the docs content scan.

- [ ] **10. Replace references readers cannot access or trace.**
  Supply public evidence or remove references to “the demo workspace's run
  records” and unspecified “September research.” Check that local-run claims
  have usable evidence links or enough public context.
  Already addressed with item 9: removed the unpublished demo link and the
  instruction to ask a workshop organiser for access.
  Pages: [baseline sources](../docs/src/content/docs/sandbox/no-regret-measures.md#sources),
  [tool shortlist](../docs/src/content/docs/tools/shortlist.md),
  [skills guide](../docs/src/content/docs/sandbox/sbx/skills.md#defending-code-reference-harness).

- [ ] **11. Move maintenance instructions out of the operator path.**
  Separate useful public acceptance evidence from editorial bookkeeping,
  implementation backlogs and instructions for editing generated docs.
  Keep operating guidance self-contained and maintenance notes in `design/`.
  Pages: [Home](../docs/src/content/docs/index.md#design-notes-and-evidence),
  [wrapper introduction](../docs/src/content/docs/sandbox/sbx/index.md),
  [threat model](../docs/src/content/docs/sandbox/threat-model.md),
  [command reference](../docs/src/content/docs/sandbox/sbx/commands.md).
  The command reference is generated: change its
  [generator](../sandbox/sbx/gen_command_reference.py) where appropriate.

- [ ] **12. Resolve draft issues before publication.**
  Remove or define “tier A/B” and “frontier-adjacent quality.” Explain or
  remove assumptions about shared cross-organisation tables. Replace stale
  `runsc` and internal-bridge instructions with guidance consistent with the
  published separate-VM approach. Keep these pages unpublished until reviewed.
  Pages: [shared observations](../docs/src/content/docs/triage/observations.md),
  [triage rubric](../docs/src/content/docs/triage/triage-rubric.md),
  [validation template](../docs/src/content/docs/validation/validation-loop-template.md),
  [hardening checklist](../docs/src/content/docs/hardening/hardening-checklist.md).

## Verification notes

The initial review covered 16 published pages and four drafts. The production
build passed, internal links and anchors resolved, and the drafts were excluded.
Readability checks flagged existing thresholds; model selection and the tool
shortlist were among the harder pages to read. External source claims were
not independently rechecked during this editorial pass.
