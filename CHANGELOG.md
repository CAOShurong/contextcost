# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Release notes that sell: the v0.5.0 and v0.5.1 GitHub Releases previously
  consisted of a single auto-generated changelog link — the page every
  release visitor, packager, and news aggregator lands on showed nothing
  about what the tool does or why its numbers are different. Both releases
  now carry full notes (the measure→propose→re-measure pitch, the real
  seventeen-repo results table, feature highlights, Discussions pointer);
  source markdown kept in `docs/engagement/release-body-v0.5.*.md`.
- Repository discoverability metadata: description rewritten to lead with
  the question ("How many tokens does an AI agent pay to read your repo?")
  plus the `uvx` one-liner; homepage now points at the landing page instead
  of PyPI; topics refreshed to 20 search-relevant tags (added `ai-tools`,
  `token-optimization`, `context-cost`, `contextcost`, `hacktoberfest`,
  `llm-tools`; dropped near-zero-search `tiktoken`, `tokens`, `github-actions`
  duplicates kept where meaningful). Note: GitHub has no API for the social
  preview image (Settings-only upload) — it must be set once in the web UI
  from `docs/assets/social-card.png`.

### Added

- Community surface: GitHub Discussions are now enabled, with a lightweight
  issue-template entry point (`Questions & feedback`) that routes
  "this number looks wrong" reports toward `--accurate --json` output so a
  dispute arrives as checkable data. README "Share it" section links the
  Discussions forum.
- Ready-to-post launch drafts for external distribution (Reddit / Show HN /
  X thread) in `docs/engagement/launch-drafts.md` — first-person posts built
  only from already-published, live-re-verified case-study numbers (buildkit
  89.5% … yq 0.7%), each with an explicit maker-disclosure and a posting
  checklist that requires re-running every cited number at posting time.
  Not posted; external posting requires user approval.

- Full independent re-verification of the published case-study numbers
  (2026-08-26): all eleven repositories re-run live with v0.5.1 `--json` on
  the local checkouts at the commits cited in the posts — every figure in
  both case studies reproduces exactly (buildkit 89.5%, lazygit 77.8%,
  bat 55.8%, uv 51.1%, ruff 50.2% … yq 0.7%; plotly.js 63,831,059 →
  37,008,917 tokens, 42.0% measured saving), with one upstream-drift
  exception: gitleaks total moved 301,132 → 300,980 tokens (−152) while its
  share stayed 33.8%. LibreChat engagement drafts rewritten against the
  current state of PR #15089 (the old draft's accounting question is now
  answered by the PR body; new draft engages with the summary-boundary
  contract and asks about unbounded summary growth). Still not posted;
  external posting requires user approval.

- Social preview card (`docs/assets/social-card.png`, 1280×640): a real
  plotly.js measurement (63.8M tokens in, 42% measured saving) rendered as the
  `og:image` / `twitter:card` of the landing page, so pasting the link into
  Slack, Discord, X or chat now shows the headline number and terminal
  screenshot instead of bare text — the repo had zero share-surface before.
  The card is also embedded at the top of this README. Generated with
  matplotlib against published case-study numbers; landing page regenerated
  via `build_site.py` (`--check` stays green).

- Second case study, ten more repositories
  (`docs/case-studies/2026-08-26-ten-more-repos.md`): moby/buildkit **89.5%**
  waste (7.5M vendored + 5.4M generated tokens of a 14.6M-token total),
  lazygit 77.8%, bat 55.8% (three md5-identical copies of a cryptography
  test-vector suite; six vector files alone are 12.1M tokens), uv 51.1%, ruff
  50.2% — down to yq at **0.7%**, the honest floor. Every number is real
  `--json` output from v0.5.1 on public checkouts; `reproduce.sh` now covers
  all seventeen repositories plus contextcost itself in one command.
  Distribution material, not a feature.

- Head-to-head case study against a packing tool:
  `docs/case-studies/2026-08-26-vs-packing.md`. Both tools ran on the same
  full plotly.js checkout — repomix packed 2,595 files / 39,150,382 exact
  tokens, of which **73% of packed characters** came from `dist/` build
  output and `test/image/mocks/` fixtures it had no opinion about;
  contextcost proposed and *measured* a 26.8 M-token (42%) saving on the same
  tree. Positions contextcost as the audit step before any packing workflow.

- GitHub Pages landing page, live at
  <https://caoshurong.github.io/contextcost/> (site enabled from `main`
  `/docs`). One static file (`docs/index.html`) rendered by
  `docs/build_site.py --check`-guarded: the seven-repo table is transcribed
  from the reproduce.sh run and CI can fail the page when it goes stale,
  same honesty rule as the README figures. First "site" leg of the
  distribution plan (HONEST_ASSESSMENT root cause #1: discoverability ≈ 0).

### Changed

- Case study made self-verifying. The seven-repo table had silently dropped
  its seventh row (contextcost itself, 161,453 → 85,663 tokens, 46.9% saved —
  the highest share of all seven); the row and a short section are restored,
  with numbers re-measured live via the new `docs/case-studies/reproduce.sh`,
  which re-runs all seven checkouts in one command (`summarize.py` renders
  each `--json` payload into one table row; contextcost's exit-1-on-waste
  convention is handled explicitly). Reproduction run on 2026-08-25 matched
  every published saved-token figure exactly (rclone/contextcost totals
  drifted <0.1% with upstream evolution).

### Changed

- README rewritten to lead with the answer instead of the mechanism. The hero
  is now real output from a full plotly.js checkout (`71a2ff7`, 2026-08-24):
  63,831,059 tokens to read, 26.8M of it (42%) measured waste — compiled
  bundles under `dist/` and recorded numeric test fixtures — with the
  `uvx contextcost .` one-liner as the first actionable thing a visitor sees.
  The estimate's credibility is shown, not asserted: `--accurate` counted
  63,363,404 exact (cl100k_base), so the headline estimate landed 0.7% off
  against its ±14% bound. The old synthetic example output moved out of the
  first screen; the generated figures and their `build_docs.py --check`
  contract are unchanged.

### Added

- A next-steps hook at the end of the terminal report. When a proposal exists,
  the report now closes with three concrete moves — accept it (`--write-ignore`
  family), gate it (`--fail-over` in CI), and publish a badge
  (`--markdown --badge`) — instead of ending at the saving number, because a
  one-shot measurement is forgotten and retained usage is what keeps waste
  out. Printed only when there is something to act on; a clean repository gets
  no follow-up section. The flag shown is derived from `ignore_file` via a new
  `Reduction.write_flag` property, which also replaces the flag-selection
  branch inside the SAVING section. Two new tests = 193.

- The first case study (`docs/case-studies/2026-08-25-seven-repos.md`):
  contextcost run over seven well-known repositories with every number from
  real `--json` output — plotly.js 63.8M tokens with 42.0% proposed as waste
  (17.4M build output + 5.9M minified bundles), dask 46.5% (one `pixi.lock`
  is 22% of the repo's context cost), pandas 21.5%, rclone 21.8%, keycloak
  7.5%, astropy 2.7% (stated honestly: a hygienic repo has little to cut).
  Distribution material, not a feature; nothing is posted externally without
  approval.

- `--delta` now accepts a git revision as its base, so measuring a change no
  longer requires a second checkout. When the base argument is not a
  directory on disk, it is offered to git as a revision of the repository
  being measured (`main`, `HEAD~1`, a tag, the PR's merge base) and the
  commit's tracked files are exported with `git archive` into a temporary
  tree that is removed at exit. The comparison itself is unchanged — two
  ordinary directories walked by the same code, so a ref delta and a
  two-checkout delta cannot disagree. A real directory always beats a ref
  with the same name (paths win over revisions), an unknown revision exits 2
  carrying git's own complaint rather than silently comparing against
  nothing, and a base given for a non-repository names that fact instead.
  Seven new tests; suite green (191 passed, 1 skipped without the optional
  tokenizer); verified live on this repo (`--delta HEAD`:
  +2,517 tokens from uncommitted work) and plotly.js (`--delta
  v4.0.0-rc.0`: +645,796 tokens across 179 files, 89% of the addition in
  build output and minified bundles).

## [0.5.0] - 2026-08-25

### Added

- A Windows path-separator audit of every rule in `classify.py`, closing the
  last backlog item. Every rule consumes a relative path that arrives joined
  with `/` — the walker normalises `os.sep` away and the ignore matcher is
  compiled over `/`-joined paths — and the audit turned that assumption into
  checked contract. Feeding each rule a backslash-joined path (the form an
  un-normalised walk would produce) split the rule set by how it reads paths:
  directory rules (`vendored`, snapshot directories, build output) scan
  segments split on `/` only, so a backslash hides every directory from them;
  name rules (`lockfile`, `minified`, snapshot extensions, large data) go
  through `os.path.basename`, which on Windows also splits on `\`. Neither is
  reachable through the walker, so no user-visible bug existed — but now the
  directory rules are pinned to fail closed on any platform, the name rules'
  platform-defined verdicts are documented with a Windows-host assertion, a
  control test proves the dense (byte-measuring) rule is separator-blind, a
  real-file test proves the generator-banner read works via
  `os.path.join` on both separators, and a walker test pins that it emits `/`
  always. Nine new tests = 190; verified live on this repo (77,338 tokens,
  Windows host) and plotly.js (63,831,059 tokens).

- `--fail-over BUDGET`: a CI gate on total size. Exits `4` when the measured
  total exceeds BUDGET tokens (the exact total under `--accurate`, otherwise
  the estimate, with the ±14% band named in the message). Deliberately
  distinct from exit `1`: waste means "clean this up", over-budget means
  "this repository no longer fits the budget at all". A negative budget is a
  usage error (exit 2). Five new tests; verified live on this repo
  (75,546 tokens: pass at 500k, fail at 1k) and plotly.js (fail at 1M,
  pass at 100M).

- A docs page for coding agents (`docs/coding-agents.md`): copy-paste MCP
  configs for Claude Code (`claude mcp add` command + committed
  `.mcp.json`), Cursor (`.cursor/mcp.json`) and Codex CLI
  (`codex mcp add` + `~/.codex/config.toml`), plus a ready-to-use prompt.
  The MCP server was unusable by anyone who did not already know each
  client's config format; this is the distribution half of the MCP feature.
  Config formats verified against current client docs (2026-08); the page
  links from the README's "As an MCP server" section.

- An MCP server (`contextcost mcp`, stdio): a coding agent that must shell out
  to contextcost has to guess at flags and parse human output; one that speaks
  MCP calls the same measurement and gets the schema-versioned JSON in band.
  Two tools -- `estimate` (the full `--json` payload) and `propose` (the
  measured exclusion proposal with a ready-to-paste ignore block) -- exposed
  over JSON-RPC 2.0 in ~150 lines of stdlib `json`/`sys`, so the
  zero-dependency install promise holds without the official SDK.
  Protocol coverage is deliberately minimal (`initialize`, `ping`,
  `tools/list`, `tools/call`); notifications get no reply per the spec, parse
  errors answer `-32700` with the session continuing, unknown methods
  `-32601` so a client can degrade gracefully, and tool errors surface as
  data (`-32603` "not a directory") instead of killing the pipe -- an agent
  that mistypes a path sees the mistake, not a confident zero-cost report.
  Verified against plotly.js over a real stdio session:
  `estimate` → 63,831,059 tokens ±14 % across 4,063 files,
  `propose` → 26,822,142 saved / 42 % measured, 158 patterns;
  bad path → `-32603 NotADirectoryError`; garbage line → `-32700`;
  `resources/list` → `-32601`. 18 tests in `tests/test_mcp.py`.

## [0.4.0] - 2026-08-25

### Added

- `--delta BASE` and a composite GitHub Action (`CAOShurong/contextcost/action`):
  the context cost of a *change*, measured the way every other number here is.
  A pull request is a change to a context budget, and until now nothing in this
  package could state what one costs -- which left the sentence that sells the
  tool ("this PR adds +41,882 tokens, 92% of it a lockfile") unsayable. The
  delta walks a base checkout and the head tree **per file** and compares by
  path: files only in one tree contribute in full, changed files contribute
  their difference, unchanged files are not listed. Per-file comparison rather
  than subtracting two totals means an ignore rule added between base and head
  shows up as churn on the files it hides instead of vanishing inside a
  plausible number. Attribution runs the ordinary waste classifiers over the
  head tree, so "+32k of it is a lockfile" is measured there; anything no rule
  fires on lands under `unclassified (real work?)`, which is exactly the split
  a reviewer needs. Output through the existing `--markdown` and `--json`
  channels (`{"schema": 1, "delta": {...}}`). Verified against two checkouts of
  this repository with a synthetic lockfile commit: 53,834 → 95,631 tokens,
  +41,797 attributed 32,232 lockfile / 9,565 unclassified.
- A `--markdown` report: the same measurement as GitHub-flavoured Markdown,
  for the two places this tool most needs to travel -- a pull-request comment
  and a README. The terminal report pasted into a PR arrives as ANSI escape
  codes, `?` glyphs and misaligned columns, so there is now a second renderer
  that emits pipe tables, a blockquoted saving line and a fenced gitignore
  block; `--badge` prepends a shields.io badge line with the measured total
  baked in for README use. The honesty rules carry over intact: the estimate
  is always printed with its ±14 % bound, the saving says it was measured by
  walking the repository again rather than subtracted, and the tier the tool
  cannot judge stays phrased as a question. Paths are escaped so a `|` in a
  filename cannot break a table. Verified on plotly.js (63.2 M tokens walked,
  the minified/dist/lockfile findings rendering as tables a collapsed PR
  comment still shows).
- A versioned `--json` schema (v1) with a printed key contract
  (`--json-schema`). The output existed but promised nothing: a key could
  change shape between releases and every script built on it would find out
  in production. Now the document carries `"schema": 1`, the contract is data
  (`json_schema.CONTRACT`) that the test suite walks against real output --
  so documentation drifting from behaviour fails CI rather than a consumer's
  parse -- and all assembly goes through one `build_payload()` that cannot
  diverge from what the CLI prints. Stability rule: existing keys never change
  meaning within a version; new optional keys may appear without a bump;
  breaking changes bump to v2. Verified as an Action-style consumer against
  plotly.js (63.2 M tokens walked, measured saving 26.2 M / 41 % parsed by
  pinning `schema` alone). This unblocks the GitHub Action.
- `.contextcostignore`, a project-local ignore file with `--emit-ignore` to
  write the proposal into it. The right exclusion for an AI context budget is
  often wrong everywhere else — a recorded test fixture should reach an agent
  and stay tracked by Git — and pushing contextcost's proposal into
  `.gitignore` or a consumer's file would change other tools' behaviour to get
  a smaller token count. This file is read for every consumer, even under
  `--no-gitignore`, and its patterns are applied last so they win over every
  earlier input, including via `!` re-inclusion. Accepting a measured saving
  is now one command that cannot leak side effects outside this tool's own
  measurement.
- A `numeric` content class for numeric data dumps — JSON number matrices,
  recorded fixture arrays, locale number tables. Found by running `--accurate`
  against plotly.js, where the estimator read 45 M tokens and the tokenizer
  said 64 M; a byte-pair encoder merges digits poorly, so files dominated by
  small integers cost up to four times more per character than the code ratio
  assumed (`gl2d_parcoords_blocks.json` was under-counted by 71%). The class
  is conservative: it applies only to code-classified files whose digit share
  is at least 10%, whose letters are under 25%, and where digits outnumber
  letters; the ratio is one over the digit share capped at 2.2, with every
  bound swept across plotly.js, astropy, h5py and pandas to minimise
  per-file regressions. Measured effect on whole-tree drift vs cl100k_base:
  plotly.js 29.4% → 1.2%, astropy 20.8% → 12.6%; h5py and pandas unchanged.
- `ERROR_BOUND` re-measured after the change: ±12% → ±14% (95th percentile
  10.8% plus the usual headroom), via `docs/calibrate.py`.

## [0.3.0] - 2026-08-24

### Added

- `--accurate` mode: exact token counts via tiktoken, installed as the
  optional extra `contextcost[accurate]`. The zero-dependency estimate stays
  the default and stays on screen beside the exact figure — including a
  statement of whether it landed inside its measured ±12 % band. Sampling
  above 2 MB is unchanged and still marked. Without tiktoken installed the
  flag exits with code 3 and an install hint rather than pretending.
  Measured against plotly.js (45 M estimated / 64 M exact), where the gap is
  dominated by numeric data dumps the character-class estimator under-charges;
  that divergence is now visible per run instead of silent.

## [0.2.0] - 2026-08-11

### Added

- Consumer-aware file selection for Cursor, Aider, and Repomix, including the
  documented native ignore inputs for each tool.
- `--write-ignore`, which writes a re-measured proposal to `.cursorignore`,
  `.aiderignore`, `.repomixignore`, or `.gitignore` as appropriate.
- Consumer and active ignore-input metadata in JSON and terminal reports.
- A real `python -m contextcost` entry point.
- Refusal to follow a symbolic-link ignore destination during write mode.

### Changed

- Clarify that consumer profiles model eligible files, not a live product's
  proprietary tokenizer, retrieval strategy, prompt, or bill.
- Keep `--write-gitignore` as an explicit backward-compatible destination.

## [0.1.0] - 2026-08-04

First release.

### Added

- `contextcost` measures what a repository costs an AI coding agent to read,
  attributing tokens per file, per directory and per extension.
- Real `.gitignore` matching: depth rules, anchoring, directory-only patterns,
  last-match-wins negation, and the rule that a negation cannot re-include a
  file underneath an excluded directory.
- Eight waste classifiers — lockfiles, generated files, minified output, dense
  machine-written content, vendored code, build output, snapshots and large
  data — each quoting its evidence for the specific file it fired on, and each
  carrying a confidence of `certain`, `likely` or `possible`.
- A reduction that proposes exclusions and then **walks the repository again
  to measure what they did**, rather than adding up what it decided to drop.
  If a pattern removes anything that was not proposed, the patterns are
  narrowed to exact paths and the report says so.
- Terminal report with an ASCII fallback for terminals that cannot encode the
  drawing characters, `--json` output, and `--write-gitignore`.
- `docs/calibrate.py`, which measures the estimator against `cl100k_base` and
  writes the observed error into `ERROR_BOUND`.
- Per-script CJK counting. Japanese kana, Korean hangul, simplified Chinese and
  traditional Chinese each cost a different amount per character, spanning 0.85
  to 1.55 — a single constant under-counted traditional Chinese by 30%.

### Known limitations

- The token count is an estimate, not a tokenizer. Measured error against
  `cl100k_base`: 2.6% median, 10.0% at the 95th percentile. That is one
  tokenizer standing in for all of them.
- The `possible` tier — mostly large data files — is never excluded
  automatically, because nothing visible from the file system distinguishes a
  fixture from the subject of the work.
- No users yet. Every number here is measured, which is not the same as being
  battle-tested.
- Simplified and traditional Chinese are told apart by a short list of
  traditional-only characters. It recognises the script, it is not a conversion
  table, and a document mixing both is charged the traditional rate throughout.

[0.5.0]: https://github.com/CAOShurong/contextcost/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/CAOShurong/contextcost/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/CAOShurong/contextcost/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/CAOShurong/contextcost/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/CAOShurong/contextcost/releases/tag/v0.1.0
