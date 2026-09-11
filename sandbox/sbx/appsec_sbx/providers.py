"""One model endpoint, one key variable per VM (threat model M1/M2; T12 T27).

Presets cover the providers whose OpenCode environment-variable auto-detection
is documented in the reference guide. Anything else is admitted explicitly
with --endpoint and --key-var; wildcards are refused because sbx deny
precedence cannot carve a broad grant back down.
"""
import re

PROVIDERS = {
    "openrouter": {"endpoints": ["openrouter.ai:443"], "key_var": "OPENROUTER_API_KEY"},
    "anthropic": {"endpoints": ["api.anthropic.com:443"], "key_var": "ANTHROPIC_API_KEY"},
    "deepseek": {"endpoints": ["api.deepseek.com:443"], "key_var": "DEEPSEEK_API_KEY"},
    # Tier A2: Claude Code on a subscription seat. Token from `claude setup-token` on the host.
    # platform.claude.com: OAuth token exchange/profile (checked 2026-09-10, 2.1.267); without it
    # the harness fails with a proxy 403. Nothing else: the seat's model list comes from the API
    # host itself (additionalModelOptionsCache), provided the blanket
    # CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC is not set (see the bootstrap profile).
    "claude-code": {"endpoints": ["api.anthropic.com:443", "platform.claude.com:443"],
                    "key_var": "CLAUDE_CODE_OAUTH_TOKEN"},
    # OpenAI Codex CLI, either credential form: an API key through `key` (OPENAI_API_KEY,
    # inference at api.openai.com) or a ChatGPT seat via `codex login --device-auth` inside the
    # guest (OAuth at auth.openai.com, inference at chatgpt.com/backend-api; hosts read from the
    # 0.154.0 binary). One preset for both: the extra hosts are the same vendor. not-yet-tested.
    "codex": {"endpoints": ["api.openai.com:443", "auth.openai.com:443", "chatgpt.com:443"],
              "key_var": "OPENAI_API_KEY"},
}
DEFAULT_PROVIDER = "openrouter"
HARNESSES = ("opencode", "claude-code", "codex")


def default_harness(provider):
    """One harness per VM, following the provider: Claude seat -> Claude Code, OpenAI -> Codex CLI,
    everything else -> OpenCode. Only that harness, its config and its variables are installed."""
    return {"claude-code": "claude-code", "codex": "codex"}.get(provider, "opencode")
DEFAULT_REGISTRY = "registry.npmjs.org:443"
# Common registries that need more than one host (threat model M1: one registry, but a
# registry may be several hosts). Named so the CLI can say --registry pypi.
REGISTRIES = {
    "npm": ["registry.npmjs.org:443"],
    "pypi": ["pypi.org:443", "files.pythonhosted.org:443"],
}
OFFLINE = {"provider": None, "endpoints": [], "key_var": None, "registry": None}

_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
ENDPOINT = re.compile(rf"^{_LABEL}(?:\.{_LABEL})+:(?:[1-9][0-9]{{0,4}})$")
KEY_VAR = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


class ProfileError(ValueError):
    pass


def check_endpoint(value, what="endpoint"):
    if not ENDPOINT.match(value or ""):
        raise ProfileError(f"{what} must be an exact lowercase host:port without wildcards: {value!r}")
    port = int(value.rsplit(":", 1)[1])
    if port > 65535:
        raise ProfileError(f"{what} port out of range: {value!r}")
    return value


def resolve(provider=None, endpoint=None, key_var=None, registry=DEFAULT_REGISTRY, harness=None):
    """Build the admitted profile for a workload VM. Exactly one model service, one harness."""
    if harness is not None and harness not in HARNESSES:
        raise ProfileError(f"--harness must be one of {', '.join(HARNESSES)}")
    if provider and (endpoint or key_var):
        raise ProfileError("Use either --provider or --endpoint with --key-var, not both")
    if provider:
        if provider not in PROVIDERS:
            raise ProfileError(f"Unknown provider {provider!r}; presets: {', '.join(sorted(PROVIDERS))}")
        preset = PROVIDERS[provider]
        endpoints, key_var = list(preset["endpoints"]), preset["key_var"]
    else:
        if not (endpoint and key_var):
            raise ProfileError("A custom provider needs both --endpoint HOST:PORT and --key-var NAME")
        endpoints = [check_endpoint(endpoint)]
        if not KEY_VAR.match(key_var):
            raise ProfileError(f"--key-var must look like an environment variable name: {key_var!r}")
        provider = f"custom:{endpoint}"
    registries = expand_registries(registry)
    if set(registries) & set(endpoints):
        raise ProfileError("The registry and the model endpoint must differ")
    return {"provider": provider, "endpoints": endpoints, "key_var": key_var, "registry": registries,
            "harness": harness or default_harness(provider)}


def expand_registries(registry):
    """None -> no registry; a name from REGISTRIES or host:port, or a list of those."""
    if registry is None:
        return []
    items = [registry] if isinstance(registry, str) else list(registry)
    hosts = []
    for item in items:
        for host in REGISTRIES.get(item, [item]):
            hosts.append(check_endpoint(host, "--registry"))
    return sorted(set(hosts))


def allowed(profile):
    """The complete workload allowlist derived from a profile (empty = offline)."""
    registry = profile.get("registry") or []
    return set(profile["endpoints"]) | set([registry] if isinstance(registry, str) else registry)


def describe(profile):
    if not profile.get("endpoints"):
        return "offline reproducer profile (no model endpoint, no key)"
    registry = profile.get("registry") or []
    registry = [registry] if isinstance(registry, str) else registry
    key = f"key variable {profile['key_var']}" if profile.get("key_var") else "harness login (no key variable)"
    return (f"provider {profile['provider']}: {', '.join(profile['endpoints'])}; "
            f"{key}; registry {', '.join(registry) or 'none'}; "
            f"harness {profile.get('harness', 'opencode')}")
