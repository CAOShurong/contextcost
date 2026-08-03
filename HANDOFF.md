# contextcost — handoff

Written 2026-08-03 23:30 HKT. Read this first; it is authoritative.

## What this is

**What does this repository cost an AI coding agent to work in, and what is
wasting that budget?**

Not a packer. Packing a repo into a prompt is a solved and crowded problem —
repomix (27.6k★), gitingest (15.3k★), code2prompt (7.5k★), files-to-prompt
(2.8k★). Auditing and *reducing* the cost is not: the best thing found in that
space had 4 stars. Verified on 2026-08-03 by searching GitHub.

So the shape is **diagnose → recommend → prove**, and the third step is the
one nobody does. A recommendation whose saving is estimated rather than
measured is exactly the kind of unearned claim the house style forbids.

## Why this project, for this user

The user hits Claude Code usage limits constantly and said so explicitly:
"别把usage windows浪费了". This tool reduces the tokens an agent burns just
loading a repo. They are the first user.

## Status

`estimate.py`, `ignorefile.py` and `walk.py` are written, tested and committed.
20 tests pass. The repository is a git repo with one commit and **no remote
yet**. See the progress log at the bottom for what each step actually did.

## Keep working until you are cut off

If the prompt that started you says "do the next unstarted item", read that as
**"work through the Next list continuously"**. One item then stopping leaves
most of a usage window unused, and the window expires whether or not it is
spent. Finish an item, commit, push, log, start the next one immediately. Being
cut off mid-sentence is the expected ending — that is precisely why every step
commits before the following one begins.

## Operating facts for an unattended run

Verified on 2026-08-04 00:30, so none of this needs rediscovering:

- **Writing files needs no approval.** A previous unattended run wrote files
  successfully. Do not hesitate on that account.
- **`python -m pytest -q` works from the repo root**, with no `PYTHONPATH` and
  nothing installed — `tests/conftest.py` puts `src/` on the path. If you see
  `ModuleNotFoundError: contextcost`, that file has been deleted; restore it.
- **`gh` is installed but not on `PATH` in bash.** Use
  `export PATH="/c/Program Files/GitHub CLI:$PATH"` first. It is authenticated
  and `gh api user` returns `CAOShurong`. (`gh auth status` prints the stale
  pre-rename name `TeresaCSR` — ignore that, the token is correct.)
- **`git push` works non-interactively**; credentials are cached. Verified with
  `GIT_TERMINAL_PROMPT=0 git ls-remote`.
- **Commit identity is already correct globally.** Do not pass `-c user.email`.

### What you are authorised to do without asking

Build, test, commit, `git push`. The remote already exists and is already
wired up — https://github.com/CAOShurong/contextcost, pushed and verified on
2026-08-04 00:35. It was deliberately created **private**, because publishing a
half-built repository is worse than not publishing one.

Flipping it public is the *last* step of the whole project, and only once all
three of these hold:

- the test suite is green,
- `README.md` exists with generated figures,
- `.github/workflows/ci.yml` exists.

```bash
export PATH="/c/Program Files/GitHub CLI:$PATH"
gh repo edit CAOShurong/contextcost --visibility public --accept-visibility-change-consequences
```

That flag is mandatory on gh 2.97; the command fails without it. The owner is
asleep and has explicitly delegated this.

### What you must NOT do

- **Do not tag a release, and do not touch PyPI.** A brand-new package needs a
  *pending* trusted publisher registered by hand on pypi.org first, which needs
  the owner's browser session. Tagging first makes the release fail after
  everything else has passed. Leave it; the last step is to write the reminder,
  not to attempt it.
- **Do not rewrite a module that already exists** to suit your own taste. Fix
  bugs, add to it, but the existing files are reviewed and deliberate.
- Do not force-push, rewrite history, or delete anything outside this
  directory.

## Design decisions already made

**Token counting without dependencies.** tiktoken is a compiled dependency and
the house rule is zero. So ship an approximation, measure its error against a
real tokenizer offline, and *state the error bound in the output*. Being
honestly approximate beats being falsely exact — and it is the differentiator,
because a number presented as exact when it is not is the failure mode this
whole portfolio is built against.

**The saving must be recomputed, not estimated.** After proposing an ignore
file, re-walk the repo with it applied and report the real delta. evalint has
exactly this pattern in `reduce.py`: it recomputes the ranking after every
reduction layer and rolls back with a note if the answer moved. Copy that
discipline; it exists because an early version reported "96% fewer calls" next
to a leaderboard that had quietly reversed.

**What counts as waste has to be defensible.** Lockfiles, generated code,
vendored deps, minified assets, snapshot fixtures, build output, large data,
duplicated content. Each category needs a stated rule and a way for the user
to disagree. Do not silently delete or rewrite anything — emit a proposal.

## Next steps, in order

1. `src/contextcost/` skeleton + `pyproject.toml` + LICENSE + `.gitignore` +
   `.gitattributes` (`* text=auto eol=lf`).
2. The walker: respect `.gitignore`, classify files, attribute cost.
3. The estimator: approximate token count, plus a calibration script that
   measures the error against a real tokenizer and records the bound.
4. The waste classifiers, each with its own rule and its own test.
5. The remediation: propose an ignore file, then **re-measure** with it.
6. Terminal report in the house visual language, plus `--json`.
7. Tests, weighted at the refusal behaviour and at the classifiers.
8. `docs/build_docs.py` + README with generated figures.
9. CI (matrix, lint, README-freshness, build) and `release.yml`.
10. Git history in logical commits, push, then tell the user to register the
    pending PyPI publisher BEFORE any tag.

## Do not go exploring — everything you need is below

An earlier version of this file claimed the 23:58 test run "spent its entire
91-second window reading" and wrote nothing. **That was wrong**, and it is
recorded here because the mistake is instructive: the diagnosis was made by
reading that run's transcript *while the run was still appending to it*. A live
log looked like a truncated one. The run actually lasted 20 minutes, made ~45
tool calls, wrote a real test file, and was cut off mid-`Write` only when the
user's own session became active at 00:19.

Two things follow, and both matter more than the correction itself:

- **A scheduled run can be killed at any instant.** Commit after every step.
  Work that is not committed is work that can vanish mid-sentence.
- **Do not diagnose from a file that something else is writing to.** Check
  whether it is still growing first.

Still true, though for a different reason — reading `evalint/` to re-derive the
house style costs a large fraction of a window: **start writing within your
first three tool calls.** Every shape you need is below.

### pyproject.toml

hatchling backend, `dynamic = ["version"]` reading `src/contextcost/__init__.py`,
`requires-python = ">=3.9"`, `dependencies = []`, a `[project.scripts]` entry
`contextcost = "contextcost.cli:main"`, optional `dev = ["pytest>=7", "ruff>=0.6"]`,
`[tool.hatch.build.targets.wheel] packages = ["src/contextcost"]`,
`[tool.pytest.ini_options] testpaths = ["tests"]`, and ruff with
`line-length = 88`, `target-version = "py39"`,
`select = ["E", "F", "I", "UP", "B", "SIM", "C4"]`,
`[tool.ruff.lint.per-file-ignores] "tests/*" = ["E501"]`.

### Module docstring tone

Every module opens by stating the problem it exists for and the decision it
makes, in prose, before any code. Constants carry `#:` comments explaining why
that value and not another. See `src/contextcost/estimate.py`, already written
— match it and you have matched the house.

### CI (.github/workflows/ci.yml)

Jobs: `test` (matrix — ubuntu/windows on 3.9 and 3.13, plus ubuntu on 3.10,
3.11, 3.12, plus macos on 3.13; `pip install pytest` only, `PYTHONPATH: src`),
`readme` (`pip install pillow`, `python docs/build_docs.py --check`), `lint`
(`ruff check src tests docs` and `ruff format --check src tests docs`),
`build` (`python -m build` then `twine check --strict dist/*`), and one
end-to-end job that runs the tool against a real repository and asserts
something concrete about the output.

### release.yml

Trigger `on: push: tags: ["v*"]`. Jobs: test, then build with a step asserting
the tag matches the package version, then `publish` using
`environment: {name: pypi}`, `permissions: {id-token: write}` and
`pypa/gh-action-pypi-publish@release/v1`, then `github-release` using
`softprops/action-gh-release@v2` with `generate_release_notes: true`.

### Tests

pytest, under `tests/`, imported with `PYTHONPATH=src`. Test names are
sentences. Weight the suite at two things: correctness against cases small
enough to verify by hand, and the *refusal* behaviour — the cases where the
right answer is "cannot determine". A test that pins a documented limitation is
worth more than three that pin a happy path.

## Order of work, so a short window still produces something

Each step leaves the tree working. If the window dies after any of them, the
next session has real ground to stand on.

1. `src/contextcost/walk.py` — the walker. **Do this first, before packaging.**
2. `tests/test_walk.py`, run for real against the `evalint` repo next door.
3. `pyproject.toml`, `src/contextcost/__init__.py` with `__version__ = "0.1.0"`.
4. `src/contextcost/classify.py` — the waste classifiers, one rule each.
5. `src/contextcost/reduce.py` — propose an ignore file, then **re-walk and
   measure the real saving**. Never estimate it.
6. `src/contextcost/report.py` and `cli.py`.
7. `docs/`, CI, release workflow, git history, push.

**Append a line to this file after each step you finish.** That is what makes
the next window cheap.

## Reference

`C:\Users\35021\Desktop\VC\claude\evalint\` is the newest and best of the five
existing projects. Match its structure, module docstring tone, README shape,
CI workflow and release workflow.

## Rules that are easy to get wrong

- Commit as `Shurong Cao <170531907+CAOShurong@users.noreply.github.com>`.
  Never the gmail address.
- **No `Co-Authored-By: Claude` trailer.** That is evalint-only.
- Everything in English.
- Write generated data files with explicit `\n`; the csv module's default CRLF
  broke a reproducibility test on Linux and macOS in evalint.
- A brand-new PyPI package needs a *pending* trusted publisher created by hand
  before the first tag, or the release fails after everything else passes.

---

## Progress log

Append one line per completed step. This is what makes the next window cheap.

- **2026-08-04 00:1x — `ignorefile.py` done.** Real gitignore matching, not a
  substring check: unanchored patterns match at any depth, an interior `/`
  anchors, trailing `/` is directory-only, `!` negates and **last match wins**,
  `**` spans separators, `[abc]` classes. 21 hand-written cases pass. One bug
  found and fixed on the way: a directory-only pattern such as `build/`
  returned False for `build/x.o`, because an early `is_dir` guard returned
  before the "or anything beneath it" branch of the regex was considered. Fixed
  by compiling a second `exact` regex and distinguishing "is the directory"
  from "is beneath it".
- **2026-08-04 00:2x — `walk.py` done and run for real against `evalint/`.**
  Skips ignored paths without descending, picks up nested `.gitignore` files
  anchored to their own directory, sorts so a walk is reproducible, samples
  files above 2 MB and marks them `sampled` rather than implying precision,
  and counts binaries separately without charging them tokens.

### The first real finding, from the first real run

Walking `evalint/` (32 files kept, 6 paths ignored, 132,963 estimated tokens):

    docs/example-results.csv    72,724 tokens

**One generated fixture is 55% of the entire repository's context cost.** No
agent working on evalint ever needs to read it. That single number is the
product thesis, and it turned up on the first repository pointed at.

- **2026-08-04 00:20 — `tests/test_ignorefile.py`, written by a scheduled run,
  found a real bug in `ignorefile.py`.** The module docstring claimed "a
  negation cannot rescue a file inside an excluded directory… git behaves this
  way and so does this". The second half was false: the walker enforced it by
  pruning, but `IgnoreRules.ignored("build/keep.txt")` called directly returned
  `False` for `build/` + `!build/keep.txt`. Documented behaviour that the code
  does not implement is precisely the failure this portfolio exists to argue
  against, and it took an adversarial test to surface it. Fixed by checking
  every ancestor directory before applying last-match-wins.
- **2026-08-04 00:30 — packaging and the first commit.** `pyproject.toml`,
  `__init__.py` at `0.1.0`, and `tests/conftest.py` so the suite runs with no
  environment set up. 20 tests pass. Committed.

- **2026-08-04 01:0x — `classify.py` done, 8 rules, 20 tests.** Confidence is a
  field (`certain` / `likely` / `possible`) and the lowest tier is never acted
  on. Pointing it at `C:\Users\35021\Desktop\tokenBridge Code` (a real, messy
  JS repo — keep using it, `evalint` is too clean to exercise the rules) found
  three defects that no fixture written from the rule descriptions would have:
  the generated-file marker was the bare substring `generated file` and matched
  the prose "chatgpt-**generated file**s" at `certain` confidence; the evidence
  quote took the first 90 characters of the line so the marker itself could be
  cut off, which is what made the first bug visible; and dense content was
  reported as `minified`, a word that claims a readable original exists
  elsewhere, which is false for the JSON manifests it mostly fires on. Each has
  a regression test named for what went wrong.
- **2026-08-04 01:1x — `reduce.py` done, 10 tests.** Proposes patterns, walks
  the repository *again*, and takes the difference. Then compares what vanished
  against what was named: if a directory pattern over-reached, it narrows to
  exact paths, walks a third time, and records `narrowed_from` so the
  correction is visible. Measured on tokenBridge Code:
  **3,645,027 → 585,725 tokens, 84% saved.** On evalint the honest answer is
  0%, because its one finding is `possible`.

## Next

6. `report.py` + `cli.py` — terminal report in the house visual language,
   plus `--json`. `Reduction.as_dict()` and `Finding.as_dict()` already exist
   for the JSON path. The report must print the error bound, must say the
   saving was measured rather than estimated, must list the `possible` tier
   separately as the user's decision, and must print `narrowed_from` when a
   pattern was corrected.
7. `tests/test_walk.py`. It does not exist yet: a scheduled run was killed
   mid-`Write` while creating it. The walker is currently covered only
   indirectly.
8. `docs/build_docs.py` + README with generated figures, then CI, then the
   public repository.
