"""Exact token counts, when somebody installs the tokenizer.

The estimator in :mod:`contextcost.estimate` is deliberately tokenizer-free,
and that stays the default: zero dependencies is a feature, and ±14% is
accurate enough to answer "is this repo worth reading" and "which files are
the problem". But some decisions are made at a different resolution. A GitHub
Action commenting on a pull request does not want "roughly 40,000"; it wants
the number that will survive being quoted.

``--accurate`` buys that with ``pip install contextcost[accurate]``, which
brings in tiktoken -- a compiled dependency, one wheel per platform, plus a
one-time encoding download cached under the user's home directory. The CLI
fails with exit code 3 and an install hint rather than pretending.

**The estimate stays on screen next to the exact number, always.** The whole
argument of this tool is that a number without its uncertainty gets quoted
without it. Showing both lets the user see the estimator land inside its band,
which is the only reason anyone should trust the default mode later.

**Sampling stays sampling.** Files above ``SAMPLE_ABOVE`` already had their
estimate extrapolated from a prefix; counting them exactly here would mean
reading 40 MB through the tokenizer to move one number by less than the
estimator's error band, so they are counted from a same-size prefix too.
The result says so instead of implying precision.

**One encoder, stated.** ``cl100k_base`` is the same encoder
``docs/calibrate.py`` measured ERROR_BOUND against, so accurate and estimated
figures in the same report share a definition of a token.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .walk import SAMPLE_ABOVE, WalkResult

__all__ = [
    "ACCURATE_ENCODING",
    "AccurateResult",
    "FileAccuracy",
    "count_bytes",
    "count_repository",
    "count_text",
]

#: The encoder everything exact in this project is measured against.
ACCURATE_ENCODING = "cl100k_base"

_ENCODER = None


def _encoder():
    """Load the shared encoder once per process."""
    global _ENCODER
    if _ENCODER is None:
        import tiktoken

        _ENCODER = tiktoken.get_encoding(ACCURATE_ENCODING)
    return _ENCODER


def count_text(text: str) -> int:
    """Exactly how many tokens ``text`` costs the shared encoder.

    Special tokens in repository content are counted as text rather than
    raising: a lockfile quoting ``<|endoftext|>`` is content, not an
    instruction to the tokenizer.
    """
    return len(_encoder().encode(text, disallowed_special=()))


def count_bytes(data: bytes) -> int:
    """Exact tokens for raw file bytes, decoded exactly as the walk decodes."""
    return count_text(data.decode("utf-8", errors="replace"))


@dataclass(frozen=True)
class FileAccuracy:
    """The exact count for one file, beside what the walk estimated."""

    path: str
    #: Exact tokens when measured whole; prefix-based when ``sampled``.
    tokens: int
    #: What the walk's estimator said for the same file.
    estimated: int
    sampled: bool = False

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "tokens": self.tokens,
            "estimated": self.estimated,
            "sampled": self.sampled,
        }


@dataclass(frozen=True)
class AccurateResult:
    """Exact counts over everything a walk read, plus totals to compare."""

    encoding: str = ACCURATE_ENCODING
    files: list[FileAccuracy] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        """The exact total over the same set of files the walk measured."""
        return sum(f.tokens for f in self.files)

    @property
    def estimated_tokens(self) -> int:
        """The walk's estimate over those files, for the side-by-side."""
        return sum(f.estimated for f in self.files)

    @property
    def sampled_paths(self) -> list[str]:
        return [f.path for f in self.files if f.sampled]

    def as_dict(self) -> dict:
        return {
            "encoding": self.encoding,
            "tokens": self.tokens,
            "estimated_tokens": self.estimated_tokens,
            "files": [f.as_dict() for f in self.files],
            "sampled_files": self.sampled_paths,
        }


def count_repository(walk: WalkResult) -> AccurateResult:
    """Exactly count every text file the walk measured.

    Takes the walk's result rather than a path, so accurate mode can never see
    a different set of files than the estimate did: one walk, two counters on
    it. Binary files cost nothing here for the same reason they cost nothing
    upstream. A file that vanishes between the walk and this pass is recorded
    at zero and marked sampled -- an honest under-count beats a crash or an
    invented number.
    """
    files: list[FileAccuracy] = []
    for cost in walk.text_files:
        exact = 0
        sampled = cost.sampled
        if cost.bytes:
            full = os.path.join(walk.root, *cost.path.split("/"))
            try:
                with open(full, "rb") as handle:
                    data = handle.read(SAMPLE_ABOVE)
                    if len(data) < cost.bytes:
                        # Same prefix discipline as the estimator: the count is
                        # extrapolation either way, so mark it rather than
                        # spend seconds being precise about one big file.
                        sampled = True
            except OSError:
                sampled = True
                data = b""
            exact = count_bytes(data) if data else 0
            if sampled and data and len(data) < cost.bytes:
                scaled = round(exact * (cost.bytes / max(len(data), 1)))
                exact = int(scaled)
        files.append(FileAccuracy(cost.path, exact, cost.tokens, sampled))
    return AccurateResult(encoding=ACCURATE_ENCODING, files=files)
