import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from .hash_chain import sha256_obj
from .location_minimization import minimize_location
from boundarycast_api.ontology.ontology_registry import get_active_ontology

# The ledger is append-only and previous_hash links each artifact to the
# last: concurrent writers must serialize or the chain forks and replay
# verification fails.
_LEDGER_LOCK = threading.Lock()

PRIVACY_NOTES = (
    "Zero-cache posture: no account, no identity, no location history. "
    "Location is used for the live forecast request only; this artifact "
    "stores a minimized location binding, never a raw real-world coordinate."
)

def _last_hash(path: Path):
    if not path.exists():
        return None
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return None
    return json.loads(lines[-1]).get("artifact_hash")

def create_artifact(path: Path, req, evidence, claim, policy_packs, verdict):
    with _LEDGER_LOCK:
        return _create_artifact_locked(path, req, evidence, claim, policy_packs, verdict)

def _create_artifact_locked(path: Path, req, evidence, claim, policy_packs, verdict):
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = _last_hash(path)
    ontology = get_active_ontology()
    binding = minimize_location(req.latitude, req.longitude, req.demo_mode)
    artifact = {
        "artifact_id": f"artifact_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "previous_hash": prev,
        "tenant_id": req.tenant_id,
        "location_context_id": evidence["location_context"].get("location_context_id"),
        "location_binding_type": binding["location_binding_type"],
        "location_binding_value": binding["location_binding_value"],
        "zero_cache": True,
        "privacy_notes": PRIVACY_NOTES,
        "evidence_root": sha256_obj(evidence),
        "claim_root": sha256_obj(claim),
        "policy_pack_versions": [p.get("policy_pack_id") for p in policy_packs],
        "ontology_version": ontology.get("ontology_id"),
        "gatekeeper_verdict": verdict.get("gatekeeper_verdict"),
        "product_verdict": verdict.get("product_verdict"),
        "reason_codes": verdict.get("reason_codes", []),
        "claim_scope": verdict.get("claim_scope"),
        "requested_scope": verdict.get("requested_scope"),
        "scope_reason_codes": verdict.get("scope_reason_codes", []),
        "fallback_applied": verdict.get("fallback_applied", False),
        "microclimate_confidence": verdict.get("microclimate_confidence"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_versions": {
            "foresight_proxy": "public-proxy-v0.2",
            "gatekeeper_lite": "v0.2",
            "ontology": ontology.get("ontology_id"),
        },
        "nonce": "demo_nonce"
    }
    artifact["artifact_hash"] = sha256_obj(artifact)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(artifact, sort_keys=True) + "\n")
    return artifact
