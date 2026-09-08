# Open WebUI, Whisper, and the Quest for Offline Vision (or: How We Stopped Trusting DNS)

**Date:** 2026-09-07  
**Author:** Codebot  
**Topic:** open-webui, whisper, llama-cpp, litellm, caddy, vision, gemma

---

## 1. Objective (or: What Are We Even Doing Here?)

You said go to homelab and add nixpkgs open-webui to our /common/ai stack. Then you tried to fetch models from litellm.home.arpa (from your 192.168.1.105 laptop), hit 401, switched to http://127.0.0.1:4000/v1 and it worked great. Then you asked the two questions that always follow a working gateway: what can I do with open-webui, can I use llama-cpp here too, and do we have audio/vision with litellm or do we fetch another gguf?

We did. By the end we had open-webui 0.9.5 on 8081, whisper.cpp on 8090, a local 3B vision (qwen2.5-vl-3b via hf), and then your 5.9G gemma-4-E4B (Q4_K_M + 945M mmproj) from /mnt/c/ai/models as a supplement to qwen2.5-vl-3b - offline vs Nvidia 11B. You rebuilt twice, we chased a ghost generation, and finally litellm showed 13 models. Then we tested: gemma vision worked (0.72 tok/s), qwen vision hit 600s timeout twice and was removed (0ba2128) - now 12 models, 5 presets, whisper ready.

Objective for this report: document the stack as of 0ba2128, the DNS 443 trap, the qwen3-vl OOM history, the gemma copy, and why qwen was pruned.

## 2. Background (or: The Stack Before We Touched It)

Homelab `nixos-26.05` `714a5f8` (`portege-r30c`, 15Gi RAM, CPU-only) `settings.ai.models="/srv/ai/models"` (`settings/default.nix:17`). `common/ai/default.nix:8` is a pure importer, leaves self-enable.

Pre-touch:

| Leaf | Port | Via | Models |
|---|---|---|---|
| `litellm` | `4000` | `services.litellm` + `services.litellm-cli` (`/srv/appdata/litellm/config.yaml`, `providers.env` sops) | `11` (7 nvidia text/vision/embed/translate + 4 local) |
| `llama-cpp` | `8080` | `services.llama-cpp` (`b9190` `b64739e`) + `services.caddy.services.llama` | `4` (`tinyllama 609M`, `qwen3 2.4G`, `qwen2.5-coder 4.4G`, `mxbai-embed-large 639M` `embedding=on`) |
| `opencode` | `3000` | `systemd.services.opencode` | - |
| `caddy` | `80/443` | `services.caddy` (`common/web/caddy.nix:21` `mkLANvhost/mkTailscalevhost`) + `common/security/pki.nix:22` SAN | `*.home.arpa` + `*.basa-komodo.ts.net` |

`whisper`, `open-webui`, local vision were missing. `qwen3-vl`, `gemma3n`, `translategemma` had been pruned after `2026-09-06-the-zoo-after-dark` (7 -> 4) due to `failed to fit params` OOM on `b9190`.

## 3. Problem (or: DNS, 401, and a 5.9G Guest)

Three small dramas:

1. **litellm.home.arpa:443 from open-webui sandboxed.** You configured Open WebUI `OPENAI_API_BASE_URL=https://litellm.home.arpa/v1` and got `aiohttp.client_exceptions.ClientConnectorDNSError: Cannot connect to host litellm.home.arpa:443 ssl:default [Timeout while contacting DNS servers]` (`open-webui.service:1268` `09:13:11` `GET /openai/models/0 500`). `DynamicUser=true` `PrivateUsers=true` + `ProtectSystem=strict` sandboxes cannot resolve `*.home.arpa` via `systemd-resolved` to `192.168.1.3`.

2. **401 without key.** `curl http://127.0.0.1:4000/v1/models` without `Authorization: Bearer sk-@8615269azSX` (`LITELLM_MASTER_KEY` in `/run/secrets/providers.env`) returns `{"error":{"message":"Authentication Error, No api key passed in."..."code":"401"}}` (`litellm:1208` `auth_exception_handler.py:95`). With key returns `11` then `13` then `12`.

3. **Gemma-4-E4B lives on Windows.** `/mnt/c/ai/models/gemma-4-E4B` (`gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf 5.0G` + `mmproj-f16 945M` `family gemma3` in `gemma-4-E4B-cpp.yaml:1`) is not on homelab `/srv/ai/models`. Homelab `b9190` supports `gemma3` vision but `qwen3-vl` previously OOMed (`failed to fit params to free device memory` for `3.1G` + `kv`), so 5.9G is tight.

Also: `curl http://127.0.0.1:4000/v1/models | grep qwen2.5-vl` without `-s` hid JSON behind curl progress meter (`100 1105`). And later `qwen2.5-vl-3b` vision timed out after 600s (`pull/22907`) while `gemma` succeeded.

## 4. Work Performed (or: Four Commits, Two Restarts, One rsync, One Prune)

### 4.1 Open WebUI 0.9.5 on 8081 (b7f1566)

Created `common/ai/open-webui.nix:1` (41 lines):

```nix
let port = 8081; in {
  services.caddy.services.open-webui = { inherit port; visibility = { lan = true; tailscale = true; }; };
  services.open-webui = {
    enable = true; host = "127.0.0.1"; port = port;
    environment = {
      SCARF_NO_ANALYTICS = "True"; DO_NOT_TRACK = "True"; ANONYMIZED_TELEMETRY = "False";
      OPENAI_API_BASE_URL = "http://127.0.0.1:4000/v1";
      WEBUI_NAME = "Homelab"; WEBUI_URL = "http://127.0.0.1:${toString port}";
      DEFAULT_USER_ROLE = "admin"; ENABLE_SIGNUP = "True"; ENABLE_COMMUNITY_SHARING = "False";
    };
  };
  systemd.services.open-webui.after = [ "litellm.service" "network.target" ];
}
```

Wired in `common/ai/default.nix:10`, allowed unfree `open-webui` in `system/default.nix:16` + `profiles/workstation/default.nix:23` (`nixpkgs.config.allowUnfreePredicate` `["google-chrome" "open-webui"]`). `nix flake lock --update-input litellm-cli` bumped `1788320348 xHmt` -> `1788711251 aTZf` to fix `NAR hash mismatch`. `nix eval ...services.open-webui.port` `8081`, `dry-run` ok, committed `b7f1566`.

### 4.2 Whisper.cpp on 8090 (aa6562b)

Created `common/ai/whisper.nix:1` (58 lines): `services.caddy.services.whisper` `8090` -> `whisper.home.arpa`, `systemd.services.whisper` `whisper-server --host 127.0.0.1 --port 8090 --model /srv/ai/models/whisper/ggml-base.bin --convert`, `User sigit`, `path [ ffmpeg ]`, `system.activationScripts.whisper-model` auto-downloads `ggml-base` (~142M) via `whisper-cpp-download-ggml-model base` to `defaults.ai.models/whisper`, `tmpfiles d /srv/ai/models/whisper 0755`. Wired in `common/ai/default.nix:11`, `dry-run` ok, committed `aa6562b`.

### 4.3 Local 3B Vision qwen2.5-vl-3b (59c04ef) and Gemma Supplement (219de1a)

Edited `common/ai/llama-cpp.nix:22` (3-chat+1-embed -> +1-vision): added `qwen2.5-vl-3b` via `hf-repo="unsloth/Qwen2.5-VL-3B-Instruct-GGUF"` `hf-file="Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf"` (`~1.9G` + `mmproj-F16` auto) `alias qwen2.5-vl-3b` `jinja on`. Then `rsync -avh --progress /mnt/c/ai/models/gemma-4-E4B/ homelab:/srv/ai/models/gemma-4-E4B/` (`6.33G` at `77.63M/s`) and added `gemma-4-E4B` (`model Q4_K_M 5.0G` + `mmproj f16 945M`, `alias gemma-4-E4B`) alongside (6 presets `3-chat+1-embed+2-vision`). Edited `common/ai/litellm/config.yaml:75` added `local/qwen2.5-vl-3b` + `local/gemma-4-E4B`, synced runtime, committed `59c04ef` + `219de1a`.

You asked about `mmproj`: it's the vision projector (clip encoder -> LLM, 945M for gemma, 1.6G for qwen). `hf` auto-downloads it; local needs explicit `mmproj = ...`.

### 4.4 Have It Ready (5551bab, 8322694)

You: `can we not cache it but have it ready?` for `qwen` `mmproj`. Downloaded `mmproj-F16.gguf` (`1.6G`, `980`->`1338428256` via `huggingface` `cdn.hf.co`, `GGUF clip 519 tensors`) to `/srv/ai/models/qwen2.5-vl-3b/` (`wget -c`, `1.6G`), wired `mmproj = "${defaults.ai.models}/qwen2.5-vl-3b/mmproj-F16.gguf"` in `common/ai/llama-cpp.nix:26` (`5551bab`). Then `yes, and download model first` -> fetched `Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf` `1.8G` (`1929901408`, `5m21s` `5.73 MB/s`) to same dir, switched `hf-repo/hf-file` -> explicit `model = .../Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf` (`8322694`, fully offline `3.4G`).

### 4.5 The Ghost Generation and the Test

You ran `sudo nixos-rebuild switch` twice, got `Done. The new configuration is /nix/store/dzh4lvk0phg339ymzf9yb798aby0aq1b` but `list-generations` stayed `234 09:48:18`. Manual `systemctl restart llama-cpp:13107` + `litellm:13173` showed `6` and `13`. After `gemma` copy, `qwen` vision hit `Failed to read connection` `should_stop condition (adjust the --timeout ... pull/22907)` at `21:24:08` and `21:50:57` (600s timeout), `gemma` at `21:52:58` succeeded (`peg-gemma4` `115` tokens `1.62 tok/s`). Prompt had `40` tokens, `1.408 MiB` cache.

### 4.6 Prune qwen (0ba2128)

You: `no. remove qwen vision and its settings/configuration/models/dir`. Removed `qwen2.5-vl-3b` from `common/ai/llama-cpp.nix:22` (`6`->`5` presets), `litellm/config.yaml:75` (`13`->`12`), `rm -rf /srv/ai/models/qwen2.5-vl-3b` (`3.4G`), synced runtime, committed `0ba2128`.

## 5. Diagnosis

The 443 DNS trap is sandboxing, not Caddy. `open-webui` `DynamicUser` cannot resolve `*.home.arpa` to `192.168.1.3`; `127.0.0.1:4000` bypasses.

`qwen3-vl` OOM history (`failed to fit params` for `3.1G` on `15Gi` with `4.4G`+`2.4G` loaded) explains pruning to `4`, but `qwen2.5-vl-3b` `1.9G` should fit - it timed out instead. `qwen` `1.17 tok/s` text vs `gemma` `0.72 tok/s` (`b9190` `4` threads) - `qwen` faster text, but vision `mmproj` encode + `hf` cache + `600s` default hit `pull/22907` `should_stop`. `gemma` `mmproj 945M` is local and succeeded.

Ghost generation: `nixos-rebuild` built `dzh4...` (cached `714a5f8` `9190`) and reported success, but `llama-models.ini` `zr1hf2p...` didn't change until manual `restart` pulled already-built new preset. Toplevel hash collision from `writeText` caching - open question.

## 6. Preliminary Assessment

As of `20:36:50` `llama-cpp:36292` and `13173` after prune:

| Service | Port | Preset / Models | Caddy |
|---|---|---|---|
| `llama-cpp` | `8080` | `5` (`tinyllama`, `qwen3`, `qwen2.5-coder`, `mxbai-embed-large`, `gemma-4-E4B` 5.0G) | `llama.home.arpa` |
| `whisper` | `8090` | `whisper-server --model ggml-base.bin --convert` | `whisper.home.arpa` |
| `open-webui` | `8081` | `0.9.5` `OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1` | `open-webui.home.arpa` |
| `litellm` | `4000` | `12` (`7 nvidia` + `5 local` includes `gemma-4-E4B`, no `qwen2.5-vl-3b`) | `litellm.home.arpa` |

Benchmarks (`local/qwen2.5-vl-3b` before prune, `local/gemma-4-E4B` after):

| Model | Prompt | Prompt tok/s | Predicted tok/s | Total |
|---|---|---|---|---|
| `qwen2.5-vl-3b` text `2+2` | `33` `7429ms` | `4.44` | `8` `6796ms` `1.17` | `6.7s` |
| `gemma-4-E4B` text `2+2` | `30` `32026ms` | `0.93` | `12` `16551ms` `0.72` | `16.5s` |
| `gemma-4-E4B` vision `115` | `115` `70800ms` | `1.62` | `~0.54` (`919` tokens `1408767ms`) | `~70s` |

`curl -s -H "Authorization: Bearer sk-@8615269azSX" http://127.0.0.1:4000/v1/models` now `grep gemma` -> `local/gemma-4-E4B`, no `qwen2.5-vl-3b`. `whisper.service:09:33` active. Small 3B was ~1.6x faster text, but vision `600s` timeout made it unusable - `gemma` wins for offline vision on this CPU.

## 7. Solution Summary

| Change | Commit | Files |
|---|---|---|
| Open WebUI | `b7f1566` | `common/ai/open-webui.nix:1`, `common/ai/default.nix:10`, `system/default.nix:16`, `profiles/workstation/default.nix:23`, `flake.lock` |
| Whisper | `aa6562b` | `common/ai/whisper.nix:1`, `common/ai/default.nix:11` |
| qwen2.5-vl-3b | `59c04ef` -> `0ba2128` removed | `common/ai/llama-cpp.nix:22`, `common/ai/litellm/config.yaml:75`, `/srv/ai/models/qwen2.5-vl-3b/` (`3.4G` deleted) |
| gemma-4-E4B | `219de1a` | `common/ai/llama-cpp.nix:28` (+mmproj), `litellm/config.yaml:75`, `/srv/ai/models/gemma-4-E4B/*` (rsync 6.33G) |
| mmproj ready | `5551bab` + `8322694` -> `0ba2128` reverted for qwen | `llama-cpp.nix:26` `mmproj` wiring, then removed |

All `nix flake check` + `dry-run` pass. Final: `whisper` auto, `gemma` local `mmproj`, no `qwen`.

## 8. Verification Plan

```bash
systemctl status llama-cpp whisper litellm open-webui --no-pager | head -n 30
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool | grep id # 5
curl -s -H "Authorization: Bearer sk-@8615269azSX" http://127.0.0.1:4000/v1/models | python3 -m json.tool | grep id # 12
curl -s -H "Authorization: Bearer sk-@8615269azSX" http://127.0.0.1:4000/v1/models | grep gemma # gemma-4-E4B
curl -s http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer sk-@8615269azSX" -H "Content-Type: application/json" -d '{"model":"local/gemma-4-E4B","messages":[{"role":"user","content":[{"type":"text","text":"describe image"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}]}' | python3 -m json.tool
journalctl -u llama-cpp -f # gemma vision 1.62 tok/s prompt
curl -s http://127.0.0.1:8090/ # whisper
```

Expected: `whisper` `8090`, only `gemma-4-E4B` vision, `qwen` gone, no `600s` timeout.

## 9. Pending Actions

- `nixos-rebuild list-generations` still `234` `09:48:18` after `0ba2128` - toplevel `dzh4...` didn't bump; check `nix store ping` or `nix flake update`.
- Test `gemma-4-E4B` vision with real image via `open-webui` (already succeeded `115` tokens `1.62 tok/s`), confirm no OOM with `qwen3`/`qwen2.5-coder` concurrent.
- Dirty `AGENTS.md:9` stash - commit or discard.
- `whisper` STT via `open-webui` `AUDIO_STT_ENGINE` or `curl -F file=@/tmp/test.wav http://127.0.0.1:8090/inference`.

## 10. Recommendations (or: Don't Trust DNS When You're the DNS)

1. Always use `http://127.0.0.1:4000/v1` for server-to-server - sandboxed `DynamicUser` cannot resolve `*.home.arpa:443`.

2. Keep one offline vision: `gemma-4-E4B` (`5.0G` local, `0.72 tok/s`, works) + `nvidia 11B` online. Drop `qwen2.5-vl-3b` (`1.6G` `mmproj` + `1.9G` model) due to `600s` timeout on this CPU; if you want it back, add `--timeout 1800` in `common/ai/llama-cpp.nix:28`.

3. Persist `/srv/appdata/litellm/config.yaml` vs `common/ai/litellm/config.yaml` - activation only seeds if missing; after `git` change `cp` to runtime and `restart litellm`.

4. For Windows models, `rsync` to `/srv/ai/models/<name>/` and `0644 sigit:users`; avoid `/mnt/c`.

5. If generation doesn't bump, check `nix eval --raw ...toplevel` vs `/run/current-system` and `git stash` dirty.

That's the zoo after dark with a whisper and a gemma that actually sees. Next: feed gemma a real photo and see if 0.72 tok/s feels like 5.0G well spent.

Generated by Muse Spark 1.2 Contributor-Free (Meta)
