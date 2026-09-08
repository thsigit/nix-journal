# From Blobs to Bungalows: Organizing the Homelab Model Zoo and Giving Llama.cpp a Front Door

**Date:** 2026-09-06  
**Author:** Codebot  
**Topic:** llama-cpp, ollama blobs, caddy, litellm, model zoo, nixos

---

## 1. The Grand Plan (or: What Are We Even Doing Here?)

The owner said, quietly, as if it were a small thing: "we are working on llama.cpp in homelab. Module is in /srv/repo/nix-lab/ai/llama-cpp.nix. I want to work with tinyllama model in /srv/ai/models/blob."

Famous last words. What followed was a full afternoon of turning a 22-gigabyte pile of content-addressed sha256 blobs into a proper neighborhood, mirroring it to Windows, and then teaching llama.cpp to serve the whole street through a router, a reverse proxy, and a gateway. You asked for tinyllama. You got a zoo with a front door.

Objective:

1. Move `/srv/ai/models/blobs/sha256-2af3b81862c6be03c769683af18efdadb2c33f60ff32ab6f83e42c043d6c7816` (609M, Q4_0, GGUF) to `/srv/ai/models/tinyllama/tinyllama.gguf` + `tinyllama-cpp.yaml` params.
2. Move `/srv/ai/gguf/models/` to `/srv/ai/models/vibevoice/` for future use.
3. Convert all `/srv/ai/models/blobs/sha256-*` (30 blobs) to `/srv/ai/models/<name>/<name>.gguf` + yaml/params.
4. Mirror the same fashion to `/mnt/c/ai/models/` (Windows, flat 10 ggufs + manifest.json).
5. Wire llama.cpp into LiteLLM, add Caddy `llama.home.arpa`, tune ctx/threads, and enable multi-model router for all 8 local models. Rebuild, verify, chat.

Narrator: it was not just tinyllama.

## 2. Background (or: How We Got a Pile of Blobs)

Homelab `nix-lab` (`nixos-26.05`, rev `714a5f8`) stores AI models under `settings.ai.models = "/srv/ai/models"` (`settings/default.nix:17`). The previous Ollama layout was the classic Docker-registry mimic:

```
/srv/ai/models/
  blobs/
  manifests/registry.ollama.ai/library/
    gemma3n/latest
    mxbai-embed-large/latest
    qwen2.5-coder/7b
    qwen3/4b
    qwen3-vl/4b-instruct
    tinyllama/latest
    translategemma/4b
```

`common/ai/llama-cpp.nix:4` was minimal:

```nix
services.llama-cpp = {
  enable = true;
  host = "127.0.0.1";
  port = 8080;
  modelsDir = defaults.ai.models;
};
```

It started as a router: `llama-server --host 127.0.0.1 --port 8080 --models-dir /srv/ai/models` and logged `Loaded 0 local model presets from /srv/ai/models` / `Available models (0)`. Of course it did - there were no `*.gguf` files in `/srv/ai/models`, only `blobs/sha256-*` without extensions. `head -c 4` on `sha256-2af3...` was `47 47 55 46` (GGUF), but the server was looking for names, not hashes.

`/srv/ai/gguf/models/` held the odd one out: `vibevoice-realtime-0.5B-q8_0.gguf` (1.6G) + `vibevoice-cpp.yaml` (244 bytes).

Windows `/mnt/c/ai/models/` was a different zoo: flat 10 ggufs (`tinyllama.gguf` 609M `sha256-2af3b818...`, `mxbai-embed-large.gguf` 639M `sha256-819c2adf...`, `qwen3-4b.gguf` 2.4G `sha256-3e4cb141...`, plus `deepseek`, `ornith`, `starcoder2`, `nomic`, `gemma-4-E4B` pair) plus `manifest.json` (10 entries).

LiteLLM was NVIDIA-only (`common/ai/litellm/config.yaml:11`, 7 models) and Caddy (`common/web/caddy.nix:21`) generated vhosts from `services.caddy.services` via `mkLANvhost`/`mkTailscalevhost`. PKI (`common/security/pki.nix:22`) auto-added every `lan` Caddy service to the wildcard SAN via `serviceDomains`.

## 3. Problem (or: The Router That Found Nothing)

Layered, like a lasagna you did not order:

1. **Tinyllama was a hash.** The only way to serve it was `sha256-2af3b818...` in `blobs/`.
2. **Vibevoice lived in the wrong suburb.** `/srv/ai/gguf/models/` vs `/srv/ai/models/` - two roots, one truth violated.
3. **All blobs were anonymous.** 30 files, 7 real GGUFs (`38e8dcc3` 7.1G gemma3n, `819c2adf` 639M mxbai, `60e05f21` 4.4G qwen2.5-coder, `3e4cb141` 2.4G qwen3, `16b83be6` 3.1G qwen3-vl, `bdbf939b` 3.1G translategemma, `2af3b818` tinyllama) plus 23 small friends (templates `e0a425`, `af0ddb`, params `fa956`, `cff3`, `f641`, etc.). Some shared (`e0a425` used by gemma3n + translategemma).
4. **Windows was flat.** `/mnt/c/ai/models/*.gguf` with a `manifest.json` at the top - no per-model bungalows.
5. **Llama was a router with no houses.** `--models-dir /srv/ai/models` found 0 models.

## 4. Work Performed (or: The Great Rehousing)

### 4.1 Inventory

SSH into `homelab` (192.168.1.3), `ls -lhR /srv/ai`, `find ... -name *.nix`, `journalctl -u llama-cpp`, `nix eval ...services.llama-cpp` (model:null, modelsDir:/srv/ai/models). Verified GGUF magic, manifest digests:

```bash
head -c 4 /srv/ai/models/blobs/sha256-2af3b818... | od -An -tx1
# 47 47 55 46 03 00 00 00  -> GGUF
cat /srv/ai/models/manifests/registry.ollama.ai/library/tinyllama/latest
# {"digest":"sha256:6331...","layers":[{"digest":"sha256:2af3b818..."},...]}
cat blobs/sha256-fa956...  # {"stop":["<|system|>",...]}
```

Mapped every model:

| Manifest | GGUF blob (size) | Template | Params |
|---|---|---|---|
| tinyllama/latest | 2af3b818 609M Q4_0 | af0ddb 70B | fa956 98B |
| gemma3n/latest | 38e8dcc3 7.1G | e0a425 358B | - |
| mxbai-embed-large/latest | 819c2adf 639M | - | b837 16B |
| qwen2.5-coder/7b | 60e05f21 4.4G | 1e654 1.6K | - |
| qwen3/4b | 3e4cb141 2.4G | 2d54 1.5K | cff3 120B |
| qwen3-vl/4b-instruct | 16b83be6 3.1G | - | f641 42B |
| translategemma/4b | bdbf939b 3.1G | e0a425 358B | 339e 61B |

### 4.2 Tinyllama + Vibevoice

```bash
mkdir -p /srv/ai/models/tinyllama /srv/ai/models/vibevoice
mv /srv/ai/gguf/models/vibevoice-realtime-0.5B-q8_0.gguf /srv/ai/models/vibevoice/
mv /srv/ai/gguf/models/vibevoice-cpp.yaml /srv/ai/models/vibevoice/
cat > /srv/ai/models/tinyllama/tinyllama-cpp.yaml <<YAML
model: tinyllama.gguf
family: llama
type: 1B
system: |
  You are a helpful AI assistant.
template: |
  <|system|>
  {{ .System }}</s>
  <|user|>
  {{ .Prompt }}</s>
  <|assistant|>
params:
  stop: ["<|system|>", "<|user|>", "<|assistant|>", "</s>"]
YAML
mv blobs/sha256-2af3b818... tinyllama/tinyllama.gguf
cp blobs/sha256-af0ddb... tinyllama/template.j2
cp blobs/sha256-c847... tinyllama/system.txt
```

### 4.3 The Other Six (Shared-Blob Trap)

For each remaining model: `cat > <name>/<name>-cpp.yaml`, `mv` the unique GGUF, `cp` the shared small blobs (`e0a425` shared by gemma3n + translategemma, so `mv` would orphan one).

```bash
mv blobs/sha256-38e8dcc3... gemma3n/gemma3n.gguf
cp blobs/sha256-e0a425... gemma3n/template.j2
```

Repeated for `mxbai` (639M), `qwen2.5-coder` (4.4G), `qwen3` (2.4G), `qwen3-vl` (3.1G), `translategemma` (3.1G). `chown -R sigit:users; chmod 644`.

### 4.4 Cleanup

```bash
tar -czf /tmp/ollama-blobs-backup-20260906.tar.gz /srv/ai/models/blobs /srv/ai/models/manifests
rm -rf /srv/ai/models/blobs /srv/ai/models/manifests
find /srv/ai/models -type f | sort
# /srv/ai/models/gemma3n/gemma3n.gguf ... 8 dirs
du -sh /srv/ai/models/* | sort -h
# 609M tinyllama ... 7.1G gemma3n
```

### 4.5 Mirroring to /mnt/c

`/mnt/c/ai/models/` flat 10 ggufs + manifest.json -> per-dir bungalows. Three identical sha reused (`tinyllama` `2af3...`, `mxbai` `819c...`, `qwen3` `3e4cb...`) copied yaml from homelab.

```bash
mkdir -p /mnt/c/ai/models/tinyllama
mv /mnt/c/ai/models/tinyllama.gguf tinyllama/tinyllama.gguf
cp /tmp/tinyllama-cpp.yaml tinyllama/tinyllama-cpp.yaml
# gemma-4-E4B got both Q4_K_M + mmproj in one dir
cp manifest.json manifest.json.bak; rm manifest.json
```

Result: 9 dirs (20G), `find | sort` clean.

### 4.6 Llama.cpp Multi-Router, Caddy, LiteLLM

Final `common/ai/llama-cpp.nix:8`:

```nix
services.caddy.services.llama = { port = 8080; visibility = { lan = true; tailscale = true; }; };
services.llama-cpp = {
  enable = true; host = "127.0.0.1"; port = 8080;
  modelsDir = defaults.ai.models;
  modelsPreset = {
    tinyllama = { model = "${defaults.ai.models}/tinyllama/tinyllama.gguf"; alias = "tinyllama"; ctx-size = "4096"; temp = "0.7"; top-p = "0.9"; jinja = "on"; };
    gemma3n = { ...; ctx-size = "4096"; jinja = "on"; };
    "mxbai-embed-large" = { model = "..."; embedding = "on"; };
    "qwen2.5-coder" = { ...; };
    qwen3 = { ...; temp = "0.6"; top-p = "0.95"; top-k = "20"; };
    "qwen3-vl" = { ...; temp = "1.0"; };
    translategemma = { ...; };
  };
  extraFlags = [ "-c" "4096" "--threads" "4" "--jinja" ];
};
```

`nix derivation show` `llama-models.ini` confirmed 7 sections.

LiteLLM `common/ai/litellm/config.yaml:11` + `/srv/appdata/litellm/config.yaml` added 7 local entries `local/tinyllama` etc via `openai/tinyllama` `api_base: http://127.0.0.1:8080/v1` `api_key: sk-local`.

## 5. Diagnosis

The router (`--models-dir`) expects `*.gguf` or an INI preset in `modelsDir`. Blobs had `sha256-*` without suffix, no preset, so `Loaded 0 cached model presets`.

## 6. Preliminary Assessment

Ollama layout intentionally removed (tar-backup at `/tmp/ollama-blobs-backup-20260906.tar.gz` 18K). Ollama CLI will not find `tinyllama:latest` - tradeoff for llama.cpp single source.

## 7. Solution Summary

| Before | After |
|---|---|
| `blobs/sha256-2af3...` | `tinyllama/tinyllama.gguf` + `tinyllama-cpp.yaml` |
| `/srv/ai/gguf/models/` | `/srv/ai/models/vibevoice/` |
| 30 blobs + manifests | 8 dirs + per-dir yaml/LICENSE/template |
| `/mnt/c/ai/models/*.gguf` flat | `/mnt/c/ai/models/<name>/<name>.gguf` + yaml (9 dirs, 20G) |
| router 0 models | router 7 presets, `c 4096`, `--threads 4` |
| Caddy no llama | `llama.home.arpa` + `llama.basa-komodo.ts.net` |
| LiteLLM NVIDIA-only (7) | LiteLLM NVIDIA (7) + local (7) = 14 |

## 8. Verification Plan

Before rebuild:

```bash
nix eval --json ...services.llama-cpp | jq .modelsPreset.tinyllama.model
nix eval --json ...services.caddy.services.llama
curl http://127.0.0.1:8080/health -> {"status":"ok"}
curl http://127.0.0.1:8080/v1/chat/completions -d '{"model":"tinyllama","messages":[{"role":"user","content":"Hello?"}]}'
# {"choices":[{"message":{"content":"Hello, welcome ... Sarah."}}], "timings":{"predicted_per_second":6.49}}
```

After `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation`:

```bash
systemctl status llama-cpp litellm caddy
curl http://127.0.0.1:8080/v1/models | jq .data[].id  # 7 aliases
curl https://llama.home.arpa/health
curl http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer sk-local" -d '{"model":"local/tinyllama","messages":[{"role":"user","content":"hi"}]}'
```

## 9. Pending Actions

- Run `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` (password required, `AGENTS.md:18`).
- `systemctl restart litellm` if needed (live config hand-edited).
- Verify `llama.home.arpa` cert SAN (`openssl x509 -noout -text | grep DNS`).
- Delete `/tmp/ollama-blobs-backup-20260906.tar.gz` after confirming no fallback.
- Commit `llama-cpp.nix` + `litellm/config.yaml` to `dev` branch.

## 10. Recommendations

1. **Keep per-model bungalows.** The hash farm deduplicates, but you debug with names. Document `cp` vs `mv` for shared blobs (`e0a425`) in `settings.ai.models` README.

2. **Do not add `llama` to `extraDomains`.** `common/security/pki.nix:22` auto-covers active Caddy services via `serviceDomains`. Reserve `extraDomains` for inactive hosts (`darkstat`, `wallabag`). The answer `No need to add to extraDomains` is correct.

3. **Tune with the yaml.** Copy `stop` tokens and `temp/top_p` from `tinyllama-cpp.yaml` into `modelsPreset` - do not invent defaults. `extraFlags -c 4096` matches `n_ctx` 2048 train -> 4096 prod.

4. **Wire once, route everywhere.** LiteLLM `local/*` proxies to `http://127.0.0.1:8080/v1` - add new GGUF by adding one `modelsPreset` block and one `model_list` entry.

Generated by Muse Spark 1.2 Contributor-Free (Meta)
