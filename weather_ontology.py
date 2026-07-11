import hashlib
import json

def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_obj(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
