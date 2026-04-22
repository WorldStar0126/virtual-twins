# Agent Instructions — Virtual Twins Video Pipeline

You're working inside the **WAT framework** (Workflows, Agents, Tools) for **Virtual Twins**, an AI video production agency. This project automates short-form video generation using fal.ai's Seed Dance 2.0 API.

## Business Context

Virtual Twins creates AI-generated video content for clients (realtors, title companies, etc.). This pipeline handles the **quick clip tier** — 8-15 second social media videos where clients appear speaking to camera. These are the affordable, scalable product, not the premium 30s-2min edited productions.

## The WAT Architecture

**Layer 1: Workflows** — Markdown SOPs in `workflows/`. Define objectives, inputs, tools to use, outputs, and edge cases.

**Layer 2: Agents (You)** — Read the relevant workflow, run tools in sequence, handle failures, ask clarifying questions when needed.

**Layer 3: Tools** — Python scripts in `tools/` that do the actual work. API calls, file uploads, video generation, downloads.

## How to Operate

1. **Check `tools/` first** before building anything new
2. **Learn and adapt when things fail** — read the error, fix the script, retest, update the workflow
3. **Keep workflows current** — but don't create/overwrite without asking
4. **Cost awareness** — Always confirm before running generation jobs. Standard: ~$0.30/sec, Fast: ~$0.24/sec at 720p. A 10-second 720p video costs ~$2.50-$3.00.

## fal.ai API Reference

**Primary Endpoint:** `bytedance/seedance-2.0/reference-to-video`
**Fast Endpoint:** `bytedance/seedance-2.0/fast/reference-to-video`

**Constraints:**
- Up to 9 reference images (JPEG/PNG/WebP, max 30MB each)
- Up to 3 audio files (WAV/MP3, max 15MB each, 15s total)
- Duration: 4, 5, 10, or 15 seconds
- Resolution: 480p or 720p
- Aspect ratios: 16:9, 9:16, 1:1, 4:3, 3:4, 21:9
- Prompt references: `@Image1`, `@Image2`, `@Audio1`, etc.

**Auth:** `FAL_KEY` environment variable (stored in `.env`)

## File Structure

```
assets/{client}/photos/    # Client reference images
assets/{client}/audio/     # Client voice/music clips
output/{client}/           # Generated videos
.tmp/                      # CDN URL caches, result metadata (regenerable)
tools/                     # Python scripts
workflows/                 # Markdown SOPs
.env                       # API keys (NEVER commit)
```

## Key Rules

- **Never commit .env or credentials**
- **Always use 480p for test runs** to save money
- **Confirm with user before any generation job** that costs money
- Local files are for processing. Final deliverables go to clients via cloud services.
