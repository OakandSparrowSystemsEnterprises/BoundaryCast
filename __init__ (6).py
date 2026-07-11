import json
from pathlib import Path

def load_policy_packs(policy_dir: Path):
    packs = []
    for path in sorted(policy_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as f:
            packs.append(json.load(f))
    return packs
