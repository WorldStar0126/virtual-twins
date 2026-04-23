"""Download a generated video from fal.ai to the output folder.

Usage:
    python tools/download_video.py --client dan-balkun
    python tools/download_video.py --url https://v3.fal.media/files/... --client dan-balkun
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TMP_DIR = Path(__file__).resolve().parent.parent / ".tmp"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def download_video(
    client: str,
    url: str | None = None,
    job_id: str | None = None,
    clip_number: int | None = None,
) -> Path:
    # Get video URL from result cache if not provided
    if url is None:
        result_path = TMP_DIR / f"{client}_result.json"
        if not result_path.exists():
            print(f"Error: No result found at {result_path}")
            print("Run generate_video.py first, or provide --url directly.")
            sys.exit(1)
        with open(result_path) as fp:
            result = json.load(fp)
        url = result.get("video", {}).get("url")
        if not url:
            print("Error: No video URL found in result file.")
            sys.exit(1)

    # Create output directory
    client_output = OUTPUT_DIR / client
    if job_id:
        client_output = client_output / job_id
    client_output.mkdir(parents=True, exist_ok=True)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if clip_number is not None:
        output_path = client_output / f"clip_{clip_number}_{timestamp}.mp4"
    else:
        output_path = client_output / f"video_{timestamp}.mp4"

    print(f"Downloading video...")
    print(f"  From: {url[:80]}...")
    print(f"  To:   {output_path}")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(output_path, "wb") as fp:
        for chunk in response.iter_content(chunk_size=8192):
            fp.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = (downloaded / total) * 100
                print(f"\r  Progress: {pct:.0f}%", end="", flush=True)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n\nDownload complete!")
    print(f"  File: {output_path}")
    print(f"  Size: {size_mb:.1f} MB")

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download generated video")
    parser.add_argument("--client", required=True, help="Client name")
    parser.add_argument("--url", default=None, help="Direct video URL (optional)")
    parser.add_argument("--job-id", default=None, help="Optional job id for per-job output folder")
    parser.add_argument("--clip-number", type=int, default=None, help="Optional clip number for file naming")
    args = parser.parse_args()

    download_video(client=args.client, url=args.url, job_id=args.job_id, clip_number=args.clip_number)
