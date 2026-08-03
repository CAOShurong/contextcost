You are continuing an unattended build of **contextcost**, a Python tool owned
by Shurong Cao (GitHub `CAOShurong`). It is the middle of the night in Hong
Kong. Nobody is awake, nobody can answer a question, and nobody can approve
anything. Decide everything yourself and write down what you decided.

This is one run in a chain of eight, forty minutes apart, all with this same
prompt. Each run picks up wherever the last one stopped. Being the first, the
last, or somewhere in the middle changes nothing about what you do.

## 1. Take the lock, or leave

A previous run in the chain may still be working. Two agents editing the same
tree is the one failure mode that destroys work rather than merely wasting a
window, so this check comes before anything else:

```bash
cd "C:/Users/35021/Desktop/VC/claude/contextcost"
if [ -f .build-lock ]; then
  age=$(( $(date +%s) - $(cat .build-lock) ))
  if [ "$age" -lt 2100 ]; then echo "LOCKED ${age}s ago"; else echo "stale (${age}s), taking over"; fi
fi
```

If it prints `LOCKED`, **stop now**. Change nothing, write nothing, and report
"another run held the lock". Losing one slot is cheap; two runs interleaving
edits is not.

Otherwise take it, and refresh it after every step you finish:

```bash
date +%s > .build-lock
```

It is in `.gitignore`. Never commit it. Delete it when you finish.

## 2. Read the brief

`HANDOFF.md` in that directory is authoritative: what the project is, why it
exists, the prior art, the design decisions and their reasons, the house
conventions inlined so you do not have to go looking, a progress log of what
each previous run did, and a numbered **Next** list.

Read it, then read nothing else unless something is genuinely ambiguous.
Re-deriving the house style by reading the neighbouring `evalint/` repository
costs a large fraction of a window and is the reason that section was inlined.

**Start writing within your first three tool calls.**

## 3. Keep working until you are cut off — do not stop after one item

**This overrides the task prompt if it reads otherwise.** The prompt that
started you says "do the next unstarted item", and taken literally that is
wrong: it would have you finish one thing in ten minutes and stop, leaving the
rest of the slot idle. The owner's actual constraint is a usage window that
expires whether or not it is used.

So: finish an item, commit, push, log it — then **immediately start the next
one**. Keep going until the list is empty or you are cut off mid-sentence.
Being cut off is the expected ending, not a failure; that is why every step
commits before the next begins.

Do not wind down early, do not stop to write a summary "while there is still
time", and do not decide the remaining work is too large to start. Start it.
Half of a committed module is worth more to the next run than a tidy stopping
point, because the log tells them exactly where you were.

## 3a. The Next list, in order

In order. Do not skip ahead to the interesting part, and do not rewrite a
module that already exists to suit your taste — the existing files are reviewed
and deliberate. Fix bugs in them, extend them, but do not replace them.

The two rules that make this project what it is, both stated at length in
HANDOFF.md:

- **A saving that was not re-measured is not a saving.** After proposing a set
  of exclusions, walk the repository again with them applied and report the
  real difference. `walk_repository` takes `extra_ignore=` for exactly this.
  Never subtract estimates and present the result as a measurement.
- **Every number the tool prints must be defensible**, including the ones that
  say "I cannot tell". An approximation labelled as an approximation is fine.
  An approximation presented as exact is the thing this whole portfolio argues
  against.

## 3b. Keep shell commands boring

Nobody is awake to approve anything, and a command that stalls waiting for a
click wastes the entire run. Permission matching works on command prefixes, so
an elaborate one-liner is many chances to hit something unrecognised: the
preflight for this very chain stalled on

    cd ... && python -m pytest -q 2>&1 | tee /tmp/out.txt; echo ---; grep -c ...

which is four commands and a pipe where one command would have done. Run
`python -m pytest -q` on its own and read what it printed. Split compound
commands into separate calls. Avoid `tee`, `xargs`, `awk`, `sed` and
process substitution unless there is no alternative — you almost always want
plain output you can read directly.

## 4. Run what you write

`python -m pytest -q` from the repo root. No `PYTHONPATH`, nothing installed —
`tests/conftest.py` handles the path. If you see
`ModuleNotFoundError: contextcost`, that file was deleted; restore it.

Then run the tool against a real repository, not a fixture:
`C:/Users/35021/Desktop/VC/claude/evalint/` is next door and has a `.gitignore`,
nested directories, binary files and one enormous generated CSV. Never claim
something works without having executed it.

## 5. Commit, every step, without being asked

A scheduled run can be killed at any instant — the run before this chain was
cut off mid-`Write`. Anything uncommitted at that moment is gone.

So: finish a step, run the tests, commit. Then the next step. Identity is
already configured globally and is correct; do not override it. Messages in the
house style — a subject line that states the change, then prose explaining the
decision and why the alternative was rejected. **No `Co-Authored-By: Claude`
trailer** on this project; that belongs to `evalint` alone.

Append a line to the progress log at the bottom of `HANDOFF.md` for each step,
including anything you got wrong and how you found out. That log is what makes
the next run in the chain cheap.

## 6. What you may do without asking

Build, test, commit, and `git push`. The remote exists already and is wired up
— https://github.com/CAOShurong/contextcost — created **private** on purpose,
pushed and verified before the chain started. Push freely and often.

Making it public is the **last step of the entire project**, and only once all
three of these hold:

- the test suite is green,
- `README.md` exists with generated figures,
- `.github/workflows/ci.yml` exists.

```bash
export PATH="/c/Program Files/GitHub CLI:$PATH"
gh repo edit CAOShurong/contextcost --visibility public --accept-visibility-change-consequences
```

The trailing flag is mandatory on gh 2.97 and the command fails without it.
`gh` is authenticated as `CAOShurong` (`gh auth status` prints the stale
pre-rename name `TeresaCSR` — ignore it; `gh api user` gives the truth).

Not before those three, though. A half-built public repository is worse than a
private one, and this is the account's sixth project — it is being looked at.

## 7. What you must not do

- **Do not tag a release. Do not touch PyPI.** A brand-new package needs a
  *pending* trusted publisher registered by hand on pypi.org, which needs the
  owner's browser session. Tagging first makes the release fail after
  everything else has already passed — this has happened before on this
  account. The final step is to *write the reminder*, not to attempt the
  release.
- Do not force-push, rewrite history, or delete anything outside the
  `contextcost` directory.
- Do not open issues, post anywhere, or contact anyone.

## 7b. Leave a trail the owner can actually read

Your report at the end of a run goes into a session the owner will never open.
As far as they are concerned, **a run that left no file behind did not happen.**

So before you finish, append your report to `NIGHT-LOG.md` in the repo root —
create it if absent — then commit and push it. Newest entry at the bottom, one
section per run, in this shape, and keep it short:

```markdown
## Run N — 04:00

**Did:** one line per step completed.
**Ran:** the command, and what it actually printed. Quote the pytest line.
**Got wrong:** anything, and how you found out. Write this even when it is
embarrassing -- especially then.
**Next run should:** the single most useful thing to pick up.
```

If you found a live lock and exited without working, still append a one-line
entry saying exactly that. A gap in this log must mean "that run never
started", never "that run did nothing and did not say so".

## 8. Finish cleanly

Delete `.build-lock`. Make sure the working tree is committed. Then report, in
English and briefly:

- which steps you completed,
- what you ran and what it printed,
- anything you got wrong and how you found out,
- what the next run should pick up,
- anything that genuinely needs the owner, stated as a specific action rather
  than a vague flag.

If the Next list is empty and everything is built, tested, documented and
pushed, do not invent scope. Improve what is weakest instead: tests for the
cases where the right answer is "cannot determine", a documented limitation you
have not yet pinned with a test, or accuracy of the estimator measured against
a real tokenizer. Then say so.
