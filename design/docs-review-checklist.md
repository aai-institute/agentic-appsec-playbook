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

- [x] **6. Clarify the overlap between Getting started and the exercise.**
  Completed 17 September 2026: kept the exercise as a standalone entry point.
  An opening callout explains the overlap and lets readers reuse a tutorial
  run on the same pilot repository after checking Parts 1–3, then continue
  with the run report in Part 4. Clarified that the tutorial's hour covers
  first-time setup; the exercise estimate includes repository selection,
  checks, the review and reporting. This preserves the exercise as the
  working group's assigned entry point without requiring session context
  on the public page. Docs build, internal links, rendered callout and handoff
  anchors passed; readability thresholds remain flagged.
  Pages: [Home](../docs/src/content/docs/index.md),
  [Getting started](../docs/src/content/docs/getting-started.md),
  [first discovery pass](../docs/src/content/docs/exercises/first-discovery-pass.md).

- [x] **7. Define essential terms early and simplify unusual wording.**
  Completed 17 September 2026: extracted the glossary from the
  threat model into a top-level page at the end of the navigation. Linked
  it from Home, the tutorial introduction and the threat model. The local
  evidence cleanup removed “unmetered slice of a seat.” Replaced “opaque
  archive,” “it is nominal” and “configuration floor” with concrete
  explanations of export behavior, the template warning and settings the
  workload must not be able to disable. Added inline definitions for harness,
  skill, workload and egress, and distinguished a reproducer program from its
  VM. Simplified credential-lifetime and shared-service wording. Docs build,
  links/anchors, phrase scan and whitespace checks passed; readability
  thresholds remain flagged.
  Pages: [glossary](../docs/src/content/docs/glossary.md),
  [baseline](../docs/src/content/docs/sandbox/no-regret-measures.md),
  [import/export](../docs/src/content/docs/sandbox/sbx/import-export.md),
  [VM lifetime](../docs/src/content/docs/sandbox/sbx/lifetime.md),
  [control coverage](../docs/src/content/docs/sandbox/threat-model/controls.md).

- [x] **8. Lead the skills guide with its main task.**
  Completed 17 September 2026: added Review skills beside the tutorial in
  Getting started. It begins with installation and invocation of the supplied
  review skill, followed by Mantis and Defending Code. The separate Skill
  installation reference keeps command syntax, file rules, paths, updates
  and troubleshooting. Updated tutorial, shortlist and standalone exercise
  links. Docs build, rendered navigation and links/anchors passed;
  readability thresholds remain flagged. No new live skill runs were made.
  Pages: [Review skills](../docs/src/content/docs/discovery/review-skills.md),
  [Skill installation](../docs/src/content/docs/sandbox/sbx/skills.md).

- [x] **9. Remove session and workshop assumptions.**
  Completed 17 September 2026: session-specific release promises now say
  content will follow. Removed masterclass, organiser and shared-report
  assumptions from Home, Getting started, the baseline, shortlist and
  exercise. The demo fallback now says a public application and setup
  instructions will follow. Build and whitespace checks passed; no matching
  workshop/session references remained in the docs content scan.

- [x] **10. Replace references readers cannot access or trace.**
  Completed 17 September 2026: removed local-run narratives, cost/timing
  anecdotes, platform test history and acceptance-record links from
  reader-facing pages. Removed “September research” and private demo-record
  references. Preserved local evidence in `design/` and `records/`, including
  a [local evidence archive](local-evidence-archive.md). Public pages retain
  operating limits, validation gaps and instructions for checking the
  reader's own setup. Item 9 already removed the unpublished demo link and
  organiser-access instructions. Docs build, links/anchors and whitespace
  checks passed; readability thresholds remain flagged.
  Pages: [baseline sources](../docs/src/content/docs/sandbox/no-regret-measures.md#sources),
  [tool shortlist](../docs/src/content/docs/tools/shortlist.md),
  [review skills](../docs/src/content/docs/discovery/review-skills.md#defending-code-reference-harness).

- [x] **11. Move maintenance instructions out of the operator path.**
  Completed 17 September 2026: Home links to sandbox limits instead of design
  notes and acceptance records. Removed implementation-backlog links,
  historical implementation commentary and instructions for maintaining IDs
  from the operator pages. Moved command-reference regeneration and threat-model
  maintenance guidance into `design/documentation-notes.md`. Updated the
  generator and regenerated the reference. Public pages retain current
  limitations and instructions for checking the reader's setup. Docs build,
  links/anchors, three CLI tests and whitespace checks passed.
  Pages: [Home](../docs/src/content/docs/index.md#sandbox-limits),
  [wrapper introduction](../docs/src/content/docs/sandbox/sbx/index.md),
  [threat model](../docs/src/content/docs/sandbox/threat-model.md),
  [command reference](../docs/src/content/docs/sandbox/sbx/commands.md).
  The command reference is generated: change its
  [generator](../sandbox/sbx/gen_command_reference.py) where appropriate.

- [x] **12. Resolve draft issues before publication.**
  Completed 17 September 2026: replaced model-tier labels with exact model
  details and human-written or agent-assisted validation methods. Run
  observations now belong to the reader's team; external sharing is optional.
  Validation and hardening use the separate reproducer VM, with model
  credentials excluded and network checks required. Removed stale `runsc`
  and internal-bridge instructions; additional capabilities require their
  own assessment. All four pages retain `draft: true` and are excluded from
  the production pages, links and sitemap. Build and whitespace checks passed;
  readability thresholds remain flagged. External incident claims and live
  validation workflows still need review before publication.
  Pages: [run observations](../docs/src/content/docs/triage/observations.md),
  [triage rubric](../docs/src/content/docs/triage/triage-rubric.md),
  [validation template](../docs/src/content/docs/validation/validation-loop-template.md),
  [hardening checklist](../docs/src/content/docs/hardening/hardening-checklist.md).

## Verification notes

The initial review covered 16 published pages and four drafts. The production
build passed, internal links and anchors resolved, and the drafts were excluded.
Readability checks flagged existing thresholds; model selection and the tool
shortlist were among the harder pages to read. External source claims were
not independently rechecked during this editorial pass.
