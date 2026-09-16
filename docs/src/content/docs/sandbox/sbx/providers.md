---
title: "Providers and credentials"
description: "One model provider per VM: presets, API keys, Claude Code and Codex seats."
---

Exactly one model provider per VM. The provider decides the workload allowlist, the key
variable and, unless `--harness` says otherwise, the installed harness: `claude-code` installs
Claude Code, `codex` installs the Codex CLI, every other provider installs OpenCode. Changing
the provider means a new VM (`destroy`, then `create`).

| `create` option | Allowlist (plus the registry) | Credential | Harness |
|---|---|---|---|
| `--provider openrouter` (default) | `openrouter.ai:443` | `OPENROUTER_API_KEY` via `shell --key` | OpenCode |
| `--provider anthropic` | `api.anthropic.com:443` | `ANTHROPIC_API_KEY` via `shell --key` | OpenCode |
| `--provider deepseek` | `api.deepseek.com:443` | `DEEPSEEK_API_KEY` via `shell --key` | OpenCode |
| `--provider claude-code` | `api.anthropic.com:443`, `platform.claude.com:443` | browser login from the guest (`/login`), or `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code |
| `--provider codex` | `api.openai.com:443`, `auth.openai.com:443`, `chatgpt.com:443` | `OPENAI_API_KEY` via `shell --key`, or `codex login --device-auth` in the guest | Codex CLI |
| `--endpoint HOST:PORT --key-var NAME` | that one exact endpoint | `NAME` via `shell --key` | OpenCode |

Wildcards are refused. `--registry` is repeatable and takes `npm`, `pypi` or an exact
`HOST:PORT` such as an organisation mirror; `--no-registry` allows none. Pick the registry the
*target* needs if the agent is meant to install its dependencies: a Python target under an
npm-only profile will show dozens of denied PyPI connections in the log and no installed
dependencies. A discovery-only prompt is not a control; the allowlist is.

### API key (OpenRouter, Anthropic, DeepSeek, custom endpoint)

`shell --key` (also `agent --key`, `exec --key`) prompts for the key without echo, or takes
it from the environment variable of the same name, writes it to a tmpfs file the workload can read but not modify, and enters. `key` alone does the same
without entering, and `unkey` removes the file. The workload can read its key; the budget is
whatever cap the key carries at the provider.

### Claude Code on a subscription seat

```sh
appsec-sbx create appsec-sbx --provider claude-code
appsec-sbx verify appsec-sbx
appsec-sbx import appsec-sbx /absolute/path/to/git-repository
appsec-sbx skills appsec-sbx /path/to/agentic-appsec-playbook/sandbox/skills
appsec-sbx shell appsec-sbx
# Inside:
cd ~/target/source && claude
# /login -> "Claude account with subscription": open the printed URL in a browser on
# the HOST, paste the one-time code back. Then /model, and /security-review-repo.
# The built-in /security-review is diff-scoped and has nothing to review here.
```

The browser login is the intended path: the pasted code is single-use and the tokens land in
the agent's home until removed with `unkey`. `stop` attempts cleanup only on a
running VM; see [credential cleanup limits](/sandbox/sbx/lifetime/). The alternative,
`shell --key` with a `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`, is a months-long
bearer token and was rejected by the API in the one trial so far. Either way the VM runs with
the whole seat's authority and the budget is the seat's rate limit, not a spend cap. A fresh VM
never has a credential: if `claude` does not ask you to log in, run `claude auth status`
before trusting it.

Expect these denials in the policy log at every Claude Code start, all harmless: a clone of
the plugin marketplace from GitHub, `downloads.claude.ai`, and a dozen attempts at
`mcp-proxy.anthropic.com`.

### Codex CLI on an API key or a ChatGPT seat

Both credential forms share the `codex` preset. API key: `shell --key` with
`OPENAI_API_KEY`. Seat: inside the workload shell run `codex login --device-auth`, open the
printed URL in a browser on the host and enter the code (device-code login must be enabled in
the ChatGPT account first). The credential lands in `~/.codex/auth.json`;
`unkey` removes it, while `stop` cleanup has the
[limits described above](/sandbox/sbx/lifetime/). Invoke the review skill by typing
`$security-review-repo` in the composer.

Codex keeps its own inner sandbox on top of the VM; the seeded configuration declares `~/out`
writable so the report write does not stop for approval, and turns account plugins off so the
VM makes no attempts to download plugin bundles. Expect denied GitHub attempts at startup
(update check, tip banner); they are harmless.
