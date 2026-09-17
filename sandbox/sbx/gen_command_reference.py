"""Render the wrapper's command reference page from its own argparse help.

    python3 sandbox/sbx/gen_command_reference.py > docs/src/content/docs/sandbox/sbx/commands.md

The unit test `test_command_reference_page_matches_cli_help` fails when the page and the
CLI drift apart, so edit the help strings in appsec_sbx/cli.py and regenerate.
"""
import os
import sys
from pathlib import Path

os.environ["COLUMNS"] = "88"  # argparse wraps to the terminal; pin it so the output is stable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from appsec_sbx.cli import ACTIONS, build_parser  # noqa: E402

PAGE = Path(__file__).resolve().parents[2] / "docs/src/content/docs/sandbox/sbx/commands.md"

HEAD = """---
title: "Command reference"
description: "Usage and options for every appsec-sbx command."
---

Use `appsec-sbx --help` to list commands and `appsec-sbx ACTION --help` for
help with one command. Every action takes the sandbox name as its first
argument and defaults to `appsec-sbx`. From a checkout,
`./sandbox/make-appsec-sbx.sh` and `python -m appsec_sbx` take the same arguments.

"""


def render():
    parser = build_parser()
    actions = parser._subparsers._group_actions[0].choices  # name -> subparser, definition order
    out = [HEAD]
    out.append("```text\n" + parser.format_help().rstrip() + "\n```\n")
    out.append("\n## Actions\n\n| Action | Purpose |\n|---|---|\n")
    for name in actions:
        out.append(f"| [`{name}`](#{name}) | {ACTIONS[name][0]} |\n")
    for name, sub in actions.items():
        # usage line plus the argument sections; the description is rendered as prose above them
        help_text = sub.format_help()
        arguments = help_text[help_text.index("\npositional arguments:") + 1:].rstrip()
        out.append(f"\n### {name}\n\n{ACTIONS[name][1]}\n\n```text\n{sub.format_usage().rstrip()}\n\n{arguments}\n```\n")
    return "".join(out)


if __name__ == "__main__":
    sys.stdout.write(render())
