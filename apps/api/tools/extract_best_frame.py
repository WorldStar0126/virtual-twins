"""Extract the sharpest frame from a video's time range (splice continuity tool).

Samples frames at a fine interval across a time window (default: last 2 seconds),
scores each by Laplacian variance (classic blur-detection metric), and reports
the top N candidates ranked by sharpness.

Usage:
    python tools/extract_best_frame.py --video output/dan-balkun/video_20260415_225636.mp4
    python tools/extract_best_frame.py --video PATH --from-end 2.0 --interval 0.1 --top 5
    python tools/extract_best_frame.py --video PATH --auto    # prints winner path only
"""

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def video_duration(video_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def extract_frames(video_path: Path, out_dir: Path, start: float, end: float, interval: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    t = start
    while t < end:
        ts_str = f"{t:.3f}".replace(".", "_")
        out_path = out_dir / f"frame_{ts_str}s.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video_path),
             "-frames:v", "1", "-pix_fmt", "rgb24", "-update", "1", str(out_path)],
            capture_output=True, check=True,
        )
        frames.append((t, out_path))
        t += interval
    return frames


def sharpness_score(image_path: Path) -> float:
    """Laplacian variance — higher is sharper."""
    arr = np.array(Image.open(image_path).convert("L"), dtype=np.float64)
    lap = (
        -4 * arr[1:-1, 1:-1]
        + arr[:-2, 1:-1]
        + arr[2:, 1:-1]
        + arr[1:-1, :-2]
        + arr[1:-1, 2:]
    )
    return float(lap.var())


def main():
    parser = argparse.ArgumentParser(description="Extract the sharpest frame from a video time range")
    parser.add_argument("--video", required=True, help="Path to source video")
    parser.add_argument("--from-end", type=float, default=2.0, help="Extract from N seconds before end (default 2.0)")
    parser.add_argument("--interval", type=float, default=0.1, help="Sampling interval in seconds (default 0.1)")
    parser.add_argument("--top", type=int, default=3, help="Show top N candidates (default 3)")
    parser.add_argument("--auto", action="store_true", help="Print only the winning frame path (for scripting)")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: video not found: {video_path}")
        sys.exit(1)

    duration = video_duration(video_path)
    start_time = max(0.0, duration - args.from_end)
    end_time = duration - 0.01

    out_dir = Path(".tmp/frames") / f"{video_path.stem}_candidates"

    if not args.auto:
        n_candidates = int((end_time - start_time) / args.interval)
        print(f"Video duration: {duration:.2f}s")
        print(f"Extracting {n_candidates} candidates from {start_time:.2f}s to {end_time:.2f}s (every {args.interval}s)...")

    frames = extract_frames(video_path, out_dir, start_time, end_time, args.interval)

    scored = [(sharpness_score(p), t, p) for t, p in frames]
    scored.sort(reverse=True)

    if args.auto:
        print(scored[0][2])
        return

    print(f"\n--- Top {args.top} sharpest frames ---")
    for rank, (score, t, path) in enumerate(scored[:args.top], 1):
        marker = " <-- winner" if rank == 1 else ""
        print(f"  #{rank}  t={t:.2f}s  sharpness={score:9.1f}  {path}{marker}")

    print(f"\nReview the top candidates visually before selecting. They are all saved in:\n  {out_dir}")


if __name__ == "__main__":
    main()
