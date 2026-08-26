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
ratio, because a flat ratio is wrong in opposite directions for the things a
repository is made of. Measured against ``cl100k_base``: prose runs about 4.5
characters per token, source code about 4.1, a structured manifest or minified
bundle about 3.4, and opaque content -- base64, columns of hex digests -- about
1.4, because there is nothing in it for a byte-pair encoder to merge.

Every one of those numbers came out of ``docs/calibrate.py``. The first version
of this module had them at 4.05 / 3.15 / 2.30, chosen by reasoning about how
tokenizers behave, and reasoning turned out to be wrong by roughly 30% on real
code and wrong in *both* directions on dense content at once. Nothing here is a
number somebody thought sounded right.

Run ``python docs/calibrate.py`` after any change to this file, and
``--check`` in CI so that drift fails a build rather than silently widening the
truth. See :data:`ERROR_BOUND` for the caveat about which tokenizer.
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

#: Measured 95th-percentile relative error of :func:`estimate_tokens` against
#: ``cl100k_base``. Regenerate with ``python docs/calibrate.py`` after any
#: change to the estimator, and never edit it by hand.
#:
#: It said 0.12 for the whole of this module's first life, and that number was
#: chosen rather than measured, because ``docs/calibrate.py`` did not exist --
#: the comment above it confidently cited a script nobody had written. When the
#: script was finally written the real figure was more than four times worse.
#: An unmeasured bound presented as a measurement, inside the tool whose entire
#: argument is against exactly that, is the most embarrassing defect this
#: project has had, and it is recorded here rather than quietly corrected.
ERROR_BOUND = 0.23

#: Characters per token, measured over real files with ``docs/calibrate.py``,
#: not chosen. See the module docstring for why one ratio cannot serve.
PROSE_RATIO = 4.52
CODE_RATIO = 4.14

#: Dense content is bimodal, which one ratio cannot express and the first
#: version of this file did not notice. A minified bundle or a JSON manifest
#: still has punctuation and repeated keys, and the tokenizer eats those in
#: large bites: ~3.4 characters per token. A base64 payload or a column of hex
#: digests has almost no structure to merge and costs ~1.4 -- more than twice
#: as much per character. A single value in the middle was wrong in both
#: directions at once.
DENSE_STRUCTURED_RATIO = 3.38
DENSE_OPAQUE_RATIO = 1.41

#: Chars per token for hash-dense lockfiles -- ``uv.lock``, ``Cargo.lock``,
#: ``package-lock.json``, ``yarn.lock``. Found by running ``--accurate``
#: against 437 real such files: they read at a median **2.18** chars/token
#: against ``cl100k_base``, but the generic structured ratio (3.38) charged
#: them as if they were JSON manifests and under-counted by **~35%**. A
#: repository whose cost is dominated by a lockfile therefore breached the
#: printed error band the instant anyone verified it -- which is exactly the
#: trust the rest of this tool's numbers rest on. Lockfile punctuation is
#: almost entirely ``: = + - / . _`` separators between hashes and versions,
#: which a byte-pair encoder has nothing to merge; a genuine manifest's is
#: ``{}",`` and merges well. The two populations do not overlap at the
#: threshold below, so the discriminator is a hard cut, not a fuzzy one.
DENSE_HASHY_RATIO = 2.2

#: Share of a file's punctuation that must be hashy separators (``: = + - / .
#: _``) before it is charged :data:`DENSE_HASHY_RATIO` instead of
#: :data:`DENSE_STRUCTURED_RATIO`. Measured: uv.lock / Cargo.lock /
#: package-lock.json sit at 0.42-0.58 (real minified bundles at a median 0.29,
#: genuine JSON manifests well below 0.3), so 0.4 separates the lockfile
#: population from the rest with a clear margin.
DENSE_HASHY_PUNCTUATION = 0.4

#: Punctuation share separating the two. Measured, and the gap is wide: random
#: base64 sits at 0.032, hex digests at 0.000, and real manifests at 0.104.
DENSE_PUNCTUATION = 0.06

#: The `numeric` class: numeric data dumps -- JSON number matrices, recorded
#: fixture arrays, locale number tables. Found by running ``--accurate``
#: against plotly.js, where the estimate read 45 M tokens and the tokenizer
#: said 64 M; the gap was dominated by files like a parcoords fixture whose
#: body is thousands of small integers, charged at the code ratio (4.14) but
#: actually costing ~1.2 characters per token. Measured against cl100k_base,
#: a byte-pair encoder merges digits poorly: random digit streams cost about
#: one token per three characters, so the more of a file is digits, the lower
#: its characters-per-token.
#:
#: A file qualifies when it was classified as code (so prose with figures and
#: ordinary source are untouched), at least this share of it is digits...
NUMERIC_MIN_DIGIT = 0.10

#: ...and under this share is letters, so JSON keys and identifiers do not
#: drag ordinary source files into the class...
NUMERIC_MAX_ALPHA = 0.25

#: ...and the digits outnumber the letters, which keeps number-heavy but
#: still word-shaped test code out. All three bounds were swept over four
#: real repositories (plotly.js, astropy, h5py, pandas); these are the values
#: that minimised per-file regressions while fixing the drift.
#:
#: The ratio itself is one over the digit share, capped here. The cap exists
#: because long decimal fractions ("0.04000000000000001") tokenize better than
#: their digit share predicts -- the sign, dot and shared prefixes give the
#: encoder something to merge -- so pure-digit extrapolation overshoots on
#: them. 2.2 minimised regressions across the same four-repository sweep;
#: below it, aggregate drift improves but individual long-decimal files get
#: worse by more than the aggregate gains.
NUMERIC_MAX_RATIO = 2.2

#: Below this digit share, one-over-digit exceeds the cap anyway, so the file
#: is simply charged NUMERIC_MAX_RATIO -- see :func:`_numeric_ratio`.
NUMERIC_MIN_RATIO_DIGIT = 0.05

#: Tokens per CJK character, by script. A CJK character is roughly one token,
#: which is why a single constant survived so long -- but "roughly" hides a
#: 32% spread, and it is wrong in both directions at once.
#:
#: Traditional Chinese is the case that matters most here and was the worst:
#: the tokenizer has far fewer merges for it than for simplified, so the same
#: sentence costs 44% more. The author works in Hong Kong and writes
#: traditional Chinese documentation, which is exactly the first user this
#: would have quietly under-billed by a third.
CJK_HAN_SIMPLIFIED = 1.08
CJK_HAN_TRADITIONAL = 1.55
CJK_KANA = 0.85
CJK_HANGUL = 1.1

#: Share of Han characters that must be traditional-only before the text is
#: treated as traditional. Measured samples land at 27% for traditional prose
#: and 0% for simplified, so anything in this region separates them; low
#: enough to catch a mostly-simplified document quoting traditional text.
TRADITIONAL_THRESHOLD = 0.03

#: Characters that exist only in traditional Chinese. Deliberately short --
#: it needs to recognise the script, not to be a conversion table, and every
#: one of these is common enough to appear within a sentence or two of real
#: traditional prose.
_TRADITIONAL_ONLY = frozenset(
    "這個們學灣體應對開關國經濟發展壓縮實現轉換處數時讀寫證驗倉檔編範圍點擊選擇來說進當義關聯網絡機軟資訊執測錯誤變條標準將無齊圖書館買賣讓認識稱職業"
)

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
        1 for byte in sample if byte in (9, 10, 13) or 32 <= byte < 127 or byte >= 128
    )
    return printable / len(sample) < 0.85


def _classify(text: str) -> str:
    """Decide which ratio applies, from what the text is made of.

    Order matters. Dense is checked first because a minified bundle is
    syntactically code and would otherwise be charged the code rate, which
    understates it by nearly a third -- and understating exactly the files
    this tool is meant to find would be the worst possible failure.
    Numeric is checked next for the same reason in the opposite register:
    numeric data dumps look like cheap code (letters, punctuation, digits --
    all plausible source) but cost up to four times more per character than
    the code ratio assumes, so they are under-counted, which is worse than
    over-counting a documentation file by the same margin. Prose stays last
    because its test is the most specific.
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


def _numeric_ratio(digit_share: float) -> float:
    """Characters per token for a numeric file with this digit share.

    One over the share, capped at :data:`NUMERIC_MAX_RATIO`: pure digits cost
    about one token per three characters against ``cl100k_base``, and files
    below the cap's break-even digit share are all close enough to it that
    the cap itself is the better estimate.
    """
    return min(1.0 / max(digit_share, NUMERIC_MIN_RATIO_DIGIT), NUMERIC_MAX_RATIO)


def _is_numeric(text: str, kind: str) -> bool:
    """Whether a non-dense, non-prose text is a numeric data dump.

    See the class constants above for where each bound came from. The shares
    are of *all* characters, matching how :func:`_classify` measures, so a
    file cannot drift into the class by whitespace alone.
    """
    if kind != "code":
        return False
    n = len(text)
    digits = alpha = 0
    for ch in text:
        if ch.isdigit():
            digits += 1
        elif "a" <= ch <= "z" or "A" <= ch <= "Z":
            alpha += 1
    digit_share = digits / n
    return (
        digit_share >= NUMERIC_MIN_DIGIT
        and alpha / n < NUMERIC_MAX_ALPHA
        and digit_share >= alpha / n
    )


def _dense_ratio(text: str) -> float:
    """Which of the dense ratios applies.

    There are three populations, not two. Opaque dense content -- base64 or
    hex digests -- offers nothing to merge; a byte-pair encoder pays well over
    twice the structured rate (DENSE_OPAQUE_RATIO). Structured content -- a
    minified bundle, a JSON manifest -- keeps its ``{}",`` punctuation, and the
    encoder merges those repeated fragments greedily (DENSE_STRUCTURED_RATIO).
    Hash-dense lockfiles -- uv.lock, Cargo.lock, package-lock.json -- sit
    between: their punctuation is almost entirely ``= : + - / . _`` separators
    between hashes and versions, which merge poorly, so they cost ~2.2
    chars/token, far more than a manifest (DENSE_HASHY_RATIO). The three
    populations separate cleanly on punctuation share, so the discriminators
    are hard cuts rather than a fuzzy line.
    """
    marks = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
    share = marks / len(text) if text else 0.0
    if share < DENSE_PUNCTUATION:
        return DENSE_OPAQUE_RATIO
    hashy = sum(1 for ch in text if ch in ":=-/._")
    return (
        DENSE_HASHY_RATIO
        if hashy / marks >= DENSE_HASHY_PUNCTUATION
        else DENSE_STRUCTURED_RATIO
    )


def _traditional_share(text: str) -> float:
    """How much of the Han in ``text`` is written in traditional characters.

    Simplified and traditional Chinese occupy the same Unicode block, so a
    codepoint range cannot separate them. This looks for characters that exist
    only in the traditional set. The two populations do not overlap in
    practice: measured over prose samples, traditional text scores about 27%
    and simplified text scores 0%.
    """
    han = [ch for ch in text if "一" <= ch <= "鿿"]
    if not han:
        return 0.0
    return sum(1 for ch in han if ch in _TRADITIONAL_ONLY) / len(han)


def _cjk_tokens(text: str) -> float:
    """Estimated tokens for the CJK characters in ``text``.

    One ratio for all of CJK was wrong by up to 32%, and wrong in both
    directions: traditional Chinese costs 1.55 tokens per character while kana
    costs 0.85. Every figure here is measured by ``docs/calibrate.py``.
    """
    han = kana = hangul = other = 0
    for ch in text:
        if not _is_cjk(ch):
            continue
        if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿":
            han += 1
        elif "぀" <= ch <= "ヿ":
            kana += 1
        elif "가" <= ch <= "힯" or "ᄀ" <= ch <= "ᇿ":
            hangul += 1
        else:
            # Fullwidth punctuation and the CJK symbol block. Close enough to
            # one token each, and too small a share to be worth calibrating.
            other += 1

    han_ratio = (
        CJK_HAN_TRADITIONAL
        if _traditional_share(text) >= TRADITIONAL_THRESHOLD
        else CJK_HAN_SIMPLIFIED
    )
    return han * han_ratio + kana * CJK_KANA + hangul * CJK_HANGUL + other * 1.0


def estimate_tokens(text: str) -> Estimate:
    """Estimate the token cost of ``text``.

    CJK is counted separately because the characters-per-token ratio does not
    apply to it at all: Latin script averages several characters per token,
    while a CJK character is usually a token on its own and sometimes two. A
    repository with Chinese documentation would otherwise be under-counted by
    a factor of three.
    """
    if not text:
        return Estimate(0, 0, "prose")

    cjk = sum(1 for ch in text if _is_cjk(ch))
    rest = len(text) - cjk

    kind = _classify(text)
    if kind == "dense":
        ratio = _dense_ratio(text)
    elif _is_numeric(text, kind):
        # A distinct reported class, not a sub-case of code: the report and
        # the JSON output say `numeric`, so a reader can see which files the
        # specialised ratio was applied to rather than taking it on faith.
        kind = "numeric"
        ratio = _numeric_ratio(sum(ch.isdigit() for ch in text) / len(text))
    else:
        ratio = {"prose": PROSE_RATIO, "code": CODE_RATIO}[kind]

    tokens = int(round(rest / ratio + _cjk_tokens(text)))
    return Estimate(max(tokens, 1 if text.strip() else 0), len(text), kind)


def _is_cjk(char: str) -> bool:
    if char < "⺀":  # fast path: all of ASCII and Latin-1
        return False
    return unicodedata.east_asian_width(char) in ("W", "F")
