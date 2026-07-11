"""Safe-harbor seam: the private foresight provider loads only from the
environment at runtime; the public repo always falls back to the public
proxy and says so."""
import sys
import types

from boundarycast_api.foresight_proxy.provider import foresight, ENV_VAR


def test_defaults_to_public_proxy(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    result = foresight({})
    assert result["provider"] == "public-proxy"
    assert "No private Manifold math" in result["risk_window"]["note"]


def test_missing_private_provider_falls_back_loudly(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "oasse_private.foresight_that_does_not_exist")
    result = foresight({})
    assert result["provider"] == "public-proxy (private provider unavailable)"


def test_private_provider_loads_from_env(monkeypatch):
    module = types.ModuleType("fake_private_foresight")
    module.risk_window = lambda evidence: {"risk_window": "private"}
    module.detect_trend = lambda evidence: {"trend": "private"}
    monkeypatch.setitem(sys.modules, "fake_private_foresight", module)
    monkeypatch.setenv(ENV_VAR, "fake_private_foresight")
    result = foresight({})
    assert result["provider"] == "private:fake_private_foresight"
    assert result["risk_window"] == {"risk_window": "private"}
