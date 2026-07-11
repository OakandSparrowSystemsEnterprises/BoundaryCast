"""Private foresight provider plug point (safe harbor seam).

The public repository ships only the public proxy. Production deployments
may load a private foresight provider — a separate, never-published
package — by setting BOUNDARYCAST_FORESIGHT_PROVIDER to an importable
module path. The module must expose:

    risk_window(evidence) -> dict
    detect_trend(evidence) -> dict

The private mathematics stays in a private repository and enters only at
runtime, so the public git history never contains it. If the variable is
unset or the provider fails to load for any reason, the public proxy is
used and the provenance field says so — the system never silently
pretends to have the private stack.
"""
import importlib
import os
from functools import lru_cache

from . import risk_window as _public_risk_window
from . import trend_detector as _public_trend

ENV_VAR = "BOUNDARYCAST_FORESIGHT_PROVIDER"


@lru_cache(maxsize=8)
def _load_module(module_path):
    """Resolve a provider module once per path; any load failure — import
    errors, syntax errors, exceptions in the module body — falls back."""
    try:
        module = importlib.import_module(module_path)
    except Exception:
        return None
    if callable(getattr(module, "risk_window", None)) and callable(getattr(module, "detect_trend", None)):
        return module
    return None


def load_provider():
    module_path = os.environ.get(ENV_VAR)
    if not module_path:
        return None, "public-proxy"
    module = _load_module(module_path)
    if module is None:
        return None, "public-proxy (private provider unavailable)"
    return module, f"private:{module_path}"


def foresight(evidence):
    provider, provenance = load_provider()
    risk_fn = provider.risk_window if provider else _public_risk_window.risk_window
    trend_fn = provider.detect_trend if provider else _public_trend.detect_trend
    return {
        "risk_window": risk_fn(evidence),
        "trend": trend_fn(evidence),
        "provider": provenance,
    }
