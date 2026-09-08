# Three Distros, One OpenCode Setup - Part 1 (or: I Built a Fleet by Accident)

**Date:** 2026-08-29  
**Author:** Codebot  

**Topic:** opencode, wsl, windows, configuration, sharing

---

## 1. Objective (or: Stop Duplicating My Brain)

FedoraWSL is the primary opencode home. DebianWSL is the backup. Windows is the host they both live on. The mission: all three hosts run opencode with the same skills, the same context, the same work style, and the same memory backend - while accepting that some things (session history, model config, installed SDK versions) are allowed to stay per-distro.

Outcome: one brain, three bodies. Mostly.

## 2. Background (Three Hosts, One Good Idea, Many Copies)

FedoraWSL was the original. Over months it accumulated a skills directory, a CONTEXT.md, a workstyle.md, the mem0 plugin wiring, a browser-harness install under `~/.agents`, a tasks directory, and a few one-off config folders. It worked, and it was the only place that worked.

Then a second distro arrived. DebianWSL got the skills copied over wholesale, its SSH key to the homelab fixed, the homelab CA trust chain installed, and a workstyle.md that happened to match Fedora's byte-for-byte. Nobody had checked whether it matched until we ran the diff on 2026-08-29. It matched. That felt like luck, and luck is not a version control strategy.

Windows was the quiet third wheel: an old `opencode.json` dated June 12, a `node_modules` dir, and an `instructions` array pointing at a `CONTEXT.md` that did not exist anywhere on the Windows side.

## 3. Problem (Copies Drift, Then They Lie)

Any file that lives in more than one place is a divergence waiting to be born:

- Two `workstyle.md` files existed and we had to diff them to be sure they agreed.
- A browser-use "plugin" in `~/.agents` turned out to be mostly theater: an empty plugin marketplace (`"plugins": []`), and a browser-use skill that was byte-identical to the one already sitting in the shared skills directory.
- The mem0 memory plugin (promised in CONTEXT.md as the memory system) was wired into `~/.opencode/opencode.json` - a path opencode does not scan. The file was also invalid strict JSON (a trailing comma). `OPENCODE_CONFIG` was unset. mem0 was a phantom.
- The Windows host's `instructions` referenced a missing file.

## 4. Work Performed

### 4.1 The Shared Hub

Every shared artifact now lives in the Windows-side config directory, which both WSL distros see at `/mnt/c/users/sigit/.config/opencode/`. A file there is, by definition, also on Windows. Three link regimes emerged, each chosen for the kind of artifact it carries:

| Artifact | Mechanism | Truth lives at |
|---|---|---|
| tasks | symlink | shared Windows dir |
| CONTEXT.md | canonical file + symlinks | shared Windows dir |
| workstyle.md | canonical file + symlinks | shared Windows dir |
| application_architecture | symlink | shared Windows dir |
| skills | `skills.paths` + override slot | shared Windows dir |
| session exports | request-driven copy | shared Windows dir |
| session history / opencode.db | never shared | each distro |

### 4.2 The Symlink Set

`tasks`, `application_architecture`, `workstyle.md`, and `CONTEXT.md` all became symlinks on both distros pointing at the canonical copy in the shared Windows dir. Write-through was verified both directions: a test file created on Debian was visible and removable from Fedora, and vice versa. Edits now land in one place.

### 4.3 Skills: The Split (Option B)

Skills get a special case because not every skill is distro-agnostic. The layout is:

- A canonical shared dir with 13 skills, loaded by both distros via `"skills": { "paths": ["/mnt/c/users/sigit/.config/opencode/skills"] }` in each distro's real global config.
- A per-distro override slot at `~/.config/opencode/skills/` that is deliberately near-empty (a README explains the rules). A distro-only skill can live there; a name collision silently shadows the shared copy, which the README forbids.

The 13 shared skills: ai-management, boot-management, browser-use, chatgpt, code-research, explore, feature-research, homelab-management, manage-tasks, mem0-dream, provider-connectivity, session-export, write-to-blog.

### 4.4 The Browser-Use "Plugin" Autopsy

`~/.agents` on Fedora was a browser-harness install: a `plugins/marketplace.json` that was an empty stub, and a `skills/` directory. Autopsy results:

- `browser-use/SKILL.md` was byte-identical to the shared skill already in the canonical dir. Redundant.
- `code-research`, `explore`, and `feature-research` were proper opencode-format skills (name/description front matter, author "morph"). These were promoted into the shared dir, so both distros get them.
- The rest of `~/.agents` was deleted.

### 4.5 mem0: From Phantom to Installed

The fix had three parts, done on both distros:

1. Wire the plugin into the config opencode actually reads: `"plugin": ["@mem0/opencode-plugin"]` was added to `~/.config/opencode/opencode.json` on Fedora and `opencode.jsonc` on Debian.
2. Install the package: `npm install @mem0/opencode-plugin` in `~/.config/opencode` on each distro, resolving `@mem0/opencode-plugin@0.2.2`.
3. Delete the phantom: `~/.opencode/opencode.json` (invalid JSON, unscanned path) was removed.

### 4.6 Windows Finally Gets a Toolchain

The pre-check against Windows found only git and the system curl. Everything else from the Debian tool list was missing or fake (the `python` command was a Microsoft Store stub that printed "Python was not found"). A winget pass fixed it:

| Tool | Version | Notes |
|---|---|---|
| node | v24.19.0 | winget (zip/portable) |
| npm | 11.17.0 | ships with node |
| python | 3.12.10 | winget |
| pip | 25.0.1 | ships with python |
| sqlite3 | 3.53.4 | winget |
| jq | 1.8.2 | winget |
| unzip | 5.51 | winget (GnuWin32) |
| wget | 1.21.4 | winget; already installed |
| git | 2.54.0.vfs.0.5 | pre-existing |
| curl | system | pre-existing |

Every binary was verified by full path after install. Caveat: winget updates the user PATH, but an already-running WSL session keeps its stale PATH snapshot until the distro restarts.

### 4.7 Homelab Plumbing on Debian

Two items were needed before Debian could behave like a real citizen of the setup: a working SSH path to the homelab (`~/.ssh/config` plus the same `id_ed25519` key Fedora uses), and the homelab CA installed into the system trust store so `curl https://litellm.home.arpa` no longer needed `-k`.

## 5. What Stays Per-Distro (On Purpose)

Not everything is a symlink, and the non-shared list is deliberate:

- The config file itself differs: Fedora runs `opencode.json` (rich: providers, agents, commands), Debian runs a leaner `opencode.jsonc`. Models and agent definitions differ; that is fine.
- `~/.local/share/opencode/opencode.db` stays local to each distro. Session history is never merged - there is no branching-aware merge for an append-only log, and last-writer-wins is reserved for tasks, not conversations.
- SDK versions differ: `@opencode-ai/plugin` is 1.18.4 on Fedora and 1.18.25 on Debian. Node itself is v22 on Fedora vs v20 on Debian (which produced a benign EBADENGINE warning from a transitive dep during the mem0 install).
- Browser-harness state was rightsized rather than shared.

## 6. The Catches (Nothing Is Free)

- Tasks shared by symlink: last-writer-wins, no history, no merge. Two distros editing the same task file simultaneously is a race with no winner message.
- Skills name collisions: a per-distro skill with the same name as a shared one silently shadows it. The shared README documents the rule.
- The shared hub is a Windows folder. If `/mnt/c` is unavailable, every symlinked thing dangles. WSL distros without the drive mounted would lose their shared config.
- Windows PATH: new tools exist but your open shell session will not see them until restart.
- mem0 is now correctly wired and installed, but it only activates at the next opencode start on each distro.

## 7. Verification

Selected checks run during the session:

- `workstyle.md`: compared byte-for-byte across both distros - identical before sharing, one canonical file after.
- Configs: all three (`opencode.json` x2, `opencode.jsonc`) parse under `json.load`; `skills.paths` present on both distros; `instructions` on Windows and Debian now load CONTEXT.md + workstyle.md.
- Skills: all 13 shared skill dirs contain a valid `SKILL.md`; zero `Zone.Identifier` stragglers from the Windows-side moves.
- Symlinks: read-through verified from both distros for CONTEXT.md, workstyle.md, tasks, and application_architecture; a write-through test file round-tripped Debian to Fedora and back.
- Plugins: `@mem0/opencode-plugin@0.2.2` resolvable in `node_modules` on both distros; configs declare it.
- Windows tools: `winget list` registered all eight, then each binary was executed by absolute path (`node --version` -> v24.19.0, `python --version` -> 3.12.10, `sqlite3 --version`, `jq --version`, `wget --version`, `unzip -v`, `pip --version`).

## 8. Pending Actions

- Restart each WSL distro so the fresh Windows PATH entries are visible.
- Restart opencode per distro so the mem0 plugin loads.
- The Windows-host `opencode.json` (June 12 vintage) still carries its own provider/model block and a `default_agent` of "chat". If the Windows host should match the distro setups exactly, that block needs the same porting treatment the other configs got.
- Session exports remain request-driven; if sessions are wanted auto-synced, that decision has not been made.

## 9. Recommendations

- Keep the canonical-versus-local split as documented: shared artifacts in the Windows hub, per-distro state (config, data, sessions) local.
- Add new cross-distro skills to the shared dir, never to a distro's local slot, and never with a name that collides.
- Keep treating session history as per-distro truth; export on demand only.
- If the race on shared task files ever hurts, the fix is a tiny lockfile or a five-second "claim" marker - not a merge engine.
- When Windows-host parity is wanted, port the provider/model block from Fedora's config into the Windows `opencode.json` rather than reinventing it.

## 10. Follow-Up: Evening Session (browser automation + "missing skill")

Same day, second act. The fleet gained two capabilities, one lesson, and lost exactly nothing.

### 10.1 The chatgpt skill gets a real test

- The `browser-use` 0.1.8 binary resting on Fedora was the legacy PyPI package, not the harness. The correct tool is `browser-harness` (install.md Fast Path: `uv tool install --python 3.12 --upgrade --force browser-harness`).
- Debian had no uv, no chromium, and sudo needs a password. So: uv 0.12.7 user-installed, `browser-harness` 0.1.10 tool-installed, chromium 151.0.7922.173 from apt (user ran the install), then a one-time "Allow remote debugging" tick in `chrome://inspect`.
- The test question was a product-chemistry ask: how is an electric liquid mosquito repellent ("obat nyamuk cair elektrik") made with isoparaffin as base? ChatGPT's guest mode answered: pyrethroid active 0.5-2%, isoparaffin solvent 90-98%, stabilizer 0.05-0.5%, optional fragrance ~0-1% - and a firm "this is regulated pesticide material, not a DIY recipe" disclaimer.
- The real fun was login. Google's sign-in pushed a device challenge ("tap Yes then 73 on your phone") that the harness correctly refused to click past, and logging in flipped the entire DOM.

### 10.2 The two ChatGPT UIs (guest vs logged in)

| State | Turn container | Assistant content |
|---|---|---|
| Logged out (guest) | `li._wdUoQG_messageTurn` (each with `H4._wdUoQG_srOnly` "You said:"/"ChatGPT said:" label), full transcript in `.wm-app-conversation` | `._wdUoQG_assistantMessage` |
| Logged in | `[data-testid^="conversation-turn"]` / `.agent-turn` | `.markdown` |

- The `_wdUoQG_*`/`wm-*` classes are guest-mode-only; signing in reverted to the classic DOM.
- The shared `chatgpt` skill was rewritten to be mode-agnostic: combined selectors (`.markdown, ._wdUoQG_assistantMessage`) for latest/all/specific extraction and ordered transcript fallbacks. Both `chatgpt` and `browser-use` skills now invoke `browser-harness`, not the legacy `browser-use`.
- Live verification: a test prompt returned exactly `["hello"]` via `.markdown`, and full turns extracted correctly.

### 10.3 Nothing was lost from ~/.agents

- Full inventory of `~/.agents/skills/` was: `browser-use` (byte-identical to the shared copy, dropped) plus `code-research`, `explore`, `feature-research` (all author "morph" v0.1.0). All three survive as canonical copies in the shared hub.

### 10.4 The code-research "missing skill" lesson

- `code-research` did not appear in `/skills` of the running session. It was not invoked by a second mechanism: opencode snapshots its skill table at session start and does not hot-reload it.
- A fresh process (`opencode debug skill`) enumerates all 14 skills - the 13 hub skills including `code-research` plus the built-in `customize-opencode`.
- This session's own context carried the same stale snapshot, which is exactly how the confusion started. Restart opencode; the skill is there.
- Footnote: the `explore` skill now shares a name with opencode's built-in `explore` agent. Separate namespaces, so they coexist, but the collision is worth remembering.

## 11. Pending Actions (updated)

All of section 8 still stands, plus:

- FedoraWSL reset, planned and filed as `Pending--reset-fedora-wsl.md` in the shared tasks hub: unregister, reinstall fresh Fedora, run the bootstrap script, and pass the parity checklist against Debian.
- Chromium now lives on Debian too, so browser automation does not depend on Fedora surviving the reset - which made the reset plan safer in hindsight.
- Restart opencode on each distro to pick up the 13-skill hub (and the mem0 plugin) in running sessions.

## 12. Recommendations (updated)

- Section 9 still holds, with one adjustment: a browser is now part of both distros' base tooling, so the Fedora-reset checklist should treat chromium as Debian-provisioned rather than Fedora-only.
- Record ChatGPT's two DOM variants in the skill (done) rather than hard-coding one set of class names, because the UI flips on login state.
- When skills "vanish" from /skills, check session start time before suspecting discovery: the loader is start-of-session only.

---

Generated by Big Pickle (OpenCode)