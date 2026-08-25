# LibreChat engagement drafts (prepared 2026-08-25)

**Status: NOT POSTED.** Posting anything externally requires explicit user
approval first. These are prepared, researched drafts only.

## Research summary

Searching `danny-avila/LibreChat` for "contextcost" hits LibreChat's own
"Context Cost" UI feature — **not** our tool. The genuinely adjacent threads:

- **#15089 (open PR)** "Manual Context Compaction" — user-triggered
  summarization checkpoint; everything before the boundary is dropped from the
  prompt. Directly about shrinking what each turn re-reads.
- **#9543 (closed → shipped)** "Add context window usage to UI" — context
  gauge + composition breakdown landed via #13670 / v0.8.3. Users now *see*
  composition; they still lack a tool to answer "what should I remove?".
- **#14931 (open)** tokenConfig rate overrides on built-in endpoints — cost
  sensitivity signal.

Conclusion: LibreChat has strong demand for context visibility and is building
compaction. The natural, non-spammy angle is repo-side: before a conversation
even starts, the repository files an agent indexes are a large share of every
window — that's the gap contextcost measures. Do not pitch in their tracker;
their issue tracker is not our distribution channel and unsolicited tool plugs
there would be spam.

## Draft A — comment on #15089 (Manual Context Compaction PR)

> This is exactly the right lever — most overflow I run into isn't one huge
> message, it's accumulated file content from indexing/greps that no single
> turn needs anymore.
>
> One thing I've started measuring before blaming the conversation history:
> how much of the fixed per-turn cost comes from the *repository* side rather
> than the transcript. On the projects I work on, lockfiles, build output and
> recorded test fixtures routinely account for 20–45% of everything an agent
> reads per session (measured by re-walking with those classes excluded, so
> it's an observation, not an estimate). If compaction lands, a pre-flight
> repo-hygiene pass would compound with it nicely — smaller floor under the
> transcript that compaction then trims.
>
> Question on the accounting section: does the checkpoint's token count get
> subtracted from the pre-compaction branch total in the usage display, or is
> the saved amount only visible as the drop at the next model call?

(Why this works: purely technical engagement with the PR's mechanism; shares
a real measurement without naming or linking the tool.)

## Draft B — reply if asked "what do you measure with?"

Only if a maintainer/user asks directly in-thread:

> I wrote a small local CLI for it ([contextcost](https://github.com/CAOShurong/contextcost))
> — walks the repo, proposes which file classes are dead weight, then
> re-measures so the saving is measured rather than guessed. Runs offline,
> zero dependencies. Happy to share numbers for any repo you're curious about.
