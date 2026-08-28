# I measured 7 well-known open-source repos: up to 42% of their tokens are waste an AI agent pays to read

*Every number in this post is real output from [contextcost](https://github.com/CAOShurong/contextcost)
v0.5.0 run on full public checkouts. Reproduce any of it with:
`uvx contextcost <repo>`.*

When you point an AI coding agent (Claude Code, Cursor, Copilot Workspace) at a
repository, the agent reads that repository as **tokens**. Not all of those
tokens are code the agent needs. Lockfiles, build output, minified bundles,
generated files, and dense machine data are all billed to the context window
the same as your source — and unlike your source, they usually tell the model
nothing.

I wanted a real answer to "how much of a repo's context cost is waste?", so I
ran contextcost over seven well-known repositories and let it propose cuts.
contextcost works in three steps:

1. **Measure** what the repository costs to read (estimate with a published
   error bound; `--accurate` gives exact tokenizer counts).
2. **Propose** what to drop — only patterns where the file system itself
   proves the file is not hand-written work.
3. **Re-measure** with the proposal applied, so the saving is a *measurement*
   (two walks), not arithmetic on guesses.

## The results

| Repository | Files | Tokens to read | After proposal | Saved | Share |
| --- | ---: | ---: | ---: | ---: | ---: |
| plotly.js | 4,063 | 63,831,059 | 37,008,917 | **26,822,142** | **42.0%** |
| dask | 623 | 4,315,000 | 2,308,363 | 2,006,637 | 46.5% |
| pandas | 2,507 | 10,105,577 | 7,929,282 | 2,176,295 | 21.5% |
| keycloak | 13,349 | 18,687,556 | 17,290,337 | 1,397,219 | 7.5% |
| rclone | 2,606 | 7,889,210 | 6,169,802 | 1,719,408 | 21.8% |
| astropy | 1,964 | 7,881,727 | 7,669,606 | 212,121 | 2.7% |
| contextcost itself | 54 | 161,453 | 85,663 | 75,790 | 46.9% |

(All figures from `contextcost <repo> --json`, estimate tier, ±14% measured
error bound. The saving column is *measured* by re-walking each repository
with the proposal applied.)

## What the waste actually is

**plotly.js — 42%, 26.8M tokens.** The single biggest class is build output:
22 files under `dist/` worth **17.4M tokens**, plus 5.9M tokens of minified
bundles. An agent asked to fix a chart bug does not need to read the compiled
bundle of every chart type. Also present: 3.0M tokens of dense numeric mock
data (`test/image/mocks/*.json` — single files up to 4.58M tokens, i.e. one
JSON file ≈ 70 novels).

**dask — 46.5%, 2.0M tokens.** A textbook case: `dask/pixi.lock`
(931,942 tokens — one lockfile is 22% of the entire repo's context cost) plus
383K tokens of logo SVGs that are pure coordinate dumps.

**pandas — 21.5%, 2.2M tokens.** `pixi.lock` again (1.13M tokens), then test
fixture CSVs like `DEMO_G.csv` (397K tokens) — data files an agent will never
reason about usefully.

**rclone — 21.8%, 1.7M tokens.** Here it's generated documentation and code:
112 generated files worth 1.65M tokens.

**astropy — 2.7%.** Worth stating honestly: a mature repo with disciplined
hygiene has almost nothing to cut. The tool found 212K tokens of dense data
files, and correctly did *not* propose removing them automatically — large
data is flagged as "your decision", because the file system cannot prove a
data file is useless.

**contextcost itself — 46.9% at the time of writing, the highest share of all
seven.** A young repo with a single `uv.lock` (75,790 tokens) that is nearly half of its own
context cost. Included deliberately: the tool flags its authors' repository
just as bluntly as anyone else's.

## Why this matters more than it looks

A typical agent session doesn't read the whole repo at once — but every file
it greps, chunks, or indexes competes for the same window, and retrieval tools
routinely pull these junk files into context anyway. If 20–45% of what your
agent reads is lockfiles and minified output, you are paying for that in
latency, money, and attention the model doesn't spend on your actual problem.

The fix is boring and permanent: add the proposed patterns to `.gitignore`
(or a `.contextcostignore` if other tools do need those files), then gate it:

```
# one-time: accept the proposal and confirm the saving
contextcost . --write-ignore

# forever after: fail CI when the budget creeps back
contextcost . --fail-over 8000000
```

## Try it on your own repo

```bash
uvx contextcost .
```

No install, no config, no tokenizer dependency. It prints what the repo costs,
what it proposes to cut, and — the part I'd ask you to check — it *re-measures*
after the proposal so the saving number is something it actually observed.

Methodology notes, for the skeptical: estimates carry a ±14% error bound
(measured against cl100k_base during calibration; a `numeric` content class
keeps data-heavy repos inside it). Savings are differences of two walks, so
they are exact at the file level regardless. Everything above is reproducible
from the linked repository — and the table itself with one command:
`bash docs/case-studies/reproduce.sh` re-measures all seven checkouts and
prints the same columns (numbers drift by a fraction of a percent as the
upstream repositories evolve; the saved-token figures have matched on every
re-run).

## Postscript: this repository's own number is now different

An honest postscript, added 2026-08-26. The paragraph above claimed "the fix
was one line in `.gitignore`" — **and that line had never been committed.**
Re-running contextcost on this repository found `uv.lock` grown to 116,440
tokens: 51% of the entire tree, 226,143 tokens before any cut, with a measured
proposal of **55%.** A tool whose pitch is "every number it reports is one it
observed" had published a claim about itself that a fresh clone would not
reproduce.

The line is committed now. The same measurement on the fixed tree:
113,369 tokens to read this repository, proposal 104,803, saving 8,566 —
**7.6%**. The README's hero table carries the corrected figure; this post's
table above stays as first published, because rewriting a published result
would be its own kind of dishonesty. (The number shifted again as the repo
grew — `docs/calibration-samples/` and `docs/index.html` are now flagged as
waste. This is expected: a living repository's waste profile changes over time.)

---

*contextcost is free, open source (MIT), and runs entirely locally.*
*Repository: https://github.com/CAOShurong/contextcost*
