# contextcost

[![CI](https://github.com/CAOShurong/contextcost/actions/workflows/ci.yml/badge.svg)](https://github.com/CAOShurong/contextcost/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/contextcost/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/CAOShurong/contextcost/blob/main/LICENSE)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)](https://github.com/CAOShurong/contextcost/blob/main/pyproject.toml)

<p align="center">
  <a href="https://caoshurong.github.io/contextcost/">
    <img src="docs/assets/social-card.png" alt="contextcost — 42% of plotly.js's context budget is dead weight. uvx contextcost ." width="640">
  </a>
</p>

## 3-second summary: Input → Output → Savings

| **You give it** | **It gives you** | **Proven savings (measured, not guessed)** |
|---|---|---|
| `uvx contextcost .` (any repo, zero install) | Full token-cost breakdown + waste proposal | **plotly.js: 42% (26.8M tokens)** • **dask: 46.5% (2.0M tokens)** • **buildkit: 89.5%** |

```bash
uvx contextcost .           # measure the repo you're standing in — nothing installed
uvx contextcost plotly.js   # or any repo by name or URL
```

**In 3 seconds, on repos you already know:**

| you point it at | it costs to read | waste it can prove (measured) |
| --- | ---: | ---: |
| `plotly/plotly.js` | 63.8M tokens | **26.8M — 42%** |
| `dask/dask` | 4.3M tokens | **2.0M — 46.5%** |

`uvx contextcost plotly.js` reports that **26.8M of its 63.8M tokens (42%) are build output, minified bundles and recorded test fixtures an agent never reads usefully.** The 42% isn't a guess — the tool re-walks the repository with its proposal applied and reports the *difference* between the two measurements. ([All 17 measured repos →](docs/case-studies/2026-08-25-seven-repos.md))

**The differentiator in one line:** a packer just bundles your repo — contextcost *proves* what's waste by re-measuring the repo with the cuts applied, so the percentage is something it observed, not a guess. That is why every number above is reproducible with `bash docs/case-studies/reproduce.sh`.

## 17 real repositories, measured

One command per repository (`uvx contextcost <repo>`), full public checkouts.
"Measured saving" is what disappears when the proposed exclusions are applied
— **re-measured by walking the tree a second time**, never added up from
guesses:

| repository | tokens to read it | measured saving | share |
| --- | ---: | ---: | ---: |
| [moby/buildkit](https://github.com/moby/buildkit) | 14,600,569 | 13,070,932 | **89.5%** |
| [jesseduffield/lazygit](https://github.com/jesseduffield/lazygit) | 5,766,190 | 4,487,197 | **77.8%** |
| [sharkdp/bat](https://github.com/sharkdp/bat) | 53,715,389 | 29,977,946 | **55.8%** |
| [astral-sh/uv](https://github.com/astral-sh/uv) | 8,855,618 | 4,523,776 | 51.1% |
| [astral-sh/ruff](https://github.com/astral-sh/ruff) | 20,666,629 | 10,384,853 | 50.2% |
| [dask/dask](https://github.com/dask/dask) | 4,315,000 | 2,006,637 | 46.5% |
| [plotly/plotly.js](https://github.com/plotly/plotly.js) | 63,831,059 | 26,822,142 | 42.0% |
| [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) | 301,132 | 101,742 | 33.8% |
| [trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog) | 4,456,181 | 1,444,421 | 32.4% |
| [rclone/rclone](https://github.com/rclone/rclone) | 7,889,210 | 1,719,408 | 21.8% |
| [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 10,105,577 | 2,176,295 | 21.5% |
| [keycloak/keycloak](https://github.com/keycloak/keycloak) | 18,687,556 | 1,397,219 | 7.5% |
| [contextcost (this repo)](https://github.com/CAOShurong/contextcost) | 113,369 | 8,566 | 7.6% |
| [pydata/xarray](https://github.com/pydata/xarray) | 2,133,276 | 126,159 | 5.9% |
| [restic/restic](https://github.com/restic/restic) | 1,054,989 | 49,807 | 4.7% |
| [astropy/astropy](https://github.com/astropy/astropy) | 7,881,727 | 212,121 | 2.7% |
| [mikefarah/yq](https://github.com/mikefarah/yq) | 420,446 | 2,989 | **0.7%** |

Numbers captured with v0.5.0, whose estimate carried a ±14% measured bound;
v0.5.2 measures that same bound at **[±23%](#what-it-will-not-do)** after
recalibration showed how far the earlier ratios were off on lockfiles and
numeric data. The savings column is unaffected either way — it is the
difference of two full walks of each repository, independent of the token
estimator's accuracy.

The spread *is* the finding: there is no universal waste percentage, only your
repository's number — and a disciplined repository like yq correctly comes
back clean instead of being handed invented findings. Per-file breakdowns:
the [first seven repositories](docs/case-studies/2026-08-25-seven-repos.md),
[ten more](docs/case-studies/2026-08-26-ten-more-repos.md), and the
head-to-head against a packing tool
[here](docs/case-studies/2026-08-26-vs-packing.md). Re-run the whole table
yourself: `bash docs/case-studies/reproduce.sh`.

## The 3-second version

Real output on [plotly.js](https://github.com/plotly/plotly.js) (full public
checkout at `71a2ff7`, 2026-08-24, contextcost v0.5.0):

```console
$ contextcost plotly.js/

  63,831,059 tokens to read this repository   ±23% estimated, no tokenizer
  2717 text files · 1346 binaries not counted · 6 paths ignored

WHERE IT GOES
  test                   35,583,286  ████████████████████████████  56%
  dist                   24,598,872  ███████████████████·········  39%
  src                     1,596,194  █···························   3%

LARGEST FILES
  4,578,500  test/image/mocks/gl3d_snowden_altered.json  sampled
  4,578,201  test/image/mocks/gl3d_snowden.json  sampled
  2,593,972  dist/plotly-strict.js  sampled

SAVING
  63,831,059 → 37,008,917 tokens   42% saved
  Measured by walking the repository again with the proposal applied,
  not by subtracting what was dropped.
```

**26.8 million tokens of that repository's reading cost is compiled bundles,
recorded test fixtures, and generated files** — enough to fill a frontier
model's 200K-token context window about **134 times**, spent mostly on JSON
number matrices and minified output. An agent asked to fix a chart bug reads
none of it usefully.

And the estimate is trustworthy: re-run with `--accurate`, the real tokenizer
(cl100k_base) counts **63,363,404** tokens — the estimate above landed 0.7%
off, well inside even the recalibrated ±23% band. On data-heavy repositories
that gap is exactly the thing naive character-counting gets wrong by 30–70%.

The "42%" is not a sum of opinions. The tool proposes cuts, then *walks the
repository a second time with the proposal applied*, so the saving is the
difference between two measurements — and if a pattern had caught anything it
wasn't supposed to, you'd see the narrowing in the report. This scales down
too: [seven real repos measured](https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-25-seven-repos.md)
ran from **46.5% waste (dask) to 2.7% (astropy)**, and
[ten more](https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-26-ten-more-repos.md) stretched that to
**89.5% (moby/buildkit) down to 0.7% (yq)** — clean repos correctly get
told they're clean.

How this relates to the packing tools (repomix, gitingest, code2prompt): we
ran repomix and contextcost on the *same* plotly.js checkout —
[the comparison](https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-26-vs-packing.md). Short version:
73% of what the packer packed was provable dead weight, and the packer has no
opinion about that. Packing is step two; auditing is step one.

Point it at any repository. It measures what reading that repository costs in
tokens, works out which files are spending that budget without earning it, and
then re-measures the result — so every number it reports is one it observed.


## Install

```bash
# try it on any repo right now, nothing installed:
uvx contextcost .

# or install it:
pip install contextcost
```

No dependencies. Python 3.9+. Also works with `pipx run contextcost .`.

## Why this exists

Every coding agent (Claude Code, Cursor, Codex, Copilot) spends 20–45% of its context window on files that add no signal — measured on full public checkouts with `uvx contextcost <repo>`: **plotly.js wastes 42% (26.8M tokens, mostly dist/ bundles + numeric mock data)**, **dask wastes 46.5% (2.0M tokens, led by a single pixi.lock at 22% of the whole repo)**, while disciplined repos like **astropy come back at 2.7%**. The spread is the finding: there is no universal waste percentage, only your repository's number — and unlike packers (repomix, gitingest) that bundle blindly, contextcost *proves* the waste by re-measuring the repo with cuts applied, so every saving is observed, not guessed. Try it: `uvx contextcost .`

## What it will not do

Stated up front, because a tool that measures something is only useful if you
know where its numbers stop.

**It does not use a real tokenizer.** An exact count needs `tiktoken` — a
compiled dependency with a wheel per platform. A tool whose pitch is "find out
what your repo costs in ten seconds" cannot open with a build toolchain. So it
approximates by character class and **prints its error bound next to every
total**.

That bound is measured, not asserted. `docs/calibrate.py` encodes a corpus with
`cl100k_base` and rewrites `ERROR_BOUND` from the result, so the printed band is
the one that was actually observed — run it after any estimator change, and CI
fails if the estimator drifts past it. The current bound is **±23%**,
measured over this repository's own source plus real lockfiles and synthetic
dense/CJK samples.

Two caveats that belong here rather than in a footnote. **It is one
tokenizer** — Anthropic and most others do not publish theirs, so this is a
proxy, and "byte-pair encoders land close to each other" is doing real work in
that sentence. And **the bound covers source, configuration and lockfiles, not
packed or minified output**: a repository whose cost is dominated by
`dist/*.min.js` or a bundled artifact can sit well outside it, because those
files tokenize nothing like the corpus. For any number you intend to quote —
especially on a JavaScript project — run `--accurate` and the real tokenizer
settles it. The estimate is the triage; the re-measurement is the answer.

### CJK is counted per script, not as one thing

Charging Chinese at the Latin rate under-counts it roughly threefold, so CJK
has always been counted separately. What was wrong until recently is that it
was counted as *one* category, and the scripts are not close to each other:

| script | tokens per character |
| --- | ---: |
| Japanese kana | 0.85 |
| Korean hangul | 1.10 |
| Chinese, simplified | 1.08 |
| **Chinese, traditional** | **1.55** |

Traditional Chinese costs 44% more per character than simplified for the same
sentence, because the tokenizer has far fewer merges for it. A single constant
under-counted it by 30% — and traditional is what this project's author writes
documentation in, so the first real user would have been the one mis-billed.

Simplified and traditional share a Unicode block, so they are told apart by
looking for characters that exist only in the traditional set. Measured on
prose: 27% of traditional Han characters trip that detector, and 0% of
simplified ones.

### Numeric data dumps are their own class

Running `--accurate` against [plotly.js](https://github.com/plotly/plotly.js)
exposed the estimator's next blind spot: it read 45 M tokens where the
tokenizer said 64 M. The gap was not source code — it was recorded test
fixtures and JSON number matrices, files whose bodies are thousands of small
integers (`gl2d_parcoords_blocks.json` was under-counted by 71%). A byte-pair
encoder merges digits poorly, so the more of a file is digits, the more
tokens per character it costs — the opposite of what the code ratio assumed.

Files that are mostly digits now form a `numeric` class with its own ratio,
derived from the measured digit share. On plotly.js this took the whole-tree
error from **29.4% to 1.2%**; on astropy from 20.8% to 12.6%; h5py and pandas,
which have almost no such files, were unchanged. The class is conservative on
purpose — a file qualifies only if it already looked like code, at least 10%
of it is digits, letters are under 25%, and the digits outnumber the letters —
so ordinary number-heavy source stays on the code path.

For most of this project's life that bound read `±12%`, and it had been chosen
rather than measured — the comment beside it cited a calibration script that
did not exist. When the script was finally written, the true figure was more
than four times worse, and fixing the ratios it exposed (source code is 4.14
characters per token, not the 3.15 that had been reasoned out; dense content is
bimodal and no single ratio fits it) is what produced the table above. That is
recorded in `estimate.py` rather than quietly corrected, because a tool that
argues against unverified numbers should say when it shipped one.

**It will not decide the ambiguous cases for you.** Findings carry a
confidence: `certain` (the file says what it is, or its name is reserved by
the tool that wrote it), `likely` (a strong path convention), and `possible`.
Confidence describes the evidence for the file's category, **not universal
irrelevance**: a lockfile is machine-written with certainty and can still be
essential during a dependency upgrade. Read the proposal in the context of
the work you use the agent for.
That last tier — mostly large data files — is **never excluded automatically**,
because a large CSV is waste in a web app and is the entire subject in an
analysis repository, and nothing visible from the file system tells those
apart. Those are listed separately, with the rule's reasoning, for you to
judge. `--include-possible` moves them in.

**It never edits your repository unless you ask.** The default output is a
proposal. `--write-ignore` targets the selected consumer's native ignore file;
`--write-gitignore` remains available as an explicit compatibility option.
Write mode refuses a symbolic-link destination instead of following it beyond
the repository boundary.

**`.contextcostignore` — exclusions that belong to the measurement alone.**
The right exclusion for an AI context budget is often wrong everywhere else: a
recorded test fixture should reach an agent and stay tracked by Git.
`contextcost --emit-ignore` writes the verified proposal into this
project-local file, which contextcost reads for every consumer (even with
`--no-gitignore`) and applies **last**, so its patterns win — including `!`
re-inclusions, if you want to rescue files from a broader rule. Accepting a
saving is one command and changes nothing outside this tool's own measurement.

**It does not reproduce a live product's prompt or bill.** Consumer profiles
model documented ignore-file inputs: the set of text files eligible for
context. They do not reproduce semantic retrieval, repo maps, compression,
tool calls, product default exclusions, a proprietary tokenizer, or how much
one particular request actually sends.

**It has no users yet.** This is a new tool. The estimator's error bound is
measured against a reference tokenizer, and the reduction is measured rather
than estimated, but neither of those is the same as having been run against a
thousand repositories by people who did not write it.

## How the saving is verified

This is the part worth being suspicious of in any tool that claims one, so
here is the mechanism in full.

1. Walk the repository, respecting the selected consumer's ignore inputs.
   Attribute a cost to every eligible file.
2. Classify what looks wasteful, with quoted evidence per file.
3. Turn the findings into ignore patterns.
4. **Walk the repository again with those patterns applied.**
5. Compare the files that disappeared against the files that were proposed.
   **Those two sets must be equal.** If a pattern took anything extra — a
   `docs/` rule that also caught `docs/guide/writing.md`, or a PNG sitting
   beside a minified bundle — the patterns are narrowed to exact paths, the
   repository is walked a third time, and the report says the narrowing
   happened.

Step 5 is the one that matters. A saving computed by adding up what a tool
decided to drop cannot tell the difference between a pattern that worked and a
pattern that matched too much: the number goes up either way.

<!-- BEGIN GENERATED -->

### On an ordinary small project

The example below is generated by `docs/build_docs.py`: a small web project
with some source, a lockfile, a bundle, a vendored widget and a snapshot file.
Nobody would call it bloated.

![Where the context budget goes](https://raw.githubusercontent.com/CAOShurong/contextcost/main/docs/breakdown.png)

**41,231 tokens** to read 16 text files
(estimated, ±23% — see below for why there is no tokenizer).

| file | tokens | rule | confidence |
| --- | ---: | --- | --- |
| `package-lock.json` | 10,392 | lockfile | certain |
| `dist/bundle.min.js` | 3,582 | minified | certain |
| `vendor/legacy/widget.js` | 1,043 | vendored | likely |
| `src/generated/schema.js` | 924 | generated | certain |
| `tests/__snapshots__/app.test.js.snap` | 850 | snapshot | likely |

![What the proposal actually saves](https://raw.githubusercontent.com/CAOShurong/contextcost/main/docs/saving.png)

Excluding those leaves **23,788 tokens — a 42%
reduction**, and that number is the difference between two walks of the
repository, not a sum of what was dropped.

<!-- END GENERATED -->

## Usage

```console
contextcost                       # measure the current directory
contextcost path/to/repo          # measure somewhere else
contextcost --json                # machine-readable, schema v1, for scripts and CI
contextcost --json-schema         # print the --json key contract
contextcost --markdown            # GitHub-flavoured Markdown, for PR comments
contextcost --markdown --badge    # ...with a shields.io badge line for a README
contextcost --accurate            # exact counts via tiktoken (see below)
contextcost --include-possible    # also act on large data files
contextcost --consumer cursor     # include .cursorignore in the measurement
contextcost --consumer aider      # include .aiderignore in the measurement
contextcost --consumer repomix    # include Repomix's documented ignore files
contextcost --consumer cursor --write-ignore  # append to .cursorignore
contextcost --emit-ignore         # append to .contextcostignore (this tool only)
contextcost --write-gitignore     # explicit legacy .gitignore destination
contextcost --no-gitignore        # count files git would hide
contextcost --top 20              # more rows per section
python -m contextcost --version   # module entry point also works
```

## Exact counts: `--accurate`

The default numbers are estimates with a measured ±23% error bound (run
`python docs/calibrate.py` to see the current figure against a real tokenizer),
and for most decisions — "is this repo worth reading", "which files are the
problem" — that resolution is enough. The bound covers source, configuration and
lockfiles; repositories dominated by packed or minified output sit outside it,
so when a number will be quoted, `--accurate` counts with the real tokenizer:

```console
pip install 'contextcost[accurate]'
contextcost --accurate
```

Three things stay true when it is on:

- **Both numbers are shown.** The estimate keeps its band beside the exact
  figure, and the report says whether the estimate landed inside it. A tool
  that prints only exact numbers is asking you to forget it was ever wrong.
- **Sampling stays sampling.** Files above 2 MB are still extrapolated from a
  prefix and marked `sampled`, rather than spending seconds being precise
  about one big file.
- **Zero dependencies stays the default.** tiktoken is never imported unless
  you pass the flag; without it installed, `--accurate` exits with code 3 and
  the install hint.

Measured on this repository itself, estimate and exact agree within 1 %. On
repositories full of numeric data dumps they can diverge far more — which is
exactly the kind of thing running `--accurate` once will tell you.

See the [exact-counts case study](docs/case-studies/2026-08-26-exact-counts.md)
for a head-to-head comparison of estimated vs. tokenizer-accurate counts on 17
repositories, and why the estimate bound was recalibrated from ±14% to ±23%.

## Consumer-native ignore files

The same repository has a different eligible file set in different tools.
ContextCost therefore measures the selected consumer and writes a verified
proposal to the file that consumer actually documents:

| `--consumer` | additional inputs | `--write-ignore` destination |
| --- | --- | --- |
| `generic` | nested `.gitignore` files | `.gitignore` |
| `cursor` | `.cursorignore` | `.cursorignore` |
| `aider` | `.aiderignore` | `.aiderignore` |
| `repomix` | `.ignore`, `.repomixignore`, `.git/info/exclude` | `.repomixignore` |

All non-generic profiles also use nested `.gitignore` files unless
`--no-gitignore` is supplied. Cursor documents `.cursorignore` as the stronger
boundary for keeping files out of AI requests; Aider documents `.aiderignore`
for large repositories; Repomix documents `.repomixignore` in the same syntax
as `.gitignore`. The exact scope and the limitations of each model are recorded
in [consumer profiles](https://github.com/CAOShurong/contextcost/blob/main/docs/consumer-profiles.md).

This distinction matters for tracked files. Git itself says that
`.gitignore` applies to intentionally untracked files and does not stop
tracking a file already in the index. A consumer may still use that pattern as
its own context filter, but writing `.cursorignore`, `.aiderignore`, or
`.repomixignore` expresses the intended AI-tool boundary directly.

The exit code is `1` when an actionable context-waste candidate was found and
`0` when it was not, so this works as a CI check:

```yaml
- name: Keep the context budget honest
  run: pipx run contextcost --quiet
```

**That exit code will bite you under `set -e`.** "Found something" is not an
error, but `bash -e` cannot tell the difference and will abort your script on
it. This tool's own CI failed on exactly that the first time it ran. When you
want the output rather than the verdict, say so:

```bash
contextcost --json > cost.json || true
```

To gate on total size rather than on removable waste, `--fail-over BUDGET`
exits `4` when the measured total exceeds BUDGET tokens — with `--accurate`
that is the exact count, otherwise the estimate. Exit code `4` is distinct
from `1` on purpose: waste (`1`) is a cleanup task, over-budget (`4`) is a
scoping decision.

```yaml
- name: The whole repo must fit an agent's window
  run: pipx run contextcost --fail-over 200000 --quiet
```

## In a pull request

`--delta` measures what a change does to the context budget: it walks a base
checkout and the head tree per file, compares them by path, and classifies the
head tree so "+32k of this is a lockfile" is a measurement, not a guess from
filenames. The bundled Action posts (and keeps updated) that report as a PR
comment:

```yaml
# .github/workflows/contextcost.yml in any repository
name: contextcost
on: pull_request
jobs:
  delta:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: CAOShurong/contextcost/action@main
        with:
          # optional: fail the check if the PR adds more than this many tokens
          # to what an agent reads (e.g. 1000000)
          max-added: 1000000
```

Or run it by hand. The base can be a second checkout of the same repository —
for example the PR's merge base next to the working tree:

```bash
contextcost . --delta ../repo-at-merge-base --markdown
```

— or simply a git revision of the repository being measured, which is
exported automatically (no second clone, no worktree):

```bash
contextcost . --delta main            # uncommitted changes vs the branch
contextcost . --delta HEAD~1          # what the last commit did to the budget
contextcost repo/ --delta v4.0.0      # a tagged release vs its checkout
```

```
## contextcost — context delta

**53,834 → 95,631 tokens** (+41,797, estimated ±23%).

| rule | tokens | share of repo |
| --- | --- | --- |
| **lockfile** | +32,232 | 34% |
| unclassified *(real work?)* | +9,565 | 10% |
```

## As a library

```python
from contextcost.reduce import reduce_repository

result = reduce_repository("path/to/repo", consumer="aider")
print(result.before, "->", result.after)   # both measured
print(result.patterns)                     # what to add to .aiderignore
print(result.deferred)                     # what it refused to decide
```

`walk_repository`, `classify` and `reduce_repository` are all usable
separately, and every dataclass has `as_dict()`.

## As an MCP server

Coding agents that speak [MCP](https://modelcontextprotocol.io) can call this
tool instead of shelling out — same measurement, same schema, one tool call:

```bash
contextcost mcp    # line-delimited JSON-RPC on stdio
```

Two tools are served. `estimate(repo)` returns the full `--json` payload;
`propose(repo)` returns the measured exclusion proposal plus a ready-to-paste
ignore block. Stdio transport, stdlib-only JSON-RPC 2.0 — no SDK dependency:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "estimate", "arguments": {"repo": "/path/to/repo"}}}
```

Claude Code, Cursor and Codex CLI each take a two-line config — copy-paste
blocks live in [docs/coding-agents.md](https://github.com/CAOShurong/contextcost/blob/main/docs/coding-agents.md). Any MCP
client then gets "what does this repo cost and what is wasting it" as a
tool call beside the model.

## Development

```bash
python -m pytest -q                      # 198 tests, no configuration needed
python -m ruff check src tests docs
python docs/build_docs.py                # regenerate the figures and README
python docs/build_docs.py --check        # CI fails if they are stale
```

The figures above are generated from a real run against a generated example
repository, and CI fails if the README's numbers drift from what the code
actually produces.

## Verify a release

Starting with v0.2.0, every GitHub release includes a `SHA256SUMS` manifest and
GitHub build-provenance attestations for the wheel and source distribution:

```bash
sha256sum --check SHA256SUMS
gh attestation verify contextcost-0.2.0-py3-none-any.whl \
  --repo CAOShurong/contextcost
```

The GitHub and PyPI files are built once in the same release workflow. Verify
the downloaded bytes rather than treating a tag or a green job as proof of the
artifact you installed.

## Share it

If the number surprised you, it will probably surprise whoever maintains the
next repository you point this at. The
[landing page](https://caoshurong.github.io/contextcost/) renders a proper
preview card when pasted into Slack, Discord, X, or a chat window — no extra
work needed, just paste the link.

Questions, methodology debates, and "this number looks wrong" reports are
welcome in [Discussions](https://github.com/CAOShurong/contextcost/discussions) —
if a saving looks off, paste `--accurate --json` output and it becomes a
concrete, checkable claim.

## Licence

MIT.
