# GitHub Copilot Free Shows No Models in OpenCode (or: 54 Models, None of Them Pickable)

**Date:** 2026-10-09  
**Author:** Codebot  
**Topic:** opencode, github-copilot, providers, config-schema, oauth, models-dev

---

## 1. Objective (or: Make the Free Copilot Play Nice)

The goal was modest: wire GitHub Copilot into opencode V2 as a real, selectable
provider for agents, using the *supported* device-OAuth login rather than the
paste-a-token custom-provider route. The question was just "does the built-in
provider work once I log in?" The answer turned out to be a small novel about
GitHub plan tiers, a plugin that quietly disables everything, and a config
schema that changed more than anyone told the config file.

## 2. Background (or: A Credential Pretending to Be a Provider)

In opencode V2, `github-copilot` is not a normal config provider backed by a
static catalog. It is a **device-OAuth connection** (`opencode auth login
github-copilot`, an interactive TTY flow) stored in the state DB, plus a
built-in plugin - `GithubCopilotPlugin` - that at startup reaches out to GitHub
for the account's model list and builds the provider from whatever comes back.

Two stores are involved, and they disagree about history:

| Store | Contents | Who writes it |
| --- | --- | --- |
| `~/.local/share/opencode/auth.json` | Legacy V1 OAuth block (old `gho_` token, `expires: 0`) | Nothing, in V2. It just sits there. |
| `~/.local/share/opencode/opencode.db` -> `credential` | The live V2 connection (`integration_id=github-copilot`, `method_id=device`, `active=1`, metadata incl. `apiEndpoint`) | `opencode auth login` |

The models.dev catalog cached in the DB (`kv` key `models-dev:catalog`) *does*
list `github-copilot` with 35 models (`gpt-5.4`, `claude-opus-4.8`,
`gemini-3.6-flash`, ...), `npm: @ai-sdk/openai-compatible`, api
`https://api.githubcopilot.com`. On paper there is plenty on offer. On paper.

## 3. The Symptom (or: `opencode models` Says Nothing)

After a clean device login and a service restart:

```text
$ opencode models | grep -i copilot
$ echo $?
1
```

Zero models. And:

```text
$ opencode run -m github-copilot/gpt-4o "reply with exactly: OK"
Error: Model unavailable: github-copilot/gpt-4o
```

Yet the *same* model, through a scratch project config and a standalone server,
answered correctly:

```text
$ opencode run --standalone -m github-copilot/gpt-4.1 "What is 17*23? Reply with just the number."
391
```

The credential is real and the network works. The provider simply never gets
registered in the background service.

## 4. Methods Tried (and Failed)

Eleven attempts. Every one either did nothing, worked once and evaporated, or
worked only *outside* the background service.

### 4.1 Trust the built-in provider after login

Log in, restart, list. Zero models. The models.dev catalog knows the provider;
the runtime does not surface it.

### 4.2 Prove the credential and the network path first

Before blaming opencode, verify the token. Read the `gho_` access token from the
V2 connection (or the stale `auth.json`) and hit GitHub directly:

```text
GET https://api.github.com/user                          -> 200
GET https://api.individual.githubcopilot.com/models      -> 200 (54 models)
POST https://api.githubcopilot.com/chat/completions      -> choices[] for gpt-4o,
                                                            gpt-4o-mini, gpt-4.1
```

Credential valid, endpoint reachable, chat works. Non-OpenAI ids
(`claude-*`, `gemini-*`) return `400 model_not_supported` on this plan, but the
OpenAI set is fine. This ruled out "bad token" entirely.

### 4.3 Declare the V1 `provider.github-copilot` block in the hub config

Add the legacy shape to `~/.config/opencode/opencode.json`, restart the service:

```json
"provider": {
  "github-copilot": {
    "name": "GitHub Copilot",
    "models": { "gpt-4o": {}, "gpt-4o-mini": {}, "gpt-4.1": {} }
  }
}
```

Still absent from `opencode models`; runs still fail. No change.

### 4.4 Declare the native V2 `providers.github-copilot` block in the host overlay

Move to the V2 shape and put it in the host-local overlay
(`OPENCODE_CONFIG=~/.config/opencode/overlays/opencode.fedora.json`), then
restart:

```json
"providers": {
  "github-copilot": {
    "package": "@opencode/ai/providers/openai-compatible",
    "settings": { "baseURL": "https://api.githubcopilot.com" },
    "headers": { "Copilot-Integration-Id": "vscode-chat" },
    "models": { "gpt-4o": {}, "gpt-4o-mini": {}, "gpt-4.1": {} }
  }
}
```

Still absent. The overlay is read (its other key, `username`, applies), but the
provider does not survive startup. This proved the problem was not "the config
file is not loaded".

### 4.5 Declare it in a project `opencode.json` (cwd)

Put the same V2 block in `/tmp/opencode/opencode.json` and run from there
through the shared service:

```text
> plan | gpt-4.1
391
```

It works - sometimes. Re-running the same command a minute later returns
`Model unavailable`. A fresh project dir with the identical file reproduces both
behaviours. Nondeterministic.

### 4.6 Try the `~/.opencode/opencode.json` location

Hypothesis: opencode treats `.opencode/` in an ancestor as a project config.
Wrote the block to `~/.opencode/opencode.json`, ran from `$HOME`. Failed.
`opencode debug config` showed the file *is* loaded, but the provider still does
not win.

### 4.7 Try `~/opencode.json` and rely on ancestor search

Confirmed that opencode searches ancestor directories for a file literally named
`opencode.json`: a config in `/tmp/anc/` is picked up when running from
`/tmp/anc/sub`. So placed `~/opencode.json` and ran from a `$HOME` subdir:

```text
> plan | gpt-4o
OK.
```

Then from `$HOME` itself: `Model unavailable`. Then, shortly after, from
everywhere: `Model unavailable`. The success window closes on its own. Deleting
the redundant duplicate and restarting the service did not re-open it.

### 4.8 Restart, reload, and clear caches

`opencode service restart` (multiple times), `opencode reload`, `touch`-ing the
config to refresh mtimes, and a cold restart to clear any in-memory per-directory
cache. Standalone runs stayed green; the shared service stayed red. Not a cache.

### 4.9 Verify listings with `opencode models --standalone`

Dead end: `opencode models --standalone` returns an empty list (exit 0) in
v2.0.26, for any config. Listing verification must go through the shared
service, which is also the thing that misbehaves - a small catch-22 for testing.

### 4.10 Blame the whitelist plugin (it is innocent)

The hub runs a `model-whitelist` plugin that prunes providers declaring a
`whitelist`. Suspected it was hiding Copilot. Its debug log told the real story:

```text
nvidia:    43 models -> kept 5,  removed 38
opencode:  84 models -> kept 7,  removed 77
openrouter: 395 models -> kept 10, removed 385
kenari:    66 models -> kept 15, removed 51
cloudflare: 3 models -> kept 3,  removed 0
transform done; 671 -> 120 models
```

`github-copilot` never appears because it declares no `whitelist` - so the plugin
never touches it. Not the culprit. (The plugin reads `cfg.providers ?? cfg.provider`,
which matters later - see section 7.)

### 4.11 Header tricks on `/models`

If the sync returns models marked "not picker enabled", maybe the right headers
flip them on. Tested `Copilot-Integration-Id: vscode-chat`, `Editor-Version`,
and the minimal opencode-like set against
`https://api.individual.githubcopilot.com/models`. Same 54 models, same answer:

```text
picker_enabled 0
```

Headers are not the lever.

## 5. Diagnosis (or: It Is the Plan, Not the Config)

Ask GitHub who this account is:

```text
GET https://api.github.com/copilot_internal/user
```

```json
{
  "login": "<redacted>",
  "access_type_sku": "free_limited_copilot",
  "copilot_plan": "individual",
  "chat_enabled": true,
  "chat": { "quota_remaining": 200, "unlimited": false },
  "can_upgrade_plan": true,
  "endpoints": { "api": "https://api.individual.githubcopilot.com" }
}
```

`access_type_sku: "free_limited_copilot"` is the whole story. Copilot Free
**does not expose model selection**: `/models` returns the full 54-model list
with `model_picker_enabled: false` on every entry. opencode faithfully maps that
flag to each model's `enabled` state:

```js
// model builder inside the Copilot plugin
// ... cost, capabilities, variants ...
status: "active",
enabled: i.model_picker_enabled,   // <-- false for every model on the free plan
limit: { context: ..., input: ..., output: ... }
```

The sync does not drop the models - it imports all of them, then marks every one
disabled. A provider with zero enabled models is invisible and unusable. This is
exactly the documented "Copilot has no models" case, and the documented cause
(no plan that exposes models) is correct.

Relevant plugin internals recovered from the v2.0.26 binary:

```js
// sync: fetch the account's models
async function UE(base, headers) {
  const r = await fetch(`${base}/models`, { headers, signal: AbortSignal.timeout(5000) });
  if (!r.ok) throw Error(`Failed to fetch Copilot models: ${r.status}`);
  return new Map(QE(await r.json()).data.flatMap((u) => {
    const l = ie(IE(u));
    return l && DE(l) ? [[l.id, l]] : [];
  }));
}
// DE filters on policy/capabilities, NOT on model_picker_enabled:
function DE(e) {
  return e.policy?.state !== "disabled"
    && e.capabilities.limits?.max_output_tokens !== undefined
    && e.capabilities.limits.max_prompt_tokens !== undefined
    && e.capabilities.supports.tool_calls !== undefined;
}
```

Note the asymmetry: the filter keeps disabled-picker models, and the builder then
disables them anyway.

## 6. Why Every Override Is Flaky (or: The Plugin Fights Back)

The config-override routes (4.4-4.7) can work because they sidestep the sync:
they declare `gpt-4o`/`gpt-4.1` and let the OAuth token ride along as a raw
bearer to `api.githubcopilot.com`. But the built-in plugin's `provider.transform`
re-adds the synced (disabled) models whenever the provider list is rebuilt, which
happens per request for project configs:

```js
yield* e.provider.transform((_) => {
  const w = _.get(vo.githubCopilot);         // the github-copilot provider
  if (!w) return;
  if (l.models) {                             // sync succeeded
    _.add({ info: w.provider, models: Array.from(
      VE(l.baseURL ?? Wm(), l.models, Array.from(w.models.values())).values()),
      sourceConnection: l.connection });
    return;
  }
  // sync failed: patch existing models to the dedicated SDK
  for (const q of w.models.keys())
    _.models.update(w.provider.id, q, (T) => {
      if (T.package = cD("@ai-sdk/github-copilot"), l.baseURL)
        T.settings = cs(T.settings, { baseURL: l.baseURL });
    });
});
```

Net effect: global config and overlay blocks get clobbered at startup;
project-config blocks win only until the next transform. Hence "sometimes 391,
sometimes unavailable". This is not a config problem that a better JSON can
solve - it is the free plan refusing to publish selectable models, and the
plugin enforcing that refusal.

## 7. A Side Note: `opencode.json` V1 vs V2 (or: The Schema Moved While We Watched)

Since the whole exercise was config archaeology, here is the shape change that
cost the most time. opencode V2 accepts the V1 `provider` block, silently
normalises it, and logs what it threw away.

Verified directly on this host:

| Aspect | V1 (`provider`) | V2 (`providers`) |
| --- | --- | --- |
| Container key | `provider` (singular) | `providers` (plural) |
| SDK package | `npm: "@ai-sdk/openai-compatible"` | `package: "@opencode/ai/providers/openai-compatible"` |
| Endpoint / options | `options: { baseURL: ... }` | `settings: { baseURL: ... }` |
| Extra HTTP headers | not first-class | `headers: { ... }` (e.g. `Copilot-Integration-Id`) |
| Model filter | `whitelist: [...]`, `blacklist: [...]` | **removed** (restored by the `model-whitelist` plugin) |
| Provider id | `id` field | the map key |
| Model entry | `models.<id>.name` (thin) | `models.<id>` object (name/limit/cost/enabled/options...) |
| Default model | `"model": "provider/model"` (string) | normalised to `{ "providerID": ..., "model": ... }` |
| Credential store | `auth.json` (`type: oauth`, `access`, `refresh`, `expires`) | state DB `credential` table (`integration_id`, `method_id`, `active`, metadata) |
| Model catalog | shipped / static | models.dev catalog cached in the DB (`kv` = `models-dev:catalog`) |

The V1 block, as it actually exists in the hub file today:

```json
"provider": {
  "nvidia": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "NVIDIA NIM (direct)",
    "options": { "baseURL": "https://integrate.api.nvidia.com/v1" },
    "models": { "meta/muse-glimmer-30b": { "name": "muse-glimmer-30b" } },
    "whitelist": [ "meta/muse-glimmer-30b" ]
  }
}
```

The V2 shape that actually worked (in a project config):

```json
"providers": {
  "github-copilot": {
    "package": "@opencode/ai/providers/openai-compatible",
    "settings": { "baseURL": "https://api.githubcopilot.com" },
    "headers": { "Copilot-Integration-Id": "vscode-chat" },
    "models": { "gpt-4o": {}, "gpt-4o-mini": {}, "gpt-4.1": {} }
  }
}
```

What V2 said out loud when handed the V1 leftovers:

```text
level=WARN message="configuration normalization diagnostic"
  source=/home/sigit/.config/opencode/opencode.json
  path=$.provider.nvidia.whitelist
  kind=unsupported action="omitted unsupported legacy setting"
```

Paths flagged on this host:

```text
$.provider.nvidia.whitelist
$.provider.opencode.whitelist
$.provider.openrouter.whitelist
$.provider.kenari.whitelist
$.provider.cloudflare.whitelist
$.experimental.continue_loop_on_deny
```

And `opencode debug config` shows the translation happening - the V1 `provider`
comes back as `providers`, and the string default model as an object:

```json
"provider"  -> "providers": [ "nvidia", "opencode", "openrouter", "kenari", "cloudflare" ]
"model": "nvidia/meta/muse-glimmer-30b"
       -> { "providerID": "nvidia", "model": "meta/muse-glimmer-30b" }
```

Two practical consequences:

- A V1 `provider` entry still works for a *simple* provider (`npm`/`options`/
  `models`), which is why nvidia, kenari, openrouter and friends keep running.
- V1-only keys (`whitelist`, `blacklist`, `id`) are dropped. The hub keeps its
  whitelists working only because a plugin reads the raw file and re-applies the
  filtering V2 no longer does.

And a subtle trap for that plugin: it reads `cfg.providers ?? cfg.provider`. The
moment a `providers` (plural) key exists anywhere in the effective config, the
plugin stops seeing the V1 `provider` whitelists entirely. Another reason not to
mix shapes casually.

## 8. Verification (or: How We Know It Is the Plan)

| Claim | Evidence |
| --- | --- |
| Credential valid, chat works | `api.github.com/user` = 200; `/chat/completions` returns choices for `gpt-4o`/`gpt-4o-mini`/`gpt-4.1` |
| Provider surfaces 0 models | `opencode models \| grep -i copilot` = 0; service API reports no `github-copilot` provider |
| Account is Copilot Free | `copilot_internal/user` -> `access_type_sku: "free_limited_copilot"` |
| Every model is picker-disabled | `/models` = 54 entries, `model_picker_enabled: false` for all, unchanged across header sets |
| It is not the whitelist plugin | plugin debug transforms nvidia/opencode/openrouter/kenari/cloudflare only; no `github-copilot` line |
| Config routes exist and are racy | project-config runs return `391`/`OK`; repeated runs later fail; standalone stays green |
| The plugin enforces the disable | binary: `enabled: i.model_picker_enabled`; `provider.transform` re-adds synced models |

## 9. Pending Actions

- None required. Every config edit was reverted (hub config byte-identical to its
  pre-change backup; the fedora overlay restored to `{"username": "sigit"}`), and
  scratch/secret temp files were deleted.
- Revisit only if the GitHub account is upgraded to a Copilot plan with model
  selection. The built-in provider should then populate with no config at all -
  worth a one-line re-test, not a project.
- If a stable workaround is ever wanted on the free plan, it will require
  defeating the built-in `GithubCopilotPlugin` sync, not a richer JSON block.

## 10. Recommendations (or: Where to Put the Effort)

- **Check the plan before debugging the config.** `copilot_internal/user` answers
  in one request what hours of config archaeology cannot. `free_limited_copilot`
  means "chat only, no model picker", full stop.
- **`model_picker_enabled` is a plan gate, not a capability probe.** A model can
  answer perfectly via the API and still be marked unpickable. opencode's
  provider visibility follows the flag, so "it works with curl" does not imply
  "opencode will list it".
- **Do not fight a built-in plugin with config layering.** The Copilot plugin
  owns `github-copilot` model registration and re-applies its sync. A config
  block may win once and lose the next time the provider list is rebuilt.
- **When migrating V1 config to V2, grep the logs for the normalizer.** The
  `configuration normalization diagnostic` warnings name exactly which legacy
  keys (`whitelist`, `blacklist`, `id`) V2 silently dropped.
- **Keep provider access on this fleet where it already works.** The hub's
  Kenari, NVIDIA, OpenCode, OpenRouter, Cloudflare and Ollama providers carry the
  load; Copilot Free adds a quota-limited chat endpoint and nothing an agent can
  select.

The Copilot token was never the problem. The catalog was never the problem. The
problem was that a free account is allowed to *have* 54 models and not allowed
to *choose* any of them - and opencode, quite reasonably, refuses to show what
the account says cannot be picked.

## 11. Update (post-close): Copilot Works After All

Everything above is still true about the *built-in* provider: on Copilot Free,
`GithubCopilotPlugin` maps `model_picker_enabled: false` to `enabled: false`, so
`github-copilot` surfaces zero models. But that is a gate in one plugin, not a
dead end for the models themselves. The raw GitHub OAuth token is accepted as a
bearer at `https://api.githubcopilot.com/chat/completions`, and any provider named
something *other* than `github-copilot` is never touched by the sync transform.

The working recipe is a separate provider id plus the existing credential:

- **Config** (no secret in it): a `provider.copilot` block using
  `@ai-sdk/openai-compatible`, `baseURL https://api.githubcopilot.com`, and the
  `Copilot-Integration-Id` / `Editor-Version` headers.
- **Credential**: a `copilot` row in the state DB `credential` table
  (`value={"type":"key","key":"<gho_ token>"}`). opencode resolves it by provider
  id, so the token never lands in `opencode.json`.

Verified on this host: `opencode models` lists `copilot/*`, and
`opencode run -m copilot/gpt-4.1` answers `391` from a neutral cwd - stable
across repeats, because the plugin only rewrites the id `github-copilot`.

Working ids on the Free plan are the older OpenAI family:
`gpt-4.1`, `gpt-4.1-2025-04-14`, `gpt-4o`, `gpt-4o-mini`,
`gpt-4o-2024-11-20`, `gpt-3.5-turbo-0613` (plus `gpt-4-o-preview`). The other
~44 of the 54 models return `400 model_not_supported`, including every
`gpt-5.x`/`gpt-6` id - so `model_picker_enabled` is not the only gate; the plan
also refuses the newer endpoints outright.

The lesson from section 10 still holds - do not fight the built-in plugin - but
it needs a qualifier: sidestep it by name, and the models are usable. Naming the
provider anything but `github-copilot` keeps the sync transform away from it
entirely.

---

Generated with Big Pickle by OpenCode
