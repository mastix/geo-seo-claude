"""
Tests for scripts/ai_content_scanner.py — AI image provenance and disclosure
detection used by the geo-ai-act agent (EU AI Act Art. 50). No network access.
"""

import io
import os
import sys
from unittest.mock import MagicMock, patch

from PIL import Image, PngImagePlugin

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import ai_content_scanner as acs  # noqa: E402
from ai_content_scanner import LABEL_RE, classify, scan_image_bytes, scan_page  # noqa: E402

XMP_AI = (
    '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
    'Iptc4xmpExt:DigitalSourceType="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"/>'
    '</rdf:RDF></x:xmpmeta>'
)


def _jpeg(xmp: str = None) -> bytes:
    buf = io.BytesIO()
    kw = {"xmp": xmp.encode()} if xmp else {}
    Image.new("RGB", (8, 8), "red").save(buf, "JPEG", **kw)
    return buf.getvalue()


def _png(text: dict = None) -> bytes:
    buf = io.BytesIO()
    info = PngImagePlugin.PngInfo()
    for k, v in (text or {}).items():
        info.add_text(k, v)
    Image.new("RGB", (8, 8), "blue").save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


class TestImageMetadata:
    def test_plain_jpeg_has_no_signal(self):
        assert scan_image_bytes(_jpeg())["ai_signal"] == "none"

    def test_iptc_digital_source_type_is_strong(self):
        info = scan_image_bytes(_jpeg(XMP_AI))
        assert info["digital_source_type"] == "trainedAlgorithmicMedia"
        assert info["ai_signal"] == "strong"

    def test_stable_diffusion_parameters_chunk_is_strong(self):
        info = scan_image_bytes(_png({"parameters": "a bowl of soup, Steps: 30, Sampler: Euler"}))
        assert info["ai_signal"] == "strong"
        assert any(s["type"] == "generator_parameters" for s in info["signals"])

    def test_generator_name_in_software_is_medium(self):
        info = scan_image_bytes(_png({"Software": "Midjourney v7"}))
        assert info["ai_signal"] == "medium"
        assert "Midjourney" in info["generator_hints"]

    def test_c2pa_manifest_detected(self):
        data = _jpeg() + b"jumb....jumdc2pa....claim_generator\x00Adobe_Firefly/3.0"
        info = scan_image_bytes(data)
        assert info["c2pa"] is True
        assert info["ai_signal"] == "strong"

    def test_non_ai_photo_software_is_ignored(self):
        assert scan_image_bytes(_png({"Software": "Adobe Lightroom 7.2"}))["ai_signal"] == "none"


class TestLabels:
    def test_german_and_english_labels(self):
        for text in ["Symbolbild (KI)", "Rezeptbild: mit KI erstellt", "KI-generiert", "AI-generated image"]:
            assert LABEL_RE.search(text), text

    def test_false_positives_rejected(self):
        for text in ["Skibild am Hang", "KI-Bildung im Verein", "Thai image gallery"]:
            assert not LABEL_RE.search(text), text

    def test_classify(self):
        unlabelled = {"ai_signal": "strong", "label": {"labelled": False}}
        assert classify(unlabelled, has_page_notice=False) == "ai_marked_unlabelled"
        assert classify(unlabelled, has_page_notice=True) == "ai_marked_page_notice_only"
        assert classify({"ai_signal": "none", "label": {"labelled": True}}, False) == "labelled_no_marker"
        assert classify({"ai_signal": "unknown", "label": {"labelled": False}}, False) == "not_scanned"


PAGE_HTML = """<html><body>
<figure><img src="/a.jpg" alt="Kürbissuppe"><figcaption>Symbolbild (KI)</figcaption></figure>
<img src="/b.png" alt="Team beim Training">
<img src="/c.jpg" alt="Vereinsheim">
<img src="/logo.svg" alt="Logo">
<script src="https://www.chatbase.co/embed.min.js"></script>
</body></html>"""


def _fake_get(url, **kwargs):
    resp = MagicMock()
    resp.status_code = 200
    resp.url = url
    bodies = {
        "https://club.example.de/": PAGE_HTML.encode(),
        "https://club.example.de/a.jpg": _jpeg(XMP_AI),
        "https://club.example.de/b.png": _png({"parameters": "photo of a football team"}),
        "https://club.example.de/c.jpg": _jpeg(),
    }
    body = bodies[url]
    resp.text = body.decode() if url.endswith("/") else ""
    resp.iter_content.return_value = [body]
    return resp


class TestScanPage:
    def _scan(self):
        with patch.object(acs.requests, "get", side_effect=_fake_get):
            return scan_page("https://club.example.de/", delay=0)

    def test_statuses_per_image(self):
        page = self._scan()
        status = {i["src"].rsplit("/", 1)[-1]: i["status"] for i in page["images"]}
        assert status == {"a.jpg": "ai_marked_labelled", "b.png": "ai_marked_unlabelled", "c.jpg": "no_signal"}

    def test_svg_skipped_and_label_location_recorded(self):
        page = self._scan()
        assert not any(i["src"].endswith(".svg") for i in page["images"])
        a = next(i for i in page["images"] if i["src"].endswith("a.jpg"))
        assert a["label"]["where"] == "figcaption"

    def test_chat_widget_without_disclosure(self):
        page = self._scan()
        assert page["chat_widgets"] == ["Chatbase"]
        assert page["chat_disclosure_text"] == ""

    def test_page_fetch_error_is_reported(self):
        with patch.object(acs.requests, "get", side_effect=acs.requests.RequestException("down")):
            page = scan_page("https://down.example/", delay=0)
        assert page["errors"] and page["images"] == []


class TestFalsePositives:
    def test_technical_xmp_fields_do_not_match_tool_names(self):
        xmp = ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description '
               'aux:Lens="Tamron Macro" aux:ImageNumber="41406" xmp:CreatorTool="Adobe Photoshop 22.5"/>'
               '</rdf:RDF></x:xmpmeta>')
        assert scan_image_bytes(_jpeg(xmp))["ai_signal"] == "none"

    def test_creator_tool_attribute_with_ai_tool_matches(self):
        xmp = ('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description '
               'xmp:CreatorTool="Adobe Firefly"/></rdf:RDF></x:xmpmeta>')
        info = scan_image_bytes(_jpeg(xmp))
        assert info["ai_signal"] == "medium"
        assert any("firefly" in h.lower() for h in info["generator_hints"])
