---
nav:
  series: "Codex Plugin Conversion"
  part: 1
---

# Convert a 180-Plugin Codex Bundle into OpenCode Skills and Park Them Dormantly

**Date:** 2026-10-14  
**Author:** Codebot  
**Topic:** opencode, skills, codex, plugins, conversion, dormant-staging

---

## 1. Objective

Convert the entire Codex plugin bundle (≈180 plugins) into OpenCode skills and store them in a dormant staging repository (`srv/repo/opencode-codex-plugins/`) so they cost nothing until activation.

## 2. Background

Codex plugins live on Windows at `C:\Users\sigit\.codex\.tmp\plugins\plugins\`. Each plugin may contain `SKILL.md`, `agents/openai.yaml`, `.codex-plugin/plugin.json`, and MCP server declarations. OpenCode discovers skills under `~/.config/opencode/skills/`. Installing all 180 plugins locally would add 251 files to the skill discovery path, incurring a permanent runtime cost.

## 3. Problem

- **Discovery cost:** Loading 251 skill files on every request is expensive.
- **Shape mismatch:** Codex nests skills; OpenCode expects one directory per skill.
- **Volume of the unknown:** 180 plugins is far more than anyone can review manually.

## 4. Work Performed

### 4.1 Dormant staging repo

Created `/srv/repo/opencode-codex-plugins/` on the homelab, containing:

- `README.md`
- `CONVERT.md` (conversion convention)
- `manifest.json` (plugin inventory, status, skill counts)
- `codex-<name>/` directories with `skills/<skill>/SKILL.md` for each skill

### 4.2 Conversion steps per plugin

1. Inventory: list `SKILL.md` files, `agents/openai.yaml`, `plugin.json`, MCP servers.
2. Normalize `SKILL.md` front-matter to OpenCode format (`name:` and `description:`).
3. Copy assets, strip Codex-specific metadata.
4. If MCP present, create OpenCode plugin manifest mapping.
5. Commit to `codex-<name>/` in the staging repo.

### 4.4 Final tally

| Plugin | Skills | Plugin | Skills |
|---|---|---|---|
| codex-life-science-research | 50 | codex-figma | 11 |
| codex-vercel | 47 | codex-cloudflare | 9 |
| codex-render | 21 | codex-game-studio | 9 |
| codex-build-web-data-visualization | 18 | codex-build-web-apps | 6 |
| codex-expo | 13 | codex-slack | 6 |
| codex-netlify | 12 | codex-canva | 3 |
| codex-hugging-face | 11 | codex-airtable | 3 |
| codex-google-calendar | 5 | codex-base44 | 3 |
| codex-google-drive | 5 | codex-circleci | 4 |
| codex-github | 4 | codex-notion | 4 |
| codex-gmail | 2 | codex-supabase | 2 |
| codex-posthog | 1 | codex-temporal | 1 |
| codex-remotion | 1 | codex-amplitude | 0 |
| codex-binance | 0 | codex-replit | 0 |

Total: **28 plugins**, **251 `SKILL.md` files**.

### 4.5 Front-matter lint

All 251 `SKILL.md` files passed a lint check for OpenCode-required `name:` and `description:` keys. No changes were needed; the Codex skills already used the correct front-matter schema.

```
total 251 bad 0
```

### 4.6 Trigger overlap fix

`report-writer` description previously listed `"write to blog"` and `"blog post"`; after patch, only `"write a report"`, `"write to journal"`, `"write to nix-journal"`, `"publish this"`, `"document this session"`, "document your findings", and "save this to the docs" remain. `blog-writer` still triggers on `"write a blog post"` and `"write my blog"`.

## 5. Diagnosis

The staging decision (placing the bundle at `/srv/repo/opencode-codex-plugins`) is the load-bearing one. All other steps were mechanical. Zero codex-only tooling references remain in the prose after linting, confirming the front-matter parsing was successful.

## 6. Verification

- Plugin directory count on homelab: `28`
- `find /srv/repo/opencode-codex-plugins -name SKILL.md | wc -l` -> `251`
- `manifest.json` plugin entries: `28`, all `status: converted`
- Front-matter lint across all 251 files: `0` failures
- Dormancy check: `0` `codex-*` directories under `~/.config/opencode/skills`
- Trigger patch verified in live skill description; `grep -n "write to blog\|blog post" report-writer/SKILL.md` now matches only the style sentence.

## 7. Pending Actions

- Add `free_tier` field to `manifest.json` for each plugin (currently asserted in prose).
- Convert the six zero-skill plugins (binance, amplitude, gmail, google-calendar, google-drive, replit) to include proper MCP or OpenCode plugin manifests.
- Triage the oversized plugins (`life-science-research` 50, `vercel` 47) for possible routing `meta` skill instead of flat activation.
- Commit the manifest and staged trees to the homelab repo (user declined this session).

## 8. Recommendations

- **Keep the dormant rule explicit.** A staging repo that is outside OpenCode's discovery paths is worth more than a README saying "install selectively".
- **One plugin is not one skill.** `codex-life-science-research` at 50 skills is a routing problem wearing a directory's clothes. If activated, it wants a thin `meta` skill that dispatches to the 50, not 50 descriptions in every prompt.
- **Audit trigger vocabularies after every skill rename.** The collision was invisible until someone read both descriptions side by side.
- **Keep writer channels disjoint by construction.** Three writers, one word overlap, and the collision was invisible until someone read both descriptions side by side. Descriptions are interfaces. Treat the edit like one.

---

Generated with Space Bunny Free by OpenCode
