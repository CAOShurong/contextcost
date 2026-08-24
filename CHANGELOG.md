# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[0.2.0]: https://github.com/CAOShurong/contextcost/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/CAOShurong/contextcost/releases/tag/v0.1.0
