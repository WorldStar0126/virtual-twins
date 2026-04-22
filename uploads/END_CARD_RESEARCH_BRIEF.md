# End Card System — Research Brief

> **Purpose:** Feed this document to Claude Research (or similar deep-research agent) to return a comparative analysis of end card generation approaches. The goal is to pick an architecture before we start building Phase 2 #2 of the Virtual Twins video pipeline.

---

## Business Context

**Virtual Twins** is an AI video production agency building the *quick clip tier* — 8-25 second social-media videos for clients in real estate, title/closing, and adjacent industries. Every finished deliverable needs a **closing CTA card** (the "end card") that displays the client's branding and contact info.

### Where the end card fits in the pipeline

```
fal.ai Seed Dance 2.0 → clip 1 (10s)
                     → clip 2 (10s, uses frame ref from clip 1)
ffmpeg splice         → combined clip (20s, audio fades at seam)
END CARD (~3s)        ← what this brief is about
ffmpeg concat         → final deliverable (~23s)
```

The end card is always the final ~3 seconds. Style: **logo + phone + email + website + optional social handles**, 9:16 vertical, matched to client brand.

### Scale expectation

- Near-term: 5-20 clients
- 12-month target: 100+ clients
- Each client generates multiple videos per month
- End card content **changes rarely per client** (same logo + same contact info → heavy caching opportunity)
- End card design template may be **shared across many clients** or **customized per tier/industry**

---

## Current Stack (Constraints)

- **Platform:** Windows 11, bash shell (MSYS/Git Bash)
- **Language:** Python 3.11, with ffmpeg/ffprobe on PATH
- **Dependencies in use:** `fal-client`, `python-dotenv`, `requests`, `Pillow`, `numpy`
- **File layout:**
  ```
  assets/{client}/photos/      # client reference images
  assets/{client}/audio/       # voice reference
  output/{client}/             # generated + spliced videos
  .tmp/                        # caches, frame candidates
  tools/                       # Python scripts (generate, splice, frame-extract, etc.)
  workflows/                   # markdown SOPs
  ```
- **Existing tools are small, composable Python scripts** (no framework, no server, CLI-invoked)
- **Output format:** MP4, H.264, AAC, 9:16 vertical, 720p
- **Cost-sensitivity:** $3-5 per generated clip via fal.ai; end card should be **~$0 per render** (local only)
- **No subscriptions preferred** — avoid After Effects, Adobe Creative Cloud licensing if possible for this pipeline
- **Short-form aesthetic:** hard cuts preferred over slow dissolves; sans-serif typography; bright, high-contrast palettes typical in real estate social content

---

## What the End Card Must Contain

Per client, statically:
- **Company logo** (PNG/SVG, transparent background preferred)
- **Phone number**
- **Email address**
- **Website** (optional)
- **Social handles** (optional — Instagram, Facebook, LinkedIn most common for realtors/title)
- **Brand color palette** (primary + accent, ideally 2-3 colors per client)

Optional / tier-based additions:
- Tagline or value-prop line
- Headshot
- QR code to landing page

---

## Open Design Questions (the research target)

### 1. Architecture / generation tool

What's the best approach to generate animated 3-second end cards programmatically at scale, given our Python/ffmpeg stack and Windows environment?

**Candidates to compare:**
- **Remotion** — React/TypeScript framework for programmatic video, props-driven templates, renders via Chromium + ffmpeg
- **Motion Canvas** — TypeScript, smoother for abstract/data-viz animation, less used in marketing
- **After Effects + aerender CLI** — industry standard, expressions + JSON data injection, but licensed
- **Manim** — math/data animation library, Python-native, probably overkill stylistically
- **MoviePy + Pillow** — Python-native, simple layouts, limited animation primitives
- **ffmpeg drawtext + overlay filters only** — zero-dependency, limited animation (opacity, simple pan)
- **Canva API / Figma API + export** — design-tool-driven, API-accessible, may require subscription
- **Skia/skia-python** — headless 2D rendering with animation, low-level but powerful
- **HTML/CSS/SVG → Puppeteer/Playwright → screen-capture-to-video** — web-dev-familiar, flexible, moderate complexity

**Comparative dimensions:**
- Learning curve for the dev team (solo + agent-assisted)
- Template reusability / componentization
- Animation capability (motion quality, easing, transitions)
- Per-render time and cost
- Windows compatibility
- Community / docs maturity in 2026
- How easily an LLM-driven workflow can author templates vs manual coding

### 2. Data staging for per-client branding

How should we store and retrieve the per-client info (logo path, contact data, colors, tagline)?

**Candidates to compare:**
- **Flat JSON per client** at `assets/{client}/branding.json` — same pattern as existing asset layout
- **Single central JSON/YAML catalog** at `clients.json`
- **SQLite database** — relational, queryable, overkill at small scale but scales
- **Airtable / Notion as source of truth + sync script** — non-technical staff can edit
- **Google Sheets + API** — similar, with familiarity advantage
- **Supabase / Postgres** — cloud DB, overkill at current scale, maybe premature

**Decision criteria:**
- Ease of onboarding a new client (how many clicks / files / fields?)
- Who edits the data (dev vs ops staff)
- Change tracking (git-tracked vs external)
- Scale headroom to 100+ clients

### 3. Template strategy

How should end card designs scale across clients?

- **One shared template, variable content** — cheapest, most consistent, least bespoke
- **Template library** (3-5 designs, pick one per client/industry) — balance of consistency and variety
- **Per-client custom template** — premium, high bespoke cost, good for high-tier clients
- **Tiered approach** — e.g., standard tier gets shared template; premium tier gets bespoke

Research should surface:
- What real video agencies do at this scale
- How to parameterize a template well (colors, font, logo placement, motion style)
- What makes end cards feel "professional" vs "template-y" in real estate/title vertical

### 4. Animation / motion design

Should the end card be:
- **Static image card held for 3s** (simplest, boring)
- **Subtle animated reveal** (logo fade-in, text slide-in, ~1s animation + 2s hold)
- **Kinetic typography** (animated text) for the CTA
- **Full motion graphic** (particle effects, logo sting, brand animation) — premium feel
- **Parallax / slow pan on static composition** — "Ken Burns" look, easy to implement

What's the cost/quality curve? What do the best real estate agency social videos do in 2026?

### 5. Integration with existing ffmpeg splicing

End card needs to be attached to the end of the spliced clip. Options:

- **Hard concat** (end of clip 2 → start of end card) — our current splice_clips.py already does this pattern
- **Crossfade** from the final video frame into the end card (200-500ms xfade)
- **Freeze-frame overlay** — final frame of video holds, end card content fades in on top, then full end card
- **Audio handling** — silence? Soft brand sting? Music continuation from any post-production music track?

### 6. Claude skills / AI tooling opportunities

Claude Code has a **skills** system (skill invocation via `/skill-name`). Worth exploring:
- **Skill for end card generation** — `/generate-end-card --client dan-balkun --output path.mp4` driven by skill-defined logic
- **Skill for brand palette extraction** — given a logo, returns 2-3 dominant brand colors (for color-matched end card backgrounds/accents)
- **Skill for auto-layout** — given text length and logo dimensions, picks best layout template
- **Skill for client onboarding** — walks through asset collection and stages data correctly

Research angle:
- Patterns for Claude skills in media-generation pipelines
- When to build a skill vs a CLI tool vs a prompt
- Example skills in the ecosystem we could borrow from

### 7. Caching and regeneration

End card content changes **rarely** per client (phone number update is an event, not a daily change). Every video for a given client uses the **same** end card. This is a massive caching opportunity.

- Render once per client, reuse for all their videos
- Invalidate cache only when branding data changes (detect via hash of branding.json + template version)
- Storage location and naming convention

### 8. Edge cases and constraints

- Very long business names (text wrapping, auto-scale-down)
- Logos with wildly different aspect ratios (wide banner vs square mark)
- Logos requiring light vs dark backgrounds for legibility
- International phone formats
- RTL language support (probably future)
- Accessibility (contrast ratios for readability)

---

## Decision Criteria (for the recommendation)

In order of priority for this project:

1. **Render cost**: must be ~$0 per card (local-only rendering)
2. **Design quality**: must look professionally produced, not "PowerPoint slide"
3. **Scalability**: adding client #50 must not require template duplication or manual work
4. **Dev velocity**: solo developer + AI agent, prefer Python-native or low-ceremony tools
5. **Windows compatibility**: must run on Windows 11 without WSL headaches
6. **Maintainability**: in 12 months, should still be easy to tweak templates or add features
7. **Separation of concerns**: client data edited by non-devs without touching code

---

## Expected Output from Research

For each **Open Design Question (1-8)**:
- **Top 2-3 recommended options** with short comparative analysis
- **Explicit recommendation** with rationale tied to our decision criteria
- **Example code snippet or workflow sketch** if applicable
- **Estimated setup time** and **per-card render time** if relevant
- **Pros and cons** with explicit attention to scalability and cost
- **Real agency examples** (who's producing comparable content well in 2026, what tech do they use)

Then a **final synthesis** section:
- The recommended end-to-end end card architecture
- A phased build plan (MVP → polished → premium-tier)
- List of small reusable Python tools the pipeline should expose (similar to our existing `generate_video.py`, `extract_best_frame.py`, `splice_clips.py`)
- Data schema proposal for per-client branding JSON
- Example command: what will `python tools/generate_end_card.py --client dan-balkun` look like?

---

## Supplementary Info for the Research Agent

- **Inspiration / benchmark videos:** luxury real estate social reels, top title-company IG content, modern DTC brand sign-off animations. Research what these do well and what tools they use.
- **Existing tools in the project** to stay compatible with:
  - `tools/upload_assets.py` — uploads client photos/audio to fal CDN
  - `tools/generate_video.py` — submits generation jobs
  - `tools/download_video.py` — retrieves completed videos
  - `tools/extract_best_frame.py` — samples candidate frames, picks sharpest
  - `tools/splice_clips.py` — ffmpeg concat with seam fades (supports `--reencode` for clean seams)
- **The pipeline's design aesthetic:** small composable CLI scripts, file-based state, no servers, no GUIs. A new tool should feel at home alongside these.
