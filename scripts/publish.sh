#!/usr/bin/env bash
# scripts/publish.sh -- build the codebot journal and publish the generated
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
STAGE_DIR="$REPO_DIR/build_docs"

WT=""
cleanup() {
  rm -rf "$BUILD_OUT" "$STAGE_DIR" "${TMP_CONF:-}"
  if [[ -n "$WT" && -d "$WT" ]]; then
    git worktree remove "$WT" --force 2>/dev/null || rm -rf "$WT"
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Preflight: prove we can push BEFORE spending minutes on a build.
#
# The original script did the build, the commit, and only then attempted the
# push. On 2026-09-29 the push failed (github.com was missing from
# known_hosts) and a month of posts went unpublished. Worse, the failure was
# unrecoverable by re-running: the local commit had already landed, so
# `git diff --cached --quiet` was true on the next run, the script printed
# "No changes to publish." and exited 0 -- never retrying the push. The site
# stayed stale indefinitely while the script reported success.
#
# So: check reachability up front, and always push when local is ahead of
# origin regardless of whether the content changed.
# ---------------------------------------------------------------------------
preflight() {
  if ! git remote get-url origin >/dev/null 2>&1; then
    echo "ERROR: no 'origin' remote configured. Nothing can be published." >&2
    echo "       git remote add origin git@github.com:<user>/<repo>.git" >&2
    return 1
  fi
  local url
  url="$(git remote get-url origin)"
  echo "==> Preflight: verifying we can reach origin ($url)"

  if [[ "$url" == git@* || "$url" == ssh://* ]]; then
    local host
    host="$(printf '%s' "$url" | sed -e 's#.*@##' -e 's#[:/].*##')"
    if ! ssh-keygen -F "$host" >/dev/null 2>&1; then
      echo "ERROR: no known_hosts entry for '$host'." >&2
      echo "       Verify the host key against the provider's published" >&2
      echo "       fingerprints, then add it. Do NOT bypass with" >&2
      echo "       StrictHostKeyChecking=no." >&2
      return 1
    fi
  fi

  if ! GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code origin HEAD >/dev/null 2>&1; then
    echo "ERROR: cannot reach origin (auth, host key, or network)." >&2
    echo "       Diagnose with:  git ls-remote origin" >&2
    return 1
  fi
  echo "    ok -- origin reachable and the host key is known."
}

preflight

if [[ "$NO_BUILD" -eq 0 ]]; then
  echo "==> Staging docs with series frontmatter (gen_home.py --stage)"
  python3 scripts/gen_home.py --stage "$STAGE_DIR"

  echo "==> Building site with zensical (site_url=$GH_SITE_URL)"
  CONF="$REPO_DIR/zensical.toml"
  TMP_CONF="$(mktemp "$REPO_DIR/zensical.publish.XXXX.toml")"
  sed -e "s#^site_url = .*#site_url = \"$GH_SITE_URL\"#" \
      -e "s#^site_dir = .*#site_dir = \".publish_tmp\"#" \
      -e "s#^docs_dir = .*#docs_dir = \"build_docs\"#" \
      "$CONF" > "$TMP_CONF"
  zensical build -f "$TMP_CONF"
fi

# NOTE: --no-build is only meaningful if a previous run left a build behind.
# cleanup() removes .publish_tmp on exit, so in practice a --no-build run has
# nothing to reuse and must say so plainly rather than dying on a missing dir.
SRC="$BUILD_OUT"
if [[ ! -d "$SRC" ]]; then
  if [[ "$NO_BUILD" -eq 1 ]]; then
    echo "ERROR: --no-build given, but no previous build is present at $SRC" >&2
    echo "       (the cleanup trap deletes it after every run, so this is" >&2
    echo "        almost always a mistake). Run without --no-build." >&2
    exit 1
  fi
  echo "ERROR: built site not found at $SRC" >&2
  exit 1
fi

# Update local journal directory (served at homelab.home.arpa/journal)
if [[ "$NO_BUILD" -eq 0 ]]; then
  echo "==> Updating local journal directory"
  cp -r "$SRC"/* /srv/www/codebot/journal/
fi

WT="$(mktemp -d /tmp/codebot-gh-pages.XXXX)"

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

COMMITTED=0
if git diff --cached --quiet; then
  echo "==> No content changes to commit."
else
  MSG="publish: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git commit -q -m "$MSG"
  echo "==> Committed: $MSG"
  COMMITTED=1
fi

# ---------------------------------------------------------------------------
# Push whenever there is anything to send. The 2026-09-29 trap was that a
# failed push left the commit local, and the next run's "no content changes"
# check short-circuited before ever retrying. Always compare local to origin.
# ---------------------------------------------------------------------------
echo "==> Checking what origin still needs"
git fetch --quiet origin gh-pages 2>/dev/null || true

AHEAD=0
BEHIND=0
if git rev-parse --verify --quiet origin/gh-pages >/dev/null; then
  AHEAD=$(git rev-list --count origin/gh-pages..gh-pages)
  BEHIND=$(git rev-list --count gh-pages..origin/gh-pages)
fi

if [[ "$BEHIND" -gt 0 ]]; then
  echo "ERROR: gh-pages has diverged from origin ($BEHIND commit(s) on origin" >&2
  echo "       that are not local). Resolve manually before publishing:" >&2
  echo "         git fetch origin gh-pages" >&2
  echo "         git rebase origin/gh-pages gh-pages" >&2
  exit 1
fi

if [[ "$AHEAD" -eq 0 && "$COMMITTED" -eq 0 ]]; then
  echo "==> Nothing to publish; origin/gh-pages is already up to date."
  echo "==> Done."
  exit 0
fi

echo "==> Pushing gh-pages to origin ($AHEAD commit(s) ahead)"
git push origin gh-pages
echo "==> Pushed."

# Verify rather than trust: confirm origin now points at our commit.
git fetch --quiet origin gh-pages
LOCAL_SHA=$(git rev-parse gh-pages)
REMOTE_SHA=$(git rev-parse origin/gh-pages)
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "ERROR: push appeared to succeed but origin/gh-pages is $REMOTE_SHA," >&2
  echo "       local is $LOCAL_SHA. The site may be stale." >&2
  exit 1
fi

echo "==> Verified: origin/gh-pages == $REMOTE_SHA"
echo "==> Done."
