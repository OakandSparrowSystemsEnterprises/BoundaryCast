"""Safe-harbor seam: the private foresight provider loads only from the
environment at runtime; the public repo always falls back to the public
proxy and says so — for ANY load failure, not just ImportError."""
import sys
import types

import pytest

from boundarycast_api.foresight_proxy import provider
from boundarycast_api.foresight_proxy.provider import foresight, ENV_VAR


@pytest.fixture(autouse=True)
def clear_provider_cache():
    provider._load_module.cache_clear()
    yield
    provider._load_module.cache_clear()


def test_defaults_to_public_proxy(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    result = foresight({})
    assert result["provider"] == "public-proxy"
    assert "No private Manifold math" in result["risk_window"]["note"]


def test_missing_private_provider_falls_back_loudly(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "oasse_private.foresight_that_does_not_exist")
    result = foresight({})
    assert result["provider"] == "public-proxy (private provider unavailable)"


def test_broken_private_provider_falls_back_for_any_exception(monkeypatch):
    def explode(_path):
        raise RuntimeError("provider module body blew up")
    monkeypatch.setattr(provider.importlib, "import_module", explode)
    monkeypatch.setenv(ENV_VAR, "oasse_private.broken")
    result = foresight({})
    assert result["provider"] == "public-proxy (private provider unavailable)"
    assert "No private Manifold math" in result["risk_window"]["note"]


def test_private_provider_loads_from_env(monkeypatch):
    module = types.ModuleType("fake_private_foresight")
    module.risk_window = lambda evidence: {"risk_window": "private"}
    module.detect_trend = lambda evidence: {"trend": "private"}
    monkeypatch.setitem(sys.modules, "fake_private_foresight", module)
    monkeypatch.setenv(ENV_VAR, "fake_private_foresight")
    result = foresight({})
    assert result["provider"] == "private:fake_private_foresight"
    assert result["risk_window"] == {"risk_window": "private"}
