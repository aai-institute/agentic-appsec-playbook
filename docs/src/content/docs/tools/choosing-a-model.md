---
title: "Choosing a model"
description: "Model-selection criteria for privacy, hosting, behavioral monitoring, cyber capability and cost."
---

After choosing a tool from the [shortlist](/tools/shortlist/), select its model
and hosting route. First establish which models can process your code under
your organisation's policy, then test how well they perform the intended job.

## Selection criteria

| Criterion | What to check |
|---|---|
| Hosting and control | Self-hosted weights or a third-party API? Where do code, prompts and findings go, including through routers and fallback providers? For self-hosting, check hardware needs, throughput and the weights' license. |
| Zero data retention (ZDR) | Is ZDR available and enabled for the exact model, endpoint and account? Check exceptions for abuse monitoring, caching and stored files. A no-training policy alone does not establish ZDR. |
| Visible reasoning for behavioral monitoring | Does the endpoint expose chain-of-thought (CoT), a reasoning summary, or neither? Can your harness capture it for monitoring alongside tool calls, commands and network events? Treat visible reasoning as an extra signal; it may omit or misrepresent why an action occurred. |
| Cyber-relevant eval scores | Check dated CyberGym and ExploitGym results for the exact model and harness. Record the task subset, reasoning settings, trial count, budget and safeguard settings. Check whether results are self-reported or independently reproduced. |
| Access and safeguards | Is access available to your organisation? Does it support discovery, reproduction and patching under your intended conditions? Record refusals, model redirects and any special access requirements. |
| Tool compatibility | Test skill following, tool calls, context limits and structured reports in the chosen harness. Confirm the actual model used by child agents and fallbacks. |
| Cost and operating limits | Measure total cost per validated finding, latency and rate limits. Include retries and child agents. Set a spend cap or manual abort threshold before running. |

## Models to investigate

Use these examples to build your own comparison. They cover different hosting
and cost choices; their AppSec quality still needs testing on your code.
Use the [cyber benchmarks below](#reading-cyber-benchmarks) to guide your evaluation.

### Hosted open-weight models

| Candidates | Why investigate them? | What to check |
|---|---|---|
| **GLM-5.3 and GLM-5.3-Flash** | Compare GLM-5.3's reported cyber capability with Flash's focus on efficient coding and agent tasks. See Z.ai's [GLM-5.3](https://docs.z.ai/guides/llm/glm-5.3) and [Flash](https://docs.z.ai/guides/vlm/glm-5.3-flash) documentation. | Evaluate both on the same findings; a base model's cyber score does not establish Flash's performance. Check each variant's license, thinking settings and tool-call support. |
| **DeepSeek V4 Pro and V4.1 Flash** | A second pair for comparing finding quality, cost and runtime. The [API guide](https://api-docs.deepseek.com/) lists `deepseek-v4-pro` and `deepseek-flash` (V4.1 Flash); the [release notes](https://api-docs.deepseek.com/updates/) describe the changes. | Confirm which version the endpoint serves. DeepSeek currently retains V4 Pro service; older V4 Flash aliases now route to V4.1 Flash. Record the provider and resolved model, including any router fallbacks. |

Open weights do not determine a hosted service's privacy policy. Check the
actual inference provider's retention and data-location terms, including any
router in front of it. Test whether reasoning text reaches your monitoring
logs through that route.

### Self-hosted experiments

Explore how far smaller **Qwen3.8** variants can take you, starting with
[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B). Its model card documents
local serving and thinking controls. Treat this as a research track: try a
bounded review or triage task, then compare it with a hosted baseline using
the same evidence and budget.

Record the exact weights, quantization, context limit, serving engine and
hardware. Measure missed findings and tool-use failures alongside speed and
memory use. Check memory needs at your intended context length before
committing to hardware. Self-hosting also makes you responsible for retention
in inference logs and monitoring systems.

### Commercial frontier models

| Candidates | Why investigate them? | Access and privacy checks |
|---|---|---|
| **Claude Opus 5 / Fable 5.1** | Anthropic's [model guidance](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1) starts with Opus 5 and suggests Fable 5.1 for harder, longer tasks. Compare discovery quality and safeguard interventions. | Fable 5.1 has model-specific retention requirements; see below. Discovery access does not imply exploit-generation access. Verify the exact model and account tier. |
| **GPT-6 Astra** | An OpenAI baseline for demanding code reasoning and agent tasks; see the [model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra). | OpenAI's [API data controls](https://developers.openai.com/api/docs/guides/your-data) require approval for ZDR. Check endpoint, tool and model eligibility, plus any account-specific retention exceptions. |
| **Gemini 3.8 Flash** | A Google candidate for coding and long-running agent workflows; see the [model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). | Verify the service and contract you will use. Google's [Cloud ZDR guidance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention) lists abuse-monitoring, grounding and Advanced AI exceptions; some features may prevent ZDR. |

**Fable 5.1 is not ZDR by default.** Anthropic's
[platform documentation](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1#availability)
specifies 30-day retention unless Anthropic explicitly authorizes ZDR.
Its [release announcement](https://www.anthropic.com/claude-fable-and-mythos-5-1)
describes ZDR access for eligible customers ahead of the phased Enterprise
Frontier Safeguards rollout. Confirm your eligibility rather than assuming an
existing ZDR agreement covers every model. The same announcement permits
vulnerability discovery while retaining restrictions on exploit development.

## Gated cyber models and access

These options require provider approval. Confirm access before choosing a
harness or planning an evaluation around them.

### OpenAI: Daybreak and the `-Cyber` variants

OpenAI's [Daybreak guidance](https://learn.chatgpt.com/docs/cyber-safety)
distinguishes general defensive workflows from advanced security testing:

| Option | Intended use | Current API model |
|---|---|---|
| **Daybreak Blue** | Reduced refusals for approved code review, discovery, incident response and patch validation. | `gpt-daybreak-blue-latest` currently resolves to `gpt-5.6-sol`. |
| **Daybreak Red / GPT-5.6-Cyber** | Specialist model for approved vulnerability research, exploit validation and security testing. Requires separate approval and provisioning. | `gpt-daybreak-red-latest` currently resolves to `gpt-5.6-cyber`; its [model reference](https://developers.openai.com/api/docs/models/gpt-5.6-cyber) lists the Responses API. |
| **GPT-5.4-Cyber** | Older variant, deprecated September 11. | Scheduled for API removal on October 1, 2026; [migrate to GPT-5.6-Cyber](https://developers.openai.com/api/docs/deprecations#2026-09-11-gpt-54-cyber). |

Apply through [Trusted Access for Cyber](https://learn.chatgpt.com/docs/cyber-safety),
using the individual or organisation route. Identity verification and Blue
approval do not grant Red access. Approval covers a specific person or
service, workspace or API organisation/project, model and product surface.
The [API access documentation](https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity#authorized-access-and-agentic-workflows)
confirms the alias mappings and requires separate approval for ZDR. Record
the resolved model when evaluating a moving `-latest` alias.

### Anthropic: Mythos and cyber verification

**Claude Mythos 5.1** (`claude-mythos-5-1`) is available to approved
Project Glasswing participants. Request access through your Anthropic, AWS
or Google Cloud account team. Anthropic currently limits Mythos to a set of
US organisations. It says Mythos access through the Cyber Verification
Program (CVP) is forthcoming. See the [model availability documentation](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1#availability)
and [Mythos overview](https://www.anthropic.com/claude/mythos).

Fable 5.1 shares Mythos 5.1's underlying model with additional cyber and
biology safeguards. Claude Security also uses Mythos 5.1; using that product
does not establish access for your own API harness. Mythos carries 30-day
retention and requires express Anthropic authorization for ZDR.

For Opus and Sonnet, the [CVP](https://support.claude.com/en/articles/14604842-real-time-cyber-safeguards-on-claude-opus-and-sonnet)
already offers a free application process for reduced safeguards on
legitimate defensive work. It requires identity verification and approval
for the organisation. Routes exist for Anthropic first-party access,
Microsoft Foundry, Claude Platform on AWS and Claude on Google Cloud;
Amazon Bedrock is currently excluded. ZDR organisations are currently
ineligible; sales-managed ZDR customers should contact their account team.
Check the provider-specific application instructions before choosing a route.

### Google: Gemini Flash Cyber and Fairwind

Google's Cyber variants focus on vulnerability discovery, validation and
patching. The current access route is the **Fairwind Program**.

| Model | Availability and intended use |
|---|---|
| **Gemini 3.8 Flash Cyber** (`gemini-3.8-flash-cyber`) | The current cyber-specific model. Google's [model reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-cyber) lists general availability behind an allowlist on Gemini Enterprise Agent Platform. Approved partners can use it directly or through CodeMender. |
| **Gemini 3.5 Flash Cyber** | Earlier variant fine-tuned for finding, validating and patching vulnerabilities. Its [launch announcement](https://deepmind.google/blog/introducing-gemini-3-5-flash-cyber/) described a limited CodeMender pilot for governments and trusted partners. Use the current 3.8 documentation when planning access. |

Apply through [Fairwind](https://deepmind.google/fairwind-program/) or contact
your Google account team. Google prioritizes governments, critical
infrastructure and core technology platforms, and welcomes academic labs
working on defensive benchmarks. Applicants undergo vetting. Access is
limited to internal security, incident response and penetration testing
teams, with authentication and access-tracking requirements; redistribution
is prohibited. CodeMender can also use public models without Fairwind access.

**Direct managed-model access supports ZDR**, according to the Fairwind FAQ.
Confirm the configuration against Google's [retention guidance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention),
including logging and applicable abuse-monitoring exceptions. CodeMender has
separate session storage: active scans can retain source snippets, diffs and
checkpoints for up to seven days. Source content is cleared within seconds
of completion; the remaining session record expires at seven days. Check
that this fits your code-handling policy before choosing that route.

For your own harness, check integration support: the current model reference
lists structured output and chat completions, but marks native function
calling unsupported. Test the harness's tool protocol before adopting it.

## Reading cyber benchmarks

[CyberGym](https://www.cybergym.io/cybergym/) primarily measures vulnerability
reproduction: the agent receives an unpatched codebase and a vulnerability
description, then must produce a triggering input.
[ExploitGym](https://rdi.berkeley.edu/blog/exploitgym/) measures exploit
development from a supplied bug and crashing proof of vulnerability. Neither
score directly measures the quality of a whole-repository review or a fix.

Compare scores under matching conditions. A result from many attempts or
special access with reduced safeguards may not transfer to your normal
endpoint. Use benchmarks to select candidates, then compare them on the same
pilot repo with a fixed tool, prompt and budget. Track validated findings,
false positives, missed bugs and cost in the
[observations table](/triage/observations/).


## Background research

The model-access research is in `model-access-tiers-2026-09.md` (not yet
public; see the [background research convention](/#conventions)).
