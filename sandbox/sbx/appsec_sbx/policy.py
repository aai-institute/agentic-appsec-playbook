"""Effective-policy compilation for one sbx sandbox.

Deny wins in sbx. The wrapper never edits global policy; it subtracts every
inherited network grant with a sandbox-scoped deny and adds only the admitted
endpoints. A broad inherited grant overlapping an admitted endpoint cannot be
narrowed safely, so that configuration is refused.
"""
import fnmatch
import json

# Sandbox-scoped denies on every managed VM (threat model T15/T16, M19/M27): the host, the LAN
# and VPN ranges, loopback, link-local, carrier-grade NAT, multicast and the reserved blocks, by
# address family. Since sbx 0.49.1 a CIDR deny also matches the address an allowed hostname
# resolves to, which is what turns these into a resolution-time control; the same change made
# the earlier catch-alls (0.0.0.0/0, ::/0) cut off every allowed hostname. Public addresses
# reached by number fall to sbx's global default deny. Not listed: ::ffff:0:0/96, because sbx
# matches plain IPv4 destinations against it as well (checked on 0.49.1, 2026-10-21); mapped
# forms such as ::ffff:127.0.0.1 already hit the IPv4 rules.
DENY = {
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12",
    "192.168.0.0/16", "224.0.0.0/4", "240.0.0.0/4",
    "::/128", "::1/128", "fc00::/7", "fe80::/10", "fec0::/10", "ff00::/8",
    "localhost", "host.docker.internal",
}
# `sbx policy check` targets that must be denied after the lock. The private ones must hit one
# of the DENY rules (an explicit deny); the public ones fall to the global default.
PRIVATE_PROBES = {"10.0.0.1:443", "172.16.0.1:443", "192.168.0.1:443", "169.254.169.254:443",
                  "127.0.0.1:443", "100.64.0.1:443", "[::1]:443", "[fe80::1]:443", "[fd00::1]:443",
                  "localhost:18080"}
PROBES = PRIVATE_PROBES | {"example.com:443", "1.1.1.1:443"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical(rules):
    """Include IDs/metadata: policy edits require a new clean sandbox."""
    return sorted(rules, key=lambda r: json.dumps(r, sort_keys=True))


def compile_denies(rules, allowed):
    """Subtract admitted endpoints from inherited grants without broadening globals.

    fnmatch is deliberately conservative (a * may match dots here).
    """
    denies = set(DENY)
    for rule in rules:
        if rule.get("resource_type") != "network" or rule.get("decision") != "allow":
            continue
        for resource in rule["resources"]:
            if resource in allowed:
                continue
            for endpoint in allowed:
                host = endpoint.rsplit(":", 1)[0]
                require(not (fnmatch.fnmatchcase(endpoint, resource) or
                             fnmatch.fnmatchcase(host, resource)),
                        f"Inherited global grant {resource!r} (rule {rule.get('id', '?')}) is broader than "
                        f"the profile's {endpoint} and cannot be narrowed: sbx deny wins, so denying it would "
                        f"deny {endpoint} too, and leaving it would allow more than the profile. Remove or "
                        f"narrow that global rule (sbx policy rm network --id {rule.get('id', '<id>')}), or "
                        "re-initialise the global policy as deny-all (sbx policy reset, then pick deny-all at "
                        "its prompt; this stops running sandboxes and drops all sandbox-scoped rules), then retry; "
                        "the wrapper never edits global policy")
            denies.add(resource)
    return denies


def validate_policy(rules, name, allowed):
    """Check the recorded effective policy against the admitted allowlist."""
    allowed = set(allowed)
    scoped = [r for r in rules if r["scope"] == f"sandbox:{name}" and r["resource_type"] == "network"]
    grants = {p for r in scoped if r["decision"] == "allow" for p in r["resources"]}
    denies = {p for r in scoped if r["decision"] == "deny" for p in r["resources"]}
    require(grants == allowed, "Unexpected sandbox network grant")
    if allowed:
        needed = compile_denies([r for r in rules if r["scope"] == "global"], allowed)
    else:
        needed = DENY | {"**"}
    require(needed <= denies, "Inherited network grant changed during policy compilation")
