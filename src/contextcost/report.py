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


def _header(walk: WalkResult, ink: _Ink) -> list[str]:
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


def _largest(walk: WalkResult, ink: _Ink, top: int) -> list[str]:
    files = walk.largest(top)
    if not files:
        return []
    lines = _section("LARGEST FILES", ink)
    for cost in files:
        note = ink("  sampled", "dim") if cost.sampled else ""
        lines.append(f"  {cost.tokens:>9,}  {cost.path[:56]}{note}")
    return lines


def _findings(reduction: Reduction, ink: _Ink, top: int) -> list[str]:
    if not reduction.findings:
        return []
    lines = _section("WHAT IS NOT WORTH READING", ink)
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


def _saving(reduction: Reduction, ink: _Ink) -> list[str]:
    lines = _section("SAVING", ink)
    if not reduction.patterns:
        lines.append(
            ink("  Nothing proposed. Nothing here is confidently waste.", "dim")
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
    lines.append(ink("  Add to .gitignore (or run with --write-gitignore):", "dim"))
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
) -> str:
    """The whole report, as one string."""
    ink = _Ink(colour, unicode_ok)
    lines: list[str] = []
    lines += _header(walk, ink)
    lines += _breakdown(walk, ink)
    lines += _largest(walk, ink, top)
    lines += _findings(reduction, ink, top)
    lines += _deferred(reduction, ink)
    lines += _saving(reduction, ink)
    lines += _unreadable(walk, ink)
    lines.append("")
    return "\n".join(lines)
