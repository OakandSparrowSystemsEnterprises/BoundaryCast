"""Oracle recipe tests: market resolution semantics on top of the governed
forecast pipeline. See docs/oracle-recipe.md."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main

PROJECT_ROOT = Path(main.__file__).resolve().parents[2]

FULL_MICROCLIMATE = {
    "surface_exposure": "open",
    "shade_exposure": "partial",
    "elevation_meters": 16,
    "wind_exposure": "moderate",
    "nearby_water": True,
    "urban_density": "high",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ARTIFACT_PATH", tmp_path / "forecast-artifacts.ndjson")
    return TestClient(main.app)


def resolve(client, **body):
    res = client.post("/api/v1/oracle/resolve", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_condition_true_resolves_yes_firm(client):
    d = resolve(client, metric="temperature_f", operator="gt", threshold=80, **FULL_MICROCLIMATE)
    assert d["resolution"] == "YES"
    assert d["resolution_confidence"] == "firm"
    assert d["resolution_basis"]["claim_scope"] == "exact_location"
    assert d["condition"]["observed_value"] == 88


def test_condition_false_resolves_no(client):
    d = resolve(client, metric="temperature_f", operator="gt", threshold=100, **FULL_MICROCLIMATE)
    assert d["resolution"] == "NO"


def test_degraded_scope_resolves_qualified(client):
    # No microclimate context: scope degrades to nearby_observation_area,
    # which still meets the default market minimum (official_forecast_area).
    d = resolve(client, metric="wind_mph", operator="gt", threshold=25)
    assert d["resolution"] == "NO"
    assert d["resolution_confidence"] == "qualified"
    assert d["resolution_basis"]["claim_scope"] == "nearby_observation_area"


def test_scope_below_market_minimum_unresolved(client):
    d = resolve(client, metric="temperature_f", operator="gt", threshold=80,
                minimum_scope="exact_location")
    assert d["resolution"] == "UNRESOLVED"
    assert d["unresolved_reason"] == "scope_below_market_minimum"
    assert d["escalation"] == "arbitration"


def test_alert_market_resolves_yes_when_alert_active(client):
    d = resolve(client, metric="alert_active", simulate_alert=True, **FULL_MICROCLIMATE)
    assert d["resolution"] == "YES"
    assert d["resolution_confidence"] == "official"
    assert d["resolution_basis"]["claim_scope"] == "official_alert_only"


def test_alert_market_resolves_no_when_no_alert(client):
    d = resolve(client, metric="alert_active", **FULL_MICROCLIMATE)
    assert d["resolution"] == "NO"


def test_condition_market_under_alert_unresolved(client):
    d = resolve(client, metric="temperature_f", operator="gt", threshold=80,
                simulate_alert=True, **FULL_MICROCLIMATE)
    assert d["resolution"] == "UNRESOLVED"
    assert d["unresolved_reason"] == "official_alert_governs"


def test_no_evidence_unresolved_to_arbitration(client):
    d = resolve(client, metric="temperature_f", operator="gt", threshold=80,
                simulate_no_official_forecast=True, simulate_no_observation=True)
    assert d["resolution"] == "UNRESOLVED"
    assert d["unresolved_reason"] == "insufficient_evidence"
    assert d["escalation"] == "arbitration"


def test_resolution_embeds_replayable_artifact(client):
    d = resolve(client, metric="temperature_f", operator="gt", threshold=80, **FULL_MICROCLIMATE)
    artifact = d["artifact"]
    assert artifact["artifact_hash"]
    assert artifact["zero_cache"] is True
    replay = client.get("/api/v1/replay").json()
    assert replay["ok"] is True
    assert replay["count"] == 1


def test_invalid_market_request_rejected(client):
    res = client.post("/api/v1/oracle/resolve", json={"latitude": 999, "metric": "temperature_f"})
    assert res.status_code == 422
    res = client.post("/api/v1/oracle/resolve", json={"metric": "stock_price"})
    assert res.status_code == 422


def test_ui_has_oracle_mode():
    index_html = (PROJECT_ROOT / "apps" / "web" / "index.html").read_text(encoding="utf-8")
    app_js = (PROJECT_ROOT / "apps" / "web" / "app.js").read_text(encoding="utf-8")
    assert "Oracle Mode" in index_html
    assert "minScope" in index_html
    assert "/api/v1/oracle/resolve" in app_js
    assert "Resolution record" in app_js
