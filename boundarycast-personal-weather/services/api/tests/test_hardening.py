"""Adversarial hardening tests: concurrency, hostile input, payout edges,
and UI injection safety."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from boundarycast_api.markets import market_book

PROJECT_ROOT = Path(main.__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ARTIFACT_PATH", tmp_path / "forecast-artifacts.ndjson")
    market_book.reset_book()
    return TestClient(main.app)


def test_concurrent_forecasts_do_not_fork_the_chain(client):
    def one(_):
        return client.post("/api/v1/personal-forecast", json={}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(one, range(24)))
    assert codes == [200] * 24
    replay = client.get("/api/v1/replay").json()
    assert replay["ok"] is True, replay
    assert replay["count"] == 24


def test_concurrent_stakes_conserve_pools(client):
    m = client.post("/api/v1/markets", json={"question": "concurrency", "metric": "wind_mph"}).json()

    def one(_):
        return client.post(f"/api/v1/markets/{m['market_id']}/stake",
                           json={"side": "YES", "amount": 1}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(one, range(50)))
    assert codes == [200] * 50
    board = client.get("/api/v1/markets").json()["markets"][0]
    assert board["pools"]["YES"] == 50
    assert len(board["positions"]) == 50


def test_seed_demo_races_do_not_duplicate(client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: client.post("/api/v1/markets/seed-demo").json(), range(4)))
    assert sum(1 for r in results if r["seeded"]) == 1
    assert len(client.get("/api/v1/markets").json()["markets"]) == 3


def test_hostile_numeric_inputs_rejected(client):
    m = client.post("/api/v1/markets", json={"question": "edges", "metric": "wind_mph"}).json()
    url = f"/api/v1/markets/{m['market_id']}/stake"
    for body in [
        '{"side": "YES", "amount": 1e999}',
        '{"side": "YES", "amount": 0}',
        '{"side": "YES", "amount": -5}',
        '{"side": "YES", "amount": 2000000}',
        '{"side": "YES", "amount": "NaN"}',
    ]:
        res = client.post(url, content=body, headers={"Content-Type": "application/json"})
        assert res.status_code == 422, body


def test_oversized_strings_rejected(client):
    assert client.post("/api/v1/personal-forecast",
                       json={"tenant_id": "x" * 101}).status_code == 422
    assert client.post("/api/v1/personal-forecast",
                       json={"surface_exposure": "x" * 101}).status_code == 422
    assert client.post("/api/v1/markets",
                       json={"question": "x" * 501, "metric": "wind_mph"}).status_code == 422
    assert client.post("/api/v1/oracle/resolve",
                       json={"metric": "temperature_f", "threshold": 1e10}).status_code == 422


def test_boundary_values_accepted(client):
    res = client.post("/api/v1/personal-forecast", json={
        "latitude": 90, "longitude": -180, "precision_meters": 100000, "forecast_hours": 72,
    })
    assert res.status_code == 200
    assert client.post("/api/v1/personal-forecast", json={"forecast_hours": 73}).status_code == 422


def test_no_winner_market_refunds_instead_of_burning_stakes(client):
    # Rain market resolves NO, but everyone staked YES: parimutuel push.
    m = client.post("/api/v1/markets", json={
        "question": "no-winner edge", "metric": "precip_probability",
        "operator": "gt", "threshold": 0.5,
    }).json()
    client.post(f"/api/v1/markets/{m['market_id']}/stake",
                json={"side": "YES", "amount": 30, "trader": "alice"})
    r = client.post(f"/api/v1/markets/{m['market_id']}/settle", json={}).json()
    assert r["resolution"]["resolution"] == "NO"
    payouts = r["market"]["payouts"]
    assert [p["kind"] for p in payouts] == ["refund"]
    assert payouts[0]["payout"] == 30


def test_mixed_traffic_keeps_chain_verifiable(client):
    client.post("/api/v1/personal-forecast", json={})
    client.post("/api/v1/oracle/resolve", json={"metric": "temperature_f", "threshold": 80})
    for m in client.post("/api/v1/markets/seed-demo").json()["markets"]:
        client.post(f"/api/v1/markets/{m['market_id']}/settle", json={})
    replay = client.get("/api/v1/replay").json()
    assert replay["ok"] is True
    assert replay["count"] == 5


def test_ui_escapes_user_content():
    app_js = (PROJECT_ROOT / "apps" / "web" / "app.js").read_text(encoding="utf-8")
    assert "function esc(" in app_js
    assert "esc(m.question)" in app_js
    assert "esc(p.trader)" in app_js
    assert "esc(c.public_message)" in app_js
