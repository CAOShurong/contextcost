"""Print one summary row from a contextcost --json payload.

Usage: python summarize.py NAME < report.json
Shared by reproduce.sh so the case-study numbers stay reproducible
with a single command. Exits 1 with a clear message when the payload
is missing or malformed.
"""

import json
import sys


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "?"
    try:
        d = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"error: {name}: invalid JSON on stdin ({exc})", file=sys.stderr)
        return 1
    try:
        before = int(d["walk"]["tokens"])
    except (KeyError, TypeError, ValueError):
        print(f"error: {name}: payload has no walk.tokens", file=sys.stderr)
        return 1
    r = d.get("reduction") or {}
    after = int(r.get("after", before))
    saved = int(r.get("saved", 0))
    share = saved / before * 100 if before else 0.0
    print(f"{name:<20} {before:>12,} {after:>12,} {saved:>12,} {share:>6.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
