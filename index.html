from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from boundarycast_api.artifacts.replay import verify_artifact_chain

path = Path(__file__).resolve().parents[1] / "artifacts" / "forecast-artifacts.ndjson"
result = verify_artifact_chain(path)

print(f"verified: {result['ok']}")
print(f"artifacts: {result['count']}")
print(result.get("message") or result.get("error"))

if not result["ok"]:
    raise SystemExit(1)
