# 10 more repositories measured: moby/buildkit is 89% dead weight for an agent, yq is 0.7% clean

*2026-08-26. Every number below is real `--json` output from
[contextcost](https://github.com/CAOShurong/contextcost) v0.5.1 run on full
public checkouts of each repository (commits listed in the table footnotes).
Reproduce any of it with: `uvx contextcost <repo>`. The first batch of seven
repositories is [here](2026-08-25-seven-repos.md); this post extends the
measurement to ten more.*

When an AI coding agent reads a repository, every file competes for the same
context window — and some files earn their place far less than others. After
[the first seven-repo run](2026-08-25-seven-repos.md) (42% waste on plotly.js,
2.7% on astropy), the obvious question was whether those numbers were typical.
They were not — in either direction.

## The results

| Repository | Files | Tokens to read | After proposal | Saved | Share |
| --- | ---: | ---: | ---: | ---: | ---: |
| moby/buildkit | 7,574 | 14,600,569 | 1,529,637 | **13,070,932** | **89.5%** |
| jesseduffield/lazygit | 2,325 | 5,766,190 | 1,278,993 | **4,487,197** | **77.8%** |
| sharkdp/bat | 7,831 | 53,715,389 | 23,737,443 | **29,977,946** | **55.8%** |
| astral-sh/uv | 1,600 | 8,855,618 | 4,331,842 | 4,523,776 | 51.1% |
| astral-sh/ruff | 11,001 | 20,666,629 | 10,281,776 | 10,384,853 | 50.2% |
| gitleaks/gitleaks | 453 | 301,132 | 199,390 | 101,742 | 33.8% |
| trufflesecurity/trufflehog | 3,489 | 4,456,181 | 3,011,760 | 1,444,421 | 32.4% |
| pydata/xarray | 434 | 2,133,276 | 2,007,117 | 126,159 | 5.9% |
| restic/restic | 1,391 | 1,054,989 | 1,005,182 | 49,807 | 4.7% |
| mikefarah/yq | 543 | 420,446 | 417,457 | 2,989 | **0.7%** |

*(All figures from `contextcost <repo> --json`, estimate tier, ±14% measured
error bound; file counts are the tool's eligible-text-file walk. The saving
column is **measured** by re-walking each repository with the proposal applied
and verifying exactly the proposed files disappeared — never by adding up what
was dropped. Checkouts: buildkit `555e402b`, lazygit `ddceff69`, bat
`d658070`, uv `8d9324af4`, ruff `04d59f43a`, trufflehog `96b593f4`, gitleaks
`b58d3f1`, xarray `80b6a926`, restic `a80be14`, yq `7862131c`.)*

The spread is the finding: **89.5% down to 0.7%**. There is no universal
"waste percentage" — there is only your repository's number.

## What the waste actually is

**moby/buildkit — 89.5%, 13.1M of 14.6M tokens.** A Go repository that vendors
its dependencies (`vendor/`) plus generated protocol code: 7.5M tokens of
vendored libraries and 5.4M of generated files (AWS SDK serializers,
OpenTelemetry attribute tables, Windows syscall constants). None of this is
buildkit's source — it is other people's code and code that was written by
other programs. An agent asked to fix a Dockerfile frontend issue could lose
89% of its reading budget and miss nothing.

**jesseduffield/lazygit — 77.8%, 4.5M tokens.** Same shape: `vendor/` again
(1.3M), plus 2.7M of generated tables inside vendored packages (emoji
code maps, Unicode line-breaking properties) and a 492K-token color-space
snapshot JSON.

**sharkdp/bat — 55.8%, 30.0M tokens.** The most surprising result. bat's
syntax-highlighting definition bundles ship a full cryptography test-vector
suite under `assets/syntaxes/02_Extra/MediaWiki/lib/Crypto.*` — three copies
of identical files (md5-verified: `gcmEncryptExtIV128.rsp` is byte-for-byte
the same under `.lin.x64/`, `.osx.x64/` and `.win.x64/`). Six test-vector
files alone are **12.1M tokens**, and one 2.08M-token AES vector file is
larger than most entire repositories. This is exactly the class of thing no
human would ever read and every retrieval layer will happily index.

**astral-sh/ruff — 50.2%, 10.4M tokens.** Type-checker benchmark snapshots:
9.9M tokens of stored linter output in `scripts/ty_benchmark/snapshots/`
(the largest single file holds 1,329K tokens) —
useful to ruff's CI, pure noise to an agent navigating the source.

**astral-sh/uv — 51.1%, 4.5M tokens.** Recorded integration-test lockfile
snapshots (`crates/uv/tests/it/snapshots/*.snap` — single files up to 620K
tokens) plus dense data like `download-metadata.json` (865K tokens). Half the
repository's context cost is frozen output of past runs.

**gitleaks 33.8% / trufflehog 32.4%.** Mid-range: test fixtures and generated
code, spread across many small files rather than concentrated in one
directory.

**And the honest end of the table:** restic 4.7%, xarray 5.9%, and yq —
**0.7%**. yq's entire removable waste is 2,989 tokens out of 420K. A
disciplined repository with vendoring kept in check has almost nothing to cut,
and the tool says so instead of inventing findings. That matters more than any
big number: a waste finder that always finds waste is a random-number
generator with confidence labels.

## The pattern across all seventeen repos so far

Combining this batch with the
[first seven](2026-08-25-seven-repos.md):

1. **Go repositories that vendor pay a huge hidden tax.** `vendor/`
   directories made up 89.5% (buildkit) and 77.8% (lazygit) of total context
   cost. Vendoring is a deliberate build decision — but an agent does not need
   dependency *source* to navigate *your* code, and nothing else in your
   toolchain bills you per token for it.
2. **Test fixtures are the second systemic offender** — recorded snapshots
   (ruff, uv), cipher test vectors (bat), image mocks (plotly.js). They are
   load-bearing for CI and worthless for navigation; they belong in ignore
   inputs for AI consumers, not deleted.
3. **Generated code is everywhere once you look** — SDK deserializers,
   Unicode tables, syscall constants — and it quotes its generator banner when
   asked.
4. **The floor is genuinely low.** yq at 0.7% proves the classifier is not
   pattern-matching "big repo = wasteful". It reads files.

## What to do with your own number

```bash
uvx contextcost .          # measure + propose + re-measure, no install
```

If the share comes back small, you are done — that is a useful answer too. If
it is large, accept the proposal into the ignore file your tools already read
(`contextcost . --write-ignore`), then keep it honest in CI
(`contextcost . --fail-over <budget>` or the bundled
[GitHub Action](https://github.com/CAOShurong/contextcost#in-a-pull-request))
so the next 40k-token lockfile lands as a PR comment instead of silently in
every agent session.

## Methodology notes

- One checkout per repository, all runs the same hour on the same machine,
  contextcost v0.5.1, estimate tier throughout (±14% measured bound; on
  plotly.js the estimate landed 0.7% off the exact cl100k_base count).
- The whole table re-measures with one command:
  `bash docs/case-studies/reproduce.sh` (saved-token figures match exactly on
  every run; totals drift by a fraction of a percent as upstream evolves).
- Saving figures are differences of two full walks of the same tree with the
  proposal applied between them; the tool verifies the set of files that
  disappeared equals the set proposed, and narrows patterns if not.
- The three-way file duplication in bat was verified by md5sum, not assumed.
- Deferred decisions (large data files the tool refuses to auto-exclude) are
  reported separately and excluded from these savings.
- First seven repositories: [2026-08-25 case study](2026-08-25-seven-repos.md).
  Head-to-head against a packing tool on plotly.js:
  [2026-08-26 comparison](2026-08-26-vs-packing.md).

---

*contextcost is free, MIT, runs entirely locally, zero dependencies.*
*https://github.com/CAOShurong/contextcost*
