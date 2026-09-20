# Wiring Cloudflare Workers AI Straight Into LiteLLM (or: The Missing Word That Cost Us a Day)

**Date:** 2026-09-20  
**Author:** Codebot  
**Topic:** litellm, cloudflare, workers-ai, homelab, open-webui, openai-compatible

---

## 1. Objective (or: Why Bother With a Middleman We Already Have)

Connect Cloudflare Workers AI to the homelab LiteLLM proxy so its free/cheap models show up in Open WebUI at chat.home.arpa alongside the NVIDIA, Ollama, and OpenRouter routes. The catch: do it directly through Cloudflare's OpenAI-compatible /ai/v1 endpoint. No wrapper service, no extra network hop, no second thing to babysit at 3am. The goal was three working Cloudflare models by end of session. Spoiler: we got there. The path was not simple.

## 2. Background (or: The Wrapper We Were Glad to Delete)

Earlier iterations of this setup routed LiteLLM through a local cloudflare_wrapper.py that translated requests into Cloudflare's legacy /ai/run format. It worked, but it was one more process, one more restart ritual, and one more place for a typo to hide. Cloudflare ships a native OpenAI-compatible Chat Completions endpoint, so the wrapper was pure overhead. We deleted cloudflare_wrapper.py and kept cloudflare_model_map.yaml around as a reference (it is just a lookup table now, not wired into anything).

The proxy runs as a NixOS systemd unit: litellm.service, ExecStart points at /nix/store/.../litellm --host 127.0.0.1 --port 4000 --config /srv/appdata/litellm/config.yaml, with EnvironmentFile=/run/secrets/providers.env supplying CF_API_TOKEN and CF_ACCOUNT_ID. Restart requires root; the agent cannot SIGHUP a root-owned PID, so live reload is always a human step.

## 3. Problem (or: Three Wrong Turns Before the Right One)

Getting a Cloudflare model to answer through LiteLLM threw three distinct errors, each a different root cause:

1. LLM Provider NOT provided - LiteLLM could not infer the provider from a bare @cf/... model string. It wants the provider prefixed onto the model name.
2. Hardcoded-deprecation redirect - @cf/meta/llama-3-8b-instruct and @cf/meta/llama-3-1-8b-instruct are deprecated in Cloudflare's catalog; the v1 endpoint replies 410 Gone with a deprecation notice.
3. No route for that URI (HTTP 400, code 7000) - the real blocker. The api_base was missing the accounts/ segment.

Errors 1 and 2 were solved mid-session. Error 3 was the one that survived until the very end, disguised as a token problem.

## 4. Work Performed

### 4.1 The Three Model Entries

Added to model_list in /srv/appdata/litellm/config.yaml:

```yaml
  - model_name: cloudflare/llama-3-8b-instruct
    litellm_params:
      model: "openai/@cf/meta/llama-3.2-3b-instruct"
      api_base: https://api.cloudflare.com/client/v4/accounts/54d5812cf8ec517010c97e8e24b33b46/ai/v1
      api_key: os.environ/CF_API_TOKEN
      provider: openai
  - model_name: cloudflare/mistral-7b-instruct
    litellm_params:
      model: "openai/@cf/mistralai/mistral-small-3.1-24b-instruct"
      api_base: https://api.cloudflare.com/client/v4/accounts/54d5812cf8ec517010c97e8e24b33b46/ai/v1
      api_key: os.environ/CF_API_TOKEN
      provider: openai
  - model_name: cloudflare/nemotron-3-8b
    litellm_params:
      model: "openai/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
      api_base: https://api.cloudflare.com/client/v4/accounts/54d5812cf8ec517010c97e8e24b33b46/ai/v1
      api_key: os.environ/CF_API_TOKEN
      provider: openai
```

### 4.2 The openai/ Prefix Fix

LiteLLM's router calls get_llm_provider(model) at deploy time. A bare @cf/meta/... string matches no known provider, so the deployment is dropped with LLM Provider NOT provided. Prefixing the model with openai/ selects the OpenAI provider AND passes the part after the slash (@cf/meta/...) as the model field to Cloudflare. The provider: openai line is belt-and-suspenders; the prefix alone does the lifting. (Side note: an awk-inserted provider: line once landed at the wrong indentation - 14 spaces instead of 6 - and was silently ignored. YAML whitespace remains undefeated.)

### 4.3 The Model Identifier Fix

The original task plan used @cf/meta/llama-3-8b-instruct. Cloudflare has deprecated it; the v1 endpoint returns 410 Gone redirecting to a tombstoned alias. Swapped to current catalog models that returned HTTP 200 in direct tests: @cf/meta/llama-3.2-3b-instruct, @cf/mistralai/mistral-small-3.1-24b-instruct, and @cf/meta/llama-3.3-70b-instruct-fp8-fast.

### 4.4 The accounts/ Fix (the actual bug)

The api_base was https://api.cloudflare.com/client/v4/54d5812.../ai/v1. The correct path is .../client/v4/accounts/54d5812.../ai/v1 - note the accounts/ segment between v4/ and the account ID. Without it, every model returns 400 / code 7000 / No route for that URI. This single missing word produced identical-looking failures across all models and all endpoints, which is exactly why it masqueraded as a credential or capacity problem. Adding accounts/ made the very next curl return real tokens.

### 4.5 Token Verification Detour

Cloudflare's /user/tokens/verify returns 1000 Invalid API Token and /accounts/ returns 9109 Unauthorized for a scoped Workers AI token. That is expected: the token only has AI permissions, not account/user read. Do not regenerate the token on the strength of those two endpoints. The only signal that matters is a successful inference call on /ai/v1/chat/completions. Once accounts/ was in place, that call returned 200 with content on the first try.

### 4.6 End-to-End Test (Before Live Reload)

Since the agent cannot restart the root-owned service, a temporary LiteLLM instance was launched on port 4009 with the env file sourced, pointed at the same config. All three models returned 200 with generated text:

```
$ curl -s http://127.0.0.1:4009/v1/chat/completions \
    -H 'Authorization: Bearer sk-...' \
    -d '{"model":"cloudflare/llama-3-8b-instruct","messages":[{"role":"user","content":"Say hi in one word"}],"max_tokens":8}'
{"choices":[{"message":{"content":"Hello."}}],"usage":{"total_tokens":43}}
```

## 5. Diagnosis (or: It Was Never the Token)

The chain of failures looked like a credential problem because the final error (No route for that URI) is the same string Cloudflare returns for an unauthenticated or malformed request. But the token was valid throughout - the scoped-token verification quirks explained above are red herrings. The decisive test was a direct curl with the corrected api_base: 200 plus a real completion. The missing accounts/ segment was the entire defect.

## 6. Solution Summary (or: The State We Shipped)

- Three Cloudflare models wired into /srv/appdata/litellm/config.yaml as cloudflare/llama-3-8b-instruct, cloudflare/mistral-7b-instruct, cloudflare/nemotron-3-8b.
- Each uses model: openai/@cf/..., provider: openai, api_key: os.environ/CF_API_TOKEN, and api_base with the accounts/ segment.
- Live litellm.service restarted by the human; all three models confirmed working from Open WebUI at chat.home.arpa.

## 7. Verification Plan

- [x] Temp instance on port 4009 returns 200 for all three models
- [x] systemctl restart litellm.service reloads live config
- [x] Open WebUI at chat.home.arpa lists and completes with all three Cloudflare models

## 8. Pending Actions

- None blocking. Optional: prune the deprecated @cf/meta/llama-3-8b-instruct / llama-3-1-8b-instruct references from the task plan so nobody reaches for them again.
- Optional: consider adding Cloudflare as a formal provider entry in providers.json (tracked separately in pending-litellm-add-providers.md); the model_list approach already satisfies the objective.

## 9. Recommendations (or: Words to Tattoo Near the Nix Store)

1. The accounts/ segment is not optional. Cloudflare's OpenAI-compatible base URL is https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1. Memorize the accounts/. It is the difference between 200 and a day of confusion.
2. Prefix Cloudflare models with openai/. LiteLLM needs the provider named explicitly; openai/@cf/meta/... is the incantation.
3. Ignore /user/tokens/verify and /accounts/ for scoped tokens. A Workers AI token legitimately fails both. Judge the token by a real inference call only.
4. Check the model catalog before wiring. @cf/meta/llama-3-8b-instruct is deprecated and answers with 410. Pick a current model or you will debug a ghost.
5. Test config changes on a temp port first. You cannot SIGHUP a root-owned service from the agent shell, but you can launch a throwaway instance on 4009 and curl it. Do that before asking a human to restart the live one.

Generated by Hy3 (Free) by Kenari (free tier)
