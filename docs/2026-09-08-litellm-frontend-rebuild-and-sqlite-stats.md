# LiteLLM Frontend Rebuild and SQLite Stats (or: How We Evicted G0DM0D3 and Gave the Gateway a Proper Dashboard)

**Date:** 2026-09-08  
**Author:** Codebot  
**Topic:** litellm, frontend, caddy, sqlite, stats, nix-journal

---

## 1. Objective (or: What Are We Even Doing Here?)

You said: merge pending tasks into two - litellm frontend and ai-gateway frontend. For litellm frontend, discard current work in /srv/www/litellm (move to /srv/repo/litellm-frontend-archive) and create a new one. Keep standard endpoints alive (core /v1/models, /v1/chat/completions, /v1/embeddings etc plus audio/files/images) and the master key. New frontend will use litellm-cli when possible, recreate it if not. For ai-gateway, it's basically open-webui with customization, and move open-webui.home.arpa to chat.home.arpa. Plus a deferred profile task: once ai-gateway is wired, refactor everything into an ai-gateway profile alongside server/workspace/failsafe.

Then: approve archive and audit litellm-cli, plus check if we can disable litellm core web UI but keep endpoints. Then: maybe disable reverse_proxy entirely (no litellm.home.arpa). Then: we still need litellm.home.arpa as gateway for other machines, so what to put in the frontend if no chat and no core litellm? You chose Option A - Gateway Admin Dashboard with sqlite auth via LITELLM_MASTER_KEY. Then: before login providers+health, after login editable providers+health+config.yaml. Then: looks good but no models/providers loading and unable to login (it was /admin.js not whitelisted). Then: can we use sqlite for stats? Yes. Then: write to blog.

Objective for this report: document the rebuild, the Caddy whitelist trap, and the 92K sqlite stats that now lives at /ui/playground/stats.json.

## 2. Background (or: The Stack Before We Touched It)

Homelab `workstation` (`nixos-26.05`, `settings.ai.models=/srv/ai/models`) with:

| Leaf | Port | Via | State |
|---|---|---|---|
| `litellm` | `4000` | `services.litellm` + `services.litellm-cli` (`/srv/appdata/litellm/config.yaml`, `providers.env` sops) | `12` models (7 nvidia + 5 local), `5/13` healthy, `usage.jsonl` 319 rows |
| `llama-cpp` | `8080` | `services.llama-cpp` | `local/*` router |
| `open-webui` | `8081` | `services.open-webui` (`OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`) | `0.9.5` ready for `chat.home.arpa` |
| `caddy` | `80/443` | `common/web/caddy.nix` `mkLANvhost` | `litellm.home.arpa` -> `@frontend path / /litellm.js /ui/playground/*` + `reverse_proxy 127.0.0.1:4000` |

Old frontend at `/srv/www/litellm` was G0DM0D3 HTML/CSS stripped (~4K lines) + `litellm.js` ~740 lines (IIFE, SSE chat) + `/ui/playground/` admin. Task `pending-litellm-frontend-build.md` had grown to include G0DM0D3 rebrand, chat, and endpoint keep-list from `pending-fix-litellm-endpoint.md`.

`litellm-cli` (`/srv/repo/litellm-cli`, pure bash, `litellm-cli models/config/run/stats/debug`) edits the static `config.yaml` directly, never during rebuild.

## 3. Problem (or: Two Frontends, One Gateway, and a Whitelist)

Three questions in one session:

1. **Task merge.** `pending-litellm-frontend-build.md`, `pending-fix-litellm-endpoint.md`, `pending-ai-gateway.md`, `pending-customizing-open-webui.md` overlapped. Need two categories (litellm frontend vs ai-gateway frontend) plus a deferred profile, and old tasks should not pollute `tasks/`.

2. **What lives at `https://litellm.home.arpa/` if chat moves to `chat.home.arpa` and core `/docs` is unwanted?** Keep gateway for LAN clients, but no single-page chat, no core UI. Need a control-plane idea.

3. **Dashboard shows `Gateway Status loading...` forever and login fails with 404 on `/admin.js`.** Also: sqlite - do we need it? If so, for what? You suggested stats.

## 4. Work Performed (or: Four Moves, One Audit, One 92K Database)

### 4.1 Merge Tasks into Two + One Deferred

Rewrote `pending-litellm-frontend-build.md:1` as `LiteLLM Frontend (Rebuild)` with archive step and keep-list (core + extended endpoints, Bearer `sk-@8615269azSX`). Created `pending-ai-gateway-frontend.md:1` (merge of open-webui customization + domain move `open-webui.home.arpa -> chat.home.arpa`) and `pending-ai-gateway-profile.md:1` (deferred, depends on Category 1+2). Superseded three files moved to `tasks/.archive/`:

```
pending-fix-litellm-endpoint.md -> .archive/ (merged into Category 1)
pending-ai-gateway.md -> .archive/ (split into 2+3)
pending-customizing-open-webui.md -> .archive/ (merged into 2)
```

Remaining active:

```
pending-litellm-frontend-build.md (79 lines, Category 1)
pending-ai-gateway-frontend.md (73 lines, Category 2)
pending-ai-gateway-profile.md (59 lines, Category 3)
```

### 4.2 Archive and Rebuild

```bash
ssh homelab "sudo mv /srv/www/litellm /srv/repo/litellm-frontend-archive && sudo mkdir -p /srv/www/litellm && sudo chown sigit:users /srv/www/litellm"
```

Result: `/srv/repo/litellm-frontend-archive` (96K `index.html` 3678 lines, 30K `litellm.js` 868 lines, `ui/playground/`), ` /srv/www/litellm` empty (later 4.6K index + 7.3K js + 2.5K stats.json).

### 4.3 Audit litellm-cli and Research Disabling Core UI

Checked `/srv/repo/litellm-cli/lib/*.sh`:

| Command | Covers | Gap for frontend |
|---|---|---|
| `config list/add/remove/validate` | YAML edit with `--api-base` | needs backend wrapper for web |
| `models [--json]` | parse `config.yaml` | frontend should use live `GET /v1/models` |
| `run [--model]` | `curl POST /v1/chat/completions` + `jq` | no SSE streaming (not needed for dashboard) |
| `debug doctor/status/config` | `health.json` | not needed |
| `stats` | `usage.jsonl` 319 rows | needs DB for dashboard (see 4.6) |

No `--disable-ui` flag in `litellm --help` (checked `/nix/store/.../litellm --help`). UI lives in `/var/lib/litellm/ui` via `LITELLM_UI_PATH`, served by same uvicorn as APIs. Can't disable at binary; can gate at Caddy (`handle @litellmUI path /docs* /openapi.json /litellm-asset-prefix/* -> 404`). Recommendation: keep proxy, block UI paths, keep `/v1/*`, `/health` alive. Disabling `reverse_proxy` entirely would break LAN gateway (still needed for other machines), so rejected.

### 4.4 Choose Option A - Gateway Admin Dashboard

You chose: **A. Admin Dashboard** (not B API Playground nor C Minimal). Auth: single user `sigit`, password = `LITELLM_MASTER_KEY` from `providers.env`, sqlite session (later stats-only). Before login: providers with models + health read-only. After login: editable providers + health + `config.yaml` viewer/editor.

Updated `pending-litellm-frontend-build.md:41` to Option A spec with backend shim `litellm-admin` on `127.0.0.1:8089`, Caddy `handle /api/* -> 8089`, block `/docs`, keep `reverse_proxy 4000` for APIs.

### 4.5 Scaffold Dashboard

Created `/srv/www/litellm/index.html` (4.6K) and `/srv/www/litellm/admin.js` (7.3K -> copied to `litellm.js` for whitelist, see 5). Features:

- Header `Gateway Status` badge (healthy X/Y from `GET /health`), links to `chat.home.arpa`, `llama.home.arpa`, `/health`
- Provider sections grouped `nvidia` vs `local` (from live `GET /v1/models`, 13 models: 7 nvidia + 5 local + 1 filtered), health badge per model
- Login: `fetch('/v1/models', Bearer pw)` test, store `localStorage.litellm_key`, toggle editable (`disable` buttons, `config.yaml` textarea with Reload/Save/Validate)
- Stats card (added 4.6) fetching ` /ui/playground/stats.json`

### 4.6 SQLite for Stats (or: The 92K That Ate jsonl)

You asked: can we use sqlite for stats? Yes - built it.

```bash
# init
sqlite3 /srv/appdata/litellm/admin.db
CREATE TABLE requests(id INTEGER PRIMARY KEY, ts REAL, iso TEXT, model TEXT, model_id TEXT,
  prompt_tokens INT, completion_tokens INT, total_tokens INT, cost REAL);
CREATE INDEX idx_model_ts ON requests(model, ts);
# ingest 319 rows from usage.jsonl (zero tokens, all cost 0 - pre-token logging)
```

Specs: `admin.db` 92K, 319 rows, top models `openai/gpt-oss-20b` 167, `nvidia/nemotron-3-super-120b:free` 38, `openrouter/free` 36. Per-day: `2026-08-31` 224 (peak), `2026-08-30` 37 etc. All `total_tokens=0` (logger predated token capture).

Two daemons (no rebuild, no `/etc/caddy` edit - ` /nix/store` is ro):

- `stats_api.py` on `127.0.0.1:8089` (`GET /api/stats`, `/api/stats/recent`, CORS `*`, auto-ingest new jsonl rows)
- `stats_writer.py` loop every 30s writes `/srv/www/litellm/ui/playground/stats.json` (2.5K, whitelisted via existing `@frontend path /ui/playground/*`)

Frontend now fetches static `/ui/playground/stats.json` (no Caddy change). Verified `curl http://127.0.0.1:8089/api/stats | jq .total` -> 319, `cat /srv/www/litellm/ui/playground/stats.json | jq .per_model[0]` matches.

## 5. Diagnosis (or: Why It Said Loading Forever)

Caddy `litellm.nix:62` whitelist is `@frontend path / /litellm.js /ui/playground/*`. New dashboard used `/admin.js` (7.3K) -> Caddy passed it to `litellm` backend -> `{"detail":"Not Found"}` 404, so no JS executed, hence `Fetching /v1/models...` stuck. Fix without `sudo nixos-rebuild switch` (per rule): copy `admin.js -> litellm.js` (both 7.3K, whitelisted) and change `index.html:80` to `src="/litellm.js"`. Live `/etc/caddy/caddy_config` is symlink to ` /nix/store/.../Caddyfile` (ro, can't patch without rebuild), so static JSON trick avoids needing `handle /api/*` proxy.

Also: `GET /health` and `GET /v1/models` require `Authorization: Bearer` (401 without). Before login, dashboard shows `No models` until key entered - expected. True public read-only without key would need ` /api/public/*` shim, deferred.

## 6. Preliminary Assessment (or: What Actually Works Now)

| Path | Status |
|---|---|
| `https://litellm.home.arpa/` | 200 (4653 bytes, new index) - loads `litellm.js` after hard refresh |
| `https://litellm.home.arpa/litellm.js` | 200 (7.3K, whitelisted) |
| `https://litellm.home.arpa/ui/playground/stats.json` | 200 (2.5K, 319 reqs, whitelisted) |
| `https://litellm.home.arpa/v1/models` | 200 with Bearer, 401 without (12-13 models, 5/13 healthy) |
| `https://litellm.home.arpa/health` | 200 with Bearer |
| `https://litellm.home.arpa/admin.js` | 404 (not whitelisted - now unused) |
| `/srv/appdata/litellm/admin.db` | 92K, ingests jsonl on 30s loop |
| `/srv/repo/litellm-frontend-archive` | preserved old frontend |

LAN gateway still alive for other machines (your requirement). Core UI (`/docs`, `/openapi.json`) still proxied but not linked - will block via Caddy after next rebuild if desired.

## 7. Solution Summary (or: The Current Recipe)

1. Tasks merged, old ones archived to `tasks/.archive/`, new categories define work.
2. Frontend rebuilt as Admin Dashboard (no chat) with `LITELLM_MASTER_KEY` Bearer check, before=read-only providers+health, after=editable+config.
3. SQLite chosen for stats (not sessions): `admin.db` ingests `usage.jsonl`, static JSON served via whitelisted path, dashboard fetches it.

No `nixos-rebuild` needed this session - all via `/srv/www`, `/srv/appdata`, and user daemons.

## 8. Verification Plan (or: How We Know It Didn't Just Pretend)

```bash
# gateway
curl -H "Authorization: Bearer $(grep LITELLM_MASTER_KEY /run/secrets/providers.env | cut -d= -f2)" https://litellm.home.arpa/v1/models | jq '.data[].id' | wc -l # -> 13
curl -H "Authorization: Bearer ..." https://litellm.home.arpa/health | jq '{healthy: (.healthy_endpoints|length)}' # -> 5
# frontend
curl -k https://litellm.home.arpa/ | grep -q "LiteLLM Gateway" && echo ok # -> ok
curl -k https://litellm.home.arpa/litellm.js | head -c 20 # -> async function loadStats
curl -k https://litellm.home.arpa/ui/playground/stats.json | jq .total # -> 319
# db
sqlite3 /srv/appdata/litellm/admin.db 'select count(*) from requests' # -> 319
# browser: hard refresh https://litellm.home.arpa/ -> login with LITELLM_MASTER_KEY -> providers + stats appear, config card after login
```

## 9. Pending Actions (or: Tomorrow's Todo List)

- [ ] Decide public read-only without key: add ` /api/public/*` or keep login-required for models.
- [ ] Implement editable config save: `POST /api/config` -> write `/srv/appdata/litellm/config.yaml` + `systemctl restart litellm` (needs backend, currently stub).
- [ ] Wire provider toggle to `litellm-cli config add/remove` via backend (currently alert stub).
- [ ] Add Caddy block for core UI (`handle @litellmUI -> 404`) and proper `handle /api/* -> 8089` in `litellm.nix:62` - requires owner `nixos-rebuild`.
- [ ] Make `stats_writer` a proper systemd service (currently `nohup bash while` + `stats_api.py` manual).
- [ ] Move `open-webui.home.arpa -> chat.home.arpa` (Category 2) and wire TTS/STT, RAG per `pending-ai-gateway-frontend.md`.
- [ ] Deferred: `pending-ai-gateway-profile.md` refactor once 1+2 stable.

## 10. Recommendations (or: What We'd Tell Future Us)

1. **Keep `litellm.home.arpa` as gateway.** Disabling `reverse_proxy` would hide APIs from LAN - you still need them for other machines. Block UI at Caddy, not by removing gateway.
2. **Whitelist is law.** Caddy `@frontend` is exact-match - new assets must be ` /litellm.js` or ` /ui/playground/*` or wait for rebuild. We learned this the hard way with `/admin.js`.
3. **SQLite for stats is perfect, for sessions maybe overkill.** Single user + `LITELLM_MASTER_KEY` works stateless; sqlite shines for history, aggregations, and `stats.json` without hitting `litellm` each load. Keep it for stats, skip session table unless you want audit.
4. **Don't fight ro `/nix/store`.** Live Caddy config is immutable without rebuild - use whitelisted static paths or direct ports with CORS as workaround until rebuild window.

---

Generated by Muse Spark 1.2 Contributor-Free (Meta)
