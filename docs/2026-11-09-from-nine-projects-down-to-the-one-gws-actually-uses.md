---
nav:
  series: "OAuth Cleanup"
  part: 2
  prev:
    title: "The OAuth Cleanup (or: One Secret, Two Clients, and the Wrong gcloud Command)"
    slug: 2026-09-17-one-secret-two-clients-wrong-gcloud-command
---

# The GCP Project Purge (or: From Nine Projects Down to the One GWS Actually Uses)

**Date:** 2026-11-09  
**Author:** Codebot  
**Topic:** google-cloud, gcp, oauth, gws, mcp, opencode, project-hygiene, cleanup

---

## 1. Objective

Finish the GCP project review that Part 1 queued: determine which Google Cloud projects still matter to the local Google Workspace (GWS) MCP setup, delete the rest with evidence and recovery windows preserved, and leave a single, explainable active project behind.

## 2. Background

Part 1 closed the leaked-secret and wrong-registry cleanup around `opencode-auth-160926` (project `732075434195`) and left a read-only review of six inactive projects for later. The review happened in passes:

| Date | What changed |
|---|---|
| 2026-10-05 | Read-only inventory of 9 projects; 4 deleted (`bjornbiosystem`, `chromium-sync-387713`, `gmp-demo-project-992423549`, `my-drupal-project-30765`), 5 kept. |
| 2026-10-10 | Gemini-project ambiguity resolved; 2 more deleted (`gen-lang-client-0606950119`, `project-57513329-1f0c-4132-be7`); 3 kept. `gws` verified working; billing accounts closed out; default gcloud project/PATH convenience applied. |
| 2026-11-09 | Revisit performed (this report): 3 more deleted; **1 kept**. |

The active GWS integration in use on this host is the local `gws` MCP path tied to the desktop OAuth client in `opencode-auth-160926` ("OpenCode GWS"). `~/.config/opencode/service.json` and `~/.config/google-workspace-mcp/tokens.json` point at that client/project context; token contents are not printed here.

## 3. Problem

The fleet still had ambiguity in two places:

1. **Deferred candidates.** `gen-lang-client-0472219941` ("Gemini Companion") was kept "until we have something better to do with it" (AI Studio API key + dummy app context). `sinuous-client-463315-k3` ("Sinuous Client 44241") was recorded in task notes as backing the `opencode-google-workspace` plugin, but the *current* working GWS MCP setup clearly used `opencode-auth-160926`.
2. **A late arrival.** `opencode-workspace-512515` ("opencode-workspace", created 2026-10-23) appeared during the 2026-11-09 revisit with Workspace/data APIs enabled but no keys, no service accounts, no buckets, and billing disabled - suspiciously named, but not obviously wired to anything.

The question was simple and annoying: which of these are real dependencies, and which are just plausible-sounding ghosts?

## 4. Work Performed

### 4.1 Read-Only Revisit (2026-11-09)

Checked state with `gcloud` (Google Cloud SDK 587.0.0, user-local `~/google-cloud-sdk`, authenticated as `th.sigit@gmail.com`) using explicit `--project` where relevant. Read-only checks covered project lifecycle, billing linkage, enabled APIs, service accounts, API keys, IAM policy summaries, and bucket presence. Cloud Asset API inventory was not enabled on the quota project (a system-state change), so the pass used targeted `gcloud` commands instead of `asset search-all-resources` for the new candidates.

Active projects observed at revisit start:

| Project | Name | Notes |
|---|---|---|
| `gen-lang-client-0472219941` | Gemini Companion | Deferred fate |
| `opencode-auth-160926` | OpenCode GWS | Active GWS OAuth client project |
| `sinuous-client-463315-k3` | Sinuous Client 44241 | Task note said "backs the opencode-google-workspace plugin" |
| `opencode-workspace-512515` | opencode-workspace | New/observed, created 2026-10-23 |

### 4.2 Candidate: `gen-lang-client-0472219941`

Pre-delete inventory (metadata only, no secret values):

- `ACTIVE`, billing disabled, no buckets found.
- Enabled APIs: `generativelanguage.googleapis.com`, `privilegedaccessmanager.googleapis.com`.
- 1 service account for the Gemini API key ("Gemini Companion Test"), system-managed keys only.
- 1 API key resource "Gemini Companion Test" (created 2026-06-28), restricted to Generative Language API.
- IAM: owner = `th.sigit@gmail.com`.

Decision: **delete** (user-approved). Snapshot saved locally and on homelab under `gcp-review-deleted/gen-lang-client-0472219941_2026-11-09/`, then:

```bash
gcloud projects delete gen-lang-client-0472219941 --quiet
```

Result: `DELETE_REQUESTED` (recoverable ~30 days via `gcloud projects undelete gen-lang-client-0472219941`).

### 4.3 Candidate: `opencode-workspace-512515`

Investigation showed:

- `ACTIVE`, created 2026-10-23, billing disabled, 0 buckets, 0 service accounts, 0 API keys.
- Enabled APIs included Gmail/Drive/Docs/Sheets/Slides/Calendar/People plus BigQuery/Dataform/Dataplex/Datastore/Storage/Logging/Monitoring/Telemetry, etc. (30 APIs) - a Workspace/data-shaped footprint with no visible credentials or data.
- No local or homelab opencode-config consumer found by project ID/number in the checks performed.

Decision: **delete as dangling** (user-approved). Snapshot saved under `gcp-review-deleted/opencode-workspace-512515_2026-11-09/`, then deleted to `DELETE_REQUESTED` (recoverable ~30 days).

### 4.4 Candidate: `sinuous-client-463315-k3`

This was the "maybe replaced by `opencode-auth-160926`?" question. Evidence gathered:

- Current local GWS MCP config references `opencode-auth-160926` / client `732075434195-...` (`~/.config/opencode/service.json`, `~/.config/google-workspace-mcp/tokens.json` context). No references to `sinuous-client-463315-k3` / `740515272895` in local `~/.config` (except gcloud logs) or `homelab:/home/sigit/.config/opencode`.
- Current project state: `ACTIVE`, billing disabled, 0 buckets, 0 service accounts, 1 **unrestricted** API key "API key 1" (created 2025-06-18).
- Enabled APIs (21) included `drive.googleapis.com`, BigQuery/Dataform/Dataplex/Datastore/Storage/Logging/Monitoring/Service Usage - notably **no** Gmail/Docs/Sheets/Slides/Calendar/People APIs.
- The old task note said it "backs the opencode-google-workspace plugin"; nix-journal only listed it earlier as an inactive project to review, not as the active GWS OAuth project.

Decision: **delete as replaced/dangling** (user-approved), with the caveat that no-config-found is strong evidence, not omniscience. Snapshot saved under `gcp-review-deleted/sinuous-client-463315-k3_2026-11-09/`, then deleted to `DELETE_REQUESTED` (recoverable ~30 days).

### 4.5 Previously Deleted Projects

The 2026-11-09 revisit also checked the six earlier deletions:

| Project | Deleted | 2026-11-09 state |
|---|---|---|
| `bjornbiosystem` | 2026-10-05 | still `DELETE_REQUESTED` |
| `chromium-sync-387713` | 2026-10-05 | describe returned no permission / may not exist (consistent with permanent purge) |
| `gmp-demo-project-992423549` | 2026-10-05 | same |
| `my-drupal-project-30765` | 2026-10-05 | same |
| `gen-lang-client-0606950119` | 2026-10-10 | still `DELETE_REQUESTED` |
| `project-57513329-1f0c-4132-be7` | 2026-10-10 | still `DELETE_REQUESTED` |

No action taken: the remaining `DELETE_REQUESTED` projects were left for GCP to purge after the recovery window.

### 4.6 Organization and Billing

- `th-sigit-org` (`507838925733`, `ACTIVE`): no `directoryCustomer` shown in `describe`; `gcloud organizations` has no `delete`. Kept.
- Billing accounts `013971-06F891-1CD49B` and `01D5BD-5D66B6-F14E9C`: both still closed. Closed billing accounts cannot be reopened.

## 5. Diagnosis

The "two projects for one GWS setup" confusion came from historical layering, not from the current runtime:

- **`opencode-auth-160926`** owns the active GWS OAuth client and is the project the live local `gws` MCP path actually uses. Keep it.
- **`sinuous-client-463315-k3`** looked important in older task notes ("backs the opencode-google-workspace plugin"), but its current API footprint, unrestricted stale API key, and absence from current configs made it look like a retired predecessor. Deleting it was reasonable *after* a snapshot and explicit approval, with the 30-day undelete window as a safety net.
- **`opencode-workspace-512515`** had the right name and the right APIs but none of the wiring. Naming is not dependency.

The durable lesson is the same one Part 1 taught in a different costume: do not confuse a plausible registry entry with a live dependency. Check which thing the current config actually points at, capture evidence before deletion, and keep a recovery path.

## 6. Verification Status

| Check | Result |
|---|---|
| 2026-11-09 read-only revisit completed (`gcloud` describe/services/SA/keys/IAM/billing/buckets where applicable) | PASS |
| `gen-lang-client-0472219941` pre-delete snapshot + delete | PASS (`DELETE_REQUESTED`, snapshots local + homelab) |
| `opencode-workspace-512515` pre-delete snapshot + delete | PASS (`DELETE_REQUESTED`, snapshots local + homelab) |
| `sinuous-client-463315-k3` pre-delete snapshot + delete | PASS (`DELETE_REQUESTED`, snapshots local + homelab) |
| No `sinuous-client-463315-k3` / `740515272895` refs in local `~/.config` (excluding gcloud logs) or `homelab:/home/sigit/.config/opencode` | PASS |
| `opencode-auth-160926` kept intact as active GWS OAuth project | PASS |
| `gws` live round-trip re-verified after these deletions | NOT YET RUN |
| `th-sigit-org` rechecked (no `directoryCustomer` shown) and kept | PASS |
| Billing accounts still closed | PASS |

## 7. Solution Summary

- Deleted 3 projects on 2026-11-09 with explicit user approval and pre-delete snapshots: `gen-lang-client-0472219941`, `opencode-workspace-512515`, `sinuous-client-463315-k3`.
- Kept 1 active project: `opencode-auth-160926` ("OpenCode GWS"), the OAuth client project used by the current GWS MCP setup.
- Left 3 older `DELETE_REQUESTED` projects alone for GCP to purge; treated 3 others as already purged based on describe behavior.
- Kept `th-sigit-org`; left both billing accounts closed.

## 8. Pending Actions

- Run a fresh `gws` round-trip (one lightweight tool call) to confirm the current Workspace MCP path still works after deleting `sinuous-client-463315-k3`.
- Recheck the 3 still-`DELETE_REQUESTED` projects later if a clean "purged" audit record matters; no user action required for normal purge.
- If a future App Engine/dummy-site task needs billing, create a **new** billing account (closed accounts cannot be reopened) and keep it isolated from `opencode-auth-160926`.

## 9. Recommendations

- **Snapshot before delete, every time.** `DELETE_REQUESTED` buys ~30 days, but durable local+homelab inventories buy clarity.
- **Prove the consumer, not the story.** A task note saying a project "backs the plugin" is a hint; the config/token/client ID that is actually in use is the evidence.
- **Names lie politely.** `opencode-workspace` sounded relevant; it had no keys, no service accounts, and no confirmed consumer.
- **Keep the GWS OAuth project boring.** `opencode-auth-160926` should hold only the credentials/integration identity the GWS MCP needs. Unrelated experiments belong elsewhere - or, better, nowhere.

---

Generated with MiniMax-M2.7 by OpenCode
