"""The cost of a change, measured the way every other number here is.

A pull request is a change to a context budget, and nothing in this package
could state what one costs. The GitHub Action needs it: "this PR adds +41,882
tokens, 92% of it a lockfile" is the sentence that makes an install happen.

Two honesty rules carry over from the rest of the package.

**Nothing is subtracted across walks with different inputs.** Each side is
walked with its *own* repository's ignore inputs -- the point is what an
agent reading each tree pays. Because the comparison happens per file, a
``.gitignore`` rule that appeared between base and head shows up as churn on
the files it hides rather than vanishing silently inside a plausible total.

**Attribution is measured, not guessed.** The head tree is classified with
the ordinary waste classifiers, and a file's contribution lands under the
rule that fired on it there. A file no rule fires on is ``unclassified`` --
real work, which is exactly the number a reviewer needs to see separated
from the noise.
"""

from __future__ import annotations

import contextlib
import os

from .classify import Finding
from .reduce import Reduction, reduce_repository
from .walk import WalkResult, walk_repository

__all__ = ["Delta", "FileDelta", "measure_delta"]


class FileDelta:
    """One file's contribution to the change."""

    __slots__ = ("path", "change", "tokens")

    def __init__(self, path: str, change: str, tokens: int):
        self.path = path
        #: ``added`` | ``removed`` | ``grown`` | ``shrunk``
        self.change = change
        #: Magnitude of the contribution (always positive).
        self.tokens = tokens

    def as_dict(self) -> dict:
        return {"path": self.path, "change": self.change, "tokens": self.tokens}


class Delta:
    """What changed in a context budget between two trees."""

    def __init__(
        self,
        *,
        before: int,
        after: int,
        files: list[FileDelta],
        attribution: dict[str, int],
    ):
        self.before = before
        self.after = after
        self.files = files
        #: Added tokens by waste-rule name, plus ``unclassified``.
        self.attribution = attribution

    @property
    def added(self) -> int:
        return max(0, self.after - self.before)

    @property
    def removed(self) -> int:
        return max(0, self.before - self.after)

    def as_dict(self) -> dict:
        return {
            "before": self.before,
            "after": self.after,
            "added": self.added,
            "removed": self.removed,
            "attribution": dict(
                sorted(self.attribution.items(), key=lambda kv: -kv[1])
            ),
            "files": [f.as_dict() for f in self.files],
        }


def measure_delta(base_root: str, head_root: str) -> Delta:
    """Measure both trees per file and compare them by path.

    Attribution runs the classifiers over the head tree, so "+412k of it is a
    lockfile" is a measurement of files that exist in the head tree -- not an
    inference from filenames alone.
    """
    def costs(root: str) -> tuple[WalkResult, dict[str, int]]:
        walked = walk_repository(os.path.abspath(root), use_gitignore=True)
        return walked, {
            cost.path: cost.tokens for cost in walked.text_files
        }

    _, base_costs = costs(base_root)
    head_walk, head_costs = costs(head_root)

    files: list[FileDelta] = []
    for path in sorted(set(base_costs) | set(head_costs)):
        b, h = base_costs.get(path), head_costs.get(path)
        if b is None:
            files.append(FileDelta(path, "added", h))
        elif h is None:
            files.append(FileDelta(path, "removed", b))
        elif h > b:
            files.append(FileDelta(path, "grown", h - b))
        elif h < b:
            files.append(FileDelta(path, "shrunk", b - h))

    # Attribute every positive contribution through the head-tree classifiers,
    # so the split between "lockfile" and "real work" is measured, not guessed.
    findings: dict[str, Finding] = {}
    with contextlib.suppress(OSError):
        # An unmeasurable head tree degrades attribution to ``unclassified``
        # rather than failing a delta that was measured fine.
        reduction: Reduction | None = reduce_repository(head_root)
        findings = {f.path: f for f in reduction.findings}

    attribution: dict[str, int] = {}
    for fdelta in files:
        if fdelta.change == "removed":
            continue
        finding = findings.get(fdelta.path)
        name = finding.rule.name if finding else "unclassified"
        attribution[name] = attribution.get(name, 0) + fdelta.tokens

    return Delta(
        before=sum(base_costs.values()),
        after=sum(head_costs.values()),
        files=files,
        attribution=attribution,
    )
