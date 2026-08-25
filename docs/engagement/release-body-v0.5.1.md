# contextcost v0.5.1

**Measure what a repository costs an AI coding agent to read — and prove how
much of it is waste by measuring again.**

```bash
uvx contextcost .          # no install, no config, results in seconds
```

## What it does

1. **Measures** the token cost of every file an agent could read (estimate
   with a published ±14% error bound; `--accurate` gives exact cl100k_base
   counts).
2. **Proposes** cuts — only where the filesystem itself proves a file isn't
   hand-written work: lockfiles, minified bundles, vendored deps, generated
   code, recorded fixtures.
3. **Re-measures** with the proposal applied, so the saving it reports is an
   observed difference between two walks of your repository — never a sum of
   guesses.

## Real numbers from real repositories

| Repository | Tokens to read | Measured saving | Waste |
| --- | ---: | ---: | ---: |
| moby/buildkit | 14.6M | 13.1M | **89.5%** |
| jesseduffield/lazygit | 5.8M | 4.5M | 77.8% |
| plotly.js | 63.8M | 26.8M | **42.0%** |
| sharkdp/bat | 53.7M | 30.0M | 55.8% |
| astral-sh/ruff | 20.7M | 10.4M | 50.2% |
| astropy | 7.9M | 212K | 2.7% |
| mikefarah/yq | 420K | 3.0K | **0.7%** |

The spread *is* the finding: there is no universal waste percentage — only
your repository's number. Full case studies with per-commit reproduction
commands:

- [Seven repos measured](https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-25-seven-repos.md)
- [Ten more repos](https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-26-ten-more-repos.md)
- [Head-to-head vs repomix on the same checkout](https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-26-vs-packing.md)

## Also in this release

- `contextcost mcp` — MCP server mode so Claude Code / Cursor / Codex can ask
  "what does this repo cost and what's wasting it" as a tool call
  ([copy-paste configs](https://github.com/CAOShurong/contextcost/blob/main/docs/coding-agents.md))
- GitHub Action that posts the context delta of every pull request
- `--delta main` / `--delta v4.0.0` — measure a change's context cost against
  any git revision without a second clone
- `--fail-over BUDGET` for CI gating (exit 4 when over budget)
- `.contextcostignore` — measurement-only exclusions that don't touch git

MIT, Python 3.9+, zero dependencies.
Questions and "this number looks wrong" reports:
[Discussions](https://github.com/CAOShurong/contextcost/discussions) — paste
`--accurate --json` output and it becomes a checkable claim.
