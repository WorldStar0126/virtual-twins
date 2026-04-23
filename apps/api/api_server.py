from __future__ import annotations

import json
import re
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
from tools.generate_end_card import render as render_end_card
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
        image_files = sorted([p.name for p in photos_dir.glob("*") if p.is_file()]) if photos_dir.exists() else []
        audio_files = sorted([p.name for p in audio_dir.glob("*") if p.is_file()]) if audio_dir.exists() else []

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
                self._update_job(job_id, status="awaiting_assembly", stage="assembly_review")
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
        if job["status"] not in {"awaiting_assembly", "done"}:
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
            match = re.match(r"^clip(?:_number)?_(\d+)_.*\.mp4$", file_path.name)
            if not match:
                continue
            clip_rows.append((int(match.group(1)), file_path))
        clip_rows.sort(key=lambda row: (row[0], row[1].name))
        clip_paths = [row[1] for row in clip_rows]
        if not clip_paths:
            raise HTTPException(status_code=400, detail="No generated clips found for assembly")

        assemble_inputs = list(clip_paths)
        end_card_path: Path | None = None
        if payload.end_card_id:
            branding_path = ASSETS_DIR / client_slug / "branding.json"
            if not branding_path.exists():
                raise HTTPException(status_code=400, detail=f"Branding file not found for client: {client_slug}")
            safe_end_card_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", payload.end_card_id).strip("-") or "selected"
            end_card_path = job_dir / f"end_card_{safe_end_card_id}.mp4"
            try:
                render_end_card(source=branding_path, out_path=end_card_path)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=500, detail=f"End card generation failed: {exc}") from exc
            assemble_inputs.append(end_card_path)

        final_path = job_dir / f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        try:
            splice_reencode(assemble_inputs, final_path, seam_fade_ms=50)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Final assembly failed: {exc}") from exc

        self._update_job(
            job_id,
            status="done",
            stage="done",
            final_output_path=str(final_path),
            final_output_local_url=output_local_url(final_path),
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
    asset_type: Literal["photo", "audio", "branding", "logo"] = Form(...),
    file: UploadFile = File(...),
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
    asset_type: Literal["photo", "audio", "branding", "logo"],
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
        match = re.match(r"^clip(?:_number)?_(\d+)_", file_path.name)
        clip_idx = int(match.group(1)) if match else None
        clips.append(
            {
                "file": file_path.name,
                "clip": clip_idx,
                "output_path": str(file_path),
                "output_local_url": output_local_url(file_path),
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
