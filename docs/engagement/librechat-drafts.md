# LibreChat engagement drafts (updated 2026-08-26)

**Status: NOT POSTED.** Posting anything externally requires explicit user
approval first. These are prepared, researched drafts only.

## Research summary

Searching `danny-avila/LibreChat` for "contextcost" hits LibreChat's own
"Context Cost" UI feature — **not** our tool. Adjacent threads:

- **#15089 (open draft PR, berry-13)** "🗜️ feat: Manual Context Compaction" —
  user-triggered branch summarization; the summary persists as a `summary`
  content part on an assistant message, `formatAgentMessages` treats it as the
  context boundary, everything before it is dropped from every later prompt.
  Re-checked 2026-08-26: the PR body answers the accounting question the old
  draft asked (`metadata.summaryUsedTokens` caps the client-side gauge at the
  compacted baseline). Draft rewritten below accordingly.
- **#9543 (closed → shipped)** "Add context window usage to UI" — context
  gauge + composition breakdown landed via #13670 / v0.8.3. Users now *see*
  composition; they still lack a tool to answer "what should I remove?".
- **#7482 (open issue)** "Automatic context compaction" — demand signal;
  #15089 is the manual half of it.

The natural, non-spammy angle stays repo-side: before a conversation even
starts, repository content an agent indexes (lockfiles, build output,
fixtures) is a large share of every window, and no transcript-side compaction
removes it. Do not pitch in their tracker; unsolicited tool plugs there would
be spam. Link only if directly asked (Draft B).

## Draft A — comment on #15089 (Manual Context Compaction PR)

> Nice that this reuses the automatic detour's `summary` part contract instead
> of inventing a second boundary format — `formatAgentMessages` not needing to
> learn a new marker is the right call.
>
> One thing worth keeping in mind when judging how much this moves the gauge
> per session: compaction trims the *transcript* branch, but on agentic
> sessions a big chunk of the fixed per-turn input is repository-side content
> injected fresh each turn anyway — indexed files, tool/MCP outputs, build
> artifacts. I've been measuring that side on repos I work with (walk the
> tree, propose removable classes like vendored deps / generated code /
> recorded fixtures, then re-measure with them excluded): it ranges from
> ~0.7% on disciplined repos to ~90% where `vendor/` + generated protocol
> code dominate — lockfiles, snapshots and fixtures routinely account for a
> third to a half of everything an agent re-reads each turn. Compaction can't
> touch any of it, so a pre-flight repo-hygiene pass would compound with this
> rather than overlap: smaller floor under the transcript that the checkpoint
> then trims further.
>
> One behaviour question from the description: the consolidated summary grows
> through repeated compactions (`summarization.updatePrompt` folding the old
> checkpoint in), and being a persisted message part it re-ships in every
> later prompt. Is there any ceiling on it — e.g. capping the fold-in once
> the summary itself crosses some token share — or does an indefinitely long
> session just keep growing one ever-larger summary message?

(Why this works: engages with the PR's actual mechanism, contributes a real
measured observation without naming or linking the tool, and asks a grounded
design question. No pitch.)

## Draft B — reply if asked "what do you measure with?"

Only if a maintainer/user asks directly in-thread:

> I wrote a small local CLI for it ([contextcost](https://github.com/CAOShurong/contextcost))
> — walks the repo, proposes which file classes are dead weight, then
> re-measures so the saving is measured rather than guessed. Runs offline,
> zero dependencies. Happy to share numbers for any repo you're curious about.
