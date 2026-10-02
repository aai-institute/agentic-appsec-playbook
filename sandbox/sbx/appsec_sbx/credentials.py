"""Host side of proxy-managed model credentials (threat model M17; T24 T25).

The raw key stays on the host: the VM's sandbox kit declares the key variable as
proxy-managed, so the workload holds the constant sentinel and sbx's proxy writes the
stored value into the declared header on requests to the declared hosts. Two host
artefacts make that work without prompts (M25):

- the kit directory rendered per VM from the provider profile, passed to `sbx create`;
- a credential *binding* in sbx's bindings file, which approves a third-party kit's use
  of the service and its domains. Without it `sbx create` withholds the credential.

Behaviour checked with a dummy value on sbx 0.46.0 (macOS, 2026-10-02):
design/sbx-managed-credentials.md. The bindings path follows Docker's documentation
(`~/.config/sbx/credentials.yaml`, `%APPDATA%\\sbx\\credentials.yaml`); the Windows path
is not yet exercised.
"""
import json
import os
from pathlib import Path
import re

from .hostos import IS_WINDOWS, private_dir
from .policy import require

KIT_NAME = "appsec-shell"
KIT_VERSION = "0.2.0"
IMAGE = "docker/sandbox-templates:shell-docker"


def bindings_path():
    if IS_WINDOWS:
        return Path(os.environ.get("APPDATA", "~")).expanduser() / "sbx" / "credentials.yaml"
    return Path("~/.config/sbx/credentials.yaml").expanduser()


def _yaml(value):
    # YAML accepts JSON scalars; this keeps hosts, headers and formats unambiguous.
    return json.dumps(value)


def render_kit(directory, credential):
    """Write the sandbox kit for one VM and return its directory.

    Without a credential (offline reproducers, seat logins) the kit declares none, so the
    guest receives neither a sentinel nor an injection.
    """
    directory = Path(directory)
    private_dir(directory)
    lines = [
        f"schemaVersion: {_yaml('2')}",
        "kind: sandbox",
        f"name: {KIT_NAME}",
        f"version: {_yaml(KIT_VERSION)}",
        "description: AppSec provisioning shell; workload entry is controlled by appsec-sbx.",
        "sandbox:",
        f"  image: {IMAGE}",
        "  entrypoint: [bash, -l]",
    ]
    if credential:
        lines += [
            "credentials:",
            f"  - service: {credential['service']}",
            "    description: model credential held by the host proxy (appsec-sbx key)",
            "    apiKey:",
            f"      name: {credential['variable']}",
            "      proxyManaged: true",
            "      inject:",
        ]
        for entry in credential["inject"]:
            lines += [f"        - domain: {_yaml(entry['domain'])}",
                      f"          header: {_yaml(entry['header'])}",
                      f"          format: {_yaml(entry['format'])}"]
    (directory / "spec.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return directory


def _entry_block(lines, start, indent):
    """Lines of the mapping entry at `start`: those indented deeper than `indent`."""
    block = []
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        block.append(line)
    return block


def _bound_domains(block):
    for i, line in enumerate(block):
        head, sep, tail = line.partition("domains:")
        if not sep or head.strip():
            continue
        tail = tail.strip()
        if tail.startswith("["):
            return {d.strip().strip("'\"") for d in tail.strip("[]").split(",") if d.strip()}
        found = set()
        for item in block[i + 1:]:
            if not item.strip().startswith("- "):
                break
            found.add(item.strip()[2:].strip().strip("'\""))
        return found
    return set()


def ensure_binding(credential, path=None):
    """Approve the kit's service and domains in sbx's bindings file; returns what was done.

    The file may carry an operator's own bindings, so it is edited line-wise: an existing
    entry for the service is accepted when it already covers the domains and refused
    otherwise; a missing entry is inserted under `bindings:`.
    """
    path = Path(path) if path else bindings_path()
    service = credential["service"]
    domains = sorted({entry["domain"] for entry in credential["inject"]})
    block = [f"  {service}:", "    apiKey:", f"      domains: [{', '.join(domains)}]"]
    if not path.exists():
        private_dir(path.parent)
        path.write_text("\n".join(["bindings:", *block]) + "\n", encoding="utf-8")
        return "written"
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if re.fullmatch(rf"\s+{re.escape(service)}:\s*", line):
            indent = len(line) - len(line.lstrip())
            found = _bound_domains(_entry_block(lines, i, indent))
            require(set(domains) <= found,
                    f"{path} already binds {service} to {sorted(found) or 'nothing'}, not to {domains}; "
                    "edit or remove that entry")
            return "present"
    for i, line in enumerate(lines):
        if re.fullmatch(r"bindings:\s*", line):
            children = [l for l in _entry_block(lines, i, 0) if l.strip()]
            indent = (len(children[0]) - len(children[0].lstrip())) if children else 2
            shifted = [" " * (indent - 2) + l for l in block] if indent >= 2 else block
            lines[i + 1:i + 1] = shifted
            break
    else:
        lines += ["bindings:", *block]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "added"
