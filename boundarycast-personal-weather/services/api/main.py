from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from boundarycast_api.models.schemas import PersonalForecastRequest, MarketResolutionRequest
from boundarycast_api.adapters.geolocation_adapter import build_location_context
from boundarycast_api.adapters.microclimate_adapter import build_microclimate_context
from boundarycast_api.adapters.nws_adapter import get_official_forecast_stub
from boundarycast_api.adapters.observation_adapter import get_observation_stub
from boundarycast_api.adapters.alert_adapter import get_alerts_stub
from boundarycast_api.epistemology.checks import evaluate_knowledge_state
from boundarycast_api.epistemology.claim_scope import determine_claim_scope
from boundarycast_api.policy.policy_loader import load_policy_packs
from boundarycast_api.policy.rule_engine import evaluate_policy_rules
from boundarycast_api.foresight_proxy.microclimate_adjuster import build_forecast_claim
from boundarycast_api.gatekeeper_lite.evaluator import evaluate_gatekeeper
from boundarycast_api.artifacts.artifact import create_artifact
from boundarycast_api.artifacts.replay import verify_artifact_chain
from boundarycast_api.oracle.market_resolution import resolve_market, ORACLE_RECIPE_MANIFEST

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "apps" / "web"
ARTIFACT_PATH = ROOT / "artifacts" / "forecast-artifacts.ndjson"

app = FastAPI(title="BoundaryCast Personal Weather", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/ui", StaticFiles(directory=str(APP_DIR), html=True), name="ui")

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")

@app.get("/health")
def health():
    return {"status": "healthy", "engine": "BoundaryCast Personal Weather v3.0"}

def evaluate_governed_forecast(req: PersonalForecastRequest):
    """The full governed pipeline: evidence -> epistemology -> scope ->
    policy -> gatekeeper -> artifact. Shared by the personal forecast and
    the oracle recipe endpoints."""
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
    scope_decision = determine_claim_scope(req.requested_scope, epistemology, evidence)
    policy_packs = load_policy_packs(ROOT / "examples" / "policy-packs")
    policy_result = evaluate_policy_rules(policy_packs, evidence, epistemology, scope_decision)
    claim = build_forecast_claim(req, evidence, epistemology, scope_decision)
    verdict = evaluate_gatekeeper(evidence, epistemology, policy_result, claim, scope_decision)
    artifact = create_artifact(ARTIFACT_PATH, req, evidence, claim, policy_packs, verdict)
    return {
        "product": "BoundaryCast",
        "frame": "Your Weather",
        "location_context": location_context,
        "microclimate_context": microclimate_context,
        "epistemology": epistemology,
        "scope_decision": scope_decision,
        "claim": claim,
        "verdict": verdict,
        "artifact": artifact,
    }

@app.post("/api/v1/personal-forecast")
def personal_forecast(req: PersonalForecastRequest):
    return evaluate_governed_forecast(req)

@app.get("/api/v1/oracle/recipe")
def oracle_recipe():
    """Machine-readable oracle recipe manifest for market factories."""
    return ORACLE_RECIPE_MANIFEST

@app.post("/api/v1/oracle/resolve")
def oracle_resolve(req: MarketResolutionRequest):
    """Oracle recipe: resolve a weather-dependent prediction market from a
    governed, replayable forecast claim."""
    forecast = evaluate_governed_forecast(req)
    return resolve_market(req, forecast)

@app.get("/api/v1/replay")
def replay():
    return verify_artifact_chain(ARTIFACT_PATH)
