"""Market Factory Lite tests: the demo market book settles exclusively
through the BoundaryCast oracle, pays parimutuel, refunds on UNRESOLVED."""
import pytest
from fastapi.testclient import TestClient

import main
from boundarycast_api.markets import market_book


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ARTIFACT_PATH", tmp_path / "forecast-artifacts.ndjson")
    market_book.reset_book()
    return TestClient(main.app)


def seed(client):
    return client.post("/api/v1/markets/seed-demo").json()["markets"]


def test_seed_is_idempotent(client):
    assert len(seed(client)) == 3
    again = client.post("/api/v1/markets/seed-demo").json()
    assert again["seeded"] is False
    assert len(again["markets"]) == 3


def test_reset_demo_clears_stale_positions_and_resolutions(client):
    market = seed(client)[0]
    client.post(f"/api/v1/markets/{market['market_id']}/stake",
                json={"side": "YES", "amount": 10, "trader": "you"})
    client.post(f"/api/v1/markets/{market['market_id']}/settle", json={})

    fresh = client.post("/api/v1/markets/reset-demo").json()["markets"]
    assert len(fresh) == 3
    assert all(m["status"] == "open" for m in fresh)
    assert all(not any(p["trader"] == "you" for p in m["positions"]) for m in fresh)


def test_settlement_accepts_live_location_context(client, monkeypatch):
    market = seed(client)[0]
    seen = {}
    original = main.evaluate_governed_forecast

    def capture(req):
        seen.update(latitude=req.latitude, longitude=req.longitude,
                    precision_meters=req.precision_meters, demo_mode=req.demo_mode)
        # Avoid outbound weather calls while preserving the complete pipeline.
        req.demo_mode = True
        return original(req)

    monkeypatch.setattr(main, "evaluate_governed_forecast", capture)
    response = client.post(f"/api/v1/markets/{market['market_id']}/settle", json={
        "latitude": 37.782, "longitude": -122.411,
        "precision_meters": 102, "demo_mode": False,
    })
    assert response.status_code == 200
    assert seen == {"latitude": 37.782, "longitude": -122.411,
                    "precision_meters": 102, "demo_mode": False}


def test_create_and_stake(client):
    m = client.post("/api/v1/markets", json={
        "question": "Will wind exceed 25 mph at this checkpoint?",
        "metric": "wind_mph", "operator": "gt", "threshold": 25,
    }).json()
    assert m["status"] == "open"
    r = client.post(f"/api/v1/markets/{m['market_id']}/stake",
                    json={"side": "YES", "amount": 30, "trader": "alice"})
    assert r.status_code == 200
    assert r.json()["market"]["pools"]["YES"] == 30
    assert client.post("/api/v1/markets/nope/stake",
                       json={"side": "YES", "amount": 5}).status_code == 404
    assert client.post(f"/api/v1/markets/{m['market_id']}/stake",
                       json={"side": "MAYBE", "amount": 5}).status_code == 422


def test_settle_pays_parimutuel(client):
    m1 = seed(client)[0]  # rain market: demo precip 0.05 > 0.5 -> NO
    client.post(f"/api/v1/markets/{m1['market_id']}/stake",
                json={"side": "NO", "amount": 25, "trader": "alice"})
    r = client.post(f"/api/v1/markets/{m1['market_id']}/settle", json={}).json()
    assert r["resolution"]["resolution"] == "NO"
    market = r["market"]
    assert market["status"] == "resolved"
    assert market["resolution"]["artifact_hash"]
    payouts = {p["trader"]: p for p in market["payouts"]}
    assert payouts["demo_yes"]["kind"] == "lost"
    # NO pool 65 splits the YES pool 60 pro-rata: 40/65 and 25/65 shares.
    assert payouts["demo_no"]["payout"] == pytest.approx(40 + 40 / 65 * 60, abs=0.01)
    assert payouts["alice"]["payout"] == pytest.approx(25 + 25 / 65 * 60, abs=0.01)
    # Winnings conserve the total pool.
    assert sum(p["payout"] for p in market["payouts"]) == pytest.approx(125, abs=0.02)


def test_alert_market_settles_yes_under_alert(client):
    alert_market = client.post("/api/v1/markets", json={
        "question": "Will an official weather alert be active for this location today?",
        "metric": "alert_active", "operator": "gt", "threshold": 0,
    }).json()
    r = client.post(f"/api/v1/markets/{alert_market['market_id']}/settle",
                    json={"simulate_alert": True}).json()
    assert r["resolution"]["resolution"] == "YES"
    assert r["market"]["resolution"]["resolution_confidence"] == "official"


def test_condition_market_under_alert_goes_to_arbitration(client):
    m = seed(client)[0]
    r = client.post(f"/api/v1/markets/{m['market_id']}/settle",
                    json={"simulate_alert": True}).json()
    assert r["resolution"]["resolution"] == "UNRESOLVED"
    assert r["market"]["status"] == "needs_arbitration"
    assert r["market"]["resolution"]["unresolved_reason"] == "official_alert_governs"


def test_unresolved_refunds_and_routes_to_arbitration(client):
    m2 = seed(client)[1]
    r = client.post(f"/api/v1/markets/{m2['market_id']}/settle",
                    json={"simulate_no_official_forecast": True,
                          "simulate_no_observation": True}).json()
    assert r["resolution"]["resolution"] == "UNRESOLVED"
    market = r["market"]
    assert market["status"] == "needs_arbitration"
    assert all(p["kind"] == "refund" for p in market["payouts"])
    assert all(p["payout"] > 0 for p in market["payouts"])


def test_settled_market_rejects_stakes_and_resettle(client):
    m1 = seed(client)[0]
    client.post(f"/api/v1/markets/{m1['market_id']}/settle", json={})
    assert client.post(f"/api/v1/markets/{m1['market_id']}/settle", json={}).status_code == 409
    assert client.post(f"/api/v1/markets/{m1['market_id']}/stake",
                       json={"side": "YES", "amount": 5}).status_code == 409


def test_settlement_artifacts_chain(client):
    for m in seed(client):
        client.post(f"/api/v1/markets/{m['market_id']}/settle", json={})
    replay = client.get("/api/v1/replay").json()
    assert replay["ok"] is True
    assert replay["count"] == 3

