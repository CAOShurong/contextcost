# contextcost v0.5.0

**Measure what a repository costs an AI coding agent to read — and prove how
much of it is waste by measuring again.**

```bash
uvx contextcost .          # no install, no config, results in seconds
```

## Highlights

1. **Measures** the token cost of every file an agent could read (estimate
   with a published ±14% error bound; `--accurate` gives exact cl100k_base
   counts).
2. **Proposes** cuts — only where the filesystem itself proves a file isn't
   hand-written work: lockfiles, minified bundles, vendored deps, generated
   code, recorded fixtures.
3. **Re-measures** with the proposal applied — the saving it reports is an
   observed difference between two walks of your repository, never a sum of
   guesses.

## New in v0.5.0

- **GitHub Action** (`CAOShurong/contextcost/action`): posts (and keeps
  updated) a per-PR comment measuring what a pull request does to the
  repository's context budget — "+41,797 tokens, 92% of it a lockfile" as a
  measurement, not a guess from filenames.
- **MCP server mode**: `contextcost mcp` serves `estimate(repo)` and
  `propose(repo)` over stdio JSON-RPC so Claude Code, Cursor and Codex can
  call it directly ([copy-paste configs](https://github.com/CAOShurong/contextcost/blob/main/docs/coding-agents.md)).
- `--delta BASE`: measure a change's context cost against any git revision —
  `contextcost . --delta main`, or against a tagged release, no second clone.
- `--fail-over BUDGET`: CI gate that exits 4 when the measured total exceeds
  BUDGET tokens.

## Real numbers from real repositories

| Repository | Tokens to read | Measured saving | Waste |
| --- | ---: | ---: | ---: |
| moby/buildkit | 14.6M | 13.1M | **89.5%** |
| jesseduffield/lazygit | 5.8M | 4.5M | 77.8% |
| plotly.js | 63.8M | 26.8M | **42.0%** |
| astropy | 7.9M | 212K | 2.7% |
| mikefarah/yq | 420K | 3.0K | **0.7%** |

The spread *is* the finding: there is no universal waste percentage — only
your repository's number. Full case studies with per-commit reproduction:
[docs/case-studies](https://github.com/CAOShurong/contextcost/tree/main/docs/case-studies).

MIT, Python 3.9+, zero dependencies.
Questions: [Discussions](https://github.com/CAOShurong/contextcost/discussions).
