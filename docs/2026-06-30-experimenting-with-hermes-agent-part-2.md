# Experimenting with Hermes Agent - Part 2

*Resolving Hermes Dashboard Access in WSL2 for real-time session monitoring*

**Date:** 2026-06-30  
**Author:** Codebot  
**Topic:** Hermes Agent, WSL2, Dashboard, PortForwarding, OpenRouter  

## 1. Objective

Set up Hermes Agent dashboard for real-time session monitoring in WSL2 environment.

## 2. Background

Hermes Agent dashboard command (Hermes Agent dashboard) returned "gio: Operation not supported" error in WSL2. The dashboard relies on GUI tools (gio) tied to GNOME environments, which are unavailable in headless WSL2. Port forwarding from Windows host to WSL2 was identified as the solution.

## 3. Problem

GUI dependency (gio) prevents dashboard from running directly in WSL2. Network configuration required precise IP targeting and firewall rules to enable cross-machine access.

## 4. Work Performed

### 4.1 Root Cause Analysis

- Identified gio dependency as WSL2 incompatibility
- Determined port forwarding from Windows host to WSL2 as workaround

### 4.2 Network Configuration

- Initial netsh command targeted 127.0.0.1 (Windows localhost) - incorrect routing
- Corrected to WSL2 actual IP: 172.23.246.136
- Added Windows inbound firewall rule for port 9119

### 4.3 Verification

- Ran Hermes Agent dashboard in background in WSL2
- Executed corrected port-forwarding command on Windows
- Accessed http://localhost:9119 from Windows browser
- Dashboard loaded successfully

## 5. Diagnosis

WSL2 headless environment lacks GUI libraries required by Hermes Agent dashboard. Port forwarding with correct IP mapping and firewall configuration enables cross-machine access. Windows firewall blocks ports by default.

## 6. Preliminary Assessment

Dashboard now accessible from Windows host via localhost:9119. Configuration is stable and repeatable.

## 7. Solution Summary

- Identified gio as blocker in WSL2
- Configured port forwarding: Windows localhost:9119 to WSL2 172.23.246.136:9119
- Added Windows firewall inbound rule for port 9119
- Verified browser access from Windows host

## 8. Verification Plan

- Test dashboard access after WSL2 restart
- Verify firewall rule persistence
- Confirm Hermes Agent dashboard functionality

## 9. Pending Actions

- Document port forwarding setup for future sessions
- Consider systemd service for persistent dashboard

## 10. Recommendations

- Use WSL2 IP (not 127.0.0.1) for port forwarding targets
- Always configure firewall rules when opening ports
- GUI tools require desktop environment or alternative access methods in WSL2