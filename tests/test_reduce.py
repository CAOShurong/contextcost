"""Tests for the measured reduction.

The claim this module makes is narrow and unusually checkable: the reported
saving is the difference between two walks of the repository, not a sum of the
things the tool decided to drop. So the tests check that difference directly,
and they check the case the whole design exists for -- a proposed pattern that
removes more than it was written for.

That case is not hypothetical. `propose_patterns` suggests a whole directory
when every text file it can see there is waste, and "every text file it can
see" is not the same as "everything in there": a binary sitting alongside, or a
subdirectory of perfectly good source, both get swept up. Rather than making
the proposal logic clever enough to never be wrong, the reduction walks the
repository again and compares what vanished against what was named. Those two
sets must be equal, and when they are not the patterns are narrowed to exact
paths and the report says so.
"""

from contextcost.classify import classify
from contextcost.reduce import propose_patterns, reduce_repository
from contextcost.walk import walk_repository

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
    return str(root)


def test_the_saving_is_the_difference_between_two_walks(tmp_path):
    """Not a sum of what was dropped. The two numbers agree here because
    nothing over-reached -- which is exactly what makes disagreement useful
    information elsewhere."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    result = reduce_repository(root)

    after = walk_repository(root, extra_ignore=result.patterns)
    assert result.after == after.tokens
    assert result.saved == result.before - after.tokens
    assert result.saved == sum(c.tokens for c in result.excluded)


def test_an_overreaching_directory_pattern_is_caught_and_narrowed(tmp_path):
    """`docs/` contains one minified file and, below it, a guide worth
    reading. Proposing the directory would take both. The second walk shows a
    file disappearing that nobody proposed, so the patterns fall back to exact
    paths and the narrowing is recorded rather than hidden.
    """
    root = build(
        tmp_path,
        {
            "docs/app.min.js": FILLER,
            "docs/guide/writing.md": FILLER,
        },
    )
    before = walk_repository(root)
    proposed = propose_patterns(before, classify(before))
    assert "/docs/" in proposed, (
        "the naive proposal really does take the whole directory"
    )

    result = reduce_repository(root)
    assert result.narrowed_from == proposed
    assert result.patterns == ["/docs/app.min.js"]
    assert [c.path for c in result.excluded] == ["docs/app.min.js"]

    survivors = {
        c.path for c in walk_repository(root, extra_ignore=result.patterns).text_files
    }
    assert "docs/guide/writing.md" in survivors


def test_a_binary_beside_the_waste_also_triggers_narrowing(tmp_path):
    """The directory grouping only sees text files, so a PNG next to a
    minified bundle is invisible to the proposal and would be swept up by it.
    It costs no tokens, which is precisely why subtracting estimates would
    never have noticed."""
    root = build(
        tmp_path,
        {
            "assets/app.min.js": FILLER,
            "assets/logo.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 400,
        },
    )
    result = reduce_repository(root)
    assert result.narrowed_from, "excluding the directory would have taken the PNG too"
    assert result.patterns == ["/assets/app.min.js"]
    assert [c.path for c in result.excluded] == ["assets/app.min.js"]


def test_a_directory_of_pure_waste_is_proposed_whole(tmp_path):
    """Narrowing is a correction, not the normal path. When the directory
    really does contain nothing else, one pattern is the better answer: it
    reads better and it keeps covering the directory as it grows."""
    root = build(
        tmp_path,
        {
            "vendor/one.py": SOURCE,
            "vendor/two.py": SOURCE,
            "vendor/deep/three.py": SOURCE,
            "src/app.py": SOURCE,
        },
    )
    result = reduce_repository(root)
    assert result.patterns == ["/vendor/"]
    assert not result.narrowed_from
    assert {c.path for c in result.excluded} == {
        "vendor/one.py",
        "vendor/two.py",
        "vendor/deep/three.py",
    }


def test_possible_findings_are_deferred_rather_than_decided(tmp_path):
    """The tier the file system cannot judge. Excluding it by default is the
    one thing this tool must not do."""
    rows = "".join(f"{n},alpha,beta,gamma,delta,epsilon\n" for n in range(1500))
    root = build(tmp_path, {"data/rows.csv": rows, "src/app.py": SOURCE})

    default = reduce_repository(root)
    assert default.saved == 0
    assert default.patterns == []
    assert [f.rule.name for f in default.deferred] == ["large-data"]
    assert default.deferred_tokens > 0

    opted_in = reduce_repository(root, include_possible=True)
    assert opted_in.saved > 0
    assert opted_in.deferred == []
    # `data/` holds nothing but the CSV, so the directory is proposed whole --
    # the same rule as `vendor/`, applied to a file the user opted in to.
    assert opted_in.patterns == ["/data/"]
    assert [c.path for c in opted_in.excluded] == ["data/rows.csv"]


def test_patterns_are_anchored_so_they_cannot_match_at_another_depth(tmp_path):
    """`yarn.lock` unanchored matches at every depth. The leading slash is the
    difference between proposing one file and proposing a class of files."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    result = reduce_repository(root)
    assert result.patterns == ["/yarn.lock"]
    assert all(p.startswith("/") for p in result.patterns)


def test_a_clean_repository_proposes_nothing_and_says_it_saved_nothing(tmp_path):
    root = build(tmp_path, {"src/app.py": SOURCE, "README.md": FILLER})
    result = reduce_repository(root)
    assert result.patterns == []
    assert result.saved == 0
    assert result.share == 0.0
    assert result.gitignore_block() == ""


def test_the_gitignore_block_carries_the_measured_number(tmp_path):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    result = reduce_repository(root)
    block = result.gitignore_block()
    assert "/yarn.lock" in block
    assert "Measured saving" in block
    assert f"{result.saved:,}" in block


def test_already_ignored_files_are_not_counted_as_a_saving(tmp_path):
    """They were never in the budget, so removing them saves nothing. A tool
    that counted `.gitignore`d files would report enormous savings on every
    repository and mean nothing by any of them."""
    root = build(
        tmp_path,
        {
            ".gitignore": "ignored/\n",
            "ignored/yarn.lock": FILLER,
            "src/app.py": SOURCE,
        },
    )
    result = reduce_repository(root)
    assert result.saved == 0
    assert result.findings == []
