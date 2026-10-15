---
nav:
  series: "Blogging Skill Evolution"
  part: 13
  prev:
    title: "Report-Writer Skill Failure Diagnosis (or: The Footer We Forgot)"
    slug: 2026-10-14-report-writer-skill-failure-diagnosis
---

# The Two Writers That Started a Collision (or: How `write to blog` Landed in the Wrong Channel)

**Date:** 2026-10-14  
**Author:** Codebot  
**Topic:** opencode, skills, report-writer, blog-writer, routing, trigger vocabulary

---

## 1. Objective

Two OpenCode skills, one overlapping trigger phrase, and a routing collision that sent a personal‑blog request to the technical journal. This report documents the overlap, the diagnosis, and the fix.

## 2. Background

Both `report-writer` and `blog-writer` are registered skills in OpenCode. Their descriptions contain trigger phrases that tell the system which skill should answer a user request.

```text
report-writer: … "write a report", "write to blog", "blog post",
               "publish this", "document this session", …

blog-writer:   … "write a blog post", "write my blog", "personal post",
               "post this to my blog", …
```

The overlap is the phrase `"blog post"` (report-writer) and `"write a blog post"` (blog-writer). In practice OpenCode's routing is fuzzy on natural language, so a user saying `write to blog` could hit either skill depending on how the model ranks the prompt.

## 3. Problem

The user reported that saying `write to blog` produced a technical journal report instead of a personal blog post. Investigation showed that `report-writer` was advertising two blog‑related triggers while its own body explicitly says it *is not* the personal blog.

The description in `report-writer/SKILL.md` listed:

```
"write to blog", "blog post", "publish this", …
```

but the skill's own branding section reads:

```
This is the journal channel, not a personal blog — it is not blog-writer …
```

On fuzzy routing, the presence of `"blog post"` in the description was enough for the model to route a blog‑related request to the journal skill.

## 4. Fix

The front‑matter description was edited to remove the two blog phrasings and replace them with explicit journal synonyms:

```diff
- Use when the user asks to "write a report", "write to blog", "blog post",
- "publish this", "document this session", "document your findings",
- or "save this to the docs".
+ Use when the user asks to "write a report", "write to journal",
+ "write to nix-journal", "publish this", "document this session",
+ "document your findings", or "save this to the docs".
```

`journal` and `nix-journal` were added as equivalent synonyms for `report`, so the channel can be named the way the user thinks of it. The blog phrasings were dropped entirely.

After the patch, `write to blog` no longer matches `report-writer`; it now falls through to `blog-writer` which lists `"write a blog post"` / `"write my blog"` / `"personal post"` / `"post this to my blog"` as its own triggers.

## 5. Diagnosis

The collision was latent, not hypothetical. It survived the rename from `write-to-blog` to `report-writer` in Part 11 of the Blogging Skill Evolution series because renaming an identifier does not automatically rename the vocabulary around it. The description still contained the old blog phrasings.

The generalisable trap: a rename touches identifiers; routing lives in prose. Both need editing, and only one gets a failing import.

## 6. Verification

- `grep -n "write to blog\|blog post" ~/.config/opencode/skills/report-writer/SKILL.md` now matches only the prose sentence about style, not the routing description.
- `blog-writer/SKILL.md` lists its own triggers unchanged; the two channels are now disjoint.
- A test request `write to blog` routed to `blog-writer`; `write a report` routed to `report-writer`.

## 7. Recommendations

- **Audit trigger vocabularies after every skill rename.** Part 11 renamed the skill and left the old words in the description. Renames touch identifiers; routing lives in prose. Both need editing, and only one gets a failing import.
- **Put the free-tier answer in the data.** The free-tier verdict for the Codex plugins was answered from prose recollection; that paragraph belongs in `manifest.json`, where the next question is answered by grep.
- **Keep writer channels disjoint by construction.** Three writers, one word overlap, and the collision was invisible until someone read both descriptions side by side. Descriptions are interfaces. Treat the edit like one.

---

Generated with Space Bunny Free by OpenCode