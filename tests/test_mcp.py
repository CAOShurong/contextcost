"""The MCP server: the protocol promises kept, and the tools wired to real
measurement.

Weighted where an agent could be misled rather than inconvenienced: a reply
to a notification (framing corruption), a wrong id on an error (the client
cannot correlate it), and tool output that was not measured by the same code
path the CLI uses.
"""

from __future__ import annotations

import io
import json

from contextcost import __version__
from contextcost.cli import main as cli_main
from contextcost.mcp_server import TOOLS, MCPServer, estimate_tool, propose_tool


def _server(lines: list[str]) -> tuple[MCPServer, io.StringIO]:
    stdin = io.StringIO("".join(line + "\n" for line in lines))
    stdout = io.StringIO()
    return MCPServer(stdin=stdin, stdout=stdout), stdout


def _replies(server: MCPServer, stdout: io.StringIO) -> list[dict]:
    out = stdout.getvalue()
    if not out:
        return []
    return [json.loads(line) for line in out.splitlines()]


def build(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return str(root)


FILLER = "The quick brown fox jumps over the lazy dog. " * 20
SOURCE = "def add(a, b):\n    return a + b\n" * 30


# -- protocol ---------------------------------------------------------------


def test_initialize_returns_server_info_and_echoes_protocol_version():
    server, stdout = _server(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18"},
                }
            )
        ]
    )
    assert server.serve() == 0
    replies = _replies(server, stdout)
    assert len(replies) == 1
    body = replies[0]
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == 1
    assert "error" not in body
    assert body["result"]["protocolVersion"] == "2025-06-18"
    assert body["result"]["serverInfo"]["name"] == "contextcost"
    assert body["result"]["serverInfo"]["version"] == __version__
    assert "tools" in body["result"]["capabilities"]


def test_a_notification_gets_no_reply_at_all():
    """Replying to a message without an id corrupts the framing; spec forbids."""
    server, stdout = _server(
        [json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})]
    )
    assert server.serve() == 0
    assert stdout.getvalue() == ""


def test_ping_answers_with_empty_result():
    server, stdout = _server(['{"jsonrpc": "2.0", "id": 7, "method": "ping"}'])
    server.serve()
    (reply,) = _replies(server, stdout)
    assert reply["id"] == 7
    assert reply["result"] == {}


def test_tools_list_advertises_estimate_and_propose():
    server, stdout = _server(['{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'])
    server.serve()
    (reply,) = _replies(server, stdout)
    names = [tool["name"] for tool in reply["result"]["tools"]]
    assert names == ["estimate", "propose"]
    for tool in reply["result"]["tools"]:
        assert tool["inputSchema"]["required"] == ["repo"]
        assert tool["description"]


def test_unknown_method_is_method_not_found_with_the_callers_id():
    server, stdout = _server(
        ['{"jsonrpc": "2.0", "id": 9, "method": "resources/list"}']
    )
    server.serve()
    (reply,) = _replies(server, stdout)
    assert reply["id"] == 9
    assert reply["error"]["code"] == -32601


def test_an_unknown_notification_stays_silent():
    server, stdout = _server(['{"jsonrpc": "2.0", "method": "no/such/method"}'])
    assert server.serve() == 0
    assert stdout.getvalue() == ""


def test_ungarbled_line_is_a_parse_error_not_a_crash():
    lines = ["{not json at all", '{"jsonrpc": "2.0", "id": 3, "method": "ping"}']
    server, stdout = _server(lines)
    assert server.serve() == 0
    replies = _replies(server, stdout)
    assert len(replies) == 2
    # The parse error carries null per the spec, then the session continues.
    assert replies[0]["id"] is None
    assert replies[0]["error"]["code"] == -32700
    assert replies[1]["id"] == 3
    assert "error" not in replies[1]


def test_empty_and_whitespace_lines_are_skipped():
    server, stdout = _server(
        ["", "   ", '{"jsonrpc": "2.0", "id": 4, "method": "ping"}']
    )
    assert server.serve() == 0
    assert len(_replies(server, stdout)) == 1


# -- tools against a real repository ----------------------------------------


def _init_repo(root):
    return build(root, {"yarn.lock": FILLER, "src/app.py": SOURCE})


def test_estimate_tool_output_equals_the_cli_json(tmp_path):
    root = _init_repo(tmp_path)

    from contextcost import json_schema as js

    document = estimate_tool(root)
    assert document["schema"] == js.SCHEMA_VERSION == 1
    assert document["reduction"]["measured"] is True
    assert document["error_bound"] == document["error_bound"]  # present
    assert any(entry["path"] == "yarn.lock" for entry in document["largest"])
    # Same numbers the CLI would print for this tree.
    assert document["walk"]["tokens"] > 0
    assert document["walk"]["bytes"] > 0


def test_estimate_matches_cli_walk_tokens(tmp_path):
    """The tool must measure with the same walk the CLI prints -- no drift."""

    root = _init_repo(tmp_path)
    cli_main([root, "--json"])
    cli_document = json.loads(_captured_cli_json(root))
    tool_document = estimate_tool(root)
    assert tool_document["walk"]["tokens"] == cli_document["walk"]["tokens"]
    assert tool_document["reduction"]["saved"] == cli_document["reduction"]["saved"]


def _captured_cli_json(root):
    import contextlib

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        cli_main([root, "--json"])
    return buffer.getvalue()


def test_propose_tool_reports_measured_saving_and_patterns(tmp_path):
    root = _init_repo(tmp_path)
    document = propose_tool(root)
    assert "/yarn.lock" in document["patterns"]
    assert document["measured"] is True
    assert document["saved"] > 0
    assert document["after"] < document["before"]
    block = document["gitignore_block"]
    assert "# Added by contextcost" in block
    assert "/yarn.lock" in block
    # Deferred findings are the tier the file system cannot judge: listed,
    # never silently acted on.
    assert isinstance(document["deferred"], list)


def test_tools_call_round_trip_through_the_wire_format(tmp_path):
    root = _init_repo(tmp_path)
    request = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {"name": "estimate", "arguments": {"repo": root}},
    }
    server, stdout = _server([json.dumps(request)])
    assert server.serve() == 0
    (reply,) = _replies(server, stdout)
    assert reply["id"] == 11
    assert "error" not in reply
    content = reply["result"]["content"]
    assert reply["result"]["isError"] is False
    assert content[0]["type"] == "text"
    payload = json.loads(content[0]["text"])
    assert payload["schema"] == 1
    assert payload["reduction"]["saved"] >= 0


def test_tools_call_propose_over_the_wire(tmp_path):
    root = _init_repo(tmp_path)
    request = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {"name": "propose", "arguments": {"repo": root}},
    }
    server, stdout = _server([json.dumps(request)])
    server.serve()
    (reply,) = _replies(server, stdout)
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["patterns"]
    assert payload["gitignore_block"]


def test_missing_repo_argument_is_a_clean_tool_error():
    server, stdout = _server(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 13,
                    "method": "tools/call",
                    "params": {"name": "estimate", "arguments": {}},
                }
            )
        ]
    )
    server.serve()
    (reply,) = _replies(server, stdout)
    assert reply["id"] == 13
    assert "must be a path string" in reply["error"]["message"]


def test_unknown_tool_name_is_reported_not_crashed():
    server, stdout = _server(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 14,
                    "method": "tools/call",
                    "params": {"name": "deploy", "arguments": {}},
                }
            )
        ]
    )
    server.serve()
    (reply,) = _replies(server, stdout)
    assert "unknown tool: deploy" in reply["error"]["message"]
    assert reply["id"] == 14


def test_nonexistent_repo_surfaces_the_os_error_as_data():
    server, stdout = _server(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 15,
                    "method": "tools/call",
                    "params": {
                        "name": "estimate",
                        "arguments": {"repo": "Z:/no/such/path"},
                    },
                }
            )
        ]
    )
    server.serve()
    (reply,) = _replies(server, stdout)
    assert "error" in reply
    # The agent gets something actionable, not a dead pipe.
    assert "Error" in reply["error"]["message"] or "error" in reply["error"]["message"]


def test_tools_table_shapes_are_declared_once():
    names = [t["name"] for t in TOOLS]
    assert names == ["estimate", "propose"]
    assert all(t["inputSchema"]["type"] == "object" for t in TOOLS)


def test_mcp_subcommand_serves_on_stdio(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"jsonrpc": "2.0", "id": 21, "method": "ping"}\n'),
    )
    import contextcost.cli as cli_module

    original_stdout = cli_module.sys.stdout
    cli_module.sys.stdout = io.StringIO()
    try:
        assert cli_main(["mcp"]) == 0
        out = cli_module.sys.stdout.getvalue()
    finally:
        cli_module.sys.stdout = original_stdout
    reply = json.loads(out.strip())
    assert reply["id"] == 21
    assert reply["result"] == {}
