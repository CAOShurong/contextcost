# Launch-post drafts (NOT posted — external posting requires user approval)

*Prepared 2026-08-26 by the product-agent track. Every number below is real
`contextcost --json` output, verifiable with `uvx contextcost <repo>`.
Source data: [seven-repo study](../case-studies/2026-08-25-seven-repos.md),
[ten-more-repos study](../case-studies/2026-08-26-ten-more-repos.md),
[repomix head-to-head](../case-studies/2026-08-26-vs-packing.md).*

---

## Draft A — Reddit r/LocalLLaMA / r/ClaudeAI style

**Title:** I measured 17 open-source repos for "AI reading cost" — up to 89% of
their tokens are waste (buildkit), one repo is 99.3% clean (astropy+others)

I built a small CLI tool that measures what it costs an AI agent to *read*
a repository — every file competes for the same context window, and a lot of
files don't earn their place. Then I ran it on 17 well-known repos. Full
methodology and per-commit numbers in the repo README; short version:

| Repo | Tokens to read | Waste |
| --- | ---: | ---: |
| moby/buildkit | 14.6M | **89.5%** |
| jesseduffield/lazygit | 5.8M | 77.8% |
| plotly.js | 63.8M | 42.0% |
| sharkdp/bat | 53.7M | 55.8% |
| astral-sh/ruff | 20.7M | 50.2% |
| astropy | 7.9M | 2.7% |
| mikefarah/yq | 420K | 0.7% |

The interesting result is the spread: there's no universal "waste percentage".
Compiled bundles, lockfiles, recorded test fixtures and generated docs eat
agent context in some repos and are nearly absent in others.

What I think makes this more than a token counter: the tool doesn't just
estimate savings arithmetically. It proposes cuts, then **re-walks the repo
with the proposal applied**, so each saving is an observed measurement, not
a subtraction. On plotly.js the estimator claimed 63.8M tokens; the real
tokenizer said 63.36M — 0.7% off.

Try it on your own repo (no install): `uvx contextcost .`

Transparency: I made this tool, so treat the numbers as claims to check, not
facts to trust — every table above links commits and reproduction commands.
Happy to run it on any repo you're curious about.

---

## Draft B — Hacker News "Show HN" style

**Title:** Show HN: Contextcost – measure how much of your repo is dead weight
for AI agents

Most "repo → LLM" workflows bill every file to the same context window:
lockfiles, minified bundles, generated fixtures and all. This tool walks a
repository, estimates its token cost (with a published error bound), proposes
cuts where the filesystem itself proves files aren't hand-written work, and
then re-measures with the proposal applied — so the reported saving is a
measurement, not arithmetic.

Numbers from real checkouts: moby/buildkit 89.5% waste, lazygit 77.8%,
plotly.js 42%, astropy 2.7%, yq 0.7%. The spread across repos turned out to
be the finding.

Single command, zero dependencies: `uvx contextcost <repo>` (or `--accurate`
for exact cl100k_base counts). There's also a GitHub Action that posts the
context delta on pull requests.

Repo: https://github.com/CAOShurong/contextcost
Case studies with per-commit repro commands:
https://github.com/CAOShurong/contextcost/tree/main/docs/case-studies

---

## Draft C — X/Twitter thread skeleton

1/ Agents read your repo as tokens — but not all tokens deserve to be read.
I measured 17 OSS repos. buildkit: 89% waste. yq: 0.7%. The spread IS the story 🧵

2/ What counts as waste? Files the filesystem itself disproves as hand-written:
generated code ("DO NOT EDIT" headers), lockfiles, minified dist/, recorded
test fixtures. Nothing opinionated — every cut is provable.

3/ plotly.js: 63.8M tokens to read; 26.8M provably wasted. That's ~134 full
200K context windows spent mostly on JSON number matrices and minified output.

4/ Savings here are MEASURED: propose cuts → re-walk with proposal applied →
report the difference. Not subtraction. Estimator landed 0.7% off the real
tokenizer on plotly.js (band: ±23%, recalibrated after lockfile/numeric-data drift showed the old ±14% was unmeasured).

5/ One command, no install: `uvx contextcost .`
GitHub Action for PR deltas, MCP server for coding agents, MIT, zero deps.
https://github.com/CAOShurong/contextcost

---

## Posting checklist (when user approves)

- [ ] Re-run all cited numbers live at posting time (upstream may have moved).
- [ ] Reddit: pick ONE subreddit, post Draft A with title adjusted to sub norms;
      reply to questions with `--accurate` evidence, never defensiveness.
- [ ] HN: Show HN, weekday morning US time; include "Ask me anything" posture;
      expect methodology challenges — answer with the re-measurement section.
- [ ] X: thread Draft C; pin repo link; paste landing page URL for card preview.
- [ ] After posting: watch Discussions (enabled) + issues daily for a week;
      respond within hours, log every question as backlog signal.
