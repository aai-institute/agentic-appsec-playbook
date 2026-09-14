# appsec-sbx

Host-side wrapper for the AppSec shell on Docker Sandboxes (`sbx`): lifecycle, policy lock,
explicit import/export, skills, reproducers. Python 3.9+, standard library only.

- **Use it:** [Getting started](../../docs/src/content/docs/getting-started.md) and the
  [user guide](../../docs/src/content/docs/sandbox/sbx/index.md).
- **Why it is built this way:** [design notes](../../design/sbx-internals.md) and the
  [threat model](../../design/threat-model.md).
- **What was verified where:** [acceptance record](../../records/sbx-acceptance.md).

Install from Git with `uv tool install 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx'`,
or run from this checkout with `../make-appsec-sbx.sh` (macOS, Linux) or `python -m appsec_sbx`
from this directory.

Tests:

```sh
python3 -m unittest discover -s sandbox/sbx -p 'test_*.py' -v
bash -n sandbox/make-appsec-sbx.sh sandbox/sbx/appsec_sbx/guest/bootstrap.sh
```

Licensed under Apache-2.0 (see the repository `LICENSE`).
