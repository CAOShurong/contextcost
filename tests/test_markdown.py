"""Tests for the Markdown report.

The consumer is a PR comment or a README: no ANSI escapes anywhere, tables
that GitHub actually renders, and the honesty rules of the terminal report
carried over intact -- estimate with its bound, saving described as measured,
the deferred tier phrased as a question.
"""

from contextcost.cli import main
from contextcost.markdown import render_markdown
from contextcost.reduce import reduce_repository
from contextcost.walk import walk_repository

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return str(root)


def test_no_ansi_escapes_reach_a_pr_comment(tmp_path):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    walk = walk_repository(root)
    reduction = reduce_repository(root)
    text = render_markdown(walk, reduction)

    assert "\033[" not in text, "a terminal colour code would print literally"


def test_headline_carries_the_error_bound(tmp_path):
    root = build(tmp_path, {"src/app.py": SOURCE})
    walk = walk_repository(root)
    text = render_markdown(walk, reduce_repository(root))

    assert "tokens" in text
    from contextcost.estimate import ERROR_BOUND

    assert f"\u00b1{ERROR_BOUND:.0%}" in text, "an estimate without its bound gets quoted without one"


def test_tables_render_as_pipe_tables(tmp_path):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    walk = walk_repository(root)
    reduction = reduce_repository(root)
    text = render_markdown(walk, reduction)

    assert "| directory | tokens | share |" in text
    assert "| file | tokens |" in text
    # A table separator row exists under each header.
    assert "| --- | --- | --- |" in text


def test_saving_is_described_as_measured(tmp_path):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    walk = walk_repository(root)
    reduction = reduce_repository(root)
    text = render_markdown(walk, reduction)

    assert "walking the repository again" in text
    assert f"{reduction.before:,}" in text and f"{reduction.after:,}" in text
    # The pattern appears in the fenced gitignore block, not as inline code.
    assert "```gitignore" in text and "/yarn.lock" in text


def test_deferred_tier_stays_a_question(tmp_path):
    rows = "".join(f"{n},alpha,beta,gamma,delta\n" for n in range(2000))
    root = build(tmp_path, {"data/rows.csv": rows, "src/app.py": SOURCE})
    walk = walk_repository(root)
    reduction = reduce_repository(root)

    assert reduction.deferred, "the fixture must actually produce deferred findings"
    text = render_markdown(walk, reduction)
    assert "not excluded automatically" in text
    assert "--include-possible" in text


def test_badge_is_opt_in_and_points_at_shields(tmp_path):
    root = build(tmp_path, {"src/app.py": SOURCE})
    walk = walk_repository(root)
    reduction = reduce_repository(root)

    without = render_markdown(walk, reduction)
    with_badge = render_markdown(walk, reduction, badge=True)

    assert "shields.io" not in without
    assert with_badge.startswith("![context cost](https://img.shields.io/badge/")
    assert f"{walk.tokens:,}%20tokens" in with_badge


def test_cli_markdown_flag_prints_the_report(tmp_path, capsys):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    assert main([root, "--markdown", "--no-color"]) == 1
    out = capsys.readouterr().out
    assert "# contextcost" in out
    assert "| directory | tokens | share |" in out


def test_cli_markdown_respects_quiet_like_the_terminal_report(tmp_path, capsys):
    """``--quiet`` silences the Markdown report exactly as it does the plain
    one, so a CI job can act on the exit code without output."""
    root = build(tmp_path, {"src/app.py": SOURCE})
    assert main([root, "--markdown", "--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_a_path_that_windows_cannot_carry_is_escaped_in_place(tmp_path):
    """Windows forbids ``|`` in filenames, so the escape path is exercised by
    calling the renderer on a hand-built walk rather than a real tree."""
    from contextcost.reduce import Reduction
    from contextcost.walk import FileCost, WalkResult

    cost = FileCost("weird|name.py", len(SOURCE), 40, "code")
    walk = WalkResult("repo", [cost])
    reduction = Reduction("repo", 40, 0, [], [], [], [])
    text = render_markdown(walk, reduction)

    assert r"weird\|name.py" in text
