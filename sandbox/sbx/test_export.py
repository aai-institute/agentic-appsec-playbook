"""Exercise real archive creation locally without a sandbox daemon."""
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile

from appsec_sbx.lifecycle import HERE, Managed


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "out"
        self.source.mkdir()
        self.env = mock.patch.dict(os.environ, {"APPSEC_SBX_STATE": str(self.root / "state")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.vm = Managed("export-test")
        self.guest = mock.patch("appsec_sbx.lifecycle.guest", side_effect=self.run_guest)
        self.guest_mock = self.guest.start()
        self.addCleanup(self.guest.stop)

    def run_guest(self, vm, *args, **kwargs):
        self.assertEqual(vm, "export-test")
        self.assertEqual(kwargs["user"], "appsec")
        command = [str(self.source) if arg == "/home/appsec/out" else arg for arg in args]
        if command[0] == "python3":
            command[0] = sys.executable
        return subprocess.run(command, stdout=kwargs["stdout"], stderr=subprocess.PIPE, check=True)

    @unittest.skipUnless(os.name == "posix", "runs the Linux guest ZIP script locally")
    def test_zip_contents_and_empty_directories(self):
        (self.source / "nested").mkdir()
        (self.source / "empty").mkdir()
        (self.source / "findings.md").write_text("Review: café\n", encoding="utf-8")
        data = bytes(range(256)) * 100
        (self.source / "nested" / "proof.bin").write_bytes(data)
        (self.source / "résumé.txt").write_bytes(b"summary")
        target = self.root / "findings.ZIP"
        self.vm.export_output(target)
        with zipfile.ZipFile(target) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()),
                             {"nested/", "empty/", "findings.md", "nested/proof.bin", "résumé.txt"})
            self.assertEqual(archive.read("nested/proof.bin"), data)
            self.assertEqual(archive.read("findings.md").decode(), "Review: café\n")
        self.assertFalse((self.root / "findings.md").exists())

    @unittest.skipUnless(os.name == "posix", "runs the Linux guest ZIP script locally")
    def test_empty_zip(self):
        target = self.root / "empty.zip"
        self.vm.export_output(target)
        with zipfile.ZipFile(target) as archive:
            self.assertEqual(archive.namelist(), [])

    @unittest.skipUnless(os.name == "posix", "runs the Linux guest ZIP script locally")
    def test_zip_streams_through_a_pipe(self):
        (self.source / "findings.md").write_bytes(b"report")
        script = (HERE / "guest" / "export_zip.py").read_text()
        result = subprocess.run([sys.executable, "-I", "-c", script, str(self.source)],
                                capture_output=True, check=True)
        with zipfile.ZipFile(io.BytesIO(result.stdout)) as archive:
            self.assertEqual(archive.read("findings.md"), b"report")

    @unittest.skipUnless(os.name == "posix", "runs the guest tar command locally")
    def test_tar_formats_still_export_contents(self):
        (self.source / "findings.md").write_bytes(b"report")
        for suffix in (".tar.gz", ".tgz"):
            with self.subTest(suffix=suffix):
                target = self.root / ("findings" + suffix)
                self.vm.export_output(target)
                with tarfile.open(target, "r:gz") as archive:
                    self.assertEqual(archive.extractfile("./findings.md").read(), b"report")

    def test_existing_destination_is_untouched(self):
        for suffix in (".zip", ".tar.gz"):
            target = self.root / ("existing" + suffix)
            target.write_bytes(b"keep me")
            with self.subTest(suffix=suffix), self.assertRaises(FileExistsError):
                self.vm.export_output(target)
            self.assertEqual(target.read_bytes(), b"keep me")
        self.guest_mock.assert_not_called()

    def test_unknown_format_fails_before_creating_file(self):
        target = self.root / "findings.7z"
        with self.assertRaisesRegex(RuntimeError, "filename"):
            self.vm.export_output(target)
        self.assertFalse(target.exists())
        self.guest_mock.assert_not_called()

    def test_failed_or_invalid_exports_remove_partial_files(self):
        def failed(vm, *args, **kwargs):
            kwargs["stdout"].write(b"partial")
            raise subprocess.CalledProcessError(1, "export")

        def invalid(vm, *args, **kwargs):
            kwargs["stdout"].write(b"not an archive")

        for suffix in (".zip", ".tar.gz"):
            for effect, error in ((failed, subprocess.CalledProcessError), (invalid, RuntimeError)):
                target = self.root / ("failed" + suffix)
                with self.subTest(suffix=suffix, effect=effect.__name__):
                    self.guest_mock.side_effect = effect
                    with self.assertRaises(error):
                        self.vm.export_output(target)
                    self.assertFalse(target.exists())

    @unittest.skipUnless(os.name == "posix", "ZIP script executes in the Linux guest")
    def test_zip_refuses_file_and_directory_symlinks(self):
        outside = self.root / "outside.txt"
        outside.write_bytes(b"must not be exported")
        for name, destination in (("file-link", outside), ("dir-link", self.root)):
            link = self.source / name
            link.symlink_to(destination)
            target = self.root / (name + ".zip")
            with self.subTest(name=name), self.assertRaises(subprocess.CalledProcessError):
                self.vm.export_output(target)
            self.assertFalse(target.exists())
            link.unlink()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a POSIX FIFO")
    def test_zip_refuses_fifo_without_blocking(self):
        os.mkfifo(self.source / "pipe")
        script = (HERE / "guest" / "export_zip.py").read_text()
        result = subprocess.run([sys.executable, "-I", "-c", script, str(self.source)],
                                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"special files", result.stderr)


if __name__ == "__main__":
    unittest.main()
