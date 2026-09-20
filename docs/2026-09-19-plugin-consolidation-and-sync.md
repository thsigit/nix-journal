# Plugin Consolidation and Sync (or: Why Is This Plugin in Two Different Directories?)

**Date:** 2026-09-19  
**Author:** Codebot  
**Topic:** opencode, plugins, skills, sync-opencode, WSL, configuration management

---

## 1. Objective (or: Fix the Plugin Location Mess)

Clean up the plugin directory sprawl across three distros (FedoraWSL, DebianWSL, Windows native) and establish a consistent rule: all plugins live in `~/.config/opencode/plugins/`, not split between `~/.opencode/plugins/` and `~/.config/opencode/plugins/`.

## 2. Background (or: How Did We Get Here)

After the decentralized sync migration, the opencode-google-workspace plugin was installed via npm/opencode CLI into `~/.opencode/plugins/` (the opencode runtime directory). Meanwhile, self-improving-skills was manually placed in `~/.config/opencode/plugins/` (the config directory). Two different locations, no clear reason why.

The sync-excludes.txt also had `plugins/*/skills/` excluded, which prevented plugin-bundled skills from syncing across distros. This was a leftover from the "bundled companion skills live at top-level skills/" assumption that no longer held.

## 3. Problem (or: Split Personality)

Three issues surfaced during the session:

1. **Plugin location split**: google-workspace in `~/.opencode/plugins/`, self-improving-skills in `~/.config/opencode/plugins/`. No functional reason for the split - just historical accident.

2. **Skills exclusion**: `plugins/*/skills/` in sync-excludes.txt prevented plugin-bundled skills (gmail, google-docs, etc.) from syncing. These skills depend on the plugin MCP server and should travel with it.

3. **Overlay path mismatch**: Windows overlay referenced `~/.opencode/plugins/` (old location), which did not exist after the move.

## 4. Work Performed (or: The Actual Fix)

### 4.1 sync-excludes.txt Update

Removed `plugins/*/skills/` from the exclude pattern. Plugin skills are now synced alongside the plugin runtime. The comment was updated:

```
# plugin clones: sync runtime files + bundled skills; never sync git metadata.
plugins/*/.git/
```

### 4.2 Plugin Move (All Three Distros)

Moved opencode-google-workspace from `~/.opencode/plugins/` to `~/.config/opencode/plugins/` on all three distros:

- Fedora: `mv ~/.opencode/plugins/opencode-google-workspace ~/.config/opencode/plugins/`
- Debian: same command
- Windows: Move-Item via PowerShell

Old `~/.opencode/plugins/` directories are now empty on all distros.

### 4.3 Overlay Updates

Updated plugin paths in all three overlays:

- Fedora/Debian: `/home/sigit/.config/opencode/plugins/opencode-google-workspace/src/index.js`
- Windows: `C:\Users\SIGIT\.config\opencode\plugins\opencode-google-workspace\src\index.js`

Shell settings preserved: bash for WSL distros, pwsh for Windows.

### 4.4 Hub Sync

Pushed updated sync-excludes.txt + plugins from Fedora to hub, then pulled to Debian and Windows. All three distros now have both plugins with bundled skills.

## 5. Diagnosis (or: Why the First Sync Failed)

The initial rsync pull from hub to Debian/Windows only showed self-improving-skills - google-workspace was missing. Root cause: the sync-excludes.txt on Debian still had the old `plugins/*/skills/` pattern, and the hub copy had not been updated yet.

The fix required: edit sync-excludes.txt on hub directly (sed), pull updated excludes to all distros, then re-pull plugins with corrected excludes.

PowerShell-to-WSL variable expansion ate `$schema` in JSON files multiple times. Solution: write files via WSL mount paths instead of heredocs.

## 6. Plugin vs Skill Architecture Discussion

Key insight: plugins provide runtime (MCP servers, tool providers), skills provide instructions.

- **Standalone skills**: just markdown, no runtime needed. Easy to create, easy to copy.
- **Plugin-managed skills**: bundled with a plugin that provides the tools those skills use.
- **Plugin advantage**: easy copy/transfer as a self-contained unit, plus optional startup hooks (auto-sync, housekeeping, monitoring).

Decision: manage-tasks stays as a standalone skill (no runtime needed). opencode-hub is a good plugin candidate if automation is desired in the future.

## 7. Verification (or: Does It Actually Work)

Final state across all three distros:

| Item | Fedora | Debian | Windows |
|---|---|---|---|
| plugins/opencode-google-workspace | yes | yes | yes |
| plugins/self-improving-skills | yes | yes | yes |
| overlay shell | bash | bash | pwsh |
| overlay plugin path | ~/.config/opencode/plugins/... | ~/.config/opencode/plugins/... | C:\Users\SIGIT\.config\opencode\plugins\... |
| old ~/.opencode/plugins/ | empty | empty | empty |

## 8. Recommendations (or: What to Do Next)

1. Run a full parity check (skills/, tasks/, plugins/) to confirm sync state across all hosts.
2. Consider converting opencode-hub to a plugin if auto-sync on startup becomes a repeated request.
3. Keep manage-tasks as a standalone skill until runtime behavior is needed.
4. Test the google-workspace plugin on Windows to confirm the path and MCP server work with shell: pwsh.

---

Generated by MiMo V2.5 Free (OpenCode)
