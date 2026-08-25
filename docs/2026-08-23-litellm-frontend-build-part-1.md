# LiteLLM Frontend Build - Part 1

*Adapting G0DM0D3 as a custom frontend for LiteLLM (or: how I learned to stop worrying and love the strip)*

**Date:** 2026-08-23  
**Author:** Codebot  
**Topic:** litellm, frontend, opencode, nixos, homelab, config

---

## 1. The Grand Plan (or: What Are We Even Doing Here?)

Build a custom web frontend for the LiteLLM gateway at `litellm.home.arpa`, using the G0DM0D3 open-source UI as a starting point. Strip the original JavaScript, keep the HTML/CSS shell, and plan a new script that works directly with the LiteLLM API instead of OpenRouter.

## 2. Backstory: Why We're Here

The LiteLLM proxy runs on the homelab, serving 499 models via NVIDIA NIM and other providers. The default LiteLLM UI is functional but basic — like a plain bagel when you wanted everything on it. G0DM0D3 is an open-source AI chat interface with a polished dark theme, modal settings, sidebar, and conversation management — exactly the UX we want, but built for OpenRouter with racing/judge logic we don't need.

The plan: take G0DM0D3's HTML and CSS, remove all JavaScript, and rebuild the script from scratch to work with our LiteLLM instance. Simple, right? (Narrator: it was not simple.)

## 3. The Beast We're Taming

The G0DM0D3 project lives at `github.com/elder-plinius/G0DM0D3`. The original `index.html` is 793KB, roughly 17,000 lines, with embedded JavaScript handling:

- **ULTRAPLINIAN mode**: Races 44 hardcoded models in parallel, scores responses, LLM judge picks winner. Because nothing says "efficient" like 44 API calls for one answer.
- **G0DM0D3 CLASSIC (PLINY)**: Races 4 model+prompt jailbreak combos. For when you need your AI to ignore its training *and* look cool doing it.
- **PARSELTONGUE**: Input obfuscation to bypass safety filters. Parseltongue. For AI. I'm not making this up.
- **TASTEMAKER**: Response scoring system (quality, filteredness, autonomy). An LLM judge for your LLM outputs. It's turtles all the way down.
- **Liquid Response**: Live morphing display as better responses arrive. Mesmerizing, slightly unnecessary.
- **Waiting Game**: Mini-games while waiting for responses. Because staring at a spinner is so 2022.

Most of this is unnecessary for a single-model chat interface talking to LiteLLM. We just want to *chat*, not host a gladiatorial tournament.

## 4. The Surgery

### 4.1 Deploying the Reference (aka "Don't Break the Original")

Copied the original `index.html` to `/srv/www/godmod3/index.html` as an untouched reference. Deployed a working copy to `/srv/www/litellm/index.html`. Rule #1: never modify the original. Rule #2: see Rule #1.

### 4.2 The Great JavaScript Exorcism

Removed every `<script>` tag and inline JavaScript from the working copy. The file dropped from 17,000 lines to approximately 4,000 lines of pure HTML and CSS. All functionality — modals, settings, chat, sidebar — stopped working. This was intentional: we're building new behavior from scratch. Also, watching a fully-styled UI do absolutely nothing is oddly satisfying.

### 4.3 Rebranding: Operation "Make It Ours"

| Element | Original | Changed To |
|---------|----------|------------|
| Logo text | G0DM0D3 | LiteLLM |
| Welcome icon | Pliny symbol | Robot emoji 🤖 |
| Welcome heading | G0DM0D3 | LiteLLM |
| Mode dropdown | 3 modes (ULTRAPLINIAN, PARSELTONGUE, PLINY) | Gone. Just gone. |
| Model select | Hidden, tied to PARSELTONGUE | Visible, standalone, proud |

### 4.5 Settings Tab KonMari Method

Stripped the Settings modal from 6 sections to 5 clean tabs. Does it spark joy? If not, thank it and delete it.

**General** — Default Model selector (NVIDIA models), Transparency toggle (Show Magic, on by default). Removed: Model & Persona (GODMODE branding), Privacy (telemetry), Waiting Game (mini-games). The "Show Magic" toggle stays because who doesn't want to see the magic?

**Strategies** — TASTEMAKER toggle with expandable philosophy preview. Placeholder for future strategies (warm-up, caching). Removed: Liquid Response parameters, ULTRAPLINIAN tier settings, G0DM0D3 Hall of Fame combos, PARSELTONGUE obfuscation settings, AutoTune. We kept the philosophy preview because it's genuinely entertaining reading.

**System Prompt** — Kept as-is. Custom system prompt textarea with enable toggle. TASTEMAKER and custom prompt combine: TASTEMAKER first (sets baseline tone), custom second (can override). Like a good cop / bad cop routine, but both are you.

**API Key** — Empty content, tab kept. API key will be stored in `localStorage`, never hardcoded in source. The tab sits there patiently, waiting for its moment.

**Data** — Export Conversations button, Storage Info section. Removed: Full Backup/Restore, Strategy Logs, Danger Zone. "Danger Zone" sounded fun but we're not deploying nukes here.

### 4.5 Design Decisions (or: How We Talked Ourselves Into Reasonable Choices)

**No racing**. The original G0DM0D3 races multiple models and has an LLM judge pick the winner. This is expensive (5x API calls + judge), slow (waits for all responses), and impractical for daily use. We use a single model selected via the dropdown. Because sometimes you just want *an* answer, not *the best possible answer after a committee review*.

**TASTEMAKER as optional system prompt**. The PROMETHEUS philosophy ("substance over safety theater") is useful, but the race it was designed for is not. We kept it as a toggleable system prompt injection, not a race judge. It's the seasoning, not the main course.

**GODMODE was just branding**. In the original, "GODMODE ENABLED" was a static display element, not a functional toggle. The actual jailbreak prompts were part of the HALL_OF_FAME race combos, which we removed. Turns out "GODMODE" was just a cool label. Who knew?

**Model selection from dropdown**. Instead of hardcoded `ULTRAPLINIAN_MODELS` array, the script will read from the `modelSelect` dropdown. This adapts to whatever models are available in LiteLLM. No more updating arrays when the model zoo expands.

## 5. Where We Landed

The HTML shell is complete. It has:

- Header with model selector and new chat button
- Chat area with welcome screen
- Sidebar for conversation history
- Settings modal with 5 tabs
- Dark theme from G0DM0D3 CSS
- No stale JavaScript references

What it doesn't have: any working JavaScript. That's Part 2. The UI sits there, beautiful and useless, like a sports car with no engine.

## 6. The TODO List (aka "Next Time on This Show")

The custom script needs to handle:

1. Chat with LiteLLM API (`/v1/chat/completions` with streaming)
2. Settings persistence (`localStorage`)
3. System prompt injection (TASTEMAKER + custom, in that order)
4. Conversation management (create, switch, delete)
5. Model selection from `modelSelect`
6. API key handling (stored in `localStorage`)
7. Settings tab switching
8. Sidebar toggle

## 7. Architecture Notes (The Boring But Important Stuff)

The TASTEMAKER system prompt (PROMETHEUS philosophy) sets response expectations: comprehensive answers, no hedging, no moralizing, substance over safety theater. When combined with a custom system prompt, TASTEMAKER comes first (sets the tone), custom prompt second (can override or extend).

The API key is never committed to source code. It lives in `localStorage` and is read by the script at runtime. The HTML just has a placeholder input field. Security through "not putting secrets in git" — revolutionary concept.

## 8. Files (The Inventory)

| File | Purpose |
|------|---------|
| `/srv/www/litellm/index.html` | Working copy, HTML+CSS only |
| `/srv/www/godmod3/index.html` | Reference copy, original G0DM0D3 untouched |
| `/srv/www/litellm/` | Served by Caddy at `https://litellm.home.arpa/` |

## 9. Unsolicited Advice for Future Me (and You)

For anyone adapting G0DM0D3 or similar UIs:

1. **Strip JavaScript first** — understand the HTML structure before rebuilding behavior. It's like reading the manual before assembling IKEA furniture.
2. **Keep a reference copy** — never modify the original; always work on a copy. Seriously. Future you will thank present you.
3. **Challenge hardcoded lists** — model arrays, API URLs, and config values should come from the environment, not source code. Hardcoding is technical debt with a fancy hat.
4. **Separate concerns** — HTML/CSS is the shell, JavaScript is behavior, config is environment. Mix them at your peril.

---

Generated with Nemotron 3 Ultra (NVIDIA)