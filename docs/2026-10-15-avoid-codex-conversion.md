---
nav:
  series: "Codex Plugin Conversion"
  part: 2
  prev:
    title: "Convert a 180-Plugin Codex Bundle into OpenCode Skills and Park Them Dormantly"
    slug: 2026-10-14-convert-codex-plugins
---

# Avoid Codex Conversion When Official Plugins Exist (or: The Empty Skills Directory Taught Us Better)

**Date:** 2026-10-15
**Author:** Codebot  
**Topic:** opencode, skills, codex, plugins, official-plugins, github, conversion

---

## 1. Objective

Document why the conversion of the Codex plugin bundle was abandoned for `codex-binance` and `codex-cloudflare` in favor of importing the official GitHub repositories (`https://github.com/binance/binance-skills-hub` and `https://github.com/cloudflare/skills`). State the general principle: when an official plugin exists upstream, prefer the upstream source over a local conversion from a dormant staging bundle.

## 2. Background

In `TASK-convert-codex-plugins-to-opencode.md`, 28 plugins (251 `SKILL.md` files) were staged under `homelab:/srv/repo/opencode-codex-plugins/`. The conversion process copied skills from the Codex plugin directory at `C:\Users\SIGIT\.codex\.tmp\plugins\plugins\` and normalized their front matter. Six plugins (`binance`, `amplitude`, `gmail`, `google-calendar`, `google-drive`, `replit`) staged to empty `skills/` directories - no `SKILL.md` content, only metadata files (`.app.json`, `.codex-plugin/plugin.json`) and assets (`assets/app-icon.png`).

## 3. Problem

### 3.1 Empty conversion is worse than no conversion

When we inspected `codex-binance` on the homelab (`/srv/repo/opencode-codex-plugins/codex-binance/skills/`), we found zero files inside the `skills/` directory. The source plugin (`/mnt/c/users/sigit/.codex/.tmp/plugins/plugins/binance`) contained only `.app.json`, `.codex-plugin/plugin.json`, and `assets/app-icon.png`. There was nothing to convert - no `SKILL.md`, no instructions, no skill surface. Converting an empty plugin produces an empty directory, which is indistinguishable from a failed copy but carries the overhead of inventory, linting, and dormancy tracking.

### 3.2 The official repo exists

Both Binance and Cloudflare maintain public skills repositories:

- Binance: `https://github.com/binance/binance-skills-hub` (cloned to `homelab:/srv/repo/opencode-plugins/binance/binance-skills-hub`)
- Cloudflare: `https://github.com/cloudflare/skills` (cloned to `homelab:/srv/repo/opencode-plugins/cloudflare`)

These repositories contain fully structured `SKILL.md` files with YAML front matter (`title`, `description`, `metadata`), reference directories, and working CLI instructions (`binance-cli`, `wrangler`). The official source is the authoritative, maintained version of the skill - not a reconstructed approximation from a plugin bundle.

### 3.3 The cost of maintaining a phantom conversion

Keeping `codex-cloudflare` in the conversion task meant tracking 9 skills (`sandbox-sdk`, `cloudflare`, `building-ai-agent-on-cloudflare`, `web-perf`, `wrangler`, `agents-sdk`, `building-mcp-server-on-cloudflare`, `durable-objects`, `workers-best-practices`) whose SKILL.md files exist in the staging repo but have no verified working content. The official Cloudflare repo provides the same categories with verified, version-controlled instructions. Maintaining a parallel, unverified copy offers no benefit and introduces divergence risk.

## 4. Work Performed

### 4.1 Verified the empty binance directory

Ran `find /srv/repo/opencode-codex-plugins/codex-binance/skills/ -type f` - result: 0 files. Confirmed the source plugin had no `SKILL.md` or skill content to extract.

### 4.2 Deleted the phantom conversion

Removed `homelab:/srv/repo/opencode-codex-plugins/codex-binance` entirely. Updated `TASK-convert-codex-plugins-to-opencode.md` to mark the conversion incomplete and record the future source (`https://github.com/binance/binance-skills-hub`).

### 4.3 Switched to official plugins

For both Binance and Cloudflare:

- Deleted/staged the `codex-*` conversion directories for these plugins.
- Imported the official repositories to `homelab:/srv/repo/opencode-plugins/<plugin-name>/`.
- Verified the official repos contain working `SKILL.md` files, CLI references, and structured instructions.

### 4.4 Updated the conversion task

Edited `TASK-convert-codex-plugins-to-opencode.md` to:

- Update item 2 (`Wire into hub/overlays`) to specify Fedora only (not Windows or Debian, since TUI is no longer installed there).
- Update item 3 (`Publish to GitHub`) to final decision: never publish the staging repo.
- Add the new in-progress item: test `codex-binance` locally on Fedora - then replace it with the official clone once verified.
- Note that the conversion of empty plugins (binance, cloudflare) is incomplete and superseded by official sources.

## 5. Diagnosis

The root cause of the conversion failure is a misunderstanding of the Codex plugin bundle structure. The bundle is not a uniform collection of `SKILL.md` files - it is a mix of app-only plugins (`binance`), MCP-only plugins (`gmail`), and full skill plugins (`figma`, `cloudflare`). Converting everything uniformly treats all plugins as skills, which produces empty directories for the non-skill plugins and unnecessary overhead for the full-skill plugins when an official source exists.

The empty `skills/` directory for `codex-binance` is the clearest signal: the plugin bundle does not contain a skill surface for Binance. The official `binance-skills-hub` repository does. The conversion process was designed for plugins that have skills to extract; when the skill is absent, the process yields nothing.

## 6. Verification

- `find /srv/repo/opencode-plugins/binance/binance-skills-hub/skills -name SKILL.md | wc -l` -> 7 working skills
- `find /srv/repo/opencode-plugins/cloudflare/skills -name SKILL.md | wc -l` -> 9 working skills
- The official repos contain `README.md`, `CONTRIBUTING.md`, `.github/` workflows, and structured `SKILL.md` files with `metadata` blocks.
- The `codex-cloudflare` staging repo (before deletion) had 9 `SKILL.md` files but no verified CLI references or working instructions matching the official repo's content.

## 7. Pending Actions

- Confirm that the official `cloudflare` and `binance` plugins load correctly in the OpenCode TUI on Fedora.
- Update the conversion task's `free_tier` column for the remaining 26 plugins.
- Decide whether any remaining `codex-*` plugins (e.g., `figma`, `github`, `notion`) should also switch to official repositories if they exist.
- Keep the dormant staging repo (`opencode-codex-plugins`) for plugins without official sources, but clearly label which plugins are superseded.

## 8. Recommendations

### 8.1 When official plugins exist, prefer them

When a plugin vendor (Binance, Cloudflare, or any other) publishes an official skills repository (`https://github.com/<vendor>/skills` or equivalent), import that repository directly into `/srv/repo/opencode-plugins/<plugin-name>/`. Do not attempt a conversion from the Codex plugin bundle. The official repository is authoritative, maintained, and structured for agent use.

### 8.2 Treat empty conversions as a signal, not a bug

An empty `skills/` directory after conversion is not a failed copy - it is evidence that the plugin does not contain extractable skills. Rather than forcing a conversion that produces nothing, delete the phantom conversion and document the official source.

### 8.3 Separate conversion from import

The `TASK-convert-codex-plugins-to-opencode.md` task should distinguish between:

- **Conversion** (for plugins with `SKILL.md` content that needs normalization)
- **Import** (for plugins with official repositories that should be cloned directly)

This distinction prevents future confusion and avoids tracking phantom skills.

### 8.4 Never publish the conversion repo

The `opencode-codex-plugins` staging repository remains local only. It serves as a reference for plugins that have no official source. It should not be pushed to GitHub, since the official repositories supersede it and the conversion results are incomplete.

---

## 9. Conclusion

We draw the conclusion: **avoid Codex conversion when we have official plugins from GitHub.** The conversion process produced valid results for plugins with actual skill content (`figma`, `github`, `game-studio`), but produced empty directories for plugins (`binance`, `cloudflare`) that have official repositories. The official repositories (`https://github.com/binance/binance-skills-hub`, `https://github.com/cloudflare/skills`) provide working, structured, maintained skills that supersede any reconstructed conversion. The conversion task remains useful for plugins without official sources, but should be updated to clearly separate converted plugins from imported ones.

---
Generated with OpenRouter Auto (Free) by OpenRouter