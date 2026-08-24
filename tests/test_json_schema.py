"""The ``--json`` schema contract: what is promised, and that it is kept.

The Action parses this output on other people's pull requests. A key that
changes shape silently does not fail loudly -- it makes someone's CI report a
wrong number, which is worse. So the contract is data (json_schema.CONTRACT),
and these tests walk it against real output so drift fails here first.
"""

from __future__ import annotations

import json

from contextcost import __version__
from contextcost.json_schema import CONTRACT, SCHEMA_VERSION, build_payload
from test_cli import FILLER, SOURCE, build
from test_cli import main as cli_main


def _run_json(tmp_path, capsys):
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    cli_main([str(root), "--json"])
    return json.loads(capsys.readouterr().out)


def test_payload_carries_the_schema_version(tmp_path, capsys):
    payload = _run_json(tmp_path, capsys)
    assert payload["schema"] == SCHEMA_VERSION == 1
    assert payload["version"] == __version__


def test_every_required_contract_key_is_present_in_real_output(tmp_path, capsys):
    """The contract is documentation only until it is enforced."""
    payload = _run_json(tmp_path, capsys)
    for key, spec in CONTRACT.items():
        if spec.get("optional"):
            assert key not in payload, f"{key} must stay absent without --accurate"
        else:
            assert key in payload, f"contract requires '{key}'"


def test_accurate_key_is_optional_and_present_only_when_asked(
    tmp_path, capsys, monkeypatch
):
    payload = _run_json(tmp_path, capsys)
    assert "accurate" not in payload

    from contextcost.accurate import AccurateResult, FileAccuracy

    fake = AccurateResult(
        files=[FileAccuracy(path="src/app.py", tokens=7, estimated=9)]
    )
    monkeypatch.setattr(
        "contextcost.cli.count_repository", lambda walk: fake, raising=False
    )

    class FakeModule:
        def count_repository(self, walk):
            return fake

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "contextcost.accurate", FakeModule())
    root = build(tmp_path / "b", {"yarn.lock": FILLER, "src/app.py": SOURCE})
    cli_main([str(root), "--json", "--accurate"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["accurate"]["tokens"] == 7
    assert payload["schema"] == SCHEMA_VERSION


def test_build_payload_matches_what_the_cli_prints(tmp_path, capsys):
    """One assembly path: the helper cannot drift from the CLI."""
    root = build(tmp_path, {"yarn.lock": FILLER, "src/app.py": SOURCE})
    cli_main([str(root), "--json"])
    printed = json.loads(capsys.readouterr().out)

    from contextcost.reduce import reduce_repository
    from contextcost.walk import walk_repository

    walk = walk_repository(str(root))
    reduction = reduce_repository(str(root))
    rebuilt = build_payload(
        version=__version__,
        consumer="generic",
        reduction=reduction,
        walk=walk,
        error_bound=printed["error_bound"],
        top=5,
    )
    assert rebuilt == printed


def test_schema_document_is_self_describing(capsys):
    from contextcost.cli import main

    assert main(["--json-schema"]) == 0
    text = capsys.readouterr().out
    assert f"schema v{SCHEMA_VERSION}" in text
    for key in CONTRACT:
        assert key in text
    assert "ignore keys you do not know" in text


def test_new_optional_keys_do_not_break_a_v1_consumer(tmp_path, capsys):
    """The stability promise, pinned: an old consumer reading known keys
    survives unknown ones, so additions never need a version bump."""
    payload = _run_json(tmp_path, capsys)
    consumer_keys = {"schema", "version", "reduction"}
    assert consumer_keys <= set(payload)  # all still there
    payload["something_new"] = 1  # a future addition
    assert {k: payload[k] for k in consumer_keys}["schema"] == 1
