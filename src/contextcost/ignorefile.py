"""Reading consumer ignore files, because getting them wrong changes every number.

This tool's whole output is "here is what this consumer may spend on the
repository". If it walks files that consumer excludes, the number is wrong in
the direction that matters most -- `.venv/` and `node_modules/` are enormous,
and counting them would make every repository look identically bloated and the
tool useless. If it misses a consumer-native ignore file, a proposal can also
be written to the wrong place and produce no saving in the real tool.

So the matching has to be real, not a substring check. The rules that actually
bite, in the order people trip over them:

* A pattern with no ``/`` matches at **any depth**. ``*.log`` matches
  ``a/b/c.log``. A pattern with an interior ``/`` is anchored to the file the
  ignore file sits in, so ``docs/*.png`` does not match ``a/docs/x.png``.
* A trailing ``/`` matches directories only.
* A leading ``!`` re-includes something an earlier pattern excluded, and the
  **last matching pattern wins**, so order is significant and a first-match
  loop gives the wrong answer.
* ``**`` spans directory separators; a single ``*`` does not.
* A directory that is excluded is not descended into at all, which is what
  makes the walk fast -- and it also means a negation cannot rescue a file
  inside an excluded directory. Git behaves this way and so does this.

There is no attempt to reproduce every product's retrieval, built-in defaults,
tokenizer or per-request behaviour. The profiles model documented ignore-file
inputs only. Where behaviour is knowingly narrower it is written down, because
a silent difference would show up as a number nobody could explain.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

__all__ = [
    "CONSUMERS",
    "CONTEXTCOST_IGNORE_FILE",
    "IgnoreRules",
    "Pattern",
    "active_ignore_files",
    "consumer_write_file",
    "load_ignore_rules",
    "parse_ignore",
]


#: Documented root-level ignore inputs for the consumers ContextCost can model.
#: Every profile still uses nested ``.gitignore`` files unless the caller asks
#: for ``use_gitignore=False``. These are file-selection profiles, not claims
#: about a product's tokenizer, retrieval, compression, or per-request billing.
_CONSUMER_IGNORE_FILES = {
    "generic": (),
    "cursor": (".cursorignore",),
    "aider": (".aiderignore",),
    "repomix": (".ignore", ".repomixignore", ".git/info/exclude"),
}

#: Where a verified proposal should be written for each consumer. Writing to
#: the consumer-native file matters: Git's own documentation is explicit that
#: adding an already tracked path to ``.gitignore`` does not stop tracking it.
_CONSUMER_WRITE_FILES = {
    "generic": ".gitignore",
    "cursor": ".cursorignore",
    "aider": ".aiderignore",
    "repomix": ".repomixignore",
}

#: This tool's own project-local ignore file, read for every consumer and even
#: under ``use_gitignore=False``. It exists because the right exclusion for an
#: AI context budget is often the wrong exclusion everywhere else: a large
#: recorded fixture belongs in front of an agent and out of no one's VCS, and
#: pushing contextcost's proposal into ``.gitignore`` would change what Git
#: tracks to get a smaller token count. Keeping the decision in a file only
#: this tool reads means accepting a saving cannot leak side effects.
#:
#: It is applied **last**, so its patterns win over every consumer input --
#: including a ``!`` re-inclusion, which lets a repository say "the generic
#: rules hide ``fixtures/``, but agents still need it" in one line. That
#: ordering is the merge semantics: git's last-matching-pattern-wins over a
#: concatenated list whose tail is this file.
CONTEXTCOST_IGNORE_FILE = ".contextcostignore"

CONSUMERS = tuple(_CONSUMER_IGNORE_FILES)


def _consumer_files(consumer: str) -> tuple[str, ...]:
    try:
        return _CONSUMER_IGNORE_FILES[consumer]
    except KeyError as exc:  # pragma: no cover - argparse rejects this for the CLI
        choices = ", ".join(CONSUMERS)
        raise ValueError(
            f"unknown consumer {consumer!r}; choose from {choices}"
        ) from exc


def consumer_write_file(consumer: str) -> str:
    """Return the consumer-native file that should receive proposals."""
    _consumer_files(consumer)
    return _CONSUMER_WRITE_FILES[consumer]


def active_ignore_files(
    root: str,
    *,
    use_gitignore: bool = True,
    consumer: str = "generic",
) -> list[str]:
    """List existing root-level ignore inputs in their application order.

    ``.contextcostignore``, when present, is always last so its patterns win.
    """
    consumer_files = tuple(
        relative
        for relative in _consumer_files(consumer)
        if use_gitignore or relative != ".git/info/exclude"
    )
    candidates = (
        (".gitignore",) if use_gitignore else ()
    ) + consumer_files + (
        CONTEXTCOST_IGNORE_FILE,  # applied last, wins over everything above
    )
    active = []
    for relative in candidates:
        if relative not in active and os.path.isfile(os.path.join(root, relative)):
            active.append(relative)
    return active


@dataclass(frozen=True)
class Pattern:
    """One line of an ignore file, compiled."""

    source: str
    regex: re.Pattern[str]
    negated: bool
    directory_only: bool
    #: The same pattern without the "or anything beneath it" tail. Needed only
    #: for directory-only patterns, to tell "this *is* the directory" from
    #: "this is a file inside it".
    exact: re.Pattern[str] | None = None

    def matches(self, relative: str, is_dir: bool) -> bool:
        if self.regex.match(relative) is None:
            return False
        if not self.directory_only or is_dir:
            return True
        # `build/` names a directory, so it cannot match a *file* called
        # `build` -- but everything beneath `build/` is still excluded. The
        # walker normally prunes the directory before asking, so this only
        # matters when a path is queried on its own; getting it wrong there
        # would make the same path answer differently depending on how it was
        # reached.
        return self.exact is None or self.exact.match(relative) is None


def _translate(pattern: str) -> str:
    """Turn one gitignore pattern into a regex over a ``/``-joined path.

    Written by hand rather than with :func:`fnmatch.translate` because fnmatch
    has no notion of a path separator: its ``*`` happily crosses ``/``, which
    would make ``docs/*.png`` match ``docs/a/b.png`` and quietly over-exclude.
    """
    out: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        char = pattern[i]
        if char == "*":
            if pattern.startswith("**", i):
                # `**/` may match nothing at all, which is why the trailing
                # separator is folded into the optional group.
                if pattern.startswith("**/", i):
                    out.append("(?:.*/)?")
                    i += 3
                    continue
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
            i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        elif char == "[":
            end = pattern.find("]", i + 1)
            if end == -1:
                out.append(re.escape(char))
                i += 1
                continue
            body = pattern[i + 1 : end]
            if body.startswith("!"):
                body = "^" + body[1:]
            out.append(f"[{body}]")
            i = end + 1
        else:
            out.append(re.escape(char))
            i += 1
    return "".join(out)


def _compile(line: str, prefix: str = "") -> Pattern | None:
    """Compile one line, or return ``None`` if it is a comment or blank.

    ``prefix`` is the directory the ignore file lives in, relative to the walk
    root, so a nested ``.gitignore`` anchors to itself rather than to the top.
    """
    raw = line
    if not line.strip() or line.lstrip().startswith("#"):
        return None

    negated = line.startswith("!")
    if negated:
        line = line[1:]

    # A trailing space is only significant when escaped -- git strips the rest.
    line = re.sub(r"(?<!\\)\s+$", "", line)
    line = line.replace("\\ ", " ")
    if not line:
        return None

    directory_only = line.endswith("/")
    if directory_only:
        line = line[:-1]

    anchored = line.startswith("/") or "/" in line.rstrip("/")
    line = line.lstrip("/")
    if not line:
        return None

    body = _translate(line)
    head = prefix if prefix.endswith("/") or not prefix else prefix + "/"
    if anchored:
        stem = f"{re.escape(head)}{body}"
    else:
        # Unanchored patterns match at any depth *below* the ignore file.
        stem = f"{re.escape(head)}(?:.*/)?{body}"

    return Pattern(
        source=raw.rstrip("\n"),
        regex=re.compile(f"{stem}(?:/.*)?$"),
        negated=negated,
        directory_only=directory_only,
        exact=re.compile(f"{stem}$") if directory_only else None,
    )


def parse_ignore(text: str, prefix: str = "") -> list[Pattern]:
    """Compile the lines of one ignore file, in order."""
    patterns = []
    for line in text.splitlines():
        compiled = _compile(line, prefix)
        if compiled is not None:
            patterns.append(compiled)
    return patterns


@dataclass
class IgnoreRules:
    """Every pattern in effect, in the order they were declared.

    Order is the whole point: git resolves a path by taking the **last**
    pattern that matches it, so that a later ``!keep-this`` can rescue a file
    an earlier ``*.log`` excluded. Evaluating first-match-wins is the single
    most common way to get this wrong, and it fails silently.
    """

    patterns: list[Pattern] = field(default_factory=list)

    def extend(self, more: list[Pattern]) -> IgnoreRules:
        return IgnoreRules(self.patterns + more)

    def ignored(self, relative: str, *, is_dir: bool = False) -> bool:
        relative = relative.replace(os.sep, "/")
        # gitignore(5): "It is not possible to re-include a file if a parent
        # directory of that file is excluded." Git never descends into an
        # excluded directory, so a later `!` inside one never gets a chance to
        # apply. The walker gets this right for free by pruning, but a caller
        # asking about a path directly has no traversal to rely on -- and the
        # same path answering differently depending on how it was reached is
        # the kind of inconsistency nobody would be able to debug from a
        # report. So the rule is enforced here, where it is stated.
        parts = relative.split("/")
        for depth in range(1, len(parts)):
            if self._decide("/".join(parts[:depth]), is_dir=True):
                return True
        return self._decide(relative, is_dir=is_dir)

    def _decide(self, relative: str, *, is_dir: bool) -> bool:
        """Last matching pattern wins, for this path alone."""
        decision = False
        for pattern in self.patterns:
            if pattern.matches(relative, is_dir):
                decision = not pattern.negated
        return decision

    def __len__(self) -> int:  # pragma: no cover - convenience
        return len(self.patterns)


#: Always skipped, whatever the ignore files say. `.git` is not interesting and
#: is frequently larger than the working tree; the rest are caches that no
#: agent should ever be asked to read and that are commonly *not* in
#: `.gitignore` because the tooling that creates them is not in use everywhere.
ALWAYS_SKIP = (
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
)


def load_ignore_rules(
    root: str, *, use_gitignore: bool = True, consumer: str = "generic"
) -> IgnoreRules:
    """The rules in force at the root of a repository.

    Only the top-level ignore file is read here; nested ones are picked up by
    the walker as it descends, because their patterns anchor to their own
    directory and cannot be flattened into a single list up front.
    """
    rules = IgnoreRules()
    for relative in active_ignore_files(
        root, use_gitignore=use_gitignore, consumer=consumer
    ):
        path = os.path.join(root, relative)
        with open(path, encoding="utf-8", errors="replace") as handle:
            rules = rules.extend(parse_ignore(handle.read()))
    return rules
