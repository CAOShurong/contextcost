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

- [ ] GitHub Action `contextcost/action`: on pull_request, comment the
      delta ("this PR adds +41,882 tokens, 92 % of it a lockfile"). Needs
      `--json` first. This is the growth loop: every install markets the CLI.
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

- [ ] MCP server mode (`contextcost mcp`, stdio): tools `estimate(repo)`
      and `propose(repo)` so Claude/Cursor agents call it directly. Stdlib
      JSON-RPC only — keep the zero-dep core intact.
- [ ] Docs page "Use with coding agents": copy-paste configs for Claude
      Code, Cursor, Codex.

## P3 — hygiene

- [ ] `--top N`, `--fail-over <budget>` exit codes for CI gating
      (mirror repomix's `--token-budget` so migrations from it are easy).
- [ ] Windows path-separator audit of every rule in classify.py.

## Release discipline

Ship v0.4.0 when P0 + `--json` land (feature release), then v0.5.0 with the
Action + MCP. Every release: changelog entry, tag, PyPI upload, README demo
refresh if output shape changed.

## Explicitly rejected (for now)

- Tokenizer-accurate by default (breaks zero-dep promise).
- Watching/scanning modes (out of scope; this is a measurement tool).
