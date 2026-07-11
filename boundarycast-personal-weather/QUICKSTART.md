# QUICKSTART — running BoundaryCast in under 2 minutes

**Requirements:** Python 3.10+ (3.11 recommended). That's it. Runtime deps are just FastAPI, Uvicorn, Pydantic (see `services/api/requirements.txt`).

## Fastest path (one command)

```bash
cd boundarycast-personal-weather
bash scripts/run_no_docker.sh          # macOS/Linux
# Windows PowerShell:
.\scripts\run_no_docker.ps1
```

That creates a `.venv`, installs the three runtime deps, and starts the server. Open **http://localhost:8787/ui**

## Manual path (if the script fights you)

```bash
cd boundarycast-personal-weather/services/api
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8787
```

## Docker path

```bash
docker build -t boundarycast .        # from the repo root (Dockerfile lives there)
docker run -p 8787:8787 boundarycast
```

Keep it to **one worker** (the default) — the artifact hash chain and market book are single-process by design in this demo.

## Once it's up

- **http://localhost:8787/ui** — YOUR WEATHER + Forecast Future Weather + Market Board
- **http://localhost:8787/ui/pitch.html** — the pitch deck (arrow keys)
- Click **Seed demo markets** first so the board is never empty
- Demo flow: `docs/demo-script.md` (3 minutes, 4 beats)

## Run the tests

```bash
cd services/api
pip install -r requirements-dev.txt    # adds pytest + httpx
python -m pytest tests/
```

## If something breaks on stage

- Port taken → `uvicorn main:app --port 8788` and use that URL
- Board looks stale → click **Refresh board**
- Nuke demo state → delete `artifacts/forecast-artifacts.ndjson` and restart (markets are in-memory; restart clears them)
