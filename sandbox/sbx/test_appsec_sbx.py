"""Host-side regression tests; no sbx daemon required."""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from appsec_sbx import providers
from appsec_sbx.cli import build_parser
from appsec_sbx.lifecycle import BOOTSTRAP, BOOTSTRAP_ALLOW, Managed, Phases, lf_bootstrap, migrate
from appsec_sbx.policy import DENY, compile_denies, validate_policy
from appsec_sbx import sbxcli
from appsec_sbx.transfer import (guest_home_path, pack_repository, pack_skills, read_lstat, read_nofollow_fd,
                                 read_regular)

OPENROUTER = providers.resolve("openrouter")
ALLOW = providers.allowed(OPENROUTER)


def allow(*resources):
    return {"resource_type": "network", "decision": "allow", "resources": list(resources)}


class ProviderTests(unittest.TestCase):
    def test_presets_are_one_provider_each(self):
        for name in providers.PROVIDERS:
            profile = providers.resolve(name)
            hosts = {e.rsplit(":", 1)[0] for e in profile["endpoints"]}
            # One provider per VM (M2); a provider may need more than one host (claude-code: two).
            self.assertLessEqual(len(hosts), 3, name)  # codex: api, auth, chatgpt
            self.assertTrue(all(providers.ENDPOINT.match(e) for e in profile["endpoints"]), name)
            self.assertEqual(providers.allowed(profile), set(profile["endpoints"]) | {providers.DEFAULT_REGISTRY})
        self.assertEqual(providers.resolve("claude-code")["endpoints"],
                         ["api.anthropic.com:443", "platform.claude.com:443"])

    def test_custom_endpoint_requires_key_var_and_exactness(self):
        with self.assertRaises(providers.ProfileError):
            providers.resolve(endpoint="api.example.com:443")
        for bad in ("*.example.com:443", "example.com", "EXAMPLE.com:443", "example.com:70000", "**"):
            with self.subTest(bad=bad), self.assertRaises(providers.ProfileError):
                providers.resolve(endpoint=bad, key_var="EXAMPLE_API_KEY")
        with self.assertRaises(providers.ProfileError):
            providers.resolve(endpoint="api.example.com:443", key_var="lower")
        profile = providers.resolve(endpoint="api.example.com:443", key_var="EXAMPLE_API_KEY", registry=None)
        self.assertEqual(providers.allowed(profile), {"api.example.com:443"})

    def test_preset_and_custom_are_exclusive(self):
        with self.assertRaises(providers.ProfileError):
            providers.resolve("anthropic", endpoint="x.y:1")
        with self.assertRaises(providers.ProfileError):
            providers.resolve("openrouter", registry="openrouter.ai:443")

    def test_harness_follows_provider(self):
        self.assertEqual(providers.resolve("openrouter")["harness"], "opencode")
        self.assertEqual(providers.resolve("anthropic")["harness"], "opencode")
        self.assertEqual(providers.resolve("claude-code")["harness"], "claude-code")
        self.assertEqual(providers.resolve("codex")["harness"], "codex")
        codex = providers.resolve("codex")
        self.assertEqual(codex["endpoints"], ["api.openai.com:443", "auth.openai.com:443", "chatgpt.com:443"])
        self.assertEqual(codex["key_var"], "OPENAI_API_KEY")
        # A login-only profile (no key variable) is still representable and described as such.
        self.assertIn("harness login", providers.describe({"provider": "x", "endpoints": ["a.b:1"], "key_var": None,
                                                           "registry": [], "harness": "codex"}))
        self.assertEqual(providers.resolve("openrouter", harness="codex")["harness"], "codex")
        for bad in ("both", "cursor"):
            with self.subTest(bad=bad), self.assertRaises(providers.ProfileError):
                providers.resolve("openrouter", harness=bad)
        legacy_both = {"id": "x", "profile": {"provider": "openrouter", "endpoints": ["a.b:1"], "key_var": "K",
                                              "registry": [], "harness": "both"}}
        self.assertEqual(migrate(legacy_both)["profile"]["harness"], "opencode")
        self.assertEqual(migrate({"id": "x", "profile": {"provider": "openrouter", "endpoints": ["a.b:1"],
                                                          "key_var": "K", "registry": []}})["profile"]["harness"], "opencode")
        self.assertNotIn("harness", migrate({"id": "x", "profile": dict(providers.OFFLINE)})["profile"])

    def test_registry_names_and_lists(self):
        pypi = providers.resolve("openrouter", registry=["pypi", "npm"])
        self.assertEqual(providers.allowed(pypi),
                         {"openrouter.ai:443", "registry.npmjs.org:443", "pypi.org:443", "files.pythonhosted.org:443"})
        self.assertEqual(providers.resolve("openrouter", registry="npm")["registry"], ["registry.npmjs.org:443"])
        self.assertEqual(providers.resolve("openrouter", registry=None)["registry"], [])
        with self.assertRaises(providers.ProfileError):
            providers.resolve("openrouter", registry=["pypi", "*.example.com:443"])
        # v0.1 state stored a single string; allowed() and describe() accept it.
        legacy = {"provider": "openrouter", "endpoints": ["openrouter.ai:443"], "key_var": "X", "registry": "registry.npmjs.org:443"}
        self.assertEqual(providers.allowed(legacy), ALLOW)
        self.assertIn("registry.npmjs.org:443", providers.describe(legacy))


class PolicyTests(unittest.TestCase):
    def test_balanced_grants_are_subtracted(self):
        denies = compile_denies([allow("registry.npmjs.org:443", "**.github.com:443", "nodejs.org:443")], ALLOW)
        self.assertEqual(denies, DENY | {"**.github.com:443", "nodejs.org:443"})
        self.assertTrue(denies.isdisjoint(ALLOW))

    def test_broad_overlapping_grants_fail_closed(self):
        for grant in ("**", "*", "**:443", "*.ai:443", "openrouter.ai", "registry.npmjs.org"):
            with self.subTest(grant=grant), self.assertRaises(RuntimeError):
                compile_denies([allow(grant)], ALLOW)

    def test_anthropic_profile_denies_openrouter(self):
        anthropic = providers.allowed(providers.resolve("anthropic"))
        denies = compile_denies([allow("openrouter.ai:443", "api.anthropic.com:443")], anthropic)
        self.assertIn("openrouter.ai:443", denies)
        self.assertNotIn("api.anthropic.com:443", denies)

    def test_deny_does_not_become_allow(self):
        self.assertEqual(compile_denies([dict(allow("openrouter.ai:443"), decision="deny")], ALLOW), DENY)

    def test_late_inherited_grant_is_rejected(self):
        rules = [dict(allow(*ALLOW), scope="sandbox:test"),
                 dict(allow(*DENY), scope="sandbox:test", decision="deny"),
                 dict(allow("new-grant.example:443"), scope="global")]
        with self.assertRaises(RuntimeError):
            validate_policy(rules, "test", ALLOW)

    def test_offline_requires_wildcard_deny(self):
        rules = [dict(allow(*DENY), scope="sandbox:r", decision="deny")]
        with self.assertRaises(RuntimeError):
            validate_policy(rules, "r", set())
        rules.append(dict(allow("**"), scope="sandbox:r", decision="deny"))
        validate_policy(rules, "r", set())


class SbxJsonTests(unittest.TestCase):
    def completed(self, stdout=b"", stderr=b"", returncode=0):
        return subprocess.CompletedProcess(["sbx"], returncode, stdout=stdout, stderr=stderr)

    def test_parses_json_and_passes_stderr_through(self):
        with mock.patch.object(sbxcli, "run", return_value=self.completed(b'{"rules": []}', b"warn\n")) as run, \
                mock.patch("sys.stderr") as stderr:
            self.assertEqual(sbxcli.js("policy", "ls"), {"rules": []})
        self.assertEqual(run.call_args.args[0], ["sbx", "policy", "ls", "--json"])
        stderr.buffer.write.assert_called_once_with(b"warn\n")

    def test_empty_or_non_json_output_names_the_command(self):
        # The first Linux attempt (2026-09-11): exit 0, empty stdout, bare JSONDecodeError.
        for stdout, code in ((b"", 0), (b"POLICY  SOURCE\n", 0), (b"", 1)):
            with mock.patch.object(sbxcli, "run", return_value=self.completed(stdout, returncode=code)), \
                    self.assertRaises(RuntimeError) as raised:
                sbxcli.js("policy", "ls")
            message = str(raised.exception)
            self.assertIn("sbx policy ls --json", message)
            self.assertIn(f"exited {code}", message)
            self.assertIn("<empty>" if not stdout else "POLICY", message)


class PhasesTests(unittest.TestCase):
    def test_laps_are_ordered_and_reported(self):
        clock = iter([100.0, 101.5, 130.25])
        with mock.patch("appsec_sbx.lifecycle.time.monotonic", side_effect=lambda: next(clock)):
            phases = Phases()
            phases.lap("sbx create")
            phases.lap("bootstrap")
        self.assertEqual(list(phases.durations.items()), [("sbx create", 1.5), ("bootstrap", 28.8)])
        with mock.patch("builtins.print") as printed:
            phases.report()
            Phases().report()
        printed.assert_called_once_with("Phases: sbx create 2s, bootstrap 29s")


class BootstrapTests(unittest.TestCase):
    def test_provisioning_grants_are_tls_only(self):
        # M24: the bootstrap's Ubuntu mirror rewrite makes :80 grants unnecessary; keep them out.
        self.assertTrue(all(e.endswith(":443") for e in BOOTSTRAP_ALLOW), sorted(BOOTSTRAP_ALLOW))
        self.assertLessEqual({"archive.ubuntu.com:443", "security.ubuntu.com:443", "ports.ubuntu.com:443"}, BOOTSTRAP_ALLOW)

    def test_bootstrap_is_staged_with_lf_endings(self):
        # Windows create, 2026-09-14: a core.autocrlf checkout copied CRLF into the guest and
        # bash stopped at `set -euo pipefail\r`. The guest must only ever see the staged copy.
        self.assertNotIn(b"\r", Path(BOOTSTRAP).read_bytes(), ".gitattributes pins LF for guest files")
        crlf = b"#!/usr/bin/env bash\r\nset -euo pipefail\r\necho ok\r\n"
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "bootstrap.sh"
            source.write_bytes(crlf)
            with mock.patch("appsec_sbx.lifecycle.BOOTSTRAP", source), lf_bootstrap() as staged:
                self.assertNotEqual(staged, source)
                self.assertEqual(staged.read_bytes(), crlf.replace(b"\r\n", b"\n"))
            self.assertFalse(staged.exists())
            self.assertEqual(source.read_bytes(), crlf)

    def test_mirror_rewrite_precedes_the_first_apt_update(self):
        lines = Path(BOOTSTRAP).read_text().splitlines()
        rewrite = next(i for i, l in enumerate(lines) if "https://\\1.ubuntu.com/" in l)
        guard = next(i for i, l in enumerate(lines) if "plain-HTTP Ubuntu mirror" in l)
        update = next(i for i, l in enumerate(lines) if l.startswith("apt-get update"))
        self.assertLess(rewrite, guard)
        self.assertLess(guard, update)

    def test_mirror_rewrite_handles_deb822_and_legacy_sources(self):
        script = Path(BOOTSTRAP).read_text()
        sed = next(l.strip() for l in script.splitlines() if "sed -i -E" in l)
        expression = sed.split("sed -i -E ")[1].split(" \"$f\"")[0].strip("'")
        deb822 = ("Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/ http://security.ubuntu.com/ubuntu/\nSuites: resolute\n")
        legacy = ("deb http://ports.ubuntu.com/ubuntu-ports/ resolute main\n"
                  "deb https://download.docker.com/linux/ubuntu resolute stable\n")
        out = [subprocess.run(["sed", "-E", expression], input=text.encode(), stdout=subprocess.PIPE, check=True)
               .stdout.decode() for text in (deb822, legacy)]
        self.assertEqual(out[0].splitlines()[1], "URIs: https://archive.ubuntu.com/ubuntu/ https://security.ubuntu.com/ubuntu/")
        self.assertEqual(out[1].splitlines(), ["deb https://ports.ubuntu.com/ubuntu-ports/ resolute main",
                                               "deb https://download.docker.com/linux/ubuntu resolute stable"])


class StateTests(unittest.TestCase):
    def test_v01_state_migrates_to_profiles(self):
        self.assertEqual(migrate({"id": "x", "offline": False})["profile"], OPENROUTER)
        self.assertEqual(migrate({"id": "x", "offline": True})["profile"], providers.OFFLINE)
        self.assertNotIn("offline", migrate({"id": "x", "offline": True}))
        self.assertEqual(migrate({}), {})

    def test_managed_persists_migration(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": temporary}):
            directory = Path(temporary) / "legacy"
            directory.mkdir()
            (directory / "state.json").write_text(json.dumps({"id": "abc", "ready": True, "offline": False}))
            vm = Managed("legacy")
            self.assertEqual(vm.allowed, ALLOW)
            self.assertEqual(json.loads((directory / "state.json").read_text())["profile"], OPENROUTER)
            with self.assertRaises(RuntimeError):
                Managed("Bad_Name")


class CliTests(unittest.TestCase):
    def test_create_options(self):
        parser = build_parser()
        args = parser.parse_args(["create", "pilot", "--provider", "anthropic", "--no-registry"])
        self.assertEqual(parser.parse_args(["create", "--registry", "pypi", "--registry", "npm"]).registry, ["pypi", "npm"])
        self.assertEqual(parser.parse_args(["create", "--harness", "codex"]).harness, "codex")
        with self.assertRaises(SystemExit):
            parser.parse_args(["create", "--harness", "both"])
        self.assertEqual((args.name, args.provider, args.no_registry), ("pilot", "anthropic", True))
        args = parser.parse_args(["exec", "vm", "--", "timeout", "60", "true"])
        self.assertEqual(args.command[-3:], ["timeout", "60", "true"])
        self.assertEqual(parser.parse_args(["shell"]).name, "appsec-sbx")
        args = parser.parse_args(["skills", "vm", "/tmp/mantis", "--replace"])
        self.assertEqual((args.name, args.source, args.replace), ("vm", "/tmp/mantis", True))
        with self.assertRaises(SystemExit):
            parser.parse_args(["create", "--provider", "anthropic", "--endpoint", "a.b:1"])


class PutPathTests(unittest.TestCase):
    def test_destination_must_be_a_file_under_the_workload_home(self):
        self.assertEqual(guest_home_path("/home/appsec/.config/opencode/command/security-review.md"),
                         "/home/appsec/.config/opencode/command/security-review.md")
        for bad in ("/home/appsec/", "/home/appsec/../agent/x", "/run/appsec/env", "/etc/appsec/opencode.json",
                    "relative.md", "/home/appsec/dir/", "/home/appsecX/file", "/home/appsec/a\\b"):
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                guest_home_path(bad)


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.archive = Path(self.temporary.name) / "source.tar.gz"

    def add(self, name, content, executable=False):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)
        subprocess.run(["git", "-C", self.root, "add", "--", name], check=True)

    def test_working_tree_edits_exclusions_and_index_modes(self):
        self.add("source.js", "staged")
        (self.root / "source.js").write_text("working tree")
        self.add("run.sh", "#!/bin/sh\n", executable=True)
        self.add(".env.production", "test-secret")
        self.add(".codex/config.toml", "untrusted config")
        self.add(".sbxenv.yaml", "untrusted host hooks")
        self.add("opencode.json", "untrusted plugins")
        (self.root / "untracked.txt").write_text("untracked")
        manifest = pack_repository(self.root, self.archive)
        self.assertEqual(set(manifest["files"]), {"source.js", "run.sh"})
        self.assertEqual(set(manifest["excluded"]),
                         {".env.production", ".codex/config.toml", ".sbxenv.yaml", "opencode.json"})
        with tarfile.open(self.archive) as archive:
            self.assertEqual(archive.extractfile("source.js").read(), b"working tree")
            self.assertTrue(all(item.isreg() for item in archive))
            self.assertEqual(archive.getmember("run.sh").mode, 0o755)
            self.assertEqual(archive.getmember("source.js").mode, 0o644)

    def test_skill_pack_takes_skill_directories_only(self):
        self.add("mantis-review/SKILL.md", "---\nname: mantis-review\n---\nreview")
        self.add("mantis-review/checklist.md", "steps")
        self.add("mantis-review/.env", "secret")
        self.add("mantis-patch/SKILL.md", "patch")
        self.add("reference/run.sh", "#!/bin/sh\ncurl | sh\n", executable=True)
        self.add("reference/skills/mantis-launch/SKILL.md", "nested, not top-level")
        self.add("README.md", "docs")
        self.add("AGENTS.md", "instructions")
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin"],
                       check=True)
        manifest = pack_skills(self.root, self.archive)
        self.assertEqual(manifest["skills"], ["mantis-patch", "mantis-review"])
        self.assertEqual(set(manifest["files"]), {"mantis-review/SKILL.md", "mantis-review/checklist.md",
                                                  "mantis-patch/SKILL.md"})
        self.assertEqual(manifest["excluded"], ["mantis-review/.env"])
        self.assertEqual(set(manifest["skipped"]), {"reference/run.sh", "reference/skills/mantis-launch/SKILL.md",
                                                    "README.md", "AGENTS.md"})
        head = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], check=True,
                              stdout=subprocess.PIPE).stdout.decode().strip()
        self.assertEqual((manifest["commit"], manifest["dirty"]), (head, False))
        (self.root / "mantis-patch" / "SKILL.md").write_text("edited")
        self.assertTrue(pack_skills(self.root, self.archive)["dirty"])
        with tarfile.open(self.archive) as archive:
            self.assertEqual(sorted(archive.getnames()), sorted(manifest["files"]))

    def test_skill_pack_from_a_subdirectory_of_a_checkout(self):
        self.add("sandbox/skills/security-review-repo/SKILL.md", "review")
        self.add("sandbox/sbx/appsec_sbx/cli.py", "code, outside the pack")
        self.add("README.md", "docs")
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin"],
                       check=True)
        manifest = pack_skills(self.root / "sandbox" / "skills", self.archive)
        self.assertEqual(manifest["skills"], ["security-review-repo"])
        self.assertEqual((manifest["subdirectory"], manifest["skipped"], manifest["dirty"]),
                         ("sandbox/skills", [], False))
        self.assertEqual(list(manifest["files"]), ["security-review-repo/SKILL.md"])
        (self.root / "README.md").write_text("edited outside the pack")
        self.assertFalse(pack_skills(self.root / "sandbox" / "skills", self.archive)["dirty"])
        with self.assertRaisesRegex(RuntimeError, "No directory with SKILL.md"):
            pack_skills(self.root / "sandbox", self.archive)

    def test_repository_review_skill_is_a_valid_pack(self):
        skills = Path(__file__).resolve().parent.parent / "skills"
        manifest = pack_skills(skills, self.archive)
        self.assertIn("security-review-repo", manifest["skills"])
        text = (skills / "security-review-repo" / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: security-review-repo\ndescription: "))
        for needed in ("allowed-tools:", "$ARGUMENTS", "FALSE POSITIVE FILTERING", "/home/appsec/out/findings.md"):
            self.assertIn(needed, text)
        self.assertNotIn("!`", text)

    def test_skill_pack_refuses_odd_names_and_empty_packs(self):
        self.add("README.md", "no skills here")
        with self.assertRaisesRegex(RuntimeError, "no commit"):
            pack_skills(self.root, self.archive)
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "pin"],
                       check=True)
        with self.assertRaisesRegex(RuntimeError, "No directory with SKILL.md"):
            pack_skills(self.root, self.archive)
        self.add("Bad_Name/SKILL.md", "underscore and capitals")
        with self.assertRaises(RuntimeError):
            pack_skills(self.root, self.archive)

    def test_symlink_index_entry_is_rejected_by_name(self):
        self.add("file", "data")
        (self.root / "link").symlink_to("file")
        subprocess.run(["git", "-C", self.root, "add", "link"], check=True)
        with self.assertRaisesRegex(RuntimeError, "Symlink in the Git index"):
            pack_repository(self.root, self.archive)

    def test_submodule_is_rejected_by_name(self):
        self.add("file", "data")
        sub = Path(self.temporary.name) / "sub"
        sub.mkdir()
        subprocess.run(["git", "init", "-q", sub], check=True)
        (sub / "x").write_text("x")
        subprocess.run(["git", "-C", sub, "-c", "user.email=t@t", "-c", "user.name=t", "add", "x"], check=True)
        subprocess.run(["git", "-C", sub, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x"], check=True)
        subprocess.run(["git", "-C", self.root, "-c", "protocol.file.allow=always", "submodule", "add", "-q",
                        str(sub), "vendor"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with self.assertRaisesRegex(RuntimeError, "Submodule"):
            pack_repository(self.root, self.archive)

    def test_hardlink_is_rejected(self):
        self.add("file", "data")
        os.link(self.root / "file", self.root / "hardlink")
        with self.assertRaises(RuntimeError):
            pack_repository(self.root, self.archive)

    def test_symlink_parent_is_rejected_by_both_readers(self):
        self.add("dir/file", "data")
        (self.root / "dir").rename(self.root / "real")
        (self.root / "dir").symlink_to("real", target_is_directory=True)
        with self.assertRaises(OSError):
            read_nofollow_fd(self.root, "dir/file")
        with self.assertRaises(RuntimeError):
            read_lstat(self.root, "dir/file")
        with self.assertRaises((OSError, RuntimeError)):
            pack_repository(self.root, self.archive)

    def test_traversal_and_fifo_are_rejected_by_both_readers(self):
        os.mkfifo(self.root / "fifo")
        for reader in (read_nofollow_fd, read_lstat, read_regular):
            for path in ("../outside", "/etc/passwd", "dir/../../outside", "a\\b"):
                with self.subTest(reader=reader.__name__, path=path), self.assertRaises(RuntimeError):
                    reader(self.root, path)
            with self.subTest(reader=reader.__name__, path="fifo"), self.assertRaises(RuntimeError):
                reader(self.root, "fifo")


if __name__ == "__main__":
    unittest.main()
