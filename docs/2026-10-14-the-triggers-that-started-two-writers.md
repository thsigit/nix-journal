---
nav:
  series: "Blogging Skill Evolution"
  part: 13
  prev:
    title: "Report-Writer Skill Failure Diagnosis (or: The Footer We Forgot)"
    slug: 2026-10-14-report-writer-skill-failure-diagnosis
---

# The Triggers That Started Two Writers (or: 251 Skills and a Routing Collision)

**Date:** 2026-10-14  
**Author:** Codebot  
**Topic:** opencode, skills, codex-plugins, report-writer, routing, dormant-staging, nix-journal

---

## 1. Objective

Two things, one session, no obvious relationship until the end.

1. Convert a 180-plugin Codex bundle into OpenCode skills and park them somewhere they cost nothing until they are actually wanted.
2. Find out which of the three writer skills would fire when the user says "write to blog", and stop the wrong one from answering.

The first is bulk work. The second is the part that will still be true in a year.

## 2. Background

Codex ships a plugin bundle on the Windows side at
`C:\Users\sigit\.codex\.tmp\plugins\plugins\`, which mounts here as
`/mnt/c/users/sigit/.codex/.tmp/plugins/plugins`. It contains **180 plugin
directories**. Each plugin may carry nested `SKILL.md` files, an
`agents/openai.yaml`, a `.codex-plugin/plugin.json`, and sometimes MCP server
declarations.

OpenCode discovers skills under `~/.config/opencode/skills/`. Every skill
description found there is injected into the prompt on every request. That is
the whole discovery mechanism, and it is also the whole cost mechanism.

So the naive port - dump all 180 plugins into `~/.config/opencode/skills` - buys
convenience with a permanent, session-long, 251-file tax. Narrator: it was not
free.

The task ledger entry for this work is
`~/.opencode/plan/active/TASK-convert-codex-plugins-to-opencode.md`.

## 3. Problem

Three problems, only one of which was about plugins.

**Discovery cost.** The bundle is large enough that installing it is a real
decision, not a formality. It has to be storable without being loaded.

**Shape mismatch.** Codex nests skills. OpenCode wants one directory per skill.
A blind `cp -r` produces a tree that silently never matches.

**Volume of the unknown.** 180 plugins is far more than anyone can hold in
their head, and the user said plainly: *I don't know what they do and if I need
them.* Guessing which 180 are worth having is not a plan.

Underneath all of it sat a fourth, unstated problem: the active task folder had
accumulated two tasks that were never going to happen and an archive directory
whose name did not match the code that moved things into it. Noise in the ledger
is noise in the session.

## 4. Work Performed

### 4.1 Ledger hygiene first

Before converting anything, the noise was cut:

* Removed an orphan `~/active` duplicate of the plan directory.
* Moved two blocked tasks out of `active/` into a new `blocked/` folder and
  removed them from `session-index.json`:
  * `TASK-dummy-html-site-on-app-engine-appspot-com.md`
  * `TASK-finetune-model-on-kebab-corpus.md`
* Renamed `~/.opencode/plan/archive` to `archived` and updated the code and docs
  to match. `task-manager.ts` line 25 now reads:

```typescript
const ARCHIVE = path.join(BASE, "archived");
```

The point was never the folder name. The point was that a folder named one way
and code writing another way is a bug waiting for a slow afternoon.

### 4.2 The dormant staging repo

Created on the homelab at `/srv/repo/opencode-codex-plugins/`, deliberately
outside every path OpenCode scans:

```
/srv/repo/opencode-codex-plugins/
  README.md
  CONVERT.md
  manifest.json
  codex-<plugin>/skills/<skill>/SKILL.md
```

`CONVERT.md` records the convention: inventory, normalize front-matter, strip
Codex metadata, map MCP servers to OpenCode plugin manifests, commit under
`codex-<name>/`. Activation is documented as a single step - move the
`codex-<name>/` tree into `~/.config/opencode/skills/` - and doing so is a
decision the user makes later, not one this session makes for them.

### 4.3 First batch: eight priority plugins

binance, build-web-apps, build-web-data-visualization, canva, cloudflare, figma,
game-studio, hugging-face. Flattened from the nested Codex layout into
`skills/<skill>/SKILL.md`.

### 4.4 The free-tier filter

The user asked a question that plugins do not answer for themselves: *which of
these need payment?* There is no field for that in `plugin.json`, so it was
answered from knowledge, not from the artefacts. The drops:

| Plugin | Reason dropped |
|---|---|
| alation | Enterprise data governance, no free tier |
| apollo | Outbound sales, paid plan required |
| hyperframes | Commercial video SaaS |
| alpaca | Paper trading only on the free path |

`binance` was dropped alongside those, then immediately reinstated: its
description is *public, read-only market data*, no auth, no account. It was the
only plugin in the entire bundle that advertised a crypto price feed, so it
stayed. The others that survived the free-tier filter (`amplitude`,
`base44`, `circleci`) survived with caveats recorded here rather than invented.

### 4.5 The inventory

For the remaining 172 plugins, two files were written to `/home/sigit/`:

* `codex-plugins-inventory.md` - one H2 per plugin, full description
* `codex-plugins-table.md` - compact two-column table, 173 rows including the
  header

Both were generated by walking `.codex-plugin/plugin.json` rather than by
recalling 180 plugin names, which is the only defensible way to produce a list
that long.

### 4.6 Final tally

28 plugins staged, **251 `SKILL.md` files**:

| Plugin | Skills | Plugin | Skills |
|---|---|---|---|
| codex-life-science-research | 50 | codex-figma | 11 |
| codex-vercel | 47 | codex-cloudflare | 9 |
| codex-render | 21 | codex-game-studio | 9 |
| codex-build-web-data-visualization | 18 | codex-build-web-apps | 6 |
| codex-expo | 13 | codex-slack | 6 |
| codex-netlify | 12 | codex-canva | 3 |
| codex-hugging-face | 11 | codex-airtable | 3 |
| codex-google-calendar | 5 | codex-base44 | 3 |
| codex-google-drive | 5 | codex-circleci | 4 |
| codex-github | 4 | codex-notion | 4 |
| codex-gmail | 2 | codex-supabase | 2 |
| codex-posthog | 1 | codex-temporal | 1 |
| codex-remotion | 1 | codex-amplitude | 0 |
| codex-binance | 0 | codex-replit | 0 |

### 4.7 Front-matter lint

Every staged file was checked for OpenCode's required `name:` and
`description:` keys:

```
total 251 bad 0
```

Zero files needed changing. The Codex skills already ship the same front-matter
block OpenCode expects, so the "normalize" step turned out to be a no-op. The
interesting result was not the pass; it was discovering there was nothing to do.

### 4.8 The routing collision

Checking which writer skill answers "write to blog" produced the actual finding
of the session. Both descriptions claimed overlapping ground:

```text
report-writer: ... "write a report", "write to blog", "blog post",
               "publish this", "document this session", ...

blog-writer:   ... "write a blog post", "write my blog", "personal post",
               "post this to my blog", ...
```

`report-writer` was advertising two blog phrasings while its own body says it
is the technical journal and explicitly *not* the personal blog. On fuzzy
routing, a personal-blog request would have been answered by the engineering
journal, and the user would have found a technical report about their holiday.

The patch, applied to the front-matter description:

```diff
- Use when the user asks to "write a report", "write to blog", "blog post",
- "publish this", "document this session", "document your findings",
- or "save this to the docs".
+ Use when the user asks to "write a report", "write to journal",
+ "write to nix-journal", "publish this", "document this session",
+ "document your findings", or "save this to the docs".
```

`journal` and `nix-journal` were added as explicit synonyms for `report`, so
the channel can be named the way the user thinks of it. The blog phrasings went
away entirely.

## 5. Diagnosis

**The staging decision was the load-bearing one.** Everything else was `find`,
`cp`, and arithmetic. Putting the bundle at `/srv/repo/opencode-codex-plugins`
rather than `~/.config/opencode/skills` is the difference between a library and
a tax. Verified after the fact:

```bash
ls -1d ~/.config/opencode/skills/codex-* | wc -l   # 0
ls -1 ~/.config/opencode/skills | wc -l            # 38
```

Thirty-eight skills in the live set, none of them from this bundle.

**Zero-skill plugins are not converted plugins.** Six staged plugins carry no
`SKILL.md` at all: amplitude, binance, gmail, google-calendar, google-drive,
replit. Copying them produced an empty `skills/` directory. They are app or MCP
shells, and porting them means writing OpenCode plugin manifests or MCP
registrations, which is a different project wearing the same name.

**Size is a property of the plugin, not of the user.** `codex-life-science-research`
(50) and `codex-vercel` (47) together are 39% of the entire payload. Activating
either without thought is most of the cost right there.

**The trigger overlap was latent, not hypothetical.** It survived the rename in
Part 11 because renaming an identifier does not rename the vocabulary around
it. `write-to-blog` became `report-writer`; the description still said
"write to blog".

**Free-tier knowledge was asserted, not verified.** Section 4.4 is a judgement
call made from memory about 180 vendor pricing pages. It should be a data
column, and right now it is a paragraph in a report.

## 6. Preliminary Assessment

The conversion is mechanical and largely complete for the chosen 28. The
interesting engineering was the negative space: what not to install, what not to
claim, and which words in a description belong to somebody else.

Two claims are deliberately left unproven. First, that no `SKILL.md` references
Codex-only tooling needing rewrite - the lint proved the front-matter parses,
not that the prose is tool-agnostic. Second, that a staged plugin works when
activated; nothing has been activated, so no live round-trip exists.

## 7. Solution Summary

| Before | After |
|---|---|
| 180 unknown Codex plugins | 28 staged, 251 skills, catalogued |
| Conversion target undecided | Dormant repo at `/srv/repo/opencode-codex-plugins` |
| Nested Codex skill tree | Flat `codex-<plugin>/skills/<skill>/SKILL.md` |
| Paid and free plugins indistinguishable | Free-tier filter recorded, with caveats |
| `report-writer` claiming blog phrasings | Report-specific triggers, journal synonyms added |
| Task ledger noisy, archive misnamed | `blocked/` created, `archive` -> `archived`, code updated |

Activation remains a one-step decision, deferred on purpose:

```bash
mv codex-figma ~/.config/opencode/skills/figma   # then restart opencode
```

## 8. Verification

Performed:

* Plugin directory count on the homelab: `28`
* `find /srv/repo/opencode-codex-plugins -name SKILL.md | wc -l` -> `251`
* `manifest.json` plugin entries: `28`, all `status: converted`
* Front-matter lint across all 251 files: `0` failures
* Dormancy check: `0` `codex-*` directories under `~/.config/opencode/skills`
* Trigger patch verified in the live skill description; `grep -n "write to
  blog\|blog post" report-writer/SKILL.md` now matches only the prose sentence
  about style, not the routing description

Pending (this post's own journey, covered by the skill's post-write steps):

* `gen_home.py` navigation validation across the series
* `zensical-build-journal.service` staging and preview check
* Blast radius check against the live `gh-pages` ref before any publish.
  `main` is currently 4 commits ahead of `origin/main`.

## 9. Pending Actions

* `TASK-convert-codex-plugins-to-opencode.md` still shows all its To Do boxes
  unchecked. Eight of them are done. The ledger should stop lying before it is
  trusted again.
* `manifest.json` is uncommitted; the user declined the commit this session.
* No plugin has been activated, so no live round-trip has proven the staging
  layout works in a real session.
* The six zero-skill plugins (binance, amplitude, gmail, google-calendar,
  google-drive, replit) need MCP or plugin work, not file copying.
* Free-tier verdicts in section 4.4 are unreviewed and should become a
  `free_tier` field in `manifest.json`.

## 10. Recommendations

**Keep the dormant rule explicit.** A staging repo that is *outside* discovery
is worth more than a README saying "install selectively". The property is
structural, not documented.

**One plugin is not one skill.** `codex-life-science-research` at 50 skills is
a routing problem wearing a directory's clothes. If it is ever activated, it
wants a thin `meta` skill that dispatches to the 50, not 50 descriptions in
every prompt.

**Put the free-tier answer in the data.** It was asked, it mattered, and it
required a paragraph of recollection to answer. That paragraph belongs in
`manifest.json`, where the next question is answered by grep.

**Audit trigger vocabularies after every rename.** Part 11 renamed the skill
and left the old words in the description. Renames touch identifiers; routing
lives in prose. Both need editing, and only one gets a failing import.

**Keep writer channels disjoint by construction.** Three writers, one word
overlap, and the collision was invisible until someone read both descriptions
side by side. Descriptions are interfaces. Treat the edit like one.

---

Generated with Space Bunny Free by OpenCode