# Miscellaneous Tasks: wakectl Finetune, Journal Prep, and Agent Cleanup

*Task Roulette: Draw One, Park It, Write a Report Instead*

**Date:** 2026-08-24  
**Author:** Codebot  
**Topic:** miscellaneous, tasks, homelab, housekeeping, opencode

---

## 1. Objective

Work through the pending-task list in `~/.config/opencode/tasks/` and close whatever can be closed: finish the wakectl finetune task, prepare the Journal site content (without wiring it into nix-lab yet), and customize the OpenCode agent roster so `@reason` is chat-only while `@fast` and `@cheap` are removed.

## 2. Background

Pending work was tracked as markdown task files under `~/.config/opencode/tasks/`. Three areas were in scope:

| Area | Task file | State at session start |
| --- | --- | --- |
| wakectl finetune | `Pending--wakectl.md` | Areas 1-3 in flight; Area 3 changes believed uncommitted |
| Journal/Zola site | `Pending--journal.md` | Idea only; no scaffold existed |
| OpenCode agents | none | `@reason` unrestricted; `@fast`/`@cheap` present |

The wakectl repository lives at `/srv/repo/wakectl` on the homelab host (Go 1.24). The journal source of truth remains `/srv/www/codebot/docs/*.md`; the new Zola site at `/srv/www/journal` consumes it via a sync script. The OpenCode global config lives at `~/.config/opencode/opencode.json`.

## 3. History

- wakectl had already absorbed three commits during earlier sessions: `9dd0492` (loadable keymap, bindings validation, stop tracking binary), `cd56714` (docs fix), and a README bindings-example correction.
- The journal idea dated back to an earlier session but had never been scaffolded.
- The OpenCode config previously defined seven agents (`reason`, `code`, `review`, `build`, `plan`, `fast`, `cheap`) with matching slash commands.

## 4. Symptoms

Two state-drift issues surfaced:

1. The wakectl task file claimed Area 3 changes were "staged but not committed", yet `git status` on homelab reported a clean tree - the work had actually landed as commit `9dd0492`. The task file was stale.
2. Repeated SSH failures of the form `/bin/bash: -c: line 1: unexpected EOF while looking for matching '"'` when remote commands were wrapped with an opening quote but no closing quote.

## 5. Work Performed

### 5.1 wakectl finetune closure

- Verified Area 1 (bindings validation, README docs, quit sequence, sticky modifiers, documented defaults) and Area 3 were already committed; confirmed via `git log` and `git status`.
- Updated `README.md` so the Options line documents default values: `--paste-delay N` (default 10), `--repeat-delay N` (default 400), `--repeat-rate N` (default 25).
- Committed the README change as `1a1890b` ("docs: update README with default option values for paste-delay, repeat-delay, repeat-rate").
- Removed the stray `main.go.bak` from the working tree.
- Ran `go vet ./...`, `go test ./...`, and `go build ./...` - all clean.
- Rewrote `Pending--wakectl.md` as a completed record. Future ideas (a full uinput backend replacing ydotool, and a second keymap layout) are tracked there as separate future work, not as unfinished items.
- Note: branch `main` sits one commit ahead of `origin/main`; nothing has been pushed yet.

### 5.2 Journal content preparation

Scaffolded `/srv/www/journal` on homelab:

```text
/srv/www/journal/
  config.toml              # base_url https://journal.home.arpa, taxonomies, search index
  sync.sh                  # transforms bold-metadata posts into Zola frontmatter
  content/posts/           # generated output
  templates/page.html      # minimal render template
  templates/shortcodes/super.html   # empty stub
  static/
```

Key implementation details:

- `sync.sh` extracts title, date, author, tags, and slug from the blog's bold-metadata format and emits TOML `+++` frontmatter, escaping embedded quotes and backslashes so titles like `"switch root target contains no usable init" - Part 3` survive round-tripping.
- A production build succeeded: 102 pages (101 orphan), search index and sitemap generated.
- Wiring into nix-lab (a `journal.nix` module, systemd path units, Caddy vhost) was explicitly deferred by operator decision; only content preparation was done.

Four Zola gotchas were hit and resolved:

| Gotcha | Resolution |
| --- | --- |
| `sort_by` rejected as invalid top-level key in `config.toml` | Removed the key entirely |
| Titles containing `"` broke TOML frontmatter | Escape quotes/backslashes in `sync.sh` |
| `safe_page_meta()` does not exist in Tera | Simplified template to title plus `{{ page.content \| safe }}` |
| Legacy `{% super %}` shortcode error | Added empty `templates/shortcodes/super.html` stub |

Also noted: `sync.sh` fails with "bad interpreter" when executed directly (CRLF line endings from scp), so it must be run as `bash /srv/www/journal/sync.sh`.

### 5.3 OpenCode agent customization

- Backed up `~/.config/opencode/opencode.json` before editing.
- Added an `instructions` array to the `reason` agent restricting it to conversational responses: no tools, no file searches, no memory calls, no command execution or file modification.
- Later removed the `fast` and `cheap` agents and their matching commands entirely, leaving `reason`, `code`, `review`, `build`, and `plan`.
- Validated the resulting JSON with `python3 -m json.tool`.

Caveat: enforcement of per-agent `instructions` is not yet verified end-to-end. Config is loaded once at startup, so a restart is required either way; if opencode ignores the field, the fallback is a `permission` block (for example `edit: deny`, restricted `bash`) or an agent definition file.

### 5.4 Random task draw

A random draw from the pending list selected `develop-dotfiles-for-nix-lab.md`: making `/srv/repo/dotfiles` consumable by nix-lab (flake input plus home-manager) while keeping the sops age private key out of any nix wiring. The task was read and summarized, then paused by the operator in favor of this report - hence the subtitle.

Later the same day the draw was revisited and became real work: `~/.config/xfce4`, `gh/config.yml`, and two systemd user units were committed to the dotfiles repo (`230854c`) after hardening `.gitignore` against live secrets found sitting untracked in the tree (`copyparty/` certs and salts, the gh OAuth token in `hosts.yml`). nix-lab now wires them through home-manager out-of-store symlinks (`ace4172`): the Xfce settings directory points straight at the repo working tree, so GUI changes land as git churn and survive rebuilds instead of being reset. Follow-ups: stale zensical user units dropped everywhere, the old five-file force-copy panel entries retired, and the declarative wallpaper block (`xfconf.settings`) removed so the dotfiles repo solely owns desktop config (`ded5b93`). Verified end to end: an Xfce settings tweak showed up as repo churn and was committed as a snapshot (`b7cf804`).

## 6. Diagnosis

The recurring SSH failures traced to a single habit: remote commands quoted with an opening `"` but a missing closing `"`. The reliable workaround for complex payloads is to write files locally with a heredoc and transfer them with `scp`, reserving inline quoting for simple one-liners.

## 7. Preliminary Assessment

All three areas are now in a defensible state: wakectl is fully closed with tests green, the journal site builds from untouched sources with secrets excluded, and the agent roster matches the operator's intent. No age key or other secret entered nix-lab or the journal pipeline at any point.

## 8. Pending Actions

- Verify that the `@reason` chat-only instructions are enforced after an OpenCode restart; fall back to `permission` rules if not.
- Push wakectl `main` to `origin/main` (one commit ahead: `1a1890b`).
- Journal nix-lab integration remains intentionally deferred.
- Decide the dotfiles integration mechanism (flake `path:` input versus dedicated home-manager module).

## 9. Recommendations

- Treat task files as records to update the moment state changes; stale "uncommitted" notes cost a verification cycle.
- Always balance quotes in SSH one-liners, and prefer local heredoc plus `scp` for anything non-trivial.
- Run `bash /srv/www/journal/sync.sh` rather than executing it directly until line endings are normalized.
- Restart OpenCode after any `opencode.json` change; running sessions keep the previously loaded config.
- After any dotfiles-to-nix-lab wiring, re-run the grep/symlink audit to confirm the gitignored age key directory stays excluded.

Generated with Big Pickle (OpenCode)
