---
title: "Review skills"
description: "Install and use the supplied repository review skill, Mantis or Defending Code."
---

A skill is an instruction pack that guides the agent's review. The
[tutorial](/getting-started/) uses `security-review-repo`. The alternatives
below let you try another approach. Compare their purpose and limits in the
[tool shortlist](/tools/shortlist/).

Create the VM and complete the tutorial's environment checks before installing
a pack. Run installation commands on your host machine, then ask the agent
to use the installed skills inside the VM. Read third-party packs before
installing them. To repeat a run with the same instructions, select a fixed
Git commit rather than a branch that may change. The
[installation reference](/sandbox/sbx/skills/) covers file selection,
installation paths, updates and troubleshooting.

## Full-repo review skill

`security-review-repo` adapts Anthropic's MIT-licensed
[`security-review` prompt](https://github.com/anthropics/claude-code-security-review)
to review a whole repository instead of pending changes. Its source is in
[`sandbox/skills/security-review-repo`](https://github.com/aai-institute/agentic-appsec-playbook/tree/main/sandbox/skills/security-review-repo).

Run this command on the host to install the skill directly from GitHub:

```sh
appsec-sbx skills appsec-sbx https://github.com/aai-institute/agentic-appsec-playbook --subdir sandbox/skills
```

The `--subdir sandbox/skills` option selects the directory containing
`security-review-repo`. The wrapper downloads the repository to a temporary
checkout on the host and removes that checkout after preparing the files for
transfer. The VM does not need access to GitHub.

By default, the command installs from the `main` branch. To install a specific
revision, add `--ref <commit>` with the Git commit you want to use. The wrapper
records the installed revision in `skills.json` on the host.

To install a version you have edited locally, or a pack from a private
repository, give the command the path to the pack in your local checkout:

```sh
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
```

In OpenCode inside the VM, ask: "Use the security-review-repo skill to review
this repository." The report is written to `~/out/findings.md`. Follow the
[tutorial's review and export steps](/getting-started/#run-the-review).

## Mantis

Google's Mantis provides skills for several stages of a security review.
Its `npx skills add` installer needs access to GitHub, which the VM's review
network policy blocks. Clone the repository on the host, select a commit you
have reviewed, and copy the pack into the VM with `appsec-sbx skills`:

```sh
git clone https://github.com/google/mantis /path/to/mantis
git -C /path/to/mantis checkout --detach <reviewed-commit>
appsec-sbx skills appsec-sbx /path/to/mantis
```

Replace `<reviewed-commit>` with the Git commit you selected.

Mantis's reproduction and patching stages expect Docker inside the agent's
environment. The workload user in this VM cannot use Docker, so limit the
run to the stages that work with source text and record which stages you
skipped.

Mantis writes working files into the imported repository. Before repeating
the review or comparing it with another tool, export the results, stop the
VM and revoke the old credential at the provider. Then reset the VM, import
the target and reinstall the skills. See
[Starting another review](/getting-started/#starting-another-review).

## Defending Code Reference Harness

Run this command on the host to install the skills from the repository's
`main` branch. The `--subdir` option selects its `.claude/skills` directory:

```sh
appsec-sbx skills appsec-sbx https://github.com/anthropics/defending-code-reference-harness --subdir .claude/skills
```

For repeatable runs, add `--ref <commit>` with the revision you have reviewed.
Check that the selected revision provides the commands and report names below.

Inside the VM, open Claude Code and enter this command to start the scan:

```text
/vuln-scan /home/appsec/target/source
```

The `/vuln-scan` skill reviews the source and writes
`VULN-FINDINGS.json` and `VULN-FINDINGS.md` in the target directory. After the
scan, exit Claude Code. Run the following command in the VM shell to copy
both reports into `~/out`, the directory included by `appsec-sbx export`:

```sh
cp ~/target/source/VULN-FINDINGS.json ~/target/source/VULN-FINDINGS.md ~/out/
```

The reference harness's autonomous pipeline and Docker environment require
separate setup. The `appsec-sbx skills` command installs only the skill pack.
For the discovery exercise, finish by exporting the raw reports. Triage,
reproduction and patching belong to later stages of the review.
