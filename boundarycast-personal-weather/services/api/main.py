import math
from fastapi import FastAPI, HTTPException, Query
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
from boundarycast_api.adapters.live_sources import search_locations
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
    """Policy packs are versioned files; load once per process. An empty
    load (e.g. missing directory at boot) is never cached — every decision
    must cite the real active packs or keep retrying."""
    global _POLICY_PACKS
    if not _POLICY_PACKS:
        _POLICY_PACKS = load_policy_packs(ROOT / "examples" / "policy-packs")
    return _POLICY_PACKS

def market_params_from(req: MarketCreateRequest):
    """Extract the stored oracle params for a new market. Markets are
    durable public objects: creation-time demo scenario flags are never
    stored (settlement decides simulation), and non-demo coordinates are
    rounded so the book never republishes a raw real location."""
    params = req.model_dump(exclude={"market_id"})
    question = params.pop("question")
    for flag in ("simulate_alert", "simulate_no_official_forecast", "simulate_no_observation"):
        params[flag] = False
    if not params.get("demo_mode"):
        params["latitude"] = round(params["latitude"], 2)
        params["longitude"] = round(params["longitude"], 2)
    return question, params

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
        "evidence_sources": {
            "official_forecast": evidence["official_forecast"].get("source_name"),
            "observation": evidence["observation"].get("source_name"),
            "alerts": evidence["alerts"].get("source_name"),
        },
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

@app.get("/api/v1/locations/search")
def location_search(q: str = Query(min_length=2, max_length=100)):
    """Resolve a city, address, or destination to coordinates without
    retaining the query or building location history."""
    try:
        return {"results": search_locations(q)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Location search is temporarily unavailable") from exc

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
    question, params = market_params_from(req)
    return market_book.create_market(question, params)

@app.get("/api/v1/markets")
def markets():
    return {"markets": market_book.list_markets(), "crowd_feedback": market_book.crowd_scoreboard()}

@app.post("/api/v1/markets/{market_id}/stake")
def stake_market(market_id: str, req: StakeRequest):
    position, error = market_book.stake(market_id, req.side, req.amount, req.trader)
    if error:
        raise HTTPException(status_code=404 if error == "unknown_market" else 409, detail=error)
    return {"position": position, "market": market_book.get_market(market_id)}

@app.post("/api/v1/markets/{market_id}/settle")
def settle_market(market_id: str, req: MarketSettleRequest):
    # Claim the market atomically BEFORE running the pipeline, so a losing
    # concurrent settle can never append an orphan resolution artifact.
    market, error = market_book.begin_settle(market_id)
    if error:
        raise HTTPException(status_code=404 if error == "unknown_market" else 409, detail=error)
    try:
        overrides = {k: v for k, v in req.model_dump().items() if v is not None}
        oracle_req = MarketResolutionRequest(
            **{**market["oracle_params"], **overrides},
            market_id=market_id,
            question=market["question"],
        )
        forecast = evaluate_governed_forecast(oracle_req)
        resolution = resolve_market(oracle_req, forecast)
        settled, error = market_book.settle(market_id, resolution)
    except Exception:
        market_book.abort_settle(market_id)
        raise
    if error:
        market_book.abort_settle(market_id)
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
        question_out, params = market_params_from(MarketCreateRequest(question=question, **condition))
        presets.append((question_out, params, 60, 40))
    seeded = market_book.seed_demo(presets)
    return {"markets": market_book.list_markets(), "seeded": seeded}

