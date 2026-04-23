# Virtual Twins Video Pipeline — Developer Handoff

## What This Is

An AI video production pipeline for **Virtual Twins**, an agency that creates **20-25 second social media videos** where clients appear speaking to camera. Built on **fal.ai's Seed Dance 2.0** API. Target market: real estate agents, brokerage companies, title companies.

Seed Dance 2.0 currently maxes out at **15 seconds per generation**. To hit our 20-25 second target, each video is composed of **2 generated clips spliced together** (e.g., 10s + 10s or 15s + 10s) plus a **3-second animated end card** with the client's branding and contact info.

## What's Been Built

### Architecture: WAT Framework (Workflows, Agents, Tools)

```
fal-video-pipeline/
├── CLAUDE.md              # Agent instructions (Claude Code reads this)
├── .env                   # FAL_KEY (never commit)
├── assets/
│   └── {client}/
│       ├── photos/        # Reference images (PNG/JPG/WebP, max 30MB each)
│       └── audio/         # Voice reference clips (MP3/WAV, max 15MB, 15s total)
├── tools/
│   ├── upload_assets.py   # Upload client assets to fal CDN
│   ├── generate_video.py  # Submit generation job to Seed Dance 2.0
│   └── download_video.py  # Download completed video to output/
├── workflows/
│   └── generate_client_video.md  # Step-by-step SOP
├── .tmp/                  # CDN URL caches, result metadata (regenerable)
│   ├── {client}_urls.json     # Uploaded asset URLs
│   └── {client}_result.json   # Last generation result + video URL
└── output/
    └── {client}/          # Downloaded video files (video_{timestamp}.mp4)
```

### Tools (Python Scripts)

**1. `tools/upload_assets.py`**
- Uploads all photos + audio from `assets/{client}/` to fal.ai CDN
- Saves URL mapping to `.tmp/{client}_urls.json`
- No cost to run
```bash
python tools/upload_assets.py --client dan-balkun
```

**2. `tools/generate_video.py`**
- Submits a generation job to Seed Dance 2.0 (Standard or Fast endpoint)
- Supports selecting specific images via `--images` flag (critical for cost control)
- Saves result JSON + video URL to `.tmp/{client}_result.json`
```bash
python tools/generate_video.py \
  --client dan-balkun \
  --images 8 4 5 6 \
  --prompt "@Image1 @Image2 @Image3 @Image4 are reference images of Dan..." \
  --duration 10 \
  --resolution 720p \
  --aspect-ratio 9:16 \
  --fast  # omit for Standard quality
```

**3. `tools/download_video.py`**
- Downloads the most recent generated video to `output/{client}/`
```bash
python tools/download_video.py --client dan-balkun
```

### Dependencies

```
fal-client
python-dotenv
requests
```

## Critical Knowledge

### How Seed Dance 2.0 Actually Works

It's NOT a single model — it's a **multi-model pipeline** that fal runs behind the scenes:
- `image-to-image` — processes reference photos
- `image-to-video` — additional processing
- `voice-clone` — clones voice from audio reference
- `speech/tts` — text-to-speech with cloned voice
- `speech-to-text` — transcribes audio reference
- `upscale/image` — upscales references
- `reference-to-video` — the actual video generation

Each sub-model bills separately. This is why cost management matters.

### Cost Data (Tested 2026-04-15)

| Config | Actual Cost | Gen Time |
|--------|-------------|----------|
| 8 images, 10s, 480p, Fast | ~$10 | ~3 min |
| 4 images, 10s, 480p, Fast | ~$2 | ~3 min |
| 4 images, 10s, 720p, Fast | ~$2-3 | ~3 min |
| 4 images, 10s, 720p, Standard | ~$3 | ~3 min |
| 4 images, 10s, 720p, Standard, multi-scene | ~$3 | ~4 min |

**The #1 cost lever is image count.** Going from 8 to 4 images dropped cost from ~$10 to ~$2-3. Resolution, endpoint tier (Fast vs Standard), and prompt complexity have minimal cost impact.

**Production sweet spot: 4 images, 720p, Standard — ~$3 per 10s video.**

### Prompting Rules

1. **Dialogue must be written in the prompt.** The audio file is only a voice reference for cloning — it does NOT provide the words. If you don't write what the person says in the prompt, the speech will be garbled.

2. **Always specify wardrobe.** Reference images show various outfits. The prompt controls what appears in the video.

3. **Be cinematically detailed.** Include: camera angles, camera movement, lighting, setting, expressions, scene transitions. Vague prompts = poor results.

4. **Multi-scene prompts work.** You can describe Scene 1, Scene 2, Scene 3 with cuts and transitions. Doesn't increase cost, just adds ~1 min to generation time.

### Example Prompt (Multi-Scene, Tested & Working)

```
@Image1 @Image2 @Image3 @Image4 are reference images of Dan. Scene 1: Wide exterior
shot of a sleek black Mercedes-AMG GLE SUV speeding down a palm-tree-lined boulevard
at golden hour. The camera tracks alongside the vehicle in a smooth dolly shot,
capturing motion blur on the road. Scene 2: Cut to interior — Dan is behind the wheel
wearing a tailored charcoal suit with an open collar white shirt. The camera is mounted
on the dashboard, slowly pushing in toward his face. Soft sunlight streams through the
driver's window. He grips the steering wheel confidently, glances at the camera with a
smirk and says: "You know what's faster than this Mercedes? Our closings." He laughs
and looks back at the road. Scene 3: Cut to exterior rear angle — the Mercedes
accelerates away from camera, taillights glowing, slight lens flare from the setting
sun. Cinematic color grading, shallow depth of field, film grain. @Audio1 is the voice
reference.
```

### API Constraints

- Up to 9 reference images (JPEG/PNG/WebP, max 30MB each) — but use 3-4 for cost
- Up to 3 audio files (WAV/MP3, max 15MB each, 15s total)
- Duration: 4, 5, 10, or 15 seconds
- Resolution: 480p or 720p
- Aspect ratios: 16:9, 9:16, 1:1, 4:3, 3:4, 21:9
- Prompt references: `@Image1`, `@Image2`, `@Audio1`, etc.

### Image Selection Best Practices

Choose 3-4 reference images that cover:
- One clean **front-facing** headshot
- One **left profile**
- One **right profile**
- One **full/mid body** shot (for build and proportions)

## Phase 2 — What to Build Next

### 1. Clip Splicing System

**Goal:** Produce ~20-25 second complete videos by combining 2 generated clips + an end card.

**Preferred formats:**
- **Option A:** 10s clip + 10s clip + 3s end card = **23 seconds**
- **Option B:** 15s clip + 10s clip + 3s end card = **28 seconds**

**Why 2 clips, not 3-4:** Shorter clips (2s, 4s, 5s) require 3-4+ generations to hit 20s, which increases production complexity, cost, and the number of seams to manage. Two longer clips keep it simple — one splice point instead of three.

**Critical requirement — visual consistency across clips:**
Both clips must feel like one continuous video, not two separate productions. To achieve this:
- **Same wardrobe** — both prompts must specify identical clothing. Two scenarios:
  - **Client's original outfit:** If the client wants to wear what they were photographed in, reference the original photos to maintain consistency across clips.
  - **Custom/different outfit:** If the prompt specifies new attire (e.g., a suit they weren't photographed in), we need to capture or extract a reference image of that outfit from clip 1's output to feed into clip 2's generation. This ensures the AI-generated wardrobe matches across both clips rather than drifting. A potential approach: extract a clean frame from clip 1, use it as an additional reference image for clip 2.
- **Same setting/location** — both clips should share the same environment (e.g., both in the same office, same car, same outdoor location)
- **Camera variety is fine within a clip** — Seed Dance handles multiple camera angles, pans, and scene cuts within a single generation. Use that for visual interest instead of relying on clip-to-clip variety.
- **Consistent lighting/color grading** — match the lighting direction, time of day, and color tone in both prompts
- **Shared seed exploration** — test whether using the same or similar seeds across clips helps maintain visual consistency

**What needs to be built:**
- A "shot list" or "video plan" config that defines: clip count, durations, per-clip prompts, shared style directives (wardrobe, setting, lighting)
- A shared style block that gets injected into every clip's prompt to enforce consistency
- ffmpeg concatenation with optional crossfade transitions between clips
- Final assembly: clip 1 + clip 2 + end card → single MP4 output

### 2. End Card Generator
Every video needs a closing CTA with the client's:
- Company logo
- Phone number
- Email address
- Optionally: website, social handles

Options to explore:
- **Pre-produced templates** — Design end cards in Canva/Figma, export as video clips, attach via ffmpeg
- **Dynamic generation** — Programmatically generate end cards from client data (Pillow/MoviePy/ffmpeg)
- **Hybrid** — Template with dynamic text overlay

### 3. Multi-Client Scale Infrastructure
- Client config/profile system (name, assets, branding, preferred prompts)
- Batch generation capability
- Asset management (organized uploads, versioning)
- Job tracking and cost logging per client

### 4. Team Frontend (Medium-Term)
Internal UI where operators can:
- Select a client
- Choose/upload reference images
- Pick a prompt template or write custom
- Configure settings (duration, resolution, etc.)
- Generate, preview, approve, deliver

### 5. Automation Pipeline (Long-Term)
- Client self-serve asset upload
- Auto-generation triggers
- Approval workflows
- Delivery to client's social channels

## First Client

**Dan Balkun** — title/closing industry professional
- 8 reference photos uploaded (use best 4: no smile front-facing, right profile, left profile, full body)
- 1 audio reference (dan vo line 4 new.mp3)
- 5 test videos generated in `output/dan-balkun/`
- Seeds saved in `.tmp/dan-balkun_result.json` for reproducibility

## Getting Started

1. Clone the repo
2. `pip install fal-client python-dotenv requests`
3. Create `.env` with `FAL_KEY=your_key_here`
4. Run: `python tools/upload_assets.py --client dan-balkun`
5. Run: `python tools/generate_video.py --client dan-balkun --images 8 4 5 6 --prompt "..." --duration 10 --resolution 480p --aspect-ratio 9:16 --fast`
6. Run: `python tools/download_video.py --client dan-balkun`
