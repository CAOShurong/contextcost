"""Tests for the command line.

Weighted at the two things a user could be hurt by rather than merely annoyed
by: writing to their `.gitignore`, and an exit code that a CI job will act on.
Everything else the CLI does is printing, which `test_report.py` covers.
"""

import json

from contextcost.cli import main

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return str(root)


def test_exit_code_is_zero_when_nothing_is_confidently_wasteful(tmp_path, capsys):
    root = build(tmp_path, {"src/app.py": SOURCE, "README.md": FILLER})
    assert main([root, "--no-color"]) == 0


def test_exit_code_is_one_when_something_was_found(tmp_path, capsys):
    """So `contextcost --quiet` works as a CI check for "did somebody commit a
    lockfile into the context budget"."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    assert main([root, "--no-color"]) == 1


def test_a_missing_directory_is_an_error_not_a_crash(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 2
    assert "not a directory" in capsys.readouterr().err


def test_quiet_prints_nothing_at_all(tmp_path, capsys):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    main([root, "--quiet"])
    assert capsys.readouterr().out == ""


def test_json_output_is_valid_and_says_the_saving_was_measured(tmp_path, capsys):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    main([root, "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["reduction"]["measured"] is True
    assert payload["error_bound"] > 0
    assert payload["reduction"]["saved"] == (
        payload["reduction"]["before"] - payload["reduction"]["after"]
    )
    assert payload["reduction"]["patterns"] == ["/yarn.lock"]
    assert payload["walk"]["tokens"] == payload["reduction"]["before"]


def test_the_gitignore_is_untouched_unless_asked(tmp_path, capsys):
    """The default output is a proposal. A tool that quietly edited a file
    somebody was about to commit would deserve what followed."""
    root = build(
        tmp_path, {".gitignore": "*.pyc\n", "yarn.lock": FILLER, "src/app.py": SOURCE}
    )
    main([root, "--no-color"])
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "*.pyc\n"


def test_write_gitignore_appends_and_says_what_it_did(tmp_path, capsys):
    root = build(
        tmp_path, {".gitignore": "*.pyc\n", "yarn.lock": FILLER, "src/app.py": SOURCE}
    )
    main([root, "--no-color", "--write-gitignore"])

    written = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert written.startswith("*.pyc\n"), "the existing content must survive"
    assert "# Added by contextcost" in written
    assert "/yarn.lock" in written
    assert "Measured saving" in written
    assert "Appended" in capsys.readouterr().out


def test_writing_twice_does_not_duplicate_the_block(tmp_path, capsys):
    """Running a tool twice is the most ordinary thing a person does.

    The second run finds nothing because the first run's patterns worked: the
    lockfile is genuinely ignored now, so the walk never sees it. That the
    tool becomes a no-op by fixing the problem is the behaviour worth pinning.
    """
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    main([root, "--no-color", "--write-gitignore"])
    first = (tmp_path / ".gitignore").read_text(encoding="utf-8")

    assert main([root, "--no-color", "--write-gitignore"]) == 0
    written = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert written == first
    assert written.count("# Added by contextcost") == 1
    assert "Nothing to write" in capsys.readouterr().out


def test_a_pattern_already_in_the_gitignore_is_not_repeated(tmp_path, capsys):
    """Reachable through --no-gitignore, where the walk sees files that are
    already ignored and so can propose patterns already written down.

    An earlier version refused outright whenever the file carried a contextcost
    block, which meant a lockfile committed a month later could never be added.
    Deduplicating per pattern rather than per block fixes that.
    """
    root = build(
        tmp_path,
        {".gitignore": "/yarn.lock\n", "yarn.lock": FILLER, "src/app.py": SOURCE},
    )

    main([root, "--no-color", "--no-gitignore", "--write-gitignore"])
    assert "already in it" in capsys.readouterr().out
    assert (tmp_path / ".gitignore").read_text(encoding="utf-8") == "/yarn.lock\n"

    # A second, genuinely new offender is still appended.
    (tmp_path / "poetry.lock").write_text(FILLER, encoding="utf-8")
    main([root, "--no-color", "--no-gitignore", "--write-gitignore"])
    written = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "/poetry.lock" in written
    assert written.count("/yarn.lock") == 1


def test_write_gitignore_on_a_clean_repository_writes_nothing(tmp_path, capsys):
    root = build(tmp_path, {"src/app.py": SOURCE})
    main([root, "--no-color", "--write-gitignore"])
    assert not (tmp_path / ".gitignore").exists()
    assert "Nothing to write" in capsys.readouterr().out


def test_include_possible_changes_the_answer(tmp_path, capsys):
    rows = "".join(f"{n},alpha,beta,gamma,delta\n" for n in range(2000))
    root = build(tmp_path, {"data/rows.csv": rows, "src/app.py": SOURCE})

    assert main([root, "--quiet"]) == 0
    assert main([root, "--quiet", "--include-possible"]) == 1


def test_no_gitignore_counts_what_git_would_hide(tmp_path, capsys):
    root = build(
        tmp_path,
        {".gitignore": "hidden/\n", "hidden/big.py": SOURCE * 4, "src/app.py": SOURCE},
    )
    main([root, "--json"])
    respecting = json.loads(capsys.readouterr().out)["walk"]["tokens"]

    main([root, "--json", "--no-gitignore"])
    counting_everything = json.loads(capsys.readouterr().out)["walk"]["tokens"]

    assert counting_everything > respecting
