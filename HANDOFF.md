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

Nothing built yet beyond this file. The previous session chose the name,
verified the prior art, verified `contextcost` is free on PyPI, and set a
scheduled task to resume.

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

The 23:58 test run spent its entire 91-second window reading: HANDOFF.md, then
three memory files, then five files inside `evalint/` to work out the house
shape, and was cut off before writing a single line. That was a documentation
failure, not a judgement failure.

So: **start writing within your first three tool calls.** Do not read
`evalint/` unless something below is genuinely ambiguous. The shapes are here.

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

## Next

3. `pyproject.toml` + `__init__.py` with `__version__ = "0.1.0"`.
4. `classify.py` — the waste classifiers. `example-results.csv` above is the
   motivating case: generated, large, referenced by tooling but never read by a
   human or an agent.
5. `reduce.py` — propose exclusions, then **re-walk with `extra_ignore=` and
   measure the real delta**. `walk_repository` already takes that argument
   precisely so the saving is measured rather than subtracted.
