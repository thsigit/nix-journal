# Gmail MCP, Wired From Scratch (or: How I Authored an OAuth Flow Because the Official One Wouldn't Write a File)

**Date:** 2026-09-16  
**Author:** Codebot  
**Topic:** gmail, mcp, oauth, opencode, pkce, google-cloud, skills

---

## 1. Objective (or: Give Me Search Help, Officially)

The Codex gmail plugin sitting in `.codex/.tmp/plugins` was a mirage: a folder full of skill docs that called tools (`search_emails`, `read_email_thread`) living only inside Codex's proprietary app-connector runtime. OpenCode could never inherit them. The real goal this session: give opencode a genuine, first-party path into Gmail by wiring Google's official Gmail MCP server, then adapt those orphaned skill docs to the tools that actually exist.

Path chosen: Google's hosted remote MCP endpoint, `https://gmailmcp.googleapis.com/mcp/v1`, authenticated with OAuth 2.0 against a Web-application client created for this purpose.

## 2. Background (or: The MCP That Google Rent Out)

The Gmail MCP server is part of Google Workspace's Developer Preview: a remote, Streamable-HTTP MCP server that lets an agent search threads, read messages, list labels, create drafts, and label messages - all under the user's own OAuth session and permissions. It is deliberately draft-only on the write side (there is no `send` tool; you stage and you review). The official tool list, straight from the reference:

| Tool | Purpose |
| --- | --- |
| `search_threads` | Mailbox search with Gmail query syntax |
| `get_thread` | Full thread contents (supports PLAIN_TEXT or FULL_CONTENT) |
| `get_message` | A single message by ID |
| `list_drafts` / `get_draft` | Drafts list / single draft |
| `list_labels` | All system + user labels |
| `create_draft` | Stage a new email (never sends) |
| `label_thread` / `unlabel_thread` | Apply / remove thread labels |
| `label_message` / `unlabel_message` | Apply / remove per-message labels |

OpenCode already models remote MCP servers natively - `type: "remote"` plus an optional `oauth` block with `clientId`, `clientSecret`, `scope`, and (crucially for Google) a pre-registered `redirectUri`. The hardcoded callback is `http://127.0.0.1:19876/mcp/oauth/callback`, and the loopback happens to be an *allowed* redirect for Google OAuth clients. So the wiring was theoretically a config block plus a consent click. Theoretically.

## 3. Problem (or: Authentication Successful! But Also, Not)

Three stubborn obstacles stood between me and a healthy connection:

1. **opencode's own `mcp auth` command claimed victory and stored nothing.** Run it, watch the spinner, get "Authentication successful!", then `cat mcp-auth.json` -> `{ "gmail": {} }`. An empty entry. The token exchange either silently failed or the token got clobbered by a concurrently-running session holding a stale in-memory copy of the auth file. "Successful" is doing a lot of work in that sentence.
2. **The Google block screen.** First consent attempt greeted us with "Access blocked: Gmail MCP Server has not completed the Google verification process." Developer Preview means unverified OAuth app, which Google routes through the test-user wall until you let yourself through.
3. **No refresh token, ever.** The first hand-rolled exchange returned `access_type: online` - a token that expires in ~1 hour and cannot renew. Fine for a demo, useless for a mail assistant.

## 4. Work Performed

### 4.1 The Config (or: Env Vars Do the Heavy Lifting)

Added the server to the hub `opencode.json` (the shared, three-distro configuration), with credentials referenced via env-var placeholders so no secret ever lands in the config file:

```json
"gmail": {
  "type": "remote",
  "url": "https://gmailmcp.googleapis.com/mcp/v1",
  "oauth": {
    "clientId": "{env:GOOGLE_OAUTH_CLIENT_ID}",
    "clientSecret": "{env:GOOGLE_OAUTH_CLIENT_SECRET}",
    "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose",
    "redirectUri": "http://127.0.0.1:19876/mcp/oauth/callback",
    "callbackPort": 19876
  }
}
```

### 4.2 The Google Cloud Client (or: A Web-Application Client With One Job)

- Project: `opencode-auth-160926`, client ID `732075434195-gvavkl44tadjf04tck6asecklk7k7d01.apps.googleusercontent.com` (the ID is public; the secret stayed out of every command line and every file).
- Application type: **Web application**.
- Authorized redirect URI: `http://127.0.0.1:19876/mcp/oauth/callback`.
- Consent screen scopes: `gmail.readonly`, `gmail.compose`. Because the Gmail MCP server is a Developer Preview, the account had to be added under Google Auth Platform -> Audience -> Test users before the consent screen would let an actual human click Allow.

### 4.3 First Attempt With the Official Command (or: Trust, Then Verify)

`opencode mcp auth gmail` produced a textbook OAuth turn: browser, consent screen, redirect, callback. And a `mcp-auth.json` that read exactly `{ "gmail": {} }`. `opencode mcp debug gmail` said "not authenticated" while simultaneously returning HTTP 200 and the server's badge (`StatelessServer`, `ESF`). The endpoint was reachable; the token just wasn't there. The command walks you to the door and does not, in fact, hand you the key.

### 4.4 The Manual PKCE Script (or: Fine, I'll Do It [the Nickname of a D.I.Y. OAuth Flow])

Wrote `gmail_oauth.ps1`: generate a PKCE verifier/challenge, build the authorization URL, open the browser, run a `HttpListener` on the callback port, grab the `code`, exchange it with `oauth2.googleapis.com/token`, and write `mcp-auth.json` directly. No opencode subprocess, no in-memory state to race with, no "trust me, it worked" UI.

The first run exposed the missing refresh-token plot twist: `tokeninfo` reported `access_type: online`. Google only issues a refresh token when the URL asks for it. Fix: add `access_type=offline` and `prompt=consent` to the authorize request, and the second round came back with a refresh token in hand.

## 5. Diagnosis (or: Three Culprits, One Is OAuth, Two Are Process Sociology)

| Symptom | Culprit | Confirm |
| --- | --- | --- |
| `mcp auth` said success, file stayed empty | Subprocess wrote nothing durable, or a running session clobbered the file with its stale `{}` snapshot. Open question: which one. | `mcp-auth.json` = `{ "gmail": {} }` after the command |
| Consent screen blocked | Unverified Developer Preview app, external user type | Google error page verbatim |
| Token expired / no renew | `access_type=online` (no offline access requested) | `tokeninfo` -> `access_type: online` |

The final, healthy credential block after the manual script:

```json
"tokens": {
  "accessToken": "<redacted>",
  "refreshToken": "<redacted>",
  "expiresAt": 1789551532,
  "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose"
},
"clientInfo": { "clientId": "...", "clientSecret": "<redacted>" },
"serverUrl": "https://gmailmcp.googleapis.com/mcp/v1"
```

`opencode mcp debug gmail` now reports `Auth status: authenticated`, access token valid, refresh token present. `opencode mcp list` shows both servers healthy: `mem0 connected` and `gmail connected (OAuth)`.

## 6. The Skill Adaptation (or: Same Papers, Different Tools)

The codex plugin's two skills were salvaged and remapped to Google's real tool names - no `search_emails` here, but `gmail_search_threads` will do the same job with better legs:

| Codex-era tool | Google MCP now |
| --- | --- |
| `search_emails` | `gmail_search_threads` (Gmail query syntax) |
| `read_email_thread` / `batch_read_email` | `gmail_get_thread` (PLAIN_TEXT) |
| `search_email_ids` | drop; `gmail_search_threads` covers it |
| label actions | `gmail_label_thread`, `gmail_label_message` |
| drafts | `gmail_create_draft` |

Delivered as `~/.config/opencode/skills/gmail/SKILL.md` (core: search, read, draft, label, Codex->Google mapping table) and `gmail-inbox-triage/SKILL.md` (Urgent / Needs reply soon / Waiting / FYI buckets). Both enforce the review-before-send discipline that matches the server's draft-only nature.

## 7. Cross-Host Parity (or: One Config, Three Keyrings)

The config lives in the hub file shared by FedoraWSL, DebianWSL, and native Windows. The OAuth client env vars now exist on all three:

| Host | Mechanism | State |
| --- | --- | --- |
| Windows (native) | User env vars via `[Environment]::SetEnvironmentVariable` | set |
| FedoraLinux-44 | `export GOOGLE_OAUTH_*` appended to `~/.bashrc` | set |
| Debian | `export GOOGLE_OAUTH_*` appended to `~/.bashrc` | set |

Caveat recorded for later: the env vars get the client in the door, but each host still needs its **own** token file in `~/.local/share/opencode/mcp-auth.json`. Credentials without tokens is admittance with no badge.

## 8. Verification Status

| Check | Result |
| --- | --- |
| `opencode mcp list` | 2/2 connected; `gmail connected (OAuth)` |
| `opencode mcp debug gmail` | Auth status: authenticated; access token valid, refresh token present |
| `tokeninfo` round-trip | scopes `gmail.readonly` + `gmail.compose`, `access_type: offline` |
| Hub config JSON | valid (`ConvertFrom-Json` passes) |
| Backup | `opencode-hub-gmail-mcp-migration-20260916-190847.json` in the tray (append-only) |
| Skills | `gmail` + `gmail-inbox-triage` in `~/.config/opencode/skills/` |
| Downloads cleanup | `client_secret*.json` kept (user needs later); throwaway helpers removed |

## 9. Pending Actions

- Confirm the gmail tools load and answer in a fresh opencode session (the session in which the skills are authored predates the config; a restart registers the MCP tools).
- Optionally copy `mcp-auth.json` from Windows into each Linux distro to skip per-host OAuth, or run the consent flow on each host.
- If a future `401` shows up from a gmail tool, re-run the manual script (or `opencode mcp auth gmail` in a tab with **no** other session running) - the refresh token should make this rare.

## 10. Recommendations

- **Don't trust an OAuth CLI's "successful" with tokens you can't see.** `cat` the artifact (`mcp-auth.json`) before closing the ticket.
- **`access_type=offline` is not optional** for any mail server you plan to use tomorrow. Without it, Google hands you a one-hour party favor instead of a key.
- **Test user first.** Any Google "unverified" OAuth integration blocks at the consent screen until the account is whitelisted (Audience -> Test users). Doing it up front saves a full blocked-page detour.
- **Env-var placeholders for client creds** (`{env:GOOGLE_OAUTH_CLIENT_ID}`) keep secrets out of config; the token file is the only credential-bearing artifact and it can be copied or re-flown per host.
- **Keep the manual script.** `gmail_oauth.ps1` is the emergency re-auth path when the official command goes coy again.

Gmail MCP: connected, authenticated, refreshable, and documented in two skills. The mailbox calls, and this time the agent can call back.

---

Generated by Big Pickle (OpenCode)