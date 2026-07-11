"""Legal/compliance UX tests.

Covers:
- Gambling warning presence in index.html
- Terms acceptance checkbox and error-message elements in index.html
- Privacy notice presence in index.html
- MSA and EULA static pages are accessible (HTTP 200)
- Terms-acceptance gating at the JS/API boundary (UI contract validated
  via HTML structure; the backend itself is API-only, so gating is client-
  side — these tests confirm the required HTML controls exist)
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import main
from boundarycast_api.markets import market_book

WEB_DIR = Path(main.__file__).resolve().parents[2] / "apps" / "web"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ARTIFACT_PATH", tmp_path / "forecast-artifacts.ndjson")
    market_book.reset_book()
    return TestClient(main.app)


# ---------------------------------------------------------------------------
# Static page accessibility
# ---------------------------------------------------------------------------

def test_index_accessible(client):
    r = client.get("/ui/")
    assert r.status_code == 200
    assert "BoundaryCast" in r.text


def test_msa_page_accessible(client):
    r = client.get("/ui/msa.html")
    assert r.status_code == 200
    assert "Master Service Agreement" in r.text


def test_eula_page_accessible(client):
    r = client.get("/ui/eula.html")
    assert r.status_code == 200
    assert "End User License Agreement" in r.text


# ---------------------------------------------------------------------------
# Gambling warning
# ---------------------------------------------------------------------------

def test_gambling_warning_present_in_index():
    html = (WEB_DIR / "index.html").read_text()
    assert "gamblingWarning" in html, "gambling warning element id missing"
    assert "speculative" in html.lower(), "speculative participation language missing"
    assert "not" in html.lower() and "licensed" in html.lower(), (
        "warning should state this is not a licensed gambling product"
    )


def test_gambling_warning_in_call_weather_section():
    html = (WEB_DIR / "index.html").read_text()
    # The warning must appear before (i.e. above) the market board in the DOM.
    assert html.index("gamblingWarning") < html.index("marketBoard"), (
        "gambling warning must appear before the market board in the DOM"
    )


# ---------------------------------------------------------------------------
# Terms acceptance controls
# ---------------------------------------------------------------------------

def test_terms_checkbox_present_in_index():
    html = (WEB_DIR / "index.html").read_text()
    assert 'id="termsAccepted"' in html, "terms acceptance checkbox missing"
    assert 'type="checkbox"' in html, "terms acceptance input must be a checkbox"


def test_terms_error_element_present_in_index():
    html = (WEB_DIR / "index.html").read_text()
    assert 'id="termsError"' in html, "terms error message element missing"


def test_msa_link_in_index():
    html = (WEB_DIR / "index.html").read_text()
    assert "msa.html" in html, "link to MSA missing from index"


def test_eula_link_in_index():
    html = (WEB_DIR / "index.html").read_text()
    assert "eula.html" in html, "link to EULA missing from index"


def test_terms_gate_in_app_js():
    js = (WEB_DIR / "app.js").read_text()
    assert "requireTerms" in js, "requireTerms gating function missing from app.js"
    assert "termsError" in js, "termsError element not referenced in app.js"


def test_terms_gate_applied_to_stake_and_settle():
    js = (WEB_DIR / "app.js").read_text()
    assert "requireTerms" in js
    # Find the marketBoard event listener block and verify requireTerms is called
    # inside it before any stake/settle API fetch is made.
    listener_start = js.index("$('marketBoard').addEventListener")
    listener_snippet = js[listener_start: listener_start + 600]
    assert "requireTerms()" in listener_snippet, (
        "requireTerms() must be called inside the marketBoard click handler"
    )
    assert "btn.dataset.stake" in listener_snippet, (
        "btn.dataset.stake must be present in the marketBoard click handler"
    )
    # The guard line must short-circuit before any fetch call.
    gate_line = "requireTerms()) return"
    assert gate_line in listener_snippet, (
        "handler must return early when requireTerms() returns false"
    )
    assert listener_snippet.index(gate_line) < listener_snippet.index("fetch("), (
        "requireTerms() guard must appear before any fetch() call in the handler"
    )


# ---------------------------------------------------------------------------
# Privacy notice
# ---------------------------------------------------------------------------

def test_privacy_notice_present_in_index():
    html = (WEB_DIR / "index.html").read_text()
    assert "privacyNotice" in html, "privacy notice element id missing"
    assert "not store" in html.lower() and "precise location" in html.lower(), (
        "privacy notice must state that precise location is not stored"
    )


def test_location_not_stored_copy_in_geo_handler():
    js = (WEB_DIR / "app.js").read_text()
    assert "never stored" in js.lower() or "not stored" in js.lower(), (
        "app.js geo handler should reinforce that location is never stored"
    )


# ---------------------------------------------------------------------------
# MSA and EULA document content
# ---------------------------------------------------------------------------

def test_msa_states_no_real_money():
    html = (WEB_DIR / "msa.html").read_text()
    assert "demonstration credits" in html.lower() or "play credits" in html.lower(), (
        "MSA must clarify credits are for demonstration only"
    )
    assert "not" in html.lower() and "real money" in html.lower(), (
        "MSA must explicitly state no real money"
    )


def test_msa_states_location_not_stored():
    html = (WEB_DIR / "msa.html").read_text()
    assert "not store" in html.lower() and "location" in html.lower(), (
        "MSA must include location privacy statement"
    )


def test_eula_states_speculative_feature():
    html = (WEB_DIR / "eula.html").read_text()
    assert "demonstration credits" in html.lower() or "play credits" in html.lower()
    assert "not a licensed gambling" in html.lower(), (
        "EULA must state this is not a licensed gambling product"
    )
