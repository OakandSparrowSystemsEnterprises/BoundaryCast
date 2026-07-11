# Deploying a public demo URL

The repo root has a `Dockerfile` that serves the API and UI on `$PORT` (default 8787). Any container host works; artifacts are ephemeral demo data, so no volume is needed.

## Render (fastest from GitHub)

1. https://dashboard.render.com → New → Web Service → connect the `BoundaryCast` repo.
2. Runtime: Docker. Everything auto-detects. Instance: free tier is fine.
3. Deploy → your URL is `https://<service>.onrender.com` (UI at `/ui/`, health at `/health`).

## Fly.io

```bash
fly launch --no-deploy   # accepts the Dockerfile, pick a region
fly deploy
```

## Railway

New Project → Deploy from GitHub repo → Dockerfile auto-detected → Deploy.

## Local sanity check

```bash
docker build -t boundarycast .
docker run -p 8787:8787 boundarycast
# open http://localhost:8787/ui
```
