#!/usr/bin/env python3
"""
Scan pages for AI-generated images and AI chat widgets, and check whether they
are visibly disclosed. Used by the geo-ai-act agent (EU AI Act Art. 50).

What it can detect (deterministic, no guessing):
  * Provenance / AI markers embedded in image files:
      - C2PA / Content Credentials manifests (JUMBF boxes labelled "c2pa")
      - IPTC "DigitalSourceType" values for AI media in XMP
        (trainedAlgorithmicMedia, compositeWithTrainedAlgorithmicMedia, ...)
      - Generator names in EXIF/XMP/PNG text chunks (Midjourney, DALL-E,
        Firefly, Stable Diffusion parameters, ComfyUI workflows, ...)
  * Visible disclosure next to each image: alt, title, aria-label,
    figcaption and the surrounding text ("KI-generiert", "AI-generated", ...),
    plus page-wide notices ("Bilder mit KI erstellt").
  * AI chat widgets (script hosts / markup) and whether the page text
    discloses the AI.

What it cannot detect: AI images whose metadata was stripped (most CMSs and
CDNs strip it), invisible watermarks such as SynthID, and AI-written text.
"No signal" therefore never means "not AI-generated".

Usage:
    python3 ai_content_scanner.py <url> [<url> ...] [--max-images N] [--delay S]

Prints JSON to stdout.
"""

import argparse
import io
import json
import re
import sys
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:  # Pillow is optional; byte-level checks still work
    Image = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
SKIP_EXT = (".svg", ".ico", ".gif")

# IPTC Digital Source Type vocabulary (cv.iptc.org/newscodes/digitalsourcetype/)
AI_SOURCE_TYPES = {
    "trainedAlgorithmicMedia": "AI-generated (trained model)",
    "compositeWithTrainedAlgorithmicMedia": "composite incl. AI-generated elements",
    "algorithmicallyEnhanced": "algorithmically enhanced",
    "compositeSynthetic": "composite of synthetic elements",
    "algorithmicMedia": "algorithmically generated (no training data)",
}
AI_TOOL_RE = re.compile(
    r"\b(?:midjourney|dall[\s·\-]?e|openai|chatgpt|gpt-image|stable[\s_-]?diffusion|sdxl|"
    r"automatic1111|comfyui|invokeai|adobe firefly|firefly|imagen|gemini|nano[\s-]?banana|"
    r"\bflux(\.1)?\b|black forest labs|leonardo\.ai|ideogram|runway|\bsora\b|bing image creator|"
    r"copilot designer|designer\.microsoft|canva (ai|magic)|magic media|grok|aurora|"
    r"recraft|krea|playground ai|dreamstudio|nightcafe)(?!\w)",
    re.I,
)
LABEL_RE = re.compile(
    r"\b(?:ki[\s-]?generiert|ki[\s-]?erzeugt|mit (hilfe )?(von )?ki (erstellt|generiert|erzeugt)|"
    r"(von|durch) (einer )?(künstliche[rn]? intelligenz|ki) (erstellt|generiert|erzeugt)|"
    r"ki[\s-]?bild|ki[\s-]?symbolbild|symbolbild \(ki\)|künstlich erzeugt|synthetisch erzeugt|"
    r"ai[\s-]?generated|generated (with|by) (ai|artificial intelligence)|created (with|by) ai|"
    r"made with ai|ai[\s-]?image|image: ai|ai-created|synthetic image)(?!\w)",
    re.I,
)
AI_CHAT_SIGNATURES = [
    ("Chatbase", ["chatbase.co"]), ("Voiceflow", ["voiceflow.com"]), ("Botpress", ["botpress.cloud", "bpcontent"]),
    ("Tidio (Lyro AI)", ["tidio.co", "tidiochat"]), ("Intercom (Fin AI)", ["intercom.io", "intercomcdn.com"]),
    ("Zendesk (AI agents)", ["zdassets.com"]), ("Userlike", ["userlike.com", "userlike-cdn"]),
    ("moin.ai", ["moin.ai"]), ("Landbot", ["landbot.io"]), ("Crisp", ["crisp.chat"]),
    ("Drift", ["drift.com", "driftt.com"]), ("Ada", ["ada.support"]), ("Typebot", ["typebot.io"]),
    ("HubSpot Chat", ["js.usemessages.com", "hubspot.com/conversations"]), ("Kauz", ["kauz.ai"]),
    ("Freshchat", ["freshchat.com", "wchat.freshchat"]), ("LiveChat", ["livechatinc.com"]),
    ("tawk.to", ["tawk.to"]), ("Chatwoot", ["chatwoot"]),
]
CHAT_DISCLOSURE_RE = re.compile(
    r"ki[\s-]?(assistent|chat|bot|agent)|virtuelle[rn]? assistent|chatbot|künstliche intelligenz|"
    r"ai (assistant|agent|chat)|powered by (ai|gpt|openai)|virtual assistant",
    re.I,
)


# ---------------------------------------------------------------------------
# Image metadata analysis (pure functions, no network)
# ---------------------------------------------------------------------------
def scan_image_bytes(data: bytes) -> dict:
    """Return AI provenance signals found in raw image bytes."""
    signals = []
    info = {"format": None, "c2pa": False, "digital_source_type": None,
            "generator_hints": [], "created": None}

    head = data[:16]
    if head.startswith(b"\xff\xd8"):
        info["format"] = "jpeg"
    elif head.startswith(b"\x89PNG"):
        info["format"] = "png"
    elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        info["format"] = "webp"
    elif b"ftypavif" in head or b"ftypheic" in head or b"ftypmif1" in head:
        info["format"] = "avif/heif"

    # C2PA manifests live in JUMBF boxes ("jumb") labelled "c2pa"
    if b"c2pa" in data and (b"jumb" in data or b"jumd" in data):
        info["c2pa"] = True
        signals.append({"type": "c2pa_manifest", "strength": "strong",
                        "detail": "C2PA / Content Credentials manifest present"})
        gen = re.search(rb"claim_generator[^A-Za-z0-9]{1,8}([ -~]{3,80})", data)
        if gen:
            info["generator_hints"].append(gen.group(1).decode("ascii", "ignore").strip())

    # XMP packet
    xmp = None
    m = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", data, re.S)
    if m:
        xmp = m.group(0).decode("utf-8", "ignore")
    # Only descriptive fields are searched for tool names: technical XMP
    # (e.g. aux:ImageNumber) would otherwise produce false hits.
    text_blobs = []

    # IPTC DigitalSourceType can sit in XMP or (as URI) inside the C2PA manifest
    for blob in [xmp or "", data[:2_000_000].decode("latin-1", "ignore")]:
        dst = re.search(r"digitalsourcetype/([A-Za-z]+)", blob)
        if dst:
            info["digital_source_type"] = dst.group(1)
            break
    if info["digital_source_type"] in AI_SOURCE_TYPES:
        signals.append({"type": "iptc_digital_source_type", "strength": "strong",
                        "detail": f"{info['digital_source_type']}: {AI_SOURCE_TYPES[info['digital_source_type']]}"})

    if xmp:
        for tag in ("xmp:CreatorTool", "photoshop:Credit", "dc:description", "dc:title",
                    "tiff:Software", "Iptc4xmpCore:ExtDescrAccessibility", "plus:ImageSupplierName"):
            for tm in re.finditer(rf"{tag}[^>]*?>(.{{0,400}}?)</{tag}>|{tag}=\"([^\"]{{1,200}})\"", xmp, re.S):
                text_blobs.append(re.sub(r"<[^>]+>", " ", tm.group(1) or tm.group(2) or ""))
        cd = re.search(r"xmp:CreateDate[=>\"']+([0-9T:\-+.]{10,30})", xmp)
        if cd:
            info["created"] = cd.group(1)

    # EXIF + PNG text chunks via Pillow
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(data))
            exif = img.getexif()
            for tag_id in (0x0131, 0x010E, 0x013B, 0x9286):  # Software, ImageDescription, Artist, UserComment
                val = exif.get(tag_id)
                if val:
                    text_blobs.append(str(val))
            dt = exif.get(0x0132)  # DateTime
            if dt and not info["created"]:
                info["created"] = str(dt)
            for key, val in (img.info or {}).items():
                if not isinstance(val, (str, bytes)):
                    continue
                sval = val.decode("utf-8", "ignore") if isinstance(val, bytes) else val
                if key.lower() in ("parameters", "prompt", "workflow", "invokeai_metadata", "sd-metadata"):
                    signals.append({"type": "generator_parameters", "strength": "strong",
                                    "detail": f"PNG text chunk '{key}' (diffusion generator settings)"})
                text_blobs.append(f"{key}: {sval[:300]}")
        except Exception:  # noqa: BLE001 — undecodable image, keep byte-level results
            pass

    for blob in text_blobs:
        tm = AI_TOOL_RE.search(blob or "")
        if tm:
            hint = tm.group(0)
            if hint not in info["generator_hints"]:
                info["generator_hints"].append(hint)
    if info["generator_hints"] and not any(s["strength"] == "strong" for s in signals):
        signals.append({"type": "generator_name", "strength": "medium",
                        "detail": "AI tool named in metadata: " + ", ".join(info["generator_hints"][:3])})
    elif info["generator_hints"]:
        signals.append({"type": "generator_name", "strength": "info",
                        "detail": "Generator: " + ", ".join(info["generator_hints"][:3])})

    info["signals"] = signals
    info["ai_signal"] = ("strong" if any(s["strength"] == "strong" for s in signals)
                         else "medium" if any(s["strength"] == "medium" for s in signals) else "none")
    return info


# ---------------------------------------------------------------------------
# HTML analysis
# ---------------------------------------------------------------------------
def _best_src(img, base: str):
    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
        val = img.get(attr)
        if val and not val.startswith("data:"):
            return urljoin(base, val.strip())
    srcset = img.get("srcset") or img.get("data-srcset")
    if srcset:
        last = srcset.split(",")[-1].strip().split(" ")[0]
        if last:
            return urljoin(base, last)
    return None


def local_label(img) -> dict:
    """Visible disclosure attached to this image (alt/title/figcaption/nearby text)."""
    texts = {
        "alt": img.get("alt") or "",
        "title": img.get("title") or "",
        "aria-label": img.get("aria-label") or "",
    }
    fig = img.find_parent("figure")
    if fig and fig.find("figcaption"):
        texts["figcaption"] = fig.find("figcaption").get_text(" ", strip=True)
    # Nearby text only from a small wrapper that belongs to this image alone,
    # otherwise one caption would "label" every image on the page.
    parent = img.parent
    if (parent is not None and parent.name not in ("body", "html", "main", "article", "section")
            and len(parent.find_all("img")) == 1):
        nearby = parent.get_text(" ", strip=True)
        if len(nearby) <= 300:
            texts["nearby"] = nearby
    for where, text in texts.items():
        m = LABEL_RE.search(text)
        if m:
            return {"labelled": True, "where": where, "text": text[:160]}
    return {"labelled": False, "where": None, "text": None}


def page_notice(soup) -> str:
    """A general AI-image notice on the page (e.g. in the footer), not a single image's caption."""
    clone = BeautifulSoup(str(soup), "lxml")
    for cap in clone.find_all("figcaption"):
        cap.decompose()
    text = clone.get_text(" ", strip=True)
    m = LABEL_RE.search(text)
    if not m:
        return ""
    start = max(0, m.start() - 80)
    return text[start:m.end() + 80]


def detect_chat_widgets(html: str, soup) -> list:
    hosts = [s.get("src", "") for s in soup.find_all("script")] + [i.get("src", "") for i in soup.find_all("iframe")]
    blob = "\n".join(hosts) + "\n" + html[:500_000]
    found = []
    for name, needles in AI_CHAT_SIGNATURES:
        if any(n.lower() in blob.lower() for n in needles):
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------
def fetch_bytes(url: str, timeout: int) -> bytes:
    resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    if resp.status_code != 200:
        raise requests.RequestException(f"HTTP {resp.status_code}")
    chunks, size = [], 0
    for chunk in resp.iter_content(65536):
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_IMAGE_BYTES:
            break
    return b"".join(chunks)


def scan_page(url: str, max_images: int = 15, delay: float = 1.0, timeout: int = 30) -> dict:
    page = {"url": url, "status_code": None, "page_notice": "", "chat_widgets": [],
            "chat_disclosure_text": "", "media_elements": {"video": 0, "audio": 0},
            "images": [], "errors": []}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        page["status_code"] = resp.status_code
        html = resp.text or ""
        base = resp.url or url
    except requests.RequestException as exc:
        page["errors"].append(f"page fetch failed: {exc}")
        return page

    soup = BeautifulSoup(html, "lxml")
    page["page_notice"] = page_notice(soup)
    page["chat_widgets"] = detect_chat_widgets(html, soup)
    if page["chat_widgets"]:
        m = CHAT_DISCLOSURE_RE.search(soup.get_text(" ", strip=True))
        page["chat_disclosure_text"] = m.group(0) if m else ""
    page["media_elements"] = {"video": len(soup.find_all("video")), "audio": len(soup.find_all("audio"))}

    seen = set()
    candidates = []
    for img in soup.find_all("img"):
        src = _best_src(img, base)
        if not src or src in seen or urlparse(src).path.lower().endswith(SKIP_EXT):
            continue
        seen.add(src)
        candidates.append((src, img))
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        src = urljoin(base, og["content"])
        if src not in seen:
            candidates.append((src, None))

    for src, img in candidates[:max_images]:
        entry = {"src": src, "alt": (img.get("alt") if img is not None else None),
                 "context": "og:image" if img is None else "img"}
        entry["label"] = local_label(img) if img is not None else {"labelled": False, "where": None, "text": None}
        try:
            if delay:
                time.sleep(delay)
            data = fetch_bytes(src, timeout)
            meta = scan_image_bytes(data)
            entry.update({k: meta[k] for k in ("format", "ai_signal", "signals", "generator_hints",
                                                "digital_source_type", "c2pa", "created")})
        except requests.RequestException as exc:
            entry.update({"ai_signal": "unknown", "signals": [], "error": str(exc)})
        entry["status"] = classify(entry, bool(page["page_notice"]))
        page["images"].append(entry)
    if len(candidates) > max_images:
        page["errors"].append(f"{len(candidates) - max_images} further images not scanned (max_images={max_images})")
    return page


def classify(entry: dict, has_page_notice: bool) -> str:
    sig, labelled = entry.get("ai_signal"), entry["label"]["labelled"]
    if sig == "unknown":
        return "not_scanned"
    if sig in ("strong", "medium"):
        if labelled:
            return "ai_marked_labelled"
        return "ai_marked_page_notice_only" if has_page_notice else "ai_marked_unlabelled"
    if labelled:
        return "labelled_no_marker"
    return "no_signal"


def scan(urls: list, max_images: int = 15, delay: float = 1.0, timeout: int = 30) -> dict:
    pages = [scan_page(u, max_images=max_images, delay=delay, timeout=timeout) for u in urls]
    images = [i for p in pages for i in p["images"]]
    count = lambda s: sum(1 for i in images if i["status"] == s)  # noqa: E731
    return {
        "pages": pages,
        "summary": {
            "pages_scanned": len(pages),
            "images_scanned": len(images),
            "ai_marked_labelled": count("ai_marked_labelled"),
            "ai_marked_page_notice_only": count("ai_marked_page_notice_only"),
            "ai_marked_unlabelled": count("ai_marked_unlabelled"),
            "labelled_no_marker": count("labelled_no_marker"),
            "no_signal": count("no_signal"),
            "not_scanned": count("not_scanned"),
            "chat_widgets": sorted({w for p in pages for w in p["chat_widgets"]}),
        },
        "limitations": [
            "Only embedded provenance metadata and visible labels are checked; many CMSs/CDNs strip metadata.",
            "'no_signal' does not mean the image is not AI-generated.",
            "Invisible watermarks (e.g. SynthID) and AI-written text are not detected.",
            "Whether an image is a 'deep fake' (Art. 3(60) AI Act) needs human/visual judgement.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan pages for AI-generated images and AI chat disclosure.")
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--max-images", type=int, default=15, help="images per page (default 15)")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(scan(args.urls, args.max_images, args.delay, args.timeout), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
