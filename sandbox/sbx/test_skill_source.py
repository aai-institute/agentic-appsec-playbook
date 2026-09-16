"""Real Git fetch/pack tests with only the network transport replaced by a local fixture."""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from appsec_sbx.cli import build_parser
from appsec_sbx.lifecycle import Managed
from appsec_sbx import skill_source


class SkillSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "upstream"
        self.repo.mkdir()
        self.real_run = subprocess.run
        self.git("init", "-q", "-b", "main")
        self.add(".claude/skills/scan/SKILL.md", "scan v1\n")
        self.add(".claude/skills/scan/helper.txt", "support\n")
        self.add("README.md", "not a skill\n")
        self.commit = self.save()
        self.git("tag", "v1")
        self.git("branch", "other")
        self.archive = self.base / "skills.tar.gz"
        self.url = "https://github.com/example/skills"
        self.roots = []

    def git(self, *args):
        return self.real_run(["git", "-C", str(self.repo), *args], check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def add(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        self.git("add", path)

    def save(self):
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com",
                 "-c", "commit.gpgSign=false", "commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def transport(self, args, **kwargs):
        args = [str(a) for a in args]
        if "fetch" in args:
            self.roots.append(Path(args[2]))
            args[args.index(self.url + ".git")] = str(self.repo)
            args[1:1] = ["-c", "protocol.file.allow=always"]
        return self.real_run(args, **kwargs)

    def pack(self, **kwargs):
        with mock.patch("subprocess.run", side_effect=self.transport):
            return skill_source.pack_skill_source(self.url, self.archive, subdir=".claude/skills", **kwargs)

    def test_default_main_and_explicit_branch_tag_commit(self):
        for ref in (None, "other", "v1", self.commit):
            with self.subTest(ref=ref):
                manifest = self.pack(ref=ref)
                self.assertEqual(manifest["commit"], self.commit)
                self.assertEqual(manifest["requested_ref"], ref or "main")
                self.assertEqual(manifest["source"], self.url + ".git")
                self.assertEqual(manifest["subdirectory"], ".claude/skills")
                self.assertFalse(manifest["dirty"])
                with tarfile.open(self.archive) as tar:
                    self.assertEqual(set(tar.getnames()), {"scan/SKILL.md", "scan/helper.txt"})
                self.assertFalse(self.roots[-1].parent.exists())

    def test_moving_branch_records_new_commit_and_old_commit_is_repeatable(self):
        self.add(".claude/skills/scan/SKILL.md", "scan v2\n")
        new = self.save()
        self.assertEqual(self.pack()["commit"], new)
        self.assertEqual(self.pack(ref=self.commit)["commit"], self.commit)

    def test_bad_inputs_fail_before_fetch(self):
        for url in ("http://github.com/a/b", "https://evil.example/a/b", "git@github.com:a/b",
                    "https://user:pass@github.com/a/b", "https://github.com/a/b?x=1",
                    "https://github.com/a/b/tree/main", "https://github.com/a/.."):
            with self.subTest(url=url), mock.patch.object(skill_source, "fetch_checkout") as fetch:
                with self.assertRaises(RuntimeError):
                    skill_source.pack_skill_source(url, self.archive)
                fetch.assert_not_called()
        for ref in ("", "--upload-pack=evil", "main:refs/heads/x", "HEAD~1", "a\nb", "../x"):
            with self.subTest(ref=ref), self.assertRaises(RuntimeError):
                self.pack(ref=ref)
        for subdir in ("../outside", "/tmp", "a/../../b", "a\\b", "C:/tmp", ""):
            with self.subTest(subdir=subdir), mock.patch.object(skill_source, "fetch_checkout") as fetch:
                with self.assertRaises(RuntimeError):
                    skill_source.pack_skill_source(self.url, self.archive, subdir=subdir)
                fetch.assert_not_called()

    def test_failure_cleans_checkout(self):
        with self.assertRaisesRegex(RuntimeError, "--ref"):
            self.pack(ref="absent")
        self.assertFalse(self.roots[-1].parent.exists())
        with mock.patch("subprocess.run", side_effect=self.transport):
            with self.assertRaises(FileNotFoundError):
                skill_source.pack_skill_source(self.url, self.archive, subdir="absent")
        self.assertFalse(self.roots[-1].parent.exists())
        with mock.patch.object(skill_source, "pack_skills", side_effect=RuntimeError("packing failed")):
            with self.assertRaisesRegex(RuntimeError, "packing failed"):
                self.pack()
        self.assertFalse(self.roots[-1].parent.exists())

    def test_symlinks_and_submodules_refused_before_checkout(self):
        for mode in ("120000", "160000"):
            with self.subTest(mode=mode):
                oid = self.commit if mode == "160000" else self.git("hash-object", "-w", "README.md")
                self.git("update-index", "--add", "--cacheinfo", f"{mode},{oid},unsafe")
                self.save()
                with self.assertRaisesRegex(RuntimeError, "Symlink|Submodule"):
                    self.pack()
                self.assertFalse(self.roots[-1].parent.exists())
                self.git("update-index", "--force-remove", "unsafe")

    def test_host_config_hooks_filters_and_environment_are_not_used(self):
        marker = self.base / "executed"
        hookdir = self.base / "hooks"
        hookdir.mkdir()
        hook = hookdir / "post-checkout"
        hook.write_text(f'#!/bin/sh\necho bad > "{marker}"\n')
        hook.chmod(0o755)
        config = self.base / "host.gitconfig"
        config.write_text(f'[core]\n hooksPath = {hookdir}\n[filter "evil"]\n'
                          f' smudge = touch "{marker}"\n required = true\n'
                          '[url "https://invalid.example/"]\n insteadOf = https://github.com/\n')
        self.add(".gitattributes", "*.md filter=evil text eol=crlf ident\n")
        self.save()
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_COUNT": "1",
                                         "GIT_CONFIG_KEY_0": "core.hooksPath",
                                         "GIT_CONFIG_VALUE_0": str(hookdir),
                                         "GIT_DIR": str(self.repo / ".git")}):
            manifest = self.pack()
        self.assertFalse(marker.exists())
        self.assertFalse(manifest["dirty"])
        with tarfile.open(self.archive) as tar:
            self.assertEqual(tar.extractfile("scan/SKILL.md").read(), b"scan v1\n")

    def test_local_path_unchanged_and_remote_options_rejected(self):
        local = self.repo / ".claude/skills"
        manifest = skill_source.pack_skill_source(local, self.archive)
        self.assertEqual(manifest["source"], str(local))
        self.assertNotIn("requested_ref", manifest)
        with self.assertRaisesRegex(RuntimeError, "URLs"):
            skill_source.pack_skill_source(local, self.archive, ref="main")

    def test_root_pack_and_optional_dot_git_suffix(self):
        self.add("scan/SKILL.md", "root skill\n")
        self.save()
        with mock.patch("subprocess.run", side_effect=self.transport):
            manifest = skill_source.pack_skill_source(self.url + ".git/", self.archive)
        self.assertEqual(manifest["skills"], ["scan"])
        self.assertEqual(manifest["subdirectory"], "")

    def test_timeout_cleans_checkout(self):
        def timeout(url, ref, root):
            self.roots.append(root)
            root.mkdir()
            raise subprocess.TimeoutExpired("git fetch", 120)
        with mock.patch.object(skill_source, "fetch_checkout", side_effect=timeout):
            with self.assertRaisesRegex(RuntimeError, "timeout"):
                self.pack()
        self.assertFalse(self.roots[-1].parent.exists())

    def test_collision_keeps_record_and_cleans_both_staging_locations(self):
        with mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": str(self.base / "state")}), \
                mock.patch("subprocess.run", side_effect=self.transport), \
                mock.patch("appsec_sbx.lifecycle.sbx"), \
                mock.patch("appsec_sbx.lifecycle.guest", return_value=mock.Mock(stdout=b"scan\n")) as guest:
            vm = Managed("test-collision")
            vm.data["profile"] = {"harness": "claude-code"}
            record = vm.directory / "skills.json"
            record.write_text('{"prior": true}\n')
            with self.assertRaisesRegex(RuntimeError, "Already installed"):
                vm.install_skills(self.url, subdir=".claude/skills")
            self.assertEqual(record.read_text(), '{"prior": true}\n')
            self.assertEqual(guest.call_args.args[1:3], ("rm", "-f"))
        self.assertFalse(self.roots[-1].parent.exists())

    def test_cli_options_and_provenance_survive_temporary_cleanup(self):
        args = build_parser().parse_args(["skills", "vm", self.url, "--subdir", ".claude/skills",
                                         "--ref", "v1", "--replace"])
        self.assertEqual((args.ref, args.subdir, args.replace), ("v1", ".claude/skills", True))
        with mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": str(self.base / "state")}), \
                mock.patch("subprocess.run", side_effect=self.transport), \
                mock.patch("appsec_sbx.lifecycle.sbx"), \
                mock.patch("appsec_sbx.lifecycle.guest", return_value=mock.Mock(stdout=b"")):
            vm = Managed("test-url-skills")
            vm.data["profile"] = {"harness": "claude-code"}
            vm.install_skills(self.url, ref="v1", subdir=".claude/skills")
            record = json.loads((vm.directory / "skills.json").read_text())["scan"]
        self.assertEqual((record["source"], record["requested_ref"], record["commit"]),
                         (self.url + ".git", "v1", self.commit))
        self.assertEqual(record["subdirectory"], ".claude/skills")
        self.assertFalse(self.roots[-1].parent.exists())


if __name__ == "__main__":
    unittest.main()
