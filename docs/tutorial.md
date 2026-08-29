# Tutorial: find the wasted context in any repo in 60 seconds

This is the shortest path from "I've never run contextcost" to "my repo's
context budget is measured, cut, and guarded in CI." Every number below is
real output from running contextcost on the contextcost repository itself.

## 1. Run it — nothing to install

```bash
uvx contextcost .
```

`uvx` downloads a throwaway copy of the tool and runs it; it touches nothing
in your project. (If you prefer, `pip install contextcost` then `contextcost .`.)
Point it at any checkout — `.` for the directory you're standing in, or a path
or URL to any other repo.

On the contextcost repo, the output looks like this:

```console
$ uvx contextcost .

contextcost   E:\Codex\Projects\caoshurong\contextcost

  113,512 tokens to read this repository   ±23% estimated, no tokenizer
  65 text files · 3 binaries not counted · 8 paths ignored

WHERE IT GOES
  src                       34,491  ████████████████████████████  30%
  docs                      28,656  ███████████████████████·····  25%
  tests                     25,713  █████████████████████·······  23%
  (root)                    20,600  █████████████████···········  18%
  .github                    3,243  ███·························   3%
  scripts                      809  █···························   1%

LARGEST FILES
      6,629  README.md
      6,448  CHANGELOG.md
      4,415  src/contextcost/cli.py
      4,283  PRODUCT_BACKLOG.md
      4,248  src/contextcost/estimate.py

CANDIDATE CONTEXT WASTE
  certain  lockfile          6,117  3 files
          3,207  docs/calibration-samples/uv.lock
                 uv.lock is written by a package manager
          1,483  docs/calibration-samples/Cargo.lock
                 cargo.lock is written by a package manager
          1,427  docs/calibration-samples/package-lock.json
                 package-lock.json is written by a package manager
  likely   dense             2,449  1 file
          2,449  docs/index.html
                 content is long unbroken runs of characters

SAVING
  113,512 → 104,946 tokens   8% saved
  Measured by walking the repository again with the proposal applied,
  not by subtracting what was dropped.

  Add to .gitignore (or run with --write-gitignore):
    /docs/calibration-samples/
    /docs/index.html

NEXT STEPS
  1. Accept the proposal above: re-run with --write-gitignore, then re-measure to confirm the saving.
  2. Gate it in CI so it stays saved: contextcost --fail-over <budget>  (exit 4 when over)
  3. Show it off: contextcost . --markdown --badge  -- paste into your README
```

## 2. Read the output

- **`113,512 tokens to read this repository ±23% estimated, no tokenizer`** —
  the headline cost, with its error bound printed *next to* it (no tokenizer
  dependency, so it estimates and tells you by how much).
- **`WHERE IT GOES`** — which directories dominate the cost. For a repo this
  size, `src`/`docs`/`tests` being the top three is exactly what you'd hope.
- **`CANDIDATE CONTEXT WASTE`** — files the tool proposes to drop, with the
  *reason* per file. Here it is three lockfiles under
  `docs/calibration-samples/` (test fixtures, not your real dependencies) and a
  generated `index.html`. Each carries a confidence: `certain` (the file says
  what it is) or `likely` (a strong path convention).
- **`SAVING`** — `113,512 → 104,946 tokens, 8% saved`. This is the important
  part: the number is **measured** by walking the repository a second time with
  the proposal applied, *not* computed by subtracting what was dropped. If a
  pattern had caught anything it shouldn't, the re-walk would show it.

(The "8% saved" here is small on purpose — a young, already-tidy repo. On
[lazygit](https://github.com/jesseduffield/lazygit) it's 77.8%, on
[buildkit](https://github.com/moby/buildkit) 89.5%, on
[plotly.js](https://github.com/plotly/plotly.js) 42%. Your number is your
repo's number — see [docs/case-studies](case-studies/).)

## 3. Accept the proposal

The tool never edits your repository on its own. To apply the cuts:

```bash
uvx contextcost . --write-gitignore
```

That appends the two proposed patterns to `.gitignore`. Re-run to confirm the
saving held:

```bash
uvx contextcost .
# 113,512 → 104,946 tokens   8% saved   (unchanged — the cuts stayed applied)
```

Prefer an exclusion that only this tool respects (so the files stay tracked by
Git and visible to other tools)? Use `--emit-ignore` instead — it writes to
`.contextcostignore`, which contextcost reads for every consumer and applies
last, so its patterns win.

## 4. Keep it saved — gate it in CI

A one-shot measurement is forgotten by lunch. Add a workflow so the budget is
re-checked on every pull request, and the gate fails if the repo grows past a
budget you pick:

```yaml
# .github/workflows/contextcost.yml
name: contextcost
on: pull_request
jobs:
  budget:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: CAOShurong/contextcost/action@main
        with:
          max-added: 1000000   # optional: fail if a PR adds >1M readable tokens
```

Or gate on total size without the Action:

```yaml
- name: The whole repo must fit an agent's window
  run: pipx run contextcost --fail-over 200000 --quiet   # exit 4 when over budget
```

The bundled Action also posts a per-PR comment showing what the change added
to what an agent reads ("+32k of this is a lockfile") — so every repository
that enables it advertises the CLI on its own PRs.

## 5. Show it off — a badge for your README

Generate a Markdown report with a shields.io badge line and paste it in:

```bash
uvx contextcost . --markdown --badge
```

## 6. Put it in your coding agent

Claude Code, Cursor and Codex can call contextcost as an MCP tool — "what does
this repo cost, and what is wasting it?" becomes a tool call beside the model.
Two-line configs for each client live in
[docs/coding-agents.md](coding-agents.md).

## Where to go next

- **17 real repos, measured** — [docs/case-studies](case-studies/), including
  the head-to-head against a packing tool (repomix).
- **How the saving is verified** — the mechanism, in the
  [README](../README.md#how-the-saving-is-verified).
- **`--accurate`** — exact tokenizer counts via `tiktoken` when you need to
  quote a number; see the [README](../README.md#exact-counts---accurate).
