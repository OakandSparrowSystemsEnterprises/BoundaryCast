import json
from pathlib import Path
from .hash_chain import sha256_obj

def verify_artifact_chain(path: Path):
    if not path.exists():
        return {"ok": True, "count": 0, "message": "No artifacts yet."}
    previous = None
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        artifact = json.loads(line)
        expected_prev = artifact.get("previous_hash")
        if expected_prev != previous:
            return {"ok": False, "count": count, "error": "previous_hash mismatch"}
        stored = artifact.get("artifact_hash")
        clone = dict(artifact)
        clone.pop("artifact_hash", None)
        if sha256_obj(clone) != stored:
            return {"ok": False, "count": count, "error": "artifact_hash mismatch"}
        previous = stored
        count += 1
    return {"ok": True, "count": count, "message": "Artifact chain verified."}
