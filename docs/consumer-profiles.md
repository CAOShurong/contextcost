# Consumer profiles

ContextCost profiles answer one narrow question: **which text files are
eligible after a tool's documented ignore files are applied?** They do not
claim to reproduce the prompt sent by a live product.

## Inputs and destinations

| consumer | inputs added to nested `.gitignore` rules | proposal destination |
| --- | --- | --- |
| `generic` | none | `.gitignore` |
| `cursor` | `.cursorignore` | `.cursorignore` |
| `aider` | `.aiderignore` | `.aiderignore` |
| `repomix` | `.ignore`, `.repomixignore`, `.git/info/exclude` | `.repomixignore` |

`--no-gitignore` disables nested `.gitignore` rules and
`.git/info/exclude`; consumer-native files remain active. The JSON report names
the consumer, the ignore inputs that actually existed, and the destination for
the proposal.

## Why these files

- [Cursor's security documentation](https://www.cursor.com/security) says
  `.cursorignore` can keep paths out of AI requests. Cursor also uses
  `.gitignore` for indexing, but indexing and direct Agent access are not the
  same boundary; ContextCost therefore writes to `.cursorignore`.
- [Aider's large-repository guidance](https://aider.chat/docs/faq.html) uses
  `.aiderignore`, with `.gitignore` syntax, to remove irrelevant parts of a
  monorepo from its repository map.
- [Repomix configuration](https://repomix.com/guide/configuration) documents
  `.gitignore`, `.git/info/exclude`, `.ignore`, and `.repomixignore`, with the
  latter using `.gitignore` syntax.
- [Git's own documentation](https://git-scm.com/docs/gitignore) states that
  `.gitignore` is for intentionally untracked files and does not affect files
  already tracked. A product can still choose to treat the pattern as its own
  context filter, but Git itself will not remove that file from the index.

## Deliberate limits

The profiles do not model proprietary tokenizers, semantic retrieval, repo
maps, compression, command-line include/exclude overrides, or product-specific
built-in patterns. Repomix, for example, has default exclusions and optional
compression that can make its packed output smaller than this eligible-file
estimate. Cursor can distinguish indexing from direct Agent access. Aider can
limit itself to a subtree.

Those differences are why ContextCost prints an estimated repository-scale
number with an error bound, not a claim about one request or a billing ledger.
The consumer profile makes the file-selection premise inspectable; it does not
turn an estimate into telemetry.
