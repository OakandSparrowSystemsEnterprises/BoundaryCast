import json
from datetime import datetime, timezone
from pathlib import Path
from .hash_chain import sha256_obj
from boundarycast_api.ontology.ontology_registry import get_active_ontology

def _last_hash(path: Path):
    if not path.exists():
        return None
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return None
    return json.loads(lines[-1]).get("artifact_hash")

def create_artifact(path: Path, tenant_id, evidence, claim, policy_packs, verdict):
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = _last_hash(path)
    ontology = get_active_ontology()
    artifact = {
        "artifact_id": f"artifact_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "previous_hash": prev,
        "tenant_id": tenant_id,
        "location_context_id": evidence["location_context"].get("location_context_id"),
        "evidence_root": sha256_obj(evidence),
        "claim_root": sha256_obj(claim),
        "policy_pack_versions": [p.get("policy_pack_id") for p in policy_packs],
        "ontology_version": ontology.get("ontology_id"),
        "gatekeeper_verdict": verdict.get("gatekeeper_verdict"),
        "product_verdict": verdict.get("product_verdict"),
        "reason_codes": verdict.get("reason_codes", []),
        "microclimate_confidence": verdict.get("microclimate_confidence"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_versions": {
            "foresight_proxy": "public-proxy-v0.1",
            "gatekeeper_lite": "v0.1",
            "ontology": ontology.get("ontology_id"),
        },
        "nonce": "demo_nonce"
    }
    artifact["artifact_hash"] = sha256_obj(artifact)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(artifact, sort_keys=True) + "\n")
    return artifact
