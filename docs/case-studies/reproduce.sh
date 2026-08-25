#!/usr/bin/env bash
# Reproduce every number in docs/case-studies/2026-08-25-seven-repos.md.
#
# Usage:   bash docs/case-studies/reproduce.sh [path-to-checkouts-parent]
# Default parent: the layout used for the original measurements
# (E:/Codex/Projects, i.e. <parent>/plotly/plotly.js, <parent>/dask/dask, ...).
#
# Requires: uv (https://docs.astral.sh/uv/) and any Python 3 — runs
# contextcost without installing it. Each repo is measured twice: as-is
# and with the tool's proposal applied; "saved" is the difference of two
# real walks, never arithmetic on guesses.
#
# Exit codes: contextcost exits 0 when a repo is clean and 1 when it has
# waste to propose — both are expected here; anything >= 2 is a real error.
set -u

PARENT="${1:-E:/Codex/Projects}"
HERE="$(cd "$(dirname "$0")" && pwd)"
case "$HERE" in
  /*) HERE="$(cygpath -w "$HERE")" ;;  # native python needs a Windows path
esac

repos=(
  "plotly/plotly.js"
  "dask/dask"
  "pandas-dev/pandas"
  "keycloak/keycloak"
  "rclone/rclone"
  "astropy/astropy"
)
# contextcost itself lives outside the parent; adjust or drop as needed
self_repo="$(cd "$HERE/../.." && pwd)"
self_repo="$(cygpath -w "$self_repo")"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

printf "%-20s %12s %12s %12s %7s\n" REPO BEFORE AFTER SAVED SHARE
failed=0
for rel in "${repos[@]}" "contextcost"; do
  if [ "$rel" = "contextcost" ]; then
    path="$self_repo"
  else
    path="$PARENT/$rel"
  fi
  rc=0
  uvx contextcost "$path" --json >"$tmp" 2>/dev/null || rc=$?
  if [ "$rc" -ge 2 ]; then
    echo "error: $rel: contextcost exited $rc" >&2
    failed=1
    continue
  fi
  python "$HERE/summarize.py" "$rel" <"$tmp" || failed=1
done

echo
echo "Notes:"
echo "  - estimate tier (±14% measured bound); add --accurate for exact cl100k_base counts"
echo "  - 'after' re-walks the repository with the proposal applied (measured, not subtracted)"
exit "$failed"
