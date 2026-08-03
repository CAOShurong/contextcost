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

## 3. Do the next unstarted item on the Next list

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
