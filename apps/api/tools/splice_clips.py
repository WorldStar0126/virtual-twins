"""Splice multiple video clips into a single output.

Usage:
    python tools/splice_clips.py --client dan-balkun --clips video_20260415_225636.mp4 video_20260417_173329.mp4
    python tools/splice_clips.py --client dan-balkun --clips clip1.mp4 clip2.mp4 --output final.mp4
    python tools/splice_clips.py --client dan-balkun --clips clip1.mp4 clip2.mp4 --reencode
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def splice_demuxer(clip_paths, output_path: Path):
    """Fast concat via ffmpeg concat demuxer. No re-encode; requires identical codec params."""
    list_file = output_path.parent / f"_concat_{output_path.stem}.txt"
    list_file.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in clip_paths)
    )
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(list_file),
             "-c", "copy",
             str(output_path)],
            check=True,
        )
    finally:
        list_file.unlink(missing_ok=True)


def video_duration_seconds(video_path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def has_audio_stream(video_path: Path) -> bool:
    """Return True when input has an audio stream."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool((r.stdout or "").strip())


def splice_reencode(
    clip_paths: list[Path],
    output_path: Path,
    seam_fade_ms: int = 50,
    seam_type: str = "hard cut",
    xfade_ms: int = 400,
) -> None:
    """Robust concat via ffmpeg. Re-encodes; works with mismatched params.
    """
    inputs: list[str] = []
    for p in clip_paths:
        inputs.extend(["-i", str(p)])

    n = len(clip_paths)
    fade_s = max(0.0, seam_fade_ms / 1000.0)
    xfade_s = max(0.0, xfade_ms / 1000.0)
    seam = (seam_type or "hard cut").strip().lower()
    durations = [video_duration_seconds(p) for p in clip_paths]

    audio_labels: list[str] = []
    prep_parts: list[str] = []
    for i, p in enumerate(clip_paths):
        if has_audio_stream(p):
            audio_labels.append(f"[{i}:a]")
        else:
            silent_label = f"[asil{i}]"
            prep_parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration={durations[i]:.6f},asetpts=N/SR/TB{silent_label}"
            )
            audio_labels.append(silent_label)

    if n == 1:
        filter_complex = ";".join([*prep_parts, f"[0:v]{audio_labels[0]}concat=n=1:v=1:a=1[outv][outa]"])
    elif seam in {"crossfade", "dip to black"} and xfade_s > 0:
        parts = [*prep_parts]
        transition = "fade" if seam == "crossfade" else "fadeblack"
        vcur = "[0:v]"
        accumulated = durations[0]
        for i in range(1, n):
            vo = f"[vx{i}]"
            offset = max(0.0, accumulated - xfade_s)
            parts.append(
                f"{vcur}[{i}:v]xfade=transition={transition}:duration={xfade_s:.6f}:offset={offset:.6f}{vo}"
            )
            vcur = vo
            accumulated += durations[i] - xfade_s

        acur = audio_labels[0]
        for i in range(1, n):
            ao = f"[ax{i}]"
            parts.append(f"{acur}{audio_labels[i]}acrossfade=d={xfade_s:.6f}{ao}")
            acur = ao

        parts.append(f"{vcur}setpts=PTS[outv]")
        parts.append(f"{acur}anull[outa]")
        filter_complex = ";".join(parts)
    elif seam_fade_ms <= 0:
        filter_parts = [f"[{i}:v]{audio_labels[i]}" for i in range(n)]
        concat_part = "".join(filter_parts) + f"concat=n={n}:v=1:a=1[outv][outa]"
        filter_complex = ";".join([*prep_parts, concat_part])
    else:
        parts = ["".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[outv]"]
        for i in range(n):
            filters = []
            if i > 0:
                filters.append(f"afade=t=in:st=0:d={fade_s}")
            if i < n - 1:
                filters.append(f"afade=t=out:st={durations[i] - fade_s}:d={fade_s}")
            if filters:
                label = f"[a{i}]"
                parts.append(f"{audio_labels[i]}{','.join(filters)}{label}")
                audio_labels[i] = label
        parts.append("".join(audio_labels) + f"concat=n={n}:v=0:a=1[outa]")
        filter_complex = ";".join([*prep_parts, *parts])

    subprocess.run(
        ["ffmpeg", "-y", *inputs,
         "-filter_complex", filter_complex,
         "-map", "[outv]", "-map", "[outa]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k",
         str(output_path)],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Splice video clips into a single output")
    parser.add_argument("--client", required=True, help="Client folder name")
    parser.add_argument("--clips", nargs="+", required=True, help="Clip filenames (in order) from output/{client}/")
    parser.add_argument("--output", default=None, help="Output filename (default: spliced_{timestamp}.mp4)")
    parser.add_argument("--reencode", action="store_true", help="Use concat filter (re-encodes; slower but more robust)")
    parser.add_argument("--seam-fade-ms", type=int, default=50, help="Audio fade duration at each seam (ms). Set 0 to disable. Only applies with --reencode (default 50)")
    parser.add_argument("--seam-type", default="hard cut", choices=["hard cut", "crossfade", "dip to black"], help="Seam transition mode for final assembly")
    parser.add_argument("--xfade-ms", type=int, default=400, help="Seam transition duration in ms for crossfade/dip to black")
    args = parser.parse_args()

    client_dir = OUTPUT_DIR / args.client
    clip_paths = [client_dir / c for c in args.clips]

    for p in clip_paths:
        if not p.exists():
            print(f"Error: clip not found: {p}")
            sys.exit(1)

    output_name = args.output or f"spliced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    output_path = client_dir / output_name

    print(f"Splicing {len(clip_paths)} clips -> {output_path.name}")
    for i, p in enumerate(clip_paths, 1):
        print(f"  Clip {i}: {p.name}")

    method = "re-encode (concat filter)" if args.reencode else "fast (concat demuxer)"
    print(f"Method: {method}\n")

    try:
        if args.reencode:
            splice_reencode(
                clip_paths,
                output_path,
                seam_fade_ms=args.seam_fade_ms,
                seam_type=args.seam_type,
                xfade_ms=args.xfade_ms,
            )
        else:
            splice_demuxer(clip_paths, output_path)
    except subprocess.CalledProcessError as e:
        print(f"\nError: ffmpeg failed with exit code {e.returncode}")
        if not args.reencode:
            print("Try running again with --reencode (handles mismatched codec params)")
        sys.exit(1)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\nDone: {output_path}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
