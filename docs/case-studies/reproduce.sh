#!/usr/bin/env bash
# Reproduce every number in docs/case-studies/2026-08-25-seven-repos.md
# (and docs/case-studies/2026-08-26-ten-more-repos.md, whose repositories are
# in the second list below).
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
  uvx contextcost "$2" --json >"$tmp" 2>/dev/null || rc=$?
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
echo "  - estimate tier (±14% measured bound); add --accurate for exact cl100k_base counts"
echo "  - 'after' re-walks the repository with the proposal applied (measured, not subtracted)"
exit "$failed"
