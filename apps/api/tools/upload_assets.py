"""Upload client photos and audio to fal.ai CDN.

Usage:
    python tools/upload_assets.py --client dan-balkun
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable

import fal_client
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TMP_DIR = Path(__file__).resolve().parent.parent / ".tmp"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}


def _upload_file_with_retry(path: Path, retries: int = 3, base_delay_sec: float = 1.0) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fal_client.upload_file(str(path))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= retries:
                break
            sleep_s = base_delay_sec * (2 ** (attempt - 1))
            print(f"retrying in {sleep_s:.1f}s (attempt {attempt + 1}/{retries})", flush=True)
            time.sleep(sleep_s)
    assert last_error is not None
    raise RuntimeError(f"Upload failed after {retries} attempts for {path.name}: {last_error}") from last_error


def upload_client_assets(
    client: str,
    image_indices: list[int] | None = None,
    audio_indices: list[int] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress_hook: Callable[[str, str], None] | None = None,
) -> dict:
    client_dir = ASSETS_DIR / client
    photos_dir = client_dir / "photos"
    audio_dir = client_dir / "audio"

    if not client_dir.exists():
        raise FileNotFoundError(f"Client directory not found: {client_dir}")

    result = {"images": [], "audio": []}

    # Upload photos
    if photos_dir.exists():
        photo_files = [f for f in sorted(photos_dir.iterdir()) if f.suffix.lower() in IMAGE_EXTENSIONS]
        if image_indices:
            selected = {idx for idx in image_indices if idx > 0}
            photo_files = [f for i, f in enumerate(photo_files, start=1) if i in selected]
        for f in photo_files:
            if should_cancel and should_cancel():
                raise RuntimeError("Upload cancelled by user")
            if f.suffix.lower() in IMAGE_EXTENSIONS:
                print(f"  Uploading photo: {f.name}...", end=" ", flush=True)
                url = _upload_file_with_retry(f)
                result["images"].append({"file": f.name, "url": url})
                print("done")
                if progress_hook:
                    progress_hook("photo", f.name)
    else:
        print(f"Warning: No photos directory found at {photos_dir}")

    # Upload audio
    if audio_dir.exists():
        audio_files = [f for f in sorted(audio_dir.iterdir()) if f.suffix.lower() in AUDIO_EXTENSIONS]
        if audio_indices:
            selected = {idx for idx in audio_indices if idx > 0}
            audio_files = [f for i, f in enumerate(audio_files, start=1) if i in selected]
        for f in audio_files:
            if should_cancel and should_cancel():
                raise RuntimeError("Upload cancelled by user")
            if f.suffix.lower() in AUDIO_EXTENSIONS:
                print(f"  Uploading audio: {f.name}...", end=" ", flush=True)
                url = _upload_file_with_retry(f)
                result["audio"].append({"file": f.name, "url": url})
                print("done")
                if progress_hook:
                    progress_hook("audio", f.name)
    else:
        print(f"Warning: No audio directory found at {audio_dir}")

    if not result["images"] and not result["audio"]:
        raise RuntimeError("No supported files found to upload.")

    # Save URL mapping
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = TMP_DIR / f"{client}_urls.json"
    with open(cache_path, "w") as fp:
        json.dump(result, fp, indent=2)

    print(f"\nUploaded {len(result['images'])} images, {len(result['audio'])} audio files")
    print(f"URL mapping saved to: {cache_path}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload client assets to fal.ai CDN")
    parser.add_argument("--client", required=True, help="Client folder name (e.g., dan-balkun)")
    args = parser.parse_args()
    print(args.client)

    print(f"Uploading assets for client: {args.client}")
    upload_client_assets(args.client)
