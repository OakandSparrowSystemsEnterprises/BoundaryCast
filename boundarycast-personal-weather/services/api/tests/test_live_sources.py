"""Live evidence adapters: off by default, parse real payload shapes,
and fall back to demo stubs on any failure. Plus the crowd feedback loop."""
import pytest
from fastapi.testclient import TestClient

import main
from boundarycast_api.adapters import live_sources
from boundarycast_api.markets import market_book

OPEN_METEO_PAYLOAD = {
    "current": {"time": "2026-07-11T20:00", "temperature_2m": 91.4, "wind_speed_10m": 9.2, "weather_code": 1},
    "hourly": {"precipitation_probability": [10, 35, None, 20]},
}
NWS_ALERTS_PAYLOAD = {
    "features": [{"id": "urn:x", "properties": {"event": "Heat Advisory", "headline": "Heat Advisory until 8 PM", "severity": "Moderate"}}]
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ARTIFACT_PATH", tmp_path / "forecast-artifacts.ndjson")
    market_book.reset_book()
    return TestClient(main.app)


def test_live_disabled_by_default_uses_stubs(client, monkeypatch):
    monkeypatch.delenv(live_sources.LIVE_ENV, raising=False)
    d = client.post("/api/v1/personal-forecast", json={"demo_mode": False}).json()
    assert d["evidence_sources"]["official_forecast"] == "official_forecast_stub"


def test_live_parses_real_payload_shapes(client, monkeypatch):
    monkeypatch.setenv(live_sources.LIVE_ENV, "1")
    def fake_fetch(url, headers=None):
        return NWS_ALERTS_PAYLOAD if "weather.gov" in url else OPEN_METEO_PAYLOAD
    monkeypatch.setattr(live_sources, "_fetch_json", fake_fetch)
    d = client.post("/api/v1/personal-forecast", json={"demo_mode": False}).json()
    assert d["evidence_sources"]["official_forecast"] == "open-meteo-forecast-live"
    assert d["evidence_sources"]["alerts"] == "nws-alerts-live"
    assert d["claim"]["temperature_f"] == 91.4
    assert d["claim"]["precip_probability"] == 0.35
    # One active NWS alert governs: PROTOCOL + official_alert_only.
    assert d["verdict"]["claim_scope"] == "official_alert_only"


def test_live_failure_falls_back_to_stub(client, monkeypatch):
    monkeypatch.setenv(live_sources.LIVE_ENV, "1")
    def broken(url, headers=None):
        raise OSError("network down")
    monkeypatch.setattr(live_sources, "_fetch_json", broken)
    d = client.post("/api/v1/personal-forecast", json={"demo_mode": False}).json()
    assert d["evidence_sources"]["official_forecast"] == "official_forecast_stub"
    assert d["claim"]["temperature_f"] == 88


def test_simulation_flags_override_live(client, monkeypatch):
    monkeypatch.setenv(live_sources.LIVE_ENV, "1")
    d = client.post("/api/v1/personal-forecast",
                    json={"demo_mode": False, "simulate_no_official_forecast": True}).json()
    assert d["evidence_sources"]["official_forecast"] == "official_forecast_stub"
    assert d["epistemology"]["official_forecast_available"] is False


def test_crowd_feedback_scoreboard(client):
    m = client.post("/api/v1/markets/seed-demo").json()["markets"][0]
    client.post(f"/api/v1/markets/{m['market_id']}/settle", json={})
    board = client.get("/api/v1/markets").json()
    cf = board["crowd_feedback"]
    assert cf["markets_scored"] == 1
    # Crowd implied 60% YES; rain market resolved NO -> crowd wrong, Brier 0.36.
    assert cf["crowd_correct"] == 0
    assert cf["crowd_brier_score"] == pytest.approx(0.36, abs=0.001)
    assert "calibration" in cf["training_note"]
