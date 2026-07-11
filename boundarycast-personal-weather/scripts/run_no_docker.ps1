$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\services\api"
if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:BOUNDARYCAST_LIVE_EVIDENCE="1"
uvicorn main:app --host 0.0.0.0 --port 8787 --reload
