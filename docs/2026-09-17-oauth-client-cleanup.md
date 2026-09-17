# The OAuth Cleanup (or: One Secret, Two Clients, and the Wrong gcloud Command)

**Date:** 2026-09-17  
**Author:** Codebot  
**Topic:** oauth, google-cloud, secret-rotation, opencode, gws, mcp, security

---

## 1. Objective (or: Close the Books on a Leaked Secret)

Close the security follow-up from the pruning-tasks session: dispose of the leaked Google OAuth client secret (`GOCSPX-*`, redacted in the published post) and remove every trace of the retired Web-application client from the environment, while keeping the Desktop client that the `gws` MCP server depends on.

## 2. Background (or: One Project, Two Clients, Different Destinies)

Project `opencode-auth-160926` (number `732075434195`) held two OAuth clients:

| Client | Type | Status | Used by |
|---|---|---|---|
| `...-gvavkl44tadjf04tck6asecklk7k7d01` | Web application | leaked, unused | retired Gmail MCP remote servers |
| `...-e5ubn9ud1qvk9domlbb75qmuapvaj5qq` | Desktop app | active, not leaked | `gws` plugin (`@dguido/google-workspace-mcp`) |

The leak was the Web client's secret, published in the gmail-mcp part 2 post and caught by GitHub secret scanning. Redaction had removed it from source and gh-pages; rotation remained the open action item. Since the Web client serves nothing anymore (the five official remote MCP servers were deleted when the Developer Preview Program wall turned out to need a Workspace account), outright deletion beat rotation.

## 3. Problem (or: Three Small Obstacles)

1. **The secret also lived in Windows User environment variables.** Redacting the blog was not enough; `GOOGLE_OAUTH_CLIENT_SECRET` was still set at User scope.
2. **`gcloud` kept refusing to delete the client.** Every CLI attempt listed zero items or 404'd, which looked like a permissions problem but was not.
3. **The Desktop client had to survive untouched.** Same project, similar name, one suffix apart - and it feeds the live `gws` integration on all three distros.

## 4. Work Performed

### 4.1 The Secret Inventory (or: Where Does It Live?)

Grepped the nix-lab and nix-journal repos, all journal sources, Linux shell configs, and `mcp-auth.json` (already emptied in the previous session): all clean. Windows held four values at User scope:

| Variable | Belongs to | Action |
|---|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` | Web client (leaked) | removed |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Web client (leaked) | removed |
| `GOOGLE_CLIENT_ID` | Desktop client (active) | kept |
| `GOOGLE_CLIENT_SECRET` | Desktop client (active) | kept |

Machine scope had none of the four.

### 4.2 The Wrong gcloud Command (or: Two Registries, One Name)

`gcloud iam oauth-clients` manages **Workforce Identity Federation** clients - applications that let external identity providers sign in to Google Cloud. The Google Auth Platform clients (the "Sign in with Google" kind, including both of ours) live in a completely separate registry with no gcloud surface here. That is why the command listed zero items and why guessed REST endpoints 404'd: the web client was never visible to that API. The client was deleted manually in Google Cloud Console (Google Auth Platform -> Clients) and the deletion confirmed by the owner.

Lesson: a zero-item CLI list is not evidence that a resource does not exist - check which registry the command actually addresses first.

### 4.3 Environment Variable Removal (or: The null That Had to Be Real)

```powershell
[Environment]::SetEnvironmentVariable('GOOGLE_OAUTH_CLIENT_ID', $null, 'User')
[Environment]::SetEnvironmentVariable('GOOGLE_OAUTH_CLIENT_SECRET', $null, 'User')
```

Two gotchas worth the ink:

1. **Bash interpolates `$null` before PowerShell sees it.** Called from WSL, the variable vanished into an empty argument and PowerShell threw "Missing expression after ','". Escaping as `\$null` fixed it.
2. **An empty string does not delete a User value.** Setting the variable to `''` left both values present in the registry. Only a true null deletes.

Verification read the registry hives directly: `HKCU:\Environment` (User) and the Machine hive both show the two `GOOGLE_OAUTH_*` values absent, the two `GOOGLE_CLIENT_*` values present.

### 4.4 Task Bookkeeping (or: The Paper Trail)

`/mnt/c/users/sigit/.config/opencode/tasks/manage-google-cloud-projects.md` now records the completed cleanup and queues the next piece of work: a read-only review of six inactive Google Cloud projects before any deletion:

- `gen-lang-client-0472219941`
- `bjornbiosystem`
- `gmp-demo-project-992423549`
- `sinuous-client-463315-k3`
- `my-drupal-project-30765`
- `chromium-sync-387713`

An empty duplicate of that task file on the homelab (left by a failed write earlier in the day) was deleted with approval. One side effect was recorded for honesty: this session changed gcloud's default project from `project-57513329-1f0c-4132-be7` to `opencode-auth-160926`; restoring it is queued as a question, not an action.

## 5. Diagnosis (or: Why It Felt Hard)

The failed deletion was a registry mix-up, not a permissions problem. "OAuth client" names two unrelated things in Google's ecosystem, and the CLI command that sounds right addresses the wrong one. Once the two registries were told apart, the remaining work was two PowerShell lines - one of which had to be a real null to stick.

Deletion also beats rotation here: the leaked credential's client no longer exists, so the pruning-tasks action item ("rotate the secret in Google Console") is retired outright rather than merely satisfied.

## 6. Verification Status

| Check | Result |
|---|---|
| `GOCSPX` in journal sources, gh-pages HTML, live journal tree | absent (PASS) |
| `nix-journal` `main` / working tree | `2aa744d`, clean (PASS) |
| gh-pages tip | `d66f896` (PASS) |
| User + Machine hives free of `GOOGLE_OAUTH_*` | PASS |
| Desktop `GOOGLE_CLIENT_*` at User scope | present (PASS) |
| `gws` round-trip after cleanup | NOT YET RUN - old processes may cache retired vars until restart |
| zensical preview watcher (`zensical-build.path`) | enabled and active; auto-builds on docs changes |

## 7. Pending Actions

- Verify `gws` in a fresh session: one tool call suffices; tokens live under `~/.config/google-workspace-mcp/`.
- Read-only review of the six inactive GCP projects listed in 4.4; explicit approval required before any deletion.
- Optionally restore gcloud's default project, or standardize on explicit `--project` flags.

## 8. Recommendations

- **Deletion beats rotation for unused clients.** One Console click retires the secret forever; rotation only mints a new one to protect.
- **Do not trust a zero-item CLI list as evidence of absence.** `gcloud iam oauth-clients` (Workforce Identity Federation) and Google Auth Platform clients are different registries that happen to share a name.
- **Only a true null deletes a Windows User environment variable.** Empty string leaves the value behind, and bash will eat a bare `$null` before PowerShell ever sees it.
- **Keep the two client types documented side by side.** The leaked one and the live one differ by a suffix nobody should have to memorize under pressure.

---

Generated by Union Alpha (OpenCode)
