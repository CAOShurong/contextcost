# HONEST ASSESSMENT — contextcost (2026-08-25, user-mandated)

## The brutal baseline

- GitHub: **0 stars, 0 forks, 0 watchers.**
- PyPI ~263 downloads/month — almost entirely **our own CI matrix + local
  validation + uv caches**, not real users. Treat external real users as **≈ 0**.
- Conclusion: **no evidence any real human has ever used this.**

## "Good" is four separate questions

| Question | Verdict | Evidence |
| --- | --- | --- |
| Technically good? | **Yes** | measure→propose→re-measure moat; 147 tests green; `numeric` class cut plotly.js drift 29%→1.2%; `--accurate`, Action, MCP, CI gate all ship |
| Does anyone need it? | **Probably, but unproven** | The pain (AI reads 5× the tokens it should) is real; but repomix already owns the "pack my repo for the LLM" mindshare, and users don't *feel* the waste until they run it |
| Has anyone found it? | **No** | PyPI only. No site, no `npx`, no VSCode extension, no tutorial, no community post. Discoverability ≈ 0 |
| Does anyone stay? | **N/A** | 0 users, so 0 retention to measure |

## Root-cause ranking (why 0 stars)

1. **Distribution = 0 (primary).** repomix's 28k stars came from a website +
   `npx` + VSCode plugin + community tutorials. We have none of those. A
   developer cannot star what they have never heard of. This is the dominant
   cause, not feature gaps.
2. **No instant "wow".** Running it produces a table; the saving only registers
   if the user already cares about token cost. No 3-second "oh damn" moment.
3. **Value prop too abstract.** "waste identification + re-measurement" means
   nothing until demonstrated on a repo the reader knows.
4. **Mindshare timing.** repomix already occupies the category; we read as a
   late, narrower clone unless the re-measure differentiator is shown live.

## If still 0 stars in 3 months

**Keep, but pivot from features to distribution.** Stop adding capability.
The product is feature-complete enough to demo.收缩 risk is real only if
distribution experiments (below) also fail — then it becomes a portfolio /
resume project, not a growth bet. Decision gate: after one case-study post +
one `uvx`/site attempt, if <5 external stars in 30 days, freeze features and
treat as maintained portfolio piece.

## Highest-leverage moves (ordered)

1. **One real case-study post** ("I measured N well-known repos; X% of their
   tokens are waste") with live numbers — the actual cold-start path repomix
   and similar tools used. Targets discoverability + abstract-value at once.
2. **README hero rewrite**: 3-second before/after on a known repo (plotly.js
   real data, not invented) + `uvx contextcost <repo>` one-liner as the first
   thing a visitor sees.
3. **Next-step hook** in CLI output ("add to CI → generate badge") to convert
   one-shot runs into retained usage.
4. **Real user contact**: the LibreChat repo has 2 contextcost-adjacent
   issues — polite technical engagement there (no spam, no pitch) to find the
   first real users and learn what they actually want.

No feature work until distribution experiments have run.
