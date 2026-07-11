#!/usr/bin/env bash
# Package the v3 release ZIP: no __pycache__, no generated artifact logs
# (the sample synthetic artifact in examples/ is kept), no venvs.
set -euo pipefail
cd "$(dirname "$0")/../.."

OUT="boundarycast-personal-weather-v3-claim-scope.zip"
rm -f "$OUT"
zip -r "$OUT" boundarycast-personal-weather \
  -x "*__pycache__*" \
  -x "*.pyc" \
  -x "*/.venv/*" \
  -x "boundarycast-personal-weather/artifacts/*.ndjson"
echo "wrote $OUT"
