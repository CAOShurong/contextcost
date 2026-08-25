# Use contextcost with coding agents

`contextcost` ships a small [MCP](https://modelcontextprotocol.io) server so
your coding agent can ask "what does this repository cost to read, and what
is wasting it?" as a tool call instead of shelling out and parsing text.

Two tools are exposed:

- **`estimate(repo)`** — the full measurement: total tokens with an honest
  error bound, cost by directory and extension, largest files, and the
  measured saving available from excluding waste.
- **`propose(repo)`** — the exclusion proposal: ignore patterns with their
  *measured* saving (the repo is re-walked with them applied, not
  subtracted), plus findings deliberately left for a human to decide.

The server is line-delimited JSON-RPC 2.0 over stdio, implemented in stdlib
only — installing it adds no dependencies beyond `contextcost` itself:

```bash
pip install contextcost        # that is the whole install
contextcost mcp                # what each client below launches
```

Copy the block for your agent below. After connecting, try asking:

> Estimate the context cost of this repo, then propose what we can safely
> exclude before you start reading files.

---

## Claude Code

One command, run once from your project root (use `--scope user` instead to
make it available in every project):

```bash
claude mcp add contextcost --scope local -- contextcost mcp
```

Or, checked into the repo for teammates (`.mcp.json` at the project root):

```json
{
  "mcpServers": {
    "contextcost": {
      "command": "contextcost",
      "args": ["mcp"]
    }
  }
}
```

## Cursor

Add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) — or
paste it via **Cursor Settings → MCP → Add new MCP server**:

```json
{
  "mcpServers": {
    "contextcost": {
      "command": "contextcost",
      "args": ["mcp"]
    }
  }
}
```

## Codex CLI

One command:

```bash
codex mcp add contextcost -- contextcost mcp
```

Or edit `~/.codex/config.toml` directly:

```toml
[mcp_servers.contextcost]
command = "contextcost"
args = ["mcp"]
```

---

## Notes

- The server never imports tiktoken; `estimate` reports what the zero-dep
  estimator says *with its error bound* — the honest number, not a
  confident one. For exact counts use the CLI's `--accurate`
  (`pip install "contextcost[accurate]"`).
- Tool errors come back as data (`-32603 NotADirectoryError`), so an agent
  that mistypes a path sees the mistake and can retry instead of hanging.
- Protocol coverage is intentionally minimal (`initialize`, `ping`,
  `tools/list`, `tools/call`); unknown methods get `-32601`, which lets any
  MCP client degrade gracefully.
- Windows note: if the client cannot find `contextcost`, give the absolute
  path to the executable in place of the bare command name.
