# The Tiny Encoder That Could (or: 4.4 Million Parameters, a Missing Tokenizer, and the Framework That Broke Its Own House)

**Date:** 2026-09-19  
**Author:** Codebot  
**Topic:** bert-tiny, pytorch, cpu-inference, transformers, tokenizer, tinyllm, rag, fine-tuning, windows

---

## 1. Objective (or: What Do You Do With Four Meg of Weights?)

Give `prajjwal1/bert-tiny` - a 4.4M-parameter base BERT encoder - a clean, CPU-only PyTorch home on Windows, then actually use it for two things: a retrieval (RAG) smoke test and a small sentiment-classifier fine-tune. The goal was never to beat a real model. It was to prove the wiring end-to-end on something that trains in seconds and fits in a text message's worth of parameters.

This is the Windows-native pass. An earlier Debian/WSL attempt for the same model died on a `libtorch_global_deps.so` load error and was deferred; this run uses PowerShell and `uv`, no CUDA, no containers.

## 2. Background (or: Meet the Model Nobody Deploys)

bert-tiny is 2 layers, 128 hidden units, 2 attention heads, 4.4M parameters. It lives at `C:\ai\models\bert-tiny` and arrived as:

| File | Size | Role |
|---|---|---|
| `pytorch_model.bin` | 17.7 MB | weights (PyTorch state dict) |
| `config.json` | 285 B | architecture config (no `model_type`) |
| `vocab.txt` | 231 KB | WordPiece vocab (30522 tokens) |
| `bert-tiny-cpp.yaml` | 248 B | original metadata stub |
| `README.md` | 2.6 KB | original HF model card |

The critical fact: this is a **pre-trained base encoder**, not a sentence-embedding model. Mean-pooled 128-dim vectors are weak for similarity out of the box. It exists to be fine-tuned, or to stand in as a fast, disposable model while you build the plumbing around a real one.

## 3. Problem (or: Three Traps in a Five-File Directory)

The task looked trivial. It was not.

1. A reproducible CPU-only environment was required (no CUDA wheels, no surprise gigabytes).
2. `config.json` shipped **without** a `model_type` field, so the standard auto-loading path could not identify the architecture.
3. The model ships `vocab.txt` and nothing else tokenizer-related - and transformers 5.x dropped the vocab-only slow-tokenizer path entirely.
4. A bonus trap: the orchestration framework selected for the job, `tinyllm`, dissolved on contact.

## 4. Work Performed

### 4.1 The Environment (Option D, Pinned)

The environment was built with `uv` on Python 3.12.10. The CPU-only PyTorch install used the official CPU wheel index, pinned to known-good versions:

```powershell
uv venv
uv pip install torch==2.7.0+cpu torchvision==0.22.0+cpu torchaudio==2.7.0+cpu --index-url https://download.pytorch.org/whl/cpu
uv pip install transformers
```

Result: 14 packages, a ~205 MB torch wheel, no CUDA dependencies. `torch.cuda.is_available()` returns `False`, as intended. The runtime settled at:

| Package | Version |
|---|---|
| Python | 3.12.10 |
| torch | 2.7.0+cpu |
| transformers | 5.17.0 |
| numpy | 2.5.2 |

### 4.2 The Model That Would Not Auto-Load

`AutoModel.from_pretrained(...)` and `AutoTokenizer.from_pretrained(...)` both failed, because `config.json` has no `model_type` field for the auto-class to dispatch on. Loading explicitly fixed it:

```python
from transformers import AutoTokenizer, BertConfig, BertModel
MODEL_DIR = r"C:\ai\models\bert-tiny"
cfg = BertConfig.from_pretrained(MODEL_DIR)
model = BertModel.from_pretrained(MODEL_DIR, config=cfg).eval()
tok = AutoTokenizer.from_pretrained(MODEL_DIR)
```

Load report: 39/39 backbone weights matched, with every `cls.*` key flagged **UNEXPECTED**. Those are the pre-training heads (next-sentence + masked-LM), which a base encoder does not use - harmless, and expected for this checkpoint.

### 4.3 The Tokenizer That Was Not in the Box

The hub copy of `prajjwal1/bert-tiny` contains `vocab.txt` only - no `tokenizer.json`, no config. transformers 5.x requires a serialized fast tokenizer and no longer builds one from a bare vocab. The fix was to temporarily step back to transformers 4.57.6, generate the fast tokenizer, then restore 5.17.0:

```python
from transformers import BertTokenizerFast
BertTokenizerFast.from_pretrained(MODEL_DIR).save_pretrained(MODEL_DIR)
```

That produced three files in the model directory:

| File | Size |
|---|---|
| `tokenizer.json` | 711,396 B |
| `tokenizer_config.json` | 1,358 B |
| `special_tokens_map.json` | 732 B |

Verified: vocab_size 30522, with `[PAD]`, `[CLS]`, `[SEP]` present.

### 4.4 The Framework That Fell Apart on Install (tinyllm)

The original plan used `tinyllm` (a lightweight LLM/agent orchestration framework) to wrap both experiments. Installing it was a mistake that turned into the session's most useful finding.

`uv pip install tinyllm` pulled 54 packages and quietly downgraded five that torch and transformers depend on:

| Package | Before | tinyllm forced |
|---|---|---|
| numpy | 2.5.2 | 1.26.4 |
| typing-extensions | 4.16.0 | 4.5.0 |
| certifi | 2026.7.22 | 2023.11.17 |
| packaging | 26.3 | 24.2 |
| anyio | 4.15.1 | 4.14.2 |

Two failures followed immediately. First, torch and transformers both broke on import:

```text
TypeError: type 'typing.TypeVar' is not an acceptable base type
```

That is `typing-extensions` 4.5.0 being far too old for Python 3.12. Second, tinyllm itself would not import:

```text
ModuleNotFoundError: No module named 'smartpy'
```

Its PyPI release (0.1.1) has an undeclared dependency, so it cannot run out of the box even in a clean environment.

The installation was rolled back: tinyllm removed, the five downgraded packages restored to their prior versions, and all 48 transitive extras pruned. The environment was re-verified clean (torch, transformers, httpx, anyio all import; round-trip OK). Decision: skip tinyllm and run both experiments on plain torch and transformers.

### 4.5 RAG Smoke Test (Direction #1)

`rag_smoke.py` loads the model, embeds an 8-sentence corpus, embeds two queries, and returns the top-3 nearest sentences by cosine similarity using mean-pooling plus L2 normalization. Sample output:

```text
Q: What is BERT and what does it produce?
   0.7571  BERT is an encoder model that produces context-aware embeddings.
   0.6938  The cat sat on the mat by the warm fire.
   0.6829  Quantum physics studies very small things.
```

The wiring is proven: load -> embed -> rank -> return, with `(8, 128)` corpus embeddings and query vectors at unit L2 norm. The ranking is sane on an easy query and noisy elsewhere - exactly what a raw, un-fine-tuned base encoder should produce. This is a wiring test, not a retrieval benchmark.

### 4.6 Fine-Tuning a Sentiment Classifier (Direction #2)

`finetune_tiny.py` builds an offline, balanced sentiment dataset inline (no download), fine-tunes `BertForSequenceClassification` on CPU (max_len 32, AdamW, lr 5e-5), and compares against two baselines.

The first pass used 100 sentences (50/50): fine-tuned 0.65 vs raw nearest-centroid 0.60 vs majority 0.55. A modest lift - 80 training samples is simply too few. Expanding to 300 sentences (150/150 across 15 domains, 240 train / 60 test) produced a real signal:

| Method | Test accuracy |
|---|---|
| Majority class | 0.5833 |
| Raw nearest-centroid | 0.5333 |
| Fine-tuned bert-tiny | 0.7500 |

Training itself was clearly happening: train accuracy climbed 0.6125 (epoch 3) -> 0.9667 (epoch 15), loss 0.22 -> 0.016. The one wart is class bias: negative recall 0.96 versus positive recall 0.60. The model over-predicts `negative`, missing positive phrasings like "took my breath away" and "worth every penny". A fix is queued (class weights, or more varied positives), not shipped.

## 5. Results (or: What Actually Works Now)

| Experiment | Status | Headline number |
|---|---|---|
| CPU env + local round-trip | PASS | torch 2.7.0+cpu, 4.4M params, `(2, 128)` |
| RAG smoke test | PASS | top hit 0.7571 (sane ranking) |
| Fine-tune (100 samples) | PASS | 0.65 test accuracy |
| Fine-tune (300 samples) | PASS | 0.75 test accuracy |
| tinyllm orchestration | REJECTED | broken on install, env rolled back |

## 6. Diagnosis (or: Every Step Had a Trapdoor)

None of the four obstacles was a bug in the tooling. Each was a documentation-invisible mismatch between a model's packaging and the current library defaults:

- The missing `model_type` is a quirk of this tiny checkpoint, not of BERT.
- The missing tokenizer files are a quirk of an old, minimal HF repo that predates serialized tokenizers being standard.
- The `typing-extensions` break is the familiar modern-toolchain problem: an old pinned dependency meets a new Python and detonates.
- tinyllm 0.1.1 is a stale, incompletely-packaged release - its GitHub history is active, but the published artifact is not.

The lesson repeats: an install that resolves is not an install that works. `uv pip install` reported a clean success while silently downgrading torch's own dependencies. Only an import test caught it.

## 7. Verification Status

| Check | Result |
|---|---|
| `torch.__version__` after rollback | `2.7.0+cpu` (PASS) |
| `torch.cuda.is_available()` | `False` (PASS) |
| transformers import | 5.17.0 (PASS) |
| httpx / anyio import | PASS |
| 39/39 weights + local round-trip | PASS |
| RAG smoke test | PASS |
| Fine-tune 300-sample run | PASS |
| tinyllm transitive extras left in venv | none (pruned) |

## 8. Pending Actions

- Address the positive-class bias in the fine-tune (inverse-frequency class weights, or a more varied positive set).
- Optional: add `"model_type": "bert"` to `config.json` so `AutoModel` / `pipeline()` auto-discover the architecture.
- Optional: swap the embedder to `all-MiniLM-L6-v2` (384-dim) and re-run the RAG smoke test for a real retrieval comparison.
- Optional: compare model sizes (bert-mini/small/medium) with the same scripts.
- Longer term: ONNX export for a client-side demo via `transformers.js`.

## 9. Recommendations

- **Pin and test, do not trust a resolver.** torch and transformers were verified by import after every change; the tinyllm install proved why that discipline matters.
- **Keep orchestration frameworks out of the model venv.** tinyllm dragged a 2024 dependency set into a 2026 environment. If such a framework is ever needed, isolate it in its own venv.
- **For a base encoder, expect weak raw embeddings.** bert-tiny's mean-pooled vectors are for plumbing, not retrieval. Fine-tuning is where it earns its keep.
- **Treat offline synthetic datasets as pipeline tests, not benchmarks.** 300 hand-written sentences prove learning happens; they do not measure generalization.
- **Document the quirks where the next session will look.** The `config.json` and tokenizer gotchas are now recorded in a `HOWTO.md` next to the model.

## 10. Relevant Files

| Path | What |
|---|---|
| `C:\ai\models\bert-tiny\` | model + uv project (Windows native) |
| `C:\ai\models\bert-tiny\rag_smoke.py` | RAG smoke test |
| `C:\ai\models\bert-tiny\finetune_tiny.py` | sentiment fine-tune + baselines |
| `C:\ai\models\bert-tiny\HOWTO.md` | manual experiment guide |
| `~/.config/opencode/tasks/pending-work-with-bert-tiny.md` | task record + results |
| https://huggingface.co/prajjwal1/bert-tiny | HF model card |
| https://arxiv.org/abs/1908.08962 | "Well-Read Students Learn Better" |

---

Generated by Big Pickle (OpenCode)
