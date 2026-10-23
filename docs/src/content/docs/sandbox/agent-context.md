---
title: "Securing the agent's context"
description: Where an agent's instructions come from, when they become dangerous, and the controls an operator can apply. The companion to the no-regret measures.
---

The [no-regret measures](/sandbox/no-regret-measures/) limit what an agent
can reach: files, credentials and the network. They leave open what the agent
is told. Everything an agent reads ends up in one context, and the model
follows whatever in it reads like an instruction.

This page covers that second half: where an agent's instructions come from,
when they become dangerous, and what an operator can do about it. The
controls apply to any agent. The examples come from security review, where
reading untrusted code is the task itself.

## What an agent reads

An agent's context has two kinds of source.

| Source | Written by | Examples |
|---|---|---|
| **Authority** | The operator | Skills and rules files you reviewed and pinned; the task you gave it |
| **Data** | Anyone | The repository under review, including its comments and agent instruction files such as `AGENTS.md` and `CLAUDE.md`; pull request and issue text; fetched web pages and documentation; MCP servers' tool descriptions and results; messages from other agents; notes the agent wrote for itself |

The model cannot tell these apart. Text from a web page carries the same
weight as text from your prompt once both are in the context. Instructions
planted in data are called **indirect prompt injection**, a term coined for
instructions hidden in web pages that an assistant retrieves (Greshake et
al., 2023).

Some sources deserve a closer look:

- **Hidden text.** Instructions can sit in invisible Unicode characters or
  HTML comments that an editor or a rendered diff does not show. Pillar
  Security demonstrated this against the rules files of Cursor and GitHub
  Copilot. Read the raw diff of any rules file or skill you adopt.
- **MCP servers.** Installing a server is the operator's choice, but its tool
  descriptions are written by someone else. They enter the context before
  any task starts, and a server can change them after you approved it.
  Invariant Labs called this a rug pull. The MCP specification itself
  treats tool descriptions as untrusted unless the server is trusted.
- **Memory.** An agent that keeps notes between sessions reads its own
  earlier output back, including anything an injection put there. Rehberger
  showed an injected instruction persisting into every later ChatGPT
  conversation through its memory feature.

## When it becomes dangerous

Simon Willison named the combination that turns an injection into a leak the
**lethal trifecta**: an agent with "access to your private data", "exposure
to untrusted content" and "the ability to externally communicate". Together,
the three let an attacker trick the agent into sending your data out.

The test that follows: if one run holds private data, reads untrusted content
and can send data out, remove one of the three, or put a person at the step
that acts. Meta's **Rule of Two** states the same as a design rule. A task
that needs all three should not run autonomously; it needs a person or
another reliable check before it acts.

## The trifecta in security review

A security review agent has all three legs by design. Reading untrusted code
is the task, so that leg never goes away. Who can write to the repository
decides how large each leg is.

| Leg | Open-source repository | Private repository |
|---|---|---|
| Reads untrusted content | The code under review and its agent instruction files. Anyone can write pull request and issue text and comments; the attacker needs no access. | The code under review and its agent instruction files. Insiders and suppliers write the rest: dependencies, unreviewed skills, MCP servers, customer tickets. |
| Holds private data | The code is public. Unfixed findings, CI secrets and the model key are private. | The code itself, plus insider knowledge: undisclosed vulnerabilities, internal issues, who owns which code. |
| Can send data out | Every output is public: pull request comments, CI logs, issue text. Secrets can leave through them, and a flaw found in existing code is disclosed. | Code or insider knowledge can leave through output or tools. The model provider receives the code by design. |

Two consequences follow. In open source, a flaw the agent finds in code that
is already on the main branch belongs in a private channel, such as a draft
security advisory. Commenting on a flaw that the pull request itself
introduces is what review is for. In a private repository, an agent with
access to the issue tracker or the findings backlog holds knowledge that can
matter to an attacker more than the source does.

Rendered output is an outbound channel too. In CamoLeak, a hidden comment in
a pull request description made GitHub Copilot Chat read the viewing user's
private repositories and send their content out as tiny images loaded
through GitHub's own image proxy. GitHub fixed it by turning off image
rendering in Copilot Chat.

## Controls for the context

Four controls work on the legs that can move. Each lists what
[appsec-sbx](/sandbox/sbx/) provides and where it stops; the
[coverage limits](/sandbox/threat-model/controls/) give the full picture.

### Choose the instructions

Take skills and MCP servers only from sources you reviewed and pinned to a
commit. Leave the target repository's agent settings behind, and decide for
each harness whether it reads the target's instruction files.

In appsec-sbx, the VM starts with no review skills; they enter only through
[`appsec-sbx skills`](/sandbox/sbx/skills/), which records the commit and file
hashes. The import leaves out agent and editor settings directories such as
`.claude`, `.codex`, `.agents` and `.opencode`, and OpenCode's project
configuration. The wrapper refuses to continue while sbx has any MCP server
configured.

Not covered yet: instruction files at the repository root, such as
`AGENTS.md` and `CLAUDE.md`, and a root `.mcp.json` still reach the VM.
According to Claude Code's documentation, a non-interactive `claude -p` run
loads a project's MCP servers without asking; pass `--strict-mcp-config` to
prevent that. Pi never loads project files, and OpenCode ignores
repository-supplied configuration. The Codex setup marks the target as
trusted.

### Keep secrets out of what it reads

Keep nothing secret in the working copy. A scanner reads what is on disk,
whether git tracks it or not: in one trial outside the sandbox, an
end-to-end security harness reported the operator's own API key from a
git-ignored `.envrc` as a finding, and its saved shell snapshots kept the
key.

In appsec-sbx, the import skips untracked files, `.env*` files, credential
files and key files. The model key stays on the host: sbx's proxy adds it to
requests to the provider and the agent holds a placeholder.

### Limit what untrusted text can trigger

Give unattended runs a fixed prompt, and pass event text such as pull request
titles as data, never as part of the prompt. Keep the tools to what the task
needs, so one bad instruction stays small. Do not render images or links
from agent output where data could leave through them.

In appsec-sbx, outbound traffic is limited to the model provider and the
registries you chose. Not covered yet: a per-tool allowlist inside the
harnesses, and stripping images and links from output.

### Keep a record you can read

Keep transcripts and tool calls as evidence, and treat the agent's output as
untrusted until a person has reviewed it. Prefer harnesses whose instructions
you can read afterwards. Some multi-agent harnesses send the instructions
for their helper agents as encrypted content, so the operator's own logs do
not show what a helper was told.

Not covered yet in appsec-sbx: Claude Code's auto memory stays on, so runs in
the same VM share it until a reset.

## Guardrails

Guardrail products promise to catch injections. Whether one helps depends on
what it checks.

**Limits outside the model** decide what the agent can do whatever it read:
which tools and arguments it may use, which keys it holds, where data may
go, and whether output can render images or links. Rely on these. Microsoft's
security response team calls deterministic defences preferable for their
hard guarantees.

**Checks that judge text** include injection classifiers, LLM judges and
pattern rules. They catch careless attacks and feed monitoring, and an
attacker who iterates gets past them. In "The Attacker Moves Second",
adaptive attacks beat most of twelve published defences more than 90 % of the
time, including detectors that had reported near-zero failure. A rule
written against text counts here too: Claude Code's documentation says a Bash
permission rule matches the command as written and is no security boundary
around the program.

Where a guardrail sits matters. NeMo Guardrails, LlamaFirewall and similar
libraries wrap model calls inside an application you build. Coding agents
such as Claude Code, Codex and OpenCode do not route their tool calls through
them; for those, the enforcement points are the harness's permission rules,
the sandbox, and an MCP gateway in front of the servers.

| Tool | What it does | Use as |
|---|---|---|
| NeMo Guardrails (NVIDIA) | Input, output, dialog, retrieval and execution rails. Checks tool names and arguments against a declared schema in its experimental IORails engine | Limit, for tool calls; signal, for its text rails |
| ToolHive (Stacklok) | MCP proxy that applies Cedar policies to tool names and arguments and refuses on deny | Limit |
| Prompt Guard 2, LlamaFirewall (Meta) | Injection classifier and an LLM-based checker | Signal |
| LLM Guard (Protect AI) | Input and output scanners; repository archived in July 2026 | Avoid for new work |

Research designs such as CaMeL and Progent limit data flow and tool calls
before they run, and report near-zero attack success in their own
evaluations. They cost task success and tokens, and attacks that stay within
the task's own permissions still work.

## Techniques to look up

Look these up in the OWASP Top 10 lists to name risks in policies and
training, or in MITRE ATLAS for technique IDs in threat models and
detection rules. The OWASP
[GenAI Crosswalk](https://genai-security-project.github.io/crosswalk/)
maps the OWASP lists to MITRE ATLAS and to compliance frameworks. Some of
its mappings come from a classifier and are still under review.

| Technique | What it does |
|---|---|
| Direct prompt injection | The user's own input overrides instructions; jailbreaks are a subset |
| Indirect prompt injection | Instructions arrive in content the agent reads |
| Hidden instructions | Invisible Unicode, HTML comments, text in images |
| Tool poisoning | Malicious MCP tool descriptions, changed after approval |
| Instruction supply chain | Poisoned rules files, `AGENTS.md`, skills |
| Memory and context poisoning | Instructions persisted into memory or retrieval stores |
| Inter-agent injection | One agent's output hijacks another |
| Goal hijacking | The agent pursues the attacker's objective |
| Excessive agency | The attacker acts through the agent's own permissions |
| Exfiltration channels | Data leaves through tool calls, URLs or rendered images |
| Adaptive attacks | Iterating against a filter; character tricks |

MITRE ATT&CK covers the conventional steps these attacks end in, such as
credential access and exfiltration over web services.

## Sources

- Greshake et al., [_Not what you've signed up for: Compromising Real-World
  LLM-Integrated Applications with Indirect Prompt
  Injection_](https://arxiv.org/abs/2302.12173) (2023-02-23)
- Simon Willison, [_The lethal trifecta for AI
  agents_](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)
  (2025-06-16)
- Meta, [_Agents Rule of Two: A Practical Approach to AI Agent
  Security_](https://ai.meta.com/blog/practical-ai-agent-security/)
  (2025-10-31)
- Pillar Security, [_New Vulnerability in GitHub Copilot and Cursor: How
  Hackers Can Weaponize Code
  Agents_](https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents)
  (2025-03-18)
- Invariant Labs, [_MCP Security Notification: Tool Poisoning
  Attacks_](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
  (2025-04-01)
- Model Context Protocol, [_Specification
  2026-07-28_](https://modelcontextprotocol.io/specification/2026-07-28)
- Johann Rehberger, [_Spyware Injection Into Your ChatGPT's Long-Term Memory
  (SpAIware)_](https://embracethered.com/blog/posts/2024/chatgpt-macos-app-persistent-data-exfiltration/)
  (2024-09-20)
- Legit Security, [_CamoLeak: Critical GitHub Copilot Vulnerability Leaks
  Private Source
  Code_](https://www.legitsecurity.com/blog/camoleak-critical-github-copilot-vulnerability-leaks-private-source-code)
  (2025-09-30)
- Anthropic, [Claude Code security](https://code.claude.com/docs/en/security)
  and [permissions](https://code.claude.com/docs/en/permissions)
  documentation (read October 2026)
- Microsoft Security Response Center, [_How Microsoft defends against indirect
  prompt injection
  attacks_](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks)
  (2025-07-29)
- Nasr et al., [_The Attacker Moves Second: Stronger Adaptive Attacks Bypass
  Defenses Against LLM Jailbreaks and Prompt
  Injections_](https://arxiv.org/abs/2510.09023) (2025-10-10)
- Hackett et al., [_Bypassing LLM Guardrails: Evasion Attacks against Prompt
  Injection and Jailbreak Detection Systems_](https://arxiv.org/abs/2504.11168)
  (2025)
- [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails),
  [ToolHive authorisation](https://github.com/stacklok/toolhive/blob/main/docs/authz.md),
  [LlamaFirewall](https://arxiv.org/abs/2505.03574),
  [Prompt Guard 2](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M),
  [LLM Guard](https://github.com/protectai/llm-guard) (read October 2026)
- Debenedetti et al., [_Defeating Prompt Injections by
  Design_](https://arxiv.org/abs/2503.18813) (CaMeL, 2025); Shi et al.,
  [_Progent: Securing AI Agents with Privilege
  Control_](https://arxiv.org/abs/2504.11703) (2025)
- OWASP GenAI Security Project, [Top 10 for LLM
  Applications](https://genai.owasp.org/llm-top-10/) (2025) and [Top 10 for
  Agentic
  Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
  (2026); [GenAI Crosswalk](https://genai-security-project.github.io/crosswalk/)
  (read 2026-10-23)
- MITRE, [ATLAS](https://atlas.mitre.org/) (release 2026.09) and
  [ATT&CK](https://attack.mitre.org/)

Figures above are as reported in those documents.
