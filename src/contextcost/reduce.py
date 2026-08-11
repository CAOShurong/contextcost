"""Propose exclusions, then walk the repository again to find out what they did.

Every tool in this space reports a saving. Almost all of them compute it by
adding up the things they decided to drop, which measures the tool's own
opinion rather than the repository. If a pattern silently matches more than it
was meant to, that arithmetic cannot tell -- the number goes up, and up is what
it was going to report anyway.

So nothing here subtracts. A proposal is turned into ignore patterns, the
repository is walked a second time with those patterns applied, and the saving
is the difference between two measurements. :func:`contextcost.walk.walk_repository`
takes ``extra_ignore=`` for precisely this and for nothing else.

That buys a check worth more than the number itself. The files that disappeared
between the two walks can be compared against the files the proposal named, and
**those two sets must be equal**. When they are not, a pattern over-reached:
`build/` written for a build directory also caught `src/build/config.py`. The
patterns are then narrowed to exact paths, the repository is walked a third
time, and the report says the narrowing happened. A rule that quietly removed a
source file would be the worst possible outcome for a tool that people run
because they distrust their context budget, and it is invisible to any approach
that does not go back and look.

The discipline is borrowed from ``evalint``, whose reduction step recomputes its
ranking after every layer and rolls back with a note when the answer moves. It
exists there because an early version reported "96% fewer calls" beside a
leaderboard that had quietly reversed.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .classify import Finding, classify
from .ignorefile import consumer_write_file
from .walk import FileCost, WalkResult, walk_repository

__all__ = ["Reduction", "propose_patterns", "reduce_repository"]

#: Confidence tiers acted on without being asked. ``possible`` is deliberately
#: absent: those are the files the file system cannot judge, and deciding them
#: silently is the one thing this tool must not do. ``--include-possible``
#: moves them in, which makes it the user's decision rather than the default.
ACTED_ON = ("certain", "likely")

#: Characters that mean something in a gitignore pattern. A path containing one
#: cannot be used as a literal, so those findings fall back to being listed
#: rather than patterned -- rare, and the verification step below would catch
#: it anyway, but failing early is cheaper than failing loudly.
_GLOB_METACHARACTERS = re.compile(r"[*?\[\]\\]")


@dataclass
class Reduction:
    """What was proposed, and what walking the repository again showed."""

    root: str
    before: int
    #: Measured by a second walk, never by subtraction.
    after: int
    patterns: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    #: Files that actually stopped being counted between the two walks.
    excluded: list[FileCost] = field(default_factory=list)
    #: Set when a proposed pattern removed files nobody proposed, and the
    #: patterns were narrowed to exact paths in response. Printed by the
    #: report, because a silent correction is just a quieter version of the
    #: bug it corrected.
    narrowed_from: list[str] = field(default_factory=list)
    #: Findings left for the user to decide: the ``possible`` tier.
    deferred: list[Finding] = field(default_factory=list)
    # New v0.2 fields stay after the v0.1 positional fields for compatibility.
    consumer: str = "generic"
    ignore_file: str = ".gitignore"

    @property
    def saved(self) -> int:
        return self.before - self.after

    @property
    def share(self) -> float:
        """Saving as a fraction of the original cost, 0.0 if there was none."""
        return self.saved / self.before if self.before else 0.0

    @property
    def deferred_tokens(self) -> int:
        return sum(f.tokens for f in self.deferred)

    def as_dict(self) -> dict:
        return {
            "root": self.root,
            "consumer": self.consumer,
            "ignore_file": self.ignore_file,
            "before": self.before,
            "after": self.after,
            "saved": self.saved,
            "share": round(self.share, 4),
            "measured": True,
            "patterns": self.patterns,
            "excluded": [c.as_dict() for c in self.excluded],
            "narrowed_from": self.narrowed_from,
            "findings": [f.as_dict() for f in self.findings],
            "deferred": [f.as_dict() for f in self.deferred],
        }

    def gitignore_block(self, patterns: list[str] | None = None) -> str:
        """The proposal, as text to append to a `.gitignore`.

        ``patterns`` narrows the block to a subset, which is how a second run
        appends only what is new instead of repeating itself.
        """
        chosen = self.patterns if patterns is None else patterns
        if not chosen:
            return ""
        lines = [
            "# Added by contextcost: files an AI coding agent pays to read",
            f"# and does not need. Measured saving: {self.saved:,} of "
            f"{self.before:,} tokens ({self.share:.0%}).",
        ]
        lines.extend(chosen)
        return "\n".join(lines) + "\n"


def _directory_of(path: str) -> str:
    head, _, _ = path.rpartition("/")
    return head


def _anchored(path: str) -> str:
    """One file path as a gitignore pattern that matches only that file.

    The leading slash matters more than it looks. Without it `yarn.lock` is
    unanchored and matches at any depth, so a proposal aimed at the lockfile in
    the root would also silently take out `packages/web/yarn.lock`.
    """
    return "/" + path


def propose_patterns(result: WalkResult, findings: list[Finding]) -> list[str]:
    """Ignore patterns covering ``findings`` and, ideally, nothing else.

    A directory is proposed whole when every text file under it was found to
    be waste -- `vendor/` reads better than two hundred paths, and it keeps
    covering the directory as it grows. Otherwise each file is named exactly.
    Whether that reasoning was right is not taken on trust; the caller walks
    the repository again and checks.
    """
    wasteful = {f.path for f in findings}
    if not wasteful:
        return []

    kept_by_directory: dict[str, set[str]] = {}
    for cost in result.text_files:
        kept_by_directory.setdefault(_directory_of(cost.path), set()).add(cost.path)

    whole_directories = set()
    for directory, paths in kept_by_directory.items():
        if directory and paths <= wasteful:
            whole_directories.add(directory)

    # Keep only the shallowest of a nested run: proposing `vendor/` and
    # `vendor/lib/` says the same thing twice and reads like two findings.
    roots = set()
    for directory in sorted(whole_directories, key=lambda d: d.count("/")):
        parents = [p for p in roots if directory.startswith(p + "/")]
        if not parents:
            roots.add(directory)

    patterns = {f"/{directory}/" for directory in roots}
    for path in sorted(wasteful):
        if any(path.startswith(directory + "/") for directory in roots):
            continue
        if _GLOB_METACHARACTERS.search(path):
            # A path that is itself a glob cannot be written as a literal
            # pattern. Left out on purpose; it shows up as a finding the
            # proposal did not cover rather than as a pattern that might
            # match something else.
            continue
        patterns.add(_anchored(path))
    return sorted(patterns)


def _paths(result: WalkResult) -> dict[str, FileCost]:
    return {cost.path: cost for cost in result.files}


def reduce_repository(
    root: str,
    *,
    use_gitignore: bool = True,
    include_possible: bool = False,
    consumer: str = "generic",
) -> Reduction:
    """Measure the repository, propose exclusions, and measure it again.

    ``include_possible`` moves the ``possible`` tier -- large data files,
    mostly -- from "listed for you to decide" into the proposal. It is off by
    default because the file system genuinely cannot tell whether a large CSV
    is a fixture or the subject of the work.
    """
    root = os.path.abspath(root)
    before = walk_repository(root, use_gitignore=use_gitignore, consumer=consumer)
    findings = classify(before)

    tiers = ACTED_ON + ("possible",) if include_possible else ACTED_ON
    chosen = [f for f in findings if f.rule.confidence in tiers]
    deferred = [f for f in findings if f.rule.confidence not in tiers]

    reduction = Reduction(
        root=root,
        before=before.tokens,
        after=before.tokens,
        consumer=consumer,
        ignore_file=consumer_write_file(consumer),
        findings=chosen,
        deferred=deferred,
    )
    if not chosen:
        return reduction

    patterns = propose_patterns(before, chosen)
    if not patterns:
        return reduction

    after = walk_repository(
        root,
        use_gitignore=use_gitignore,
        extra_ignore=patterns,
        consumer=consumer,
    )

    intended = {f.path for f in chosen}
    before_paths = _paths(before)
    removed = set(before_paths) - set(_paths(after))
    unexpected = removed - intended

    if unexpected:
        # A pattern took more than it was written for. Fall back to naming
        # every file, which cannot over-reach, and walk a third time. The
        # report says this happened; correcting it silently would leave the
        # user trusting a pattern set that had already been wrong once.
        reduction.narrowed_from = patterns
        patterns = sorted(
            _anchored(p) for p in intended if not _GLOB_METACHARACTERS.search(p)
        )
        after = walk_repository(
            root,
            use_gitignore=use_gitignore,
            extra_ignore=patterns,
            consumer=consumer,
        )
        removed = set(before_paths) - set(_paths(after))

    reduction.patterns = patterns
    reduction.after = after.tokens
    reduction.excluded = sorted(
        (before_paths[path] for path in removed), key=lambda c: -c.tokens
    )
    return reduction
