"""How many tokens a piece of text costs, without a tokenizer.

The honest problem first. An exact answer needs the model's own tokenizer,
which means ``tiktoken`` — a compiled dependency, a wheel per platform, and a
download. This tool exists to *save* people effort, so making them install a
build toolchain to find out what their repository costs is the wrong trade.

So this estimates, and the report says so. That is the whole design decision:
a number presented as exact when it is not is worse than a number presented as
approximate with a stated error, because the first one gets quoted in a
decision and the second one gets checked.

The estimator is character-class based rather than a flat characters-per-token
ratio, because a flat ratio is wrong in opposite directions for the two things
a repository is mostly made of. Prose compresses well: common English words
are single tokens, so it lands near 4 characters per token. Source code does
not: punctuation, camelCase boundaries, indentation runs and long identifiers
all split, and dense code lands closer to 3. Minified or base64 content is
worse still, near 2, which matters because those are exactly the files this
tool is looking for.

:func:`calibrate` in ``docs/`` measures the error against a real tokenizer and
writes the bound that :data:`ERROR_BOUND` reports. Nothing here claims an
accuracy that has not been measured.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = [
    "ERROR_BOUND",
    "Estimate",
    "estimate_tokens",
    "looks_binary",
]

#: Measured relative error of :func:`estimate_tokens` against the reference
#: tokenizer, over the calibration corpus in ``docs/calibration/``. Regenerate
#: with ``python docs/calibrate.py`` after any change to the estimator, and
#: never edit this by hand -- an error bound nobody measured is the exact kind
#: of confident-looking wrong number this tool is built to avoid.
ERROR_BOUND = 0.12

#: Characters per token, by what the text is made of. Derived in
#: ``docs/calibrate.py``; see the module docstring for why one ratio is not
#: enough.
PROSE_RATIO = 4.05
CODE_RATIO = 3.15
DENSE_RATIO = 2.30

#: Runs of this many characters without whitespace are treated as dense:
#: base64 payloads, minified bundles, hashes, embedded data URIs. Chosen
#: because ordinary source lines break well below it -- the longest identifiers
#: in real code are rarely past 40 characters, and a 64-character unbroken run
#: is nearly always machine-generated.
DENSE_RUN = 64

#: Bytes to read when deciding whether a file is text at all.
SNIFF_BYTES = 8192

_WORD = re.compile(r"[A-Za-z]{2,}")
_PUNCT = re.compile(r"[^\w\s]")
_LONG_RUN = re.compile(rf"\S{{{DENSE_RUN},}}")


@dataclass(frozen=True)
class Estimate:
    """An estimated token count, and the reason it is only an estimate."""

    tokens: int
    characters: int
    #: Which ratio dominated: ``prose``, ``code`` or ``dense``.
    kind: str

    @property
    def low(self) -> int:
        """Lower end of the measured error band."""
        return int(self.tokens * (1.0 - ERROR_BOUND))

    @property
    def high(self) -> int:
        return int(self.tokens * (1.0 + ERROR_BOUND))

    def as_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "low": self.low,
            "high": self.high,
            "characters": self.characters,
            "kind": self.kind,
        }


def looks_binary(sample: bytes) -> bool:
    """Whether these bytes are not worth counting as text.

    A NUL byte is the classic signal and is what git itself uses. The second
    test catches files that are technically decodable but are not text a
    reader would read -- a run of bytes with no printable structure.
    """
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    printable = sum(
        1
        for byte in sample
        if byte in (9, 10, 13) or 32 <= byte < 127 or byte >= 128
    )
    return printable / len(sample) < 0.85


def _classify(text: str) -> str:
    """Decide which ratio applies, from what the text is made of.

    Order matters. Dense is checked first because a minified bundle is
    syntactically code and would otherwise be charged the code rate, which
    understates it by nearly a third -- and understating exactly the files
    this tool is meant to find would be the worst possible failure.
    """
    if not text:
        return "prose"
    dense_chars = sum(len(m.group()) for m in _LONG_RUN.finditer(text))
    if dense_chars / len(text) > 0.25:
        return "dense"
    words = sum(len(m.group()) for m in _WORD.finditer(text))
    punctuation = len(_PUNCT.findall(text))
    # Prose is mostly letters with little punctuation; code is the reverse.
    # The thresholds are deliberately far apart, so anything ambiguous falls
    # through to the code ratio -- the safer default, because over-estimating
    # a documentation file is cheaper than under-estimating a source tree.
    if words / len(text) > 0.72 and punctuation / max(len(text), 1) < 0.06:
        return "prose"
    return "code"


def estimate_tokens(text: str) -> Estimate:
    """Estimate the token cost of ``text``.

    CJK is counted separately because the ratio does not apply to it at all:
    Latin script averages several characters per token, while a CJK character
    is usually a token on its own and sometimes two. A repository with Chinese
    documentation would otherwise be under-counted by a factor of three.
    """
    if not text:
        return Estimate(0, 0, "prose")

    cjk = sum(1 for ch in text if _is_cjk(ch))
    rest = len(text) - cjk

    kind = _classify(text)
    ratio = {"prose": PROSE_RATIO, "code": CODE_RATIO, "dense": DENSE_RATIO}[kind]

    # 1.05 rather than 1.0 for CJK: most common characters are one token, but
    # rarer ones split into two, and the average sits just above one.
    tokens = int(round(rest / ratio + cjk * 1.05))
    return Estimate(max(tokens, 1 if text.strip() else 0), len(text), kind)


def _is_cjk(char: str) -> bool:
    if char < "⺀":  # fast path: all of ASCII and Latin-1
        return False
    return unicodedata.east_asian_width(char) in ("W", "F")
