#!/usr/bin/env bash
# macOS/Linux host shim; see sbx/README.md. No workspace is mounted.
# Windows: python -m appsec_sbx from sandbox/sbx, or install the package (appsec-sbx).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="$HERE/sbx${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m appsec_sbx "$@"
