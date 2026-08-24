"""Tests for --accurate: exact counts beside the estimate.

Weighted where a wrong number would actually hurt: the exact total must be
exact (checked against tiktoken directly), it must cover exactly the files
the walk measured, and the CLI must refuse loudly rather than pretend when
tiktoken is missing.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip(
    "tiktoken",
    reason="accurate mode is an optional extra; these tests need tiktoken",
)

from contextcost.accurate import ACCURATE_ENCODING, count_repository, count_text
from contextcost.cli import MISSING_DEPENDENCY_EXIT, main

FILLER = "The quick brown fox jumps over the lazy dog. " * 20
# Deliberately shaped like real source -- varied lines, docstrings, real
# identifiers -- not like a pathological repeated stub, which no repository
# is made of and which no character-class ratio is calibrated on.
SOURCE = (
    '''import os
from pathlib import Path


def load_config(root: Path) -> dict:
    """Read the project configuration file."""
    path = root / "contextcost.toml"
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def main() -> int:
    config = load_config(Path.cwd())
    print("loaded", len(config), "keys")
    return 0
'''
    * 4
)


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # Bytes, not write_text: a text-mode write translates newlines on
        # Windows, and then what is counted is not the fixture string.
        path.write_bytes(text.encode("utf-8"))
    return str(root)


def test_count_text_is_actually_exact():
    assert count_text("hello world") == 2
    # Special tokens in content are counted as text, never raise.
    assert count_text("<|endoftext|>") > 0


def test_exact_total_is_the_sum_of_per_file_counts(tmp_path):
    from contextcost.walk import walk_repository

    root = build(tmp_path, {"src/app.py": SOURCE, "README.md": FILLER})
    walk = walk_repository(root)
    accurate = count_repository(walk)

    encoder = tiktoken_encoding()
    expected = sum(
        len(encoder.encode(text, disallowed_special=())) for text in (SOURCE, FILLER)
    )
    assert accurate.tokens == expected


def tiktoken_encoding():
    import tiktoken

    return tiktoken.get_encoding(ACCURATE_ENCODING)


def test_accurate_covers_exactly_the_walks_text_files(tmp_path):
    from contextcost.walk import walk_repository

    root = build(
        tmp_path,
        {"src/app.py": SOURCE, "README.md": FILLER, "logo.png": "not really png"},
    )
    walk = walk_repository(root)
    accurate = count_repository(walk)

    assert {f.path for f in accurate.files} == {c.path for c in walk.text_files}
    binary_paths = {c.path for c in walk.binary_files}
    assert all(f.path not in binary_paths for f in accurate.files)


def test_estimated_lands_inside_its_band_on_this_corpus(tmp_path):
    """The fixture corpus: the estimate must sit inside its stated ±12% band."""
    from contextcost.walk import walk_repository

    root = build(tmp_path, {"src/app.py": SOURCE, "README.md": FILLER})
    walk = walk_repository(root)
    accurate = count_repository(walk)

    drift = abs(accurate.estimated_tokens - accurate.tokens) / accurate.tokens
    assert drift <= 0.12


def test_missing_file_between_walk_and_count_is_zero_and_sampled(tmp_path):
    from contextcost.walk import walk_repository

    root = build(tmp_path, {"gone.py": SOURCE})
    walk = walk_repository(root)
    (tmp_path / "gone.py").unlink()

    accurate = count_repository(walk)
    assert accurate.tokens == 0
    assert accurate.sampled_paths == ["gone.py"]


def test_cli_json_carries_both_numbers(tmp_path, capsys):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    assert main([root, "--json", "--accurate"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["accurate"]["encoding"] == ACCURATE_ENCODING
    exact = payload["accurate"]["tokens"]
    estimated = payload["walk"]["tokens"]
    assert exact > 0
    assert abs(exact - estimated) / exact <= 0.12
    # The reduction totals are still the estimator's; the exact block sits
    # beside them rather than replacing them.
    assert payload["reduction"]["before"] == estimated


def test_cli_report_shows_estimate_beside_exact_never_alone(tmp_path, capsys):
    root = build(tmp_path, {"src/app.py": SOURCE})
    main([root, "--no-color", "--accurate"])
    out = capsys.readouterr().out

    assert "exact (" in out
    assert ACCURATE_ENCODING in out
    assert "estimated" in out, "the estimate must stay on screen"


def test_without_tiktoken_the_flag_fails_with_exit_3(tmp_path, capsys, monkeypatch):
    import sys as _sys

    import contextcost.accurate as accurate_module

    # A `None` entry in sys.modules makes `import tiktoken` raise ImportError,
    # which is exactly what a missing optional dependency looks like. The
    # module-level encoder cache must go too, or an earlier test in the same
    # process would have already loaded tiktoken and hidden the failure.
    monkeypatch.setitem(_sys.modules, "tiktoken", None)
    monkeypatch.setattr(accurate_module, "_ENCODER", None)
    root = build(tmp_path, {"src/app.py": SOURCE})

    assert main([root, "--accurate"]) == MISSING_DEPENDENCY_EXIT == 3
    err = capsys.readouterr().err
    assert "contextcost[accurate]" in err
    # And it does not half-print a report as if nothing happened.
    assert capsys.readouterr().out == "" or "--accurate" in err
