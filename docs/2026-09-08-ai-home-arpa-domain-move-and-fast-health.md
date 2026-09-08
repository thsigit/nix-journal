# A Gateway Rename and a Health Check That Finally Keeps Up (or: How ai.home.arpa Was Born)

**Date:** 2026-09-08  
**Author:** Codebot  
**Topic:** litellm, caddy, nix, health checks, domain move

---

## 1. Objective (or: What Are We Even Doing Here?)

One Tuesday, the homelab decided its AI endpoints deserved better street addresses. `litellm.home.arpa` was demoted to a memory, and `ai.home.arpa` took over. Meanwhile `open-webui.home.arpa` retired in favor of `chat.home.arpa`. Per the commit message: `no transition, swift change per 2026-09-08 decision`.

But moving the mailboxes opened the door to two security/UX follow-ups that turned into their own commits across the same afternoon:

1. **Read-only endpoints should not demand a key from a browser.** After the move, a browser pointing at `https://ai.home.arpa/health` or `/v1/models` hit `401` - not because auth broke, but because browsers do not carry `Authorization: Bearer ...` headers in their pocket. Read-only calls on a private LAN should answer without one.
2. **`/health` was slow enough to look dead.** It live-probed every model on every request; local llama.cpp models are not what you would call prompt. Curl gave up at `000` after 20s; a with-key run was aborted past 45s.

Ground rule that survived intact: **local models stay in the gateway** (that is the whole point of the box). They just should not be *probed* by `/health`.

## 2. Background (or: The Stack On the Eve of the Move)

Homelab `workstation` (`nixos-26.05`), Caddy in front of everything:

| Leaf | Port | Via | Old vhost | New vhost |
|---|---|---|---|---|
| `litellm` | `4000` | `services.litellm` + `services.litellm-cli`, config `/srv/appdata/litellm/config.yaml`, `providers.env` (sops) | `litellm.home.arpa` | `ai.home.arpa` |
| `open-webui` | `8081` | `services.open-webui` (`OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`) | `open-webui.home.arpa` | `chat.home.arpa` |
| `admin api` | `8091` | `services.litellm-admin-api` (`admin_api.py`) | - | `ai.home.arpa/api/*` |
| `caddy` | `80/443` | `common/web/caddy.nix` `mkLANvhost` / `mkTailscalevhost` | - | - |

Caddy vhosts are generated from `services.caddy.services.*`; `mkLANvhost` produces the `.home.arpa` host and `mkTailscalevhost` the `.<tailnet>.ts.net` one - so `ai.home.arpa` and `ai.basa-komodo.ts.net` share the same `preConfig`, quirks included.

Two configs live in parallel and must match:

- **Live config**: `/srv/appdata/litellm/config.yaml` - admin-edited, never re-rendered on rebuild.
- **Committed seed**: `/srv/repo/nix-lab/common/ai/litellm/config.yaml`.

At the start they were **103 lines and byte-identical**. `LITELLM_MASTER_KEY=sk-@8615269azSX` lives in `providers.env`.

## 3. Problem (or: Three Landmines in the Aftermath of a Rename)

1. **The dashboard and browser hits went `401`.** The admin API on `:8091` and the general proxy on `:4000` both demand a key. The browser has none to give.
2. **`/health` could not be trusted as a status page.** Default `HEALTH_CHECK_TIMEOUT_SECONDS=60` plus llama.cpp hosting. The dashboard's 5s `AbortController` always fell back to `/api/health` on the admin port.
3. **LiteLLM's native "make some routes public" knob is premium-only.** `general_settings.public_routes` exemption requires `LITELLM_LICENSE` - not in the community build. Key injection had to happen one layer up: at Caddy.

## 4. Work Performed (or: Three Commits, In Order of Heroism)

### 4.1 The Swift Rename, With Sprinkles

`55d2f2a` - `ai: move litellm.home.arpa -> ai.home.arpa, open-webui -> chat, add sqlite stats + admin api`

- `services.caddy.services.litellm` renamed to `services.caddy.services.ai`, static root `/srv/www/litellm` -> `/srv/www/ai`.
- `open-webui.home.arpa` -> `chat.home.arpa` (`services.caddy.services.chat`).
- **Plus, folded in**: sqlite stats (`admin.db`, 319 rows at the time, `stats.json` served via `/ui/playground/*`), the editable-config admin API `admin_api.py` on `:8091`, and new `stats.nix` / `admin.nix` modules. Caddy gained `handle /api/* -> 8091` and a block on `/docs* /openapi.json /litellm-asset-prefix/* /swagger/*` ("Not Found" 404) so the raw LiteLLM UI stays hidden.
- Dashboard at `ai.home.arpa`: providers + health read-only -> editable + config.yaml once logged in.
- 5 files changed, 66 insertions.

### 4.2 Read-Only Routes Go Public

`74f7812` - `ai/litellm: make read-only endpoints public via Caddy master-key injection`

A `@readonly` Caddy matcher lists the read-only paths and injects the key as it proxies, **before** the general `reverse_proxy`:

```
@readonly path /health /health/liveness /health/readiness /health/services /v1/models /models /v1/model/info /model/info
handle @readonly {
    reverse_proxy 127.0.0.1:4000 {
        header_up Authorization "Bearer {env.LITELLM_MASTER_KEY}"
    }
}
```

The key needed to reach Caddy's runtime: `systemd.services.caddy.serviceConfig.EnvironmentFile = [ config.sops.secrets."providers.env".path ]`. Caddy runs as `caddy:caddy`; `providers.env` is `sigit:users 0440` - so only systemd-as-root could read it into Caddy's environment. Without this, `{env.LITELLM_MASTER_KEY}` would resolve to nothing and the injection would be a lie.

Validation before rebuild: `nix eval` rendered `preConfig` correctly, `EnvironmentFile` resolved to `["/run/secrets/providers.env"]`, `nix-instantiate --parse` clean. User rebuilt (`sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation`).

### 4.3 A Health Check That Doesn't Check Everything, All the Time

`40c131e` - `ai/litellm: background health checks, skip local models from probing`

Two config changes (`config.yaml`, 103 -> 118 lines):

- `general_settings.background_health_checks: true` -> `/health` serves **cached** `health_check_results` instead of probing on every request; a background loop refreshes it.
- Per-model `model_info.disable_background_health_check: true` on the 5 local models (`local/tinyllama`, `local/qwen2.5-coder`, `local/qwen3`, `local/mxbai-embed-large`, `local/gemma-4-E4B`) -> the background loop skips them, so `/health` never touches llama.cpp.

Deploy dance (live config is admin-edited, so no rebuild needed for this half):

- Staged as `/tmp/config.yaml.new`, validated on the homelab. Validation itself was a small adventure: system `/usr/bin/python3` has **no `yaml` module**; `nix-shell -p python3` lacked PyYAML too; the **litellm runtime env** at `/nix/store/kag92x4mfgr1r83lnirnw7ax8sqjgcl1-python3-3.13.13-env/bin/python3` bundled it. Result: `YAML OK`, `bg_health: True`, locals still present in `model_list` with `skip: [True, True, True, True, True]`.
- `sudo cp /tmp/config.yaml.new /srv/appdata/litellm/config.yaml`, `sudo systemctl restart litellm` (user-approved per workstyle contract).
- Same content into `common/ai/litellm/config.yaml`; `diff` confirmed seed == live; committed at `40c131e`.

Pre-existing dirty files (`M AGENTS.md`, `D archive/.gitkeep`) were left untouched - only the target file was staged.

## 5. Diagnosis (or: It Was Never the Key, and It Was Never the Models)

- **Browser `401` on read endpoints**: not an auth bug - a missing header. Caddy-side injection was the only viable route in the community build.
- **Slow `/health`**: per-request live probing of slow llama.cpp models. Fix confirmed in the litellm source:
  - `_health_endpoints.py`: with `use_background_health_checks`, `/health` returns cached `health_check_results` instantly.
  - `proxy_server.py` (~line 2571): the background loop skips models with `model_info.disable_background_health_check: true`.

## 6. Solution Summary (or: The Stack After a Busy Tuesday)

| Request, no key | Before | After |
|---|---|---|
| `/health` | `000` curl timeout (20s); aborted 45s with key | **`200` in 0.025s** (cached) |
| `/v1/models`, `/models`, `/model/info`, `/v1/model/info` | `401` | **`200`** |
| `/health/readiness`, `/health/liveliness` | `401` | **`200`** |
| `/api/config` | `401` | **`401`** (still gated - correct) |

- Health state: `healthy_count: 4`, `unhealthy_count: 3` - **no local model** in healthy or unhealthy lists (excluded from probing entirely).
- Models still offered: `12` total, `5` local (unchanged).

## 7. Verification (or: Proof, Not Vibes)

All checks against `https://ai.home.arpa` with NO key via `curl -k --resolve ai.home.arpa:443:127.0.0.1`:

```
/health        -> 200 (time=0.025s)
/v1/models     -> 200
/models        -> 200
/model/info    -> 200
/v1/model/info -> 200
/health/readiness -> 200
/health/liveliness -> 200
/api/config    -> 401
```

`journalctl -u litellm` confirmed all 12 models loaded post-restart and every public endpoint served `200`. The same `preConfig` powers `ai.basa-komodo.ts.net`, so the tailscale host inherits the read-only routes too.

One wrinkle: immediately after restart, `/health` returns `[]` until the first background cycle completes (it runs at startup, then every `health_check_interval`, default 300s). Give it a beat before you alarm the on-call pager.

## 8. Recommendations

1. **Both persistence layers are handled.** `55d2f2a` + `74f7812` (Caddy routing) re-apply on rebuild; `40c131e` (seed config) re-seeds fresh deployments. The live config is admin-edited, so a future `litellm-cli add-provider` will not resurrect `/health` slowness unless it rewrites `general_settings` wholesale.
2. **The 3 "unhealthy" NVIDIA entries** are chronic slow/EOL stragglers predating this session - unrelated. A future pruning pass (see the model zoo posts) can retire them.
3. **`disable_background_health_check` is a scalpel, not a default.** It hides real outages; use it only for genuinely unruly models (our llama.cpp single process qualifies).
4. **Keep the Caddy-level injection for the private LAN.** If this box ever reaches beyond the tailnet, revisit with per-client keys or an auth-token middleware.
5. **Domain renames on one host are cheap when vhosts are data-driven** (`services.caddy.services.*`). The `mkLANvhost`/`mkTailscalevhost` split means one definition, two hostnames - rename once, both follow.

---

Generated by Big Pickle (OpenCode)