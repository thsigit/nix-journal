# Automating Blog Series Navigation

## Problem

Manually maintaining series navigation links in blog posts was error-prone and tedious. Each post in a series required:
- Manual Previous/Next link updates when adding/removing posts
- Risk of broken links when URLs changed
- Inconsistent formatting across series posts
- Time-consuming manual editing

## Solution: Automated Series Detection and Navigation

Implemented automated series detection and navigation generation in the nix-journal blog system.

### Key Components

1. **Series Detection from Filenames**
   - Parses filenames to detect series patterns
   - Handles `-part-N` and `-part-N-final` suffixes
   - Groups posts by series identifier

2. **Staging Workflow**
   - `gen_home.py --stage build_docs` creates staged copies with injected frontmatter
   - Preserves original source files
   - Enables safe generation without modifying source

3. **YAML Frontmatter Injection**
   - Automatically adds series metadata to each post:
     ```yaml
     series: the-litellm-callback-saga
     series_name: The LiteLLM Callback Saga
     series_prev_url: ../2026-08-27-the-litellm-callback-saga-part-2/
     series_prev_title: The LiteLLM Callback Saga - Part 2
     ```

4. **Template Overrides**
   - Custom `content.html` includes series footer
   - `series-footer.html` partial renders navigation links
   - Uses injected frontmatter for dynamic link generation

### Results

**Before:** Manual links like `[Part 2](https://homelab.home.arpa/journal/2026-08-27-litellm-callback-debugging.md)`
**After:** Relative links like `[Part 2](../2026-08-27-the-litellm-callback-saga-part-2/)`

**Benefits:**
- Zero manual link maintenance
- Consistent navigation across all series posts
- Automatic updates when series structure changes
- Works for both local development (`journal.home.arpa`) and production (GitHub Pages)
- Eliminates broken links from hardcoded URLs

### Technical Implementation

The system consists of:
- `gen_home.py`: Main script with series detection and staging logic
- `publish.sh`: Updated deployment script using staging workflow
- Overrides in `/overrides/partials/` for custom templates
- Generated `.cache/series_data.json` for series tracking

### Next Steps

Implement Next link in series navigation to complete bidirectional series traversal.

## Verification

All manual `homelab.home.arpa/journal` links have been replaced with proper relative paths. Series navigation renders correctly with working Previous links. Build system produces consistent output for both local and deployment environments.

*Created: 2026-08-30*
