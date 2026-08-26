# I measured 3 more repos with exact token counts: the waste is real, and here is the proof

*Third in a series ([7 repos](2026-08-25-seven-repos.md), [10 more](2026-08-26-ten-more-repos.md)).
Every number below is real output from contextcost at commit `4f52b8f` (the
lockfile-accuracy fix, released as v0.5.2), run on full public checkouts of
plotly.js, rclone and astropy at the commits listed per section. The headline
savings are **exact tokenizer counts** (cl100k_base), not estimates — this post
is specifically about what happens when you stop trusting the estimator.*

The two earlier posts measured seventeen repositories with contextcost's
estimator, which prints a measured error bound (±23% since v0.5.2). A fair
objection: *estimates are cheap — where is the proof?* This post re-measures
three well-known repos with `--accurate`, which tokenizes every file with
tiktoken's `cl100k_base` (the encoding behind GPT-4-class pricing) instead of
estimating from byte structure. Same walk, same proposal; only the counter
changes.

## The results

| Repository | Commit | Exact tokens (cl100k_base) | After proposal (exact floor) | Saved | Share |
| --- | --- | ---: | ---: | ---: | ---: |
| plotly.js | `71a2ff73b` (2026-08-24) | 63,363,404 | 54,585,681 | **8,777,723** | **≥ 13.9%** |
| rclone | `8869a848f` (2026-08-25) | 9,506,888 | 9,144,959 | **361,929** | **≥ 3.8%** |
| astropy | `8a5859f1` (2026-08-23) | 8,673,561 | 8,300,259 | **373,302** | **4.3%** |

**How to read "exact floor":** files above 2 MiB are counted from their first
2 MiB and extrapolated by size rather than read whole (reading a 40 MiB mock
JSON just to count it exactly would be its own joke). Those sampled files are
marked, never silently mixed in. The "after" column subtracts only the
exactly-counted dropped files, so it *under-counts* the saving on plotly.js
and rclone — where most of the proposed drop happens to be big sampled files.
astropy had zero sampled files, so its 4.3% is exact through and through.

For reference, the estimate tier on identical trees reported 42% / 22% / 3%
saved — because the estimator prices the *proposed* cut differently than the
tokenizer does (see the honesty check below).

## What the waste actually is

**plotly.js — ≥ 13.9%, 8.78M exact tokens.** The proposal drops 158 files:
22 build outputs under `dist/` priced at ~17.4M estimated tokens (including
`dist/plotly.js` itself at 2.39M), nine minified bundles (~5.89M estimated),
three lockfiles, one generated TypeScript schema, plus 123 dense-data files.
An agent asked to debug a chart should never pay to read the compiled bundle
of every chart type.

**rclone — ≥ 3.8%, 362K exact tokens.** 178 generated files, led by four
parallel renderings of the manual (`MANUAL.html` 808K, `MANUAL.txt` 730K,
`MANUAL.md` 732K estimated each — Pandoc wrote them, nobody edits them by
hand) and a machine-generated test table (`lib/encoder/encoder_cases_test.go`,
566K estimated). Generated documentation is the classic rclone-shaped waste:
real bytes, zero signal for a code-reading agent.

**astropy — 4.3%, 373K exact tokens.** The honest floor of the whole series:
a meticulously clean repo still carries 18 generated reference-data files,
generated parser sources under `cextern/wcslib/C/flexed/`, and vendored
libraries. Even the best-run projects have a few percent of pure noise.

## Honesty check: does the estimator survive verification?

Yes — with the band doing exactly its job. On these three repos:

| Repository | Estimate | Exact | Drift | Verdict |
| --- | ---: | ---: | ---: | --- |
| plotly.js | 64,142,024 | 63,363,404 | 1.2% | inside ±23% |
| rclone | 7,892,030 | 9,506,888 | 17.0% | inside ±23% |
| astropy | 7,901,740 | 8,673,561 | 8.9% | inside ±23% |

rclone drifts 17% because its biggest files are prose-heavy HTML/text that
tokenize denser than source code — precisely why the printed bound exists and
why every number you intend to quote deserves an `--accurate` run. The
estimate tier stays the default because it needs no dependencies; the exact
tier settles disputes.

## Reproduce any of it

```bash
uvx --from "contextcost[accurate]" contextcost --accurate <repo>
```

which prints both tiers plus the applied-proposal re-measurement for any
repository. The estimate-tier table across all twenty measured repositories
reproduces with `bash docs/case-studies/reproduce.sh <checkouts-parent>`.

## Why this matters

Across twenty measured repositories now, the median well-known project carries
double-digit-percent context waste — build output, lockfiles, parallel
renderings of the same docs, machine-generated test data. An AI coding agent
bills all of it identically to source it actually needs. The fix is not a
smarter model; it is not feeding the compiled bundle to the model in the first
place.

contextcost measures the bill, proposes cuts the file system can prove are
machine-made, and re-measures to show the result. `--accurate` exists so you
never have to take the estimator's word for it.
