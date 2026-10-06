import os, re, glob, json, sys, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs")
CACHE = os.path.join(REPO, ".cache")
SKIP = ("index.md", "about.md", "reports.md")

# ---------------------------------------------------------------------------
# Navigation is DECLARED, not inferred.
#
# Each series post carries its own nav: frontmatter (series, part, prev, next).
# Nothing here derives membership from a filename, because filenames now describe
# content and carry no sequence information.
#
# The important function in this file is validate(), not collect(). Under the old
# design a broken grouping failed visibly (no footer rendered). With hand-written
# navigation the failure modes are silent: a link to a post that was renamed, a
# one-way prev/next pair, a self-reference. Those render as a dead or
# contradictory footer on a live page. So they are build errors.
# ---------------------------------------------------------------------------


def parse_frontmatter(path):
    """Return (frontmatter_dict_or_None, body). Minimal YAML subset:
    nav.series (str), nav.part (int), nav.prev/.next ({title, slug})."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 3)
    if end == -1:
        return None, text
    block = text[4:end + 1]
    body = text[end + 5:]
    nav = {"series": None, "part": None, "prev": None, "next": None}
    section = None
    side = None
    for raw in block.split("\n"):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        m = re.match(r"^(\s*)([A-Za-z_]+):\s*(.*)$", raw)
        if not m:
            continue
        indent, key, val = m.group(1), m.group(2), m.group(3).strip()
        if indent == "":
            section = key if val == "" else None
            if key == "nav":
                section = "nav"
                side = None
            continue
        if section != "nav":
            continue
        if indent == "  ":
            if key in ("prev", "next"):
                side = key
                nav[side] = {}
            elif key == "series":
                nav["series"] = unquote(val)
                side = None
            elif key == "part" and val.isdigit():
                nav["part"] = int(val)
                side = None
        elif indent == "    " and side:
            nav[side][key] = unquote(val)
    return nav, body


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v.replace('\\"', '"').replace("\\\\", "\\")


def title_of(path, body):
    for line in body.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return None


def collect():
    """Group posts by their declared nav.series. Returns (series, standalone)."""
    series = {}
    standalone = []
    for path in sorted(glob.glob(os.path.join(DOCS, "*.md"))):
        base = os.path.basename(path)
        if base in SKIP:
            continue
        stem = base[:-3]
        nav, body = parse_frontmatter(path)
        title = title_of(path, body)
        if not nav or not nav.get("series"):
            standalone.append({"stem": stem, "title": title})
            continue
        series.setdefault(nav["series"], []).append({
            "stem": stem,
            "part": nav["part"],
            "title": title,
            "prev": nav["prev"],
            "next": nav["next"],
        })
    for items in series.values():
        items.sort(key=lambda x: (x["part"] is None, x["part"] or 0))
    return series, standalone


def validate(series, standalone):
    """Fail the build on any navigation defect. Returns a list of errors."""
    errors = []
    stems = {p["stem"] for items in series.values() for p in items}
    stems |= {p["stem"] for p in standalone}

    for name, items in series.items():
        parts = [i["part"] for i in items]
        if any(p is None for p in parts):
            errors.append(f"series {name!r}: post missing nav.part")
            continue
        expected = list(range(1, len(parts) + 1))
        if sorted(parts) != expected:
            errors.append(f"series {name!r}: parts {sorted(parts)} are not contiguous from 1")
            continue
        for idx, item in enumerate(items):
            want_prev = items[idx - 1] if idx > 0 else None
            want_next = items[idx + 1] if idx < len(items) - 1 else None
            for side, neighbour in (("prev", want_prev), ("next", want_next)):
                got = item[side]
                if neighbour is None:
                    if got:
                        errors.append(
                            f"{item['stem']}: has nav.{side} but is at the edge of {name!r}")
                    continue
                if not got:
                    errors.append(f"{item['stem']}: missing nav.{side} in {name!r}")
                    continue
                if got.get("slug") != neighbour["stem"]:
                    errors.append(
                        f"{item['stem']}: nav.{side}.slug is {got.get('slug')!r}, "
                        f"expected {neighbour['stem']!r}")
                if not got.get("title"):
                    errors.append(f"{item['stem']}: nav.{side}.title is empty")
                if got.get("slug") == item["stem"]:
                    errors.append(f"{item['stem']}: nav.{side} points at itself")
                if got.get("slug") and got["slug"] not in stems:
                    errors.append(
                        f"{item['stem']}: nav.{side}.slug {got['slug']!r} does not exist")
            # reciprocity, checked independently of ordering
            if want_next and item["next"] and want_next["prev"]:
                back = want_next["prev"].get("slug")
                if back != item["stem"]:
                    errors.append(
                        f"one-way link: {item['stem']} -> {want_next['stem']} "
                        f"but {want_next['stem']} -> {back!r}")
    return errors


def write_index(series, standalone, out_dir):
    dated = []
    for items in series.values():
        for i in items:
            dated.append(i)
    all_items = [(s["title"], s["stem"]) for s in standalone] + \
                [(i["title"], i["stem"]) for i in dated]

    def date_of(stem):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-", stem)
        return m.group(1) if m else ""

    ordered = sorted(all_items, key=lambda x: date_of(x[1]), reverse=True)
    featured = ordered[:4]
    latest = ordered[4:10]

    order = sorted(series.items(),
                   key=lambda kv: date_of(kv[1][-1]["stem"]), reverse=True)

    hero = (
        '<div class="cb-hero">\n  <div class="cb-hero__content">\n'
        '    <h1>Codebot Reports</h1>\n'
        '    <p>Technical reports from homelab experiments, builds, and research.</p>\n'
        '    <div class="cb-hero__cta">\n'
        '      <a href="#series" class="cb-btn cb-btn--primary">Browse Series</a>\n'
        '      <a href="#latest" class="cb-btn cb-btn--secondary">Latest Posts</a>\n'
        '    </div>\n  </div>\n</div>\n'
    )

    b = '<section class="cb-featured" id="featured">\n  <h2>Latest Highlights</h2>\n'
    b += '  <div class="cb-featured__grid">\n'
    for t, stem in featured:
        b += f'    <div class="cb-card">\n      <a href="{stem}/">{esc(t)}</a>\n'
        b += f'      <span class="cb-card__date">{date_of(stem)}</span>\n    </div>\n'
    b += "  </div>\n</section>\n"

    b += '<section class="cb-latest" id="latest">\n  <h2>More Recent Posts</h2>\n  <ul>\n'
    for t, stem in latest:
        b += f'    <li><a href="{stem}/">{esc(t)}</a></li>\n'
    b += "  </ul>\n</section>\n"

    b += '<section class="cb-series" id="series">\n  <h2>Series Archive</h2>\n'
    b += '  <div class="cb-series__list">\n'
    for name, items in order:
        b += '    <details class="cb-series__item">\n'
        b += '      <summary class="cb-series__summary">\n'
        b += f'        <span class="cb-series__name">{esc(name)}</span>\n'
        b += f'        <span class="cb-series__count">{len(items)} parts</span>\n'
        b += "      </summary>\n      <ul class=\"cb-series__parts\">\n"
        for i in items:
            b += f'        <li><a href="{i["stem"]}/">{esc(i["title"])}</a></li>\n'
        b += "      </ul>\n    </details>\n"
    b += "  </div>\n</section>\n"

    content = ("---\nnav_exclude: true\nhide:\n  - navigation\n---\n\n"
               + hero + "\n" + b)
    with open(os.path.join(out_dir, "index.md"), "w") as f:
        f.write(content)


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    args = sys.argv[1:]
    stage = None
    if "--stage" in args:
        i = args.index("--stage")
        if i + 1 >= len(args):
            print("error: --stage requires a directory", file=sys.stderr)
            sys.exit(2)
        stage = os.path.abspath(args[i + 1])
        # --stage was removed by 7396181 (2026-10-06) while the service kept
        # passing it, so it silently became a no-op: build_docs stopped being
        # refreshed and the auto-build served a stale snapshot. Python ignores
        # unknown argv, which makes an un-honoured flag indistinguishable from a
        # honoured one -- hence these guards fail loudly instead of doing nothing.
        if stage == DOCS:
            print(f"error: --stage must not be the docs directory itself ({DOCS});",
                  file=sys.stderr)
            print("       it would be deleted before being copied", file=sys.stderr)
            sys.exit(2)
        if not os.path.isdir(os.path.dirname(stage) or "."):
            print(f"error: --stage parent does not exist: {os.path.dirname(stage)}",
                  file=sys.stderr)
            sys.exit(2)

    os.makedirs(CACHE, exist_ok=True)
    series, standalone = collect()

    errors = validate(series, standalone)
    if errors:
        print(f"navigation validation FAILED ({len(errors)} problems):")
        for e in errors:
            print("  !!", e)
        sys.exit(1)

    with open(os.path.join(CACHE, "series_data.json"), "w") as f:
        json.dump(series, f, indent=2)

    if stage:
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        shutil.copytree(DOCS, stage)
        # The fresh index goes into the STAGE, never into docs/: docs/ is
        # watched by zensical-build.path, so writing index.md there during a
        # service run re-triggers the watcher. That is the protection 58d75b4
        # added and 7396181 lost.
        write_index(series, standalone, stage)
        print(f"staged {len(glob.glob(os.path.join(stage, '*.md')))} .md files -> {stage}")
    else:
        write_index(series, standalone, DOCS)

    print(f"wrote index.md and series_data.json")
    print(f"series: {len(series)}  posts in a series: {sum(len(v) for v in series.values())}"
          f"  standalone: {len(standalone)}")
    print("navigation validation passed")


if __name__ == "__main__":
    main()