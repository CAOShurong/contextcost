#!/usr/bin/env python3
"""Render docs/index.html — the GitHub Pages landing page.

One static file, no build system. Every number on the page comes from
`docs/case-studies/reproduce.sh` output (see the case study for the full
run), never from typing: a landing page quoting a saving the tool no longer
produces is the exact failure this project argues against. Re-run
`python docs/build_site.py --check` to fail CI when the page goes stale.

The page's job is distribution, not documentation: a visitor should see
*what the tool does*, *one real number from a repo they know*, and *the
uvx one-liner* within three seconds of arriving.
"""

from __future__ import annotations

import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

#: All seventeen repositories measured across both case studies, re-run live
#: with `contextcost --json` on 2026-08-26 (v0.5.1, same machine, same hour).
#: Every figure below matched the published case studies exactly except
#: gitleaks (upstream drift −152 tokens, share unchanged) and ruff (upstream
#: drift, 50.2% → 49.8%) — the page quotes the fresh run. Kept in one place
#: so --check has a single source to compare against.
REPOS = [
    (
        "moby/buildkit",
        "https://github.com/moby/buildkit",
        14_600_569,
        1_529_637,
        13_070_932,
    ),
    (
        "jesseduffield/lazygit",
        "https://github.com/jesseduffield/lazygit",
        5_766_190,
        1_278_993,
        4_487_197,
    ),
    (
        "sharkdp/bat",
        "https://github.com/sharkdp/bat",
        53_715_389,
        23_737_443,
        29_977_946,
    ),
    ("astral-sh/uv", "https://github.com/astral-sh/uv", 8_855_618, 4_331_842, 4_523_776),
    (
        "astral-sh/ruff",
        "https://github.com/astral-sh/ruff",
        20_978_634,
        10_531_462,
        10_447_172,
    ),
    (
        "plotly.js",
        "https://github.com/plotly/plotly.js",
        63_831_059,
        37_008_917,
        26_822_142,
    ),
    ("dask", "https://github.com/dask/dask", 4_315_000, 2_308_363, 2_006_637),
    (
        "pandas",
        "https://github.com/pandas-dev/pandas",
        10_105_577,
        7_929_282,
        2_176_295,
    ),
    (
        "rclone",
        "https://github.com/rclone/rclone",
        7_889_081,
        6_169_673,
        1_719_408,
    ),
    (
        "trufflesecurity/trufflehog",
        "https://github.com/trufflesecurity/trufflehog",
        4_456_181,
        3_011_760,
        1_444_421,
    ),
    (
        "gitleaks",
        "https://github.com/gitleaks/gitleaks",
        300_980,
        199_238,
        101_742,
    ),
    (
        "keycloak",
        "https://github.com/keycloak/keycloak",
        18_687_556,
        17_290_337,
        1_397_219,
    ),
    (
        "pydata/xarray",
        "https://github.com/pydata/xarray",
        2_133_276,
        2_007_117,
        126_159,
    ),
    (
        "restic",
        "https://github.com/restic/restic",
        1_054_989,
        1_005_182,
        49_807,
    ),
    ("astropy", "https://github.com/astropy/astropy", 7_881_727, 7_669_606, 212_121),
    (
        "mikefarah/yq",
        "https://github.com/mikefarah/yq",
        420_446,
        417_457,
        2_989,
    ),
    # contextcost itself, measured last so the tool's own tree is stable
    # under this edit (2026-08-26 live run: 65 files, 47.6%).
    (
        "contextcost itself",
        "https://github.com/CAOShurong/contextcost",
        175_189,
        91_872,
        83_317,
    ),
]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>contextcost — what does it cost an AI agent to read your repo?</title>
<meta name="description" content="Measure what a repository costs an AI coding agent to read in tokens, find what is wasting that budget, and prove the saving by measuring it again.">
<meta property="og:type" content="website">
<meta property="og:title" content="contextcost — what does it cost an AI agent to read your repo?">
<meta property="og:description" content="42% of plotly.js's context budget is dead weight. Measure yours, get a verified proposal, see the saving re-measured.">
<meta property="og:image" content="https://caoshurong.github.io/contextcost/assets/social-card.png">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://caoshurong.github.io/contextcost/assets/social-card.png">
<style>
  :root {{ --ink:#101218; --paper:#e8eaf0; --muted:#787e8e; --waste:#e8765c; --saved:#7cc48c; }}
  * {{ box-sizing:border-box; margin:0; }}
  body {{ background:var(--ink); color:var(--paper); font:16px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; max-width:880px; margin:0 auto; padding:3rem 1.5rem 5rem; }}
  h1 {{ font-size:1.7rem; line-height:1.3; margin-bottom:.75rem; }}
  h2 {{ font-size:1.05rem; margin:2.5rem 0 .75rem; color:var(--paper); }}
  p, li {{ color:#c4c8d4; }}
  a {{ color:var(--saved); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
  .sub {{ color:var(--muted); margin-bottom:1.5rem; }}
  .try {{ background:#181b24; border:1px solid #2c303c; border-radius:8px; padding:1rem 1.25rem; font-size:1.05rem; margin:1.5rem 0; overflow-x:auto; }}
  .try b {{ color:var(--saved); font-weight:normal; }}
  .try .dim {{ color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; margin:1rem 0; font-size:.85rem; }}
  th {{ text-align:right; color:var(--muted); font-weight:normal; padding:.35rem .5rem; border-bottom:1px solid #2c303c; }}
  th:first-child, td:first-child {{ text-align:left; }}
  td {{ text-align:right; padding:.35rem .5rem; border-bottom:1px solid #22252f; white-space:nowrap; }}
  td:first-child {{ white-space:normal; }}
  td.save {{ color:var(--waste); font-weight:bold; }}
  footer {{ margin-top:3rem; color:var(--muted); font-size:.85rem; }}
</style>
</head>
<body>
<h1>What does it cost an AI agent to read your repository &mdash; and how much of that is waste?</h1>
<p class="sub">Free, open source (MIT), runs entirely locally. No tokenizer dependency.</p>

<div class="try"><b>$ uvx contextcost .</b><br><span class="dim"># no install, no config, results in seconds</span></div>

<h2>Measured on 17 well-known open-source repositories</h2>
<table>
<tr><th>Repository</th><th>Tokens to read</th><th>After proposal</th><th>Saved</th><th>Share</th></tr>
{rows}
</table>
<p>The "after" number is not arithmetic on guesses: contextcost proposes cuts,
then <em>walks the repository again</em> with the proposal applied. Estimates
carry a measured ±14% error bound; <code>--accurate</code> gives exact
cl100k_base counts (on plotly.js the estimate landed 0.7% off).</p>

<h2>The spread is the finding</h2>
<ul>
<li><strong>moby/buildkit &mdash; 89.5%, 13.1M of 14.6M tokens:</strong> a vendored <code>vendor/</code> tree plus generated protocol code. An agent fixing a Dockerfile frontend issue could lose 89% of its reading budget and miss nothing.</li>
<li><strong>dask &mdash; 46.5%:</strong> one lockfile (<code>pixi.lock</code>, 932K tokens) is 22% of the entire repository's context cost.</li>
<li><strong>mikefarah/yq &mdash; 0.7%:</strong> a disciplined repository correctly gets told it is clean. The tool does not invent waste.</li>
</ul>

<h2>Make it permanent</h2>
<div class="try"><b>$ contextcost . --write-ignore</b><br><span class="dim"># accept the proposal, confirm the saving once</span><br><br><b>$ contextcost . --fail-over 8000000</b><br><span class="dim"># then let CI fail when the budget creeps back</span></div>
<p>Or gate pull requests automatically with <a href="https://github.com/CAOShurong/contextcost#in-a-pull-request">the GitHub Action</a> &mdash; every PR gets a comment with its token delta. There is also an <a href="https://github.com/CAOShurong/contextcost/blob/main/docs/coding-agents.md">MCP server mode</a> so Claude Code, Cursor and Codex can call it directly.</p>

<footer>
Full methodology and reproduction commands:
<a href="https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-25-seven-repos.md">the seven-repo case study</a> and
<a href="https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-26-ten-more-repos.md">ten more repos (89.5% on buildkit down to 0.7% on yq)</a>.
Also: <a href="https://github.com/CAOShurong/contextcost/blob/main/docs/case-studies/2026-08-26-vs-packing.md">repomix vs contextcost on the same repo</a>.
Source: <a href="https://github.com/CAOShurong/contextcost">github.com/CAOShurong/contextcost</a>
&middot; <a href="https://pypi.org/project/contextcost/">PyPI</a>.
</footer>
</body>
</html>
"""


def rows() -> str:
    out = []
    for name, url, before, after, saved in REPOS:
        share = f"{saved / before * 100:.1f}%"
        out.append(
            f'<tr><td><a href="{url}">{html.escape(name)}</a></td>'
            f"<td>{before:,}</td><td>{after:,}</td>"
            f'<td class="save">{saved:,}</td><td class="save">{share}</td></tr>'
        )
    return "\n".join(out)


def build(check: bool) -> int:
    page = PAGE.format(rows=rows())
    path = os.path.join(HERE, "index.html")
    if check:
        with open(path, encoding="utf-8") as handle:
            current = handle.read()
        if current != page:
            print(
                "docs/index.html is stale. Run: python docs/build_site.py",
                file=sys.stderr,
            )
            return 1
        print("docs/index.html is up to date.")
        return 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(page)
    print(f"Wrote {path} ({len(page):,} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(build("--check" in sys.argv))
