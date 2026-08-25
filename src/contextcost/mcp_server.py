"""An MCP server so a coding agent can call this tool instead of shelling out.

**Who uses it, and what breaks without it.** Claude Code, Cursor and Codex
grow an "MCP servers" config where tools appear beside the model. An agent
that must shell out to ``contextcost`` has to guess at flags, parse human
output and hope the exit codes stay put; one that calls ``estimate`` or
``propose`` gets the same JSON the Action consumes, with the schema version in
band. This is the distribution channel for the measure→propose→re-measure
methodology: every agent that lists these tools can now ask "what does this
repo cost and what is wasting it" as a tool call.

**Stdlib only, on purpose.** The official SDK is a runtime dependency, which
would break the zero-dependency promise that ``pyproject.toml`` opens with.
MCP's wire format is JSON-RPC 2.0 over line-delimited stdio -- a ``Content-
Length`` framing exists for HTTP transports, but the stdio transport is one
JSON object per line -- and that is ~150 lines of ``json`` and ``sys``. The
server never imports tiktoken; ``estimate`` reports what the estimator says,
with its error bound, which is the honest number.

Protocol coverage is deliberately minimal: ``initialize``, ``notifications/
initialized``, ``ping``, ``tools/list``, ``tools/call``. Everything else gets
a method-not-found error, which is what a client needs to degrade gracefully.
Responses are always ``{"jsonrpc": "2.0", ...}``; notifications (no ``id``)
get no reply at all, per the spec.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING, Any

from . import __version__
from .estimate import ERROR_BOUND
from .json_schema import SCHEMA_VERSION, build_payload
from .reduce import reduce_repository
from .walk import walk_repository

if TYPE_CHECKING:  # pragma: no cover - import used only for annotations
    from .reduce import Reduction

__all__ = ["MCPServer", "serve"]


def _measure(root: str) -> tuple[Any, Reduction]:
    """One walk + reduction pair shared by both tools.

    A path that is not a directory raises here instead of measuring to an
    empty answer: an agent that mistyped a path must see the error, not a
    confident zero-cost report for a repository it never measured.
    """
    if not os.path.isdir(root):
        raise NotADirectoryError(f"not a directory: {root}")
    walk = walk_repository(root)
    reduction = reduce_repository(root)
    return walk, reduction


def estimate_tool(repo: str) -> dict:
    """The ``--json`` payload: what the repository costs to read."""
    walk, reduction = _measure(repo)
    return build_payload(
        version=__version__,
        consumer="generic",
        reduction=reduction,
        walk=walk,
        error_bound=ERROR_BOUND,
        top=5,
    )


def propose_tool(repo: str) -> dict:
    """The proposal on its own: patterns, measured saving, deferred findings."""
    _, reduction = _measure(repo)
    document = reduction.as_dict()
    # The agent-facing answer to "what should I drop": the patterns as text,
    # ready to paste into .gitignore or hand back to the user to accept.
    document["gitignore_block"] = reduction.gitignore_block()
    document["schema"] = SCHEMA_VERSION
    return document


#: The tool table, in MCP ``tools/list`` shape. Descriptions are written for
#: the model doing the choosing: they say when to call each and what comes
#: back, because an agent that cannot tell two tools apart calls the wrong
#: one and trusts the answer.
TOOLS = [
    {
        "name": "estimate",
        "description": (
            "Measure what a repository costs an AI coding agent to read:"
            " total tokens with error bound, cost by directory and extension,"
            " largest files, and the measured saving available from excluding"
            " waste. Call before filling a context window with a codebase."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "path to the repository root",
                },
            },
            "required": ["repo"],
        },
    },
    {
        "name": "propose",
        "description": (
            "Get the exclusion proposal for a repository: ignore patterns"
            " with a *measured* saving (the repo is walked again with them"
            " applied, not subtracted), plus findings left for a human to"
            " decide. Call after estimate to act on what it found."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "path to the repository root",
                },
            },
            "required": ["repo"],
        },
    },
]


class MCPServer:
    """One session of the protocol over arbitrary text streams."""

    def __init__(self, stdin=None, stdout=None):
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout

    # -- dispatch ---------------------------------------------------------

    def handle(self, message: dict) -> dict | None:
        """One decoded request/notification -> the response to write.

        Notifications get ``None``: the spec forbids replying to a message
        without an id, and a stray reply confuses framers more than silence.
        """
        method = message.get("method")
        identifier = message.get("id")
        params = message.get("params") or {}
        try:
            result = self._dispatch(method, params)
            if identifier is None:
                return None
            return {"jsonrpc": "2.0", "id": identifier, "result": result}
        except _MethodNotFound as exc:
            if identifier is None:
                return None
            return self._error(identifier, -32601, str(exc))
        except Exception as exc:  # noqa: BLE001 - reported over the wire
            # A failed measurement is data ("not a directory"), not a crash:
            # the agent gets the message and can correct its argument.
            if identifier is None:
                return None
            return self._error(identifier, -32603, f"{type(exc).__name__}: {exc}")

    def _dispatch(self, method: str | None, params: dict):
        if method == "initialize":
            return {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "contextcost", "version": __version__},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": TOOLS}
        if method == "tools/call":
            return self._call(params)
        raise _MethodNotFound(f"method not found: {method}")

    def _call(self, params: dict) -> dict:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handlers = {"estimate": estimate_tool, "propose": propose_tool}
        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"unknown tool: {name}")
        repo = arguments.get("repo")
        if not isinstance(repo, str) or not repo:
            raise ValueError("tool 'repo' argument must be a path string")
        return {
            "content": [{"type": "text", "text": json.dumps(handler(repo), indent=2)}],
            "isError": False,
        }

    @staticmethod
    def _error(identifier: Any, code: int, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": identifier,
            "error": {"code": code, "message": message},
        }

    # -- the loop ----------------------------------------------------------

    def serve(self) -> int:
        """Read line-delimited JSON requests until EOF. Returns an exit code."""
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                # A parse failure with no id cannot be correlated; the spec's
                # parse error carries null, which is still better than dying
                # and leaving the client waiting on a dead pipe.
                response = self._error(None, -32700, "parse error")
                if response is not None:
                    self._write(response)
                continue
            response = self.handle(message)
            if response is not None:
                self._write(response)
        return 0

    def _write(self, response: dict) -> None:
        self.stdout.write(json.dumps(response) + "\n")
        self.stdout.flush()


class _MethodNotFound(Exception):
    pass


def serve() -> int:
    """Entry point for ``contextcost mcp``."""
    return MCPServer().serve()
