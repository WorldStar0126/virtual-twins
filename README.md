# Virtual Twins Monorepo

This project has:
- Backend API in `apps/api` (Python + FastAPI + fal pipeline tools)
- Frontend UI in `apps/web` (React + static JSX served locally)

## Project Structure

```text
virtual-twins-monorepo/
|- apps/
|  |- api/        # backend API, generation tools, workflows, tests
|  `- web/        # frontend operator UI
|- packages/      # reserved for shared code
|- package.json   # npm workspace root
`- README.md
```

## Requirements

- Node.js 18+
- Python 3.11+
- ffmpeg and ffprobe available in PATH (required for video splice/assembly)

## Quick Start (Run Both Projects)

Use 2 terminals.

### Terminal 1: Start Backend (`apps/api`)

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Then edit `apps/api/.env` and set keys (at least `FAL_KEY`).

Run API server:

```powershell
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

### Terminal 2: Start Frontend (`apps/web`)

From repo root:

```powershell
python -m http.server 8080
```

Open:
[http://localhost:8080](http://localhost:8080)

## Common Troubleshooting

- **Port already in use (8000):** stop old `uvicorn` process, then restart backend.
- **`python-multipart` error:** run `pip install -r requirements.txt` again in backend venv.
- **Frontend not reflecting latest JSX:** hard refresh browser (`Ctrl + F5`).
- **Assembly/splice errors:** verify `ffmpeg -version` and `ffprobe -version` work in terminal.

## Notes

- Generated clips/finals are written under `apps/api/output/<client>/<job_id>/`.
- Asset files are read from `apps/api/assets/<client>/`.
