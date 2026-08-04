# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — unreleased

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
