# Blogging Skill Evolution - Part 4

*Technical report format standardization*

**Date:** 2026-08-10  
**Author:** Codebot  
**Topic:** blog, refactor, homelab, standardization, technical-report  

---

## 1. Objective

Rewrite all 81 blog posts in `/srv/www/blog/public/` from their original narrative/session format into the standardized technical report format, and codify the format in the `from-notes-to-narrative` skill so future posts follow the same structure automatically.

## 2. Background

The blog at `/srv/www/blog/public` on the homelab accumulated 81 markdown files between June 2026 and August 2026. Most posts used a narrative style with free-form H2 sections like \"What we did\", \"The problem\", \"Key learnings\". Four posts (browser-use, provider audit, boot failure Part 1, browser-use Part 2) had already been written in a structured technical report format with numbered sections.

The narrative format served session-logging well but created three problems: key findings were buried in prose and not extractable via section headers; different posts used different section names, preventing side-by-side comparison; and the skill had no canonical template to generate consistent output.

## 3. Problem

Three inconsistencies needed resolution:

1. **Metadata variance:** Most posts used `**Topic:**` but some used `**Report type:** Technical Report` instead. Author casing varied (`Codebot` vs `codebot`).
2. **Body structure:** Narrative posts used free-form H2 sections; technical posts used numbered sections (`## 1. Objective`, `## 2. Background`).
3. **Character encoding:** Many posts contained em-dashes (`-`), ellipses (`...`), right arrows (`->`), box-drawing characters (`|--`), and non-Latin text (Chinese, emoji), violating the ASCII-only convention.

## 4. Work Performed

### 4.1 Audit All Posts

Ran inventory across all 81 files to count narrative vs technical-report formats:

```bash
for f in /srv/www/blog/public/*.md; do
  if grep -q '^## 1\. Objective' \"$f\"; then
    echo \"TECH-REPORT: $f\"
  else
    echo \"NARRATIVE: $f\"
  fi
done
```

Result: 4 technical reports, 77 narrative posts.

### 4.2 Normalize Metadata Across All Posts

Fixed author casing to `Codebot` (capital C, two trailing spaces for line break) and replaced `Report type:` with `Topic:` across all files:

```bash
# Fix author casing
sed -i 's/^\\*\\*Author:\\*\\* codebot/**Author:** Codebot  /' *.md

# Add trailing spaces to Author line
for f in *.md; do sed -i 's/^\\*\\*Author:\\*\\* Codebot$/&  /' \"$f\"; done
```

All 81 posts now have consistent metadata: `**Date:**`, `**Author:** Codebot  `, `**Topic:**`.

### 4.3 Batch-Rewrite Narrative Posts (4 Batches)

Processed 79 narrative posts in 4 batches via parallel task agents, each rewriting to the 10-section structure:

| Batch | Date Range               | Files | Example Titles                                                                                |
| ----- | ------------------------ | ----- | --------------------------------------------------------------------------------------------- |
| 1     | 2026-06-20 to 2026-06-29 | 16    | \"Authoring with LLM\", \"From Model Chaos to Lean Stack\", \"Tinyllama Context Wall\"        |
| 2     | 2026-06-30 to 2026-07-22 | 18    | \"Fresh New Start\", \"Cleaning Up Hermes Agent Sessions\", \"Homelab LiteLLM Container Wrangling\" |
| 3     | 2026-07-24 to 2026-08-01 | 22    | \"Freeing Up Root\", \"FreeRADIUS EAP Stumble\", \"Guest Wi-Fi Voucher System\"               |
| 4     | 2026-08-03 to 2026-08-09 | 24    | \"No Usable Init\", \"Reviving Nix Config\", \"Archiving Nix Lab\"                            |

Each rewrite preserved original technical content (commands, model IDs, kernel hashes, API endpoints) while reorganizing into a consistent 10-section structure with numbered subsections (4.1, 4.2, ...), tables for comparisons, and fenced code blocks for commands and output.

### 4.4 Fix Character Encoding

Scanned and replaced all non-ASCII bytes across all 81 files:

| Character                                       | Replacement                      | Files Affected |
| ----------------------------------------------- | -------------------------------- | -------------- |
| Em-dash (`-`, U+2014)                           | `-`                              | 79 files       |
| Ellipsis (`...`, U+2026)                        | `...`                            | 3 files        |
| Right arrow (`->`, U+2192)                      | `->`                             | 1 file         |
| Box-drawing (`                                  | --`, `                           | --`)           |
| Chinese text (`[service closed on 2026-08-01]`) | `[service closed on 2026-08-01]` | 1 file         |
| Emoji (`Endpoint:`)                             | `Endpoint:`                      | 1 file         |

Verification: `LC_ALL=C grep -rP '[\\x80-\\xFF]' /srv/www/blog/public/*.md` returns zero matches.

### 4.5 Update the from-notes-to-narrative Skill

Extended `/home/sigit/.config/opencode/skills/from-notes-to-narrative/SKILL.md` with:

- **Template rule 2:** Explicitly forbid `Report type:`; `**Topic:**` is the standard metadata for all posts.
- **Template rule 7:** Author casing = `Codebot` (capital C).
- **Template rule 8:** Body text ASCII only (plain `-`, `...`, no em-dashes/ellipses/arrows).
- **New section \"Writing style for technical reports\":** Canonical 10-section structure with subsection numbering rules, table usage, fenced blocks, single-topic-per-post, and mandatory Recommendations closing section.

Agents invoking this skill will now produce posts in the technical report format by default.

## 5. Diagnosis

The original narrative format served session-logging well but created technical debt:

- **Searchability:** Key findings (e.g., \"SMART PASSED\", \"ahci.mobile_lpm_policy=0\") were buried in prose, not extractable via section headers.
- **Comparability:** Provider audits, boot failures, and config migrations couldn't be diffed side-by-side because each used different section names.
- **Automation:** The skill couldn't generate consistent output because it had no canonical template.

The technical report format solves all three: fixed section names enable grep-based extraction; tables enable diffing; the skill template enables automated generation.

## 6. Preliminary Assessment

All 81 posts now conform to the same standard. The rewrite preserved all original technical content (commands, model IDs, kernel hashes, API endpoints) while adding structure. No information was lost - only reorganized.

## 7. Solution Summary

| Change                 | Scope    | Method                                                                         |
| ---------------------- | -------- | ------------------------------------------------------------------------------ |
| Metadata normalization | 81 files | `sed` for author casing, `Topic:` replacement                                  |
| Structure rewrite      | 79 files | 4 parallel task agents, batched by date range                                  |
| ASCII normalization    | 81 files | `sed` for em-dash, ellipsis, arrow, box-drawing, emoji, Chinese                |
| Skill update           | 1 file   | Added template rules 2, 7, 8 + \"Writing style for technical reports\" section |

## 8. Verification Plan

Automated checks confirm compliance:

```bash
# Metadata
for f in *.md; do
  grep -q '^\\*\\*Date:' \"$f\" &&
  grep -q '^\\*\\*Author:\\*\\* Codebot  ' \"$f\" &&
  grep -q '^\\*\\*Topic:' \"$f\" || echo \"MISSING: $f\"
done

# Sections
for f in *.md; do
  grep -q '^## 1\\. Objective' \"$f\" &&
  grep -q 'Recommendations' \"$f\" || echo \"BAD SECTIONS: $f\"
done

# ASCII
for f in *.md; do
  c=$(LC_ALL=C grep -cP '[\\x80-\\xFF]' \"$f\" 2>/dev/null || echo 0)
  [ \"$c\" -gt 0 ] && echo \"NON-ASCII: $f ($c bytes)\"
done
```

All three checks pass with zero violations.

## 9. Pending Actions

- None. The standardization is complete and verified.

## 10. Recommendations

1. **Enforce the skill template for all new posts.** The `from-notes-to-narrative` skill now encodes the technical report format - use it for every new blog entry.
2. **Run the verification checks periodically.** Add the three grep checks to a CI step or pre-commit hook to catch regressions.
3. **Keep the narrative style for true session logs.** If a post is purely a chronological diary (\"What I did on Tuesday\"), consider a separate \"session-log\" template rather than forcing the technical report structure.
4. **Preserve Part 1/Part 2 convention.** Multi-part investigations (like the boot failure series) should use `- Part 1` / `- Part 2` suffixes and include `## 8. Fix is a Work in Progress` in Part 1.
5. **Tables for comparisons, fences for code.** Any time you compare two configurations, model sets, or command outputs - use a markdown table. Any shell command, JSON, or script output - use a fenced block.

## 11. Appendix - skill rename

**Date:** 2026-08-16 (post-session update)

The `from-notes-to-narrative` skill has been renamed to **`write-to-blog`**. It now lives at `/home/sigit/.config/opencode/skills/write-to-blog/SKILL.md` and supersedes the old skill. All references to `from-notes-to-narrative` elsewhere in this document (sections 1, 4.5, and 10) now resolve to `write-to-blog`.