"""Printing the numbers so that the uncertain ones still look uncertain.

A terminal report is a summary, and summarising is where honest analysis
usually goes to die: the caveats live in the docstrings, the headline is a
round number in bold, and the reader takes away the round number. This module
is where that would happen, so the constraints are here rather than upstream.

**The estimate carries its error everywhere it is printed.** ``132,963 tokens``
is a claim to six significant figures from a tool with no tokenizer. It is
always printed with its bound, because a number quoted without one gets quoted
again later without one.

**"Measured" and "estimated" are different words and are never mixed.** The
totals are estimates. The *saving* is a measurement -- the difference between
two walks -- and the report says which is which every time, since the whole
argument for the tool rests on that distinction.

**The tier the tool cannot judge gets its own section, phrased as a question.**
Not "excluded" but "your decision", with the rule's reasoning printed so the
reader can disagree on the spot. It is listed after the automatic proposal so
that it reads as unfinished business rather than as part of the result.

Colour degrades to nothing when the output is not a terminal, when ``NO_COLOR``
is set, or when ``--no-color`` is passed. Reports get piped into files and
pasted into issues far more often than tool authors expect.
"""

from __future__ import annotations

import os
import sys

from .classify import by_rule
from .estimate import ERROR_BOUND
from .reduce import Reduction
from .walk import WalkResult

__all__ = ["render", "supports_colour", "supports_unicode"]

#: Text shown when accurate counts are on but the encoder could not be
#: reached mid-run. Never expected; kept so the slot is honest rather than
#: silently blank.
_ACCURATE_UNAVAILABLE = "unavailable"

#: Drawing characters, and the plain-ASCII fallback used when the terminal
#: cannot encode them. This is not a nicety: the first Windows console this ran
#: in was cp936, where every block and arrow came out as `?`, turning the bar
#: chart into rows of identical noise and the saving line into `3,645,027 ?
#: 585,725`. A report that is unreadable in the author's own terminal would
#: not have survived first contact with anyone else's.
_GLYPHS = {
    True: {
        "fill": "█",
        "empty": "·",
        "arrow": "→",
        "plusminus": "±",
        "ellipsis": "…",
        "dot": "·",
    },
    False: {
        "fill": "#",
        "empty": ".",
        "arrow": "->",
        "plusminus": "+/-",
        "ellipsis": "...",
        "dot": "|",
    },
}

#: Width of the bar in the breakdown. Narrow on purpose: the bar is there to
#: make one row obviously dominant at a glance, not to be read off precisely.
#: Anyone who needs the exact figure has it printed beside the bar.
BAR_WIDTH = 28

_ANSI = {
    "dim": "\033[2m",
    "bold": "\033[1m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "cyan": "\033[36m",
    "reset": "\033[0m",
}

#: How a confidence tier is coloured. `possible` is deliberately the same
#: colour as a warning: it is the tier most likely to be wrong, and the report
#: should not let it pass as a conclusion.
_TIER_COLOUR = {"certain": "green", "likely": "cyan", "possible": "yellow"}


def supports_colour(stream=None) -> bool:
    """Whether to emit ANSI at all."""
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def supports_unicode(stream=None) -> bool:
    """Whether this stream can actually encode the drawing characters.

    Asked of the stream rather than assumed from the platform, because the
    same Windows machine answers differently depending on the code page, and
    the failure is silent: `print` substitutes `?` and the report still looks
    like it worked.
    """
    stream = stream or sys.stdout
    encoding = getattr(stream, "encoding", None) or ""
    try:
        "".join(_GLYPHS[True].values()).encode(encoding)
    except (LookupError, UnicodeEncodeError, TypeError):
        return False
    return True


class _Ink:
    """Colour and drawing characters, decided once."""

    def __init__(self, enabled: bool, unicode_ok: bool = True):
        self.enabled = enabled
        self.glyph = _GLYPHS[bool(unicode_ok)]

    def __call__(self, text: str, *names: str) -> str:
        if not self.enabled or not names:
            return text
        return "".join(_ANSI[n] for n in names) + text + _ANSI["reset"]


def _bar(share: float, ink: _Ink, colour: str = "cyan") -> str:
    filled = int(round(share * BAR_WIDTH))
    return ink(ink.glyph["fill"] * filled, colour) + ink(
        ink.glyph["empty"] * (BAR_WIDTH - filled), "dim"
    )


#: Words whose plural is not the word plus "s". Short on purpose -- it exists
#: because the report cheerfully printed "16 binarys".
_PLURALS = {"binary": "binaries", "directory": "directories", "entry": "entries"}


def _plural(count: int, word: str) -> str:
    if count == 1:
        return f"{count} {word}"
    return f"{count} {_PLURALS.get(word, word + 's')}"


def _header(walk: WalkResult, ink: _Ink, accurate=None) -> list[str]:
    if accurate is not None:
        # Both numbers, always. The estimate keeps its band even beside an
        # exact figure -- the pair is what lets a reader check the estimator
        # instead of taking it on faith.
        drift = (
            abs(accurate.tokens - walk.tokens) / accurate.tokens
            if accurate.tokens
            else 0.0
        )
        inside = "within" if drift <= ERROR_BOUND else "OUTSIDE"
        lines = [
            "",
            ink("contextcost", "bold") + ink(f"  {walk.root}", "dim"),
            "",
            "  "
            + ink(f"{walk.tokens:,} tokens", "bold")
            + " to read this repository"
            + ink(
                f"   {ink.glyph['plusminus']}{ERROR_BOUND:.0%} estimated",
                "dim",
            ),
            "  "
            + ink(f"{accurate.tokens:,} tokens", "bold", "green")
            + " exact ("
            + f"{accurate.encoding}"
            + ink(
                f"; estimate {drift:.1%} {inside} its "
                f"{ink.glyph['plusminus']}{ERROR_BOUND:.0%} band)",
                "dim",
            ),
        ]
    else:
        lines = [
            "",
            ink("contextcost", "bold") + ink(f"  {walk.root}", "dim"),
            "",
            "  "
            + ink(f"{walk.tokens:,} tokens", "bold")
            + " to read this repository"
            + ink(
                f"   {ink.glyph['plusminus']}{ERROR_BOUND:.0%} estimated, no tokenizer",
                "dim",
            ),
        ]
    counts = [
        _plural(len(walk.text_files), "text file"),
        f"{_plural(len(walk.binary_files), 'binary')} not counted",
        f"{_plural(walk.ignored_count, 'path')} ignored",
    ]
    lines.append(ink("  " + f" {ink.glyph['dot']} ".join(counts), "dim"))
    if walk.consumer != "generic":
        inputs = ", ".join(walk.ignore_files) or "none found"
        lines.append(
            ink(
                f"  consumer: {walk.consumer} {ink.glyph['dot']} inputs: {inputs}",
                "dim",
            )
        )
    if walk.skipped:
        lines.append(
            ink(
                f"  {_plural(len(walk.skipped), 'file')} unreadable, listed below",
                "yellow",
            )
        )
    return lines


def _section(title: str, ink: _Ink) -> list[str]:
    return ["", ink(title, "bold")]


def _breakdown(walk: WalkResult, ink: _Ink, depth: int = 1) -> list[str]:
    totals = walk.by_directory(depth=depth)
    if not totals:
        return []
    lines = _section("WHERE IT GOES", ink)
    biggest = max(totals.values())
    for name, tokens in list(totals.items())[:8]:
        share = tokens / walk.tokens if walk.tokens else 0.0
        lines.append(
            f"  {name[:22]:<22} {tokens:>9,}  "
            f"{_bar(tokens / biggest, ink)} {share:>4.0%}"
        )
    return lines


def _largest(walk: WalkResult, ink: _Ink, top: int, accurate=None) -> list[str]:
    files = walk.largest(top)
    if not files:
        return []
    lines = _section("LARGEST FILES", ink)
    if accurate is not None:
        exact_by_path = {f.path: f for f in accurate.files}
        lines.append(ink("       estimate      exact", "dim"))
        for cost in files:
            note = ink("  sampled", "dim") if cost.sampled else ""
            exact = exact_by_path.get(cost.path)
            shown = f"{exact.tokens:,}" if exact else _ACCURATE_UNAVAILABLE
            lines.append(f"  {cost.tokens:>9,}  {shown:>9}  {cost.path[:48]}{note}")
        return lines
    for cost in files:
        note = ink("  sampled", "dim") if cost.sampled else ""
        lines.append(f"  {cost.tokens:>9,}  {cost.path[:56]}{note}")
    return lines


def _findings(reduction: Reduction, ink: _Ink, top: int) -> list[str]:
    if not reduction.findings:
        return []
    lines = _section("CANDIDATE CONTEXT WASTE", ink)
    for name, group in by_rule(reduction.findings).items():
        rule = group[0].rule
        total = sum(f.tokens for f in group)
        lines.append(
            "  "
            + ink(f"{rule.confidence:<9}", _TIER_COLOUR[rule.confidence])
            + ink(f"{name:<14}", "bold")
            + f"{total:>9,}  {_plural(len(group), 'file')}"
        )
        for finding in group[:top]:
            lines.append(f"      {finding.tokens:>9,}  {finding.path[:50]}")
            lines.append(ink(f"                 {finding.evidence[:66]}", "dim"))
        if len(group) > top:
            lines.append(
                ink(
                    f"                 {ink.glyph['ellipsis']} and "
                    f"{len(group) - top} more",
                    "dim",
                )
            )
    return lines


def _deferred(reduction: Reduction, ink: _Ink) -> list[str]:
    """The tier the tool will not decide. Phrased as a question, on purpose."""
    if not reduction.deferred:
        return []
    lines = _section("YOUR DECISION — not excluded automatically", ink)
    for name, group in by_rule(reduction.deferred).items():
        rule = group[0].rule
        total = sum(f.tokens for f in group)
        lines.append(
            "  "
            + ink(f"{name:<14}", "yellow")
            + f"{total:>9,}  {_plural(len(group), 'file')}"
        )
        for finding in group[:5]:
            lines.append(f"      {finding.tokens:>9,}  {finding.path[:50]}")
        # The rationale, wrapped by hand rather than by textwrap so the
        # indentation lines up with the rows above it.
        words, line = rule.rationale.split(), "     "
        for word in words:
            if len(line) + len(word) > 74:
                lines.append(ink(line, "dim"))
                line = "     "
            line += " " + word
        lines.append(ink(line, "dim"))
        lines.append(
            ink("      Re-run with --include-possible to act on these.", "dim")
        )
    return lines


def _saving(reduction: Reduction, ink: _Ink, accurate=None) -> list[str]:
    lines = _section("SAVING", ink)
    if not reduction.patterns:
        lines.append(
            ink("  Nothing proposed. No rule found actionable context waste.", "dim")
        )
        if reduction.deferred:
            lines.append(
                ink(
                    "  The section above is the only candidate, "
                    "and it is yours to judge.",
                    "dim",
                )
            )
        return lines

    lines.append(
        "  "
        + f"{reduction.before:,}"
        + ink(f" {ink.glyph['arrow']} ", "dim")
        + ink(f"{reduction.after:,} tokens", "bold", "green")
        + f"   {reduction.share:.0%} saved"
    )
    # The distinction the whole tool rests on, stated where the number is.
    lines.append(
        ink(
            "  Measured by walking the repository again with the proposal applied,",
            "dim",
        )
    )
    lines.append(ink("  not by subtracting what was dropped.", "dim"))
    if accurate is not None:
        lines.append(
            ink(
                f"  Token figures are estimates ({accurate.encoding} exact total: "
                f"{accurate.tokens:,}); the saving is a difference of two walks,",
                "dim",
            )
        )
        lines.append(ink("  so it is exact in files even where counts are not.", "dim"))

    if reduction.narrowed_from:
        lines.append("")
        lines.append("  " + ink("One proposal was narrowed.", "yellow"))
        lines.append(
            ink(
                f"  {', '.join(reduction.narrowed_from[:4])} would have removed"
                " files that were",
                "dim",
            )
        )
        lines.append(ink("  never proposed, so exact paths are used instead.", "dim"))

    lines.append("")
    flag = (
        "--write-gitignore"
        if reduction.ignore_file == ".gitignore"
        else "--write-ignore"
    )
    lines.append(ink(f"  Add to {reduction.ignore_file} (or run with {flag}):", "dim"))
    for pattern in reduction.patterns[:12]:
        lines.append("    " + ink(pattern, "cyan"))
    if len(reduction.patterns) > 12:
        lines.append(
            ink(
                f"    {ink.glyph['ellipsis']} and {len(reduction.patterns) - 12} more",
                "dim",
            )
        )
    return lines


def _unreadable(walk: WalkResult, ink: _Ink) -> list[str]:
    if not walk.skipped:
        return []
    lines = _section("COULD NOT READ", ink)
    for path, reason in walk.skipped[:10]:
        lines.append(f"  {path[:46]}  " + ink(reason[:28], "dim"))
    lines.append(ink("  Counted as nothing, which understates the total.", "dim"))
    return lines


def render(
    walk: WalkResult,
    reduction: Reduction,
    *,
    colour: bool = True,
    top: int = 5,
    unicode_ok: bool = True,
    accurate=None,
) -> str:
    """The whole report, as one string.

    ``accurate`` is an :class:`contextcost.accurate.AccurateResult` when exact
    counts were asked for; the report then shows both numbers everywhere a
    total appears, and never the exact one alone.
    """
    ink = _Ink(colour, unicode_ok)
    lines: list[str] = []
    lines += _header(walk, ink, accurate)
    lines += _breakdown(walk, ink)
    lines += _largest(walk, ink, top, accurate)
    lines += _findings(reduction, ink, top)
    lines += _deferred(reduction, ink)
    lines += _saving(reduction, ink, accurate)
    lines += _unreadable(walk, ink)
    lines.append("")
    return "\n".join(lines)
