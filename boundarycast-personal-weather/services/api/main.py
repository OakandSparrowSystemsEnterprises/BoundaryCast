import math
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from boundarycast_api.models.schemas import (
    PersonalForecastRequest,
    MarketResolutionRequest,
    MarketCreateRequest,
    StakeRequest,
    MarketSettleRequest,
)
from boundarycast_api.markets import market_book
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

_POLICY_PACKS = None

def get_policy_packs():
    """Policy packs are versioned files; load once per process."""
    global _POLICY_PACKS
    if _POLICY_PACKS is None:
        _POLICY_PACKS = load_policy_packs(ROOT / "examples" / "policy-packs")
    return _POLICY_PACKS

app = FastAPI(title="BoundaryCast Personal Weather", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/ui", StaticFiles(directory=str(APP_DIR), html=True), name="ui")

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    # Non-finite floats (JSON `Infinity`/`NaN`) in a rejected request would
    # otherwise crash the 422 response serializer. Sanitize the echo.
    def clean(obj):
        if obj is None or isinstance(obj, (str, int, bool)):
            return obj
        if isinstance(obj, float):
            return obj if math.isfinite(obj) else str(obj)
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean(v) for v in obj]
        return str(obj)
    return JSONResponse(status_code=422, content={"detail": clean(exc.errors())})

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
    policy_packs = get_policy_packs()
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

# --- Market Factory Lite: a demo market book resolved by the oracle ---

@app.post("/api/v1/markets")
def create_market(req: MarketCreateRequest):
    params = req.model_dump(exclude={"market_id"})
    question = params.pop("question")
    return market_book.create_market(question, params)

@app.get("/api/v1/markets")
def markets():
    return {"markets": market_book.list_markets()}

@app.post("/api/v1/markets/{market_id}/stake")
def stake_market(market_id: str, req: StakeRequest):
    position, error = market_book.stake(market_id, req.side, req.amount, req.trader)
    if error:
        raise HTTPException(status_code=404 if error == "unknown_market" else 409, detail=error)
    return {"position": position, "market": market_book.get_market(market_id)}

@app.post("/api/v1/markets/{market_id}/settle")
def settle_market(market_id: str, req: MarketSettleRequest):
    market = market_book.get_market(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="unknown_market")
    if market["status"] != "open":
        raise HTTPException(status_code=409, detail="market_not_open")
    overrides = {k: v for k, v in req.model_dump().items() if v is not None}
    oracle_req = MarketResolutionRequest(
        **{**market["oracle_params"], **overrides},
        market_id=market_id,
        question=market["question"],
    )
    forecast = evaluate_governed_forecast(oracle_req)
    resolution = resolve_market(oracle_req, forecast)
    settled, error = market_book.settle(market_id, resolution)
    if error:
        raise HTTPException(status_code=409, detail=error)
    return {"market": settled, "resolution": resolution}

@app.post("/api/v1/markets/seed-demo")
def seed_demo_markets():
    """Seed the board with three preset markets and starter stakes so the
    demo is never empty on stage."""
    presets = []
    for question, condition in [
        ("Will it rain at this outdoor event between 2 PM and 5 PM?",
         dict(metric="precip_probability", operator="gt", threshold=0.5, minimum_scope="nearby_observation_area")),
        ("Will wind exceed 25 mph on this delivery route today?",
         dict(metric="wind_mph", operator="gt", threshold=25, minimum_scope="nearby_observation_area")),
        ("Will the temperature exceed 100°F at this job site today?",
         dict(metric="temperature_f", operator="gt", threshold=100, minimum_scope="nearby_observation_area")),
    ]:
        base = MarketCreateRequest(**condition).model_dump(exclude={"market_id"})
        base.pop("question")
        presets.append((question, base, 60, 40))
    seeded = market_book.seed_demo(presets)
    return {"markets": market_book.list_markets(), "seeded": seeded}
