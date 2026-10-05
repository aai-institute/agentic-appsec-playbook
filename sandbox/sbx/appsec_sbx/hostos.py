"""Host-OS differences, kept in one place (threat model M22).

Containment is enforced by sbx outside the guest; this module only makes the
wrapper's own host-side behaviour identical across macOS, Linux and Windows.
"""
import os
import subprocess
import sys

IS_WINDOWS = os.name == "nt"
# Hosts with an acceptance record in records/sbx-acceptance.md (macOS 2026-09-09/10, Windows 11 x64 and
# Linux x86_64 2026-09-14).
# Others run, but are announced as untested.
TESTED_HOSTS = {"darwin", "win32", "linux"}

if IS_WINDOWS:
    import msvcrt
else:
    import fcntl


def host_note():
    if sys.platform not in TESTED_HOSTS:
        print(f"NOTE: host {sys.platform!r} has no acceptance record for this wrapper; "
              "see the platform checks in design/sandbox-comparison.md", file=sys.stderr)


class Lock:
    """Advisory exclusive lock on a file; released early before interactive entry."""

    def __init__(self, path, blocking=True):
        self.path, self.blocking, self.handle = path, blocking, None

    def __enter__(self):
        self.handle = open(self.path, "a+")
        fd = self.handle.fileno()
        try:
            try:
                self._acquire(fd, wait=False)
            except OSError:
                if not self.blocking:
                    raise
                # A `key` typed while `import` runs used to wait without a word (2026-10-05).
                print(f"Waiting for another appsec-sbx action on {os.path.basename(os.path.dirname(self.path))} to finish...",
                      file=sys.stderr, flush=True)
                self._acquire(fd, wait=True)
        except OSError as error:
            self.handle.close()
            raise RuntimeError(f"Another wrapper invocation holds {self.path}: {error}") from None
        return self

    @staticmethod
    def _acquire(fd, wait):
        if IS_WINDOWS:
            # LK_LOCK retries for about ten seconds, then raises OSError.
            msvcrt.locking(fd, msvcrt.LK_LOCK if wait else msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))

    def release(self):
        if self.handle is None:
            return
        fd = self.handle.fileno()
        try:
            if IS_WINDOWS:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None

    def __exit__(self, *exc):
        self.release()


def private_dir(path):
    """0700 on POSIX; on Windows the per-user profile ACL is the boundary."""
    path.mkdir(parents=True, exist_ok=True)
    if not IS_WINDOWS:
        path.chmod(0o700)


def run_interactive(cmd):
    """Run with the console inherited; returns the exit status (exec semantics differ on Windows)."""
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130
