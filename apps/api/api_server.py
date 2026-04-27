from __future__ import annotations

import json
import re
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tools.download_video import download_video
from tools.generate_video import generate_video
from tools.splice_clips import splice_reencode
from tools.upload_assets import upload_client_assets

ROOT = Path(__file__).resolve().parent
TMP_DIR = ROOT / ".tmp"
DB_PATH = TMP_DIR / "operator_db.json"
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets"
URL_CACHE_SUFFIX = "_urls.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_cost(duration_sec: int, fast: bool) -> float:
    rate = 0.24 if fast else 0.30
    return round(duration_sec * rate, 2)


def output_local_url(path: Path | str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    try:
        rel = p.resolve().relative_to(OUTPUT_DIR.resolve())
    except Exception:  # noqa: BLE001
        return None
    return f"/output-files/{rel.as_posix()}"


def media_duration_seconds(path: Path) -> float:
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(0.0, float((probe.stdout or "0").strip() or 0.0))


def has_audio_stream(path: Path) -> bool:
    probe = subprocess.run(
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
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool((probe.stdout or "").strip())


def estimate_audio_speed(path: Path) -> float:
    """Estimate speaking pace factor from speech activity ratio."""
    if not has_audio_stream(path):
        return 0.0
    total = media_duration_seconds(path)
    if total <= 0:
        return 0.0
    detect = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "info",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-30dB:d=0.20",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    silence_total = 0.0
    for m in re.finditer(r"silence_duration:\s*([0-9.]+)", detect.stderr or ""):
        silence_total += float(m.group(1))
    speaking_ratio = max(0.0, min(1.0, (total - silence_total) / total))
    # 1.0 ~= typical speaking density; below/above means slower/faster perceived pace.
    # Keep a floor to avoid extreme underestimation, but allow faster clips to show
    # more separation in UI instead of flattening at 1.40x.
    pace_factor = speaking_ratio / 0.55
    return round(max(0.6, min(2.0, pace_factor)), 2)


def build_atempo_filter(speed_factor: float) -> str:
    """Build ffmpeg atempo chain for any positive speed factor."""
    factor = max(0.01, float(speed_factor))
    parts: list[str] = []
    while factor < 0.5:
        parts.append("atempo=0.5")
        factor /= 0.5
    while factor > 2.0:
        parts.append("atempo=2.0")
        factor /= 2.0
    parts.append(f"atempo={factor:.6f}")
    return ",".join(parts)


def retime_clip_av(input_path: Path, output_path: Path, audio_speed_factor: float, video_pts_factor: float) -> None:
    """Retime both audio and video to preserve sync."""
    af = build_atempo_filter(audio_speed_factor)
    vf = f"setpts={video_pts_factor:.6f}*PTS"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vf",
            vf,
            "-af",
            af,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ],
        check=True,
    )


def render_seam_preview(
    clip1_path: Path,
    clip2_path: Path,
    output_path: Path,
    seam_type: Literal["hard cut", "crossfade", "dip to black"] = "crossfade",
    seam_ms: int = 400,
) -> None:
    """Create seam preview according to selected seam style."""
    seam_s = max(0.05, min(2.5, float(seam_ms) / 1000.0))
    if seam_type == "hard cut":
        raise ValueError("hard cut does not require seam preview generation")
    if seam_type == "crossfade":
        window_s = max(0.6, seam_s + 0.5)
        offset_s = max(0.0, window_s - seam_s)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-sseof",
                f"-{window_s:.3f}",
                "-t",
                f"{window_s:.3f}",
                "-i",
                str(clip1_path),
                "-t",
                f"{window_s:.3f}",
                "-i",
                str(clip2_path),
                "-filter_complex",
                (
                    "[0:v]setpts=PTS-STARTPTS[v0];"
                    "[1:v]setpts=PTS-STARTPTS[v1];"
                    f"[v0][v1]xfade=transition=fade:duration={seam_s:.3f}:offset={offset_s:.3f}[outv]"
                ),
                "-map",
                "[outv]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                str(output_path),
            ],
            check=True,
        )
        return
    # dip to black
    side_s = max(0.3, seam_s)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            f"-{side_s:.3f}",
            "-t",
            f"{side_s:.3f}",
            "-i",
            str(clip1_path),
            "-t",
            f"{side_s:.3f}",
            "-i",
            str(clip2_path),
            "-filter_complex",
            (
                f"[0:v]trim=duration={side_s:.3f},setpts=PTS-STARTPTS,setsar=1[v0];"
                f"[1:v]trim=duration={side_s:.3f},setpts=PTS-STARTPTS,setsar=1[v1];"
                f"color=c=black:s=64x64:d={seam_s:.3f}[blk];"
                "[blk][v0]scale2ref[blkfit][v0ref];"
                "[v0ref]setsar=1[v0fix];"
                "[blkfit]setsar=1[blkfix];"
                "[v1]setsar=1[v1fix];"
                "[v0fix][blkfix][v1fix]concat=n=3:v=1:a=0,format=yuv420p[outv]"
            ),
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            str(output_path),
        ],
        check=True,
    )


class JobCreateRequest(BaseModel):
    client_slug: str
    prompt: str = Field(min_length=10)
    format: Literal["20s", "30s"] = "20s"
    resolution: Literal["480p", "720p"] = "720p"
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"] = "9:16"
    fast_tier: bool = False
    image_indices: list[int] | None = None
    audio_indices: list[int] | None = None
    template: str = "Custom / Freeform"


class ApprovalRequest(BaseModel):
    approved: bool
    note: str = ""


class AssembleRequest(BaseModel):
    end_card_id: str | None = None
    seam_type: Literal["hard cut", "crossfade", "dip to black"] = "crossfade"
    xfade_ms: int = 400


class AppState:
    def __init__(self) -> None:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cancel_requested: set[str] = set()
        if DB_PATH.exists():
            self.db = json.loads(DB_PATH.read_text(encoding="utf-8"))
        else:
            self.db = {"jobs": [], "run_events": []}
            self._save()

    def _save(self) -> None:
        DB_PATH.write_text(json.dumps(self.db, indent=2), encoding="utf-8")

    def is_cancel_requested(self, job_id: str) -> bool:
        return job_id in self._cancel_requested

    def request_cancel(self, job_id: str) -> None:
        self._cancel_requested.add(job_id)

    def clear_cancel(self, job_id: str) -> None:
        self._cancel_requested.discard(job_id)

    def clients(self) -> list[dict[str, Any]]:
        clients: list[dict[str, Any]] = []
        for client_dir in sorted(ASSETS_DIR.iterdir() if ASSETS_DIR.exists() else []):
            if not client_dir.is_dir() or client_dir.name.startswith("_"):
                continue
            photos = client_dir / "photos"
            audio = client_dir / "audio"
            clients.append(
                {
                    "slug": client_dir.name,
                    "name": client_dir.name.replace("-", " ").title(),
                    "company": f"{client_dir.name.replace('-', ' ').title()} Team",
                    "industry": "Video Automation",
                    "market": "Internal",
                    "tier": "Standard",
                    "status": "Active",
                    "photoCount": len([p for p in photos.glob("*") if p.is_file()]) if photos.exists() else 0,
                    "audioCount": len([p for p in audio.glob("*") if p.is_file()]) if audio.exists() else 0,
                    "lastVideo": "recently",
                    "videosThisMonth": len([j for j in self.db["jobs"] if j["client"] == client_dir.name]),
                    "videoQuota": 999,
                    "color": "#9B5CF6",
                    "initials": "".join(part[0].upper() for part in client_dir.name.split("-")[:2]),
                    "assetDrive": "local-assets",
                    "format": "20s",
                    "brandPrimary": "#C0C0C0",
                    "brandAccent": "#1A1A1A",
                }
            )
        return clients

    def add_event(self, job_id: str, event_type: str, message: str, meta: dict[str, Any] | None = None) -> None:
        event = {
            "id": f"evt_{uuid.uuid4().hex[:10]}",
            "job_id": job_id,
            "type": event_type,
            "message": message,
            "meta": meta or {},
            "created_at": utc_now(),
        }
        self.db["run_events"].append(event)
        self._save()

    def client_assets(self, client_slug: str) -> dict[str, Any]:
        client_dir = ASSETS_DIR / client_slug
        if not client_dir.exists():
            raise HTTPException(status_code=404, detail=f"Client assets not found: {client_slug}")

        photos_dir = client_dir / "photos"
        audio_dir = client_dir / "audio"
        videos_dir = client_dir / "videos"
        end_cards_dir = client_dir / "end_cards"
        image_files = sorted([p.name for p in photos_dir.glob("*") if p.is_file()]) if photos_dir.exists() else []
        audio_files = sorted([p.name for p in audio_dir.glob("*") if p.is_file()]) if audio_dir.exists() else []
        video_files = sorted([p.name for p in videos_dir.glob("*") if p.is_file()]) if videos_dir.exists() else []
        end_card_files = sorted([p.name for p in end_cards_dir.glob("*") if p.is_file()]) if end_cards_dir.exists() else []

        cache_path = TMP_DIR / f"{client_slug}{URL_CACHE_SUFFIX}"
        cache_images: list[dict[str, Any]] = []
        cache_audio: list[dict[str, Any]] = []
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding="utf-8"))
                cache_images = cache.get("images", [])
                cache_audio = cache.get("audio", [])
            except Exception:  # noqa: BLE001
                cache_images = []
                cache_audio = []

        image_by_name = {row.get("file"): row.get("url") for row in cache_images}
        audio_by_name = {row.get("file"): row.get("url") for row in cache_audio}
        images = [
            {
                "index": idx + 1,
                "file": name,
                "url": image_by_name.get(name),
                "local_url": f"/assets-files/{client_slug}/photos/{name}",
            }
            for idx, name in enumerate(image_files)
        ]
        audio = [
            {
                "index": idx + 1,
                "file": name,
                "url": audio_by_name.get(name),
                "local_url": f"/assets-files/{client_slug}/audio/{name}",
            }
            for idx, name in enumerate(audio_files)
        ]
        videos = [
            {
                "index": idx + 1,
                "file": name,
                "local_url": f"/assets-files/{client_slug}/videos/{name}",
            }
            for idx, name in enumerate(video_files)
        ]
        end_cards = [
            {
                "index": idx + 1,
                "id": Path(name).stem,
                "title": Path(name).stem.replace("_", " ").replace("-", " ").strip().title(),
                "file": name,
                "local_url": f"/assets-files/{client_slug}/end_cards/{name}",
            }
            for idx, name in enumerate(end_card_files)
        ]
        branding_path = client_dir / "branding.json"
        branding: dict[str, Any] | None = None
        if branding_path.exists():
            try:
                parsed = json.loads(branding_path.read_text(encoding="utf-8"))
                logo_cfg = parsed.get("visual", {}).get("logo", {})
                light_logo = logo_cfg.get("light_bg_path")
                dark_logo = logo_cfg.get("dark_bg_path")
                branding = {
                    "raw": parsed,
                    "identity": parsed.get("identity", {}),
                    "contact": parsed.get("contact", {}),
                    "social": parsed.get("social", {}),
                    "colors": parsed.get("visual", {}).get("colors", {}),
                    "logo_light_url": f"/assets-files/{client_slug}/{light_logo}" if light_logo else None,
                    "logo_dark_url": f"/assets-files/{client_slug}/{dark_logo}" if dark_logo else None,
                }
            except Exception:  # noqa: BLE001
                branding = None
        return {
            "client": client_slug,
            "images": images,
            "audio": audio,
            "videos": videos,
            "end_cards": end_cards,
            "branding": branding,
            "cache_available": cache_path.exists(),
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        return list(self.db["jobs"])

    def delete_failed_jobs(self) -> dict[str, int]:
        failed_ids = {job["id"] for job in self.db["jobs"] if job.get("status") == "failed"}
        if not failed_ids:
            return {"deleted_jobs": 0, "deleted_events": 0}
        before_jobs = len(self.db["jobs"])
        before_events = len(self.db["run_events"])
        self.db["jobs"] = [job for job in self.db["jobs"] if job.get("id") not in failed_ids]
        self.db["run_events"] = [evt for evt in self.db["run_events"] if evt.get("job_id") not in failed_ids]
        self._save()
        return {
            "deleted_jobs": before_jobs - len(self.db["jobs"]),
            "deleted_events": before_events - len(self.db["run_events"]),
        }

    def delete_job(self, job_id: str) -> dict[str, int]:
        exists = any(job["id"] == job_id for job in self.db["jobs"])
        if not exists:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        before_jobs = len(self.db["jobs"])
        before_events = len(self.db["run_events"])
        self.db["jobs"] = [job for job in self.db["jobs"] if job["id"] != job_id]
        self.db["run_events"] = [evt for evt in self.db["run_events"] if evt.get("job_id") != job_id]
        self._save()
        return {
            "deleted_jobs": before_jobs - len(self.db["jobs"]),
            "deleted_events": before_events - len(self.db["run_events"]),
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        for job in self.db["jobs"]:
            if job["id"] == job_id:
                return job
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    def job_events(self, job_id: str) -> list[dict[str, Any]]:
        return [e for e in self.db["run_events"] if e["job_id"] == job_id]

    def _update_job(self, job_id: str, **updates: Any) -> dict[str, Any]:
        for idx, job in enumerate(self.db["jobs"]):
            if job["id"] == job_id:
                next_job = {**job, **updates, "updated_at": utc_now()}
                self.db["jobs"][idx] = next_job
                self._save()
                return next_job
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    def create_job(self, payload: JobCreateRequest) -> dict[str, Any]:
        with self._lock:
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            clips_total = 2 if payload.format == "20s" else 3
            duration_sec = 10
            job = {
                "id": job_id,
                "client": payload.client_slug,
                "template": payload.template,
                "format": payload.format,
                "status": "queued",
                "stage": "clip_1_gen",
                "createdAt": "just now",
                "created_at": utc_now(),
                "updated_at": utc_now(),
                "duration": 20 if payload.format == "20s" else 30,
                "resolution": payload.resolution,
                "aspect_ratio": payload.aspect_ratio,
                "cost": 0.0,
                "costProjected": estimate_cost(duration_sec, payload.fast_tier) * clips_total,
                "clipsDone": 0,
                "clipsTotal": clips_total,
                "prompt": payload.prompt,
                "thumb": "#E8B860",
                "video_url": None,
                "output_path": None,
                "output_local_url": None,
                "clip_outputs": {},
                "fast_tier": payload.fast_tier,
                "image_indices": payload.image_indices or [],
                "audio_indices": payload.audio_indices or [],
            }
            self.db["jobs"].append(job)
            self.add_event(job_id, "job.created", "Job created")
        threading.Thread(target=self._run_clip_1, args=(job_id,), daemon=True).start()
        return job

    def _run_clip_1(self, job_id: str) -> None:
        try:
            job = self.get_job(job_id)
            self.clear_cancel(job_id)
            self._update_job(job_id, status="rendering", stage="clip_1_gen")
            self.add_event(job_id, "clip_1.started", "Generating clip 1")
            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", "Job stopped before upload started")
                return

            cache_path = TMP_DIR / f"{job['client']}{URL_CACHE_SUFFIX}"
            try:
                self.add_event(
                    job_id,
                    "assets.upload.started",
                    f"Running upload step: python tools/upload_assets.py --client {job['client']}",
                )
                upload_client_assets(
                    job["client"],
                    image_indices=job.get("image_indices") or None,
                    audio_indices=job.get("audio_indices") or None,
                    should_cancel=lambda: self.is_cancel_requested(job_id),
                    progress_hook=lambda kind, name: self.add_event(
                        job_id, "assets.upload.progress", f"Uploaded {kind}: {name}"
                    ),
                )
                self.add_event(job_id, "assets.uploaded", "Upload finished: client assets uploaded to fal CDN")
            except Exception as upload_error:  # noqa: BLE001
                if cache_path.exists():
                    self.add_event(
                        job_id,
                        "assets.upload_skipped",
                        "Asset upload failed, using cached CDN URLs",
                        {"warning": str(upload_error)},
                    )
                else:
                    raise

            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", "Job stopped after upload")
                return

            result = generate_video(
                client=job["client"],
                prompt=job["prompt"],
                duration="10",
                resolution=job["resolution"],
                aspect_ratio=job["aspect_ratio"],
                fast=bool(job.get("fast_tier")),
            )
            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", "Job stopped after clip generation")
                return
            video_url = result.get("video", {}).get("url")
            clip_output_path = download_video(client=job["client"], job_id=job_id, clip_number=1)
            self.add_event(job_id, "clip_1.downloaded", "Clip 1 downloaded locally", {"output_path": str(clip_output_path)})
            cost = estimate_cost(10, bool(job.get("fast_tier")))
            latest_job = self.get_job(job_id)
            next_clip_outputs = dict(latest_job.get("clip_outputs") or {})
            next_clip_outputs["1"] = {
                "clip": 1,
                "output_path": str(clip_output_path),
                "output_local_url": output_local_url(clip_output_path),
            }
            self._update_job(
                job_id,
                status="awaiting_approval",
                stage="clip_1_review",
                clipsDone=1,
                cost=cost,
                video_url=video_url,
                output_path=str(clip_output_path),
                output_local_url=output_local_url(clip_output_path),
                clip_outputs=next_clip_outputs,
            )
            self.add_event(job_id, "clip_1.ready", "Clip 1 ready for approval", {"video_url": video_url})
        except Exception as exc:  # noqa: BLE001
            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", "Job stopped by user", {"detail": str(exc)})
            else:
                self._update_job(job_id, status="failed", stage="clip_1_gen", failReason=str(exc))
                self.add_event(job_id, "job.failed", "Clip 1 failed", {"error": str(exc)})

    def _run_clip_n(self, job_id: str, clip_idx: int) -> None:
        try:
            job = self.get_job(job_id)
            self._update_job(job_id, status="rendering", stage=f"clip_{clip_idx}_gen")
            self.add_event(job_id, f"clip_{clip_idx}.started", f"Generating clip {clip_idx}")
            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", f"Job stopped before clip {clip_idx} generation")
                return

            result = generate_video(
                client=job["client"],
                prompt=job["prompt"],
                duration="10",
                resolution=job["resolution"],
                aspect_ratio=job["aspect_ratio"],
                fast=bool(job.get("fast_tier")),
            )
            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", f"Job stopped after clip {clip_idx} generation")
                return

            clip_output_path = download_video(client=job["client"], job_id=job_id, clip_number=clip_idx)
            self.add_event(
                job_id,
                f"clip_{clip_idx}.downloaded",
                f"Clip {clip_idx} downloaded locally",
                {"output_path": str(clip_output_path)},
            )
            video_url = result.get("video", {}).get("url")
            next_cost = float(job.get("cost", 0.0)) + estimate_cost(10, bool(job.get("fast_tier")))
            latest_job = self.get_job(job_id)
            next_clip_outputs = dict(latest_job.get("clip_outputs") or {})
            next_clip_outputs[str(clip_idx)] = {
                "clip": clip_idx,
                "output_path": str(clip_output_path),
                "output_local_url": output_local_url(clip_output_path),
            }
            self._update_job(
                job_id,
                status="awaiting_approval",
                stage=f"clip_{clip_idx}_review",
                clipsDone=clip_idx,
                cost=next_cost,
                video_url=video_url,
                output_path=str(clip_output_path),
                output_local_url=output_local_url(clip_output_path),
                clip_outputs=next_clip_outputs,
            )
            self.add_event(job_id, f"clip_{clip_idx}.ready", f"Clip {clip_idx} ready for approval", {"video_url": video_url})
        except Exception as exc:  # noqa: BLE001
            if self.is_cancel_requested(job_id):
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stopped", "Job stopped by user", {"detail": str(exc)})
            else:
                self._update_job(job_id, status="failed", failReason=str(exc))
                self.add_event(job_id, "job.failed", f"Clip {clip_idx} failed", {"error": str(exc)})

    def approval_decision(self, job_id: str, payload: ApprovalRequest) -> dict[str, Any]:
        job = self.get_job(job_id)
        stage = str(job.get("stage", ""))
        m = re.fullmatch(r"clip_(\d+)_review", stage)
        if not m:
            # Idempotent behavior for UI retries / stale clicks:
            # if the job already moved forward (or was already stopped), return current state.
            if payload.approved and job["status"] in {"rendering", "done"}:
                self.add_event(job_id, "clip.approval_ignored", "Approval ignored; job already progressed")
                return job
            if not payload.approved and job["status"] in {"failed", "done"}:
                self.add_event(job_id, "clip.rejection_ignored", "Rejection ignored; job already finalized")
                return job
            if not payload.approved and job["status"] == "rendering":
                self.request_cancel(job_id)
                self._update_job(job_id, status="failed", stage="stopped_by_rejection")
                self.add_event(job_id, "job.stop_requested", "Reject & Stop requested while generating", {"note": payload.note})
                return self.get_job(job_id)
            raise HTTPException(
                status_code=409,
                detail=f"Job is not waiting for clip approval. Current stage: {job['stage']}",
            )
        clip_idx = int(m.group(1))
        clips_total = int(job.get("clipsTotal", 2))
        if payload.approved:
            if clip_idx < clips_total:
                next_idx = clip_idx + 1
                self._update_job(job_id, status="rendering", stage=f"clip_{next_idx}_gen")
                self.add_event(
                    job_id,
                    f"clip_{clip_idx}.approved",
                    f"Clip {clip_idx} approved; continuing generation",
                    {"note": payload.note},
                )
                threading.Thread(target=self._run_clip_n, args=(job_id, next_idx), daemon=True).start()
            else:
                self._update_job(job_id, status="queued", stage="assembly_review")
                self.add_event(job_id, f"clip_{clip_idx}.approved", "Final clip approved; ready for assembly", {"note": payload.note})
        else:
            self._update_job(job_id, status="failed", stage="stopped_by_rejection")
            self.add_event(job_id, f"clip_{clip_idx}.rejected", f"Clip {clip_idx} rejected; job stopped", {"note": payload.note})
        return self.get_job(job_id)

    def regenerate_current_clip(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job.get("status") == "rendering":
            raise HTTPException(status_code=409, detail="Clip is currently generating.")
        stage = str(job.get("stage", ""))
        m = re.fullmatch(r"clip_(\d+)_review", stage)
        if not m:
            raise HTTPException(status_code=409, detail=f"Job is not in clip review stage. Current stage: {stage}")
        clip_idx = int(m.group(1))
        self._update_job(job_id, status="rendering", stage=f"clip_{clip_idx}_gen")
        self.add_event(job_id, f"clip_{clip_idx}.regenerate_requested", f"Regenerating clip {clip_idx}")
        if clip_idx == 1:
            threading.Thread(target=self._run_clip_1, args=(job_id,), daemon=True).start()
        else:
            threading.Thread(target=self._run_clip_n, args=(job_id, clip_idx), daemon=True).start()
        return self.get_job(job_id)

    def stop_job(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job.get("status") != "rendering":
            raise HTTPException(status_code=409, detail="Job is not currently rendering.")
        self.request_cancel(job_id)
        self._update_job(job_id, status="failed", stage="stopped_by_rejection")
        self.add_event(job_id, "job.stop_requested", "Reject & Stop requested")
        return self.get_job(job_id)

    def assemble(self, job_id: str, payload: AssembleRequest) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job["status"] not in {"queued", "awaiting_assembly", "done"}:
            raise HTTPException(status_code=400, detail="Job is not ready for assembly yet.")
        client_slug = str(job.get("client") or "").strip()
        if not client_slug:
            raise HTTPException(status_code=400, detail="Job has no client")
        job_dir = OUTPUT_DIR / client_slug / job_id
        if not job_dir.exists():
            raise HTTPException(status_code=404, detail="Job output directory not found")

        clip_rows: list[tuple[int, Path]] = []
        for file_path in job_dir.glob("*.mp4"):
            if not file_path.is_file():
                continue
            match = re.match(r"^clip(?:_number)?_(\d+)(?:_.*)?\.mp4$", file_path.name)
            if not match:
                continue
            clip_rows.append((int(match.group(1)), file_path))
        clip_rows.sort(key=lambda row: (row[0], row[1].name))
        clip_paths = [row[1] for row in clip_rows]
        if not clip_paths:
            raise HTTPException(status_code=400, detail="No generated clips found for assembly")

        adjusted_clip_paths = list(clip_paths)
        adjusted_temp_files: list[Path] = []
        speed_adjustments: list[dict[str, Any]] = []
        speed_by_clip: dict[int, float] = {}
        for i, clip_path in enumerate(clip_paths, start=1):
            if not has_audio_stream(clip_path):
                continue
            clip_speed = estimate_audio_speed(clip_path)
            if clip_speed > 0:
                speed_by_clip[i] = clip_speed

        total_speed = round(sum(speed_by_clip.values()) / len(speed_by_clip), 4) if speed_by_clip else 0.0
        # Normalize only when clips differ materially from the average pace.
        normalize_threshold = 0.05
        max_rel_delta = max((abs((s / total_speed) - 1.0) for s in speed_by_clip.values()), default=0.0) if total_speed > 0 else 0.0
        should_normalize = total_speed > 0 and max_rel_delta > normalize_threshold

        if should_normalize:
            for i, clip_path in enumerate(clip_paths, start=1):
                clip_speed = speed_by_clip.get(i)
                if not clip_speed:
                    continue
                audio_atempo_factor = total_speed / clip_speed
                video_setpts_factor = clip_speed / total_speed
                if abs(audio_atempo_factor - 1.0) < 0.01:
                    continue
                retimed_path = job_dir / f"_assembly_retime_clip_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.mp4"
                retime_clip_av(
                    clip_path,
                    retimed_path,
                    audio_speed_factor=audio_atempo_factor,
                    video_pts_factor=video_setpts_factor,
                )
                adjusted_clip_paths[i - 1] = retimed_path
                adjusted_temp_files.append(retimed_path)
                speed_adjustments.append(
                    {
                        "clip": i,
                        "from_speed": clip_speed,
                        "to_speed_target": total_speed,
                        "atempo_factor": round(audio_atempo_factor, 4),
                        "setpts_factor": round(video_setpts_factor, 4),
                        "output_file": retimed_path.name,
                    }
                )

        assemble_inputs = list(adjusted_clip_paths)
        selected_end_card_path: Path | None = None
        if payload.end_card_id:
            end_cards_dir = ASSETS_DIR / client_slug / "end_cards"
            if not end_cards_dir.exists():
                raise HTTPException(status_code=400, detail=f"End cards folder not found for client: {client_slug}")
            candidates = [p for p in end_cards_dir.glob("*") if p.is_file()]
            card_id = str(payload.end_card_id).strip()
            selected_end_card_path = next(
                (
                    p
                    for p in candidates
                    if p.stem == card_id or p.name == card_id
                ),
                None,
            )
            if not selected_end_card_path:
                raise HTTPException(status_code=400, detail=f"End card not found: {card_id}")
            assemble_inputs.append(selected_end_card_path)

        final_path = job_dir / f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        seam_preview_path: Path | None = None
        seam_preview_error: str | None = None
        seam_type = str(payload.seam_type or "crossfade").strip().lower()
        seam_ms = max(0, int(payload.xfade_ms or 0))
        try:
            splice_reencode(
                assemble_inputs,
                final_path,
                seam_fade_ms=50,
                seam_type=seam_type,
                xfade_ms=seam_ms,
            )
            if len(adjusted_clip_paths) >= 2 and seam_type != "hard cut" and seam_ms > 0:
                try:
                    seam_preview_path = job_dir / f"seam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    render_seam_preview(
                        adjusted_clip_paths[0],
                        adjusted_clip_paths[1],
                        seam_preview_path,
                        seam_type=seam_type if seam_type in {"crossfade", "dip to black"} else "crossfade",
                        seam_ms=seam_ms,
                    )
                except Exception as seam_exc:  # noqa: BLE001
                    seam_preview_error = str(seam_exc)
                    seam_preview_path = None
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Final assembly failed: {exc}") from exc
        finally:
            for temp_path in adjusted_temp_files:
                temp_path.unlink(missing_ok=True)

        self._update_job(
            job_id,
            status="done",
            stage="done",
            final_output_path=str(final_path),
            final_output_local_url=output_local_url(final_path),
            seam_preview_path=str(seam_preview_path) if seam_preview_path else None,
            seam_preview_local_url=output_local_url(seam_preview_path) if seam_preview_path else None,
            assembled_end_card_id=payload.end_card_id,
        )
        self.add_event(
            job_id,
            "assembly.completed",
            "Final assembly completed",
            {
                "end_card_id": payload.end_card_id,
                "final_output_path": str(final_path),
                "clip_count": len(clip_paths),
                "has_end_card": bool(payload.end_card_id),
                "seam_preview_path": str(seam_preview_path) if seam_preview_path else None,
                "seam_preview_error": seam_preview_error,
                "seam_type": seam_type,
                "xfade_ms": seam_ms,
                "audio_speed_total_target": total_speed,
                "audio_speed_normalize_threshold": normalize_threshold,
                "audio_speed_max_relative_delta": round(max_rel_delta, 4),
                "audio_speed_normalized": should_normalize,
                "audio_speed_adjustments": speed_adjustments,
            },
        )
        return self.get_job(job_id)

state = AppState()
app = FastAPI(title="Virtual Twins Operator API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets-files", StaticFiles(directory=str(ASSETS_DIR)), name="assets-files")
app.mount("/output-files", StaticFiles(directory=str(OUTPUT_DIR)), name="output-files")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/clients")
def get_clients() -> list[dict[str, Any]]:
    return state.clients()


@app.get("/v1/jobs")
def get_jobs() -> list[dict[str, Any]]:
    return state.list_jobs()


@app.delete("/v1/jobs/failed")
def delete_failed_jobs() -> dict[str, int]:
    return state.delete_failed_jobs()


@app.delete("/v1/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, int]:
    return state.delete_job(job_id)


@app.get("/v1/clients/{client_slug}/assets")
def get_client_assets(client_slug: str) -> dict[str, Any]:
    return state.client_assets(client_slug)


@app.post("/v1/clients/{client_slug}/assets/upload")
async def upload_client_asset(
    client_slug: str,
    asset_type: Literal["photo", "audio", "video", "branding", "logo", "end_card"] = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(None),
) -> dict[str, Any]:
    client_dir = ASSETS_DIR / client_slug
    if not client_dir.exists():
        raise HTTPException(status_code=404, detail=f"Client assets not found: {client_slug}")

    safe_name = Path(file.filename or "").name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Missing file name")

    ext = Path(safe_name).suffix.lower()
    if asset_type == "photo":
        allowed = {".jpg", ".jpeg", ".png", ".webp"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Photos must be jpg/jpeg/png/webp")
        target_dir = client_dir / "photos"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
    elif asset_type == "audio":
        allowed = {".mp3", ".wav", ".m4a"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Audio must be mp3/wav/m4a")
        target_dir = client_dir / "audio"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
    elif asset_type == "video":
        allowed = {".mp4", ".mov", ".m4v", ".webm"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Video must be mp4/mov/m4v/webm")
        target_dir = client_dir / "videos"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
    elif asset_type == "end_card":
        allowed = {".mp4", ".mov", ".m4v", ".webm"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="End card must be mp4/mov/m4v/webm")
        raw_title = (title or Path(safe_name).stem).strip()
        safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_title).strip("_") or "end_card"
        target_dir = client_dir / "end_cards"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{safe_title}{ext}"
    elif asset_type == "branding":
        if ext != ".json":
            raise HTTPException(status_code=400, detail="Branding file must be .json")
        target_path = client_dir / "branding.json"
    else:  # logo
        allowed = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Logo must be jpg/jpeg/png/webp/svg")
        target_dir = client_dir / "branding"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"logo_on_light{ext}"

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")
    target_path.write_bytes(contents)
    return {
        "ok": True,
        "client": client_slug,
        "asset_type": asset_type,
        "path": str(target_path.relative_to(ASSETS_DIR)),
        "bytes": len(contents),
    }


@app.delete("/v1/clients/{client_slug}/assets")
def delete_client_asset(
    client_slug: str,
    asset_type: Literal["photo", "audio", "video", "branding", "logo", "end_card"],
    file_name: str | None = None,
) -> dict[str, Any]:
    client_dir = ASSETS_DIR / client_slug
    if not client_dir.exists():
        raise HTTPException(status_code=404, detail=f"Client assets not found: {client_slug}")

    if asset_type == "photo":
        if not file_name:
            raise HTTPException(status_code=400, detail="file_name is required for photo delete")
        target_path = client_dir / "photos" / Path(file_name).name
    elif asset_type == "audio":
        if not file_name:
            raise HTTPException(status_code=400, detail="file_name is required for audio delete")
        target_path = client_dir / "audio" / Path(file_name).name
    elif asset_type == "video":
        if not file_name:
            raise HTTPException(status_code=400, detail="file_name is required for video delete")
        target_path = client_dir / "videos" / Path(file_name).name
    elif asset_type == "end_card":
        if not file_name:
            raise HTTPException(status_code=400, detail="file_name is required for end_card delete")
        target_path = client_dir / "end_cards" / Path(file_name).name
    elif asset_type == "branding":
        target_path = client_dir / "branding.json"
    else:  # logo
        if file_name:
            target_path = client_dir / "branding" / Path(file_name).name
        else:
            branding_dir = client_dir / "branding"
            candidates = sorted(list(branding_dir.glob("logo_on_light.*"))) if branding_dir.exists() else []
            if not candidates:
                raise HTTPException(status_code=404, detail="Logo not found")
            target_path = candidates[0]

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {target_path.name}")
    target_path.unlink()
    return {
        "ok": True,
        "client": client_slug,
        "asset_type": asset_type,
        "deleted": target_path.name,
    }


@app.post("/v1/jobs")
def create_job(payload: JobCreateRequest) -> dict[str, Any]:
    return state.create_job(payload)


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    return state.get_job(job_id)


@app.get("/v1/jobs/{job_id}/events")
def get_job_events(job_id: str) -> list[dict[str, Any]]:
    return state.job_events(job_id)


@app.get("/v1/jobs/{job_id}/clips")
def get_job_clips(job_id: str) -> list[dict[str, Any]]:
    job = state.get_job(job_id)
    client = str(job.get("client") or "").strip()
    if not client:
        raise HTTPException(status_code=400, detail="Job has no client")
    clip_dir = OUTPUT_DIR / client / job_id
    if not clip_dir.exists():
        return []

    clips: list[dict[str, Any]] = []
    for file_path in sorted([p for p in clip_dir.glob("*.mp4") if p.is_file()]):
        # Support both legacy and current clip naming:
        # - clip_1.mp4
        # - clip_1_20260424_101010.mp4
        # - clip_number_1.mp4
        # - clip_number_1_20260424_101010.mp4
        match = re.match(r"^clip(?:_number)?_(\d+)(?:_|\.mp4$)", file_path.name)
        clip_idx = int(match.group(1)) if match else None
        audio_speed = estimate_audio_speed(file_path)
        duration_sec = media_duration_seconds(file_path)
        clips.append(
            {
                "file": file_path.name,
                "clip": clip_idx,
                "output_path": str(file_path),
                "output_local_url": output_local_url(file_path),
                "audio_speed": audio_speed,
                "duration_sec": duration_sec,
            }
        )
    clips.sort(key=lambda row: (row.get("clip") is None, row.get("clip") or 9999, row.get("file") or ""))
    return clips


@app.get("/v1/jobs/{job_id}/clips/{clip_idx}/stream")
def stream_job_clip(job_id: str, clip_idx: int) -> FileResponse:
    job = state.get_job(job_id)
    client = str(job.get("client") or "").strip()
    if not client:
        raise HTTPException(status_code=400, detail="Job has no client")
    clip_dir = OUTPUT_DIR / client / job_id
    if not clip_dir.exists():
        raise HTTPException(status_code=404, detail="Clip directory not found")

    candidates = list(clip_dir.glob(f"clip_{clip_idx}_*.mp4"))
    candidates.extend(list(clip_dir.glob(f"clip_number_{clip_idx}_*.mp4")))
    if not candidates:
        # Fallback for any legacy naming that still has identifiable clip number.
        for file_path in clip_dir.glob("*.mp4"):
            match = re.match(r"^clip(?:_number)?_(\d+)(?:_.*)?\.mp4$", file_path.name)
            if match and int(match.group(1)) == clip_idx:
                candidates.append(file_path)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"Clip {clip_idx} not found")

    selected = max(candidates, key=lambda p: p.stat().st_mtime)
    return FileResponse(path=str(selected), media_type="video/mp4", filename=selected.name)


@app.post("/v1/jobs/{job_id}/approval")
def post_approval(job_id: str, payload: ApprovalRequest) -> dict[str, Any]:
    return state.approval_decision(job_id, payload)


@app.post("/v1/jobs/{job_id}/regenerate-clip-1")
def post_regenerate_clip_1(job_id: str) -> dict[str, Any]:
    return state.regenerate_current_clip(job_id)


@app.post("/v1/jobs/{job_id}/stop")
def post_stop_job(job_id: str) -> dict[str, Any]:
    return state.stop_job(job_id)


@app.post("/v1/jobs/{job_id}/assemble")
def post_assemble(job_id: str, payload: AssembleRequest) -> dict[str, Any]:
    return state.assemble(job_id, payload)
