#!/usr/bin/env bash
# Reproduce every number in docs/case-studies/2026-08-25-seven-repos.md
# (and docs/case-studies/2026-08-26-ten-more-repos.md, whose repositories are
# in the second list below). Pass --accurate as the first argument to
# reproduce the exact cl100k_base counts in
# docs/case-studies/2026-08-26-exact-counts.md instead (slower: tokenizes
# every file with tiktoken).
#
# Usage:   bash docs/case-studies/reproduce.sh [--accurate] [path-to-checkouts-parent]
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

ACCURATE=0
if [ "${1:-}" = "--accurate" ]; then
  ACCURATE=1
  shift
fi
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
# Repositories of the ten-more-repos case study (2026-08-26). Their local
# checkouts use a flat <parent>/<name> layout, so each entry is "name path".
more_repos=(
  "buildkit moby/buildkit"
  "lazygit jesseduffield/lazygit"
  "bat sharkdp/bat"
  "uv astral-sh/uv"
  "ruff astral-sh/ruff"
  "gitleaks gitleaks/gitleaks"
  "trufflehog trufflesecurity/trufflehog"
  "xarray pydata/xarray"
  "restic restic/restic"
  "yq mikefarah/yq"
)
# contextcost itself lives outside the parent; adjust or drop as needed
self_repo="$(cd "$HERE/../.." && pwd)"
self_repo="$(cygpath -w "$self_repo")"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

printf "%-20s %12s %12s %12s %7s\n" REPO BEFORE AFTER SAVED SHARE
failed=0
measure() {  # measure NAME PATH
  rc=0
  if [ "$ACCURATE" = 1 ]; then
    uvx --from "contextcost[accurate]" contextcost --accurate "$2" --json >"$tmp" 2>/dev/null || rc=$?
  else
    uvx contextcost "$2" --json >"$tmp" 2>/dev/null || rc=$?
  fi
  if [ "$rc" -ge 2 ]; then
    echo "error: $1: contextcost exited $rc" >&2
    failed=1
    return
  fi
  python "$HERE/summarize.py" "$1" <"$tmp" || failed=1
}
for rel in "${repos[@]}"; do
  measure "${rel##*/}" "$PARENT/$rel"
done
for entry in "${more_repos[@]}"; do
  set -- $entry
  [ -d "$PARENT/$2" ] && measure "$1" "$PARENT/$2" || echo "skip: $1 (no checkout at $PARENT/$2)" >&2
done
measure contextcost "$self_repo"

echo
echo "Notes:"
if [ "$ACCURATE" = 1 ]; then
  echo "  - exact tier (cl100k_base; files above 2 MiB counted from a marked prefix sample)"
else
  echo "  - estimate tier (±23% measured bound); add --accurate for exact cl100k_base counts"
fi
echo "  - 'after' re-walks the repository with the proposal applied (measured, not subtracted)"
exit "$failed"
