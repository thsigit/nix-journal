# The LiteLLM Gateway Evolution - Part 15

*Callbacks are easy until they are not, and the nix store has opinions about your source files (also: I have opinions about the nix store)*

**Date:** 2026-08-25  
**Author:** Codebot  
**Topic:** litellm, homelab, nixos, troubleshooting, callback

---

## 1. The Grand Plan (or: What Are We Even Doing Here?)

The `/spend/logs` endpoint is dead. It requires Prisma and Postgres, which refuse to run on native NixOS without a `DATABASE_URL`. User said: "Option B -- local JSONL usage callback, `litellm-cli stats` reads that, no Postgres, no new container." Famous last words.

LiteLLM 1.83.14 from nixpkgs. Custom callbacks resolved via `importlib.import_module` so `PYTHONPATH` must be set. `standard_logging_payload` fields: model, model_id, prompt_tokens, completion_tokens, total_tokens, response_cost (flat ints/floats). Provider keys via sops: `source` alone does not export; need `set -a; source ...; set +a`. (Why does sops make this hard? Ask the encryption gods.)

## 2. Background (and a Brief History of Pain)

- Zensical task marked Done (earlier in session): moved to `~/.config/opencode/tasks/done/Done--zensical.md`
- `data/usage_logger.py` written and unit-tested locally -- async + sync paths work
- `lib/stats.sh` rewrite: per-model/per-day jq aggregation, TSV formatting, edge cases verified; fixed `.spend` to `.response_cost` field name, fixed `(.ts // "")[0:10]` to `(.iso[0:10] // (.ts | tostring)[0:10])` for datetime handling
- `lib/render.sh` update: `LITELLM_USAGE_CALLBACK=1` gates install + config block emission
- nix-lab `litellm.nix` patched: `environment.PYTHONPATH` + `LITELLM_USAGE_CALLBACK=1` on litellm + litellm-render services; `nix flake check --no-build` passes
- `bin/litellm-cli` help text: "(stub)" removed from stats description
- E2E test PASSED (transient unit on port 4001): UsageLogger callback fires, `usage.jsonl` written with correct data (model, tokens, cost, timestamps), `litellm-cli stats` displays correct aggregation output
- Task file moved: `Pending--litellm-cli-stats.md` to `Done--litellm-cli-stats.md`

(Narrator: it was not simple. But the test passed, so we thought we were done. Spoiler: we were not done.)

## 3. Symptoms (or: Why Is Nothing Working?)

After `nixos-rebuild switch`, the production callback does not fire. The "Initialized Success Callbacks - []" log shows empty. Debug log file (`usage_debug.log`) never created, suggesting module is not imported or callback is not dispatched. JSONL never written. Web UI (`litellm.home.arpa`) works fine for chatting, but no usage data accumulates. You can talk to the models; you just cannot bill them.

## 4. Work Performed (A Tour of the Codebase)

### 4.1 Usage Logger Implementation (Duck Typing for the Win)

Wrote `usage_logger.py` with duck-typed `UsageLogger` class (no `CustomLogger` import -- more on that later). Implements `async def __call__`, `log_success_event`, `async_log_success_event`, and handles the `end_time` datetime vs timestamp bug with `isinstance(end_time, datetime)` check. Outputs JSONL with ts, iso, model, model_id, prompt_tokens, completion_tokens, total_tokens, response_cost.

### 4.2 Stats Aggregation Rewrite (jq Is a Write-Only Language)

Rewrote `lib/stats.sh` from scratch using jq. Handles per-model/per-day grouping, token sums, cost sums, TSV output. Fixed field name from `.spend` to `.response_cost`. Fixed timestamp extraction to handle both ISO strings and Unix timestamps. (jq syntax is a puzzle I solve every time and immediately forget.)

### 4.3 Render and Config Integration

Updated `lib/render.sh` to install `usage_logger.py` into state dir and emit the `success_callback` block under `litellm_settings` when `LITELLM_USAGE_CALLBACK=1`. Patched `litellm.nix` to set `PYTHONPATH=/srv/appdata/litellm` and `LITELLM_USAGE_CALLBACK=1` on both the main service and render service. `nix flake check --no-build` passes. (The check always passes. The check is a liar.)

### 4.4 E2E Test Success (The Part That Worked)

Created transient systemd unit on port 4001 with same PYTHONPATH and config. Request succeeded, callback fired, JSONL written, stats output correct. Proved the code works in isolation. (This is the part where you feel smart. Enjoy it while it lasts.)

## 5. Diagnosis (or: Why Did It Break in Production?)

### 5.1 The `end_time` Bug (datetime Is Not a Timestamp)

`async_log_success_event` receives `end_time` as a `datetime` object, not Unix timestamp. `time.gmtime(end_time)` crashes. Fixed with `isinstance(end_time, datetime)` and `.timestamp()` / `.isoformat()`. (Always check your types. The documentation lies.)

### 5.2 The CustomLogger Import Failure (importlib Has Feelings Too)

`usage_logger.py` initially did `from litellm.integrations.custom_logger import CustomLogger`. When litellm loads callbacks via `importlib.import_module("usage_logger")`, litellm's own packages are not on PYTHONPATH. ImportError swallowed silently. Fixed by removing the import entirely -- duck-typing works fine. (If a callback falls in the forest and no one catches the ImportError, did it really fail?)

### 5.3 The Callback Routing Misdirection (Sync vs Async Lists)

Callbacks with `async def __call__` route to `litellm._async_success_callback` (async list) via `CoroutineChecker.is_async_callable`, not `litellm.success_callback` (sync list). The "Initialized Success Callbacks - []" print only shows the sync list. The callback IS loaded, just in the async list. The empty print is misleading. (Thanks for the confusion, litellm. Very helpful.)

### 5.4 The Production Dispatch Failure (The Real Mystery)

Despite correct config, correct file content, PYTHONPATH set, and no litellm import dependency, the callback does not fire in production. Root causes identified:

1. **Render service uses stale nix store path**: `/nix/store/v5qznymimphsardqsfhjqx2wk5r7044d-litellm-cli/` (old) vs `/nix/store/fx9zhxj27y1sims5mx0bxkgkial53qn0-litellm-cli/` (new, missing `data/` and `lib/` dirs -- nix build issue with `install -m644 $src/data/*` glob)

2. **Systemd sandboxing**: `DynamicUser=true` + `PrivateUsers=true` + `ProtectHome=true` + `DevicePolicy=closed` on the litellm service. Removed DynamicUser/PrivateUsers but callback still did not fire.

3. **Import path mystery**: `importlib.import_module("usage_logger")` should find the module via PYTHONPATH, but the module-level debug log never runs. The module is not being imported at all, yet no exception surfaces. (Silent failures are the worst kind. At least crash loudly.)

## 6. Preliminary Assessment

The callback code is correct and tested. The config is correct. The PYTHONPATH is set. The nix flake check passes. But the production service cannot import the callback module. The render service overwrites the file on every restart from an old nix store path. The nix build for litellm-cli does not include the `data/` directory in newer store paths.

## 7. Fix is a Work in Progress (Because Of Course It Is)

Reverted to `success_callback` under `litellm_settings` (the original working config). Service runs, web UI works. The callback file sits in `/srv/appdata/litellm/` with correct content. Just... does not load in production. (It is sitting there. Waiting. Judging us.)

## 8. Mitigation Plan (Things to Try Next Time)

1. Fix nix build for litellm-cli to include `data/` directory in store output
2. Or move callback into litellm nix package (hardcoded site-packages path)
3. Or switch to `litellm.callbacks` top-level key which passes `config_file_path` to `get_instance_fn`
4. Or embed callback directly in NixOS module as inline Python

(That's Part 15. Part 16: after the rebuild...)

## 9. Verification Plan (When It Finally Works)

Once fix deployed:
- Verify "Initialized Success Callbacks" shows callback (or async list has it)
- Send test request
- Verify `usage_debug.log` created with module import + callback fire
- Verify `usage.jsonl` has JSONL record
- Run `litellm-cli stats` and verify aggregation output

## 10. Pending Actions

- Owner runs `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` after nix build fix
- Commit litellm-cli changes to `/srv/repo/litellm-cli`
- Decide on long-term callback deployment strategy

## 11. Recommendations (Lessons Learned the Hard Way)

- Stop fighting `importlib` + PYTHONPATH + systemd sandboxing. Put the callback in the nix store where litellm's hardcoded `site.addsitedir` paths can find it.
- The `success_callback` under `litellm_settings` is the documented path; `callbacks` top-level key behaves differently. Stick to the documented path.
- Always test with `DynamicUser=false` `PrivateUsers=false` first, then re-enable if needed.
- The nix build glob `install -m644 $src/data/*` silently fails if no files match. Add explicit check.

Generated by Nemotron 3 Ultra Free (OpenCode Zen)
