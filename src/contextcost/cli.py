"""The command line.

Two decisions worth stating, because both are about what the tool refuses to
do.

**It never writes to the repository unless asked in so many words.** The
default output is a proposal you can read and disagree with. ``--write-ignore``
appends it to the selected consumer's native ignore file, prints exactly what
it appended, and skips any pattern the file already carries.
``--write-gitignore`` remains an explicit compatibility option. A tool that
quietly edited an ignore file on a repository somebody was about to commit
would deserve everything that followed.

**The exit code answers a question worth scripting against.** ``0`` when no
actionable context-waste candidate was found, ``1`` when something was. That makes
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
from .ignorefile import CONSUMERS, CONTEXTCOST_IGNORE_FILE, consumer_write_file
from .json_schema import _contract_text, build_payload
from .reduce import reduce_repository
from .report import render, supports_colour, supports_unicode
from .walk import walk_repository

__all__ = ["main"]

#: Exit code for ``--accurate`` without the optional dependency. Distinct from
#: ``2`` (usage / IO errors) so a CI job can tell "this run could not be
#: exact" from "the repository was not measurable".
MISSING_DEPENDENCY_EXIT = 3


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
    parser.add_argument(
        "--json", action="store_true", help="machine-readable output (schema v1)"
    )
    parser.add_argument(
        "--json-schema",
        action="store_true",
        help=(
            "print the --json key contract and exit; consumers should pin"
            " 'schema' from the output and read this before relying on a key"
        ),
    )
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
        "--consumer",
        choices=CONSUMERS,
        default="generic",
        help=(
            "model the documented ignore inputs for generic, Cursor, Aider, "
            "or Repomix (default: generic)"
        ),
    )
    write = parser.add_mutually_exclusive_group()
    write.add_argument(
        "--write-ignore",
        action="store_true",
        help="append the verified proposal to the consumer-native ignore file",
    )
    write.add_argument(
        "--write-gitignore",
        action="store_true",
        help="append the verified proposal to .gitignore (backward-compatible)",
    )
    write.add_argument(
        "--emit-ignore",
        action="store_true",
        help=(
            "append the verified proposal to .contextcostignore, this tool's "
            "own project-local ignore file -- it changes only what contextcost "
            "measures, never what Git tracks or another tool reads"
        ),
    )
    parser.add_argument(
        "--accurate",
        action="store_true",
        help=(
            "exact counts via tiktoken (install with "
            "'pip install contextcost[accurate]'); the estimate stays shown"
        ),
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


def _write_ignore_file(root: str, relative: str, reduction) -> str:
    """Append whatever is not already there, and say what happened.

    Deduplicating per pattern rather than refusing when a contextcost block
    exists. Refusing was the first version, and it meant that a lockfile
    committed a month after the first run could never be added: the file
    already carried a block, so the tool declined and said so as if that were
    helpful. The reachable path for this is ``--no-gitignore``, where the walk
    sees files that are already ignored and can propose patterns that are
    already written down.
    """
    root = os.path.realpath(root)
    path = os.path.abspath(os.path.join(root, relative))
    if os.path.lexists(path) and os.path.islink(path):
        raise OSError(f"refusing to write symbolic link: {relative}")
    try:
        contained = os.path.commonpath((root, os.path.realpath(path))) == root
    except ValueError:
        contained = False
    if not contained:
        raise OSError(f"refusing to write outside the repository: {relative}")

    existing = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            existing = handle.read()

    present = {line.strip() for line in existing.splitlines() if line.strip()}
    fresh = [pattern for pattern in reduction.patterns if pattern not in present]
    if not fresh:
        return f"Left {relative} alone: every proposed pattern is already in it."

    block = reduction.gitignore_block(fresh)
    separator = (
        ""
        if not existing or existing.endswith("\n\n")
        else ("\n" if existing.endswith("\n") else "\n\n")
    )
    # Check again immediately before opening, then ask the OS not to follow a
    # link where that flag exists. The second check narrows the Windows race;
    # O_NOFOLLOW closes it on platforms that provide the flag.
    if os.path.lexists(path) and os.path.islink(path):
        raise OSError(f"refusing to write symbolic link: {relative}")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o666)
    with os.fdopen(descriptor, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(separator + block)
    return f"Appended {len(fresh)} pattern(s) to {path}"


def _write_gitignore(root: str, reduction) -> str:
    """Backward-compatible wrapper for callers of the v0.1 helper."""
    return _write_ignore_file(root, ".gitignore", reduction)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.json_schema:
        print(_contract_text())
        return 0
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"contextcost: not a directory: {args.path}", file=sys.stderr)
        return 2

    use_gitignore = not args.no_gitignore
    walk = walk_repository(root, use_gitignore=use_gitignore, consumer=args.consumer)
    reduction = reduce_repository(
        root,
        use_gitignore=use_gitignore,
        include_possible=args.include_possible,
        consumer=args.consumer,
    )
    if args.write_gitignore:
        # The legacy flag is an explicit destination override. Keep the
        # report and JSON aligned with the file that will actually be written.
        reduction.ignore_file = ".gitignore"
    elif args.emit_ignore:
        reduction.ignore_file = CONTEXTCOST_IGNORE_FILE
    elif args.write_ignore:
        reduction.ignore_file = consumer_write_file(args.consumer)

    accurate = None
    if args.accurate:
        try:
            from .accurate import count_repository

            accurate = count_repository(walk)
        except ImportError:
            print(
                "contextcost: --accurate needs the optional tokenizer.\n"
                "  install it with: pip install 'contextcost[accurate]'\n"
                "(the default estimate is unchanged and still shown without it)",
                file=sys.stderr,
            )
            return MISSING_DEPENDENCY_EXIT

    if args.json:
        payload = build_payload(
            version=__version__,
            consumer=args.consumer,
            reduction=reduction,
            walk=walk,
            error_bound=ERROR_BOUND,
            top=args.top,
            accurate=accurate,
        )
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
                accurate=accurate,
            )
        )

    if args.write_gitignore or args.write_ignore or args.emit_ignore:
        ignore_file = (
            ".gitignore"
            if args.write_gitignore
            else (
                CONTEXTCOST_IGNORE_FILE
                if args.emit_ignore
                else consumer_write_file(args.consumer)
            )
        )
        try:
            message = (
                _write_ignore_file(root, ignore_file, reduction)
                if reduction.patterns
                else "Nothing to write: no patterns proposed."
            )
        except OSError as exc:
            print(f"contextcost: could not write {ignore_file}: {exc}", file=sys.stderr)
            return 2
        if not args.quiet:
            print(message)

    return 1 if reduction.patterns else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
