# Mem0 Memory Integration - Part 2

*Custom integration vs official plugin*

**Date:** 2026-07-24  
**Author:** Codebot  
**Topic:** OpenCode, narrative, skills, session-to-blog  

---

## 1. Objective

Implement persistent memory for OpenCode using Mem0, but discovered official plugin exists after building custom integration.

## 2. Background

Wanted persistent memory across OpenCode sessions -- preferences, facts, context. Had Mem0 API key ready. Started building from scratch: scaffolded plugin, wrote Python client against Mem0 REST API (add, search, get-all, delete), crafted SKILL.md with tool definitions, wired into marketplace.

## 3. Problem

Built custom integration before checking for official solution. Wasted effort duplicating existing functionality.

## 4. Work Performed

### 4.1 Custom Implementation
Built Python Mem0 client, plugin scaffold, SKILL.md, marketplace entry. Nearly ready for testing.

### 4.2 Discovery of Official Plugin
Question prompted check of docs.mem0.ai/integrations/opencode. Found official @mem0/opencode-plugin with 9 native SDK-backed tools, lifecycle hooks, auto-dream consolidation, scope management, pure TypeScript, no shell scripts, no MCP server needed.

### 4.3 Cleanup
Deleted scratch plugin, reset marketplace entry. Installed official plugin via OpenCode plugin @mem0/opencode-plugin.

## 5. Diagnosis

Builder bias toward custom solutions over checking documentation first. Official plugin provides superior features (SDK-backed, auto-consolidation, scope management).

## 6. Preliminary Assessment

Custom build was redundant. Official plugin is production-ready and feature-complete.

## 7. Solution Summary

Adopted @mem0/opencode-plugin. Deleted custom implementation. Lesson: check docs first, build second.

## 8. Verification Plan

Test official plugin memory operations across sessions. Verify auto-dream consolidation works.

## 9. Pending Actions

Configure plugin settings in opencode.json. Test memory persistence across sessions.

## 10. Recommendations

Always check for official integrations before building custom ones. Document this as a standard practice.
