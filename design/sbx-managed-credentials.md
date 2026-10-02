# Replacing the tmpfs key with sbx proxy-managed credentials

Investigation of 2026-10-02 into whether the wrapper's `key`/`unkey` path
(`/run/appsec/env` on tmpfs, sourced by the workload's login shell) can be
replaced by sbx's own credential mechanism, so that the workload only ever
holds a surrogate and the host-side proxy adds the real key. This is the
mechanism the open measure M17 asks for; the
[OpenShell evaluation](openshell-evaluation.md) already noted that sbx's
managed credentials rest on the same contract.

Conclusion: yes, with a kit-declared credential and `sbx secret set
<service> --sandbox <vm>`. The experimental `sbx secret set-custom` path is
unsuitable. Details, evidence and the remaining risks follow. Implemented in
wrapper 0.4.0 (`appsec_sbx/credentials.py`, M17 partial in the control register).

## How sbx handles credentials (verified-at-source, sbx 0.46.0)

- A kit declares `credentials[].apiKey` with `name` (the environment variable),
  `proxyManaged: true` and `inject[]` entries of `domain`, `header` and
  `format` (or `scheme: bearer`). The sandbox then sees `NAME=proxy-managed`;
  the host-side proxy writes the real value into the declared header on
  requests to the declared domains. [Kit spec](https://docs.docker.com/ai/sandboxes/customize/kit-reference/),
  [credentials guide](https://docs.docker.com/ai/sandboxes/configuration/credentials/).
- The value enters with `sbx secret set <service>`, which reads stdin, and is
  stored on the host: macOS Keychain, Windows Credential Manager, a desktop
  Secret Service on Linux, or a 0700 file under `~/.config/com.docker.sandboxes`
  on a headless Linux host (sbx prints a notice in that case). `--sandbox <vm>`
  scopes the value to one VM; sandbox scope takes precedence over global.
- Third-party kits (ours is one) need a *binding* that approves the
  service and its domains. Without one, `sbx create` prints a note and
  withholds the credential. Bindings live in `~/.config/sbx/credentials.yaml`
  (`%APPDATA%\sbx\credentials.yaml` on Windows) and can be written ahead of
  time, which keeps creation prompt-free (M25).
- Kit-declared services with `scheme: bearer` failed to inject before 0.42.0
  ([sbx-releases#490](https://github.com/docker/sbx-releases/issues/490),
  fixed and verified by the maintainer on 0.45.1). The wrapper already
  requires 0.45.0.
- Since 0.43.0 the proxy does not forward a client-supplied credential it did
  not issue to a managed provider host. This broke `set-custom` placeholders
  aimed at provider hosts, still open as
  [sbx-releases#601](https://github.com/docker/sbx-releases/issues/601);
  body substitution for custom secrets does not work on 0.46.0 either
  ([sbx-releases#650](https://github.com/docker/sbx-releases/issues/650)).
  `set-custom` also takes the value only through `--value`/`--token` (visible
  in the process list) or a host command re-run on refresh. The service-secret
  path has none of these problems.

## Live probe (checked, macOS Apple silicon, sbx v0.46.0, 2026-10-02)

Throwaway v2 kit from `docker/sandbox-templates:shell-docker` declaring
service `appsec-probe`, variable `PROBE_API_KEY`, `proxyManaged: true`,
inject `domain: httpbin.org`, `scheme: bearer`. Dummy value
`dummy-probe-value-7f3a` stored with `sbx secret set appsec-probe --sandbox
appsec-secret-probe` from stdin; binding written by hand; `httpbin.org:443`
allowed for the probe VM only. All probes ran through `sbx exec` as the
template's `agent` user. Everything was removed afterwards: VM, secret,
template, binding file.

| Probe | Result |
|---|---|
| `sbx create` without a binding | VM created; note `no binding authorizes appsec-probe — the credential was not injected`; exit 0 |
| Environment of an `sbx exec` session | `PROBE_API_KEY=proxy-managed`, `HTTPS_PROXY=http://gateway.docker.internal:3128`, `SSL_CERT_FILE`/`NODE_EXTRA_CA_CERTS`/`REQUESTS_CA_BUNDLE` pointing at the system bundle, `PROXY_CA_CERT_B64`. The template also carries a GitHub sentinel `GH_TOKEN=gho_sbxproxymanaged…` |
| `Authorization: Bearer proxy-managed` to httpbin.org via the forward proxy | echoed as `Bearer dummy-probe-value-7f3a` |
| `Authorization: Bearer raw-client-token-xyz` | overwritten with the stored value; daemon log `proxy: overriding client-supplied credential with host credential (security policy)` |
| No `Authorization` header at all | the proxy adds `Bearer dummy-probe-value-7f3a` |
| Bare `Authorization: proxy-managed` | replaced by `Bearer dummy-probe-value-7f3a` |
| Sentinel in query string or POST body | forwarded as the literal text `proxy-managed` |
| Sentinel in `X-Api-Key` (undeclared header) | header removed from the request |
| Same request to a second allowed but unbound host (postman-echo.com) | `Bearer proxy-managed` forwarded unchanged; nothing injected |
| `curl --noproxy '*'` (transparent path) | TLS and policy worked, header forwarded as `Bearer proxy-managed`; no injection |
| TLS seen by the guest | server certificate `O=Docker Sandboxes; CN=httpbin.org` issued by `Docker Sandboxes Proxy CA`, trusted through `/usr/local/share/ca-certificates/proxy-ca.crt` in the system bundle |
| `sbx inspect --json` | `secrets: [{name: appsec-probe, source: uploaded}, {name: mcpgateway, …}]` |
| `sbx stop`, then `sbx exec` | sentinel and injection still present: the credential survives a stop |
| `sbx secret rm appsec-probe --sandbox … -f` on a running VM | next request carries the raw sentinel; daemon log `secrets: credential revoked` |
| `sbx rm` of the VM | the sandbox-scoped secret disappears from `sbx secret ls` |
| Recreate with the same name and kit | `PROBE_API_KEY=proxy-managed` present, nothing injected until a new `secret set` |
| `sbx template save`, `sbx rm`, `sbx create --template` with the kit | kit credential still declared; after `secret set` injection works |
| macOS login keychain listing | only the `sandboxes-auth` Docker Hub items; where the service secret itself rests was not identified |

The daemon log records the override and the revocation, not each injection.

## Wrapper design (as implemented in 0.4.0)

1. **Kit per VM.** Render `spec.yaml` at `create` and `reset` time from the
   profile: service `appsec-<provider>` (private names, so an operator's
   global `openrouter` or `anthropic` secret is never picked up by the VM),
   `name` = the profile's `key_var`, one `inject` entry per endpoint host.
   Headers: `Authorization` / `Bearer %s` for OpenRouter, DeepSeek, OpenAI and
   custom endpoints; `x-api-key` / `%s` for Anthropic. The OFFLINE profile
   declares no credentials, so reproducer VMs carry neither variable nor value.
2. **Binding before create.** Merge `bindings.appsec-<provider>.apiKey.domains`
   into the sbx bindings file (host adapter for the Windows path, M22). Keep
   the domains equal to the profile endpoints.
3. **Sentinel in the entry environment.** The bootstrap's `env -i` entry
   drops sbx's variables, so the bootstrap writes `export <key_var>=proxy-managed`
   into `/etc/appsec/credential.env`, and the login profile sources it only when
   the wrapper's entry says a key is stored (`APPSEC_KEYED=1`, decided from
   `sbx secret ls --sandbox` at entry). The `/run/appsec/env` sourcing, the
   tmpfiles entry and `inject_key` are gone.
4. **`key`** becomes `sbx secret set appsec-<provider> --sandbox <vm>` with the
   value on stdin (prompted without echo or from the environment, as today).
   **`unkey`**, **`stop`** and **`destroy`** run `sbx secret rm … -f`, which
   works on a stopped VM and takes effect at once. `stop` no longer needs a
   running VM to clear the API key, which closes that part of the M23 gap.
   Harness login stores on disk are unchanged.
5. **Guards.** `sbxcli.isolation` admits `appsec-<provider>` next to
   `mcpgateway`; `verify` asserts `sbx secret ls --sandbox <reproducer>` is
   empty; `credential_hint` consults `sbx secret ls --sandbox <vm> --json`
   instead of probing the tmpfs file, since the sentinel is always present.
6. **Docs.** Providers page, VM lifetime table (the key no longer disappears
   on idle stop, so `shell --key` loses its reason; `unkey` or `stop` is
   required) and the no-regret checklist line "the agent's shell environment
   holds the model key" become "holds a surrogate".

## Threat-model consequences

- **T25 / T24.** The workload, its dependencies and generated code can no
  longer read the key; a copied sentinel is worthless elsewhere (checked
  against an unbound host). They can still *use* it: the proxy adds the
  credential to every request to the bound host, header or not. M17's second
  half (limiting which API calls the workload may make) stays open, and the
  provider-side cap remains the budget control.
- **M17** moves from open to partial: credential held outside workload
  authority by sbx's proxy; residual as above.
- **M13 / T23.** A sandbox-scoped secret is removed with the VM and does not
  re-arm a recreated VM of the same name (checked). `reset` therefore still
  starts without a credential.
- **New residuals.** The key rests in the host credential store for the VM's
  life instead of in guest memory, and survives idle stops and daemon
  restarts. On a headless Linux host that store is a 0700 file. Injection
  needs the forward proxy; a workload that clears the proxy variables gets a
  401 (fail closed). TLS to the model endpoint is already terminated by the
  proxy today, so this adds no new plaintext exposure.
- **M20 / M25.** Entry guards change as in step 5; creation stays prompt-free
  through the pre-written binding.

## Checking injection without a real key

OpenRouter's `GET /api/v1/auth/key` distinguishes three cases (checked from the host,
2026-10-02): `User not found.` for a well-formed unknown key (`sk-or-v1-` and 64 hex
digits), `Missing Authentication header` for a malformed token such as the placeholder,
and `No cookie auth credentials found` when the header is absent. Store a well-formed dummy
with `key` and run that request from the guest: `User not found.` proves the proxy added the
stored value. From a wrapper VM, probe sandboxes with the private service name and a sandbox
from Docker's built-in `opencode` agent all gave that answer; the proxy's debug log
(`sbx daemon log-level set proxy debug`) shows `injected header ... replaced_sentinel: true`.

`sbx secret set` on an existing secret prompts `Overwrite? (y/N)` and cancels with exit
status 0 without a terminal, so the wrapper removes the old secret before storing a new one.

## Not yet tested

- OpenCode, Claude Code and Codex running against the sentinel in the
  wrapper's own guest (Docker's built-in kits use this mechanism with the
  same harnesses, which is encouraging but not our configuration).
- Claude Code's `CLAUDE_CODE_OAUTH_TOKEN` path with a sentinel; Claude Code
  may validate the token format locally. The kit `oauth` declaration, which
  rewrites token responses into sentinels, is the candidate for replacing the
  on-disk browser-login store, a separate piece of work.
- Behaviour when the operator also holds a global secret for the same
  provider under sbx's built-in service name.
- Windows and Linux: bindings path, credential store, and the Windows
  requirement for a desktop session already recorded for `sbx create`.
