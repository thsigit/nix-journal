# MCP Servers Failed After Restart: `npx` Wrapper Breaks the Stdio Handshake

**Date:** 2026-09-30
**Author:** Codebot
**Topic:** opencode, mcp, gws, mem0, npx, stdio, plugin, fleet-sync

---

## 1. Objective

Document and fix a regression introduced while repairing the fleet: after correcting the plugin `id` mismatches and restarting OpenCode, both MCP servers (`gws` and `mem0`) failed to connect. The fix replaces the `npx -y <pkg>` invocation in `opencode.json` with a direct `node <local-entrypoint>` call, removing the `npx` wrapper that breaks OpenCode's MCP stdio handshake.

## 2. Background

OpenCode v2 runs two MCP servers declared in `~/.config/opencode/opencode.json` under the `mcp` block:

- **`gws`** — `@dguido/google-workspace-mcp`, launched via `npx -y @dguido/google-workspace-mcp`, authenticated from `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` env vars.
- **`mem0`** — `@mem0/mcp-server`, launched via `npx -y @mem0/mcp-server`, authenticated from `MEM0_API_KEY` (read from a file).

The same `opencode.json` is the shared hub file (Windows disk, canonical), synced byte-identical to FedoraWSL and DebianWSL. Only the two WSL distros run an OpenCode service; the hub does not.

This session had already: (1) built the four TypeScript plugins from root, (2) corrected the `plugin` array `id` mismatches (`fleet-sync` → `opencode-fleet-sync`, `opencode-google-workspace` → `google-workspace`), and (3) converged the plan/task git peers. The MCP failure appeared only **after the service restart** that picked up the corrected config.

## 3. Problem

After restart (`opencode mcp list`):

```
✗ gws   failed: Request timed out
✗ mem0  failed: Request timed out
```

The servers' processes were not staying connected to OpenCode's MCP client. Two distinct failure modes were observed across iterations:

1. **`Request timed out`** — with the original `npx -y <pkg>` command, and still after dropping `-y` (→ `npx <pkg>`).
2. **`Connection closed`** — after switching to a relative-path `node node_modules/<pkg>/dist/index.js` command.

The servers themselves were never broken: launching either manually with `npx -y` or `node` produced a valid MCP `initialize` response in under 1 second, with correct JSON-RPC on stdout. The fault was in **how OpenCode spawns and pipes the subprocess**, not in the server code.

## 4. Diagnosis

The decisive test: run the exact server command in a shell and feed it an `initialize` request.

```
$ printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize",...}' \
    | npx -y @dguido/google-workspace-mcp
{"result":{...,"serverInfo":{"name":"google-workspace-mcp","version":"3.4.4"},...},"jsonrpc":"2.0","id":1}
# exits 0, ~1.5s
```

The server works. So the failure is specific to OpenCode's supervisor:

- `npx` spawns the real `node` server as a **child of the npx process**. OpenCode's stdio pipes connect to `npx`, not directly to the server. The extra process hop, plus `npx`'s own stderr/probe output, interferes with the JSON-RPC stream and the connect timeout fires.
- Even `npx` *without* `-y` keeps the wrapper layer and still failed (timeout → after config change, "Connection closed").
- A **relative** `node node_modules/.../dist/index.js` command produced "Connection closed" because OpenCode does not spawn MCP commands with the config directory as CWD — the relative path resolved against the wrong directory, `node` couldn't find the entrypoint, and exited immediately.

Conclusion: **bypass `npx` entirely and invoke the server's entrypoint with `node` via an absolute path.**

## 5. Work Performed

### 5.1 Install MCP servers locally (no network at spawn)

On each runtime host, install the packages into the local `node_modules` so no `npx` fetch is needed:

| Step | Action |
|------|--------|
| **5.1.1** | `cd ~/.config/opencode && npm install --no-save @dguido/google-workspace-mcp @mem0/mcp-server` (FedoraWSL) |
| **5.1.2** | Same command on DebianWSL (via `wsl.exe -d Debian`) |
| **5.1.3** | Hub install attempted but blocked by EACCES rename races on the WSL-mounted Windows disk; **not required** — the hub runs no service |

Verified local binaries exist:
```
~/.config/opencode/node_modules/.bin/google-workspace-mcp
~/.config/opencode/node_modules/.bin/mem0-mcp
~/.config/opencode/node_modules/@dguido/google-workspace-mcp/dist/index.js
~/.config/opencode/node_modules/@mem0/mcp-server/dist/index.js
```

### 5.2 Change the MCP `command` (hub-first)

Edited the hub `opencode.json` `mcp` block, replacing `npx` with direct `node`:

```json
"gws": {
  "type": "local",
  "command": ["node", "/home/sigit/.config/opencode/node_modules/@dguido/google-workspace-mcp/dist/index.js"],
  "environment": { "GOOGLE_CLIENT_ID": "{env:GOOGLE_CLIENT_ID}", "GOOGLE_CLIENT_SECRET": "{env:GOOGLE_CLIENT_SECRET}", "GOOGLE_WORKSPACE_SERVICES": "drive,docs,sheets,slides,gmail" },
  "enabled": true
},
"mem0": {
  "type": "local",
  "command": ["node", "/home/sigit/.config/opencode/node_modules/@mem0/mcp-server/dist/index.js"],
  "environment": { "MEM0_API_KEY": "{file:~/.config/opencode/mem0.key}" },
  "enabled": true
}
```

### 5.3 Sync and restart

| Step | Action |
|------|--------|
| **5.3.1** | `rsync` hub `opencode.json` → Fedora `~/.config/opencode/opencode.json` |
| **5.3.2** | `cat >` hub `opencode.json` into Debian `~/.config/opencode/opencode.json` via `wsl.exe -d Debian` |
| **5.3.3** | Verified all three `opencode.json` byte-identical (`md5sum` match) |
| **5.3.4** | `opencode service restart` on Fedora |

### 5.4 Verify

```
$ opencode mcp list
✓ gws   connected
✓ mem0  connected
```

- `mem0` end-to-end confirmed (`search-memories` returns cleanly).
- `gws` is connected and re-appears in the live tool catalog.

## 6. Key Findings

- **`npx` is unsafe for MCP `command` entries under OpenCode's supervisor.** The wrapper process hops the stdio pipe and emits probe output that breaks the JSON-RPC handshake. Either `Request timed out` (npx network/probe) or `Connection closed` (wrapper child death) results.
- **Direct `node <entrypoint>` is the correct invocation.** It execs the server in-process (no wrapper), so OpenCode's stdio connects straight to the server.
- **Relative paths in MCP `command` do not resolve against the config dir.** OpenCode does not spawn MCP commands with CWD = config directory, so a relative `node_modules/...` path fails. Use an **absolute** path.
- **Local install per host is required.** The `sync-opencode` rule excludes `node_modules` from rsync, so each host must `npm install` its own MCP servers locally. The shared config only names the absolute entrypoint.
- **The `npx -y` → `npx` → relative `node` → absolute `node` progression** was the diagnostic path; only the last form works reliably.

## 7. Portability Note

The absolute path `/home/sigit/.config/opencode/node_modules/...` is identical on FedoraWSL and DebianWSL (both `/home/sigit`). The Windows hub uses a different path but runs no service, so the byte-identical shared config is harmless there. If the hub ever serves, its entrypoint would need the Windows equivalent (`C:\Users\SIGIT\.config\opencode\node_modules\...`) — ideally placed in an overlay, not the shared file, per the `sync-opencode` host-local rule.

## 8. Remaining Issue (separate, pre-existing)

`gws` **connects** but its real tool calls hit a Google **auth timeout** — the WSL distros lack `~/.config/google-workspace-mcp/credentials.json` (only `tokens.json`, which has no OAuth client behind it). This is tracked separately as `TASK-distro-gws-credentials-missing`. The MCP *connection* layer is fully fixed; the *auth* layer is the next task.

## 9. Lessons for the Unified Fleet-Sync Skill

The `TASK-unified-fleet-sync-skill` plan should codify this: `syncConfig()` must verify not just that plugins build and `opencode.json` is byte-identical, but that **MCP `command` entries use direct `node` invocations of locally-installed entrypoints**, never `npx`. The `buildPlugins()` step already installs `@opencode/plugin` + `typescript` at root; the same local-install discipline must extend to MCP servers so no spawn-time network fetch can break a service restart.
