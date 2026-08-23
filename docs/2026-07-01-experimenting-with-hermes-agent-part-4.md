# Experimenting with Hermes Agent - Part 4

*Replacing the Gemini API Key Without Taking Down the Main Tab*

**Date:** 2026-07-01  
**Author:** Codebot  
**Topic:** Hermes Agent, Gemini, api-key, troubleshooting, secondary-session  

## 1. Objective

Replace exhausted Gemini API key without disrupting main session running in another tab.

## 2. Background

Main session mid-swap to Alibaba Coding Plan model. Secondary session opened to fix Gemini API key returning HTTP 429 RESOURCE_EXHAUSTED for hours. Hermes auth pool contained two Gemini keys, both rate-limited.

## 3. Problem

Gemini free tier hard ceiling (limit: 0 for generativelanguage.googleapis.com/generate_content_free_tier_requests on gemini-2.0-flash). Connection was functional (177ms probe to generativelanguage.googleapis.com), but quota exhausted. Fallback chain should have routed around but wasn't functioning as expected.

## 4. Work Performed

### 4.1 Diagnosis

- Inspected ~/.hermes/auth.json: both Gemini credentials marked exhausted, error code 429
- Network probe: curl to Google API host returned 177ms, HTTP 400 (expected with placeholder key)
- Identified: free tier limit: 0 is hard ceiling, not transient spike

### 4.2 Key Replacement

- User edited ~/.hermes/auth.json manually: swapped old AIzaSy...7J44 for new key (tail ...stUg)
- Confirmed old key deleted from Google console
- User preference: execute setup commands directly, not via chat transcript

### 4.3 Auth State Reset

- Ran hermes auth list: pool still showed stale exhaustion flags (last_error_* fields)
- Ran hermes auth reset Gemini to clear flags
- Clarified: hermes auth status Google returns "logged out" for API-key providers (normal, means no OAuth session, not "no credentials")

### 4.4 Verification

- Fixed Hermes Agent chat flag usage: -q/--query is single-shot flag, not positional
- Working command: Hermes Agent chat -q "reply with the single word PONG" -m google/gemini-2.0-flash -Q
- Result: PONG - new key live and responding

### 4.5 Memory Capture

- Saved memory entry capturing resolution for future sessions

## 5. Diagnosis

Misdiagnosis: "connection issue" was actually quota exhaustion. Key swap works because new key has fresh quota bucket. Free tier limit: 0 is hard ceiling. CLI status "logged out" for API-key providers differs from "no credentials."

## 6. Preliminary Assessment

New Gemini key operational. Fallback chain should now function. Two loose ends remain.

## 7. Solution Summary

- Diagnosed quota exhaustion (not connection failure)
- User replaced API key in auth.json manually
- Reset auth flags via hermes auth reset Gemini
- Corrected Hermes Agent chat flag syntax
- Verified: PONG response

## 8. Verification Plan

- Test fallback chain under load
- Monitor for recurring 429 on new key

## 9. Pending Actions

- Update or remove credential #2 (source: env:GOOGLE_API_KEY) to prevent dead key shadowing
- Main tab still mid-swap to glm-5

## 10. Recommendations

- Rotate keys on free tier limit: 0, do not chase network issues
- Distinguish "logged out" (no OAuth session) from "no credentials" in CLI status
- Clear auth pool flags after key rotation via hermes auth reset