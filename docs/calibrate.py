"""Measure how wrong the estimator is, against a real tokenizer.

`estimate.py` prints an error bound beside every total, and the whole argument
for this tool is that a number carrying an honest bound beats a number
pretending to be exact. That argument is worth nothing if the bound itself was
chosen rather than measured -- which is what it was until this file existed.

So: encode a corpus with a real tokenizer, compare against the estimate, and
write the observed error into `ERROR_BOUND`. If the estimator gets worse, this
says so, and CI fails.

**Which tokenizer, and the honest caveat.** `cl100k_base` via `tiktoken`, which
is OpenAI's. Anthropic does not publish a tokenizer library, and neither do
most of the others, so there is no way to measure against every model an agent
might use. Byte-pair encoders trained on similar corpora land close to one
another on ordinary text, but "close" is doing real work in that sentence: the
bound below is measured against one public tokenizer and is a proxy for the
rest. That is a weaker claim than "±12%" looks, and it is the reason this
paragraph exists rather than living in a footnote.

The corpus is this repository's own source, tests, tooling and prose, plus
three synthetic dense samples. Reproducible anywhere the repository is checked
out, which is what lets CI re-run it -- and it also means every commit changes
the corpus slightly, which is why the published bound carries headroom over the
measured figure rather than sitting exactly on it.

Usage:
    python docs/calibrate.py            # measure and rewrite ERROR_BOUND
    python docs/calibrate.py --check    # fail if the estimator drifted
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from contextcost.estimate import ERROR_BOUND, estimate_tokens  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: The bound is rounded up to a multiple of this before being written, so that
#: a trivial corpus change does not produce a churn commit editing 0.1183 to
#: 0.1179. It also keeps the printed figure honest-looking rather than
#: falsely precise.
ROUNDING = 0.01

#: Headroom the published bound carries over the measured 95th percentile.
#: The corpus is this repository's own files, so *every commit changes it*.
#: A bound sitting exactly on the measurement would turn ordinary editing into
#: a red build, and the fix for a red build is to widen the bound -- which is
#: how a number stops meaning anything. Better to publish a slightly loose
#: bound on purpose and print the tight measurement beside it.
HEADROOM = 1.2


def corpus() -> list[tuple[str, str, str]]:
    """``(label, kind, text)`` for everything being measured.

    **Real files only.** The first version of this calibrated partly against
    the generated example repository from ``build_docs.py``, and that was
    worthless: the example is built by repeating a single line hundreds of
    times, which a byte-pair encoder compresses far better than any real
    source file. It reported the estimator as 54% wrong when most of that was
    the corpus being unlike anything a user owns.

    So the corpus is this repository's own source, tests, tooling and prose --
    genuinely written, genuinely varied -- plus two synthetic dense samples,
    which are the one case where synthetic is honest, since a hash column
    really is random by construction.
    """
    samples: list[tuple[str, str, str]] = []

    for relative in ("README.md", "CHANGELOG.md", "pyproject.toml"):
        path = os.path.join(ROOT, relative)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                samples.append((relative, "docs", handle.read()))

    for folder in ("src", "tests", "docs"):
        base = os.path.join(ROOT, folder)
        for current, _, names in os.walk(base):
            for name in sorted(names):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(current, name)
                with open(path, encoding="utf-8") as handle:
                    samples.append(
                        (os.path.relpath(path, ROOT), "python", handle.read())
                    )

    # Prose on its own. Every module here opens with several paragraphs of it,
    # and concatenated they are the only sample of unmarked English in the
    # repository -- worth measuring separately because the classifier sends
    # very little real-world content down the prose path.
    import ast

    docstrings = []
    for current, _, names in os.walk(os.path.join(ROOT, "src")):
        for name in sorted(names):
            if name.endswith(".py"):
                with open(os.path.join(current, name), encoding="utf-8") as handle:
                    found = ast.get_docstring(ast.parse(handle.read()))
                if found:
                    docstrings.append(found)
    if docstrings:
        samples.append(("<module prose>", "prose", "\n\n".join(docstrings)))

    samples.extend(_dense_samples())
    samples.extend(_cjk_samples())
    return samples


def _dense_samples() -> list[tuple[str, str, str]]:
    """Both halves of the dense population, which behave very differently."""
    import base64
    import random

    # Seeded so the corpus is identical on every machine and in CI.
    rng = random.Random(7)
    opaque = base64.b64encode(bytes(rng.randrange(256) for _ in range(9000))).decode()
    digests = "\n".join(f"{rng.randrange(16**64):064x}" for _ in range(220))
    structured = (
        "{"
        + ",".join(
            f'"pkg{n}":{{"version":"1.0.{n}","integrity":"sha512-{rng.randrange(16**40):040x}"}}'
            for n in range(600)
        )
        + "}"
    )
    return [
        ("<random base64>", "dense", opaque),
        ("<hex digests>", "dense", digests),
        ("<structured manifest>", "dense", structured),
    ]


def _cjk_samples() -> list[tuple[str, str, str]]:
    """Every script the estimator treats separately.

    These are in the corpus because CJK went entirely unmeasured until it was
    not: a single ratio for all of it under-counted traditional Chinese by 30%,
    which is the script this project's author writes documentation in.
    """
    simplified = (
        "这个工具用来测量代码仓库让人工智能编程助手读取时的成本，"
        "它会找出哪些文件在浪费预算，然后重新走一遍仓库来验证节省的数量。"
    )
    traditional = (
        "這個工具用來測量程式碼倉庫讓人工智慧編程助手讀取時的成本，"
        "並且找出哪些檔案在浪費預算，然後重新走一遍倉庫來驗證節省的數量。"
    )
    japanese = (
        "このツールはリポジトリをコーディングエージェントが読むときの"
        "コストを測定します。無駄なファイルを見つけて、実際に再測定します。"
    )
    korean = "이 도구는 저장소를 코딩 에이전트가 읽는 데 드는 비용을 측정합니다."
    return [
        ("<chinese simplified>", "prose", simplified * 8),
        ("<chinese traditional>", "prose", traditional * 8),
        ("<japanese>", "prose", japanese * 8),
        ("<korean>", "prose", korean * 10),
    ]


def measure() -> dict:
    import tiktoken

    encoder = tiktoken.get_encoding("cl100k_base")
    rows = []
    for label, kind, text in corpus():
        if not text.strip():
            continue
        actual = len(encoder.encode(text, disallowed_special=()))
        if actual < 50:
            # Relative error on a handful of tokens is dominated by rounding
            # and says nothing about the estimator.
            continue
        guess = estimate_tokens(text).tokens
        rows.append(
            {
                "label": label,
                "kind": kind,
                "actual": actual,
                "estimated": guess,
                "error": abs(guess - actual) / actual,
                "signed": (guess - actual) / actual,
            }
        )

    rows.sort(key=lambda r: -r["error"])
    errors = [r["error"] for r in rows]
    total_actual = sum(r["actual"] for r in rows)
    total_guess = sum(r["estimated"] for r in rows)
    return {
        "rows": rows,
        "worst": max(errors),
        # The figure that goes into ERROR_BOUND: 95th percentile rather than
        # the maximum, because one pathological file should not widen the
        # band reported for every ordinary one. The worst case is printed
        # alongside so it is not hidden.
        "p95": sorted(errors)[max(0, int(len(errors) * 0.95) - 1)],
        "median": sorted(errors)[len(errors) // 2],
        "aggregate": abs(total_guess - total_actual) / total_actual,
        "files": len(rows),
    }


def report(result: dict) -> None:
    print(
        f"{result['files']} files, {sum(r['actual'] for r in result['rows']):,} real tokens"
    )
    print(f"  median error     {result['median']:.1%}")
    print(f"  95th percentile  {result['p95']:.1%}")
    print(f"  worst file       {result['worst']:.1%}")
    print(
        f"  whole corpus     {result['aggregate']:.1%}  (what a repository total looks like)"
    )
    print()
    by_kind: dict[str, list[float]] = {}
    for row in result["rows"]:
        by_kind.setdefault(row["kind"], []).append(row["signed"])
    for kind, signed in sorted(by_kind.items()):
        mean = sum(signed) / len(signed)
        direction = "over" if mean > 0 else "under"
        print(
            f"  {kind:<8} {len(signed):>3} files, mean {mean:+.1%} ({direction}-estimates)"
        )
    print()
    print("  worst five:")
    for row in result["rows"][:5]:
        print(
            f"    {row['error']:>6.1%}  {row['label'][:44]:<44} "
            f"{row['estimated']:>7,} vs {row['actual']:>7,}"
        )


def main(check: bool) -> int:
    try:
        result = measure()
    except ImportError:
        print("tiktoken is not installed. pip install tiktoken", file=sys.stderr)
        return 2

    report(result)
    import math

    bound = math.ceil(result["p95"] * HEADROOM / ROUNDING) * ROUNDING
    bound = round(bound, 4)

    if check:
        if result["p95"] > ERROR_BOUND + 1e-9:
            print(
                f"\nERROR_BOUND is {ERROR_BOUND:.0%} but the 95th percentile error is "
                f"{result['p95']:.1%}. Run: python docs/calibrate.py",
                file=sys.stderr,
            )
            return 1
        print(
            f"\nERROR_BOUND {ERROR_BOUND:.0%} still covers the measured {result['p95']:.1%}."
        )
        return 0

    path = os.path.join(ROOT, "src", "contextcost", "estimate.py")
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    updated = re.sub(
        r"^ERROR_BOUND = [0-9.]+$", f"ERROR_BOUND = {bound}", source, flags=re.M
    )
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(updated)
    print(f"\nERROR_BOUND set to {bound} (95th percentile {result['p95']:.1%}).")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    raise SystemExit(main("--check" in sys.argv))
