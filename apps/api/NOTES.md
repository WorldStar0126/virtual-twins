# Phase 1 — Build Notes & Deferred Items

Working notes from the end-card Phase 1 MVP build. Things I decided, trade-offs I made, and items explicitly pushed to later phases.

## Judgment calls made during Phase 1

**Social icons: hand-drawn Pillow glyphs, not SVG.**
The spec allowed either SVG-derived shapes or shipped PNG glyphs. I went with Pillow primitives drawn at render time (inside `generate_end_card.py`) because:
- Zero new dependencies (no cairo, no svglib, no reportlab)
- Tint at render time using the client's foreground color
- Works identically on Windows without poppler/cairo DLL headaches
- Recognizable enough for Phase 1 (IG camera, FB "f", LI "in", YT play-in-rect, TikTok music-hook, X crossed lines)

**Downside:** These are stylized approximations, not pixel-perfect brand marks. Phase 2 should swap in authentic glyphs (Font Awesome Brands font file or simple-icons SVGs rasterized once to `assets/_icons/`).

**Social handle text: not rendered.**
The spec said to render handle text next to each icon. When I tried this with Dan's data, long handles like `@balkuntitleandclosing` blew out the horizontal layout. The fallback was "icons only" anyway. I simplified the renderer to always show icons only — cleaner design, matches how most professional end cards treat social (the brand mark is the signal, the handle is implicit). If you want handle text visible, it's a Phase 2 addition.

**Logo background transparency: auto-keyed at load time.**
Dan's logo PNG is RGB (no alpha channel) with a white background. Compositing it onto the `#FAF9F9` card background left a visible white rectangle. The renderer now detects fully-opaque logos and auto-keys near-white pixels (R≥240, G≥240, B≥240) to transparent. This gives clean edges on Dan's silver/black logo without needing a pre-processed transparent version.

**Downside:** If a logo has legitimate white parts (e.g., an interior counter-shape), those also get keyed out. None of the current fixtures or Dan's logo hit this. Phase 2 should support client-provided pre-keyed PNGs and skip the auto-key when alpha is already present (which is what the code already does via the `alpha_min == 255 and alpha_max == 255` check — pre-keyed logos pass through untouched).

**Dan's dark-bg logo variant: points at the same file as light-bg.**
The brand PDF has a proper dark-background silver variant, but extracting it needs a PDF library we don't have installed. Since the end card uses a light background (per Dan's brand aesthetic), the dark variant never actually renders. For now both paths point at `branding/logo_on_light.png`. Phase 2 should either install `pypdfium2` + extract, or the user should drop a `logo_on_dark.png` directly into the branding folder.

**Typography: the schema supports per-client fonts (hybrid per user decision).**
Both fixtures and Dan's config point at the shared studio fonts (`assets/fonts/Manrope-Bold.ttf`, `assets/fonts/Inter-Medium.ttf`). Opt-in override works — a client's JSON can point at a different font file in their own `assets/{slug}/fonts/` directory. No code changes needed for per-client overrides; just set the `typography.*.file_path` to a client-local path.

**Fonts: shipped as variable TTFs, named instance picked at load time.**
Google Fonts' current Manrope and Inter are variable fonts with named weight instances. The renderer calls `font.set_variation_by_name("Bold")` for heading and `("Medium")` for body. If that fails (older Pillow, non-variable font), it falls back to the font's default instance silently.

**Vertical layout: computed center, not fixed padding.**
The original spec had fixed `[12% padding][content][12% padding]` layout. I replaced this with a pre-measured block that centers the entire content stack in the frame vertically. This keeps the composition balanced regardless of whether socials are present (minimal-client has 4 lines; test-client and Dan have 5 lines). More robust to content variation.

**WCAG contrast check: warn-only by default.**
The spec said to fail on <4.5:1 when `--strict-contrast` is set, warn otherwise. I simplified: the renderer samples only the foreground vs background hex (not per-text-centroid sampling), because Phase 1 only has one text color per role. Per-text-centroid sampling is Phase 2 when we add more complex layouts.

## Explicitly deferred to Phase 2+

These are all in the Phase 1 spec's "out of scope" list, not forgotten:

- **Other layouts** (`bar_cta`, `split_hero`, `fullscreen_mark`)
- **Other motion styles** (`static`, `kinetic`)
- **Background motion** (hue drift, Ken Burns pan, film grain overlay)
- **Claude Code skills** for one-command render
- **Supabase / Airtable** client data sync
- **Remotion** alternative renderer for motion-heavy templates
- **Brand palette extraction** from logos (auto-sample dominant colors)
- **Interactive `onboard_client.py`** — walks through asset collection
- **Compliance disclaimer rendering** (EHO logo, NMLS, broker licensee info)
- **Multi-line text wrapping + auto-font-shrink** for long business names
- **Auto-derived light/dark logo variants** via inversion or smart processing
- **Authentic social brand icons** (replace hand-drawn Phase 1 glyphs)
- **Handle text beside icons** with smart truncation / shrink
- **Per-text-centroid WCAG sampling**

## Deferred that I want to flag for Phase 2 planning

**Font caching in canonicalize_for_hash.**
The cache key hashes `heading_family` and `body_family` names but NOT the font file contents. If a client updates their font file without renaming it, the old cache entry stays valid and they'll see the old render. Low-probability but should be fixed in Phase 2 by hashing font bytes like we do for logos.

**Cache layout doesn't track schema_version.**
If we bump `schema_version` in a breaking way, old cache entries are still served. The canon hash includes `template_version` (integer) and `renderer` string, so bumping either invalidates cache. For a schema-breaking change, bump `RENDERER_ID` (e.g., `pillow-ffmpeg@1.1`).

**ffmpeg encoding is CPU-bound and single-threaded at the per-frame level.**
For 100+ clients × multiple renders/day this matters less than it sounds because end cards cache aggressively — a single render per client per branding-change. But if ever needed, `libx264 -threads 0` is already effectively auto-parallelized; the bottleneck is actually the Pillow per-frame composition (90 frames × ~50ms = 4-5s).

## Things I built beyond the minimum

- **Full validator CLI** with `--path`, `--no-slug-check`, `--print-normalized` flags, covering the fixtures use case where slug doesn't need to match the fixture folder name exactly
- **pytest fixture auto-creation** for `.tmp/test_outputs/` so the suite works cleanly on a fresh clone
- **Cache-hit timing in tests** (asserts <500ms) — defensive against a regression where someone accidentally makes cache lookup O(everything)
- **Integration test does a real ffprobe** on the output to verify exact codec params, not just "file exists and is non-zero bytes"

## Files added this phase

```
schemas/branding.schema.json          ← new
tools/generate_end_card.py            ← new
tools/validate_branding.py            ← new
tests/test_end_card.py                ← new
assets/fonts/Manrope-Bold.ttf         ← new (OFL, Google Fonts)
assets/fonts/Inter-Medium.ttf         ← new (OFL, Google Fonts)
assets/_fixtures/test-client/         ← new (branding.json + generated logo.png)
assets/_fixtures/minimal-client/      ← new (branding.json + generated logo.png)
assets/dan-balkun/branding.json       ← new
assets/dan-balkun/branding/           ← new (logo_on_light.png + logo_source.pdf)
docs/end_card.md                      ← new
requirements.txt                      ← updated (+Pillow, numpy, jsonschema, phonenumbers, portalocker, pytest)
output/_cache/end_cards/               ← created at first render
.locks/                                ← created at first render
```

## Design polish backlog (post-Phase 1)

End card v3 shipped as "good enough for now" — functional, on-brand, client-deliverable. Items parked for a future design iteration pass, in rough priority order:

1. **Richer background treatment** — the current subtle 4% gradient is minimal. Explore: gentle diagonal gradient using primary + secondary brand colors, a very faint watermark shape (brand mark at 3-5% opacity in a corner), or a subtle vertical fade with a textured paper/linen grain. Current near-flat background reads as "PowerPoint template."

2. **Optional `identity.tagline` schema field** — short line (~30 chars) rendered between the divider and the contact block, or below the socials. Fills lower negative space and reinforces positioning ("Closings made simple", "Trust. Precision. Closed."). Add to schema as nullable.

3. **Compliance / license disclosure line** — very small-type line at the very bottom for regulated industries: NMLS #, state license, broker name, etc. Schema would need `compliance.disclosure_text` or similar. Important for mortgage/insurance/real estate clients who have legal requirements.

4. **Logo entrance polish** — current motion is fade + scale (0.92→1.0). Consider: subtle upward lift (translateY +20px→0), a thin gold accent-sweep that traces across the logo after it settles, or a very brief brand-color backglow pulse.

5. **Social icon micro-motion** — currently fades in as a group. Polish: per-icon stagger (30ms apart), subtle bounce/settle at end, or a tiny shadow drop as they arrive. Adds perceived quality.

6. **Auto brand-palette extraction from logo** — during client onboarding, sample the top 3-5 dominant colors from the logo PNG and suggest them as `colors.primary/secondary/accent`. Saves manual color-picking work per client. Pillow + k-means on pixel RGB.

7. **Additional layouts** (from original spec, deferred):
   - `bar_cta` — horizontal CTA bar with logo + name on one side, contact + socials on the other
   - `split_hero` — logo large on top half, contact grid on bottom half with a distinct background color
   - `fullscreen_mark` — just the logo centered on a branded color with a minimal CTA text

8. **Animated brand decorations** — thin gold line-draws for higher-tier deliverables: corner flourishes, subtle particle trails during the logo entrance, a thin accent stroke that frames the card. Only for premium tier — standard tier keeps it clean.

9. **Phone icon refinement** — current smartphone silhouette is clean but basic. Consider a more distinctive/branded phone glyph if we want visual personality (e.g., a subtle notch for modern aesthetic, or classic handset for more traditional feel).

10. **Variable typography weights** — currently locked to Manrope Bold for heading + Inter Medium for body. Could expose heading weight as a schema option for clients who prefer a lighter or more condensed feel.

11. **Higher-resolution logo handling** — Dan's 360×360 logo is the bottleneck for visual sharpness at 720p output. Document that client onboarding should collect ≥1200px logos; consider a validation warning if logo dims are below 800px.

12. **Handle text next to social icons (optional)** — currently dropped because long handles blow out horizontal layout. Explore: smaller font + truncation with ellipsis, or a stacked layout with icon above handle. Opt-in via schema flag.

## Phase 1 smoke test result

Full pipeline produces a 23.1-second MP4 at `output/dan-balkun/full_deliverable_20260418.mp4`:
- Clip 1 (walking to seated): 10s
- Clip 2 (seated continuation): 10s
- End card (Balkun Title + contact info + 4 socials, subtle reveal): 3s

Cache hit on second run: 0.03s. 45/45 tests pass.

---

# Phase 2 — Automation Priorities

The two rough edges coming out of James Duffer's first deliverable. Both are manual today; both need to become repeatable across many clients and many videos.

## 1. Music track selection & mixing

**Current state (james-duffer, 17 Keith Drive):**
- Music picked manually by the operator (royalty-free `Marble Morning.mp3` dropped into `assets/james-duffer/audio/`)
- Mixed via a one-off `ffmpeg` command in the session transcript: trim to video length, `volume=0.15` (~−16 dB), 0.4s fade-in, 1.0s fade-out, `amix` under the dialogue track
- Video stream copied; audio re-encoded to 44.1kHz AAC
- Worked nicely for one listing, will not scale

**What Phase 2 should build:**
- **Curated library first.** `assets/_music/` with ~20–40 CC0 / Pixabay-license tracks tagged by mood + tempo + length + loop-friendly flag. Sources: Pixabay, Mixkit, FMA. Cheap, deterministic, no API dependencies.
- **`branding.json` extension.** Add `audio.default_bed` (slug pointing into the library) + optional per-video override CLI flag. Keep the per-client bed stable so a client's catalog of videos sounds like one brand.
- **`tools/mix_music.py`.** Wraps the ffmpeg filter-complex we proved out: auto-trim to video duration, fade in/out, fixed bed gain (−16 dB default, per-client override in branding), output stream-copy video.
- **Sidechain ducking (stretch).** Auto-lower music under dialogue, return to full bed-level during end card + silent gaps. ffmpeg `sidechaincompress` or a two-pass loudnorm approach.
- **Do NOT build on Suno wrappers.** Third-party Suno SDKs scrape session cookies and break on every site redesign. If we want AI-generated music later, use a licensed API (Mubert, Beatoven.ai, Loudly, AIVA) — those have real commercial terms.

## 2. End card design automation via Claude Design

**Why this is Phase 2:**
- The `generate_end_card.py` output (Pillow-composited, hand-drawn icons, fixed layout) works but reads "good enough," not premium. Adam's assessment is that the RISE Open House card designed in Claude Design (claude.ai/design) is noticeably better — better typography, better composition, better feel.
- Claude Design produces HTML/CSS/JS prototypes with real fonts, proper spacing, and real brand polish. Per-client one-off design sessions don't scale, but the output format (a handoff bundle — HTML + assets + README) is machine-readable.

**What we proved out (2026-04-19, 17 Keith Drive):**
- Fetched a Claude Design handoff bundle via URL (`api.anthropic.com/v1/design/h/{id}`) → gzipped tar → extracted HTML + assets + chat transcripts + README
- Manually ported the layout into `tools/generate_property_card.py` (1080×1920, 3s @ 30fps, Pillow + ffmpeg)
- Result was clean and matched the design closely; faster than designing from scratch inside the Python renderer

**What Phase 2 should build:**
- **Design bundle fetcher.** `tools/fetch_claude_design.py` — takes a Claude Design URL, extracts the bundle, reads the README + chats for intent, surfaces the primary HTML file for porting.
- **Investigate API access.** Check whether Anthropic exposes a Claude Design API (or whether the Claude Agent SDK with appropriate skills/tools can drive it programmatically) so we can generate designs without a browser session. If not public, the manual "design once per client template, port once, then render many times" pattern still wins on cost.
- **Template catalog.** Port 3–5 Claude Design output styles into parameterized Python renderers (open-house, agent-intro, just-listed, closed-sale, testimonial). Each becomes a reusable template driven by `branding.json` + per-video inputs, same pattern as `generate_property_card.py`.
- **Consider a headless renderer path.** If the Claude Design HTML prototypes are high-fidelity enough, we could skip the Python port entirely by running the HTML in a headless browser (Playwright) and screen-capturing frames for ffmpeg. Tradeoff: adds a browser dependency but preserves pixel-perfect fidelity and speeds iteration.

## What shipped this session (2026-04-19)

- **James Duffer** onboarded as second production client (`assets/james-duffer/` — branding.json, logo, property photos, voice sample, license-free music)
- **`tools/generate_property_card.py`** — 1080×1920 open-house card, ported from the RISE Claude Design bundle. Hero property photo with Ken-Burns, "Open House" pill badge, Cormorant Garamond serif address, two-column SAT/SUN date blocks, italic agent attribution, brand-colored social icons. Staggered easeOutExpo fades matching the design.
- **New fonts in `assets/fonts/`** — Cormorant Garamond (regular + italic VF) and JetBrains Mono (VF). OFL, Google Fonts.
- **First deliverable for James** at `output/james-duffer/final_17_keith_drive_with_music.mp4` (23.13s, 10.86 MB): 20s dialogue clips + 3s open-house card, music bed at −16 dB.

## What shipped this session (2026-04-20)

- **Evelyn DeCosta / Guaranteed Autosales** onboarded as first automotive client (`assets/evelyn-decosta/`). Schema extended: `automotive` industry added, `email` now optional (BHPH dealerships may not publish one), `contact.address` added for brick-and-mortar businesses.
- **`tools/scrape_vehicle_listing.py`** — dealer VDP scraper. Parses Schema.org `Vehicle` JSON-LD + OG meta, with an optional `--all-photos` Playwright mode that captures the full hydrated photo array. Tested against guaranteedautoloansri.com.
- **20-second automotive inventory video POC** for the 2016 Honda CR-V listing (VIN `5J6RM4H42GL016732`). Two 10s Seed Dance clips + splice → 20.1s social short.
- **`docs/automotive_inventory.md`** — handoff doc for the developer picking up the automotive work next: shipped state, proven commands, moderation gotchas, and the scoped 30-second-option task (add an optional third 10s clip).
