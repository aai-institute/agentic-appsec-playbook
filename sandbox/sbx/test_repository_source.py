"""Repository URL imports with real Git and only network transport substituted."""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from appsec_sbx import repository_source
from appsec_sbx.cli import build_parser, dispatch
from appsec_sbx.lifecycle import Managed


class RepositorySourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "upstream"
        self.repo.mkdir()
        self.real_run = subprocess.run
        self.git("init", "-q", "-b", "main")
        self.add("main.py", "print('v1')\n")
        self.add(".env.production", "secret")
        self.add(".codex/config.toml", "untrusted config")
        self.add(".sbxenv.yaml", "host hooks")
        self.commit = self.save()
        self.git("tag", "v1")
        self.git("branch", "other")
        self.archive = self.base / "source.tar.gz"
        self.url = "https://github.com/example/target"
        self.roots = []

    def git(self, *args):
        return self.real_run(["git", "-C", str(self.repo), *args], check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def add(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        self.git("add", "--", path)

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
            return repository_source.pack_repository_source(self.url, self.archive, **kwargs)

    def test_refs_filtering_and_provenance(self):
        for ref in (None, "other", "v1", self.commit):
            with self.subTest(ref=ref):
                manifest = self.pack(ref=ref)
                self.assertEqual(manifest["commit"], self.commit)
                self.assertEqual(manifest["requested_ref"], ref or "main")
                self.assertEqual(manifest["source"], self.url + ".git")
                self.assertEqual(set(manifest["files"]), {"main.py"})
                self.assertEqual(set(manifest["excluded"]), {".env.production", ".codex/config.toml", ".sbxenv.yaml"})
                with tarfile.open(self.archive) as tar:
                    self.assertEqual(tar.getnames(), ["main.py"])
                    self.assertEqual(tar.extractfile("main.py").read(), b"print('v1')\n")
                self.assertFalse(self.roots[-1].parent.exists())
        self.add("main.py", "print('v2')\n")
        latest = self.save()
        self.assertEqual(self.pack()["commit"], latest)
        self.assertEqual(self.pack(ref=self.commit)["commit"], self.commit)

    def test_host_config_is_ignored_through_packing(self):
        config = self.base / "host.gitconfig"
        config.write_text('[url "https://invalid.example/"]\n insteadOf = https://github.com/\n'
                          '[core]\n autocrlf = true\n[filter "bad"]\n required = true\n smudge = exit 1\n')
        self.add(".gitattributes", "*.py filter=bad text eol=crlf\n")
        self.save()
        with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_DIR": str(self.base / "absent")}):
            manifest = self.pack()
        self.assertIn("main.py", manifest["files"])
        with tarfile.open(self.archive) as tar:
            self.assertEqual(tar.extractfile("main.py").read(), b"print('v1')\n")

    def test_bad_arguments_fail_before_fetch(self):
        for url in ("http://github.com/a/b", "git@github.com:a/b", "https://evil.example/a/b",
                    "https://user:pass@github.com/a/b", "https://github.com/a/b/tree/main"):
            with self.subTest(url=url), mock.patch.object(repository_source, "fetch_checkout") as fetch:
                with self.assertRaises(RuntimeError):
                    repository_source.pack_repository_source(url, self.archive)
                fetch.assert_not_called()
        for ref in ("--upload-pack=evil", "main:refs/heads/x", "HEAD~1", "../x"):
            with self.subTest(ref=ref), mock.patch.object(repository_source, "fetch_checkout") as fetch:
                with self.assertRaises(RuntimeError):
                    self.pack(ref=ref)
                fetch.assert_not_called()

    def test_failures_clean_temporary_checkout(self):
        with self.assertRaisesRegex(RuntimeError, "--ref"):
            self.pack(ref="absent")
        self.assertFalse(self.roots[-1].parent.exists())
        for error in (RuntimeError("packing failed"), subprocess.TimeoutExpired("git", 120)):
            with mock.patch.object(repository_source, "pack_repository", side_effect=error):
                with self.assertRaises(RuntimeError):
                    self.pack()
            self.assertFalse(self.roots[-1].parent.exists())

    def test_symlinks_and_submodules_are_rejected(self):
        for mode in ("120000", "160000"):
            with self.subTest(mode=mode):
                oid = self.commit if mode == "160000" else self.git("hash-object", "-w", "main.py")
                self.git("update-index", "--add", "--cacheinfo", f"{mode},{oid},unsafe")
                self.save()
                with self.assertRaisesRegex(RuntimeError, "Symlink|Submodule"):
                    self.pack()
                self.assertFalse(self.roots[-1].parent.exists())
                self.git("update-index", "--force-remove", "unsafe")

    def test_local_import_keeps_edits_and_rejects_ref(self):
        (self.repo / "main.py").write_text("working tree edit")
        (self.repo / "untracked").write_text("not imported")
        manifest = repository_source.pack_repository_source(self.repo, self.archive)
        self.assertEqual(set(manifest["files"]), {"main.py"})
        with tarfile.open(self.archive) as tar:
            self.assertEqual(tar.extractfile("main.py").read(), b"working tree edit")
        with self.assertRaisesRegex(RuntimeError, "--ref"):
            repository_source.pack_repository_source(self.repo, self.archive, ref="main")

    def test_cli_forwards_ref_and_replace(self):
        args = build_parser().parse_args(["import", "test-repo", self.url, "--ref", "v1", "--replace"])
        with mock.patch("appsec_sbx.cli.Managed") as managed:
            dispatch(args)
        managed.return_value.import_repo.assert_called_once_with(self.url, replace=True, ref="v1")

    def test_install_records_remote_provenance_after_transfer(self):
        with mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": str(self.base / "state")}), \
                mock.patch("subprocess.run", side_effect=self.transport), \
                mock.patch("appsec_sbx.lifecycle.sbx") as sbx, \
                mock.patch("appsec_sbx.lifecycle.guest") as guest:
            vm = Managed("test-repo")
            vm.import_repo(self.url, ref="v1", replace=True)
            manifest = json.loads((vm.directory / "import.json").read_text())
        self.assertEqual(manifest["commit"], self.commit)
        self.assertEqual(manifest["requested_ref"], "v1")
        self.assertEqual(manifest["source"], self.url + ".git")
        self.assertEqual(sbx.call_args.args[:2], ("exec", "-i"))
        self.assertIn('rm -rf /home/appsec/target/source;', guest.call_args_list[0].args[3])
        self.assertEqual(guest.call_args.args[1:3], ("rm", "-f"))

    def test_failed_transfer_preserves_previous_record(self):
        for failure in ("upload", "extract"):
            with self.subTest(failure=failure), \
                    mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": str(self.base / "state")}), \
                    mock.patch("appsec_sbx.lifecycle.sbx") as sbx, \
                    mock.patch("appsec_sbx.lifecycle.guest") as guest:
                if failure == "upload":
                    sbx.side_effect = subprocess.TimeoutExpired("upload", 120)
                else:
                    guest.side_effect = [subprocess.TimeoutExpired("extract", 120), mock.Mock()]
                vm = Managed("test-repo")
                record = vm.directory / "import.json"
                record.write_text('{"prior": true}\n')
                with self.assertRaisesRegex(RuntimeError, "while " + failure):
                    vm.import_repo(self.repo)
                self.assertEqual(record.read_text(), '{"prior": true}\n')
                self.assertEqual(guest.call_args.args[1:3], ("rm", "-f"))
                self.assertEqual(guest.call_count, 1 if failure == "upload" else 2)


if __name__ == "__main__":
    unittest.main()
