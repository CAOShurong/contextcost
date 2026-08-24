"""Direct tests of gitignore-pattern parsing and matching.

These pin the specific cases gitignore(5) documents and a naive
fnmatch-per-line translation gets wrong: unanchored-vs-anchored patterns,
directory-only trailing slashes, ``!`` negation and its precedence, and
``**`` crossing directory separators. Each case is small enough to verify by
hand against the spec, which is the point -- these are not asserting what the
code happens to do, they are asserting what git itself does.
"""

from __future__ import annotations

from contextcost.ignorefile import (
    ALWAYS_SKIP,
    CONTEXTCOST_IGNORE_FILE,
    IgnoreRules,
    active_ignore_files,
    load_ignore_rules,
    parse_ignore,
)


def rules(text: str, prefix: str = "") -> IgnoreRules:
    return IgnoreRules(parse_ignore(text, prefix))


# -- unanchored vs anchored patterns -----------------------------------------


def test_a_pattern_with_no_slash_matches_at_any_depth():
    r = rules("*.log\n")
    assert r.ignored("a.log")
    assert r.ignored("a/b/c.log")
    assert not r.ignored("a.log.txt")


def test_an_interior_slash_anchors_to_the_ignore_files_directory():
    r = rules("docs/*.png\n")
    assert r.ignored("docs/x.png")
    assert not r.ignored("a/docs/x.png")


def test_a_leading_slash_also_anchors():
    r = rules("/build\n")
    assert r.ignored("build", is_dir=True)
    assert not r.ignored("a/build", is_dir=True)


def test_nested_gitignore_patterns_anchor_to_their_own_prefix_not_the_root():
    r = rules("*.tmp\n", prefix="docs")
    assert r.ignored("docs/scratch.tmp")
    assert not r.ignored("scratch.tmp")


# -- trailing slash: directories only, but excludes everything beneath ------


def test_trailing_slash_matches_a_directory_not_a_same_named_file():
    r = rules("build/\n")
    assert r.ignored("build", is_dir=True)
    assert not r.ignored("build", is_dir=False)


def test_trailing_slash_still_excludes_files_beneath_it():
    r = rules("build/\n")
    assert r.ignored("build/output.txt", is_dir=False)
    assert r.ignored("build/nested/output.txt", is_dir=False)


# -- negation, and the order it depends on -----------------------------------


def test_negation_reincludes_a_previously_excluded_file():
    r = rules("*.log\n!keep.log\n")
    assert r.ignored("a.log")
    assert not r.ignored("keep.log")


def test_last_matching_pattern_wins_regardless_of_which_came_first():
    # The exclusion is written *after* the negation here, so it must win --
    # a first-match evaluator would get this backwards.
    r = rules("!keep.log\n*.log\n")
    assert r.ignored("keep.log")


def test_negation_cannot_rescue_a_file_whose_directory_is_excluded():
    """gitignore(5): "It is not possible to re-include a file if a parent
    directory of that file is excluded." Real git never looks inside an
    excluded directory, so the negated rule never gets a chance to apply.

    contextcost's walker (walk_repository) enforces this by never
    descending into an excluded directory in the first place -- see
    test_walk.py. This checks the same property at the IgnoreRules level,
    where there is no traversal to rely on.
    """
    r = rules("build/\n!build/keep.txt\n")
    assert r.ignored("build/keep.txt", is_dir=False)


# -- ** crosses directory boundaries, a single * does not --------------------


def test_leading_double_star_matches_any_depth_above():
    r = rules("**/target\n")
    assert r.ignored("target", is_dir=True)
    assert r.ignored("a/target", is_dir=True)
    assert r.ignored("a/b/target", is_dir=True)


def test_trailing_double_star_matches_everything_inside():
    r = rules("abc/**\n")
    assert r.ignored("abc/one.txt")
    assert r.ignored("abc/nested/two.txt")


def test_interior_double_star_matches_zero_or_more_directories():
    r = rules("a/**/b\n")
    assert r.ignored("a/b")
    assert r.ignored("a/x/b")
    assert r.ignored("a/x/y/b")
    assert not r.ignored("a/bee")


def test_single_star_does_not_cross_a_directory_separator():
    r = rules("a/*/c\n")
    assert r.ignored("a/b/c")
    assert not r.ignored("a/b/x/c")


# -- character classes --------------------------------------------------------


def test_bracket_class_matches_one_of_a_set():
    r = rules("file[12].txt\n")
    assert r.ignored("file1.txt")
    assert r.ignored("file2.txt")
    assert not r.ignored("file3.txt")


def test_negated_bracket_class():
    r = rules("file[!12].txt\n")
    assert r.ignored("file3.txt")
    assert not r.ignored("file1.txt")


# -- comments and blank lines are not patterns --------------------------------


def test_comment_and_blank_lines_are_skipped():
    r = rules("# a comment\n\n*.log\n")
    assert len(r) == 1
    assert r.ignored("a.log")


# -- always-skip directories, independent of any .gitignore ------------------


def test_always_skip_names_the_expected_set():
    assert ".git" in ALWAYS_SKIP
    assert "__pycache__" in ALWAYS_SKIP


# -- loading from disk ---------------------------------------------------------


def test_load_ignore_rules_reads_the_root_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    loaded = load_ignore_rules(str(tmp_path))
    assert loaded.ignored("a.log")


def test_load_ignore_rules_with_use_gitignore_false_returns_no_rules(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    loaded = load_ignore_rules(str(tmp_path), use_gitignore=False)
    assert not loaded.ignored("a.log")
    assert len(loaded) == 0


def test_load_ignore_rules_with_no_gitignore_file_returns_no_rules(tmp_path):
    loaded = load_ignore_rules(str(tmp_path))
    assert len(loaded) == 0


# -- .contextcostignore: project-local ignores with last-word semantics ------


def test_contextcostignore_is_read_for_every_consumer(tmp_path):
    (tmp_path / ".gitignore").write_text("fixtures/\n", encoding="utf-8")
    (tmp_path / CONTEXTCOST_IGNORE_FILE).write_text("docs/generated.md\n")
    loaded = load_ignore_rules(str(tmp_path), consumer="cursor")

    assert loaded.ignored("docs/generated.md")
    assert CONTEXTCOST_IGNORE_FILE in active_ignore_files(
        str(tmp_path), consumer="cursor"
    )


def test_contextcostignore_patterns_win_over_earlier_inputs(tmp_path):
    """The merge is concatenation with this file at the tail, so git's
    last-matching-pattern-wins gives its lines the final say -- including a
    `!` re-inclusion that undoes what .gitignore hid."""
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (tmp_path / CONTEXTCOST_IGNORE_FILE).write_text("!keep.log\n", encoding="utf-8")

    loaded = load_ignore_rules(str(tmp_path))
    assert loaded.ignored("other.log")
    assert not loaded.ignored("keep.log")


def test_active_ignore_files_orders_contextcostignore_last(tmp_path):
    (tmp_path / ".gitignore").write_text("")
    (tmp_path / ".aiderignore").write_text("")
    (tmp_path / CONTEXTCOST_IGNORE_FILE).write_text("")

    assert active_ignore_files(str(tmp_path), consumer="aider") == [
        ".gitignore",
        ".aiderignore",
        CONTEXTCOST_IGNORE_FILE,
    ]


def test_contextcostignore_is_read_even_when_gitignore_semantics_are_off(tmp_path):
    """--no-gitignore asks what a repository looks like to a tool with no
    ignore inputs at all; this file is *this* tool's own input, so it still
    applies. Otherwise accepting a proposal via --emit-ignore could never
    change a --no-gitignore measurement, and the flag would lie."""
    (tmp_path / CONTEXTCOST_IGNORE_FILE).write_text("data/\n", encoding="utf-8")

    assert load_ignore_rules(
        str(tmp_path), use_gitignore=False
    ).ignored("data/big.csv")
    # ...and it is listed as an input even then.
    assert active_ignore_files(str(tmp_path), use_gitignore=False) == [
        CONTEXTCOST_IGNORE_FILE
    ]
