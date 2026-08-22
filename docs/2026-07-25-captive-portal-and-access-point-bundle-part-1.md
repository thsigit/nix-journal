# Captive Portal and Access Point Bundle - Part 1

*hostapd + dnsmasq + NAT*

**Date:** 2026-07-25  
**Author:** Codebot  
**Topic:** homelab, hostapd, NixOS, networking, firewall, troubleshooting, narrative  

---

## 1. Objective

Deploy WiFi access point on NixOS homelab with hostapd, dnsmasq DHCP/DNS, and NAT to internet.

## 2. Background

Hardware: Toshiba Portege R30-C (workstation profile) with wlp2s0 WiFi and enp0s31f6 Ethernet. NixOS 26.05 with services.hostapd.radios API. Plan: hostapd for AP, dnsmasq for DHCP/DNS, NAT from 192.168.4.0/24 via enp0s31f6.

## 3. Problem

Phone connected, got IP, WPA handshake complete, dnsmasq lease written, NAT counters incrementing, DNS queries resolved -- but phone showed "Connected, no internet." Apps failed, browser pages wouldn't load, but push notifications arrived.

## 4. Work Performed

### 4.1 Port 53 Conflict Resolution
systemd-resolved on 127.0.0.53:53 conflicted with dnsmasq on 0.0.0.0:53. Fixed with bind-interfaces + listen-address=192.168.4.1.

### 4.2 DNS Disabled Workaround
Removed port=0 workaround that killed DNS entirely.

### 4.3 Regulatory Domain
Country code unset (00), channels on passive scan. Noted but not root cause.

### 4.4 MTU and rp_filter Checks
MTU 1500 everywhere. rp_filter passing cleanly (71085 returns, 0 drops).

### 4.5 Namespace Simulation
Created veth pair + network namespace to simulate AP client. Ping failed -- expected since veth not wlp2s0, so NAT prerouting rule (iifname wlp2s0) never marked packets.

### 4.6 Firewall Chain Analysis Breakthrough
NixOS firewall has two paths: FORWARD (traffic through machine) and INPUT (traffic to machine). FORWARD chain was open:
```
nixos-filter-forward:
  iifname "wlp2s0" oifname "enp0s31f6" accept
  ct state related,established accept
```
NAT counters ticked because FORWARD worked.

But DNS queries to 192.168.4.1:53 hit INPUT chain, not FORWARD. NixOS INPUT restrictive by default: only loopback, RELATED/ESTABLISHED, SSH/HTTP/HTTPS/SMB, trustedInterfaces. DNS from wlp2s0 dropped silently.

### 4.7 Fix
Single line in firewall.nix:
```nix
networking.firewall.trustedInterfaces = [ "wlp2s0" ];
```
Treats all AP interface traffic as trusted -- no INPUT filtering. Dnsmasq gets all queries. Captive portal check passes.

## 5. Diagnosis

Focused on FORWARD path (NAT) but client DNS hits INPUT chain. Restrictive INPUT default drops local service traffic from AP interface.

## 6. Preliminary Assessment

NixOS firewall separation is correct for security but easy to overlook when debugging wrong chain.

## 7. Solution Summary

Added wlp2s0 to trustedInterfaces. DNS works. Captive portal passes. Phone online.

## 8. Verification Plan

Test client internet access. Verify DNS resolution from AP clients. Confirm captive portal detection.

## 9. Pending Actions

Document firewall chain behavior for future reference.

## 10. Recommendations

When debugging "connected, no internet" on NAT gateway, check both FORWARD and INPUT paths. Traffic to local services (DNS, DHCP, APIs) hits INPUT. NixOS trustedInterfaces is the correct integration point.
