"""Resolving a git ref into a plain tree, so ``--delta`` needs one checkout.

``--delta BASE`` compares two trees, and the first version demanded that the
user materialise BASE themselves: a second clone, a ``git worktree add``, a
directory nobody remembers to delete. Every one of those is a step between
the question ("what did this branch do to my budget?") and the answer, and a
step taken once by the curious and never again.

When BASE names something that resolves as a git ref in PATH's repository --
``main``, ``HEAD~1``, the PR's merge base -- this module exports that commit
with ``git archive`` into a temporary directory and hands back its path. The
comparison itself stays exactly what it was: two ordinary directories walked
by the same code, so a ref delta and a two-checkout delta cannot disagree.

Honesty rules for the failure modes:

**A ref is only offered when it resolves.** A directory named ``main`` beats
a ref named ``main``; a string that resolves as neither is reported as the
error it is rather than silently compared against an empty tree.

**The snapshot is read-only in spirit and disposable in fact.** It lives in
the platform's temp directory, contains only what the commit tracked (never
uncommitted edits, never ignored files), and is removed when the process
exits. The report never claims to describe working-tree state it did not
walk.
"""

from __future__ import annotations

import atexit
import io
import os
import shutil
import subprocess
import tarfile
import tempfile

__all__ = ["RefResolutionError", "resolve_ref_tree"]


class RefResolutionError(Exception):
    """A base argument resolved as neither a directory nor a git ref."""


def _run_git(root: str, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", root, *arguments],
        capture_output=True,
        # A ref can name a tree only if the path really is a repository;
        # git's own stderr is the honest error message either way.
        text=False,
    )


def _snapshot_dir(root: str) -> str:
    """Create the temp directory an exported ref is unpacked into."""
    return tempfile.mkdtemp(prefix="contextcost-ref-")


def _looks_like_ref(base: str) -> bool:
    """Whether ``base`` is worth offering to git at all.

    Anything that is not an existing directory is worth one ``rev-parse``:
    refs share their namespace with nothing on disk in the common case
    (``main``, ``HEAD~3``, ``origin/release-2``), and refusing to try would
    send every one of them back as "not a directory".
    """
    return not os.path.isdir(base)


def resolve_ref_tree(base: str, root: str) -> str | None:
    """Return a directory holding ``base``'s tree, or ``None`` if not a ref.

    ``root`` is the repository the ref is resolved against -- always PATH,
    never the caller's working directory, so ``contextcost . --delta main``
    and ``contextcost ../other-repo --delta main`` ask different questions
    and get different answers.

    Returns ``None`` when ``base`` is an existing directory: the caller keeps
    its current behaviour of walking it directly, and a directory genuinely
    named ``main`` beats a branch named ``main`` because the user spelled a
    path -- paths win over revisions everywhere else in git too.

    Raises :class:`RefResolutionError` when ``base`` resolves as neither a
    directory nor a revision: the user asked for *something* and deserves
    git's own complaint about what was not found rather than a silent
    fallback to an empty comparison.
    """
    if not _looks_like_ref(base):
        return None
    # No --quiet here: when the probe fails, git's own complaint ("unknown
    # revision or path not in the working tree") is the most useful line the
    # error can carry, so it is captured for _stderr rather than suppressed.
    probe = _run_git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
    if probe.returncode != 0:
        if _is_repository(root):
            raise RefResolutionError(
                f"base '{base}' is neither a directory nor a git revision "
                f"of {root}: {_stderr(probe)}"
            )
        raise RefResolutionError(
            f"base '{base}' is not a directory, and {root} is not a git "
            "repository, so it cannot be resolved as a revision either"
        )
    commit = probe.stdout.decode("utf-8", "replace").strip()
    return _export(root, commit)


def _is_repository(root: str) -> bool:
    return _run_git(root, "rev-parse", "--git-dir").returncode == 0


def _export(root: str, commit: str) -> str:
    """Export ``commit``'s tracked files into a fresh temp directory."""
    archive = _run_git(root, "archive", "--format=tar", commit)
    if archive.returncode != 0:
        raise RefResolutionError(f"cannot export {commit}: {_stderr(archive)}")
    destination = _snapshot_dir(root)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        # `extractall` with a filter refuses absolute paths, `..` segments and
        # devices; on interpreters without filters it degrades to the
        # historical behaviour, which is acceptable for content the local git
        # just produced from the user's own repository.
        try:
            bundle.extractall(destination, filter="data")
        except TypeError:  # pragma: no cover - Python < 3.12, no filter kwarg
            bundle.extractall(destination)
    marker = os.path.join(destination, ".contextcost-ref")
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(commit + "\n")
    atexit.register(shutil.rmtree, destination, ignore_errors=True)
    return destination


def _stderr(completed: subprocess.CompletedProcess) -> str:
    text = (completed.stderr or b"").decode("utf-8", "replace").strip()
    return text.splitlines()[-1] if text else "unknown git error"
