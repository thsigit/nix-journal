#!/usr/bin/env bash
# scripts/publish.sh — build the codebot journal and publish the generated
# HTML (journal/) to the gh-pages branch of origin.
#
# GitHub Pages serves the prebuilt site as-is (we do NOT use Jekyll, hence
# .nojekyll). The nix-journal repo's `main` branch keeps the source
# (docs/, zensical.toml, overrides/); gh-pages keeps only built output.
#
# Usage: ./scripts/publish.sh [--no-build]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

NO_BUILD=0
[[ "${1:-}" == "--no-build" ]] && NO_BUILD=1

if [[ "$NO_BUILD" -eq 0 ]]; then
  echo "==> Building site with zensical"
  zensical build -f "$REPO_DIR/zensical.toml"
fi

SRC="$REPO_DIR/journal"
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: built site not found at $SRC (run without --no-build)" >&2
  exit 1
fi

WT="$(mktemp -d /tmp/codebot-gh-pages.XXXX)"
cleanup() { git worktree remove "$WT" --force 2>/dev/null || rm -rf "$WT"; }
trap cleanup EXIT

echo "==> Preparing gh-pages worktree"
if git show-ref --verify --quiet refs/heads/gh-pages; then
  git worktree add "$WT" gh-pages
elif git fetch origin gh-pages 2>/dev/null; then
  git worktree add "$WT" gh-pages
else
  git worktree add -b gh-pages "$WT" --orphan
fi

echo "==> Syncing built site into gh-pages"
cd "$WT"
git rm -r --quiet --ignore-unmatch '*' 2>/dev/null || true
find . -maxdepth 1 -mindepth 1 ! -name '.git' -exec rm -rf {} +
cp -r "$SRC"/. "$WT"/
touch "$WT/.nojekyll"
git add -A

if git diff --cached --quiet; then
  echo "==> No changes to publish."
else
  MSG="publish: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git commit -q -m "$MSG"
  echo "==> Committed: $MSG"
  if git remote get-url origin >/dev/null 2>&1; then
    git push origin gh-pages
    echo "==> Pushed gh-pages to origin."
  else
    echo "==> No 'origin' remote configured; commit left in local gh-pages branch."
    echo "    Add a GitHub remote and re-run to push."
  fi
fi

echo "==> Done."
