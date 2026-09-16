"""Host-only GitHub skill fetches (M14 / T33); local packs keep their existing path."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .policy import require
from .transfer import index_entries, pack_skills, safe_parts


GITHUB = re.compile(r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)/?")


def github_url(source):
    match = GITHUB.fullmatch(source)
    require(match is not None, "Use a public https://github.com/OWNER/REPO URL (no credentials, query or fragment)")
    owner, repo = match.groups()
    repo = repo.removesuffix(".git")
    require(repo not in {"", ".", ".."}, "Invalid GitHub repository name")
    return f"https://github.com/{owner}/{repo}.git"


def remote_ref(value):
    # A single remote ref or object ID, never a refspec, option or revision expression.
    require(bool(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", value)) and
            ".." not in value and "//" not in value and not value.endswith(("/", ".")),
            "--ref must be a branch, tag or commit, not a refspec or revision expression")
    return value


def fetch_checkout(url, ref, root):
    """Return a Git environment for a temporary checkout with no inherited Git config."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.pop("SSH_ASKPASS", None)
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_ATTR_NOSYSTEM="1")
    empty = root.parent / "empty"
    empty.mkdir()

    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], env=env, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)

    root.mkdir()
    git("init", "-q", f"--template={empty}")
    # All config is local to the disposable repository. No host credentials or hooks
    # are copied into it; config also applies to pack_skills' subsequent Git reads.
    for key, value in {
        "core.hooksPath": str(empty), "core.attributesFile": os.devnull,
        "core.autocrlf": "false", "core.protectNTFS": "true", "core.protectHFS": "true",
        "credential.helper": "", "protocol.allow": "never", "protocol.https.allow": "always",
        "http.followRedirects": "false", "http.sslVerify": "true", "submodule.recurse": "false",
    }.items():
        git("config", key, value)
    try:
        git("fetch", "--depth=1", "--no-tags", "--no-recurse-submodules", "--", url, ref)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Could not fetch {ref!r} from {url}. Check the public repository and --ref "
                           "(default: main); private repositories require a local checkout.") from error
    commit = git("rev-parse", "--verify", "FETCH_HEAD^{commit}").stdout.decode().strip()
    git("update-ref", "HEAD", commit)
    git("read-tree", commit)
    # Reject symlinks and submodules before materializing any fetched paths.
    for path in index_entries(root, git_env=env):
        safe_parts(path)
    # info/attributes overrides repository attributes, so checkout never invokes a
    # smudge filter or changes bytes through line endings, ident or encoding rules.
    info = root / ".git" / "info"
    info.mkdir(exist_ok=True)
    (info / "attributes").write_text("* -filter -text -ident -working-tree-encoding\n")
    git("checkout-index", "--all")
    return env


def pack_skill_source(source, destination, *, ref=None, subdir=None):
    source = str(source)
    remote = "://" in source or source.startswith("git@")
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
