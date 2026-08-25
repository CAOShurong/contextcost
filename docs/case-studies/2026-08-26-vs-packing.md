# We ran repomix and contextcost on the same repo. One packs, one audits. You probably want both — but only one tells you what to cut.

*2026-08-26. Every number below is real output from a single checkout of
[plotly.js](https://github.com/plotly/plotly.js) at `71a2ff7`
([contextcost](https://github.com/CAOShurong/contextcost) v0.5.0,
`npx repomix@latest`). Reproduce with: `uvx contextcost <repo>`.*

## The short version

If you feed a repository to an AI agent, two different questions matter:

1. **How do I hand the repo to the model?** → that's packing (repomix,
   gitingest, code2prompt). Solved problem.
2. **Why does it cost 39 million tokens, and how much of that is junk?** →
   nobody answers this. That's what contextcost is for.

We ran both on the same full plotly.js checkout:

| | repomix (`--style json`) | contextcost |
| --- | ---: | ---: |
| What it did | packed all **2,595 text files** into one bundle | walked 2,717 eligible files and proposed cuts |
| Token count | **39,150,382** exact (via `gpt-tokenizer`, o200k_base) | **63,831,059** estimate ±14% (`--accurate`: 63.4M, cl100k_base) |
| After its own proposal | — (packing doesn't propose) | **37,008,917** tokens |
| Saving | none reported | **26,822,142 tokens = 42%**, *measured* by re-walking with the proposal applied |

Two things worth pausing on.

## 1. Packing tools will happily pack 73% dead weight

Of the characters repomix packed into that 89 MB JSON bundle, **73% came from
just two directory classes**: `dist/` build output and
`test/image/mocks/*.json` recorded fixtures. The six largest files in the pack
are JSON number matrices — the biggest is a 6.3 MB snow-scene mock. An agent
asked to fix a chart bug reads none of them usefully, but a packing tool has
no opinion about them; its job is to include, not to judge. Repomix's own
docs point you at `--include`/`--ignore` patterns for exactly this — but
figuring out *which* patterns, and proving they don't overmatch, is the audit
problem. That's the gap.

## 2. The counts differ by 24M tokens — and both are honest

Repomix says the repo is ~39M tokens. Contextcost estimates reading the whole
tree costs ~64M. Both numbers are correct because they measure different
sets: repomix applies its default ignore list before counting, so much of the
waste never enters its bundle — which is quietly an admission that a large
share of a raw tree shouldn't be there. Contextcost walks everything your
agent could actually reach (grep, indexing, retrieval), then proves what's
safe to drop.

The deeper difference is epistemic. A token count is a number. Contextcost's
saving figure is not computed by adding up "what we decided to drop" — the
tool turns findings into ignore patterns, **walks the repository a second time
with those patterns applied**, and verifies the files that disappeared are
exactly the ones proposed. If a pattern had caught anything extra, you'd see
the narrowing in the report. On plotly.js the 42% saving is the difference of
two measurements of the same tree, not arithmetic on guesses.

And the estimator is calibrated, not vibes: against the real tokenizer
(cl100k_base) the whole-repo estimate landed within **0.7%** of exact — well
inside the ±14% bound it prints next to every total. On data-heavy repos like
this one, naive character-counting misses by 30–70%; a `numeric` file class
is what keeps this tool inside its stated error bar.

## Try it

```bash
uvx contextcost .          # measure + propose + re-measure, no install
```

It doesn't pack anything. Run it once, accept the proposal into
`.contextcostignore` or your consumer's native ignore file
(`contextcost . --write-ignore`), then gate regressions in CI
(`contextcost . --fail-over <budget>` or the
[GitHub Action](https://github.com/CAOShurong/contextcost#in-a-pull-request)).
Your packing tool keeps doing what it does — just on a tree that isn't
mostly dead weight.

## Methodology notes

- Single checkout, both tools run the same hour, same machine.
- contextcost figures: `contextcost <repo> --json` (estimate tier) and
  `--consumer repomix` cross-check (identical saving, since repomix's ignore
  inputs are already respected).
- repomix figures: `npx repomix@latest --style json` pack summary line
  ("Total Tokens: 39,150,382"); per-file character shares computed from the
  bundle itself. Character share is used as a proxy for token share within
  one pack — valid here because the waste classes (JSON matrices, minified
  JS) sit near the extremes either way.
- The 73% waste-share computation is conservative: only `dist/` and
  `test/image/mocks/`; adding locale data tables pushes it higher.
- Full seven-repo measurements (46.5% waste on dask down to 2.7% on astropy):
  [the case study](2026-08-25-seven-repos.md).

---

*contextcost is free, MIT, runs entirely locally, zero dependencies.*
*https://github.com/CAOShurong/contextcost*
