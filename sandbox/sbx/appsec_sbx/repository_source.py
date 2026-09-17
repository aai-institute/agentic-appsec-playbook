"""Prepare filtered target archives from local checkouts or public GitHub (M3 / T04)."""
from pathlib import Path
import subprocess
import tempfile

from .git_source import fetch_checkout, github_url, is_remote, remote_ref
from .policy import require
from .transfer import pack_repository


def pack_repository_source(source, destination, *, ref=None):
    source = str(source)
    if not is_remote(source):
        require(ref is None, "--ref applies only to GitHub URLs; for a local import, "
                "select the revision in a checkout or Git worktree first")
        return pack_repository(source, destination)

    url = github_url(source)
    requested = remote_ref("main" if ref is None else ref)
    with tempfile.TemporaryDirectory(prefix="appsec-repository-source-") as temporary:
        root = Path(temporary).resolve() / "repo"
        try:
            env = fetch_checkout(url, requested, root)
            commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                                    check=True, stdout=subprocess.PIPE, env=env,
                                    timeout=120).stdout.decode().strip()
            manifest = pack_repository(root, destination, git_env=env)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Git repository fetch or checkout exceeded its 120-second command timeout") from error
    manifest.update(source=url, requested_ref=requested, commit=commit)
    return manifest
