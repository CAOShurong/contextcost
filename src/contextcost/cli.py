"""The command line.

Two decisions worth stating, because both are about what the tool refuses to
do.

**It never writes to the repository unless asked in so many words.** The
default output is a proposal you can read and disagree with. ``--write-gitignore``
appends it, prints exactly what it appended, and skips any pattern the file
already carries. A tool that quietly edited `.gitignore` on a repository
somebody was about to commit would deserve everything that followed.

**The exit code answers a question worth scripting against.** ``0`` when
nothing confidently wasteful was found, ``1`` when something was. That makes
``contextcost --quiet`` usable as a CI check for "did somebody commit a
lockfile into the context budget", which is the only automated use of this that
seems genuinely worth having.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .estimate import ERROR_BOUND
from .reduce import reduce_repository
from .report import render, supports_colour, supports_unicode
from .walk import walk_repository

__all__ = ["main"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextcost",
        description=(
            "Measure what a repository costs an AI coding agent to read, find "
            "what is wasting that budget, and prove the saving by measuring it "
            "again."
        ),
        epilog=(
            f"Token counts are estimates with a measured error bound of "
            f"±{ERROR_BOUND:.0%}; savings are measured by walking the "
            f"repository a second time."
        ),
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="repository to measure (default: .)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--include-possible",
        action="store_true",
        help=(
            "also act on findings the file system cannot judge, "
            "such as large data files"
        ),
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help=(
            "count files git would ignore "
            "(usually makes every repository look identical)"
        ),
    )
    parser.add_argument(
        "--write-gitignore",
        action="store_true",
        help="append the proposed patterns to .gitignore",
    )
    parser.add_argument(
        "--top", type=int, default=5, help="rows per section (default: 5)"
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    parser.add_argument(
        "--quiet", action="store_true", help="print nothing; use the exit code"
    )
    parser.add_argument(
        "--version", action="version", version=f"contextcost {__version__}"
    )
    return parser


def _write_gitignore(root: str, reduction) -> str:
    """Append whatever is not already there, and say what happened.

    Deduplicating per pattern rather than refusing when a contextcost block
    exists. Refusing was the first version, and it meant that a lockfile
    committed a month after the first run could never be added: the file
    already carried a block, so the tool declined and said so as if that were
    helpful. The reachable path for this is ``--no-gitignore``, where the walk
    sees files that are already ignored and can propose patterns that are
    already written down.
    """
    path = os.path.join(root, ".gitignore")
    existing = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            existing = handle.read()

    present = {line.strip() for line in existing.splitlines() if line.strip()}
    fresh = [pattern for pattern in reduction.patterns if pattern not in present]
    if not fresh:
        return "Left .gitignore alone: every proposed pattern is already in it."

    block = reduction.gitignore_block(fresh)
    separator = (
        ""
        if not existing or existing.endswith("\n\n")
        else ("\n" if existing.endswith("\n") else "\n\n")
    )
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(separator + block)
    return f"Appended {len(fresh)} pattern(s) to {path}"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"contextcost: not a directory: {args.path}", file=sys.stderr)
        return 2

    use_gitignore = not args.no_gitignore
    walk = walk_repository(root, use_gitignore=use_gitignore)
    reduction = reduce_repository(
        root, use_gitignore=use_gitignore, include_possible=args.include_possible
    )

    if args.json:
        payload = {
            "version": __version__,
            "walk": walk.as_dict(),
            "error_bound": ERROR_BOUND,
            "by_directory": walk.by_directory(),
            "by_extension": walk.by_extension(),
            "largest": [c.as_dict() for c in walk.largest(args.top)],
            "reduction": reduction.as_dict(),
        }
        print(json.dumps(payload, indent=2))
    elif not args.quiet:
        colour = supports_colour() and not args.no_color
        print(
            render(
                walk,
                reduction,
                colour=colour,
                top=args.top,
                unicode_ok=supports_unicode(),
            )
        )

    if args.write_gitignore:
        message = (
            _write_gitignore(root, reduction)
            if reduction.patterns
            else "Nothing to write: no patterns proposed."
        )
        if not args.quiet:
            print(message)

    return 1 if reduction.patterns else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
