import sys

# Checkout runs (make-appsec-sbx.sh, python -m) skip the installer's requires-python check,
# and the python3 that ships with macOS is 3.9.
if sys.version_info < (3, 10):
    sys.exit(f"appsec-sbx requires Python 3.10 or newer (found {sys.version.split()[0]}). "
             "Install it with uv (Getting started) or run `uv run appsec-sbx` from sandbox/sbx.")

from .cli import main  # noqa: E402

main()
