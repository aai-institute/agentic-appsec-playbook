---
title: "Glossary"
description: "Definitions of the agent, sandbox and security terms used throughout the playbook."
---

These terms are used throughout the playbook, from the first review tutorial
to the sandbox reference and threat model.

| Term | Meaning |
|---|---|
| Host / guest | Your computer / the Linux virtual machine (VM) running the review. |
| Harness | The program that connects the model to files and commands, such as OpenCode, Claude Code or Codex CLI. |
| Workload | The harness and everything it starts, including dependency installers and generated code. |
| Target | The repository or application being reviewed. |
| Skill | An instruction pack the operator installs for the harness to use. It may include scripts and other support files. |
| MCP | Model Context Protocol, an interface through which an agent can use tool servers. Host-connected servers can grant access beyond the VM. |
| Reproducer | A small program used to check whether a reported vulnerability is real. The wrapper provides a separate VM for running it. |
| Egress / allowlist | Outbound network traffic / the destinations that traffic is permitted to reach. |
| Control plane | The settings and services that enforce permissions, network rules and VM lifetime. |
| Provisioning / clean template | Installing tools before project data arrives / a saved VM baseline used by `reset`. |
| Residual risk | A risk that remains after a control is applied. |
