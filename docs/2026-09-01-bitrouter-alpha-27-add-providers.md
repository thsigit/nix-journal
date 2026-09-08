# BitRouter v1.0.0-alpha.27: Adding Providers Is Easy, Making Them Chat Is Not

**Date:** 2026-09-01  
**Author:** Codebot  
**Topic:** bitrouter, provider, gateway, nvidia, freetheai, openrouter

---

## 1. Objective (or: Round Two for a Router That Already Round-Robins)

BitRouter is the homelab's *other* LLM gateway - the quiet second router sitting
next to LiteLLM on port 4356, fronted by Caddy at `bitrouter.home.arpa`. While
LiteLLM is the workhorse that actually handles the model fleet, BitRouter has
been keeping one lonely routable model to itself: `openrouter/free`.

This session set out to fix that. The goal was to add the same upstream
providers BitRouter's louder sibling already uses - **nvidia** and **freetheai**
- with a small curated model set, and verify they actually route. By the end I
had a working multi-provider config, a new virtual key, a strange new respect
for the phrase "outbound dispatch," and very little to show for it except a
gloriously detailed explanation of why things *couldn't* work.

The happy ending: we reverted, because sometimes the correct answer is
"actually, it's fine as it is."

## 2. Background

### 2.1 What BitRouter Is

BitRouter is a self-improving LLM router with those buzzwords all over it:
OpenAI/Anthropic/Gemini-compatible, agentic, routing tables, the works. On the
homelab it runs as v1.0.0-alpha.27, a prebuilt glibc binary from the BitRouter
GitHub releases, packaged through a Nix derivation (`/srv/repo/bitrouter/
default.nix`) and deployed as a Podman container.

```
podman-bitrouter.service -> container 'bitrouter' (localhost/bitrouter:1.0.0-alpha.27)
  port 4356, Caddy vhost bitrouter.home.arpa
  config:  /srv/appdata/bitrouter/bitrouter.yaml
  sqlite:  /srv/appdata/bitrouter/bitrouter.db
  client auth on /v1/chat/completions: brvk_ virtual keys
```

The config loader has an `inherit_defaults` concept: built-in provider
definitions are merged underneath what you write. The claims in the README are
grand - "provider `derives` chains are resolved before the runtime starts" -
which is exactly what drew us in.

### 2.2 The Starting Config

A single, humble provider, doing one thing well:

```yaml
server:
  listen: 0.0.0.0:4356
  skip_auth: false

database:
  url: sqlite:///var/lib/bitrouter/bitrouter.db

providers:
  openrouter: {}

models:
  openrouter/free:
    endpoints:
      - provider: openrouter
        service_id: openrouter/free
```

### 2.3 What Keys Exist

The container loads its environment from the sops-encrypted `providers.env`
(pulled in by the Nix module's `environmentFiles`). Key *names* present:

`NVIDIA_API_KEY`, `FREETHEAI_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_API_KEY`,
`LITELLM_MASTER_KEY`.

Good news: the secrets we needed were already there. LiteLLM (the main gateway)
runs the same nvidia/freetheai/openrouter providers successfully, so the
upstream endpoints and credentials were proven good. We just needed BitRouter to
agree.

## 3. Problem

Add `nvidia` and `freetheai` to BitRouter, give them a small curated model set,
and confirm a chat request round-trips through the gateway.

The transfer of intent was simple. The YAML schema, it turned out, had opinions.

## 4. Work Performed

### 4.1 The Naive Attempt (derives)

BitRouter's own README shows exactly how you add a custom OpenAI-compatible
provider:

```yaml
providers:
  openrouter:
    derives: openai
    api_base: "https://openrouter.ai/api/v1"
    api_key: "${OPENROUTER_API_KEY}"
```

So naturally, we wrote:

```yaml
providers:
  nvidia:
    derives: openai
    api_base: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
  freetheai:
    derives: openai
    api_base: https://api.freetheai.xyz/v1
    api_key: ${FREETHEAI_API_KEY}
```

The gateway's answer was immediate and unambiguous:

```
provider 'freetheai' derives from unknown provider 'openai'
```

We tried `derives: openrouter`, `anthropic`, `google` - same rejection each
time. Every base the docs imply should exist was "unknown."

**Root cause:** in this alpha build only the *hosted* `bitrouter` cloud gateway
is compiled into the binary. All other provider definitions come from a
registry fetched at runtime. The `openrouter: {}` name works because it resolves
through that fetched registry, but none of the classic `openai`/`anthropic`/
`google` names are compile-time `derives` bases. The README describes a newer
world; the binary lives in an older one.

### 4.2 Switching to Explicit api_protocol

`derives` was out, so we reached for the `ProviderConfig` field directly:
`api_protocol`. Three YAML shapes later, we pinned down what this build actually
wants. The error messages did the archaeology for us:

- `api_protocol: openai` -> `expected sequence start`
- `api_protocol: [openai]` -> `expected mapping start`
- `api_protocol: { "*": openai }` -> `expected sequence start`

The winner is a **list of glob-to-protocol mappings**:

```yaml
providers:
  nvidia:
    api_protocol:
      - "*": openai
    api_base: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
```

Run it in a scratch container and *finally*, a gateway that serves instead of
yells. That was validation attempt number six, and it worked.

### 4.3 The Curated Model Set (and an Honest Look at NVIDIA)

We chose a small, sensible set - three from NVIDIA's current-gen catalog and
two from FreeTheAI - verified against each provider's live `/v1/models`:

```
nvidia/gemma-4-31b-it          ->  google/gemma-4-31b-it
nvidia/nemotron-nano-reasoning ->  nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
nvidia/nemotron-ultra          ->  nvidia/nemotron-3-ultra-550b-a55b
freetheai/gemini-3.5-flash     ->  bbl/gemini-3.5-flash
freetheai/glm-4.5              ->  glm/glm-4.5
```

Round-trips against the upstreams told an important story:

| Provider / model | Upstream result |
|---|---|
| freetheai `bbl/gemini-3.5-flash` | 200 OK |
| freetheai `glm/glm-4.5` | 200 OK |
| freetheai `bbl/gpt-5.4-mini` | 200 OK |
| nvidia `google/gemma-4-31b-it` | 000 timeout |
| nvidia `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 503 ResourceExhausted |
| nvidia `nvidia/nemotron-3-ultra-550b-a55b` | 000 timeout |
| nvidia `meta/llama-3.3-70b-instruct` | 410 Gone (EOL 2026-08-26) |

FreeTheAI was healthy and fast. NVIDIA NIM, true to the ongoing saga in our
pruning task, was having a rough week: the older plain `meta/llama-*` models are
dead (410 EOL), and the current-gen catalog was bouncing 503 "worker local total
request limit reached" alongside plain timeouts. This mattered later, but not
for the blocker we were about to hit.

### 4.4 Live Deploy (It Gets Worse Before We Understand Better)

The full six-model config loaded, the container restarted clean, and
`GET /v1/models` proudly listed all six models. Celebration, briefly.

Then we tried an actual chat request. The gateway was having none of it:

```
{"error":{"message":"internal error: no outbound dispatch registered for
protocol 'openai' (target provider 'nvidia'); register an OutboundAdapter +
Transport via OutboundDispatch::register","type":"internal_error"}}
```

The same error for `freetheai`. But `openrouter/free`? Smooth as silk, a
cheerful little `"OK"`.

That discrepancy is the whole story: **BitRouter alpha.27 will happily *advertise*
a custom `api_protocol: openai` provider, but it has no runtime outbound adapter
wired to actually complete the call.** The config layer validates, the routing
table lists the model, and the dispatcher throws up its hands. Built-in
providers have registered adapters; custom ones simply do not exist at dispatch
time in this build.

### 4.5 The Client-Key Riddle

There was a small side quest for completeness: the live gateway runs
`skip_auth: false`, so `/v1/chat/completions` demands a `brvk_` virtual key
(`/v1/models` will take the LiteLLM master key, but chat insists on a genuine
BitRouter key). We minted one via the container:

```
sudo podman exec bitrouter /bin/bitrouter key sign -u sigit
-> id:     brvk_id_e82552aef16b92c9
   secret: brvk_ihuLqJ2LNRD7_XrpR72PramD5iJxN2S7Wu82QO2a4j0
```

It authenticates fine and confirms the "no dispatch" error is a routing
limitation, not an auth failure. Worth knowing: there is **no `key revoke`
subcommand** - `key sign` is the only operation. Cleanup means deleting the row
from `api_keys` in the sqlite DB.

## 5. Diagnosis

BitRouter v1.0.0-alpha.27 cannot execute a chat against a custom,
OpenAI-compatible provider, even though it will happily load, validate, and
advertise it. The dispatch table has no adapter for it.

| Layer | Custom `api_protocol: openai` provider |
|---|---|
| YAML parse | OK |
| Config validation | OK |
| Model advertisement (`/v1/models`) | OK (model listed) |
| Chat dispatch (`/v1/chat/completions`) | FAIL - "no outbound dispatch registered" |

Built-in providers (`openrouter/free`) pass all four layers. The alpha binary
simply does not register arbitrary OpenAI-compatible outbound dispatch; that
belongs to a newer (or differently-built) BitRouter.

## 6. Preliminary Assessment

- The provider definitions and models are correct and load cleanly.
- The blocker is entirely in the runtime dispatch layer, not the config.
- For chat, this build only reliably routes to built-in/registered providers.
- Therefore adding nvidia/freetheai to BitRouter is, today, decorative - they
  show up in `/v1/models` but cannot complete a request.

## 7. Solution Summary

Decision: **revert.** The user's intent was explicit - "we're using bitrouter
only for openrouter:free." BitRouter's whole value here is that one route, and
LiteLLM already handles nvidia/freetheai properly. Since BitRouter could not
chat through the new providers anyway, keeping them around was pure cruft.

Reverted state:

```yaml
providers:
  openrouter: {}

models:
  openrouter/free:
    endpoints:
      - provider: openrouter
        service_id: openrouter/free
```

- Restored from backup, restarted the service -> `active`, `/v1/models` lists
  only `openrouter/free`.
- Deleted the minted test key (`brvk_id_e82552aef16b92c9`) from the DB; the
  original `sigit` key remains.
- Removed the intermediate broken-backup artifact.

## 8. Verification Plan

- [x] Confirm reverted config serves only `openrouter/free` (`/v1/models`).
- [x] Confirm `podman-bitrouter.service` is `active`.
- [x] Confirm the origin and original single `sigit` key remain in `api_keys`.
- [ ] (Blocked) Chat round-trip through a custom provider - cannot pass until
      BitRouter supports custom outbound dispatch.

## 9. Pending Actions

- Decide whether to upgrade BitRouter to a version that registers
  OpenAI-compatible outbound dispatch for custom providers (revisit if/when the
  fleet grows beyond LiteLLM).
- Keep this finding archived so nobody re-derives the `api_protocol` glob-map
  format from scratch.

## 10. Recommendations

1. **Leave BitRouter on `openrouter/free` only.** It does that one job and does
   it well; LiteLLM already covers nvidia/freetheai.
2. **Do not rely on `derives:`** in this build - every documented base is
   "unknown provider." Use the explicit `api_protocol` glob-map list.
3. **Treat "model advertised" as distinct from "model callable."** `GET
   /v1/models` lies when a custom provider has no outbound adapter. Test chat,
   not just the model list.
4. **Remember the `brvk_` key lifecycle:** `key sign` is the only CLI op - to
   revoke, delete the `api_keys` row in the sqlite DB.
5. **Revisit only if** the homelab needs a second exec-capable gateway. Until
   then, one router that works beats two that mostly don't.

## Relevant Files

- `/srv/appdata/bitrouter/bitrouter.yaml` - live config (reverted to openrouter)
- `/srv/appdata/bitrouter/bitrouter.yaml.bak-20260901-181043` - original config
  backup
- `/srv/appdata/bitrouter/bitrouter.db` - sqlite DB (`api_keys` table)
- `/srv/repo/bitrouter/default.nix` - BitRouter package derivations
- `/srv/repo/nix-lab/common/ai/bitrouter.nix` - NixOS service module

---

Generated by Big Pickle (OpenCode)
