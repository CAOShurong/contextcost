"""Walking a repository and attributing what it costs to read.

The output of this module is one number per file and the sums that roll up
from it. Everything downstream -- what is wasteful, what to exclude, how much
that saves -- is an opinion about these numbers, so the numbers have to be
defensible first.

Three decisions shape them.

**Only what the selected consumer can consider.** Ignored paths are skipped,
and an ignored directory is never descended into. Counting `.venv/` would
make every repository look identically enormous and the report worthless.
The generic profile follows nested ``.gitignore`` files; Cursor, Aider and
Repomix profiles add their documented root ignore files. The result records
those inputs, because the same tree can have different eligible context for
different tools.

**Binary files cost nothing here, and that is a claim worth stating.** An
agent does not read a PNG as text; it either skips it or pays for a wholly
different representation. Charging it the text rate would be inventing a
number. So they are counted, sized, and reported as a separate quantity that
is deliberately not added to the token total.

**Unreadable is not empty.** A file that cannot be decoded, or that vanishes
mid-walk, is recorded as skipped with the reason. Silently treating it as zero
would understate the total in exactly the cases where something odd is going
on.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .estimate import SNIFF_BYTES, estimate_tokens, looks_binary
from .ignorefile import (
    ALWAYS_SKIP,
    IgnoreRules,
    active_ignore_files,
    load_ignore_rules,
    parse_ignore,
)

__all__ = ["FileCost", "WalkResult", "walk_repository"]

#: Files at or above this size are sampled rather than read whole. A 40 MB
#: generated file does not need to be measured exactly to be reported as the
#: problem -- and reading it whole is the one thing that would make this tool
#: slow on the repositories that most need it.
SAMPLE_ABOVE = 2 * 1024 * 1024


@dataclass(frozen=True)
class FileCost:
    """What one file contributes."""

    path: str
    bytes: int
    tokens: int
    #: ``prose``, ``code`` or ``dense`` -- see :mod:`contextcost.estimate`.
    kind: str
    binary: bool = False
    #: Set when the token count was extrapolated from a sample rather than
    #: measured, so the report can say so instead of implying precision.
    sampled: bool = False

    @property
    def extension(self) -> str:
        _, dot, suffix = os.path.basename(self.path).rpartition(".")
        return f".{suffix.lower()}" if dot else "(none)"

    @property
    def directory(self) -> str:
        head, _, _ = self.path.rpartition("/")
        return head or "."

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "bytes": self.bytes,
            "tokens": self.tokens,
            "kind": self.kind,
            "binary": self.binary,
            "sampled": self.sampled,
        }


@dataclass
class WalkResult:
    """Every file that would be read, and what it costs."""

    root: str
    files: list[FileCost] = field(default_factory=list)
    #: Paths skipped, and why. Kept rather than discarded because "I did not
    #: read this" is information the reader needs to trust the total.
    skipped: list[tuple[str, str]] = field(default_factory=list)
    ignored_count: int = 0
    # New v0.2 fields stay after the v0.1 positional fields so constructing a
    # public result object positionally does not silently change meaning.
    consumer: str = "generic"
    #: Existing ignore inputs applied at the root, plus nested .gitignore files
    #: discovered during traversal. Exposed so a number says what shaped it.
    ignore_files: list[str] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return sum(f.tokens for f in self.files if not f.binary)

    @property
    def text_files(self) -> list[FileCost]:
        return [f for f in self.files if not f.binary]

    @property
    def binary_files(self) -> list[FileCost]:
        return [f for f in self.files if f.binary]

    @property
    def bytes(self) -> int:
        return sum(f.bytes for f in self.files)

    def by_directory(self, depth: int = 1) -> dict[str, int]:
        """Token totals rolled up to ``depth`` path segments.

        Depth rather than full paths because the actionable unit is a
        top-level directory -- nobody excludes ``src/a/b/c``, they exclude
        ``vendor``.
        """
        totals: dict[str, int] = {}
        for cost in self.text_files:
            parts = cost.path.split("/")
            key = "/".join(parts[:depth]) if len(parts) > depth else parts[0]
            if len(parts) <= depth and len(parts) == 1:
                key = "(root)"
            totals[key] = totals.get(key, 0) + cost.tokens
        return dict(sorted(totals.items(), key=lambda kv: -kv[1]))

    def by_extension(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for cost in self.text_files:
            totals[cost.extension] = totals.get(cost.extension, 0) + cost.tokens
        return dict(sorted(totals.items(), key=lambda kv: -kv[1]))

    def largest(self, count: int = 20) -> list[FileCost]:
        return sorted(self.text_files, key=lambda f: -f.tokens)[:count]

    def as_dict(self) -> dict:
        return {
            "root": self.root,
            "consumer": self.consumer,
            "ignore_files": self.ignore_files,
            "tokens": self.tokens,
            "bytes": self.bytes,
            "files": len(self.files),
            "text_files": len(self.text_files),
            "binary_files": len(self.binary_files),
            "ignored": self.ignored_count,
            "skipped": [{"path": p, "reason": r} for p, r in self.skipped],
        }


def _read_text(path: str, size: int) -> tuple[str, bool, bool]:
    """Return ``(text, is_binary, sampled)`` for one file."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(SNIFF_BYTES)
            if looks_binary(head):
                return "", True, False
            if size > SAMPLE_ABOVE:
                # Extrapolation is honest here only because the caller marks
                # the result as sampled and the report repeats it.
                sample = head + handle.read(SAMPLE_ABOVE - len(head))
                return sample.decode("utf-8", errors="replace"), False, True
            rest = handle.read()
    except OSError as exc:  # pragma: no cover - platform dependent
        raise OSError(str(exc)) from exc
    return (head + rest).decode("utf-8", errors="replace"), False, False


def walk_repository(
    root: str,
    *,
    use_gitignore: bool = True,
    extra_ignore: list[str] | None = None,
    consumer: str = "generic",
) -> WalkResult:
    """Measure every file an agent would read under ``root``.

    ``extra_ignore`` holds additional gitignore-syntax patterns, which is how
    a proposed exclusion set is tried out: the reduction re-walks with them
    applied and compares, rather than subtracting estimates.
    """
    root = os.path.abspath(root)
    result = WalkResult(
        root=root,
        consumer=consumer,
        ignore_files=active_ignore_files(
            root, use_gitignore=use_gitignore, consumer=consumer
        ),
    )
    base = load_ignore_rules(root, use_gitignore=use_gitignore, consumer=consumer)
    if extra_ignore:
        base = base.extend(parse_ignore("\n".join(extra_ignore)))

    # One rule set per directory, so nested ignore files apply only below
    # themselves. Keyed by relative directory path.
    rules_for: dict[str, IgnoreRules] = {"": base}

    for current, dirnames, filenames in os.walk(root):
        relative_dir = os.path.relpath(current, root).replace(os.sep, "/")
        if relative_dir == ".":
            relative_dir = ""
        rules = rules_for.get(relative_dir, base)

        if use_gitignore and relative_dir:
            nested = os.path.join(current, ".gitignore")
            if os.path.isfile(nested):
                with open(nested, encoding="utf-8", errors="replace") as handle:
                    rules = rules.extend(parse_ignore(handle.read(), relative_dir))
                relative_ignore = f"{relative_dir}/.gitignore"
                if relative_ignore not in result.ignore_files:
                    result.ignore_files.append(relative_ignore)

        kept_dirs = []
        for name in dirnames:
            if name in ALWAYS_SKIP:
                result.ignored_count += 1
                continue
            child = f"{relative_dir}/{name}" if relative_dir else name
            if rules.ignored(child, is_dir=True):
                result.ignored_count += 1
                continue
            kept_dirs.append(name)
            rules_for[child] = rules
        # Sorted so a walk is reproducible; os.walk's order is filesystem
        # dependent and a report whose ties broke differently between runs
        # would look like it had changed its mind.
        dirnames[:] = sorted(kept_dirs)

        for name in sorted(filenames):
            relative = f"{relative_dir}/{name}" if relative_dir else name
            if rules.ignored(relative, is_dir=False):
                result.ignored_count += 1
                continue
            full = os.path.join(current, name)
            try:
                size = os.path.getsize(full)
            except OSError as exc:
                result.skipped.append((relative, f"cannot stat: {exc.strerror}"))
                continue
            if size == 0:
                result.files.append(FileCost(relative, 0, 0, "prose"))
                continue
            try:
                text, binary, sampled = _read_text(full, size)
            except OSError as exc:
                result.skipped.append((relative, f"cannot read: {exc}"))
                continue
            if binary:
                result.files.append(FileCost(relative, size, 0, "binary", binary=True))
                continue
            estimate = estimate_tokens(text)
            tokens = estimate.tokens
            if sampled and text:
                tokens = int(round(estimate.tokens * (size / len(text.encode()))))
            result.files.append(
                FileCost(relative, size, tokens, estimate.kind, sampled=sampled)
            )

    result.files.sort(key=lambda f: f.path)
    return result
