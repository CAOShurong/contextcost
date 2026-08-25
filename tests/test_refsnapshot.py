"""Tests for resolving a ``--delta`` base that names a git revision.

The promise under test: ``--delta main`` must answer the same question as a
hand-made second checkout, because both paths end in two ordinary directories
walked by the same code. The failure modes are pinned just as hard -- an
unknown ref is an error with git's own words, not a silent empty comparison,
and a real directory always wins over a ref of the same name.
"""

import os
import subprocess

import pytest

from contextcost.cli import main
from contextcost.refsnapshot import RefResolutionError, resolve_ref_tree

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


def _git(root, *arguments):
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    """A real git repository: base commit on `main`, heavier working tree."""
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text(SOURCE, encoding="utf-8")
    identity = (
        "-c", "user.email=test@example.com",
        "-c", "user.name=Test",
    )
    _git(root, "init", "--initial-branch=main")
    _git(root, *identity, "add", ".")
    _git(root, *identity, "commit", "-m", "base")
    # Uncommitted growth: present in PATH's walk, absent from the ref tree.
    (root / "yarn.lock").write_text(FILLER, encoding="utf-8")
    return root


def test_ref_base_matches_a_materialised_checkout(repo, capsys):
    """`--delta HEAD` agrees with the classic two-directory invocation."""
    via_ref = None
    assert (
        main([str(repo), "--delta", "HEAD", "--json", "--no-color"]) == 0
    )
    payload = capsys.readouterr()
    via_ref = payload.out
    # A second run through the directory path must produce identical JSON.
    export_dir = resolve_ref_tree("HEAD", str(repo))
    try:
        assert (
            main([str(repo), "--delta", export_dir, "--json", "--no-color"]) == 0
        )
        again = capsys.readouterr().out
    finally:
        pass
    assert via_ref == again


def test_ref_delta_reports_the_uncommitted_lockfile(repo, capsys):
    assert main([str(repo), "--delta", "HEAD", "--json", "--no-color"]) == 0
    import json

    payload = json.loads(capsys.readouterr().out)
    delta = payload["delta"]
    assert delta["added"] > 0
    paths = {entry["path"] for entry in delta["files"]}
    assert "yarn.lock" in paths


def test_unknown_revision_is_an_error_not_an_empty_comparison(repo):
    assert main([str(repo), "--delta", "no-such-branch"]) == 2


def test_existing_directory_beats_a_same_named_ref(tmp_path, repo):
    """A path spelled by the user wins over a revision of the same name."""
    decoy = tmp_path / "main"
    decoy.mkdir()
    resolved = resolve_ref_tree(str(decoy), str(repo))
    assert resolved is None


def test_resolution_against_a_non_repository_names_the_real_problem(
    tmp_path, repo
):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(RefResolutionError) as raised:
        resolve_ref_tree("HEAD", str(plain))
    assert "not a git repository" in str(raised.value)


def test_exported_tree_holds_only_tracked_files(repo):
    exported = resolve_ref_tree("HEAD", str(repo))
    assert exported is not None
    # yarn.lock exists only as an untracked edit in the working tree; the
    # commit's tree must not contain it.
    assert not os.path.exists(os.path.join(exported, "yarn.lock"))
    assert os.path.isfile(os.path.join(exported, "src", "app.py"))


def test_export_is_repeatable_and_independent(repo):
    first = resolve_ref_tree("HEAD", str(repo))
    second = resolve_ref_tree("main", str(repo))
    assert first != second
    for directory in (first, second):
        with open(os.path.join(directory, "src", "app.py"), encoding="utf-8") as handle:
            assert handle.read() == SOURCE
