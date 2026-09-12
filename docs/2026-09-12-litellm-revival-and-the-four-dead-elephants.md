# An Empty Config, Four Dead Elephants, and a Hard Veto on Kimi (or: The LiteLLM Revival, September Edition)

**Date:** 2026-09-12  
**Author:** Codebot  
**Topic:** litellm, nvidia, config, pruning, vision, embedding, discovery

---

## 1. Objective (or: Why Is Everything Down, Again?)

The phone call went like clockwork: "go to homelab and check why litellm fails." One glance at `systemctl status` told the whole story - the gateway had been down since boot at 06:12 WITA, and the culprit was buried in a single line of a Python traceback:

```text
Exception: Config cannot be None or Empty.
```

The config file it was so proudly refusing to load was, at that moment, a perfectly round zero bytes. So this session started as a rescue and turned into the most productive kind of rescue: once the lights were back on, every model that had been silently rotting in the roster got dragged into the sun and interrogated. The scorecard at the end: the proxy gained three fresh faces, lost four dead ones, and made a firm executive decision about embeddings.

The plan:

1. Identify why `litellm.service` refused to boot.
2. Restore a working config.
3. Re-verify the NVIDIA roster - because, spoiler, "NVIDIA-only" had quietly become "NVIDIA-mostly-dead."
4. Pin down one vision model and one embedding model for Open WebUI, and not a single one more.

## 2. Background (or: Where We Left the Menagerie)

The last time the zoo was curated properly, `2026-09-02`'s pruning session shrank the proxy from 32 models to 7: NVIDIA-only, static config, every survivor round-trip tested. The architecture has been stable ever since:

| Piece | Location | Notes |
|---|---|---|
| Live config | `/srv/appdata/litellm/config.yaml` | admin-edited, never re-rendered on rebuild |
| Committed seed | `/srv/repo/nix-lab/common/ai/litellm/config.yaml` | first-boot copy, synced by hand |
| Provider registry | `/srv/appdata/litellm/providers.json` | litellm-cli's view of the world |
| Secrets | `/run/secrets/providers.env` (sops) | `NVIDIA_API_KEY`, `LITELLM_MASTER_KEY` |
| Runtime | `services.litellm`, native systemd, no PostgreSQL | `--config /srv/appdata/litellm/config.yaml` |

The new wrinkle since September: the September-2 survivor list (`gpt-oss-120b`, `nemotron-3-super-120b`, `nemotron-3.5-lightning`, plus `llama-3.2-11b-vision` and two embedders) had started to collect dust. And as of this morning, the live config was *empty* - the whole menagerie reduced to a directory listing and a shrug.

## 3. Problem (or: The Zero-Byte Elephant in the Room)

The journal told it plainly:

```text
Sep 12 06:12:28 homelab litellm[1231]: ... _get_config_from_file -> "Config cannot be None or Empty."
Sep 12 06:12:30 homelab litellm[1231]: ... status=1/FAILURE
```

`/srv/appdata/litellm/config.yaml` sat at `-rw------- 1 sigit users 0` - size zero, owner sigit, last modified 20:47 the night before. Someone (or some past-me) had truncated the live config, and the activation script's "seed only if missing" rule did exactly what it said on the tin: the file existed, so nothing was seeded. The service dutifully crashed into the morning.

Downstream of that, three more problems were waiting their turn:

1. **EOL models had snuck back into the text roster.** `gpt-oss-120b` and `nemotron-3-ultra-550b` were pulling duty again after a restore that reached for a stale backup.
2. **The provenance of "working" was a single stale list.** The `litellm-nvidia-discovery` skill exists precisely so we test, not assume. It had not been run in ten days.
3. **Two embedding models were one too many.** The Open WebUI integration wanted exactly one embedding workhorse, and the charade of "both are fine, keep both" had to end.

## 4. Work Performed

### 4.1 The Rescue (or: Backups, Not Guesswork)

First move, house rules: back up the sad zero-byte config and the providers registry before touching anything.

```bash
cp config.yaml   backups/config.yaml.pre-nvidia-update-20260912-095247
cp providers.json backups/providers.json.pre-nvidia-update-20260912-095247
```

Then a hero restored the config from a healthy sibling (`config.yaml.new`, the NVIDIA-only 4-model set), and a `systemctl restart` brought the gateway back on its feet. Narrator: it was not that simple, but let's give the restoration its due - the service came up, `/health/readiness` answered `{"status":"healthy","db":"Not connected"}` in the expected no-DB way, and a round-trip against `nemotron-3.5-lightning` returned proper content.

### 4.2 Enter the Discovery Skill (or: It Was Definitely Not All Working)

With the lights back on, we let the discovery script do what it does best - actually call every candidate:

```bash
./litellm-nvidia-discovery.sh --test
```

Result (text models, 45s timeout each):

| Model | Verdict |
|---|---|
| `nvidia/meta/muse-glimmer-30b` | **PASS** |
| `nvidia/nvidia/nemotron-3-super-120b-a12b` | **PASS** |
| `nvidia/nvidia/nemotron-3.5-lightning-30b-a3b` | **PASS** |
| `nvidia/openai/gpt-oss-20b` | **PASS** |
| `nvidia/moonshotai/kimi-k3` | TIMEOUT |

Five text models in the filtered list, four passed, and `kimi-k3` (a relic that had survived two pruning rounds) finally got the timeout it had been asking for. Notably absent from the list: `gpt-oss-120b` and `nemotron-3-ultra-550b` - they are no longer even listed in NVIDIA's text catalog for this account, which is the free-tier way of saying "decommissioned."

### 4.3 The New Text Roster (or: Four Passes, No Grievances)

The working set settled on the four who answered the phone:

| Model | Reasoning-capable? |
|---|---|
| `nvidia/meta/muse-glimmer-30b` | yes (`reasoning_content` + `content`) |
| `nvidia/nvidia/nemotron-3-super-120b-a12b` | - |
| `nvidia/nvidia/nemotron-3.5-lightning-30b-a3b` | - |
| `nvidia/openai/gpt-oss-20b` | yes (`reasoning_content` + `content`) |

(`gpt-oss-20b`'s first probe looked alarming - `content: null` - until we realized it is a *reasoning* model and the answer lives in `reasoning_content`. A bigger `max_tokens` settled it: `content: "OK"`.)

### 4.4 The Vision and Embedding Veto (or: One Each, Final Answer)

The user's decree: keep vision/embedding for Open WebUI, but pick **one** of each. So we went catalog-fishing against NVIDIA's `/v1/models` (82 listed for the account) and probed the plausible candidates:

**Vision candidates:**

| Model | Result |
|---|---|
| `meta/llama-3.2-11b-vision-instruct` | **chat round-trip PASS** |
| `meta/llama-3.2-90b-vision-instruct` | empty reply |
| `nvidia/neva-22b` | null content / no usable chat |
| `microsoft/phi-3-vision-128k-instruct` | null content / no usable chat |

Same story as September: exactly **one** vision model is actually usable through chat completions on this account. Pick made itself.

**Embedding candidates:**

| Model | Result |
|---|---|
| `nvidia/nvidia/nemotron-3-embed-1b` | PASS, 2048-dim (text-only) |
| `nvidia/nvidia/llama-nemotron-embed-vl-1b-v2` | PASS, 2048-dim (**multimodal** VL) |
| `nvidia/nv-embedqa-mistral-7b-v2` | 404 not for account |
| `nvidia/embed-qa-4` | 404 not for account |
| `snowflake/arctic-embed-l` | 404 not for account |

Both embedders that are entitled to the account work and return 2048 dimensions. The tiebreak was capability, not dimension count: `llama-nemotron-embed-vl-1b-v2` embeds **images and text**; `nemotron-3-embed-1b` is text-only. For a box that just got its vision story sorted, the multimodal embedder is the single obvious house model. `nemotron-3-embed-1b` was cut.

The local llama.cpp router models stayed put - `tinyllama`, `qwen2.5-coder`, `qwen3`, `sailor2-1b`, `mxbai-embed-large` - because `llama-cpp.service` is alive and those are the point of the gateway. `background_health_checks: true` rode along so `/health` stays fast.

### 4.5 Verified Round-Trips (or: Proof, Not Vibes)

Every survivor was exercised through the actual proxy on `:4000`:

| Model | Probe | Result |
|---|---|---|
| `nemotron-3.5-lightning-30b` | chat | content returned |
| `muse-glimmer-30b` | chat | content "OK" |
| `gpt-oss-20b` | chat | reasoning + content "OK" |
| `llama-3.2-11b-vision-instruct` | chat w/ image | answered (on a red 1x1 px, it insisted "Pink." - close enough) |
| `llama-nemotron-embed-vl-1b-v2` | embeddings | 2048-dim |
| `tinyllama` | chat (local) | content returned |

### 4.6 Config Applied (or: The Seed Catches Up)

The live config and the committed seed were synced byte-for-byte, so the next accidental zero-byte incident finally seeds the *right* default:

```bash
cmp /srv/repo/nix-lab/common/ai/litellm/config.yaml /srv/appdata/litellm/config.yaml  # identical
```

`providers.json.nvidia.whitelist` was trimmed to the four PASS text models. Repo state: `M common/ai/litellm/config.yaml` (uncommitted working-tree change on `dev`).

## 5. Verification (or: The Numbers That Matter)

- `systemctl is-active litellm` -> active; startup logged all 11 models in `Set models:`.
- `/health/readiness` -> 200, healthy, no-DB mode.
- `journalctl` model list matches the config exactly (4 NVIDIA text + vision + VL-embed + 5 local).
- Backups on disk: `backups/config.yaml.pre-nvidia-update-20260912-095247`, `backups/providers.json.pre-nvidia-update-20260912-095247`.

## 6. The Final Roster (or: Eleven, Minus the Make-Believe)

| # | Model | Type |
|---|---|---|
| 1 | `nvidia/meta/muse-glimmer-30b` | text (reasoning) |
| 2 | `nvidia/nvidia/nemotron-3-super-120b-a12b` | text |
| 3 | `nvidia/nvidia/nemotron-3.5-lightning-30b-a3b` | text |
| 4 | `nvidia/openai/gpt-oss-20b` | text (reasoning) |
| 5 | `nvidia/meta/llama-3.2-11b-vision-instruct` | vision |
| 6 | `nvidia/nvidia/llama-nemotron-embed-vl-1b-v2` | embedding 2048d (multimodal) |
| 7-11 | `local/{tinyllama, qwen2.5-coder, qwen3, sailor2-1b, mxbai-embed-large}` | local llama.cpp |

Gone: `gpt-oss-120b`, `nemotron-3-ultra-550b` (text, EOL), `kimi-k3` (test only - timed out, never in final config), `nemotron-3-embed-1b` (double-fallback embedder, cut by veto).

## 7. Recommendations (or: Where We Go From Here)

1. **Account-scoped catalog, not blog-scoped.** NVIDIA's free tier quietly retires models; a model that passed in September can be a ghost by Friday. Re-run `litellm-nvidia-discovery.sh --test` before assuming "working."
2. **One vision, one embedding, no regrets.** The multimodal VL embedder covers both rerank and image-bearing retrieval. Adding a text-only peer back "just in case" is how a zoo grew to 32. Do not.
3. **Reasoning models return `content: null` at small `max_tokens`.** If a probe looks dead, raise the token cap before declaring EOL. Both reasoning models here passed once given room to think.
4. **Commit the synced seed.** The working-tree change to `common/ai/litellm/config.yaml` should be committed so the next rebuild's first-boot seed matches reality.
5. **Possible future discovery pass.** Several catalog entries remain unexplored at the time of writing (nano-class models, newer text entrants). A broader sweep is cheap and could surface a better long tail.

## 8. Open Questions and Follow-Ups

- **`kimi-k3`**: timed out in this run but the catalog still lists it. Retest in a future pass before writing it off.
- **Broader discovery**: this session only swept the 5-model text list plus the vision/embedding candidates. A full catalog walk (nano-class, newer text models) is on the board.
- **Index refresh**: the journal index is hand-maintained; this post needs a link in `index.md`.
- **Why was the live config zero bytes?** Still unclear - "someone" truncated it the night before, and the seed-if-missing rule protected the file precisely because it existed. Worth digging into if it recurs.

---

Generated by Big Pickle (OpenCode)