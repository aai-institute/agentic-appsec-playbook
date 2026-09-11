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
from appsec_sbx.lifecycle import Managed, claude_code_variant, codex_variant, migrate
from appsec_sbx.policy import DENY, compile_denies, validate_policy
from appsec_sbx.transfer import guest_home_path, pack_repository, read_lstat, read_nofollow_fd, read_regular

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
            self.assertLessEqual(len(hosts), 3, name)
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
        self.assertEqual(providers.resolve("codex")["endpoints"], ["api.openai.com:443"])
        self.assertEqual(providers.resolve("codex")["key_var"], "OPENAI_API_KEY")
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


class CommandVariantTests(unittest.TestCase):
    def test_claude_code_frontmatter_swap_keeps_body(self):
        source = (Path(__file__).parent / "appsec_sbx" / "guest" / "commands" / "security-review.md").read_text()
        out = claude_code_variant(source)
        self.assertTrue(out.startswith("---\ndescription: Whole-repository"))
        self.assertIn("allowed-tools: Bash(find:*)", out)
        self.assertEqual(out.split("---\n", 2)[2], source.split("---\n", 2)[2])
        with self.assertRaises(RuntimeError):
            claude_code_variant("no frontmatter")

    def test_codex_variant_drops_the_shell_block(self):
        source = (Path(__file__).parent / "appsec_sbx" / "guest" / "commands" / "security-review.md").read_text()
        out = codex_variant(source)
        self.assertTrue(out.startswith("---\ndescription: Whole-repository"))
        self.assertIn("argument-hint:", out)
        self.assertNotIn("!`find", out)
        self.assertIn("Begin by listing every file", out)
        self.assertIn("$ARGUMENTS", out)
        self.assertIn("FALSE POSITIVE FILTERING", out)
        with self.assertRaises(RuntimeError):
            codex_variant("---\ndescription: x\n---\nno listing block")


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
