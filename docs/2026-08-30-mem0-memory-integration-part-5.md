# Mem0 Memory Integration - Part 5

*From plugin to MCP, and a local store that survives the quota wall*

**Date:** 2026-08-30  
**Author:** Codebot  
**Topic:** Mem0, OpenCode, MCP, memory, local store

---

## 1. Objective (or: The Plugin Had a Good Run)

Part 4 ended with 210 tidy memories and a promise to let mem0-dream keep house. This part does something more structural: it **retires the `@mem0/opencode-plugin`** (and all nine `mem0-*` skills that rode along with it) and swaps cross-session memory onto a **remote MCP server**, where the agent decides when to read and write rather than the plugin auto-injecting context every session.

Then it builds a second, quieter thing: a **local, quota-free memory store** at `/mnt/c/users/sigit/.config/opencode/mem0/` (the shared Windows-side hub, so one archive serves every distro) that buffers memories as plain markdown until they are merged into the cloud on an occasional basis.

The end state: one consolidated `mem0` skill, a cloud backend for durable knowledge, and a local text archive that keeps working even when the cloud says "you are out of budget this month."

## 2. Background (A Plugin, Nine Skills, and a Growing Tax)

From Part 1 and Part 2, memory went from a hand-rolled Python client to the official `@mem0/opencode-plugin`. That plugin shipped nine skills (`mem0-context-loader`, `mem0-dream`, `mem0-forget`, `mem0-pin`, `mem0-remember`, `mem0-scope`, `mem0-search`, `mem0-status`, `mem0-tour`) and a promise of automatic context injection. From Part 3 and Part 4, the store itself proved its worth: deduplication, noise pruning, categorized types (`decision`, `task_learning`, `anti_pattern`, ...), and a 19% reduction in 259 memories during a dream run.

But the plugin had a habit. Every opencode session would wake up, load nine skills, and auto-inject whatever it thought was relevant, whether the agent asked for it or not. That is convenient, and it is also a tax: startup weight, a fixed context budget spent before a single turn, and a hidden control flow the agent does not steer.

## 3. Problem (Three Irritations Looking for a Decision)

1. **Auto-injection you never asked for.** Context was loaded whether the task needed memory or not. The agent should decide, not the plugin.
2. **The search quota wall.** mem0 metered SEARCH events. On 2026-08-30 the account sat at 1000/1000 SEARCH events for the month, with reads blocked until the reset at 2026-09-01T00:00:00Z. The plugin's auto-injection is, at bottom, a steady stream of reads - a meter burning in the background. When reads are blocked, even a plugin that wants to be helpful has nothing to inject.
3. **Nine skills for one job.** Most of the nine lived a life of quiet redundancy. Plenty of surface area, little reason.

The user's verdict: remove all mem0 plugins and skills except **one** consolidated skill, switch to a remote MCP server, and let the agent decide when to touch memory. Plus the new idea - temporary local storage as a buffer, so memory capture is never hostage to a quota.

## 4. Work Performed

### 4.1 The Config Swap (plugin -> MCP)

The config swap now lives in the **universal** config at `/mnt/c/users/sigit/.config/opencode/opencode.json` - the Windows-side hub that is the source of truth from `three-distros-one-opencode-setup-part-1`. FedoraWSL and Debian both symlink their `~/.config/opencode/opencode.json` to that file, and native Windows reads it directly. Originally the swap had been applied only to FedoraWSL's local `opencode.json` (Debian uses `opencode.jsonc`; the hub file had no `plugin`/`mcp` keys) - a discrepancy closed by the convergence pass below (section 11).

Before:
```json
"plugin": ["@mem0/opencode-plugin"]
```

After:
```json
"plugin": [],
"mcp": {
  "mem0": {
    "type": "remote",
    "url": "https://mcp.mem0.ai/mcp/",
    "headers": {
      "Authorization": "Token {env:MEM0_API_KEY}"
    },
    "oauth": false
  }
}
```

The `MEM0_API_KEY` stays in the environment (prefix `m0-dWS...`); the config references it via `{env:MEM0_API_KEY}` rather than embedding the secret. JSON validated (initially against the FedoraWSL file, then against the universal hub config): `plugin` is an empty array, the `mem0` MCP block is present.

### 4.2 Skills: Nine In, One Out

- The retired plugin's skills vanish with the plugin (they are only installed as part of the package).
- `mem0-dream` in the shared skills hub was **deleted**.
- A single **`mem0`** skill was written to `/mnt/c/users/sigit/.config/opencode/skills/mem0/SKILL.md`. It adopts the useful bits the plugin skills got right - the identity values (`user_id=sigit`, `app_id=sigit`), the metadata `type` classification table, async write confirmation via `get_event_status`, dual-search recall, and update-over-delete - and drops the auto-injection. It also documents an MCP quirk discovered during a probe: `delete_memory` takes `memory_id`, not `id`.
- The shared skills `README.md` and `CONTEXT.md` were updated (CONTEXT.md line 9 now describes memory as "mem0 via remote MCP server ... agent decides when to use it (see `mem0` skill)").

### 4.3 MCP End-to-End Verified Over HTTP

The remote MCP server speaks streamable HTTP. A raw `curl` probe (with `Accept: application/json, text/event-stream`) against `https://mcp.mem0.ai/mcp/` confirmed:

| Step | Result |
|---|---|
| `initialize` | 200, `serverInfo` name=mem0 version=1.29.1 |
| `tools/list` | 11 tools |
| `add_memory` | `event_id` returned, status PENDING (async write) |
| `get_event_status` | event_type ADD, source MCP, status RUNNING |

The 11 tools exposed by the MCP server:

```
add_memory, search_memories, get_memories, delete_all_memories,
list_entities, get_memory, update_memory, delete_memory,
delete_entities, list_events, get_event_status
```

Notably, `add_memory` is **asynchronous**: it returns an `event_id`, not a memory ID. Confirmation requires a follow-up `get_event_status(event_id=...)` poll. That async contract is baked into the skill's guidance.

### 4.4 The Quota Wall, Live-Confirmed

The same probing session that proved writes worked also proved why the local store matters. A `search_memories` call returned:

```json
{
  "error": "Usage quota exceeded for this billing period. Please upgrade your plan at https://app.mem0.ai/dashboard/billing.",
  "event_type": "SEARCH",
  "quota_limit": 1000,
  "quota_used": 1000,
  "quota_reset": "2026-09-01T00:00:00+00:00"
}
```

And `get_memories` (the browse path) hit the **same** SEARCH meter - so when reads are exhausted, no read path works, writes or no writes. Writes kept working. Reads were the casualty. That asymmetry is exactly the hole a local store fills.

### 4.5 The Local Offline Store (`mem0-local.py`)

A new CLI, `mem0-local.py`, lives beside the skill at `/mnt/c/users/sigit/.config/opencode/skills/mem0/`. It manages a directory of plain markdown files, one memory each, at `/mnt/c/users/sigit/.config/opencode/mem0/` - the shared Windows-side hub, so one archive serves every distro (native Windows resolves the identical directory via `~/.config/opencode/mem0`). Every file carries a small `---` frontmatter block:

```
id: m-20260830-143629-d50f
type: decision
branch: main
confidence: 1.0
scope: project
source: agent
created: 2026-08-30T06:36:29+00:00
cloud_id: <set when merged to cloud>
```

Commands (all exercised end-to-end in testing):

| Command | Purpose |
|---|---|
| `add "<text>" [--type --branch --confidence --scope]` | write a memory locally |
| `search <query...>` | keyword match (case-insensitive, quoted multi-word ok) |
| `list [--unsynced] [--type TYPE]` | enumerate, optionally only not-yet-merged |
| `get <id-or-prefix>` | read one memory's full body |
| `mark-synced <id> [--cloud-id ID]` | record that a local entry was merged to cloud |
| `delete <id-or-prefix>` | remove a local entry |
| `status` | totals synced/unsynced, breakdown by type |

The store is deliberately simple - no semantic search, just term-count ranking over plain text - because simple is robust. When cloud search is a wall, a `grep`-able archive of decisions is a feature, not a compromise.

Testing surfaced three real bugs, each caught by exercising the CLI rather than trusting it:

1. `add` received the text as a list and tried to `.strip()` it - crash, leaving an empty file. Fixed by joining args.
2. Prefix lookup only matched the start of the full id (`m-2026...`), so the handy short tail (`d50f`) did not resolve. Fixed to also match the last id segment.
3. A quoted multi-word query (`search "mem0 plugin MCP"`) arrived as one token and never matched. Fixed by splitting each arg on whitespace.

The store was cleaned up after testing, leaving its directory ready for real use.

## 5. Diagnosis

Two distinct layers now handle memory:

- **Cloud (MCP)**: durable, semantic, cross-session truth. Subject to the SEARCH quota and an async write contract.
- **Local (`/mnt/c/users/sigit/.config/opencode/mem0/`)**: quota-free, greppable, transient, shared across distros via the Windows hub. A buffer and a safety net.

The agent workflow, per the skill: write to the cloud normally; if `add_memory` fails or reads are quota-exhausted, fall back to `mem0-local.py add` (same `type` classification). Recall while blocked uses `mem0-local.py search`. Merging is an explicit, occasional act - list the unsynced set, push each to cloud `add_memory`, then `mark-synced` or `delete`.

## 6. Preliminary Assessment

The migration is clean on the config and skill surface. The MCP write path is proven. The remaining open thread is that the local store's full value shows itself under the same condition that blocks verification of it against the cloud: the quota wall. We cannot yet prove a local-to-cloud merge round-trip because reads are down until the reset.

## 7. Solution Summary

- Retired `@mem0/opencode-plugin` and all nine `mem0-*` skills; removed `mem0-dream`.
- Added `mcp.mem0` remote MCP config (token from env); emptied the plugin array.
- Wrote one consolidated `mem0` skill; updated CONTEXT.md and the skills README.
- Verified MCP over HTTP: initialize, 11 tools, async `add_memory` -> `get_event_status` (source MCP).
- Confirmed the SEARCH quota wall live (1000/1000, reset 2026-09-01Z), including that `get_memories` reads are metered the same way.
- Built `mem0-local.py`: quota-free local memory store with add/search/list/get/delete/mark-synced/status; tested end-to-end with three fixed bugs.

## 8. Verification Plan

- On the next opencode session, confirm the `mem0` skill loads and the MCP tools appear under the `mem0` MCP prefix (both are snapshotted at session start, so this session cannot show them yet).
- After the SEARCH quota reset (2026-09-01T00:00:00Z), prove the local-to-cloud merge: `mem0-local.py add` something, cloud `add_memory` it, then `mark-synced`.
- Delete the `BLOGPROBE transient verification write` probe entry created during verification (its write succeeded but, with reads blocked, its memory ID could not be discovered to delete it; it is labeled for manual cleanup).
- DONE (2026-08-30 evening, section 11): the plugin->MCP config was converged into the universal `/mnt/c/users/sigit/.config/opencode/opencode.json`, symlinked by both FedoraWSL and Debian and read natively by Windows. Earlier drafts wrongly said a DebianWSL `opencode.json` was the source; there is no such file (Debian uses `opencode.jsonc`), and parity was never "apply to Fedora" - Fedora already had it.

## 9. Pending Actions

- DONE (2026-08-30 evening, section 11): the MCP + plugin-removal config was ported from FedoraWSL's file into the universal hub config, which all three environments now share; `MEM0_API_KEY` is exported on all three.
- Clean up the BLOGPROBE entry after quota reset.
- Do a post-restart smoke test (skill loads + MCP tools under `mem0` prefix).
- Consider whether the local store should also serve as the landing zone for auto-capture before any cloud write, i.e. make local-first the default rather than the fallback.

## 10. Recommendations

- Keep the split explicit: cloud for durable, semantic, cross-session truth; local for quota-free buffering and archives.
- Treat writes as async - always `get_event_status` before reporting a memory ID.
- Do not route reads that can be local when the cloud SEARCH meter is at risk; the local store exists exactly for that.
- On the next merge, decide whether `cloud_id` on a local file should store the cloud memory ID (so future edits can `update_memory` instead of duplicate) - currently marked as just `synced`.
- Keep the local store plain text. Its whole edge is that it degrades gracefully and searches without a budget.

## 11. Erratum & Universal Convergence (2026-08-30 evening)

This report originally mis-stated two things and left one promise unfilled; all three were corrected the same evening:

1. **Wrong host claimed.** The draft said the source of truth was `~/.config/opencode/opencode.json` "on the DebianWSL host." There is no `opencode.json` on Debian (it uses `opencode.jsonc`), and the `plugin: []` + `mcp.mem0` block actually lived in FedoraWSL's file. The intended source of truth is the shared hub `/mnt/c/users/sigit/.config/opencode/opencode.json`.
2. **Wrong store path claimed.** The draft (and the tool) said the local archive lives at `~/.config/opencode/mem0/` (per-host). The intended path is the shared `/mnt/c/users/sigit/.config/opencode/mem0/` so one archive serves every distro.
3. **The fix was left pending.** Rather than merely re-documenting the intent, the settings were actually converged this evening, turning three environments into one configuration:

   - The **universal config** `/mnt/c/users/sigit/.config/opencode/opencode.json` now carries the hub's full provider/agent/command menu **plus** the FedoraWSL additions (`plugin: []`, `mcp.mem0`, `permission.bash`, `experimental.continue_loop_on_deny: false`, `skills.paths`, `provider.nvidia` whitelist, `writer` agent/command) and `steps: 32` on every agent.
   - FedoraWSL and Debian `opencode.json` are now **symlinks to the hub file**; native Windows reads it directly. Debian's `opencode.jsonc` was retired (backed up).
   - `MEM0_API_KEY` is exported on **all three** (Fedora pre-existing; Debian `~/.bashrc`; Windows user env, set without exposing the secret).
   - `mem0-local.py` resolves `STORE` to `/mnt/c/users/sigit/.config/opencode/mem0` on WSL and the identical directory via `~/.config/opencode/mem0` on native Windows; the `mem0` skill documents the universal path.
   - Pre-change files were backed up under `/mnt/c/users/sigit/.config/opencode-backups/` (`opencode-{hub,debian,fedora}-pre-universal-*.json*`).

   Deliberate deviations kept for stability: default model stays `litellm/kenari/kenari-free` and `default_agent` stays `chat` (Fedora's `reason`/nemotron defaults can be flipped on if preferred). Restart opencode on FedoraWSL and Debian for the new config to load (snapshotted at session start).

---

*Generated by Big Pickle (OpenCode)*
