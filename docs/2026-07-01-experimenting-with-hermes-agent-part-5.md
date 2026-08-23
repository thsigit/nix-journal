# Experimenting with Hermes Agent - Part 5

*A Manual Check That Caught a Rogue Blob*

**Date:** 2026-07-01  
**Author:** Codebot  
**Topic:** Hermes Agent, Ollama, WSL2, safety, secondary-session, model-cleanup  

## 1. Objective

Safely clean up Ollama model blobs in WSL2 by cross-referencing a kill list against actual disk usage and manifest references, preventing accidental deletion of active or needed models.

## 2. Background

Main session was blocked on a destructive cleanup decision. A secondary session was opened to perform manual verification before any deletion. The kill list contained 32 blob hashes targeting ~/.ollama/models/blobs/ directory.

## 3. Problem

Blind deletion of 32 blobs risked: (1) deleting qwen3:4b (2.5 GB) before confirming Windows rsync completion, (2) deleting mxbai-embed-large (638 MB) and tinyllama (608 MB) weight files prematurely, (3) deleting active minimax-m3:cloud config blob (362 bytes) mid-session.

## 4. Work Performed

### 4.1 Blob Census

- Listed ~/.ollama/models/blobs/: 35 files on disk, 16 matched kill list
- Walked 10 manifests in ~/.ollama/models/manifests/
- Built blob-to-model reference map from manifest JSON (config.digest, layers[].digest)
- Fixed separator bug: manifest JSON uses sha256: (colon), filenames use sha256- (dash)

### 4.2 Classification Results

| Blob Count | Category            | Models                                                                                    |
| ---------- | ------------------- | ----------------------------------------------------------------------------------------- |
| 15         | Safe to delete      | qwen3:4b, qwen2.5:3b, tinyllama:latest, mxbai-embed-large:latest, nomic-embed-text:latest |
| 1          | Active - preserve   | minimax-m3:cloud (currently serving this session)                                         |
| 16         | No-op (not on disk) | Various                                                                                   |

### 4.3 User Decision

Presented 4 options: skip all, delete orphans (0), delete non-preserve (15), delete all including active. User selected option 3 (delete 15 non-preserve).

### 4.4 Execution

- Re-verified cross-reference: 15 safe, 1 carved out
- Ran rm -v on 15 deletions with pre-deletion ls -la showing sizes
- Post-deletion verification: 15 removed confirmations, minimax-m3:cloud config intact (original timestamp Jun 9 18:44), 20 blobs remaining, 4.7 GB on disk

## 5. Diagnosis

Manifest walking revealed true blob ownership. Separator mismatch (colon vs dash) is a recurring paper cut. Active model config deletion would truncate session log. Cross-machine copy must complete before source deletion.

## 6. Preliminary Assessment

3.81 GB freed, 4.7 GB remaining. Remaining models not in kill list: starcoder2:3b (1.7 GB), qwen2.5:3b (1.9 GB), deepseek-r1:1.5b (1.1 GB), nomic-embed-text (274 MB). Cloud models (minimax-m3:cloud, nemotron-3-super:cloud) configs intact. Local ornith:9b not in manifest tree.

## 7. Solution Summary

- Cross-referenced 32-hash kill list against 35 disk blobs and 10 manifests
- Classified 15 as safe, 1 as active (preserved), 16 as no-ops
- Executed targeted deletion of 15 blobs (3.81 GB)
- Preserved active minimax-m3:cloud config
- Verified post-state: 20 blobs, 4.7 GB, active model undisturbed

## 8. Verification Plan

- Confirm minimax-m3:cloud continues serving session
- Verify remaining models functional
- Re-issue ornith:9b pull in fresh session

## 9. Pending Actions

- Copy remaining models to Windows before next cleanup
- Run WSL --shutdown + diskpart compact for vhdx shrink
- Create skill for "blob kill list classification" pattern

## 10. Recommendations

- Always cross-reference kill lists against manifests before deletion
- Note: manifest JSON uses sha256: (colon), filenames use sha256- (dash)
- Complete cross-machine copies before source deletion
- Secondary session pattern effective for destructive operations requiring human judgment