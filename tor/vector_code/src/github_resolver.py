"""
github_resolver.py - Resolves a GitHub URL to a local temporary clone.

Supports:
  https://github.com/owner/repo
  https://github.com/owner/repo.git
  https://github.com/owner/repo/tree/branch-or-tag
  https://github.com/owner/repo/tree/branch/subdir  (clones repo, returns subdir path)
  git@github.com:owner/repo.git

The clone is shallow (--depth=1) to minimise disk and network usage.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional


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


def _parse_github_url(url: str) -> tuple[str, str, str, Optional[str]]:
    """Return (clone_url, owner, repo, subpath_or_None)"""
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
        owner = m.group('owner')
        repo  = m.group('repo')
        clone_url = f"https://github.com/{owner}/{repo}.git"
        return clone_url, owner, repo, None, None

    raise ValueError(f"Cannot parse GitHub URL: {url!r}")


def resolve(url: str) -> CloneResult:
    """Clone a GitHub repository and return the clone result"""
    clone_url, owner, repo, ref, subpath = _parse_github_url(url)
    app_name = f"{owner}/{repo}"

    if shutil.which('git') is None:
        raise RuntimeError(
            "git is not installed or not on PATH. "
            "Install git: sudo apt-get install git"
        )

    tmp_dir = tempfile.mkdtemp(prefix="vector_code_")

    cmd = ['git', 'clone', '--depth=1', '--single-branch']
    if ref:
        cmd += ['--branch', ref]
    cmd += [clone_url, tmp_dir]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {exc}") from exc

    if result.returncode != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        stderr_lines = [l for l in result.stderr.splitlines() if l.strip()]
        detail = stderr_lines[-1] if stderr_lines else result.stderr.strip()
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