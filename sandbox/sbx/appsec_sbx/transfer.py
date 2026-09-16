"""Filtered import of a Git working tree, skill packs and opaque export (threat model M3, M14, M22).

Import admits tracked regular files only. Symlink and submodule index entries,
symlinks or reparse points in any path component, hardlinks, special files and
traversal paths are rejected. Modes come from the Git index so that Windows
hosts, which have no executable bit, produce the same archive as POSIX hosts.
"""
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile

from .policy import require

FILE_LIMIT = 64 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
EXCLUDED_DIRS = {".git", ".agents", ".claude", ".codex", ".opencode", ".vscode", ".idea",
                 ".ssh", ".aws", ".azure", ".kube", "node_modules"}
EXCLUDED_NAMES = {".npmrc", ".pypirc", ".sbxenv.yaml", "opencode.json", "opencode.jsonc",
                  "credentials", "auth.json"}
EXCLUDED_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
# One skill = one directory holding SKILL.md; the name becomes a guest path segment and,
# in the harness, `/name` or `$name`. OpenCode's rule (the strictest of the three, docs
# 2026-09-11): lowercase alphanumerics with single hyphens, 1–64 characters.
SKILL_NAME = re.compile(r"(?=.{1,64}$)[a-z0-9]+(-[a-z0-9]+)*")


def excluded(path):
    parts = PurePosixPath(path).parts
    return any(p in EXCLUDED_DIRS or p.startswith(".env") or p.lower() in EXCLUDED_NAMES or
               p.lower().endswith(EXCLUDED_SUFFIXES) for p in parts)


def safe_parts(relative):
    parts = PurePosixPath(relative).parts
    require(parts and not relative.startswith("/") and "\\" not in relative and
            all(p not in {".", ".."} for p in parts), f"Unsafe path: {relative}")
    return parts


def _check_regular(info, relative):
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            f"Only regular, non-hardlinked files can be imported: {relative}")
    require(info.st_size <= FILE_LIMIT, f"File exceeds 64 MiB: {relative}")


def _read_stream(stream, relative):
    data = stream.read(FILE_LIMIT + 1)
    require(len(data) <= FILE_LIMIT, f"File grew too large: {relative}")
    return data


def read_nofollow_fd(root, relative):
    """POSIX: walk every component with O_NOFOLLOW relative to a root fd; race-free."""
    parts = safe_parts(relative)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        source = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(source, "rb") as stream:
            _check_regular(os.fstat(stream.fileno()), relative)
            return _read_stream(stream, relative)
    finally:
        os.close(fd)


def _reparse_point(info):
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def read_lstat(root, relative):
    """Portable: lstat each component, then open. Not race-free; documented in M22."""
    parts = safe_parts(relative)
    current = Path(root)
    for part in parts:
        current = current / part
        info = os.lstat(current)
        require(not stat.S_ISLNK(info.st_mode) and not _reparse_point(info),
                f"Symlink or reparse point in path: {relative}")
    # Refuse FIFOs and devices before open(): opening a FIFO would block.
    _check_regular(info, relative)
    with open(current, "rb") as stream:
        info = os.fstat(stream.fileno())
        _check_regular(info, relative)
        require(not _reparse_point(info), f"Reparse point: {relative}")
        return _read_stream(stream, relative)


read_regular = (read_nofollow_fd if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW")
                else read_lstat)


GUEST_HOME = "/home/appsec/"


def guest_home_path(destination):
    """Absolute guest path inside the workload home; no traversal, not the key/tmp dirs."""
    require(destination.startswith(GUEST_HOME) and ".." not in PurePosixPath(destination).parts and
            "\\" not in destination and destination != GUEST_HOME and not destination.endswith("/"),
            f"Destination must be a file path under {GUEST_HOME}: {destination}")
    return destination


def index_entries(root, *, git_env=None):
    """Tracked paths with their index modes; symlink and submodule entries are refused by name."""
    output = subprocess.run(["git", "-C", str(root), "ls-files", "-s", "-z"], check=True,
                            stdout=subprocess.PIPE, env=git_env).stdout.decode("utf-8", "surrogateescape")
    entries = {}
    for record in filter(None, output.split("\0")):
        meta, path = record.split("\t", 1)
        mode = meta.split(" ", 1)[0]
        require(mode != "120000", f"Symlink in the Git index is not imported: {path}")
        require(mode != "160000", f"Submodule is not imported; choose an explicit strategy: {path}")
        require(mode in {"100644", "100755"}, f"Unexpected index mode {mode} for {path}")
        entries[path] = 0o755 if mode == "100755" else 0o644
    return entries


def autocrlf_warning(root):
    result = subprocess.run(["git", "-C", str(root), "config", "--get", "core.autocrlf"],
                            stdout=subprocess.PIPE, check=False)
    value = result.stdout.decode().strip().lower()
    if value == "true":
        print("NOTE: core.autocrlf=true; the working tree carries CRLF line endings into the guest",
              file=sys.stderr)


def pack_repository(source, destination):
    root = Path(source).resolve(strict=True)
    git_root = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], check=True,
                              stdout=subprocess.PIPE).stdout.decode().strip()
    require(Path(git_root).resolve() == root, "Import the repository root")
    autocrlf_warning(root)
    manifest = {"files": {}, "excluded": []}
    total = 0
    with tarfile.open(destination, "w:gz") as archive:
        for relative, mode in sorted(index_entries(root).items()):
            if excluded(relative):
                manifest["excluded"].append(relative)
                continue
            data = read_regular(root, relative)
            total += len(data)
            require(total <= TOTAL_LIMIT, "Import exceeds 512 MiB")
            entry = tarfile.TarInfo(relative)
            entry.size, entry.mode = len(data), mode
            archive.addfile(entry, io.BytesIO(data))
            manifest["files"][relative] = hashlib.sha256(data).hexdigest()
    return manifest


def pack_skills(source, destination, *, git_env=None):
    """Skill directories (immediate subdirectories holding SKILL.md) of a Git checkout as a tar.gz.

    `source` is the checkout root or a directory inside it; the pin is the checkout's commit.
    Same readers, index modes and exclusions as the repository import. Anything outside a
    skill directory (frameworks, install scripts, tests, README) is skipped and listed, so a
    pack such as google/mantis contributes its SKILL.md trees and nothing that executes.
    """
    root = Path(source).resolve(strict=True)
    top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], check=True,
                         stdout=subprocess.PIPE, env=git_env).stdout.decode().strip()
    top = Path(top).resolve()
    require(root == top or top in root.parents, "Pass a directory inside a Git checkout")
    head = subprocess.run(["git", "-C", str(top), "rev-parse", "--verify", "-q", "HEAD"],
                          check=False, stdout=subprocess.PIPE, env=git_env)
    require(head.returncode == 0, "Skill pack has no commit to pin it to; commit first")
    commit = head.stdout.decode().strip()
    # Uncommitted edits inside the pack only; the rest of the checkout is not what is installed.
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no", "--", "."],
                           check=True, stdout=subprocess.PIPE, env=git_env).stdout.strip() != b""
    prefix = root.relative_to(top).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    entries = {path[len(prefix):]: mode for path, mode in index_entries(top, git_env=git_env).items()
               if path.startswith(prefix)}
    skills = sorted({PurePosixPath(p).parts[0] for p in entries
                     if len(PurePosixPath(p).parts) == 2 and PurePosixPath(p).name == "SKILL.md"})
    require(skills, f"No directory with SKILL.md directly under {root}")
    for name in skills:
        require(SKILL_NAME.fullmatch(name) is not None, f"Skill directory name is not admitted: {name}")
    manifest = {"commit": commit, "dirty": dirty, "subdirectory": prefix.rstrip("/"), "skills": skills,
                "files": {}, "excluded": [], "skipped": []}
    total = 0
    with tarfile.open(destination, "w:gz") as archive:
        for relative, mode in sorted(entries.items()):
            if PurePosixPath(relative).parts[0] not in skills:
                manifest["skipped"].append(relative)
                continue
            if excluded(relative):
                manifest["excluded"].append(relative)
                continue
            data = read_regular(root, relative)
            total += len(data)
            require(total <= TOTAL_LIMIT, "Skill pack exceeds 512 MiB")
            entry = tarfile.TarInfo(relative)
            entry.size, entry.mode = len(data), mode
            archive.addfile(entry, io.BytesIO(data))
            manifest["files"][relative] = hashlib.sha256(data).hexdigest()
    return manifest
