# Generate Client Video

## Objective
Produce a short (8-15 second) AI-generated video of a client speaking to camera using their reference photos and audio via fal.ai Seed Dance 2.0.

## Required Inputs
- **Client name** (used as folder name, e.g., `dan-balkun`)
- **Reference photos** — Multiple angles/expressions of the client (up to 9 images, JPEG/PNG/WebP, max 30MB each)
- **Audio clip** — Client's voice recording or script audio (WAV/MP3, max 15MB, max 15 seconds)
- **Prompt** — Description of what the video should show
- **Settings** — Duration, resolution, aspect ratio, fast vs standard

## Steps

### 1. Prepare Assets
Organize the client's files into the correct folder structure:
```
assets/{client-name}/
    photos/    ← Drop reference images here
    audio/     ← Drop audio clips here
```

**Photo tips for best results:**
- Include multiple angles: front-facing, slight left/right turns, different expressions
- Good lighting, clean background
- High resolution preferred but under 30MB per image

**Audio requirements:**
- Clear voice recording, minimal background noise
- WAV or MP3 format
- Max 15 seconds total across all audio files

### 2. Upload Assets to fal CDN
```bash
python tools/upload_assets.py --client {client-name}
```
This uploads all photos and audio to fal's CDN and saves the URLs to `.tmp/{client}_urls.json`.

### 3. Generate Video
```bash
python tools/generate_video.py \
    --client {client-name} \
    --prompt "Your prompt here" \
    --duration 10 \
    --resolution 480p \
    --aspect-ratio 9:16
```

**Start with 480p for testing** (~$0.97 for 4 seconds) before running at 720p production quality.

Add `--fast` flag for the cheaper endpoint ($0.24/sec vs $0.30/sec).

**Prompt format:** Use `@Image1`, `@Image2`, etc. to reference uploaded photos (in the order they were uploaded). Use `@Audio1` to reference audio.

### 4. Download & Review
```bash
python tools/download_video.py --client {client-name}
```
Video saves to `output/{client-name}/video_{timestamp}.mp4`.

### 5. Iterate
- Try different prompts, swap which images are referenced
- Test `--fast` vs standard quality
- Use `--seed {number}` for reproducible results
- Try different aspect ratios: `9:16` (social/vertical), `16:9` (landscape), `1:1` (square)

## Prompt Templates

### Title/Closing Company (Dan Balkun style)
```
@Image1 is a professional in the title and closing industry, speaking directly to camera with confidence. @Audio1 provides the voiceover. The setting is a modern office. Camera is steady, slight slow zoom in.
```

### Just Sold Announcement (Realtor)
```
@Image1 is a real estate agent speaking excitedly to camera about a successful closing. @Audio1 provides the voiceover. Bright, professional setting. Camera steady with slight movement.
```

### Market Update (Realtor)
```
@Image1 is a real estate professional delivering a market update to camera. @Audio1 provides the voiceover. Clean, professional background. Steady camera, slight dolly in.
```

### Personal Brand Introduction
```
@Image1 introduces themselves to camera with warmth and professionalism. @Audio1 provides the voiceover. Modern, well-lit setting. Camera smooth and steady.
```

### Holiday/Seasonal Greeting
```
@Image1 delivers a warm holiday greeting to camera. @Audio1 provides the voiceover. Festive but professional setting. Camera steady, gentle zoom.
```

## Cost Reference
| Duration | Resolution | Standard | Fast |
|----------|-----------|----------|------|
| 4 sec    | 480p      | ~$1.20   | ~$0.97 |
| 4 sec    | 720p      | ~$1.21   | ~$0.97 |
| 10 sec   | 720p      | ~$3.00   | ~$2.42 |
| 15 sec   | 720p      | ~$4.55   | ~$3.63 |

## Edge Cases
- **Upload fails:** Check file sizes (images < 30MB, audio < 15MB). Check FAL_KEY in .env.
- **Generation timeout:** fal.ai jobs typically complete in 1-2 minutes. If it hangs, check your internet connection.
- **Poor quality output:** Try different reference images, adjust prompt wording, use standard instead of fast.
- **Audio sync issues:** Ensure audio is clean and matches the desired video duration.
