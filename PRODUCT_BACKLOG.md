# PRODUCT BACKLOG — contextcost

Owned by the product-agent cron track. One requirement gates everything:
**really useful, really solves a pain point, promising.** No vanity features.

## Mission

Make contextcost the default answer to "what will this repo cost me in
context, and what can I safely drop?" — the measure→propose→re-measure
methodology is the moat; everything below strengthens or distributes it.

## P0 — credibility & correctness

- [done rev 4] Estimator blind spot found by `--accurate` on plotly.js: numeric data
      dumps (JSON number matrices, locale tables) are classified as `code`
      (4.14 chars/token) but really cost ~2.8 chars/token — per-file drift up
      to 74%, repo-wide drift 29%. Add a `numeric` content class (digit share
      heuristic), calibrate it with docs/calibrate.py against cl100k_base,
      and re-measure ERROR_BOUND. Evidence: estimate 45.3 M vs exact
      64.2 M tokens on plotly.js; worst files gl2d_parcoords_blocks.json
      (71.6%), lib/locales/*.js (~70%).

- [done rev 1] `--accurate` mode: exact counts via tiktoken (optional extra
      `contextcost[accurate]`); estimate kept as default and shown beside the
      exact number. NOTE discovered: numeric data dumps (JSON matrices,
      locale tables) drift up to 70% — estimator blind spot, needs a
      `numeric` class + recalibration (see new P0 entry).
- [done rev 5] `.contextcostignore` file: project-local ignores with comments,
      merged with .gitignore semantics. `--emit-ignore` writes the proposal
      as this format so accepting a saving is one line.
      (Shipped e6e6541: read for every consumer incl. --no-gitignore, applied
      last so patterns win; 4 CLI tests + 4 ignorefile tests; verified on a
      scratch repo and git check-ignore.)

## P1 — distribution

- [done rev 8] GitHub Action `contextcost/action`: on pull_request, comment the
      delta ("this PR adds +41,882 tokens, 92 % of it a lockfile"). Needs
      `--json` first. This is the growth loop: every install markets the CLI.
      (Shipped e09d367: core `delta.py` (per-file compare + head-tree
      attribution) + `--delta BASE` printing through `--markdown`/`--json`;
      composite `action.yml` posts/updates one marked PR comment; 11 new
      tests = 150 total; verified on two checkouts of this repo with a
      synthetic lockfile commit, +41,797 tokens split 32k lockfile / 9.5k
      unclassified.)
- [done rev 6] `--json` machine output (stable schema, versioned) — prerequisite for
      the Action and for editor integrations.
      (Shipped 3532dbc: `"schema": 1` in every payload, contract as data in
      json_schema.CONTRACT walked against real output by tests, single
      build_payload() assembly path, `--json-schema` prints the contract;
      6 new tests, verified as an Action-style consumer on plotly.js.)
- [done rev 7] `--markdown` report suited for README badges / PR comments.
      (Shipped db9e959: `src/contextcost/markdown.py` second renderer — pipe
      tables, blockquoted saving, fenced gitignore block, `--badge` prepends
      a shields.io badge line; honesty rules carried over (bound, measured
      saving, deferred as question); pipes in paths escaped; 10 new tests;
      verified on this repo (63k tokens + badge) and plotly.js (63.2M).)

## P2 — agent-native surface

- [done rev 9] MCP server mode (`contextcost mcp`, stdio): tools
      `estimate(repo)` and `propose(repo)` so Claude/Cursor agents call it
      directly. Stdlib JSON-RPC only — keep the zero-dep core intact.
      (Shipped aefd046: mcp_server.py ~150 lines stdlib-only, minimal
      protocol initialize/ping/tools.list/tools.call, errors-as-data; 18
      tests; live-verified on plotly.js stdio session — estimate
      63.83 M tokens, propose 26.8 M saved / 42 %, bad path −32603.)
- [done rev 10] Docs page "Use with coding agents": copy-paste configs for Claude
      Code, Cursor, Codex.
      (Shipped 18d6987: docs/coding-agents.md — `claude mcp add` command +
      committed .mcp.json, .cursor/mcp.json, `codex mcp add` +
      ~/.codex/config.toml; formats verified against current client docs;
      ready-to-use prompt + honest-notes section; linked from README MCP
      section. 176 tests green, live plotly.js stdio re-verified
      63.83M tokens / saved 26.8M = 42%.)

## P3 — hygiene

- [done rev 11] `--top N`, `--fail-over <budget>` exit codes for CI gating
      (mirror repomix's `--token-budget` so migrations from it are easy).
      NOTE: `--top N` already existed since v0.1; this item was really about
      `--fail-over`. (Shipped: exit 4 = over budget, distinct from 1 = waste,
      exact total under --accurate else estimate with ±14% band in message;
      negative budget is usage error 2; 5 new tests = 181; verified live on
      this repo — 75,546 tokens passes 500k, fails 1k — and plotly.js —
      fails 1M, passes 100M.)
- [ ] Windows path-separator audit of every rule in classify.py.

## Release discipline

Ship v0.4.0 when P0 + `--json` land (feature release), then v0.5.0 with the
Action + MCP. Every release: changelog entry, tag, PyPI upload, README demo
refresh if output shape changed.

## Explicitly rejected (for now)

- Tokenizer-accurate by default (breaks zero-dep promise).
- Watching/scanning modes (out of scope; this is a measurement tool).
