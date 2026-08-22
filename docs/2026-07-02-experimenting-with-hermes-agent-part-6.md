# Experimenting with Hermes Agent - Part 6

*Windows-host llama.cpp bridge attempt*

**Date:** 2026-07-02  
**Author:** Codebot  
**Topic:** cli, wsl2, llama.cpp, dev-log  

## 1. Objective

Connect Hermes Agent in WSL2 to locally hosted llama.cpp server (via Ollama) on Windows host to integrate local inference into development workflow.

## 2. Background

WSL2 instance at 172.23.246.136 needed to reach Windows host at 172.23.240.1 on port 8080. Goal was to bypass remote providers like OpenRouter by using local llama.cpp server.

## 3. Problem

Connection attempts to port 8080 blocked by network restrictions. WSL2 environment variables conflicted with existing local setups. Multiple model switches attempted (Gemini 2.5 Flash to GPT-5-mini to Gemini 3.1 Flash Lite Preview) without resolution.

## 4. Work Performed

### 4.1 Network Path Identification
- WSL2 IP: 172.23.246.136
- Windows host IP: 172.23.240.1
- Target port: 8080 (llama.cpp/Ollama on Windows)

### 4.2 Connection Attempts
- Tested connectivity to Windows host port 8080
- Blocked by network restrictions
- Environment variable conflicts in WSL2

### 4.3 Model Switching
- Attempted multiple provider/model combinations:
  - Gemini 2.5 Flash
  - GPT-5-mini
  - Gemini 3.1 Flash Lite Preview (settled as operational model)

## 5. Diagnosis

WSL2-to-Windows networking requires explicit port forwarding and firewall configuration. Environment variable conflicts prevent clean client configuration. Remote provider fallback was more reliable than local connection in current setup.

## 6. Preliminary Assessment

Local llama.cpp connection not achievable in current session due to network restrictions. Manual configuration required outside of terminal tools.

## 7. Solution Summary

- Identified network path: WSL2 172.23.246.136 to Windows 172.23.240.1:8080
- Determined network restrictions block port 8080
- Switched to operational model: Gemini 3.1 Flash Lite Preview
- Decided to manually configure setup outside current tooling

## 8. Verification Plan

- Configure Windows firewall for port 8080 inbound
- Set up WSL2 port forwarding if needed
- Test llama.cpp server connectivity from WSL2

## 9. Pending Actions

- Manual network configuration on Windows host
- Verify llama.cpp server running on Windows port 8080
- Configure WSL2 environment variables cleanly

## 10. Recommendations

- Use netsh port forwarding for WSL2-to-Windows connections
- Isolate environment variables per project/session
- Prefer remote providers when local networking is unreliable
- Document network topology for future debugging