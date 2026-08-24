"""The same report, in the one format a PR comment or README can hold.

A pull request has no ANSI colours, no box-drawing characters and no bar
chart -- paste the terminal report into one and it arrives as escape codes,
``?`` glyphs and misaligned columns. The consumers that matter most for this
tool's distribution are exactly those places: a GitHub Action comment under
the PR ("this adds 41,882 tokens, 92% of it a lockfile") and a badge in a
README. So there is a second renderer, and it writes GitHub-flavoured
Markdown: tables render as tables, the saving is a blockquote because that is
what survives a comment collapse, and every number keeps the honesty rules of
the terminal report.

Those rules are shared, not re-derived:

* the estimate is always printed with its error bound;
* ``measured`` and ``estimated`` are never mixed -- the saving is a difference
  of two walks and the text says so;
* the tier the tool will not judge appears as an open question, not an
  exclusion.

The badge line is generated too, because hand-maintained badge URLs drift.
It points at shields.io with a static value -- no external service reads the
repository -- which means it states what the last run *here* measured, and
the user refreshes it by running the command again.
"""

from __future__ import annotations

from .classify import by_rule
from .estimate import ERROR_BOUND
from .reduce import Reduction
from .walk import WalkResult

__all__ = ["render_markdown"]


def _esc(text: str) -> str:
    """Escape the two characters a pipe table cannot carry literally."""
    return text.replace("|", "\\|").replace("\n", " ")


def _fmt(n: int) -> str:
    return f"{n:,}"


def _badge(walk: WalkResult) -> str:
    """One shields.io badge URL for a README, with today's numbers baked in."""
    label = "context cost"
    message = f"{_fmt(walk.tokens)} tokens"
    if walk.tokens > 500_000:
        colour = "red"
    elif walk.tokens > 100_000:
        colour = "orange"
    else:
        colour = "green"
    return (
        f"![{label}](https://img.shields.io/badge/"
        f"{label.replace(' ', '_')}-{message.replace(' ', '%20')}-{colour})"
    )


def _header(walk: WalkResult, accurate=None) -> list[str]:
    lines = [f"# contextcost — `{_esc(walk.root)}`", ""]
    if accurate is not None:
        drift = (
            abs(accurate.tokens - walk.tokens) / accurate.tokens
            if accurate.tokens
            else 0.0
        )
        inside = "within" if drift <= ERROR_BOUND else "**OUTSIDE**"
        exact = (
            f"**{_fmt(accurate.tokens)} tokens** exact ({accurate.encoding})"
            " to read this repository;"
            f" the tokenizer-free estimate says {_fmt(walk.tokens)}"
            f" (±{ERROR_BOUND:.0%}, {drift:.1%} {inside} its band)."
        )
        lines += [exact, ""]
    else:
        lines += [
            (
                f"**≈ {_fmt(walk.tokens)} tokens** to read this repository "
                f"(estimated, ±{ERROR_BOUND:.0%}, no tokenizer)."
            ),
            "",
        ]
    counts = ", ".join(
        [
            f"{len(walk.text_files)} text files",
            f"{len(walk.binary_files)} binaries not counted",
            f"{walk.ignored_count} paths ignored",
        ]
    )
    lines.append(f"{counts}.")
    lines.append("")
    return lines


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _breakdown(walk: WalkResult) -> list[str]:
    totals = walk.by_directory()
    if not totals:
        return []
    rows = []
    for name, tokens in list(totals.items())[:8]:
        share = tokens / walk.tokens if walk.tokens else 0.0
        rows.append([f"`{_esc(name)}`", _fmt(tokens), f"{share:.0%}"])
    return ["## Where it goes", ""] + _table(
        ["directory", "tokens", "share"], rows
    ) + [""]


def _largest(walk: WalkResult, top: int, accurate=None) -> list[str]:
    files = walk.largest(top)
    if not files:
        return []
    exact_by_path = {}
    if accurate is not None:
        exact_by_path = {f.path: f for f in accurate.files}
    rows = []
    for cost in files:
        row = [_esc(cost.path), _fmt(cost.tokens)]
        if accurate is not None:
            exact = exact_by_path.get(cost.path)
            shown = _fmt(exact.tokens) if exact else "unavailable"
            note = " *(sampled)*" if cost.sampled else ""
            row.append(shown + note)
        rows.append(row)
    headers = ["file", "tokens"]
    if accurate is not None:
        headers.append("exact")
    return ["## Largest files", ""] + _table(headers, rows) + [""]


def _findings(reduction: Reduction, top: int) -> list[str]:
    if not reduction.findings:
        return []
    lines = ["## Candidate context waste", ""]
    rows = []
    for name, group in by_rule(reduction.findings).items():
        rule = group[0].rule
        total = sum(f.tokens for f in group)
        rows.append(
            [
                rule.confidence,
                f"**{name}**",
                _fmt(total),
                str(len(group)),
            ]
        )
    lines += _table(
        ["confidence", "rule", "tokens", "files"], rows
    ) + [""]
    # The per-file detail stays below the table so a collapsed PR comment
    # still shows the totals before the evidence gets long.
    for name, group in by_rule(reduction.findings).items():
        lines.append(f"* **{name}** ({rule_named_confidence(group)}):")
        for finding in group[:top]:
            lines.append(
                f"  * `{_esc(finding.path)}` — {_fmt(finding.tokens)} tokens"
                f" — {finding.evidence}"
            )
        if len(group) > top:
            lines.append(f"  * …and {len(group) - top} more")
    lines.append("")
    return lines


def rule_named_confidence(group) -> str:
    """Confidence word of a finding group, kept out of the f-string above."""
    return group[0].rule.confidence


def _deferred(reduction: Reduction) -> list[str]:
    if not reduction.deferred:
        return []
    lines = ["## Your decision — not excluded automatically", ""]
    groups = by_rule(reduction.deferred)
    rows = []
    for name, group in groups.items():
        total = sum(f.tokens for f in group)
        rows.append([name, _fmt(total), str(len(group))])
    lines += _table(["rule", "tokens", "files"], rows)
    first_group = next(iter(groups.values()))
    lines.append("")
    lines.append(f"> {first_group[0].rule.rationale}")
    lines.append("")
    lines.append("Re-run with `--include-possible` to act on these.")
    lines.append("")
    return lines


def _saving(reduction: Reduction, accurate=None) -> list[str]:
    lines = ["## Saving", ""]
    if not reduction.patterns:
        lines += [
            "Nothing proposed: no rule found actionable context waste.",
            "",
        ]
        if reduction.deferred:
            lines += [
                "The section above is the only candidate, and it is yours to judge.",
                "",
            ]
        return lines

    lines.append(
        f"> **{_fmt(reduction.before)} → {_fmt(reduction.after)} tokens** "
        f"— {reduction.share:.0%} saved."
    )
    lines.append("")
    lines.append(
        "Measured by walking the repository again with the proposal applied, "
        "not by subtracting what was dropped."
    )
    if reduction.narrowed_from:
        lines.append("")
        lines.append(
            "One proposal was narrowed: "
            + ", ".join(f"`{_esc(p)}`" for p in reduction.narrowed_from[:4])
            + " would have removed files that were never proposed, so exact"
            " paths are used instead."
        )
    lines.append("")
    flag = {
        ".gitignore": "--write-gitignore",
        ".contextcostignore": "--emit-ignore",
    }.get(reduction.ignore_file, "--write-ignore")
    lines.append(f"Add to `{reduction.ignore_file}` (or run with `{flag}`):")
    lines.append("")
    lines.append("```gitignore")
    for pattern in reduction.patterns[:12]:
        lines.append(pattern)
    if len(reduction.patterns) > 12:
        lines.append(f"# …and {len(reduction.patterns) - 12} more")
    lines.append("```")
    if accurate is not None:
        lines.append("")
        lines.append(
            f"Token figures are estimates ({accurate.encoding} exact total: "
            f"{_fmt(accurate.tokens)}); the saving is a difference of two walks,"
            " so it is exact in files even where counts are not."
        )
    lines.append("")
    return lines


def render_markdown(
    walk: WalkResult,
    reduction: Reduction,
    *,
    top: int = 5,
    accurate=None,
    badge: bool = False,
) -> str:
    """The whole report as GitHub-flavoured Markdown.

    ``badge=True`` prepends a ready-to-paste shields.io badge line for a
    README. It is off by default because a PR comment carrying a badge image
    is noise; a README without one wastes the measurement.
    """
    lines: list[str] = []
    if badge:
        lines.append(_badge(walk))
        lines.append("")
    lines += _header(walk, accurate)
    lines += _breakdown(walk)
    lines += _largest(walk, top, accurate)
    lines += _findings(reduction, top)
    lines += _deferred(reduction)
    lines += _saving(reduction, accurate)
    return "\n".join(lines).rstrip() + "\n"
