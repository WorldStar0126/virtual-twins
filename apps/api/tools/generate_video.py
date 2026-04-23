"""Generate a video using fal.ai Seed Dance 2.0 reference-to-video.

Usage:
    python tools/generate_video.py --client dan-balkun --prompt "@Image1 speaks to camera. @Audio1 provides voiceover." --duration 10
    python tools/generate_video.py --client dan-balkun --prompt "..." --fast --resolution 480p
"""

import argparse
import json
import sys
from pathlib import Path

import fal_client
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TMP_DIR = Path(__file__).resolve().parent.parent / ".tmp"

STANDARD_ENDPOINT = "bytedance/seedance-2.0/reference-to-video"
FAST_ENDPOINT = "bytedance/seedance-2.0/fast/reference-to-video"


def load_urls(client: str) -> dict:
    cache_path = TMP_DIR / f"{client}_urls.json"
    if not cache_path.exists():
        print(f"Error: No cached URLs found at {cache_path}")
        print("Run upload_assets.py first.")
        sys.exit(1)
    with open(cache_path) as fp:
        return json.load(fp)


def generate_video(
    client: str,
    prompt: str,
    duration: str = "10",
    resolution: str = "720p",
    aspect_ratio: str = "9:16",
    fast: bool = False,
    seed: int | None = None,
    images: list[int] | None = None,
    audios: list[int] | None = None,
) -> dict:
    urls = load_urls(client)

    all_images = [item["url"] for item in urls.get("images", [])]
    all_audio = [item["url"] for item in urls.get("audio", [])]

    if images:
        image_urls = [all_images[i - 1] for i in images if 1 <= i <= len(all_images)]
        selected = [urls["images"][i - 1]["file"] for i in images if 1 <= i <= len(all_images)]
        print(f"Using {len(image_urls)} of {len(all_images)} images: {selected}")
    else:
        image_urls = all_images

    if audios:
        audio_urls = [all_audio[i - 1] for i in audios if 1 <= i <= len(all_audio)]
        selected_audio = [urls["audio"][i - 1]["file"] for i in audios if 1 <= i <= len(all_audio)]
        print(f"Using {len(audio_urls)} of {len(all_audio)} audio files: {selected_audio}")
    else:
        audio_urls = all_audio

    if not image_urls:
        print("Error: No image URLs found. Upload photos first.")
        sys.exit(1)

    endpoint = FAST_ENDPOINT if fast else STANDARD_ENDPOINT
    tier = "Fast" if fast else "Standard"

    # Estimate cost
    dur_seconds = int(duration) if duration != "auto" else 10
    rate = 0.24 if fast else 0.30
    est_cost = dur_seconds * rate

    print(f"\n--- Generation Settings ---")
    print(f"  Client:       {client}")
    print(f"  Endpoint:     {tier} ({endpoint})")
    print(f"  Duration:     {duration}s")
    print(f"  Resolution:   {resolution}")
    print(f"  Aspect Ratio: {aspect_ratio}")
    print(f"  Images:       {len(image_urls)}")
    print(f"  Audio:        {len(audio_urls)}")
    print(f"  Est. Cost:    ~${est_cost:.2f}")
    print(f"  Prompt:       {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"---------------------------\n")

    arguments = {
        "prompt": prompt,
        "image_urls": image_urls,
        "resolution": resolution,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
    }

    if audio_urls:
        arguments["audio_urls"] = audio_urls

    if seed is not None:
        arguments["seed"] = seed

    print("Submitting job... (this may take 1-2 minutes)")

    def on_queue_update(update):
        if hasattr(update, "logs") and update.logs:
            for log in update.logs:
                print(f"  [{log.get('level', 'info')}] {log.get('message', '')}")

    result = fal_client.subscribe(
        endpoint,
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    # Save result
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    result_path = TMP_DIR / f"{client}_result.json"
    with open(result_path, "w") as fp:
        json.dump(result, fp, indent=2, default=str)

    video_url = result.get("video", {}).get("url", "N/A")
    seed_used = result.get("seed", "N/A")

    print(f"\nGeneration complete!")
    print(f"  Video URL: {video_url}")
    print(f"  Seed:      {seed_used}")
    print(f"  Result saved to: {result_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate video via Seed Dance 2.0")
    parser.add_argument("--client", required=True, help="Client name")
    parser.add_argument("--prompt", required=True, help="Generation prompt (use @Image1, @Audio1 refs)")
    parser.add_argument("--duration", default="10", choices=["4", "5", "10", "15", "auto"])
    parser.add_argument("--resolution", default="720p", choices=["480p", "720p"])
    parser.add_argument("--aspect-ratio", default="9:16", choices=["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"])
    parser.add_argument("--fast", action="store_true", help="Use fast/cheaper endpoint")
    parser.add_argument("--seed", type=int, default=None, help="Seed for reproducibility")
    parser.add_argument("--images", type=int, nargs="+", default=None, help="Which image numbers to use (e.g. --images 4 5 6 8)")
    parser.add_argument("--audios", type=int, nargs="+", default=None, help="Which audio numbers to use (e.g. --audios 1)")
    args = parser.parse_args()

    generate_video(
        client=args.client,
        prompt=args.prompt,
        duration=args.duration,
        resolution=args.resolution,
        aspect_ratio=args.aspect_ratio,
        fast=args.fast,
        seed=args.seed,
        images=args.images,
        audios=args.audios,
    )
