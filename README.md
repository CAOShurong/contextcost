# contextcost

**What does this repository cost an AI coding agent to read, and what is
wasting that budget?**

Point it at a repository. It measures what reading that repository costs in
tokens, works out which files are spending that budget without earning it, and
then — the part nobody else does — **applies its own proposal and measures the
result again**, so the saving it reports is a difference between two
measurements rather than a sum of its own opinions.

```console
$ contextcost .

contextcost  ~/work/example

  74,318 tokens to read this repository   ±12% estimated, no tokenizer
  12 text files · 1 binary not counted · 3 paths ignored

WHERE IT GOES
  (root)                    41,882  ████████████████████████████  56%
  vendor                    12,704  ████████·····················  17%
  src                        9,331  ██████·······················  13%

WHAT IS NOT WORTH READING
  certain  lockfile         38,905  1 file
             38,905  package-lock.json
                      package-lock.json is written by a package manager
  likely   vendored         12,704  2 files
             7,110  vendor/legacy/helpers.js
                      inside a directory named vendor/

SAVING
  74,318 → 15,033 tokens   80% saved
  Measured by walking the repository again with the proposal applied,
  not by subtracting what was dropped.

  Add to .gitignore (or run with --write-gitignore):
    /package-lock.json
    /vendor/
```

## Install

```bash
pip install contextcost
```

No dependencies. Python 3.9+.

## Why this exists

Every coding agent — Claude Code, Cursor, Codex, Copilot Workspace, an
in-house one — spends part of its context window just working out what is in
your repository. That budget is finite and it is charged per token, and most
repositories quietly spend a large fraction of it on files no human and no
agent will ever read: lockfiles, minified bundles, vendored dependencies,
snapshot fixtures, generated clients.

The first repository this was ever pointed at had **55% of its entire context
cost in a single generated CSV**.

There are good tools for *packing* a repository into a prompt — repomix,
gitingest, code2prompt, files-to-prompt. This is not one of them. Packing is a
solved and crowded problem. Auditing what the packing will cost you, and
reducing it with evidence, was not.

## What it will not do

Stated up front, because a tool that measures something is only useful if you
know where its numbers stop.

**It does not use a real tokenizer.** An exact count needs `tiktoken` — a
compiled dependency with a wheel per platform. A tool whose pitch is "find out
what your repo costs in ten seconds" cannot open with a build toolchain. So it
approximates by character class and **prints its error bound next to every
total**.

That bound is measured, not asserted. `docs/calibrate.py` encodes a corpus with
`cl100k_base` and compares:

| | error vs. a real tokenizer |
| --- | ---: |
| median file | 2.6% |
| 95th percentile | 10.0% |
| whole corpus (what a repository total looks like) | 7.6% |

The bound the tool actually prints is **±12%**: the measured 95th percentile
plus 20% headroom. The corpus is this repository's own files, so every commit
changes it slightly, and a bound sitting exactly on the measurement would turn
ordinary editing into a red build — where the tempting fix is to widen the
bound, which is how a number stops meaning anything.

Two caveats that belong here rather than in a footnote. **It is one
tokenizer** — Anthropic and most others do not publish theirs, so this is a
proxy, and "byte-pair encoders land close to each other" is doing real work in
that sentence. And **the corpus is this repository's own files** plus synthetic
dense samples; it is real code and real prose, but it is not yours.

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
That last tier — mostly large data files — is **never excluded automatically**,
because a large CSV is waste in a web app and is the entire subject in an
analysis repository, and nothing visible from the file system tells those
apart. Those are listed separately, with the rule's reasoning, for you to
judge. `--include-possible` moves them in.

**It never edits your repository unless you ask.** The default output is a
proposal. `--write-gitignore` appends it and tells you exactly what it wrote.

**It has no users yet.** This is a new tool. The estimator's error bound is
measured against a reference tokenizer, and the reduction is measured rather
than estimated, but neither of those is the same as having been run against a
thousand repositories by people who did not write it.

## How the saving is verified

This is the part worth being suspicious of in any tool that claims one, so
here is the mechanism in full.

1. Walk the repository, respecting `.gitignore`. Attribute a cost to every
   file.
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

![Where the context budget goes](docs/breakdown.png)

**37,603 tokens** to read 16 text files
(estimated, ±12% — see below for why there is no tokenizer).

| file | tokens | rule | confidence |
| --- | ---: | --- | --- |
| `package-lock.json` | 6,764 | lockfile | certain |
| `dist/bundle.min.js` | 3,582 | minified | certain |
| `vendor/legacy/widget.js` | 1,043 | vendored | likely |
| `src/generated/schema.js` | 924 | generated | certain |
| `tests/__snapshots__/app.test.js.snap` | 850 | snapshot | likely |

![What the proposal actually saves](docs/saving.png)

Excluding those leaves **23,788 tokens — a 37%
reduction**, and that number is the difference between two walks of the
repository, not a sum of what was dropped.

<!-- END GENERATED -->

## Usage

```console
contextcost                       # measure the current directory
contextcost path/to/repo          # measure somewhere else
contextcost --json                # machine-readable, for scripts and CI
contextcost --include-possible    # also act on large data files
contextcost --write-gitignore     # append the proposal to .gitignore
contextcost --no-gitignore        # count files git would hide
contextcost --top 20              # more rows per section
```

The exit code is `1` when something confidently wasteful was found and `0`
when it was not, so this works as a CI check:

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

## As a library

```python
from contextcost.reduce import reduce_repository

result = reduce_repository("path/to/repo")
print(result.before, "->", result.after)   # both measured
print(result.patterns)                     # what to add to .gitignore
print(result.deferred)                     # what it refused to decide
```

`walk_repository`, `classify` and `reduce_repository` are all usable
separately, and every dataclass has `as_dict()`.

## Development

```bash
python -m pytest -q                      # 83 tests, no configuration needed
python -m ruff check src tests docs
python docs/build_docs.py                # regenerate the figures and README
python docs/build_docs.py --check        # CI fails if they are stale
```

The figures above are generated from a real run against a generated example
repository, and CI fails if the README's numbers drift from what the code
actually produces.

## Licence

MIT.
