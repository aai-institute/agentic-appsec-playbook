"""Host-only public GitHub checkouts shared by imports and skills (M3/M14, T04/T33)."""
import os
import re
import subprocess

from .policy import require
from .transfer import index_entries, safe_parts


def require_git():
    """Fail before VM access if the host Git executable is missing or broken."""
    hint = ("Install Git (Git for Windows on Windows), make sure it is on PATH, "
            "and verify `git --version` in a new terminal before retrying.")
    try:
        result = subprocess.run(["git", "--version"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, timeout=10)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("System Git did not respond within 10 seconds. " + hint) from error
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"System Git is required for import and skills but could not run: {error}. "
                           + hint) from error
    require(re.match(rb"git version [0-9]+\.[0-9]+(?:[.\s]|$)", result.stdout.strip()) is not None,
            "System Git returned an unexpected version response. " + hint)


def is_remote(source):
    return "://" in str(source) or str(source).startswith("git@")


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
    # are copied into it; config also applies to the packers' subsequent Git reads.
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
