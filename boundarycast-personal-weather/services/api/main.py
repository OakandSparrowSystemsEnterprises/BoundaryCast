from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from boundarycast_api.models.schemas import PersonalForecastRequest
from boundarycast_api.adapters.geolocation_adapter import build_location_context
from boundarycast_api.adapters.microclimate_adapter import build_microclimate_context
from boundarycast_api.adapters.nws_adapter import get_official_forecast_stub
from boundarycast_api.adapters.observation_adapter import get_observation_stub
from boundarycast_api.adapters.alert_adapter import get_alerts_stub
from boundarycast_api.epistemology.checks import evaluate_knowledge_state
from boundarycast_api.policy.policy_loader import load_policy_packs
from boundarycast_api.policy.rule_engine import evaluate_policy_rules
from boundarycast_api.foresight_proxy.microclimate_adjuster import build_forecast_claim
from boundarycast_api.gatekeeper_lite.evaluator import evaluate_gatekeeper
from boundarycast_api.artifacts.artifact import create_artifact
from boundarycast_api.artifacts.replay import verify_artifact_chain

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "apps" / "web"
ARTIFACT_PATH = ROOT / "artifacts" / "forecast-artifacts.ndjson"

app = FastAPI(title="BoundaryCast Personal Weather", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/ui", StaticFiles(directory=str(APP_DIR), html=True), name="ui")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")

@app.get("/health")
def health():
    return {"status": "healthy", "engine": "BoundaryCast Personal Weather v0.1"}

@app.post("/api/v1/personal-forecast")
def personal_forecast(req: PersonalForecastRequest):
    location_context = build_location_context(req)
    microclimate_context = build_microclimate_context(req, location_context)
    evidence = {
        "tenant_id": req.tenant_id,
        "location_context": location_context,
        "microclimate_context": microclimate_context,
        "official_forecast": get_official_forecast_stub(req),
        "observation": get_observation_stub(req),
        "alerts": get_alerts_stub(req),
    }
    epistemology = evaluate_knowledge_state(evidence, req)
    policy_packs = load_policy_packs(ROOT / "examples" / "policy-packs")
    policy_result = evaluate_policy_rules(policy_packs, evidence, epistemology)
    claim = build_forecast_claim(req, evidence, epistemology)
    verdict = evaluate_gatekeeper(evidence, epistemology, policy_result, claim)
    artifact = create_artifact(ARTIFACT_PATH, req.tenant_id, evidence, claim, policy_packs, verdict)
    return {
        "product": "BoundaryCast",
        "frame": "Your Weather",
        "location_context": location_context,
        "microclimate_context": microclimate_context,
        "epistemology": epistemology,
        "claim": claim,
        "verdict": verdict,
        "artifact": artifact,
    }

@app.get("/api/v1/replay")
def replay():
    return verify_artifact_chain(ARTIFACT_PATH)
