"""v3 regression suite: Claim Scope, graceful degradation, zero-cache privacy.

Covers the 13 regression requirements in docs/v3-claim-scope-and-zero-cache.md.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from boundarycast_api.gatekeeper_lite.evaluator import evaluate_gatekeeper, SEVERITY

API_DIR = Path(main.__file__).resolve().parent
PROJECT_ROOT = API_DIR.parents[1]
POLICY_PACK_DIR = PROJECT_ROOT / "examples" / "policy-packs"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "verify_artifacts.py"

FULL_MICROCLIMATE = {
    "surface_exposure": "open",
    "shade_exposure": "partial",
    "elevation_meters": 16,
    "wind_exposure": "moderate",
    "nearby_water": True,
    "urban_density": "high",
}


@pytest.fixture
def artifact_path(tmp_path, monkeypatch):
    path = tmp_path / "forecast-artifacts.ndjson"
    monkeypatch.setattr(main, "ARTIFACT_PATH", path)
    return path


@pytest.fixture
def client(artifact_path):
    return TestClient(main.app)


def forecast(client, **body):
    res = client.post("/api/v1/personal-forecast", json=body)
    assert res.status_code == 200, res.text
    return res.json()


# 1. Invalid latitude/longitude returns schema validation error, not a forecast.
def test_invalid_coordinates_rejected(client, artifact_path):
    for body in [{"latitude": 999}, {"latitude": -91}, {"longitude": 500}, {"longitude": -180.1}]:
        res = client.post("/api/v1/personal-forecast", json=body)
        assert res.status_code == 422, body
        assert "claim" not in res.json()
    assert not artifact_path.exists(), "rejected requests must not create artifacts"


# 2. Active official alert produces PROTOCOL + official_alert_only.
def test_active_alert_protocol_scope(client):
    data = forecast(client, simulate_alert=True, **FULL_MICROCLIMATE)
    v = data["verdict"]
    assert v["gatekeeper_verdict"] == "PROTOCOL"
    assert v["product_verdict"] == "official_alert_governs"
    assert v["claim_scope"] == "official_alert_only"
    assert "official_alert_scope_governs" in v["scope_reason_codes"]


# 3. Strong exact evidence produces PERMIT + exact_location.
def test_strong_exact_evidence(client):
    data = forecast(client, precision_meters=25, **FULL_MICROCLIMATE)
    v = data["verdict"]
    assert v["gatekeeper_verdict"] == "PERMIT"
    assert v["claim_scope"] == "exact_location"
    assert v["fallback_applied"] is False
    claim = data["claim"]
    for field in ["requested_scope", "claim_scope", "scope_reason_codes", "fallback_applied",
                  "public_message", "microclimate_confidence", "uncertainty_label", "evidence_score"]:
        assert field in claim, f"claim missing {field}"


# 4. Medium microclimate evidence produces PERMIT or PERMIT_WITH_CAUTION + microclimate_adjusted.
def test_medium_microclimate_scope(client):
    data = forecast(client, precision_meters=5000, **FULL_MICROCLIMATE)
    v = data["verdict"]
    assert v["claim_scope"] == "microclimate_adjusted"
    assert v["gatekeeper_verdict"] in ("PERMIT", "PERMIT_WITH_CAUTION")


# 5. Missing microclimate but available official forecast produces
#    official_forecast_area, not total abstention.
def test_missing_microclimate_degrades_to_area(client):
    data = forecast(client, simulate_no_observation=True)
    v = data["verdict"]
    assert v["claim_scope"] == "official_forecast_area"
    assert v["gatekeeper_verdict"] != "ABSTAIN"
    assert v["product_verdict"] in ("publish", "publish_with_caution")


# 6. Requested exact forecast without sufficient exact evidence falls back
#    to the highest supported scope.
def test_requested_exact_falls_back(client):
    data = forecast(client, requested_scope="exact_location")
    v = data["verdict"]
    assert v["requested_scope"] == "exact_location"
    assert v["fallback_applied"] is True
    assert v["claim_scope"] == "nearby_observation_area"
    assert "unsupported_specific_claim" in v["scope_reason_codes"]


# 7. No official forecast and no observation produces ABSTAIN + unsupported_specific_claim.
def test_no_evidence_abstains(client):
    data = forecast(client, simulate_no_official_forecast=True, simulate_no_observation=True)
    v = data["verdict"]
    assert v["gatekeeper_verdict"] == "ABSTAIN"
    assert v["claim_scope"] == "unsupported_specific_claim"


# 8. Gatekeeper severity precedence cannot be loosened.
def test_severity_precedence_cannot_be_loosened():
    scope = {"requested_scope": "exact_location", "claim_scope": "exact_location",
             "scope_reason_codes": [], "fallback_applied": False}

    def verdict_for(effects, knowledge_state):
        return evaluate_gatekeeper(
            {}, {"knowledge_state": knowledge_state},
            {"effects": effects, "reason_codes": []},
            {}, scope,
        )["gatekeeper_verdict"]

    # A strict policy effect is never downgraded by a friendlier knowledge state.
    assert verdict_for(["ABSTAIN"], "sufficient") == "ABSTAIN"
    assert verdict_for(["PROTOCOL"], "sufficient") == "PROTOCOL"
    assert verdict_for(["BLOCK"], "sufficient") == "BLOCK"
    assert verdict_for(["PROTOCOL", "PERMIT_WITH_CAUTION"], "partial") == "PROTOCOL"
    assert verdict_for(["BLOCK", "ABSTAIN", "PROTOCOL"], "sufficient") == "BLOCK"
    # Knowledge state can only tighten.
    assert verdict_for([], "insufficient") == "ABSTAIN"
    assert verdict_for([], "partial") == "PERMIT_WITH_CAUTION"
    assert verdict_for([], "sufficient") == "PERMIT"
    assert SEVERITY == ["PERMIT", "PERMIT_WITH_CAUTION", "ABSTAIN", "PROTOCOL", "BLOCK"]


# 9. Reason codes must match policy packs.
def test_reason_codes_match_policy_packs(client):
    defined = set()
    for pack_path in POLICY_PACK_DIR.glob("*.json"):
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        for rule in pack.get("rules", []):
            if rule.get("reason_code"):
                defined.add(rule["reason_code"])

    scenarios = [
        dict(**FULL_MICROCLIMATE),
        dict(simulate_alert=True),
        dict(simulate_no_observation=True),
        dict(simulate_no_official_forecast=True, simulate_no_observation=True),
        dict(precision_meters=5000, **FULL_MICROCLIMATE),
        dict(requested_scope="official_forecast_area"),
    ]
    for scenario in scenarios:
        v = forecast(client, **scenario)["verdict"]
        emitted = set(v["reason_codes"]) | set(v["scope_reason_codes"])
        unknown = emitted - defined
        assert not unknown, f"engine emitted codes not defined in any policy pack: {unknown}"


# 10. Artifact chain verifies.
def test_artifact_chain_verifies(client):
    for _ in range(3):
        forecast(client, **FULL_MICROCLIMATE)
    replay = client.get("/api/v1/replay").json()
    assert replay["ok"] is True
    assert replay["count"] == 3

    artifact = forecast(client, **FULL_MICROCLIMATE)["artifact"]
    for field in ["claim_scope", "requested_scope", "fallback_applied", "scope_reason_codes",
                  "location_binding_type", "location_binding_value", "zero_cache", "privacy_notes",
                  "evidence_root", "claim_root", "policy_pack_versions", "gatekeeper_verdict",
                  "product_verdict", "reason_codes", "artifact_hash", "previous_hash"]:
        assert field in artifact, f"artifact missing {field}"
    assert artifact["zero_cache"] is True
    assert "claim-scope-policy-v1" in artifact["policy_pack_versions"]


# 11. Tampered artifact chain exits nonzero.
def test_tampered_chain_exits_nonzero(client, artifact_path):
    for _ in range(2):
        forecast(client, **FULL_MICROCLIMATE)

    clean = subprocess.run([sys.executable, str(VERIFY_SCRIPT), str(artifact_path)],
                           capture_output=True, text=True)
    assert clean.returncode == 0, clean.stdout + clean.stderr

    lines = artifact_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["gatekeeper_verdict"] = "PERMIT_FORGED"
    lines[0] = json.dumps(tampered, sort_keys=True)
    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = subprocess.run([sys.executable, str(VERIFY_SCRIPT), str(artifact_path)],
                            capture_output=True, text=True)
    assert result.returncode != 0, "tampered chain must exit nonzero"


# 12. Artifact does not persist raw exact real lat/lon unless synthetic/demo
#     mode is explicit.
def test_no_raw_location_persisted_outside_demo(client, artifact_path):
    lat, lon = 37.7974, -121.2161
    data = forecast(client, latitude=lat, longitude=lon, demo_mode=False, **FULL_MICROCLIMATE)
    artifact = data["artifact"]
    assert artifact["location_binding_type"] == "rounded"
    raw_line = artifact_path.read_text(encoding="utf-8").splitlines()[-1]
    assert str(lat) not in raw_line
    assert str(lon) not in raw_line

    demo = forecast(client, latitude=lat, longitude=lon, demo_mode=True, **FULL_MICROCLIMATE)
    assert demo["artifact"]["location_binding_type"] == "synthetic"


# 13. UI shows claim scope and fallback explanation.
def test_ui_shows_claim_scope_and_fallback():
    index_html = (PROJECT_ROOT / "apps" / "web" / "index.html").read_text(encoding="utf-8")
    app_js = (PROJECT_ROOT / "apps" / "web" / "app.js").read_text(encoding="utf-8")
    assert "requestedScope" in index_html
    assert "Forecast Scope" in app_js
    assert "Why this scope?" in app_js
    assert "fell back to the highest supported scope" in app_js
    assert "Artifact Status" in app_js
