---
title: "Choosing a model"
description: "Model-selection criteria for privacy, hosting, behavioral monitoring, cyber capability and cost."
---

After choosing a tool from the [shortlist](/tools/shortlist/), select its model
and hosting route. First establish which models can process your code under
your organisation's policy, then test how well they perform the intended job.

Use this page for a detailed comparison. The
[Getting started checklist](/getting-started/#4-choose-the-tool-model-and-provider)
summarises the decisions needed for a first run. Once you have chosen an
approved model and provider route, continue with
[credential setup](/getting-started/#prepare-a-credential).

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
| **GLM-5.3 and GLM-5.3-Flash** | Compare GLM-5.3's reported cyber capability with Flash's focus on efficient coding and agent tasks. See Z.ai's [GLM-5.3](https://docs.z.ai/guides/llm/glm-5.3) and [Flash](https://docs.z.ai/guides/vlm/glm-5.3-flash) documentation. NIST's [CAISI assessment](https://www.nist.gov/news-events/news/2026/09/caisis-assessment-zais-glm-53-cyber-capabilities) (September 17, 2026) is an independent datapoint: GLM-5.3 is the most cyber-capable open-weight model it has tested, about four months behind the US frontier. | Evaluate both on the same findings; a base model's cyber score does not establish Flash's performance, and CAISI did not test Flash. Check each variant's license, thinking settings and tool-call support. |
| **Qwen3.8-Max** | Alibaba's frontier-class model, hosted on [Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-max) (Singapore, Germany and US regions) and on OpenRouter, with thinking, function calling and a 1M context. The [open weights](https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B) are released as Qwen3.8-2.4T-A95B under a permissive custom licence whose conditions only bind very large products and model-as-a-service businesses. | Alibaba publishes no cyber benchmark for it. The only public CyberGym figure (78.5) is a single run by Z.ai in its own harness for the [GLM-5.3 launch table](https://z.ai/blog/glm-5.3), alongside 14 of 26 on ExploitGym; the official leaderboard lists Qwen3.8-Max only inside a multi-model agent. Treat it as an untested candidate: run it on your pilot repo before comparing. The hosted model adds features the open checkpoint lacks, so record which one you used. Alibaba Cloud states it does not train on customer data; retention terms sit in separate agreements, so check them for your region. |
| **DeepSeek V4.1 Flash** | A cheaper comparison point for finding quality, cost and runtime. The [API guide](https://api-docs.deepseek.com/) lists `deepseek-flash`; the [release notes](https://api-docs.deepseek.com/updates/) describe the changes. | Confirm which version the endpoint serves. DeepSeek is phasing out V4 Pro: since September 14, 2026, `deepseek-v4-pro` requests also route to V4.1 Flash. Record the provider and resolved model, including any router fallbacks. |

Open weights do not determine a hosted service's privacy policy. Check the
actual inference provider's retention and data-location terms, including any
router in front of it. Test whether reasoning text reaches your monitoring
logs through that route.

### Self-hosted experiments

Explore how far smaller **Qwen3.8** variants can take you, starting with
[Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) (Apache-2.0). Its model card documents
local serving and thinking controls but no cyber benchmark. The one public
datapoint comes from Alibaba Security's
[CyberGym write-up](https://alibaba-velldepth.github.io/writeups/model-track.html)
(September 13, 2026): the untuned 27B scored 54.5% in their harness, against
88.9% for their own fine-tune and the mid-80s that frontier models report.
Expect a large gap on discovery tasks and measure it. Treat this as a
research track: try a bounded review or triage task, then compare it with a
hosted baseline using the same evidence and budget.

Record the exact weights, quantization, context limit, serving engine and
hardware. Measure missed findings and tool-use failures alongside speed and
memory use. Check memory needs at your intended context length before
committing to hardware. Self-hosting also makes you responsible for retention
in inference logs and monitoring systems.

### Commercial frontier models

| Candidates | Why investigate them? | Access and privacy checks |
|---|---|---|
| **Claude Opus 5.5 / Sonnet 5.5 / Fable 5.1** | Anthropic's [model guidance](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1) suggests Fable 5.1 for harder, longer tasks. [Opus 5.5](https://www.anthropic.com/claude-opus-5-5) (September 22, 2026) and [Sonnet 5.5](https://www.anthropic.com/claude-sonnet-5-5) (September 28) carry the same discovery-permitting cyber safeguards at lower prices. Compare discovery quality and safeguard interventions. | Fable 5.1 has model-specific retention requirements; see below. Opus 5.5 and Sonnet 5.5 are available with ZDR. Discovery access does not imply exploit-generation access: flagged requests fall back to Opus 4.8 (Fable and Opus) or Sonnet 5 (Sonnet 5.5). Verify the exact model and account tier. |
| **GPT-6 Astra / GPT-6.1 Sol** | OpenAI baselines for demanding code reasoning and agent tasks; see the [model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra). Astra (September 3, 2026) is the first model OpenAI classifies at the *Critical* cyber level of its Preparedness Framework; GPT-6.1 Sol (September 29) is the cheaper option. | OpenAI's [API data controls](https://developers.openai.com/api/docs/guides/your-data) require approval for ZDR. Check endpoint, tool and model eligibility, plus any account-specific retention exceptions. Astra keeps standard cyber safeguards even under Daybreak Blue; see below. |
| **Gemini 3.8 Flash** | A Google candidate for coding and long-running agent workflows; see the [model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). It is the Google frontier model you can use today. | Verify the service and contract you will use. Google's [Cloud ZDR guidance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention) lists abuse-monitoring, grounding and Advanced AI exceptions; some features may prevent ZDR. |
| **Gemini 4 Argon** | Google's new frontier model, [announced September 30, 2026](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/) for long-horizon software engineering and cyber defence. | Only available through the [Fairwind Program](#google-gemini-4-argon-flash-cyber-and-fairwind). Paid API access is planned after further safeguard work, without a date. With no model page or safety report yet, ZDR terms, reasoning visibility and tool-call support cannot be checked. Plan evaluations around 3.8 Flash until that changes. |

**Fable 5.1 is not ZDR by default.** Anthropic's
[platform documentation](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1#availability)
specifies 30-day retention unless Anthropic explicitly authorizes ZDR.
Its [release announcement](https://www.anthropic.com/claude-fable-and-mythos-5-1)
describes ZDR access for eligible customers ahead of the phased Enterprise
Frontier Safeguards rollout. Confirm your eligibility rather than assuming an
existing ZDR agreement covers every model. The same announcement permits
vulnerability discovery while retaining restrictions on exploit development.
Organisations that need ZDR now have a Claude route: the Opus 5.5 and Sonnet
5.5 announcements state both are available with ZDR, with safeguards similar
to Fable 5.1's. Anthropic's help centre names the fallback targets: flagged
requests on Fable 5, Fable 5.1, Opus 5 and Opus 5.5 switch to Opus 4.8, and
on Sonnet 5.5 to Sonnet 5.

## Gated cyber models and access

These options require provider approval. Confirm access before choosing a
harness or planning an evaluation around them.

### OpenAI: Daybreak and the `-Cyber` variants

OpenAI's [Daybreak guidance](https://learn.chatgpt.com/docs/cyber-safety)
distinguishes general defensive workflows from advanced security testing.
The help centre's
[program overview](https://help.openai.com/en/articles/20001258-openai-daybreak-trusted-access-for-cyber-overview)
(updated late September 2026) lists four levels:

| Level | Models and safeguards | Intended use |
|---|---|---|
| **Standard** | Mainline models (GPT-5.6 Sol, GPT-6 Sol, GPT-6 Luna, Astra) with standard safeguards. | Threat modeling, secure code review and patching. |
| **Daybreak Blue** | Reduced refusals on mainline models. Astra keeps standard safeguards under Blue. No cyber-specialised models. | Vulnerability triage, code review, malware analysis, incident response, patch validation. |
| **Daybreak Red** | GPT-5.5-Cyber, plus reduced refusals on mainline models including Astra. Organisations only; separate approval and stronger verification. | Penetration testing, exploit validation or development, controlled vulnerability research. |
| **Red with additional model approval** | GPT-5.6-Cyber; its [model reference](https://developers.openai.com/api/docs/models/gpt-5.6-cyber) lists the Responses API. | As for Red, per approved model. |

In the API, `gpt-daybreak-blue-latest` currently resolves to `gpt-5.6-sol`
and `gpt-daybreak-red-latest` to `gpt-5.6-cyber`; on Amazon Bedrock the IDs
differ and the aliases are unavailable. GPT-5.4-Cyber, deprecated September
11, is [removed from the API on October 1, 2026](https://developers.openai.com/api/docs/deprecations#2026-09-11-gpt-54-cyber).
Record the resolved model when evaluating a moving `-latest` alias.

Apply through [Trusted Access for Cyber](https://learn.chatgpt.com/docs/cyber-safety),
using the individual or organisation route. Individual applicants need a paid
plan, Advanced Account Security and FIDO2 hardware keys as their only login
methods; existing individual users must meet this by October 1, 2026. Identity
verification and Blue approval do not grant Red access. Approval covers a
specific person or service, workspace or API organisation/project, model and
product surface, and reduced refusals stay off until enabled for the request:
the Codex toggle defaults to off, and the Responses API takes an explicit
`access_programs.cyber` setting. The
[API access documentation](https://developers.openai.com/api/docs/guides/safety-checks/cybersecurity#authorized-access-and-agentic-workflows)
confirms the alias mappings and requires separate approval for ZDR. OpenAI's
hosted Codex Security Cloud, announced September 29, includes the Daybreak
Blue models without a separate application for Pro, Business, Enterprise and
Edu plans; the open-source CLI on the [shortlist](/tools/shortlist/#openai-codex-security)
still needs your own approval.

### Anthropic: Mythos and cyber verification

**Claude Mythos 5.1** (`claude-mythos-5-1`) is available to approved
Project Glasswing participants. Request access through your Anthropic, AWS
or Google Cloud account team. Anthropic currently limits Mythos to a set of
US organisations. It says Mythos access through the Cyber Verification
Program (CVP) is forthcoming. See the [model availability documentation](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1#availability)
and [Mythos overview](https://www.anthropic.com/claude/mythos).

Fable 5.1 shares Mythos 5.1's underlying model with additional cyber and
biology safeguards. Claude Security also uses Mythos 5.1; using that product
does not establish access for your own API harness, and the product is
Enterprise-only and not available under ZDR. Mythos carries 30-day
retention and requires express Anthropic authorization for ZDR.

For Opus and Sonnet, the [CVP](https://support.claude.com/en/articles/14604842-real-time-cyber-safeguards-on-claude-opus-and-sonnet)
already offers a free application process for reduced safeguards on
legitimate defensive work. Opus 5.5 and Sonnet 5.5 are not in the program
yet; Anthropic says it will expand the CVP to those models and to Mythos-class
models in three tiers, without a date. It requires identity verification and approval
for the organisation. Routes exist for Anthropic first-party access,
Microsoft Foundry, Claude Platform on AWS and Claude on Google Cloud;
Amazon Bedrock is currently excluded. ZDR organisations are currently
ineligible; sales-managed ZDR customers should contact their account team.
Check the provider-specific application instructions before choosing a route.

### Google: Gemini 4 Argon, Flash Cyber and Fairwind

Google's cyber-capable models focus on vulnerability discovery, validation
and patching. The current access route is the **Fairwind Program**, which
now leads with Gemini 4 Argon.

| Model | Availability and intended use |
|---|---|
| **Gemini 4 Argon** | Google's frontier model, [announced September 30, 2026](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/). It is rolling out first to vetted Fairwind participants and Google's internal teams *without its cyber guardrails*, for finding, validating and patching vulnerabilities, directly or through CodeMender. Before a wider release Google says it is strengthening four safeguards: misuse refusals for cyber and CBRN requests, resistance to indirect prompt injection, monitoring of chain-of-thought and actions with the ability to stop execution, and sealed sandboxes for high-risk training and evaluation. The public release will carry those guardrails; expect refusals and redirects that Fairwind participants do not see. |
| **Gemini 3.8 Flash Cyber** (`gemini-3.8-flash-cyber`) | The cyber-specific model with a published [model reference](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-cyber), which lists general availability behind an allowlist on Gemini Enterprise Agent Platform. Approved partners can use it directly or through CodeMender. Google reports that Argon outperforms it on internal and external cyber benchmarks, without publishing the figures. |
| **Gemini 3.5 Flash Cyber** | Earlier variant fine-tuned for finding, validating and patching vulnerabilities. Its [launch announcement](https://deepmind.google/blog/introducing-gemini-3-5-flash-cyber/) described a limited CodeMender pilot for governments and trusted partners. Use the current 3.8 documentation when planning access. |

Apply through [Fairwind](https://deepmind.google/fairwind-program/) or contact
your Google account team. Google prioritizes governments, critical
infrastructure and core technology platforms, and welcomes academic labs
working on defensive benchmarks. Applicants undergo vetting. Access is
limited to internal security, incident response and penetration testing
teams, with authentication and access-tracking requirements; redistribution
is prohibited. CodeMender can also use public models without Fairwind access.

**Direct managed-model access supports ZDR**: the Fairwind FAQ states that
Gemini 4 Argon supports zero data retention when accessed directly as a
managed model on Gemini Enterprise.
Confirm the configuration against Google's [retention guidance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention),
including logging and applicable abuse-monitoring exceptions. CodeMender has
separate session storage: active scans can retain source snippets, diffs and
checkpoints for up to seven days. Source content is cleared within seconds
of completion; the remaining session record expires at seven days. Check
that this fits your code-handling policy before choosing that route.

For your own harness, check integration support: the 3.8 Flash Cyber model
reference lists structured output and chat completions, but marks native
function calling unsupported. Argon has no model reference yet, so its
tool-call support, input context limit and reasoning visibility are
unconfirmed. Test the harness's tool protocol before adopting either.

## Reading cyber benchmarks

[CyberGym](https://www.cybergym.io/cybergym/) primarily measures vulnerability
reproduction: the agent receives an unpatched codebase and a vulnerability
description, then must produce a triggering input.
[ExploitGym](https://rdi.berkeley.edu/blog/exploitgym/) measures exploit
development from a supplied bug and crashing proof of vulnerability. Neither
score directly measures the quality of a whole-repository review or a fix.
Vendors also report other benchmarks: Google's Gemini 4 Argon launch gives
CWE-bench v1 rather than CyberGym or ExploitGym, so it cannot be placed on
the same scale as the other candidates here.

Compare scores under matching conditions. A result from many attempts or
special access with reduced safeguards may not transfer to your normal
endpoint. Use benchmarks to select candidates, then compare them on the same
pilot repo with a fixed tool, prompt and budget. For a first discovery pass,
record raw findings and cost in the
[run report](/exercises/first-discovery-pass/#part-4-write-the-run-report).
Later triage will assess false positives and finding quality.
