# PRODUCT BACKLOG — contextcost

Owned by the product-agent cron track. One requirement gates everything:
**really useful, really solves a pain point, promising.** No vanity features.

## Mission

Make contextcost the default answer to "what will this repo cost me in
context, and what can I safely drop?" — the measure→propose→re-measure
methodology is the moat; everything below strengthens or distributes it.

## P0 — credibility & correctness

- [done rev 4] Estimator blind spot found by `--accurate` on plotly.js: numeric data
      dumps (JSON number matrices, locale tables) are classified as `code`
      (4.14 chars/token) but really cost ~2.8 chars/token — per-file drift up
      to 74%, repo-wide drift 29%. Add a `numeric` content class (digit share
      heuristic), calibrate it with docs/calibrate.py against cl100k_base,
      and re-measure ERROR_BOUND. Evidence: estimate 45.3 M vs exact
      64.2 M tokens on plotly.js; worst files gl2d_parcoords_blocks.json
      (71.6%), lib/locales/*.js (~70%).

- [done rev 1] `--accurate` mode: exact counts via tiktoken (optional extra
      `contextcost[accurate]`); estimate kept as default and shown beside the
      exact number. NOTE discovered: numeric data dumps (JSON matrices,
      locale tables) drift up to 70% — estimator blind spot, needs a
      `numeric` class + recalibration (see new P0 entry).
- [done rev 5] `.contextcostignore` file: project-local ignores with comments,
      merged with .gitignore semantics. `--emit-ignore` writes the proposal
      as this format so accepting a saving is one line.
      (Shipped e6e6541: read for every consumer incl. --no-gitignore, applied
      last so patterns win; 4 CLI tests + 4 ignorefile tests; verified on a
      scratch repo and git check-ignore.)

## P1 — distribution

- [done 2026-08-26i] Profile freshness pass: the "Latest changes" section in
      CAOShurong/CAOShurong had gone stale against its own rule (newest
      release *or* substantive commit per repo). Audited the local git log of
      all 24 checkouts and refreshed 4 rows, shipped as profile commit
      5e5377a: VulnFuse now names the synthetic three-scanner demo (90c9d42)
      and the README worked example (38a95b7) instead of "routine dependency
      upkeep"; BenchLineage's row gained the zero-install `uvx` trial
      (81ee19a); DidYouLearn and OhmJudge correctly say "only dependency
      upkeep since" with links. Integrity catch: didyoulearn@e932cc0 and
      ohmjudge@d1e4f84 exist only locally — Dependabot landed them on GitHub
      as merge commits f98a100/#9 and fbd7ff4/#5, so direct-SHA links would
      have been dead; rows link PRs instead and both local clones were reset
      to origin/main. Lesson: before linking a commit SHA from another
      checkout, verify it exists on origin (`git rev-list HEAD..origin/main`),
      or link the PR.
- [done 2026-08-26h] VulnFuse README gains a worked example: the synthetic
      three-scanner demo is now walked end to end as a user story — five
      findings become four explainable clusters; Log4Shell merges across
      Grype/Trivy with the quoted evidence scores (+40 shared CVE, +25
      component, +15 asset, +10 location); the Snyk same-CVE record stays a
      separate cluster because its asset differs (source repo vs built image);
      single-tool OpenSSL/zlib stay untouched; and the coverage tables turn
      scanner disagreement into numbers (Trivy×Grype 33% Jaccard, Snyk 0%).
      Every figure was taken from a fresh CLI run of the docs/demo fixtures,
      not written from memory; `prettier --check` +
      `scripts/check-repository.mjs` green before push. Shipped as
      CAOShurong/vulnfuse 38a95b7. No product code touched.
- [done 2026-08-26g] benchlineage README gains a zero-install trial section:
      contextcost's own conversion lesson (`uvx` one-liner first) applied to
      the portfolio's highest-real-usage project. Shipped as CAOShurong/
      benchlineage 81ee19a: "Try it without installing" section placed right
      after the evidence-chain figure — `uvx benchlineage demo my-bench
      --seed 20260804` + `verify` with expected `"valid": true` stated, plus
      a pointer from the Install section. Both commands live-verified on
      PyPI 0.3.8 before publishing (demo generated, verify returned valid,
      report written); repo check script green (83 files). No product code
      touched.
- [done 2026-08-26f] Integrity repair: this repository now actually follows its
      own recommendation. The seven-repos case study claimed contextcost's own
      `uv.lock` finding had been fixed with "one line in `.gitignore`" —
      measuring again showed that line had never been committed; the lockfile
      had grown to 116,440 tokens = 51% of the tree (226,143 before cut,
      proposal 55%, worse than any of the seven published repos). Shipped:
      `/uv.lock` ignored for real; same walk now 109,797 tokens, proposal 7.2%
      (CI uses `pip install .`, nothing consumes uv.lock); README hero row and
      landing-page self-row re-measured and corrected (was 161,453/46.9% and
      175,189/47.6% — three different stale numbers across surfaces, all
      wrong); case study gains an honest postscript instead of a silent edit;
      CHANGELOG Unreleased entry records it. 203 tests pass,
      `docs/build_docs.py --check` green. Lesson: self-referential claims need
      a check like any other number.
- [done 2026-08-26e] Third case study published + v0.5.2 released: the
      exact-counts post (`docs/case-studies/2026-08-26-exact-counts.md`) and
      `reproduce.sh --accurate` support existed only as uncommitted drafts —
      and the post's claim "released as v0.5.2" was false (PyPI/GitHub were
      both at 0.5.1, without the lockfile fix it cites). Shipped f6bd3e0:
      version bumped to 0.5.2, CHANGELOG dated entry added, tag pushed,
      release workflow green end-to-end, live-verified on PyPI (`latest:
      0.5.2`), GitHub Release assets present (wheel/sdist/SHA256SUMS), and
      cold-user path re-checked (`uvx --refresh contextcost --version` →
      0.5.2, self-measure JSON schema 1). The savings in the new post are now
      backed by an installable release instead of an unreleased tree. 203
      tests pass.
- [done 2026-08-26d] Credibility fix that unblocks distribution: the estimator
      used to breach its own printed error band the moment anyone verified it
      with `--accurate` on a lockfile-heavy repo — `contextcost --accurate .`
      on this repo reported "21.5% OUTSIDE its ±14% band", the headline honesty
      claim failing at exactly the moment a sceptical reader checks it. Root
      cause: 437 real lockfiles scanned, 289 (66%) were mis-billed as generic
      structured-dense (3.38 chars/token) when they actually cost ~2.2
      (hash-dense punctuation merges poorly). Added a hashy-lockfile ratio
      (2.2, measured) and folded three real lockfile excerpts into
      `docs/calibrate.py`'s corpus so `ERROR_BOUND` is now genuinely measured
      against lockfiles; the same run now reports "3.0% within its ±23% band".
      README's ±14% promises (which were untested against lockfiles) were
      corrected to ±23% and to state the bound covers source/config/lockfiles
      but not minified output. This is the precondition for the case-study post
      — every published number must survive verification. 203 tests pass; not
      released (awaiting next version tag).
- [done 2026-08-26c] Landing page upgraded to all seventeen measured repos:
      the Pages site still led with only the first batch, hiding buildkit
      89.5% and yq 0.7% — the spread that is the tool's best argument. All
      rows re-measured live with v0.5.1 before publishing (gitleaks/ruff
      upstream drift quoted fresh); hero switched to buildkit; --check
      staleness gate intact; 201 tests green; shipped d06111f.

- [done 2026-08-26b] Community surface + launch readiness: GitHub Discussions
      enabled (repo had no discussion venue for the traffic a launch post
      would send); `Questions & feedback` issue-template routes "number
      looks wrong" reports to `--accurate --json`; README Share-it section
      links the forum. Ready-to-post Reddit / Show HN / X drafts written in
      docs/engagement/launch-drafts.md from live-re-verified numbers only,
      each with maker disclosure + re-verify-at-posting checklist. Cold-user
      path re-verified end-to-end: `uvx contextcost` v0.5.1 on rclone
      (7,889,081 → 6,169,673, 22% saved) and astropy (7,881,727 → 3%,
      matches published figure exactly). Not posted; external posting needs
      user approval.

- [done 2026-08-26] Integrity audit of every published number + engagement
      refresh: re-ran v0.5.1 `--json` live on all eleven local checkouts at
      the commits cited in both case studies — all figures reproduce exactly
      except gitleaks' total (upstream drift −152 tokens, share unchanged at
      33.8%). The posts are verifiably true, not just claimed. LibreChat
      drafts rewritten against PR #15089's current body (old accounting
      question already answered there); new Draft A engages the summary-part
      contract and asks about unbounded summary growth. Not posted; external
      posting requires user approval.

- [done rev 157] Social preview card (`docs/assets/social-card.png`,
      1280×640): pasting the repo link into Slack/Discord/X previously
      rendered bare text — zero share-surface despite three case studies
      existing. Landing page now carries `og:image`/`twitter:card` showing a
      real plotly.js measurement (63.8M tokens in, 42% measured saving) plus
      a rendered terminal screenshot; same card embedded at the top of the
      README. Verified live on Pages after deploy (og meta present, PNG
      served with matching byte length); CI+CodeQL green; 201 tests pass;
      no product code touched.

- [done rev 156] Distribution release v0.5.1: the rewritten README (plotly.js
      hero + `uvx` one-liner) and CLI next-steps hook existed only on main —
      the PyPI landing page still showed the old mechanism-first text.
      Tagged `v0.5.1`, release workflow green end-to-end, verified live on
      PyPI (`latest: 0.5.1`). Also: LibreChat engagement research —
      "contextcost" in their tracker matches *their own* Context Cost UI
      feature, not us; adjacent open thread is #15089 (Manual Context
      Compaction). Unposted comment drafts prepared in
      docs/engagement/librechat-drafts.md; external posting needs user
      approval.
- [done rev 155] `--delta` accepts a git revision as BASE (`contextcost .
      --delta main`): the ref is exported via `git archive` into a temp tree
      removed at exit, so measuring a PR's cost needs no second clone.
      Directory beats same-named ref; unknown ref exits 2 with git's own
      message. (Shipped: refsnapshot.py + CLI wiring, 7 new tests; verified
      on this repo --delta HEAD (+2,517 uncommitted) and plotly.js --delta
      v4.0.0-rc.0 (+645,796 / 179 files).)

- [done rev 8] GitHub Action `contextcost/action`: on pull_request, comment the
      delta ("this PR adds +41,882 tokens, 92 % of it a lockfile"). Needs
      `--json` first. This is the growth loop: every install markets the CLI.
      (Shipped e09d367: core `delta.py` (per-file compare + head-tree
      attribution) + `--delta BASE` printing through `--markdown`/`--json`;
      composite `action.yml` posts/updates one marked PR comment; 11 new
      tests = 150 total; verified on two checkouts of this repo with a
      synthetic lockfile commit, +41,797 tokens split 32k lockfile / 9.5k
      unclassified.)
- [done rev 6] `--json` machine output (stable schema, versioned) — prerequisite for
      the Action and for editor integrations.
      (Shipped 3532dbc: `"schema": 1` in every payload, contract as data in
      json_schema.CONTRACT walked against real output by tests, single
      build_payload() assembly path, `--json-schema` prints the contract;
      6 new tests, verified as an Action-style consumer on plotly.js.)
- [done rev 7] `--markdown` report suited for README badges / PR comments.
      (Shipped db9e959: `src/contextcost/markdown.py` second renderer — pipe
      tables, blockquoted saving, fenced gitignore block, `--badge` prepends
      a shields.io badge line; honesty rules carried over (bound, measured
      saving, deferred as question); pipes in paths escaped; 10 new tests;
      verified on this repo (63k tokens + badge) and plotly.js (63.2M).)

## P2 — agent-native surface

- [done rev 9] MCP server mode (`contextcost mcp`, stdio): tools
      `estimate(repo)` and `propose(repo)` so Claude/Cursor agents call it
      directly. Stdlib JSON-RPC only — keep the zero-dep core intact.
      (Shipped aefd046: mcp_server.py ~150 lines stdlib-only, minimal
      protocol initialize/ping/tools.list/tools.call, errors-as-data; 18
      tests; live-verified on plotly.js stdio session — estimate
      63.83 M tokens, propose 26.8 M saved / 42 %, bad path −32603.)
- [done rev 10] Docs page "Use with coding agents": copy-paste configs for Claude
      Code, Cursor, Codex.
      (Shipped 18d6987: docs/coding-agents.md — `claude mcp add` command +
      committed .mcp.json, .cursor/mcp.json, `codex mcp add` +
      ~/.codex/config.toml; formats verified against current client docs;
      ready-to-use prompt + honest-notes section; linked from README MCP
      section. 176 tests green, live plotly.js stdio re-verified
      63.83M tokens / saved 26.8M = 42%.)

## P3 — hygiene

- [done rev 11] `--top N`, `--fail-over <budget>` exit codes for CI gating
      (mirror repomix's `--token-budget` so migrations from it are easy).
      NOTE: `--top N` already existed since v0.1; this item was really about
      `--fail-over`. (Shipped: exit 4 = over budget, distinct from 1 = waste,
      exact total under --accurate else estimate with ±14% band in message;
      negative budget is usage error 2; 5 new tests = 181; verified live on
      this repo — 75,546 tokens passes 500k, fails 1k — and plotly.js —
      fails 1M, passes 100M.)
- [done rev 12] Windows path-separator audit of every rule in classify.py.
      (Shipped: no user-visible bug existed — the walker always normalises to
      `/`. Audit pinned the contract with 9 tests: directory rules fail
      closed on backslash paths on every platform; name rules' verdicts are
      host-basename-defined and documented; dense rule proven
      separator-blind; banner read via os.path.join proven for both
      separators; walker pinned to emit `/` always. 190 tests green;
      verified on this repo (77,338 tokens) and plotly.js (63.83M).)

## Release discipline

Ship v0.4.0 when P0 + `--json` land (feature release), then v0.5.0 with the
Action + MCP. Every release: changelog entry, tag, PyPI upload, README demo
refresh if output shape changed.

- [done rev 154] v0.5.0 shipped 2026-08-25: tag `v0.5.0`, release workflow
      green end to end (test matrix ubuntu/windows × py3.9/3.14, twine
      --strict, PyPI trusted publish), live-verified on PyPI (`latest: 0.5.0`)
      and GitHub Release (wheel + sdist + SHA256SUMS + attestations).

## Explicitly rejected (for now)

- Tokenizer-accurate by default (breaks zero-dep promise).
- Watching/scanning modes (out of scope; this is a measurement tool).
