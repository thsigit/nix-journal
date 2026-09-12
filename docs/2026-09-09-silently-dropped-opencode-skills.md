# Skills That Load, and One That Didn't (or: How YAML 2.x Silently Ate My Research Skill)

**Date:** 2026-09-09  
**Author:** Codebot  
**Topic:** opencode, skills, yaml, frontmatter, debugging, loader

---

## 1. Objective (or: Where Did My Skill Go?)

A freshly written `general-research` skill was silently absent from every opencode session. No error on the screen, no tutorial moment, no "skill not found" toast - it just wasn't there. The skill list showed the other 20 skills dutifully lined up, and `general-research` (and later `language-learning`) were nowhere to be seen.

The goal: find out why skills disappear without a trace, fix them, and make the fix reproducible so it never eats a skill again.

## 2. Background (or: Skills Are Just Markdown With a Mood Ring)

An opencode skill is a directory with a `SKILL.md`: YAML frontmatter (name, description, metadata) on top, markdown workflow below. The loader scans `skills.paths` and registers whatever parses. The frontmatter is parsed with the `yaml` package - version 2.9.0 in this opencode install (1.18.30).

The innocent-looking prize: a `general-research` skill whose frontmatter looked like this:

```yaml
metadata:
  argument-hint: "<subject> [scope: broad|narrow] [depth: school|general|university] [format: report|blog|summary]"
```

Wait, that's the fixed version. The broken version had that value **unquoted**:

```yaml
argument-hint: <subject> [scope: broad|narrow] [depth: school|general|university] [format: report|blog|summary]
```

Which is exactly the kind of line that looks harmless, parses in PyYAML happily, and then throws a party under yaml 2.x.

## 3. Problem (or: Silence Is Not a Valid Diagnostic)

Skills fail silently by design. The loader logs the parse failure to the opencode log and moves on; the user only sees the skill's absence later, in a session that needed it. Combined with a parser that changed behavior across major versions, "it just vanished" becomes the entire symptom description. No crash, no red text, no line number.

Reproducing it was the first real step:

```bash
$ node -e "console.log(require('/home/sigit/.opencode/node_modules/yaml/package.json').version)"
2.9.0

$ node -e "
const YAML = require('/home/sigit/.opencode/node_modules/yaml');
try { YAML.parse('description: <subject> [scope: broad|narrow] [depth: school|general]'); }
catch(e){ console.log(e.message.split('\n')[0]); }
"
Nested mappings are not allowed in compact mappings at line 1, column 14
```

There it is. Inside an *unquoted* flow context, the `[`-`]` block reads as a YAML collection - and a single-line `key: value` mapping cannot *contain* a nested mapping in compact form, so the parser faults the entire document. One unquoted bracket sequence took the whole skill down with it.

## 4. Work Performed

### 4.1 Diagnosed via the Log (or: The Quiet Failure Had a Paper Trail)

`~/.local/share/opencode/log/opencode.log` records the loader's judgment even when the TUI doesn't. Grepping for the skill name surfaced the parse error the UI swallowed. This is the single most useful habit for "vanished config" mysteries: **the log always knows.**

### 4.2 The Two Culprits

- **`general-research`**: unquoted `argument-hint` containing `[scope: broad|narrow]` etc. - the exact `Nested mappings are not allowed in compact mappings` shape.
- **`language-learning`**: the `description` contained `Front-load keywords: language`, ... - an unquoted `colon-space` inside a flow value, which yaml 2.x also rejects (BLOCK_AS_IMPLICIT_KEY).

### 4.3 The Fix (or: Quotation Marks, the Unsung Heroes)

Both offending values now carry full quotes (and nothing else needed touching):

```yaml
---
name: general-research
metadata:
  argument-hint: "<subject> [scope: broad|narrow] [depth: school|general|university] [format: report|blog|summary]"
---
```

The `general-research` description survived unquoted - no `: `, `[`, or `{` in it - so only `argument-hint` needed the fix. `language-learning` had the opposite problem: its `description` contained `Front-load keywords: language, ...`, so the whole description got quoted:

```yaml
---
name: language-learning
description: "Use when the user wants to learn a language through conversation. ... Front-load keywords: language, learn, ..."
---
```

Any value containing `: `, `[`, `{`, or quoted inner strings gets double-quoted wholesale. It costs nothing and is immune to every compact-mapping trap.

## 5. Verification Status

| Check | Result |
|---|---|
| Reproduce the fault under yaml 2.9.0 | `Nested mappings are not allowed in compact mappings` |
| `general-research` after quoting | parses clean under yaml 2.9.0 |
| `language-learning` after quoting | parses clean under yaml 2.9.0 |
| Both present in loaded skill list | 21/21 file skills registered |
| Backups | pre-fix copies in the tray (`general-research-SKILL-pre-quote-argument-hint-*`, `language-learning-SKILL-pre-quote-description`) |
| Live confirmation | user confirmed the skill loads in sessions |

## 6. Pending Actions

- Apply the same quote-any-frontmatter-value discipline to all new skills (done retroactively for both fixed skills; `kb-recall` was authored quoted from day one).

## 7. Recommendations

- **Always quote skill frontmatter scalar values** that contain `: `, `[`, `{`, or nested quotes. If in doubt, quote. Bare words only, no exceptions.
- **When a skill vanishes, grep the opencode log before rebuilding anything.** The loader logs the parse error even when the UI stays silent.
- **Validate frontmatter with the exact parser in use** - `yaml` 2.x in opencode is *not* PyYAML. A one-liner node check against the bundled module catches it before a session ever misses the skill.
- **Keep the parameterized `version` in metadata.**
- Back up pre-fix files to the tray before editing shared skill frontmatter (append-only history exists there now for both).

---

Generated by Big Pickle (OpenCode)
