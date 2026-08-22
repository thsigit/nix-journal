# Mem0 Memory Integration - Part 1

*Entity scoping diagnosis*

**Date:** 2026-07-24  
**Author:** Codebot  
**Topic:** Mem0, OpenCode, troubleshooting, memory  

---

## 1. Objective

Test Mem0 connection, diagnose why previous hermes session memories were invisible, and understand Mem0 entity scoping and API key constraints.

## 2. Background

The client asked to check what Mem0 knows about them. Two searches (decision type, task_learning type) returned only two results from the current session (ses_1784893629), both under user_id: sigit, app_id: sigit. The client mentioned previous Hermes Agent sessions using user_id: hermes-user.

## 3. Problem

Mem0 searches across various entity parameter combinations (hermes-user with Hermes Agent, sigit with Hermes Agent, etc.) returned only the same three memories under sigit/sigit. Direct curl calls with hermes-user also returned empty results.

## 4. Work Performed

### 4.1 Initial Testing
Ran parallel searches for decision and task_learning memory types. Received two results from current session only.

### 4.2 Entity Parameter Exploration
Tested all combinations of user_id, app_id, agent_id parameters including hermes-user, Hermes Agent, sigit variants. All returned same three memories.

### 4.3 Global Scope Testing
Enabled explicit scope: global via MEM0_GLOBAL_SEARCH=false override. Still returned only three results.

### 4.4 Plugin Source Code Analysis
Examined @mem0/opencode-plugin at ~/.cache/opencode/packages/@mem0/opencode-plugin/node_modules/@mem0/opencode-plugin/dist/index.js. Found resolveFilters function (line 29541) hardcodes user_id and app_id from environment variables (MEM0_USER_ID=sigit, MEM0_APP_ID=sigit), overriding explicit parameters.

### 4.5 API Key Constraint Discovery
Direct curl to Mem0 API with hermes-user returned empty. The API key is project-scoped. Dashboard shows 2-year-old data because it uses web authentication (cookies/session) with org-wide visibility.

## 5. Diagnosis

The @mem0/opencode-plugin injects entity filters from environment variables regardless of explicit parameters. The API key itself is project-scoped, limiting visibility to the sigit project namespace. Hermes Agent and OpenCode use different entity namespaces under the same key.

## 6. Preliminary Assessment

Two separate API keys needed: one for Hermes Agent (daily logs), one for OpenCode (lessons). Shell profile exports cannot hold multiple MEM0_API_KEY values simultaneously.

## 7. Solution Summary

Create new project + API key on Mem0 dashboard for OpenCode. Options for key management: per-project opencode.json with env field, direnv for automatic switching, or org-wide API key with entity isolation via user_id/app_id routing.

## 8. Verification Plan

Create new Mem0 project for OpenCode. Configure opencode.json with new API key. Verify cross-project memory isolation works as expected.

## 9. Pending Actions

Implement chosen key management strategy (direnv or per-project config). Migrate existing OpenCode memories to new project if needed.

## 10. Recommendations

Always verify API key scope before assuming cross-project visibility. Check plugin source code for filter injection behavior. Document entity namespace conventions for each tool (Hermes Agent vs OpenCode).
