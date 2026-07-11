"""Market Factory Lite: a minimal parimutuel prediction-market book that
resolves exclusively through the BoundaryCast oracle recipe.

This is deliberately the thinnest possible market layer — play-money,
in-memory, demo-grade — because the point of the demo is the resolution
path, not the exchange. YES and NO stakes pool parimutuel-style; on a
YES/NO resolution the winning side splits the losing pool pro-rata; an
UNRESOLVED outcome refunds all stakes and routes the market to
arbitration. Every resolution stores the oracle's replayable artifact
hash on the market.

Zero-cache note: markets are public objects, so they carry only the
demo/synthetic coordinates given at creation. Play-money positions carry
no identity beyond a caller-chosen display name.
"""
import copy
import threading
from datetime import datetime, timezone

_MARKETS = {}
_COUNTER = {"market": 0, "position": 0}
# Serializes stake/settle/create so pools, positions, and status never race.
_BOOK_LOCK = threading.RLock()


def reset_book():
    with _BOOK_LOCK:
        _MARKETS.clear()
        _COUNTER["market"] = 0
        _COUNTER["position"] = 0


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_market(question, oracle_params):
    with _BOOK_LOCK:
        _COUNTER["market"] += 1
        market_id = f"mkt_{_COUNTER['market']:04d}"
        market = {
            "market_id": market_id,
            "question": question,
            "oracle_params": oracle_params,
            "oracle_recipe": "boundarycast-weather-oracle-v1",
            "status": "open",
            "pools": {"YES": 0.0, "NO": 0.0},
            "positions": [],
            "created_at": _now(),
            "resolution": None,
            "payouts": None,
        }
        _MARKETS[market_id] = market
        return market


def seed_demo(presets):
    """Atomically seed the board once: (question, oracle_params, yes, no)."""
    with _BOOK_LOCK:
        if _MARKETS:
            return False
        for question, oracle_params, yes_stake, no_stake in presets:
            market = create_market(question, oracle_params)
            stake(market["market_id"], "YES", yes_stake, trader="demo_yes")
            stake(market["market_id"], "NO", no_stake, trader="demo_no")
        return True


def list_markets():
    # Snapshot under the lock: readers must never see a mid-mutation market
    # or iterate a dict a concurrent create is resizing. Insertion order is
    # market_id order (ids are monotonic), so no sort is needed.
    with _BOOK_LOCK:
        return copy.deepcopy(list(_MARKETS.values()))


def get_market(market_id):
    with _BOOK_LOCK:
        return copy.deepcopy(_MARKETS.get(market_id))


def begin_settle(market_id):
    """Atomically claim an open market for settlement. This runs BEFORE the
    forecast pipeline so a losing concurrent settle never writes an orphan
    resolution artifact to the ledger."""
    with _BOOK_LOCK:
        market = _MARKETS.get(market_id)
        if market is None:
            return None, "unknown_market"
        if market["status"] != "open":
            return None, "market_not_open"
        market["status"] = "settling"
        return copy.deepcopy(market), None


def abort_settle(market_id):
    with _BOOK_LOCK:
        market = _MARKETS.get(market_id)
        if market is not None and market["status"] == "settling":
            market["status"] = "open"


def stake(market_id, side, amount, trader="anon"):
    with _BOOK_LOCK:
        market = _MARKETS.get(market_id)
        if market is None:
            return None, "unknown_market"
        if market["status"] != "open":
            return None, "market_not_open"
        if side not in ("YES", "NO"):
            return None, "side_must_be_yes_or_no"
        if amount <= 0:
            return None, "stake_must_be_positive"
        _COUNTER["position"] += 1
        position = {
            "position_id": f"pos_{_COUNTER['position']:04d}",
            "trader": trader,
            "side": side,
            "stake": float(amount),
            "created_at": _now(),
        }
        market["positions"].append(position)
        market["pools"][side] += float(amount)
        return position, None


def crowd_scoreboard():
    """Gamified feedback loop: stakes are votes. For every resolved market,
    compare the crowd's implied probability against the oracle outcome.
    The aggregate is exposed as a public training signal (crowd calibration)
    that future forecast weighting can consume — recorded now, honestly
    labeled as not yet weighting the public demo forecast."""
    with _BOOK_LOCK:
        scored = 0
        crowd_correct = 0
        brier_sum = 0.0
        for market in _MARKETS.values():
            resolution = market.get("resolution")
            if not resolution or resolution["resolution"] not in ("YES", "NO"):
                continue
            total = market["pools"]["YES"] + market["pools"]["NO"]
            if total <= 0:
                continue
            implied_yes = market["pools"]["YES"] / total
            outcome = 1.0 if resolution["resolution"] == "YES" else 0.0
            scored += 1
            crowd_correct += 1 if (implied_yes >= 0.5) == (outcome == 1.0) else 0
            brier_sum += (implied_yes - outcome) ** 2
        return {
            "markets_scored": scored,
            "crowd_correct": crowd_correct,
            "crowd_brier_score": round(brier_sum / scored, 3) if scored else None,
            "training_note": "Crowd stakes are recorded as a calibration signal for future forecast weighting; the public demo forecast does not consume it yet.",
        }


def _refund_all(market):
    return [
        {"position_id": p["position_id"], "trader": p["trader"], "payout": p["stake"], "kind": "refund"}
        for p in market["positions"]
    ]


def settle(market_id, resolution_record):
    """Apply an oracle resolution record to the market."""
    with _BOOK_LOCK:
        market = _MARKETS.get(market_id)
        if market is None:
            return None, "unknown_market"
        if market["status"] not in ("open", "settling"):
            return None, "market_not_open"

        outcome = resolution_record["resolution"]
        basis = resolution_record["resolution_basis"]
        market["resolution"] = {
            "resolution": outcome,
            "resolution_confidence": resolution_record.get("resolution_confidence"),
            "unresolved_reason": resolution_record.get("unresolved_reason"),
            "detail": resolution_record.get("detail"),
            "claim_scope": basis["claim_scope"],
            "gatekeeper_verdict": basis["gatekeeper_verdict"],
            "reason_codes": basis["reason_codes"],
            "scope_reason_codes": basis["scope_reason_codes"],
            "artifact_hash": resolution_record["artifact"]["artifact_hash"],
            "resolved_at": _now(),
        }

        if outcome == "UNRESOLVED":
            market["status"] = "needs_arbitration"
            market["payouts"] = _refund_all(market)
            return market, None

        market["status"] = "resolved"
        winning_pool = market["pools"][outcome]
        losing_pool = market["pools"]["NO" if outcome == "YES" else "YES"]
        if winning_pool <= 0:
            # Nobody backed the true outcome: parimutuel push. Refund the
            # losing side rather than letting their stakes vanish.
            market["payouts"] = _refund_all(market)
            return market, None
        payouts = []
        for p in market["positions"]:
            if p["side"] != outcome:
                payouts.append({"position_id": p["position_id"], "trader": p["trader"], "payout": 0.0, "kind": "lost"})
            else:
                share = p["stake"] / winning_pool
                payouts.append({
                    "position_id": p["position_id"],
                    "trader": p["trader"],
                    "payout": round(p["stake"] + share * losing_pool, 2),
                    "kind": "won",
                })
        market["payouts"] = payouts
        return market, None
