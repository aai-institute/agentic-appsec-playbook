# appsec-sbx

`appsec-sbx` runs agents in Docker Sandboxes (`sbx`) and manages their VMs from your machine: lifecycle, policy lock,
explicit import/export, skills, reproducers. Python 3.9+, standard library only.

- **Use it:** [Getting started](../../docs/src/content/docs/getting-started.md) and the
  [user guide](../../docs/src/content/docs/sandbox/sbx/index.md).
- **Why it is built this way:** [design notes](../../design/sbx-internals.md) and the
  [threat model](../../docs/src/content/docs/sandbox/threat-model.md).
- **What was verified where:** [acceptance record](../../records/sbx-acceptance.md).

Install from Git with `uv tool install 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx'`,
or run `uv run appsec-sbx` from this directory. Alternatives are
`../make-appsec-sbx.sh` (macOS, Linux) or `python -m appsec_sbx`.

Tests:

```sh
python3 -m unittest discover -s sandbox/sbx -p 'test_*.py' -v
bash -n sandbox/make-appsec-sbx.sh sandbox/sbx/appsec_sbx/guest/bootstrap.sh
```

Licensed under Apache-2.0 (see the repository `LICENSE`).
