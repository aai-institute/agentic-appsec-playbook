# Agentic AppSec Pilot Playbook

Run open-source, AI-agent-based application security tooling on your own code: contained
first, then measured, so that a local go/no-go decision comes from your own evidence rather
than from public leaderboards. For AppSec and DevSecOps engineers who own security tooling in
an organisation and can run CLI tools against a test repository.

**Status: pre-release working material.** Pages carry their own status lines; operational
claims are tagged (`checked`, `to-verify`, …).

## Start here

The user-facing documentation is a [Starlight](https://starlight.astro.build/) site under
[`docs/`](docs/); its pages are plain Markdown and read fine on GitHub:

1. [Getting started](docs/src/content/docs/getting-started.md): install Docker Sandboxes and
   the `appsec-sbx` wrapper, then run a first contained review of your repository.
2. [No-regret measures](docs/src/content/docs/sandbox/no-regret-measures.md): the six things
   that must hold before the first agent run.
3. [AppSec shell](docs/src/content/docs/sandbox/sbx/index.md): the wrapper's user guide.
4. [Tool shortlist](docs/src/content/docs/tools/shortlist.md),
   [triage rubric](docs/src/content/docs/triage/triage-rubric.md),
   [observations table](docs/src/content/docs/triage/observations.md),
   [validation loop](docs/src/content/docs/validation/validation-loop-template.md),
   [hardening checklist](docs/src/content/docs/hardening/hardening-checklist.md).

To browse the site locally:

```sh
cd docs && npm install && npm run dev
```

Install the wrapper without cloning:

```sh
uv tool install 'git+https://github.com/aai-institute/agentic-appsec-playbook.git#subdirectory=sandbox/sbx'
```

## Repository layout

| Directory | Audience | Contents |
|---|---|---|
| [`docs/`](docs/) | operators | The site: getting started, the five steps, the wrapper's user guide |
| [`sandbox/`](sandbox/) | operators, contributors | Code: the `appsec-sbx` package (`sandbox/sbx/`), the review skill (`sandbox/skills/`), the frozen Colima scripts |
| [`design/`](design/) | maintainers, reviewers | Threat model, sandbox backend comparison, wrapper design notes, Colima reference, CI runner design, working-group notes |
| [`records/`](records/) | reviewers | Dated evidence: platform acceptance records |

## Contributing

Issues and pull requests are welcome while the repository is private to the working group.
Changes to anything under `sandbox/` cite a threat row (`T…`) and register a measure (`M…`) in
the [threat model](design/threat-model.md) first. Guest-side files keep LF line endings
(`.gitattributes` enforces it).

## License

Code (`sandbox/`, `docs/` site configuration) is licensed under
[Apache-2.0](LICENSE). Documentation (Markdown content under `docs/`, `design/` and
`records/`) is licensed under [CC BY-SA 4.0](LICENSE-docs). Third-party notices are in
[`NOTICE`](NOTICE). Maintained by the appliedAI Institute for Europe gGmbH.
