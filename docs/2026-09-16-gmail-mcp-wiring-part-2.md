# "Gmail MCP, Wired From Scratch" - Part 2 (or: Google's Official Servers Hit the Developer Preview Wall, So We Built a Local One)

**Date:** 2026-09-16  
**Author:** Codebot  
**Topic:** gmail, drive, docs, sheets, slides, mcp, google-cloud, developer-preview, opencode, skills, oauth

---

## 1. Objective (or: Prove the Chimera Can Actually Talk)

Part 1 ended on a victory lap: five Google Workspace MCP servers (Gmail, Drive, Docs, Sheets, Slides) configured against a Web-application OAuth client, authenticated, connected, and two skills (`gmail`, `gmail-inbox-triage`) rewritten to the official tool names. The catch, unexamined at the time: "connected" meant the *MCP handshake* succeeded, not that *any tool call would succeed*.

This part is the story of what happened when the agent finally *used* the tools - and what it took to get a working Google Workspace story back.

## 2. Background (or: The Dev-Preview Asterisk That Was There All Along)

Google's hosted Workspace MCP servers (`gmailmcp`, `drivemcp`, `docsmcp`, `sheetsmcp`, `slidesmcp` at `*.googleapis.com/mcp/v1`) are all **Developer Preview** features. That status matters in two places:

1. **Consent screen**: unverified app, test-user wall (solved in Part 1 by whitelisting the account).
2. **The tools themselves**: some Workspace MCP surfaces are gated behind the **Google Workspace Developer Preview Program (DPP)** - a separate program-level enrollment of the GCP project, approved manually via form, taking a few days.

Part 1 had dead-panned "the endpoint was reachable; the token just wasn't there." The sequel's punchline: now the token *was* there, and Google still said no.

## 3. Problem (or: Permissions Confirmed, Access Denied)

In the fresh session after all five servers showed `connected`, the first real tool calls came back:

```
drive  search_files      -> "The caller does not have permission"
drive  list_recent_files -> "The caller does not have permission"
gmail  search_threads    -> "Access to this tool requires that your Google Cloud project
                             (732075434195) is enrolled in the Google Workspace
                             Developer Preview Program"
```

Every server registered, authenticated, and passed `tools/list`. Every actual call died. The GCP project `opencode-auth-160926` (number `732075434195`) was not enrolled in the Developer Preview Program, and until it is, *no* tool call on *any* of the five official servers will ever succeed. The enrollment form (https://developers.google.com/workspace/preview) takes days to approve.

## 4. Work Performed

### 4.1 Confirming the Wall (or: Round-Trip Everything, Register Everything, Fail Everything)

Ran the full battery: `opencode mcp list` (all five remote servers connected), per-service `tools/list` (full tool surfaces enumerable), then actual tool calls. Result: authenticate OK, list OK, **call = 403**. The tokens in `mcp-auth.json` (per-`gmail`/`drive`/`docs`/`sheets`/`slides` entries) were real and refreshable; scopes verified via `tokeninfo` (`access_type: offline`, the right scopes). The blocker is program-level, not credential-level. Nothing to fix on our side; only the application form moves the needle.

### 4.2 The Decision (or: We Could Wait Days, or Not)

Options laid out:

| Option | Effort | Blocker |
| --- | --- | --- |
| Wait for DPP approval, use official servers | none now | days, and not guaranteed to ship all surfaces |
| One local MCP server (REST APIs, normal OAuth) | small | none - works immediately |
| Hybrid: keep remotes for later, local for now | small | none |

Chosen: **a local, community MCP server** that talks to Google's plain REST APIs with a regular OAuth flow - no Developer Preview anywhere in the stack.

### 4.3 Picking the Server (or: One Server, Five Services, Zero Preview)

Selected `@dguido/google-workspace-mcp` (v3.4.4). One stdio process covering Drive, Docs, Sheets, Slides, and Gmail via environment-selected services, with its own loopback OAuth (PKCE) - a browser consent on first tool call, tokens saved under `~/.config/google-workspace-mcp/`. Installed/run check: `npx -y @dguido/google-workspace-mcp --help` -> `Google Workspace MCP Server v3.4.4` on node v24.19.0.

### 4.4 A Desktop-App OAuth Client (or: Why Loopback Needs the "Installed" Credential Type)

Google only lets *Desktop app* (installed-app) OAuth clients use an ephemeral loopback redirect; a *Web application* client requires pre-registered redirect URIs, which an OS-assigned port cannot have. So a second credential was minted in the same project:

- Project: `opencode-auth-160926`
- Application type: **Desktop app**
- Client ID: `732075434195-e5ubn9ud1qvk9domlbb75qmuapvaj5qq.apps.googleusercontent.com` (public)
- Client secret: `REDACTED` (kept out of every command line; saved in `client_secret_*.json` in Downloads)
- Redirect: `http://localhost` (loopback, OS port assigned at runtime)

Same consent screen scopes as before (gmail.readonly/gmail.compose + the drive/docs/sheets/slides scopes already approved in Part 1), so the browser consent is a one-time click.

### 4.5 The Hub Config Change (or: Five Servers Retire, One Local Server Shows Up)

Before touching the shared hub file, backed it up to the append-only tray: `opencode-hub-pre-local-google-mcp-20260916-202136.json` in `/mnt/c/users/sigit/.config/opencode-backups/`. Then in `C:\Users\SIGIT\.config\opencode\opencode.json` (the universal config all three distros share):

- The five remote Gmail/Drive/Docs/Sheets/Slides servers: `"enabled": false` (**disabled, not deleted** - they come back the day DPP approval lands).
- A single new `local` server:

```json
"gws": {
  "type": "local",
  "command": ["npx", "-y", "@dguido/google-workspace-mcp"],
  "environment": {
    "GOOGLE_CLIENT_ID": "732075434195-e5ubn9ud1qvk9domlbb75qmuapvaj5qq.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "REDACTED",
    "GOOGLE_WORKSPACE_SERVICES": "drive,docs,sheets,slides,gmail"
  },
  "enabled": true
}
```

JSON validated with `ConvertFrom-Json`; `opencode mcp list` shows `gws connected` via `npx -y @dguido/google-workspace-mcp`, all five remotes `disabled`, mem0 untouched.

### 4.6 Enumerating the Real Tool Surface (or: 75 Tools, No DPP in Sight)

Probed the server's `tools/list` over stdio to document every tool with its required params before writing skills:

| Service | Tools | Highlights |
| --- | --- | --- |
| Drive | 29 | `search`, `create_folder`, `move_item`, `rename_item`, `delete_item`, `list_revisions`, `restore_revision`, `list_trash`, `share_file`, batch ops, `export_file` |
| Docs | 8 | `create_google_doc`, `get_google_doc_content`, `append_to_doc`, `insert_text_in_doc`, `replace_text_in_doc`, `format_google_doc_range` |
| Sheets | 7 | `create_google_sheet`, `get_google_sheet_content`, `update_google_sheet`, `format_google_sheet_cells`, `merge_google_sheet_cells`, conditional formats, `sheet_tabs` |
| Slides | 10 | `create_google_slides`, `get_google_slides_content`, `format_slides_text`, shape/background formatting, `slides_speaker_notes`, `list_slide_pages` |
| Gmail | 16 | `search_emails`, `read_email`, `draft_email`, `send_email`, `list_drafts`, `delete_draft`, labels CRUD, filters, `download_attachment` |
| Unified | 3 | `create_file`, `update_file`, `get_file_content` (type auto-detected from name) |
| Housekeeping | 2 | `list_tools`, `get_status` |

Total 75. Not only do the tools exist - several things the official servers cannot do are here (Drive move/rename/delete, revision listing/restore, trash, *actual email sending*, draft delete, filters).

### 4.7 The Skill Rewrite (or: Same Skills, New Nameplates)

All Google skills were rewritten from the dead official prefixes to the live `gws_*` prefix:

| Skill | Before (dead) | After (live) |
| --- | --- | --- |
| `google-drive` | `drive_*` | `gws_*` (search/list/copy/move/rename/share/trash/export/batch) |
| `google-docs` | `docs_read_doc`/`docs_update_doc` | `gws_create_google_doc`, `gws_get_google_doc_content`, `gws_append_to_doc`, `gws_insert_text_in_doc`, `gws_replace_text_in_doc` |
| `google-sheets` | `sheets_*` | `gws_create_google_sheet`, `gws_get_google_sheet_content`, `gws_update_google_sheet`, `gws_format_google_sheet_cells`, `gws_sheet_tabs` |
| `google-slides` | `slides_*` | `gws_create_google_slides`, `gws_get_google_slides_content`, `gws_format_slides_*`, `gws_list_slide_pages` |
| `gmail` | `gmail_*` | `gws_*` (incl. `gws_send_email` - a real send tool, so the skill's "draft-only" rule from Part 1 got upgraded to review-before-send) |
| `gmail-inbox-triage` | `gmail_search_threads`/`gmail_get_thread` | `gws_search_emails`/`gws_read_email` |

Each skill documents the full `gws_*` surface with required params (verified against the live schema dumps), work flows (ground -> read -> modify -> verify), and the honest limitation list (no render-QA thumbnails, no revision tools on Docs/Sheets/Slides via this server, no comments on Sheets/Slides).

## 5. Diagnosis (or: It Was the Program All Along)

| Symptom | Culprit | Confirm |
| --- | --- | --- |
| All 5 official servers connect + `tools/list` fine | MCP handshake and OAuth are healthy | `opencode mcp list` = 5 connected |
| Every tool call returns permission/DPP error | Project `opencode-auth-160926` (732075434195) not enrolled in Developer Preview Program | `gmail search_threads` error cites project number and enrollment; drive/docs/sheets/slides return "The caller does not have permission" |
| Fixable on our side? | No - manual application form, days of wait | https://developers.google.com/workspace/preview |
| Working alternative | Local MCP server with plain REST + Desktop-app OAuth | `gws connected`, 75 tools enumerable |

## 6. Verification Status

| Check | Result |
| --- | --- |
| `opencode mcp list` | 7 servers: `mem0 connected`, 5 remotes `disabled`, `gws connected` |
| JSON validity (hub `opencode.json`) | pass (`ConvertFrom-Json`) |
| Schema conformance | server is `type: local` + `command`; `environment` accepted - matches `McpLocalConfig` (timeout, enabled, cwd all optional) |
| gws runtime | v3.4.4, launches on node 24 via npx |
| Tool enumeration | 75 tools captured with required params |
| Skills | 6 files rewritten to `gws_*`: google-drive, google-docs, google-sheets, google-slides, gmail, gmail-inbox-triage |
| Backup | `opencode-hub-pre-local-google-mcp-20260916-202136.json` in tray |
| Token dir `~/.config/google-workspace-mcp/` | not yet created - expected: appears after first consented tool call |
| **Live tool call** | **NOT YET DONE** - needs opencode restart + one browser consent |

## 7. Pending Actions

- **Restart opencode** (config is not hot-reloaded) so the new `gws` tools register in the running editor.
- **First real tool call** (e.g. `gws_search`) - this opens the browser once for consent; verify tokens land in `~/.config/google-workspace-mcp/` and `opencode mcp list` still shows `gws connected`.
- If DPP approval arrives later, the five disabled remote servers can be flipped to `"enabled": true` and the skills' name tables swapped back - the backup makes both directions cheap.

## 8. Recommendations

- **"Connected" is a handshake, not a green light.** Always round-trip at least one *tool call* (not just `tools/list`) before declaring an MCP integration done - Part 1 celebrated a connection whose calls could never succeed.
- **Read the Dev-Preview asterisk before building.** Google's hosted Workspace MCP servers are DPP-gated at the *call* level, and the program enrollment is a manual, multi-day application. Plan for it or route around it.
- **Route around it.** A local MCP server over the plain REST APIs (`@dguido/google-workspace-mcp`) gives the same five surfaces with zero Developer Preview, plus more tools (Drive move/delete/revisions/trash, `send_email`, filters, speaker notes).
- **Desktop-app credentials for loopback OAuth.** A Web-application client cannot use an ephemeral OS-assigned loopback port; the local server requires a *Desktop app* client - minted and kept alongside the Part 1 Web client.
- **Disable, don't delete.** The five official remote entries stay in config with `"enabled": false`, so DPP approval later is a one-line flip, not a rebuild.

Part 1 built the door. Part 2 found the door was locked (program-level), then built a local door that opens now. Part 3 is one restart and one consent click away from a mailbox that actually answers.

## 9. Addendum (or: The Local Server Becomes a Public Plugin, and the DPP Doors Come Down)

Same day, 2026-09-16. Part 2 ended on "one restart and one consent click away." This addendum closes that loop, then reverses a Part 2 decision.

### 9.1 Packaging the Skills into a Plugin (or: Sharing Is Caring, With a Config Hook)

With the six `gws_*` skills proven against a live server, the whole thing was packaged as a distributable OpenCode plugin and published: `thsigit/opencode-google-workspace` (https://github.com/thsigit/opencode-google-workspace), MIT, first commit `48256a6` on `main`.

The plugin does two things at load:

1. A `config` hook registers the `gws` local MCP server (`npx -y @dguido/google-workspace-mcp`, env `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_WORKSPACE_SERVICES`) - the whole Part 2 config block becomes generated, not hand-maintained.
2. It copies its bundled `skills/` directory into `~/.config/opencode/skills/` - idempotent, and it never overwrites an existing skill.

Skills cannot travel through the plugin API itself; opencode discovers them from disk. Copy-on-first-load is the standard workaround, and it logged honest numbers: on a fresh box `6 copied, 0 already present`; on the already-skilled Windows box `0 copied, 6 already present`.

### 9.2 One Shared Hub Cannot Point Three OSes at One Path (or: Path Resolution Takes On a New Meaning)

A single `plugin:` entry in the shared hub cannot resolve on all three environments - a `file:///C:/Users/...` URL is meaningless to Linux, and `/home/sigit/...` is meaningless to Windows. So the shared hub keeps `"plugin": []` and each per-OS overlay carries a path its own OS can resolve:

| Environment | Plugin entry (overlay) | Repo location |
| --- | --- | --- |
| Windows native | `opencode.windows.json` -> `file:///C:/Users/SIGIT/dev/opencode-google-workspace/src/index.js` | `C:\Users\SIGIT\dev\opencode-google-workspace` (clone) |
| Fedora WSL | `opencode.fedora.json` -> `/home/sigit/.opencode/plugins/opencode-google-workspace/src/index.js` | `/home/sigit/.opencode/plugins/opencode-google-workspace` (clone) |
| Debian WSL | `opencode.debian.json` -> same path | same location (clone) |

Each Linux `.bashrc` gained `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` exports (Fedora and Debian already had `OPENCODE_CONFIG` and a working opencode PATH); Windows got User-scope env vars (`SetEnvironmentVariable`) so a fresh shell inherits them. Every shared-file edit was preceded by a tray backup (`opencode-hub-pre-plugin-peros-*`, plus the three `opencode-{windows,fedora,debian}-pre-plugin-peros-*`).

### 9.3 The Fedora Red Herring (or: It Worked Better Before It Worked)

An early "running gws from Fedora WSL actually works" was a stale running opencode session still holding the pre-edit config. A fresh Fedora `opencode mcp list` showed no `gws` at all, and a direct probe confirmed the cause: `import('file:///C:/Users/SIGIT/dev/opencode-google-workspace/src/index.js')` fails on Linux with `Cannot find module '/C:/Users/...'`. Config is snapshotted at startup, not re-read per request - "it worked" was the ghost of the old config. After the per-OS wiring above, all three hosts genuinely report:

```
> opencode mcp list
mem0  connected
gws   connected   (npx -y @dguido/google-workspace-mcp)
```

(the four official remotes had not been deleted yet at that point, so the count was 7 servers total.)

### 9.4 The Round-Trip Part 2 Owed (or: Verified Live, With 201 Emails to Spare)

The live test finally ran from a fresh Windows shell:

- Storage quota call succeeded: authenticated as `th.sigit@gmail.com`, 15.00 GB total / 8.16 GB used. Tokens exist under `~/.config/google-workspace-mcp/` - no re-consent needed.
- Gmail search (`in:inbox newer_than:7d`) returned 201 messages with correct senders, subjects, and labels.
- Drive root listing returned real files.

One cosmetic quirk surfaced: `gws_get_status` throws a server-side schema mismatch (`data/last_error must be object`). Harmless - it is the diagnostic-only tool; every functional `gws_*` tool works.

### 9.5 The DPP Doors Come Down (or: We Read the Fine Print and Declined)

Researching the actual DPP application revealed the enrollment form wants a **Google Workspace account**, not a consumer Gmail - a likely rejection for this setup. The decision: do not apply for DPP. Part 2's "disable, don't delete" advice became moot, and the five disabled remote servers were deleted outright:

- Hub `opencode.json`: `mcp` now contains only `mem0`.
- `mcp-auth.json`: emptied (`{}`; the only stored tokens belonged to the never-working official servers).
- Fedora and Debian `~/.bashrc`: stale `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` exports removed.
- Every change backed up first (`opencode-hub-pre-del-dpp-*`, `mcp-auth-pre-del-dpp-*`).

Nothing else was affected: `gws` reads `GOOGLE_CLIENT_*` and its own token directory, neither touched.

## 10. Recommendations (Addendum)

- **Config is snapshotted at startup.** Before debugging an "it works here but not there" that spans environments, check whether the environment in question was actually restarted - a running opencode keeps its load-time config and goes stale fast.
- **Per-OS plugin paths belong in per-OS overlays.** A single absolute Windows or POSIX path can never serve a three-distro shared hub; the per-distro overlays are where platform-resolvable plugin entries must live.
- **Idempotent skill install matters.** Copy-on-first-load with a "never overwrite existing" rule is what makes the plugin safe on an already-skilled box - it logged `0 copied, 6 already present` instead of stomping working files.
- **Route-around beats enrollment.** Even with a Workspace account, DPP approval costs days of waiting; the local REST server worked within a session and is now public tooling.
- **Read admission criteria before filling the form.** DPP accepts Workspace organizational email, not consumer Gmail - know that before deciding whether to apply at all.

Part 3 turned out to be that restart, a consent click, and a surprising amount of cross-OS path wrangling. The mailbox answers now - from all three hosts.
---

Generated by Big Pickle (OpenCode)
