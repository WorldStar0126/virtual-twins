# Automotive inventory videos — handoff

Per-vehicle short-form videos for automotive dealership clients. Each listing gets a short
social clip where the dealership spokesperson showcases the car, talking through a few
highlights and a CTA. First client: `evelyn-decosta` (Guaranteed Autosales, Johnston, RI),
spokesperson Evelyn DeCosta.

## Status (2026-04-20)

**Shipped:**
- Dealer listing scraper — [tools/scrape_vehicle_listing.py](../tools/scrape_vehicle_listing.py)
  - Parses Schema.org `Vehicle` JSON-LD + Open Graph + `exposed_vars`.
  - Optional `--all-photos` flag runs headless Chromium (Playwright) to capture
    the full photo array after the VDP's JS hydrates.
- Proof-of-concept for the **20-second** format (two 10s Seed Dance clips, spliced).
  Worked example: 2016 Honda CR-V (VIN `5J6RM4H42GL016732`) at
  [output/evelyn-decosta/honda-crv-2016/](../output/evelyn-decosta/honda-crv-2016/)
  (gitignored; regenerate as needed).

**Next milestone (this handoff):** make the format extensible to **30 seconds** by
adding an optional third 10s clip. The workflow should be "2 clips or 3 clips" depending
on what the client wants per-listing.

## What the proven 20-second flow looks like today

1. Scrape the listing:
   ```
   python tools/scrape_vehicle_listing.py \
     --url https://guaranteedautoloansri.com/inventory/2016-Honda-CR-V-5J6RM4H42GL016732 \
     --out .tmp/inventory/honda-crv-2016.json --pretty --all-photos
   ```
   Fields extracted: year/make/model/trim, VIN, price, mileage, engine, transmission,
   drivetrain, body type, condition, full marketing description, hero + additional
   photo URLs.

2. Download + convert photos to JPEG (the S3 bucket serves AVIF):
   ```
   # See .tmp/inventory/honda-crv-2016/photos/ for the working set.
   ffmpeg -i {image}.avif -q:v 3 {image}.jpg
   ```

3. Pick 1–2 clean car angles, stage alongside Evelyn's reference photos under
   [assets/evelyn-decosta/photos/](../assets/evelyn-decosta/photos/). Current set:

   | Idx | File                                     | Role                            |
   |----:|------------------------------------------|---------------------------------|
   |  1  | evelyn_closeup_mouth_open.jpg            | face (mouth open) — **proven**  |
   |  2  | evelyn_closeup_mouth_slight.jpg          | face (mouth slight)             |
   |  3  | evelyn_closeup_mouth_slight_2.jpg        | face (mouth slight) alt         |
   |  4  | evelyn_midbody_1.jpg                     | body/pose — **proven**          |
   |  5  | evelyn_midbody_2.jpg                     | body/pose alt                   |
   |  6  | honda-crv-2016_driverside3q.jpg          | car driver-side 3/4             |
   |  7  | honda-crv-2016_front.jpg                 | car front — **proven**          |

4. Upload to fal CDN, generate both clips, splice. Proven commands and full prompts
   live in the worked shoot-plan at `.tmp/inventory/honda-crv-2016.shoot.md`
   (regeneratable from the JSON scrape + the patterns in this doc).

## What the developer should build next

### Task: add an optional third 10s clip → 30s total deliverable

**Goal.** A client can request a 30s version of an inventory video. The pipeline
generates three 10s Seed Dance clips (instead of two) and splices them.

**Suggested third-clip content (discuss with Adam before locking in):**
- **Option A — interior showcase.** Evelyn seated in the driver's seat or standing
  at an open door, gesturing to interior features (steering wheel, dashboard, cargo).
  Dialogue: specific features from the scrape (keyless entry, power windows, etc.).
- **Option B — closer/soft CTA.** A warmer, slower closer with an explicit
  invitation to visit/apply. Uses the existing dealership-exterior setting.
- **Option C — financing pitch.** Focused on the "any credit situation" message,
  cutaway to Evelyn mid-body at the front of the car.

Option A has the best visual variety (interior vs. two exterior shots). Option B is
the safest (uses proven reference set).

**Architectural work to make this clean:**

1. **Separate per-listing photos from the client's permanent reference set.**
   Today the working photos (Evelyn) and per-vehicle photos (`honda-crv-2016_*.jpg`)
   live side-by-side in `assets/evelyn-decosta/photos/`. This pollutes the client
   asset pool for every new listing. Proposed structure:
   ```
   assets/evelyn-decosta/
     photos/                  ← permanent references (Evelyn only)
     listings/
       {vin}/
         vehicle.json         ← scraped data
         photos/              ← vehicle photos (downloaded + converted)
         shoot.md             ← per-listing prompts / commands
   ```
   `tools/upload_assets.py` would grow a `--listing {vin}` flag to merge the client's
   permanent photos with that listing's vehicle photos for a single upload.

2. **Codify the 2-clip / 3-clip flow in a tool or SOP.**
   Current flow is: shell out to `upload_assets.py`, then `generate_video.py` twice
   (or three times), then `download_video.py`, then `splice_clips.py`. A small
   `tools/generate_inventory_video.py` wrapper could:
   - Accept `--listing {vin} --length 20|30`
   - Read per-listing prompt templates (stored per client or globally)
   - Run the upload → generate → download → splice pipeline end-to-end
   - Fail gracefully on moderation rejections (see below)

### Critical gotchas to know about before touching this

**1. Seed Dance moderation is strict and image-specific.**
During the Honda CR-V POC, we hit four `content_policy_violation` rejections in a
row on Clip 2. Summary of what we learned:

| What we tried                                                   | Moderator verdict |
|-----------------------------------------------------------------|-------------------|
| Clip 1 (first take): `midbody_1` + `closeup_mouth_open` + `front` car | ✅ accepted       |
| Clip 2: AI-generated last-frame of Clip 1 as reference          | ❌ rejected       |
| Clip 2: alternate Evelyn photos + `rear 3/4` car photo          | ❌ rejected       |
| Clip 2: AI last-frame + `driver-side 3/4` car photo             | ❌ rejected       |
| Clip 2: **Clip-1-proven image set** + new prompt (walkaround)   | ✅ accepted       |

Diagnosis that held up: certain *alternate* reference photos trigger the moderator.
We never isolated which exact photo detail was the trigger; what did work was
falling back to the proven set + using a **verbal setting lock** in the prompt.

**Rules of thumb we derived:**
- Don't feed AI-generated frames back in as reference images for likeness-sensitive
  generations. The moderator treats these as problematic.
- If an alternate photo fails twice, move on; don't try to "fix" it — swap to a
  proven one and lock the setting verbally.
- The bytedance/seedance-2.0 **standard** endpoint is what we used. Unknown whether
  the `fast` endpoint has different moderation behavior; worth a test if rejections
  become a pain.

**2. Moderation failures don't cost money** (the job is killed before generation),
but they do eat iteration time. Retry a few times before pivoting.

**3. The scraper currently pulls one full photo set, but the images carry dealer
overlays** (price banners, phone numbers, "Guaranteed Auto Sales" logos). In-prompt
suppression works:

> Important: the vehicle must appear clean and unbranded. Do not render any text
> overlays, promotional banners, price badges, dealer logos, phone numbers, or
> watermarks visible in @Image3 — render only the car itself and its natural
> surroundings without any of those graphics.

Long-term, the dealership has offered to supply unbranded raw photos from their DMS
for premium use. Until that's wired up, prompt suppression is the fallback.

**4. Continuity across a splice.** Our first attempt at Clip-2 continuity used the
last frame of Clip 1 as a reference image — this triggered moderation. The approach
that worked was describing the setting verbally in the Clip 2 prompt ("paver pavement,
dealership building with blue accent stripe on the left, evergreen trees on the
right, blue sky with scattered clouds") and describing Evelyn's outfit explicitly
("long black pinstripe blazer over a black turtleneck, dark pants, long dark hair").
Seed Dance still produces a slightly different setting, but it reads as close
enough for a 20s social clip.

### Relevant files

- [tools/scrape_vehicle_listing.py](../tools/scrape_vehicle_listing.py) — the scraper
- [tools/generate_video.py](../tools/generate_video.py) — fal.ai Seed Dance wrapper
- [tools/upload_assets.py](../tools/upload_assets.py) — fal CDN upload
- [tools/download_video.py](../tools/download_video.py) — pulls the rendered MP4
- [tools/splice_clips.py](../tools/splice_clips.py) — multi-clip concat (with seam fades)
- [assets/evelyn-decosta/branding.json](../assets/evelyn-decosta/branding.json) — client config
- [schemas/branding.schema.json](../schemas/branding.schema.json) — schema
  (note: `automotive` industry added, `email` now optional, `contact.address` added for
  brick-and-mortar businesses)
- [NOTES.md](../NOTES.md) — running build notes + Phase 2 priorities
