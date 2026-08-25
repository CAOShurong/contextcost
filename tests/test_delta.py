"""Tests for the context-cost delta and the CLI that prints it.

The consumer is a pull-request comment: it must answer "what did this change
do to the budget" with per-file honesty -- no subtraction across walks, no
attribution guessed from filenames, and an estimate never printed without
its error bound.
"""

from contextcost.cli import main
from contextcost.delta import measure_delta

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return str(root)


def test_added_files_account_for_the_whole_increase(tmp_path):
    base = build(tmp_path / "base", {"src/app.py": SOURCE})
    head = build(
        tmp_path / "head",
        {"src/app.py": SOURCE, "yarn.lock": FILLER, "src/extra.py": SOURCE},
    )
    delta = measure_delta(base, head)

    assert delta.after > delta.before
    assert delta.added == delta.after - delta.before
    paths = {f.path for f in delta.files}
    assert "yarn.lock" in paths and "src/extra.py" in paths


def test_removed_file_is_reported_not_just_a_negative_total(tmp_path):
    base = build(tmp_path / "base", {"src/app.py": SOURCE, "old.js": SOURCE})
    head = build(tmp_path / "head", {"src/app.py": SOURCE})
    delta = measure_delta(base, head)

    removed = [f for f in delta.files if f.change == "removed"]
    assert [f.path for f in removed] == ["old.js"]
    assert delta.removed == delta.before - delta.after


def test_grown_and_shrunk_files_carry_the_difference(tmp_path):
    grown = SOURCE + "x = 1\n"
    base = build(tmp_path / "base", {"src/app.py": SOURCE, "src/b.py": SOURCE})
    head = build(tmp_path / "head", {"src/app.py": grown, "src/b.py": SOURCE[:100]})
    delta = measure_delta(base, head)

    by_path = {f.path: f for f in delta.files}
    assert by_path["src/app.py"].change == "grown"
    assert by_path["src/b.py"].change == "shrunk"
    # Unchanged files are noise; they must not be listed.
    unchanged = [
        p for p, c in {
            "/src/app.py": (len(SOURCE), len(grown)),
            "/src/b.py": (len(SOURCE), 100),
        }.items()
        if c[0] == c[1]
    ]
    assert not any(f.path in unchanged for f in delta.files)


def test_identical_trees_produce_an_empty_delta(tmp_path):
    files = {"src/app.py": SOURCE, "README.md": FILLER}
    base = build(tmp_path / "base", files)
    head = build(tmp_path / "head", files)
    delta = measure_delta(base, head)

    assert delta.added == 0 and delta.removed == 0
    assert delta.files == []


def test_attribution_names_the_rule_that_fired_on_head(tmp_path):
    head = build(tmp_path / "head", {"yarn.lock": FILLER, "src/app.py": SOURCE})
    base = build(tmp_path / "base", {"src/app.py": SOURCE})
    delta = measure_delta(base, head)

    assert "lockfile" in delta.attribution
    lockfile_tokens = delta.attribution["lockfile"]
    yarn = next(f for f in delta.files if f.path == "yarn.lock")
    assert lockfile_tokens >= yarn.tokens


def test_unclassified_work_is_separated_from_noise(tmp_path):
    """A new source file is not waste; the report must say so by leaving it
    under ``unclassified`` rather than stretching a rule to cover it."""
    head = build(tmp_path / "head", {"src/new_module.py": SOURCE})
    base = build(tmp_path / "base", {})
    delta = measure_delta(base, head)

    assert "unclassified" in delta.attribution
    total = sum(delta.attribution.values())
    assert total == delta.added


def test_as_dict_round_trips_the_shape(tmp_path):
    base = build(tmp_path / "base", {"src/app.py": SOURCE})
    head = build(tmp_path / "head", {"src/app.py": SOURCE, "yarn.lock": FILLER})
    payload = measure_delta(base, head).as_dict()

    assert set(payload) >= {"before", "after", "added", "removed", "attribution"}
    assert isinstance(payload["files"], list) and payload["files"]


def test_cli_delta_markdown_prints_the_pr_comment(tmp_path, capsys):
    base = build(tmp_path / "base", {"src/app.py": SOURCE})
    head = build(tmp_path / "head", {"src/app.py": SOURCE, "yarn.lock": FILLER})
    assert main([head, "--delta", base, "--markdown", "--no-color"]) == 0
    out = capsys.readouterr().out

    assert "## contextcost" in out
    assert "| rule | tokens |" in out
    assert "**lockfile**" in out
    assert "`yarn.lock`" in out


def test_cli_delta_json_carries_the_numbers_for_ci_gating(tmp_path, capsys):
    import json

    base = build(tmp_path / "base", {"src/app.py": SOURCE})
    head = build(tmp_path / "head", {"src/app.py": SOURCE, "yarn.lock": FILLER})
    assert main([head, "--delta", base, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema"] == 1
    added = payload["delta"]["added"]
    assert added > 0
    assert payload["delta"]["attribution"]["lockfile"] <= added


def test_cli_delta_rejects_a_missing_base(tmp_path):
    build(tmp_path / "head", {"src/app.py": SOURCE})
    assert main([str(tmp_path / "head"), "--delta", str(tmp_path / "nope")]) == 2


def test_cli_delta_quiet_prints_nothing(tmp_path, capsys):
    base = build(tmp_path / "base", {"src/app.py": SOURCE})
    head = build(tmp_path / "head", {"src/app.py": SOURCE, "yarn.lock": FILLER})
    assert main([head, "--delta", base, "--quiet"]) == 0
    assert capsys.readouterr().out == ""
