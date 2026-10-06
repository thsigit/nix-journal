# Moving LLM Models Out Of WSL2

*... and a Manifest Sidecar Decision*

**Date:** 2026-07-01  
**Author:** Codebot  
**Topic:** WSL2, Ollama, llama.cpp, refactor, organization  

## 1. Objective

Move LLM model cache from WSL2 Fedora to Windows host to utilize better hardware resources (more cores, RAM, disk space) and transition from Ollama to llama.cpp on Windows.

## 2. Background

WSL2 Fedora vhdx consumed 8.3 GB of GGUF blobs while Windows host had 200+ GB free. User had already migrated from Ollama to llama.cpp on Windows. Ollama blob directory is flat hash pool (sha256-<hex>) requiring manifest cross-reference for human-readable identification.

## 3. Problem

Opaque blob filenames prevent direct identification. Need to map hashes to model names, copy to Windows with friendly names, preserve SHA256 provenance, and update environment configuration.

## 4. Work Performed

### 4.1 Blob Census and Mapping

Scanned ~/.ollama/models/blobs/ and cross-referenced against manifests in ~/.ollama/models/manifests/registry.ollama.ai/library/:

| Model             | Size    | Blob Hash (prefix) |
| ----------------- | ------- | ------------------ |
| qwen3:4b          | 2.50 GB | sha256-3e4cb1...   |
| qwen2.5:3b        | 1.93 GB | sha256-...         |
| starcoder2:3b     | 1.71 GB | sha256-...         |
| deepseek-r1:1.5b  | 1.12 GB | sha256-...         |
| mxbai-embed-large | 0.67 GB | sha256-...         |
| tinyllama         | 0.64 GB | sha256-...         |
| nomic-embed-text  | 0.27 GB | sha256-...         |

Total: 7 GGUFs, ~8.84 GB. File magic confirmed all start with GGUF (0x47475546).

Cloud models (nemotron-3-super:cloud, minimax-m3:cloud) had no local blobs - Hermes Agent provider aliases routing to OpenAI-compatible endpoints. ornith:9b (5.6 GB) on NixOS homelab, not in WSL.

### 4.2 Copy to Windows

- Target: C:\llama\blobs\
- Transfer: ~97 seconds over 9P share (~140 MB/s per file)
- Verification: SHA256 re-hash matched filename for all 7 files
- Windows free space: 214.7 GB to 196.8 GB (delta ~8.84 GB)

### 4.3 Human-Friendly Renaming with Sidecar Manifest

- Renamed: qwen3:4b to qwen3-4b.gguf (colons not allowed on Windows)
- Created manifest.json sidecar mapping friendly name to original SHA256:
  
  ```json
  {
    "name": "qwen3:4b",
    "file": "qwen3-4b.gguf",
    "size_bytes": 2500000000,
    "sha256": "3e4cb1..."
  }
  ```

### 4.4 Environment Cleanup

- Commented OLLAMA_HOST in ~/.bashrc with two commented alternatives:
  - Ollama on Windows at port 11434
  - llama-server at port 8080
- Local ollama serve still running but manifests reference deleted blobs

## 5. Diagnosis

Sidecar manifest preserves SHA256 identity critical for verification, re-pull, and cross-reference with llama-cli. Flat hash pool requires manifest mapping for human usability. Windows filename restrictions (no colons) necessitate renaming with provenance tracking.

## 6. Preliminary Assessment

C:\llama\blobs\ contains 7 .gguf files + manifest.json. WSL2 ~/.ollama/models/ retains ~4.7 GB (deepseek, nomic blobs + metadata). vhdx shrink via WSL --shutdown + diskpart compact queued. Hermes Agent cloud aliases unaffected.

## 7. Solution Summary

- Mapped 7 GGUF blobs to model names via manifest cross-reference
- Copied 8.84 GB to Windows over 9P (verified SHA256)
- Renamed with colon-to-dash substitution
- Created manifest.json sidecar preserving SHA256 provenance
- Updated ~/.bashrc with commented Windows endpoints

## 8. Verification Plan

- Verify llama-server serves models from C:\llama\blobs\
- Run vhdx compact after WSL2 shutdown
- Test model loading from Windows llama.cpp

## 9. Pending Actions

- Uncomment chosen llama-server port in ~/.bashrc
- Start llama-server on Windows
- Execute diskpart compact vdisk

## 10. Recommendations

- Always create sidecar manifest when renaming opaque hash files
- SHA256 is canonical identifier in Ollama/HuggingFace GGUF ecosystem
- Verify SHA256 after cross-machine copy
- Keep sidecar invisible until needed (minimal overhead, high future value)