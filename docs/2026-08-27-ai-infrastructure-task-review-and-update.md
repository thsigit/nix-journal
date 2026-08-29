# AI Infrastructure Task Review and Update

*or: How I audited the task list against actual code and found most items already completed*

**Date:** 2026-08-27  
**Author:** Codebot  
**Topic:** ai-infrastructure, task-management, litellm, homelab, nixos

---

## 1. The Task Audit Request

The user asked me to verify the completion status of items in the AI Infrastructure Plan task file (`/home/sigit/.config/opencode/tasks/ai-infrastructure.md`) by inspecting the actual code in `/srv/repo/nix-lab/common` and `/srv/repo/litellm-cli`. They believed most tasks were done but wanted confirmation before updating the task file.

## 2. Deep Code Dive

I conducted a thorough inspection of:
- LiteLLM-related NixOS modules (`common/ai/litellm/`)
- LiteLLM CLI package and module (`litellm-cli/`)
- Activation scripts and services
- Provider management and model fetching logic
- Git commit history for key changes

## 3. Key Findings

### ✅ Surprisingly Completed Tasks
Several tasks thought to be pending were actually already implemented:

**DATABASE_URL "Fix"**
- Not merely reading from database.env - PostgreSQL dependency was entirely removed
- Commit cbfeaa7 shows: "refactor(litellm): remove PostgreSQL, run no-DB mode"
- LiteLLM now runs in pure API proxy mode with no database

**NVIDIA Inventory Switch**
- The fetch-models.sh script does exactly what "Switch NVIDIA inventory to litellm-cli models fetch nvidia" requested
- It queries each provider's `/v1/models` endpoint directly via curl
- For NVIDIA: `https://integrate.api.nvidia.com/v1/models` with bearer token auth
- Updates committed `data/models.json` and syncs to runtime `/run/litellm-cli/models.json`
- Runs via `litellm-cli fetch` subcommand (called by doctor service hourly)

**AI Module Reorganization**
- The `common/ai/` → `common/ai/litellm/` grouping was already done
- `common/ai/default.nix` imports `./litellm` alongside other AI services
- Verified by directory structure and imports

### 🔄 Actually In Progress
Only one task truly needs work:

**Automatic Fetch Before Render**
- The `litellm-render` service runs `litellm-cli debug render` only
- It uses existing `/run/litellm-cli/models.json` with no pre-fetch
- The doctor service runs fetch hourly, but render happens on config change
- Gap: render process doesn't guarantee freshest model inventory

### 📋 Genuine To-Do Items
Several items remain legitimate work:
- Blacklist remaining 22 broken models
- Implement 404/410 error-based blacklisting strategy
- Prioritize stable model families (Llama, Mistral, Nemotron)
- Document model modality support

### ⏸️ Correctly Deferred
Items appropriately left for later:
- Add OpenWebUI consumer (`openwebui.home.arpa`)
- Dual URI setup (litellm.home.arpa/admin + openwebui.home.arpa/user)
- Multi-modal routing (image/audio/embeddings)

## 4. The Activation Script Discovery

While reviewing `/srv/repo/nix-lab/common/ai/litellm/litellm-cli.nix`, I found:
- `system.activationScripts.litellm-healthjson-prep` is complete (creates health.json)
- `system.activationScripts.litellm-cli-config` has only deps but no `text` block
- This makes it a no-op activation script that only enforces ordering but performs no actions
- User noted they'll fix this in next session

## 5. Task File Update

I updated `/home/sigit/.config/opencode/tasks/ai-infrastructure.md` to reflect reality:
- Moved 3 items from To Do/Deferred to Completed (with explanations)
- Changed "Fix DATABASE_URL hardcoding" to note the actual solution (no-DB mode)
- Kept "Update render.sh or boot process to auto-fetch before render" as In Progress
- Left genuinely pending items in To Do
- Maintained deferred items as appropriate

## 6. Lessons Learned

1. **Trust but verify**: Task lists can drift from actual implementation
2. **Git history is invaluable**: Commit messages often reveal the true story
3. **Code doesn't lie**: Grepping for actual function names beats speculation
4. **NixOS services tell the real activation story**: When/what actually runs at boot
5. **Documentation lags implementation**: The task file was conservative about claiming completion

The AI infrastructure is actually in much better shape than the task list suggested - the foundation is solid, and remaining work is mostly refinement and edge cases rather than core functionality.

---
*Report generated during homelab session investigating AI infrastructure task completion status.*
