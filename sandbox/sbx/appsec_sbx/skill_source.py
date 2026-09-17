"""Host-only GitHub skill fetches (M14 / T33); local packs keep their existing path."""
from pathlib import Path
import subprocess
import tempfile

from .git_source import fetch_checkout, github_url, is_remote, remote_ref
from .policy import require
from .transfer import pack_skills


def pack_skill_source(source, destination, *, ref=None, subdir=None):
    source = str(source)
    remote = is_remote(source)
    if not remote:
        require(ref is None and subdir is None, "--ref and --subdir apply only to GitHub URLs; "
                "for a local pack, pass its directory and select the commit in that checkout")
        manifest = pack_skills(source, destination)
        manifest["source"] = str(Path(source).resolve())
        return manifest

    url = github_url(source)
    requested = remote_ref("main" if ref is None else ref)
    directory = "." if subdir is None else subdir
    if directory != ".":
        require(bool(directory) and not directory.startswith("/") and
                all(p not in {"", ".", ".."} for p in directory.split("/")) and
                ":" not in directory and "\\" not in directory,
                "--subdir must be a relative directory inside the repository")
    with tempfile.TemporaryDirectory(prefix="appsec-skill-source-") as temporary:
        root = Path(temporary).resolve() / "repo"
        try:
            env = fetch_checkout(url, requested, root)
            selected = (root / directory).resolve(strict=True)
            require(selected == root or root in selected.parents, "Skill directory escapes the checkout")
            manifest = pack_skills(selected, destination, git_env=env)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Git skill fetch or checkout exceeded its 120-second command timeout") from error
    manifest.update(source=url, requested_ref=requested)
    return manifest
