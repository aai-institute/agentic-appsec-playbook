# Local evidence removed from reader-facing docs

Archived 17 September 2026. These excerpts preserve development observations
and their original limits; this move adds no new validation. Platform details
remain in [the acceptance record](../records/sbx-acceptance.md). Some discovery
run details refer to the private demo workspace.

## docs/src/content/docs/discovery/review-skills.md

To use the revision tested in the September 16 Claude Code review, add
`--ref d3bea6b5793b5f3d59a75ebe69a58efa88383145` to the installation command.
That run installed the skills from a local checkout into sbx 0.43.0 on macOS.

Installing directly from GitHub into OpenCode 1.18.29 also succeeded on that
setup and copied nine skills containing 19 files. A review using GLM-5.3-Flash
through OpenRouter completed six review tasks, seven scoring tasks and both
reports in 45 minutes and 19 seconds. It exceeded the planned 20-minute budget
and reported incorrect counts for low-confidence findings and templates.
Usage statistics also showed web requests despite instructions to analyse
only the supplied source; the VM blocked requests to hosts outside its
allowlist. The completed run shows that the skills can be installed and used,
but their output and adherence to instructions still need review.

## docs/src/content/docs/tools/shortlist.md

- **Maturity:** an established prompt with a small setup burden. September
  research flagged maintenance drift and reported defects in the Action;
  test that integration separately before relying on it in CI.

## docs/src/content/docs/tools/shortlist.md

- **Local evidence:** discovery runs completed in the playbook sandbox. The
  September 16 OpenCode run took 45m 19s against a 20-minute budget, miscounted
  parts of its report and attempted blocked web fetches. Allow time for a
  dry run; completion alone does not establish correct behavior.

## docs/src/content/docs/sandbox/no-regret-measures.md

In this playbook's own runs on 2026-09-10, three models tried to install the
target's dependencies from PyPI despite a discovery-only prompt, one of them
with certificate checks disabled. The allowlist blocked them.

## docs/src/content/docs/sandbox/no-regret-measures.md

This playbook's five runs on one small target cost between three cents and
three dollars on API billing, plus an unmetered slice of a seat.

## docs/src/content/docs/getting-started.md

Desktop is not required. Tested versions and hosts: sbx `0.42.1` and `0.43.0` on
macOS (Apple silicon), Windows 11 x64 and Linux x86_64.

## docs/src/content/docs/sandbox/sbx/providers.md

`shell --key` with a `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`, is a months-long
bearer token and was rejected by the API in the one trial so far. Either way the VM runs with
the whole seat's authority and the budget is the seat's rate limit, not a spend cap.

## docs/src/content/docs/sandbox/sbx/providers.md

Expect these denials in the policy log at every Claude Code start, all harmless: a clone of
the plugin marketplace from GitHub, `downloads.claude.ai`, and a dozen attempts at
`mcp-proxy.anthropic.com`.

## docs/src/content/docs/sandbox/sbx/providers.md

VM makes no attempts to download plugin bundles. Expect denied GitHub attempts at startup
(update check, tip banner); they are harmless.

## docs/src/content/docs/sandbox/threat-model.md

Reviewed against the wrapper source and recorded tests on **16 September
2026**. This review adds no new VM test evidence. Platform and version limits
are in the [acceptance record](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/records/sbx-acceptance.md).

## docs/src/content/docs/sandbox/threat-model/controls.md

## Evidence and implementation

The [acceptance record](https://github.com/aai-institute/agentic-appsec-playbook/blob/main/records/sbx-acceptance.md)
covers sbx 0.42.1 on macOS, Windows 11 x64 and Linux x86_64. The macOS 0.43.0
discovery runs cover a narrower workflow; they did not repeat reset,
reproducer and full network checks. No record establishes complete [R1–R8](/sandbox/threat-model/acceptance/#requirements)
acceptance.
