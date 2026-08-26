#!/usr/bin/env bash
# scripts/publish.sh — build the codebot journal and publish the generated
# HTML to the gh-pages branch of origin.
#
# GitHub Pages serves the prebuilt site as-is (we do NOT use Jekyll, hence
# .nojekyll). The nix-journal repo's `main` branch keeps the source
# (docs/, zensical.toml, overrides/); gh-pages keeps only built output.
#
# The GitHub repo is published as a <user>.github.io user site, so it is
# served at the domain ROOT (https://thsigit.github.io/), not under a
# /nix-journal/ subpath. zensical's internal theme emits root-absolute links
# (/reports/, /2026-.../), which only resolve correctly under root serving.
# The build for publishing therefore overrides site_url to the root URL (via a
# temporary config copy). The local build (systemd / manual) keeps the config's
# own site_url (journal.home.arpa) and also serves at root.
#
# IMPORTANT: the publish build writes to a throwaway dir, never to the live
# /srv/www/codebot/journal, so local serving is left untouched.
#
# Usage: ./scripts/publish.sh [--no-build]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

NO_BUILD=0
[[ "${1:-}" == "--no-build" ]] && NO_BUILD=1

GH_SITE_URL="https://thsigit.github.io/nix-journal/"
BUILD_OUT="$REPO_DIR/.publish_tmp"

cleanup() { rm -rf "$BUILD_OUT" "${TMP_CONF:-}"; }
trap cleanup EXIT

if [[ "$NO_BUILD" -eq 0 ]]; then
  echo "==> Building site with zensical (site_url=$GH_SITE_URL)"
  CONF="$REPO_DIR/zensical.toml"
  TMP_CONF="$(mktemp "$REPO_DIR/zensical.publish.XXXX.toml")"
  sed -e "s#^site_url = .*#site_url = \"$GH_SITE_URL\"#" \
      -e "s#^site_dir = .*#site_dir = \".publish_tmp\"#" \
      "$CONF" > "$TMP_CONF"
  zensical build -f "$TMP_CONF"
fi

SRC="$BUILD_OUT"
if [[ ! -d "$SRC" ]]; then
  echo "ERROR: built site not found at $SRC (run without --no-build)" >&2
  exit 1
fi

WT="$(mktemp -d /tmp/codebot-gh-pages.XXXX)"
cleanup_wt() { git worktree remove "$WT" --force 2>/dev/null || rm -rf "$WT"; }
trap 'cleanup; cleanup_wt' EXIT

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
