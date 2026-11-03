"""
Tests for scripts/tech_detector.py — technology / third-party detection used by
the geo-legal agent to cross-check privacy policies. No network access.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import tech_detector  # noqa: E402
from tech_detector import detect, is_third_party, match_signatures  # noqa: E402


def _response(html: str, url: str = "https://shop.example.de/", headers=None, cookies=None):
    resp = MagicMock()
    resp.status_code = 200
    resp.text = html
    resp.url = url
    resp.headers = headers or {}
    resp.raw.headers.getlist.return_value = cookies or []
    return resp


def _detect(html: str, **kw) -> dict:
    with patch("tech_detector.requests.get", return_value=_response(html, **kw)):
        return detect("https://shop.example.de/")


def _names(result: dict) -> set:
    return {t["name"] for t in result["technologies"]}


TRACKING_HTML = """<!doctype html><html><head>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script>
<script>window.dataLayer=[];function gtag(){dataLayer.push(arguments)}gtag('config','G-ABC123');</script>
<script>!function(f,b,e,v,n,t,s){}(window,document,'script');fbq('init','1234567890');</script>
<script src="/js/app.js"></script>
</head><body>
<iframe src="https://www.youtube.com/embed/xyz"></iframe>
<p>Wir akzeptieren PayPal und Klarna.</p>
</body></html>"""


class TestSignatureDetection:
    def test_detects_analytics_pixels_fonts_and_embeds(self):
        names = _names(_detect(TRACKING_HTML))
        assert {"Google Analytics", "Google Tag Manager", "Meta Pixel",
                "Google Fonts (remote)", "YouTube"} <= names

    def test_payment_names_in_visible_text_are_not_detected(self):
        names = _names(_detect(TRACKING_HTML))
        assert "PayPal" not in names
        assert "Klarna" not in names

    def test_consent_required_summary(self):
        result = _detect(TRACKING_HTML)
        assert "Meta Pixel" in result["summary"]["consent_required"]
        assert "Google" in result["summary"]["third_country_vendors"]

    def test_first_party_script_is_not_third_party(self):
        result = _detect(TRACKING_HTML)
        assert "shop.example.de" not in result["third_party_hosts"]
        assert "fonts.googleapis.com" in result["third_party_hosts"]

    def test_evidence_is_recorded(self):
        result = _detect(TRACKING_HTML)
        meta = next(t for t in result["technologies"] if t["name"] == "Meta Pixel")
        assert any("fbq" in e for e in meta["evidence"])


class TestPlatformAndConsentManager:
    def test_shopware6_from_headers(self):
        result = _detect("<html><body>Shop</body></html>",
                         headers={"sw-language-id": "abc", "Server": "Apache"})
        assert "Shopware 6" in result["platforms"]
        assert result["server"] == "Apache"

    def test_consent_manager_listed(self):
        html = '<html><head><script src="https://app.usercentrics.eu/browser-ui/latest/loader.js"></script></head></html>'
        result = _detect(html)
        assert result["consent_manager"] == ["Usercentrics"]

    def test_generator_meta(self):
        result = _detect('<html><head><meta name="generator" content="WordPress 6.8"></head></html>')
        assert "generator: WordPress 6.8" in result["platforms"]


class TestCookiesAndErrors:
    def test_server_cookies_classified(self):
        result = _detect("<html></html>", cookies=["session-abc=1; Path=/", "_fbp=fb.1; Path=/"])
        classes = {c["name"]: c["class"] for c in result["cookies_set_by_server"]}
        assert classes["session-abc"] == "technical"
        assert classes["_fbp"] == "unknown"

    def test_fetch_error_is_reported_not_raised(self):
        with patch("tech_detector.requests.get",
                   side_effect=tech_detector.requests.RequestException("boom")):
            result = detect("https://down.example/")
        assert result["errors"] and result["technologies"] == []


class TestHelpers:
    def test_is_third_party(self):
        assert not is_third_party("https://cdn.shop.example.de/x.js", "https://www.example.de/")
        assert is_third_party("https://connect.facebook.net/x.js", "https://www.example.de/")
        assert not is_third_party("https://a.example.co.uk/x", "https://b.example.co.uk/")

    def test_match_signatures_empty(self):
        assert match_signatures([], "", "") == []
