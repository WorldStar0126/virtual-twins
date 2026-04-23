# End Card Generator

Local, zero-cost renderer that produces a **3-second branded end card** (720×1280 @ 30fps MP4) from a client's `branding.json`. Phase 1 MVP.

## What it produces

A silent 3-second MP4 with matching codec params to fal.ai Seed Dance 2.0 output, designed to concat cleanly onto the end of a spliced video deliverable:

- 720×1280 (9:16 vertical)
- 30 fps, 3.0 seconds, 90 frames
- H.264 `high@4.0`, CRF 18, yuv420p, faststart
- AAC 192kbps stereo @ 48kHz (silent track for Phase 1)

## Layout

Template `centered_stack` (only option in Phase 1) — a vertically centered block:

```
[logo]              max 28% frame height, auto light/dark variant
[display_name]      64pt Manrope Bold, foreground color
[phone]             36pt Inter Medium, foreground color
[email]             36pt Inter Medium, secondary color
[website]           36pt Inter Medium, secondary color
[social icons row]  56px icons, foreground color, shown only if any handle present
```

Motion (3.0s, ease-out-cubic):
- 0.00–0.40s: logo fade/scale in
- 0.35–0.65s: display name rises + fades in
- 0.55–1.05s: contact lines stagger in (60ms apart)
- 0.95–1.20s: social row fades + scales in (skipped if absent)
- 1.20–3.00s: everything held settled

## CLI

```bash
python tools/generate_end_card.py --client dan-balkun
python tools/generate_end_card.py --client dan-balkun --out path/to/end_card.mp4
python tools/generate_end_card.py --path assets/_fixtures/test-client/branding.json
python tools/generate_end_card.py --client dan-balkun --force-rebuild --verbose
```

| Flag | Default | Meaning |
|---|---|---|
| `--client SLUG` | — | Reads `assets/{SLUG}/branding.json` |
| `--path FILE` | — | Direct path to a branding.json |
| `--out PATH` | `output/{slug}/end_cards/latest.mp4` | Where to write |
| `--layout centered_stack` | only option in Phase 1 | |
| `--motion subtle` | only option in Phase 1 | |
| `--strict-contrast` | false | Fail render on WCAG <4.5:1 (else warn only) |
| `--no-cache` | false | Skip the cache check (read path only) |
| `--force-rebuild` | false | Render fresh and overwrite cache |
| `--verbose` | false | Show ffmpeg output |

Output on a cache hit is <100ms (copies from content-addressed cache). First render takes 4–8s.

## Validator

Standalone validation, useful during client onboarding:

```bash
python tools/validate_branding.py --client dan-balkun
python tools/validate_branding.py --path assets/_fixtures/test-client/branding.json --no-slug-check
python tools/validate_branding.py --client dan-balkun --print-normalized
```

Checks:
- JSON Schema structural validation (`schemas/branding.schema.json`)
- Phone parses + `is_valid_number()` via `phonenumbers` — stored in E.164
- Email regex
- Website normalization (scheme/trailing slash stripped, lowercased)
- Social handles normalized (leading `@` stripped, null for empty)
- Referenced logo + font files actually exist
- Slug matches containing folder (unless `--no-slug-check`)

## Branding schema

Full schema at [`schemas/branding.schema.json`](../schemas/branding.schema.json). Skeleton:

```json
{
  "schema_version": "1.0.0",
  "slug": "example-realty",
  "identity": {
    "display_name": "Example Realty Co",
    "industry": "real_estate"
  },
  "contact": {
    "phone_e164": "+12025550123",
    "email": "hello@example.com",
    "website": "example.com"
  },
  "social": {
    "instagram": "examplerealty",
    "tiktok": null,
    "facebook": "examplerealtyco",
    "youtube": "@examplerealty",
    "linkedin": null,
    "x": null
  },
  "visual": {
    "colors": {
      "primary":    {"hex": "#0B3D2E"},
      "secondary":  {"hex": "#C9A96E"},
      "accent":     {"hex": "#E63946"},
      "background": {"hex": "#FAF7F2", "preference": "light"},
      "foreground": {"hex": "#121212"}
    },
    "logo": {
      "light_bg_path": "logo_on_light.png",
      "dark_bg_path":  "logo_on_dark.png"
    }
  },
  "typography": {
    "heading": {"family": "Manrope", "file_path": "../../fonts/Manrope-Bold.ttf"},
    "body":    {"family": "Inter",   "file_path": "../../fonts/Inter-Medium.ttf"}
  }
}
```

| Field | Notes |
|---|---|
| `industry` | One of: `real_estate`, `title_closing`, `mortgage`, `insurance`, `other` |
| `contact.phone_e164` | Any format accepted at ingest; stored as E.164 (e.g., `+14013699100`) |
| `social.*` | Every platform nullable; unknown platforms ignored. Supported: `instagram`, `tiktok`, `facebook`, `youtube`, `linkedin`, `x` |
| `colors.background.preference` | `"light"`, `"dark"`, or `"auto"` (auto uses WCAG luminance of the background hex) |
| `logo.light_bg_path` / `dark_bg_path` | Paths relative to the branding.json directory. Both required — you can point both at the same file if you only have one variant |
| `typography.*.file_path` | Variable TTFs OK; renderer auto-picks "Bold" named instance for heading, "Medium" for body |

## Onboarding a new client (5-step checklist)

1. **Create folder.** `mkdir -p assets/{slug}` where `{slug}` is lowercase alphanumeric + hyphens.
2. **Drop logo files.** Put `logo_on_light.png` (and optionally `logo_on_dark.png`) in `assets/{slug}/branding/` (or wherever — you'll reference them in the JSON).
3. **Copy the schema template.** Create `assets/{slug}/branding.json` using the skeleton above as a starting point; edit every field.
4. **Validate.** `python tools/validate_branding.py --client {slug}` — should print `OK` with a summary.
5. **Render.** `python tools/generate_end_card.py --client {slug}` — writes `output/{slug}/end_cards/latest.mp4`. Watch the video to sanity-check the result.

## Caching

End cards are content-addressed. Cache key = SHA-256 over:
- Full hash of the logo bytes
- Normalized branding fields (phone, email, website, colors, socials, typography)
- Template version, motion variant, renderer ID
- Output params (720×1280, 30fps, 3s)

Cache layout: `output/_cache/end_cards/{slug}/{slug}__v1__subtle__{hash16}.mp4` with a JSON sidecar for debugging. Cache hits are <100ms. Change the branding (e.g., update a phone number) and you get a new hash; previous cache entry stays on disk (remove manually if you want to clean up).

Single-flight protected via `portalocker` locks in `.locks/` (cross-platform).

## Assembling the full deliverable

Use the existing `splice_clips.py` — it handles N clips, so the end card is just clip N+1:

```bash
python tools/splice_clips.py --client dan-balkun \
  --clips clip_1.mp4 clip_2.mp4 end_cards/latest.mp4 \
  --reencode \
  --output final_deliverable.mp4
```

This gives you a single MP4 with: spliced voice clips + 3-second end card, clean seams, 50ms audio fades at each cut, CRF 18 re-encode.

## Tests

```bash
python -m pytest tests/ -v
```

45 tests covering ease function, WCAG luminance, logo variant selection, phone/website/social normalization, schema validation, cache key stability, icon drawing, and a full integration render that ffprobes the output.

## Deferred to later phases

See [NOTES.md](../NOTES.md) for Phase 1 decisions and what's explicitly deferred to Phase 2+.
