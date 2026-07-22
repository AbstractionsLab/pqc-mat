"""
github_resolver.py - Resolves a GitHub URL to a local temporary clone.

Supports:
  https://github.com/owner/repo
  https://github.com/owner/repo.git
  https://github.com/owner/repo/tree/branch-or-tag
  https://github.com/owner/repo/tree/branch/subdir  (clones repo, returns subdir path)

The clone is shallow (--depth=1) to minimise disk and network usage.
"""

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field


_HTTPS_RE = re.compile(
    r'^https://github\.com'
    r'/(?P<owner>[^/]+)'
    r'/(?P<repo>[^/]+?)(\.git)?'
    r'(?:/tree/(?P<ref>[^/]+)(?P<subpath>/.+)?)?'
    r'/?$'
)

_SSH_RE = re.compile(
    r'^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?$'
)

_AUTH_OR_MISSING_MARKERS = (
    "could not read username",
    "could not read password",
    "authentication failed",
    "invalid username or password",
    "terminal prompts disabled",
    "support for password authentication was removed",
    "permission denied (publickey)",
    "not found",
)

def _is_auth_or_missing_repo_failure(stderr: str) -> bool:
    """True if there is a missing, private, or credential-gated repo"""
    lowered = stderr.lower()
    return any(marker in lowered for marker in _AUTH_OR_MISSING_MARKERS)

@dataclass
class CloneResult:
    """Result of a successful GitHub clone"""
    path: str
    clone_root: str
    app_name: str
    _owns_cleanup: bool = field(default=True, repr=False)

    def cleanup(self) -> None:
        """Delete the cloned directory from disk."""
        if self._owns_cleanup and os.path.isdir(self.clone_root):
            shutil.rmtree(self.clone_root, ignore_errors=True)


def is_github_url(source: str) -> bool:
    """Return True if source looks like a GitHub URL"""
    s = source.strip()
    return bool(_HTTPS_RE.match(s) or _SSH_RE.match(s))


def _parse_github_url(url: str) -> tuple[str, str, str, str|None, str| None]:
    """Return (clone_url, owner, repo, ref_or_None, subpath_or_None)"""
    url = url.strip()

    m = _HTTPS_RE.match(url)
    if m:
        owner = m.group('owner')
        repo = m.group('repo')
        ref = m.group('ref')
        subpath = m.group('subpath')
        clone_url = f"https://github.com/{owner}/{repo}.git"
        return clone_url, owner, repo, ref, subpath

    m = _SSH_RE.match(url)
    if m:
        raise ValueError(
            f"SSH-style GitHub URLs are not supported: {url!r}. VECTOR-Code "
            f"only supports public GitHub repositories over HTTPS; private "
            f"repositories requiring SSH authentication are out of scope. "
            f"Use the HTTPS form instead, e.g. 'https://github.com/<owner>/<repo>'."
        )

    raise ValueError(f"Cannot parse GitHub URL: {url!r}")


def resolve(url: str) -> CloneResult:
    """Clone a GitHub repository and return the clone result"""
    clone_url, owner, repo, ref, subpath = _parse_github_url(url)
    app_name = f"{owner}/{repo}"

    tmp_dir = tempfile.mkdtemp(prefix="vector_code_")

    cmd = ['git', 'clone', '--depth=1', '--single-branch']
    if ref:
        cmd += ['--branch', ref]
    cmd += [clone_url, tmp_dir]

    clone_env = dict(os.environ)
    clone_env["GIT_TERMINAL_PROMPT"] = "0"
    clone_env["GCM_INTERACTIVE"] = "never"
    clone_env.pop("GIT_ASKPASS", None)
    clone_env.pop("SSH_ASKPASS", None)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=clone_env,
        )
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {exc}") from exc

    if result.returncode != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        stderr_lines = [l for l in result.stderr.splitlines() if l.strip()]
        detail = stderr_lines[-1] if stderr_lines else result.stderr.strip()

        if _is_auth_or_missing_repo_failure(result.stderr):
            raise RuntimeError(
                f"git clone failed for {clone_url!r}: the repository was not found, "
                f"or it may be private and require authentication. \n"
            )

        raise RuntimeError(
            f"git clone failed for {clone_url!r}:\n  {detail}"
        )

    analysis_path = tmp_dir
    if subpath:
        candidate = os.path.join(tmp_dir, subpath.lstrip('/'))
        if os.path.isdir(candidate):
            analysis_path = candidate
        else:
            print(
                f"  Warning: subpath '{subpath}' not found in cloned repo; "
                f"scanning repository root instead."
            )

    return CloneResult(
        path=analysis_path,
        clone_root=tmp_dir,
        app_name=app_name,
    )