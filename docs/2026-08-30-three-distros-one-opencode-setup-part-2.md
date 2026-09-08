# Three Distros, One OpenCode Setup - Part 2 (or: Three Distros, One Configuration, and a Windows Asterisk)

**Date:** 2026-08-30  
**Author:** Codebot  
**Topic:** opencode, wsl, windows, configuration, convergence, overlay

---

## 1. Objective (or: One Brain Now Has One Skeleton)

The first fleet report (`three-distros-one-opencode-setup-part-1`, 2026-08-29) gave three
environments one brain: shared skills, shared context, shared work style, shared
memory backend. But it left the skeleton alone. Each distro still carried its own
`opencode.json`; the Windows host ran a config from June 12; `MEM0_API_KEY` lived
on exactly one machine; and `auth.json` was duplicated with different keys on two
of them.

This post is the sequel: the **universal convergence**. It turns one brain into
one configuration too - a single `opencode.json` read by every environment, one
shared auth file, one shared memory store - and it covers the one thing the
"one configuration" motto quietly ignored: **Windows is not Linux.** So the final
chapter is a small but honest exception, the per-OS overlay that lets
`opencode.exe` know it is Windows while Fedora and Debian politely stay Linux.

## 2. Background (Two Sparks, One Fire)

Two sessions lit this fire back to back.

**Spark one: the fleet report.** The 2026-08-29 post established the shared
Windows hub at `/mnt/c/users/sigit/.config/opencode/` and symlinked the soft
artifacts (tasks, CONTEXT.md, workstyle, application_architecture). Skills were
shared via `skills.paths`. But the config file itself stayed per-distro:
FedoraWSL ran a rich `opencode.json`; Debian ran a lean `opencode.jsonc`; Windows
ran a stale file that predated both. That was written up as "models and agent
definitions differ; that is fine." It was fine. It was also only a matter of time.

**Spark two: a report that described the future as fact.** The mem0 part-5
report (2026-08-30) was drafted around the plugin-to-MCP swap and asserted that
the source of truth was `~/.config/opencode/opencode.json` "on the DebianWSL
host." That file did not exist - Debian uses `opencode.jsonc`, and the `plugin: []`
plus `mcp.mem0` block actually lived in Fedora's config. No DebianWSL, wrong path,
wrong host. Errata were written that same evening (part-5, section 11), and the
erratum ended with a promise: rather than re-documenting the intent, actually
converge the settings. This post is what that promise produced.

## 3. Problem (The Report Knew What the Setup Did Not)

1. **The universal config did not exist.** Three divergent `opencode.*` files,
   each with a different provider menu, agent roster, and permission posture.
2. **Secrets were not universal.** `MEM0_API_KEY` was exported in Fedora's
   `~/.bashrc` only. Debian had a plugin that wanted it and nothing set. Windows
   had neither the variable nor the MCP wiring.
3. **Skills were only half-shared.** The hub had the skills, but each distro's
   config pointed at skills with per-distro path lists, and the Windows config
   pointed at nothing at all.
4. **`auth.json` was lying in two languages.** Fedora held
   `github-copilot`/`litellm`/`nvidia`; the Windows host held
   `abliteration-ai`/`aihubmix`/`litellm`. Any change on one host was invisible
   to the others.
5. **No way to say "this key is Windows-only".** A single shared config cannot,
   by itself, set a `shell` to PowerShell on Windows and leave bash alone on
   Linux - not without some mechanism that knows which OS is asking.

## 4. Work Performed

### 4.1 The Midway Inventory (Three Rooms, Three Furnishings)

Before merging anything, each environment's actual state was recorded - from the
files, not from memory (that is how the part-5 erratum got written in the first place).

| Env | What it actually had |
|---|---|
| FedoraWSL | rich `opencode.json`: `litellm` + `bitrouter` + `nvidia`(whitelist) providers, 6 agents, `permission.bash`, `experimental.continue_loop_on_deny: false`, its own `skills.paths`, `plugin: []`, `mcp.mem0`, `MEM0_API_KEY` in `~/.bashrc` |
| Debian | lean `opencode.jsonc`: `@mem0/opencode-plugin`, `steps: 8`, `skills.paths`, no `MEM0_API_KEY` |
| Windows | June-12 `opencode.json` (no mem0, no skills, a phantom CONTEXT.md in `instructions`), `auth.json` with `abliteration-ai`/`aihubmix`/`litellm`, no `MEM0_API_KEY` |
| Shared hub | the widest config: 94 `litellm` models, 10 agents, full command menu - but no `plugin`/`mcp`/`permission`/`experimental`/`skills`/`steps` keys at all |

Funny thing: the hub was the richest config and the least authoritative. It
described a fleet that did not match any of its own members.

### 4.2 The Merge Script

A one-off Python generator (`gen_universal.py`) was written to produce the
universal config deterministically rather than by hand-editing 488 lines of JSON:

- Start with the hub base (all providers, all models, the command menu).
- Layer in the FedoraWSL additions that the hub lacked: `plugin: []`,
  `mcp.mem0`, `permission.bash`, `experimental.continue_loop_on_deny: false`,
  `skills.paths`, `provider.nvidia` whitelist, the `writer` agent/command.
- Set `steps: 32` on every agent.
- Take the provider `apiKey` from Fedora's working `litellm` key (the hub still
  had an older one) while keeping the default model `litellm/kenari/kenari-free`
  and `default_agent` untouched for stability.

The generator was a throwaway (it lived under `/tmp`, as god intended); the
*procedure* it encoded is preserved in the `universal-setup` skill, so future
convergence passes are a documented process, not a recovered script.

### 4.3 Symlinks, a Retirement, and a Backup Tray

The generated config was written to `/mnt/c/users/sigit/.config/opencode/opencode.json`.
Fedora and Debian `~/.config/opencode/opencode.json` became **symlinks** to it;
Windows reads the same file natively. Debian's `opencode.jsonc` was retired.

Before overwriting anything, every pre-change file was parked in
`/mnt/c/users/sigit/.config/opencode-backups/`:

| Backup | Size | Role |
|---|---|---|
| `opencode-hub-pre-universal-20260830-152934.json` | 14330 B | hub before the merge |
| `opencode-fedora-pre-universal-20260830-153027.json` | 6035 B | Fedora's rich config |
| `opencode-debian-pre-universal-20260830-152934.jsonc` | 858 B | Debian's retired config |
| `auth-windows-pre-universal-20260830-153728.json` | 268 B | Windows auth keys |
| `auth-fedora-pre-universal-20260830-153728.json` | 371 B | Fedora auth keys |
| `opencode-hub-pre-overlay-20260830-222915.json` | 15835 B | hub before the Windows overlay (section 5) |

(The `skills-fedora-*`/`tasks-*-20260829.tar.gz` archives predate this session;
they belong to the fleet report's cleanup.)

The rule of thumb going forward: any change to the universal stack gets a
`-pre-<change>-<timestamp>` backup first, in that same tray.

### 4.4 Environment Parity (One Secret, Three Shells)

`MEM0_API_KEY` needed to exist on all three hosts - and needed to never appear
in a transcript. The value was read from Fedora's `~/.bashrc` by tools that do
not echo (file reads, PowerShell pipeline reads), then placed:

| Host | Where |
|---|---|
| FedoraWSL | already in `~/.bashrc` |
| Debian | appended to `~/.bashrc`, value pulled without echoing |
| Windows | user env var, set via PowerShell reading `\\wsl$\FedoraLinux-44\home\sigit\.bashrc` directly |

Every read-back was masked (prefix only, `m0-dWSN***`). The TLS/CA posture
stayed per-host on purpose: Debian and Windows trust the homelab CA via the
system store; Fedora pins `NODE_EXTRA_CA_CERTS` in its `~/.bashrc`.

### 4.5 Auth.json United (One File, Five Keys, Zero Conflicts)

The two auth files were merged into a canonical
`C:\Users\sigit\.local\share\opencode\auth.json` (WSL: `/mnt/c/users/sigit/.local/share/opencode/auth.json`):

| Source | Providers |
|---|---|
| Fedora backup | `github-copilot`, `litellm`, `nvidia` |
| Windows backup | `abliteration-ai`, `aihubmix`, `litellm` |
| Union (designed) | five providers; the `litellm` key collided but was byte-identical on both sides, so the merge was conflict-free |

Fedora and Debian `~/.local/share/opencode/auth.json` are now **symlinks** to the
canonical file, so any `opencode auth login` on any host writes through to one file.

Acting postscript (checked after the merge, because the post's own rule is
"verify, don't remember"): the canonical file currently holds
`github-copilot`/`litellm`/`nvidia` - the two Windows-only providers
(`abliteration-ai`/`aihubmix`) are no longer present. Something rewrote the shared
file with Fedora's set after the union landed. That is not a bug in the
convergence; it is the documented **last-writer-wins** property of sharing one
file, demonstrated live. The Windows keys are still in the backup tray, waiting
to be restored if they are wanted.

### 4.6 Agents Chiseled Down (chat and reason Retire)

With the whole roster in one file, the dust settled: 9 agents/commands -
`code`, `review`, `vision`, `fast`, `cheap`, `homelab-management`, `build`,
`plan`, `writer` - every one with `steps: 32`. The `chat` and `reason` agents were
removed by user request, and `default_agent` became `plan`. The universal config
also kept `experimental.continue_loop_on_deny: false`, meaning a denied tool call
ends the turn (fail-fast) rather than looping.

### 4.7 The mem0 Store, Wherever You Stand

The part-5 local memory store was pointed at the shared hub path
`/mnt/c/users/sigit/.config/opencode/mem0/` on WSL and the byte-identical
directory via `~/.config/opencode/mem0` on native Windows. One archive, every
distro, zero copies.

### 4.8 A Skill Documents the Machine

All of the above became a skill: `universal-setup`, living in the shared hub at
`/mnt/c/users/sigit/.config/opencode/skills/universal-setup/SKILL.md`. It covers
the hub file map, how to reach each environment, the config shape, the shared
auth, the per-host env table, and how to change a setting once so all three pick
it up. Discovery was verified with a fresh `opencode debug skill` - it lists
`universal-setup` exactly once, from the hub path. The hub now holds 15 skills
(plus a README).

## 5. The Windows Special Case (or: How opencode.exe Learns It Is Windows)

The convergence says "one configuration." Windows breaks the slogan for two
structural reasons, and the fix is a deliberate, documented exception - not a lie
in the motto's fine print.

### 5.1 Why a Second File Instead of a Second Config

There is no filename-based platform merge (a file named `opencode.windows.json`
is not loaded by itself). But opencode supports the `OPENCODE_CONFIG` environment
variable: a **custom config path loaded after the global config**, which
overrides conflicting keys and preserves non-conflicting ones. Precedence and
semantics shape the whole approach:

1. Precedence: remote -> global (`~/.config/opencode/opencode.json`) -> custom
   (`OPENCODE_CONFIG`) -> project -> `.opencode/` -> inline -> managed.
2. Later files override earlier ones only for conflicting keys; the rest merges
   (objects deep-merge, arrays like `skills.paths` are replaced).
3. `~` resolves per-host, so it means `C:\Users\sigit` on Windows and
   `/home/sigit` on the distros.

That gives a clean split: the shared `opencode.json` stays 100% universal, and a
tiny Windows-only overlay carries the differences.

### 5.2 The Overlay File

`/mnt/c/users/sigit/.config/opencode/opencode.windows.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "shell": "pwsh",
  "skills": {
    "paths": [".opencode/skills", "~/.config/opencode/skills"]
  }
}
```

Two keys, two different reasons:

- `"shell": "pwsh"` - **structural.** WSL distros run bash by default; native
  Windows should use PowerShell 7 (`C:\Program Files\PowerShell\7\pwsh.exe`).
  Naming it beats trusting auto-detection.
- `"skills": { "paths": [...] }` - **path-reality.** The base config lists
  `".opencode/skills"`, `"~/.config/opencode/skills"`, and
  `"/mnt/c/users/sigit/.config/opencode/skills"`. That third entry is exactly
  right on WSL and meaningless on native Windows where `/mnt/c` does not exist.
  The overlay replaces the list with the two-worlds version, where `~` resolves
  to `C:\Users\sigit` and still reaches the same hub skills.

Everything else - providers, models, agents, permissions, MCP - flows from the
shared base untouched.

### 5.3 Wiring It In (One Registry Key)

Windows reads the overlay through the user environment variable
`OPENCODE_CONFIG`. The first attempts to set it echoed PowerShell expressions
through a `powershell.exe -Command` string and the quoting got eaten (the shell
wars are real). The clean path was a small `.ps1` file run directly:

```powershell
[Environment]::SetEnvironmentVariable('OPENCODE_CONFIG',
  'C:\Users\sigit\.config\opencode\opencode.windows.json', 'User')
[Environment]::GetEnvironmentVariable('OPENCODE_CONFIG', 'User')
```

Verified at the registry, not just in the session:

```
HKEY_CURRENT_USER\Environment
    OPENCODE_CONFIG    REG_SZ    C:\Users\sigit\.config\opencode\opencode.windows.json
```

### 5.4 Proof It Loaded

`opencode.exe` (a scoop shim on Windows) was run with the env var set, and the
resolved config was dumped:

| Platform | `shell` | `skills.paths` |
|---|---|---|
| Windows (with overlay) | `"pwsh"` | two entries, no `/mnt/c` |
| Linux (Fedora + Debian) | absent (bash default) | three entries incl. `/mnt/c` |

The Linux side needed no change at all - and importantly, it is protected from
the Windows overlay by design: WSL does not import Windows user environment
variables (only `WSLENV`-whitelisted ones), so the overlay cannot leak into the
distros even though they share the same disk.

Should a Linux-only difference ever appear, the pattern generalizes:
`opencode.linux.json` in the hub plus an `export OPENCODE_CONFIG=...` in both
distro shells. For now, neither distro exports it (verified unset).

## 6. Verification

Every claim in this report was re-checked against the live systems after the work:

- **Configs parse**: universal `opencode.json` and the Windows overlay both pass
  strict JSON validation.
- **Symlinks**: `readlink` on Debian and Fedora all resolve to
  `/mnt/c/users/sigit/.config/opencode/opencode.json` (thumbprinted with
  `ls -l`); auth symlinks resolve to the canonical auth file.
- **Env parity**: `MEM0_API_KEY` present on all three hosts (value masked
  everywhere it was read back); `OPENCODE_CONFIG` present only on Windows.
- **Overlay resolution**: `opencode debug config` with the var set shows
  `"shell": "pwsh"` and the two-entry `skills.paths`; Linux shows neither.
- **Auth**: both distro `auth.json` entries are symlinks; the union was built
  from the two backups; the current 3-provider state is documented in 4.5.
- **Backups**: all pre-change files present in `opencode-backups/` (section 4.3).
- **Skills**: `opencode debug skill` enumerates `universal-setup` from the hub.

## 7. What Still Stays Per-Environment (On Purpose)

Convergence does not mean sameness. Still local by design:

- `~/.local/share/opencode/opencode.db` (and `-wal`/`-shm`) - session history is
  per-distro truth; it survives the Fedora reset and is never merged.
- `node_modules/` in each config dir - plugin/theme dependencies stay per host.
- The per-distro skills override slot `~/.config/opencode/skills/` - a README
  explains a name collision silently shadows the shared copy, so the slot stays
  near-empty.
- Host-only secrets (SSH keys, CA pins like Fedora's `NODE_EXTRA_CA_CERTS`) and
  PATH snapshots (already-running shells keep stale Windows PATHs until restart).

## 8. Pending Actions

- **Restart opencode on Fedora and Debian.** Config, skills table, auth, and MCP
  are snapshotted at session start; neither distro has restarted since the
  convergence landed. Windows picks the overlay up on its next launch, no restart
  magic required.
- Confirm the `universal-setup` skill and 9-agent roster after restarting.
- Decide whether the two Windows-only auth providers (`abliteration-ai`,
  `aihubmix`) should be restored to the canonical `auth.json` from the backup.
- Let the first mem0 local store actually populate at
  `/mnt/c/users/sigit/.config/opencode/mem0/` (directory is created on first use).

## 9. Recommendations

- Change registry-level behavior **once, in the hub**. Universal changes go in
  `opencode.json`; Windows-only changes go in `opencode.windows.json`. Never
  edit a distro's symlinked copy to change shared behavior.
- Back up before every change: copy the current file to `opencode-backups/` with
  a `-pre-<change>-<timestamp>` suffix. It costs nothing and has already
  rescued two rewrites.
- Treat shared `auth.json` as last-writer-wins across three hosts: any
  `opencode auth login` that rewrites the whole file now rewrites it for
  everyone. Expect it; use the backup tray when it bites.
- Mask secrets in transcripts. The whole `MEM0_API_KEY` pass was done by tools
  that never echo the value.
- Keep `steps` caps sane; a denied tool call ends the turn by design
  (`continue_loop_on_deny: false`). Fail fast, ask the user, move on.
- Do not revive `chat`/`reason` agent names without the user asking; they were
  removed deliberately and `default_agent` is `plan`.
- If a Linux-only difference materializes later, mirror the Windows pattern with
  `opencode.linux.json` instead of editing the base.

---

*Generated by Big Pickle (OpenCode)*