import os, re, glob, json, sys, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs")
CACHE = os.path.join(REPO, ".cache")
SKIP = ("index.md", "about.md", "reports.md")

NAMES = {
    "blogging-skill-evolution": "Blogging Skill Evolution",
    "boot-recovery": "Boot Recovery",
    "captive-portal-and-access-point-bundle": "Captive Portal and Access Point Bundle",
    "coding-with-hermes-agent": "Coding with Hermes Agent",
    "experimenting-with-hermes-agent": "Experimenting with Hermes Agent",
    "hermes-agent-provider-and-fallback-chain": "Hermes Agent Provider and Fallback Chain",
    "homelab-management": "Homelab Management",
    "litellm-frontend-build": "LiteLLM Frontend Build",
    "mem0-memory-integration": "Mem0 Memory Integration",
    "opencode-configuration-evolution": "OpenCode Configuration Evolution",
    "opencode-provider-and-fallback-chain": "OpenCode Provider and Fallback Chain",
    "switch-root-target-contains-no-usable-init": "Switch Root Target Contains No Usable Init",
    "the-litellm-callback-saga": "The LiteLLm Callback Saga",
    "the-litellm-gateway-evolution": "The LiteLLM Gateway Evolution",
    "the-tinyllama-experiment": "The TinyLlama Experiment",
    "zensical-customization": "Zensical Customization",
}
def disp(key):
    return NAMES.get(key, key.replace("-", " ").title())

def meta(path):
    base = os.path.basename(path)[:-3]
    m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", base)
    date, slug = m.group(1), m.group(2)
    title = base
    for line in open(path):
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return date, slug, title, base

def collect(docs_dir):
    series_re = re.compile(r"^(.*)-part-(\d+)(?:-[a-z]+)?$")
    files = [f for f in glob.glob(docs_dir + "/*.md") if os.path.basename(f) not in SKIP]
    groups = {}
    standalone = []
    for path in files:
        date, slug, title, base = meta(path)
        mm = series_re.match(slug)
        if mm:
            groups.setdefault(mm.group(1), []).append((int(mm.group(2)), date, slug, title, base))
        else:
            standalone.append((date, slug, title, base))
    series_data = {}
    for key, items in groups.items():
        items_sorted = sorted(items, key=lambda x: x[0])
        parts = []
        for idx, (part_num, date, slug, title, base) in enumerate(items_sorted):
            prev_url = items_sorted[idx - 1][4] + "/" if idx > 0 else None
            prev_title = items_sorted[idx - 1][3] if idx > 0 else None
            next_url = items_sorted[idx + 1][4] + "/" if idx < len(items_sorted) - 1 else None
            next_title = items_sorted[idx + 1][3] if idx < len(items_sorted) - 1 else None
            parts.append({
                "part": part_num,
                "title": title,
                "url": base + "/",
                "slug": slug,
                "date": date,
                "prev_url": prev_url,
                "prev_title": prev_title,
                "next_url": next_url,
                "next_title": next_title,
            })
        series_data[key] = {
            "name": disp(key),
            "parts": parts,
            "total": len(parts),
        }
    return series_data, groups, standalone

def yaml_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')

def inject_frontmatter(stage_dir, series_data):
    count = 0
    manual_line_re = re.compile(r"^\[Part \d+\]\(https://homelab\.home\.arpa/journal/[^)]+\.md\)\.$")
    for path in glob.glob(stage_dir + "/*.md"):
        base = os.path.basename(path)[:-3]
        if base in SKIP:
            continue
        mdate = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", base)
        slug = mdate.group(2) if mdate else base
        m = re.match(r"^(.*)-part-(\d+)", slug)
        if not m:
            continue
        key = m.group(1)
        series = series_data.get(key)
        if not series:
            continue
        part = None
        for p in series["parts"]:
            if p["slug"] == slug:
                part = p
                break
        if part is None:
            continue
        with open(path) as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if manual_line_re.match(line.rstrip()):
                continue
            new_lines.append(line)
        body = "".join(new_lines)
        meta_lines = [
            "---",
            "series: " + key,
            'series_name: "' + yaml_escape(series["name"]) + '"',
        ]
        if part.get("prev_url"):
            meta_lines.append('series_prev_url: "' + yaml_escape(part["prev_url"]) + '"')
            meta_lines.append('series_prev_title: "' + yaml_escape(part["prev_title"]) + '"')
        if part.get("next_url"):
            meta_lines.append('series_next_url: "' + yaml_escape(part["next_url"]) + '"')
            meta_lines.append('series_next_title: "' + yaml_escape(part["next_title"]) + '"')
        meta_lines.append("---")
        with open(path, "w") as f:
            f.write("\n".join(meta_lines) + "\n\n" + body)
        count += 1
    return count

def write_index(docs_dir, series_data, groups, standalone):
    all_items = standalone + [(d, s, t, b) for k in groups for (_, d, s, t, b) in groups[k]]
    latest10 = sorted(all_items, key=lambda x: x[0], reverse=True)[:10]
    order = sorted(groups.items(), key=lambda kv: max(d for _, d, _, _, _ in kv[1]), reverse=True)

    block = (
        '<div class="cb-home">\n'
        '  <div class="cb-home__top">\n'
        '    <section class="cb-hero">\n'
    '      <h1>Codebot Reports</h1>'
    '      <p>Collection of reports generated by Codebot from the blog markdown. '
    'Browse the series below, or the latest posts on the right.</p>'
    '    </section>'
    '    <aside class="cb-latest" aria-label="Latest posts">'
    '      <h2>Latest posts</h2>'
    '      <ul>'
    )
    for d, s, t, b in latest10:
        block += f'        <li><a href="{b}/">{t}</a></li>\n'
    block += '      </ul>'
    '    </aside>'
    '  </div>'
    '</div>'
    '\n'

    # Generate series section as HTML to ensure proper rendering
    series_html = ['<section class="cb-series-list">', '<h2>Series</h2>']
    for key, items in order:
        items_sorted = sorted(items, key=lambda x: x[0])
        series_html.append(f'<h3>{disp(key)}</h3>')
        series_html.append('<ul>')
        for _, date, slug, title, base in items_sorted:
            series_html.append(f'  <li><a href="{base}/">{title}</a></li>')
        series_html.append('</ul>')
    series_html.append('</section>')
    series_block = '\n'.join(series_html)

    content = (
        "---\n"
        "nav_exclude: true\n"
        "hide:\n"
        "  - navigation\n"
        "---\n\n"
        + block
        + "\n"
        + series_block
        + "\n"
    )
    with open(os.path.join(docs_dir, "index.md"), "w") as f:
        f.write(content)

def main():
    args = sys.argv[1:]
    stage = None
    if "--stage" in args:
        i = args.index("--stage")
        stage = args[i + 1]

    os.makedirs(CACHE, exist_ok=True)
    series_data, groups, standalone = collect(DOCS)

    with open(os.path.join(CACHE, "series_data.json"), "w") as f:
        json.dump(series_data, f, indent=2)

    write_index(DOCS, series_data, groups, standalone)

    if stage:
        if os.path.exists(stage):
            shutil.rmtree(stage)
        shutil.copytree(DOCS, stage)
        injected = inject_frontmatter(stage, series_data)
        print(f"staged {stage} ({injected} posts with series frontmatter)")
    else:
        print("wrote index.md and series_data.json")
    print("series groups:", len(groups))

if __name__ == "__main__":
    main()
