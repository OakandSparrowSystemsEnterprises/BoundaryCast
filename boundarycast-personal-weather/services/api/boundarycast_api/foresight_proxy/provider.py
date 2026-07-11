"""Private foresight provider plug point (safe harbor seam).

The public repository ships only the public proxy. Production deployments
may load a private foresight provider — a separate, never-published
package — by setting BOUNDARYCAST_FORESIGHT_PROVIDER to an importable
module path. The module must expose:

    risk_window(evidence) -> dict
    detect_trend(evidence) -> dict

The private mathematics stays in a private repository and enters only at
runtime, so the public git history never contains it. If the variable is
unset or the import fails, the public proxy is used and the provenance
field says so — the system never silently pretends to have the private
stack.
"""
import importlib
import os

from . import risk_window as _public_risk_window
from . import trend_detector as _public_trend

ENV_VAR = "BOUNDARYCAST_FORESIGHT_PROVIDER"


def load_provider():
    module_path = os.environ.get(ENV_VAR)
    if not module_path:
        return None, "public-proxy"
    try:
        module = importlib.import_module(module_path)
        if callable(getattr(module, "risk_window", None)) and callable(getattr(module, "detect_trend", None)):
            return module, f"private:{module_path}"
    except ImportError:
        pass
    return None, "public-proxy (private provider unavailable)"


def foresight(evidence):
    provider, provenance = load_provider()
    if provider is None:
        return {
            "risk_window": _public_risk_window.risk_window(evidence),
            "trend": _public_trend.detect_trend(evidence),
            "provider": provenance,
        }
    return {
        "risk_window": provider.risk_window(evidence),
        "trend": provider.detect_trend(evidence),
        "provider": provenance,
    }
