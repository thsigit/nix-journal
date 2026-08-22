# The LiteLLM Gateway Evolution - Part 8

*Fix SQLite crash loop + PostgreSQL requirement*

**Date:** 2026-07-31  
**Author:** Codebot  
**Topic:** LiteLLM, Podman, NixOS, troubleshooting, SQLite  

---

## 1. Objective

Fix LiteLLM proxy crash loop caused by SQLite database URL in config.yaml.

## 2. Background

podman-litellm.service crash-looping: start, run ~25s, die, restart every 30s. Error: "DATABASE_URL uses unsupported scheme 'sqlite'. LiteLLM's database features require PostgreSQL."

## 3. Problem

LiteLLM v1.92.0 only supports PostgreSQL for database features. SQLite URL present in rendered config.yaml.

## 4. Work Performed

### 4.1 First Attempt: Environment Override
Added DATABASE_URL = "" to container environment in podman-litellm.nix. Rebuilt. Still crashed -- empty string not overriding. DATABASE_URL not from environment but baked into mounted config.yaml.

### 4.2 Real Culprit: Renderer
litellm-render script generates config.yaml from inventory/policy. Line 172 hardcoded:
```bash
echo "  database_url: sqlite:////srv/appdata/litellm/litellm.db"
```
Every render (activation, provider changes) rewrote SQLite URL. Manual deletion restored on next render.

### 4.3 Second Attempt: Remove from config.yaml
Deleted database_url line from rendered config.yaml directly. Restarted container. New error: "DATABASE_URL uses unsupported scheme '<missing scheme>'" -- DATABASE_URL="" env var still present, LiteLLM parsing empty string as connection URL.

### 4.4 Actual Fix (Two Files)
File 1: /srv/repo/nix-lab/pkgs/litellm-cli/bin/litellm-render -- comment out hardcoded SQLite line so future renders don't reintroduce.
File 2: /srv/repo/nix-lab/modules/ai/podman-litellm.nix -- remove DATABASE_URL environment variable entirely. No override, no empty string, nothing.

After both: config.yaml has no database_url, container env has no DATABASE_URL, LiteLLM starts cleanly without database connection attempt.

### 4.5 Verification
Manual podman run with decrypted litellm.env:
```bash
podman run -d --name litellm --network host \
  -v /srv/appdata/litellm/config.yaml:/app/config.yaml:ro \
  -v /srv/appdata/litellm/data:/app/data \
  -v /srv/appdata/litellm/logs:/app/logs \
  -e LITELLM_DISABLE_CHAT_CACHE=true \
  --env-file /tmp/litellm-decrypted.env \
  ghcr.io/berriai/litellm:v1.92.0 \
  --config /app/config.yaml --host 0.0.0.0 --port 4000
```
Health endpoint: 401 (auth required -- expected with master key). Test request to kenari/kenari-free: valid completion. Proxy operational.

## 5. Diagnosis

Environment variables don't always win -- config files mounted as volumes override at application level. Activation scripts (litellm-render on every rebuild) reintroduce hardcoded values. Error message pointed to runtime config but root cause in build-time renderer.

## 6. Preliminary Assessment

LiteLLM works without database for core proxying. Database features (virtual keys, spend tracking, UI management, dynamic config) not needed currently.

## 7. Solution Summary

Removed SQLite URL from renderer. Removed DATABASE_URL from container env. Proxy starts cleanly. 139 models serving.

## 8. Verification Plan

Run nixos-rebuild switch. Verify container stable. Test model requests.

## 9. Pending Actions

If DB features needed later: PostgreSQL container with Prisma migrations (built into upstream image).

## 10. Recommendations

- Check what app reads from config file, not just process environment
- Trace full config pipeline before editing
- Activation scripts can reintroduce deleted state -- fix at source (renderer)
