#!/usr/bin/env python3
"""
Detect the technologies and third-party services a web page uses.

Used by the geo-legal agent to cross-check the privacy policy
(Datenschutzerklärung) against what the site actually loads: analytics,
advertising pixels, tag managers, consent managers, web fonts, embeds,
payment providers, review widgets, chat tools, CDNs and the shop/CMS platform.

Two modes:
  static   (default) — one HTTP GET; inspects HTML, inline scripts and
                       response headers. No JavaScript is executed.
  browser  (--browser) — loads the page in headless Chromium via Playwright
                       WITHOUT interacting with any consent banner and records
                       every network request and cookie. Third-party requests
                       and cookies observed here happened *before consent*.

Usage:
    python3 tech_detector.py <url> [--browser] [--timeout SECONDS]

Prints JSON to stdout.
"""

import argparse
import json
import re
import sys
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

# ---------------------------------------------------------------------------
# Signature database
#
# hosts:    substrings matched against the hostname of every resource URL
# patterns: regexes matched against inline <script> content and the raw HTML
# consent:  "required"  — non-essential; needs prior consent (§25 TDDDG / ePrivacy)
#           "depends"   — consent need depends on configuration / purpose
#           "not_required" — typically strictly necessary or first-party
# third_country: vendor processes data outside the EU/EEA by default (US etc.)
# privacy_terms: words to look for in the privacy policy to see if it is covered
# ---------------------------------------------------------------------------
SIGNATURES = [
    # --- Analytics ---
    {"name": "Google Analytics", "category": "analytics", "vendor": "Google",
     "hosts": ["google-analytics.com", "analytics.google.com"],
     "patterns": [r"\bgtag\(\s*['\"]config['\"]\s*,\s*['\"]G-", r"\bga\(\s*['\"]create", r"\bUA-\d{4,}-\d+"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Google Analytics"]},
    {"name": "Google Tag Manager", "category": "tag-manager", "vendor": "Google",
     "hosts": ["googletagmanager.com"],
     "patterns": [r"\bGTM-[A-Z0-9]{4,}"],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["Tag Manager"]},
    {"name": "Matomo", "category": "analytics", "vendor": "Matomo / self-hosted",
     "hosts": ["matomo.cloud", "innocraft.cloud"],
     "patterns": [r"\b_paq\.push\(", r"matomo\.js", r"piwik\.js"],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Matomo", "Piwik"]},
    {"name": "etracker", "category": "analytics", "vendor": "etracker",
     "hosts": ["etracker.com", "etracker.de"],
     "patterns": [r"_etracker"],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["etracker"]},
    {"name": "Hotjar", "category": "analytics", "vendor": "Hotjar",
     "hosts": ["hotjar.com", "hotjar.io"],
     "patterns": [r"\bhjid\s*:", r"static\.hotjar\.com"],
     "consent": "required", "third_country": False,
     "privacy_terms": ["Hotjar"]},
    {"name": "Microsoft Clarity", "category": "analytics", "vendor": "Microsoft",
     "hosts": ["clarity.ms"],
     "patterns": [r"clarity\.ms/tag"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Clarity"]},
    {"name": "Plausible", "category": "analytics", "vendor": "Plausible",
     "hosts": ["plausible.io"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Plausible"]},
    # --- Advertising / pixels ---
    {"name": "Google Ads / Floodlight", "category": "advertising", "vendor": "Google",
     "hosts": ["googleadservices.com", "doubleclick.net", "googlesyndication.com"],
     "patterns": [r"\bAW-\d{6,}", r"\bDC-\d{6,}"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Google Ads", "Conversion", "DoubleClick"]},
    {"name": "Meta Pixel", "category": "advertising", "vendor": "Meta",
     "hosts": ["connect.facebook.net", "facebook.com/tr"],
     "patterns": [r"\bfbq\(\s*['\"]init"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Meta Pixel", "Facebook Pixel", "Facebook-Pixel"]},
    {"name": "TikTok Pixel", "category": "advertising", "vendor": "TikTok",
     "hosts": ["analytics.tiktok.com"],
     "patterns": [r"\bttq\.load\("],
     "consent": "required", "third_country": True,
     "privacy_terms": ["TikTok"]},
    {"name": "Pinterest Tag", "category": "advertising", "vendor": "Pinterest",
     "hosts": ["ct.pinterest.com", "s.pinimg.com"],
     "patterns": [r"\bpintrk\("],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Pinterest"]},
    {"name": "Microsoft Advertising UET", "category": "advertising", "vendor": "Microsoft",
     "hosts": ["bat.bing.com"],
     "patterns": [r"\buetq\b"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Microsoft Advertising", "Bing Ads", "UET"]},
    {"name": "LinkedIn Insight Tag", "category": "advertising", "vendor": "LinkedIn",
     "hosts": ["snap.licdn.com", "px.ads.linkedin.com"],
     "patterns": [r"_linkedin_partner_id"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["LinkedIn"]},
    {"name": "Criteo", "category": "advertising", "vendor": "Criteo",
     "hosts": ["criteo.com", "criteo.net"], "patterns": [],
     "consent": "required", "third_country": False,
     "privacy_terms": ["Criteo"]},
    # --- Consent management platforms ---
    {"name": "Usercentrics", "category": "consent", "vendor": "Usercentrics",
     "hosts": ["usercentrics.eu", "usercentrics.com"], "patterns": [r"usercentrics"],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["Usercentrics"]},
    {"name": "Cookiebot", "category": "consent", "vendor": "Usercentrics (Cookiebot)",
     "hosts": ["cookiebot.com", "consent.cookiebot.com"], "patterns": [r"Cookiebot"],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["Cookiebot"]},
    {"name": "OneTrust", "category": "consent", "vendor": "OneTrust",
     "hosts": ["onetrust.com", "cookielaw.org"], "patterns": [r"OptanonConsent|otSDKStub"],
     "consent": "not_required", "third_country": True,
     "privacy_terms": ["OneTrust"]},
    {"name": "Borlabs Cookie", "category": "consent", "vendor": "Borlabs",
     "hosts": [], "patterns": [r"borlabs-cookie|BorlabsCookie"],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["Borlabs"]},
    {"name": "CCM19", "category": "consent", "vendor": "Papoo Software",
     "hosts": ["ccm19.de"], "patterns": [r"ccm19"],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["CCM19"]},
    {"name": "consentmanager", "category": "consent", "vendor": "consentmanager",
     "hosts": ["consentmanager.net"], "patterns": [r"__cmp\("],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["consentmanager"]},
    {"name": "Shopware Cookie Consent", "category": "consent", "vendor": "Shopware (built-in)",
     "hosts": [], "patterns": [r"cookie-permission|data-cookie-permission"],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["Cookie"]},
    # --- Fonts / CDNs ---
    {"name": "Google Fonts (remote)", "category": "fonts", "vendor": "Google",
     "hosts": ["fonts.googleapis.com", "fonts.gstatic.com"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Google Fonts", "Google Web Fonts"]},
    {"name": "Adobe Fonts", "category": "fonts", "vendor": "Adobe",
     "hosts": ["use.typekit.net", "p.typekit.net"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Adobe Fonts", "Typekit"]},
    {"name": "Font Awesome CDN", "category": "fonts", "vendor": "Fonticons",
     "hosts": ["kit.fontawesome.com", "use.fontawesome.com"], "patterns": [],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["Font Awesome"]},
    {"name": "Cloudflare", "category": "cdn", "vendor": "Cloudflare",
     "hosts": ["cdnjs.cloudflare.com", "cloudflareinsights.com", "challenges.cloudflare.com"],
     "patterns": [], "consent": "depends", "third_country": True,
     "privacy_terms": ["Cloudflare"]},
    {"name": "jsDelivr", "category": "cdn", "vendor": "jsDelivr",
     "hosts": ["cdn.jsdelivr.net"], "patterns": [],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["jsDelivr"]},
    {"name": "unpkg", "category": "cdn", "vendor": "unpkg",
     "hosts": ["unpkg.com"], "patterns": [],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["unpkg"]},
    # --- Embeds / maps / video ---
    {"name": "YouTube", "category": "video", "vendor": "Google",
     "hosts": ["youtube.com", "youtube-nocookie.com", "ytimg.com"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["YouTube"]},
    {"name": "Vimeo", "category": "video", "vendor": "Vimeo",
     "hosts": ["player.vimeo.com", "vimeocdn.com"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Vimeo"]},
    {"name": "Google Maps", "category": "maps", "vendor": "Google",
     "hosts": ["maps.googleapis.com", "maps.google.com", "google.com/maps"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Google Maps"]},
    {"name": "OpenStreetMap", "category": "maps", "vendor": "OSM Foundation",
     "hosts": ["openstreetmap.org", "tile.openstreetmap.org"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["OpenStreetMap"]},
    {"name": "Instagram embed", "category": "social", "vendor": "Meta",
     "hosts": ["instagram.com/embed", "cdninstagram.com"], "patterns": [r"instagram-media"],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Instagram"]},
    # --- Captcha / security ---
    {"name": "Google reCAPTCHA", "category": "captcha", "vendor": "Google",
     "hosts": ["google.com/recaptcha", "recaptcha.net", "gstatic.com/recaptcha"],
     "patterns": [r"g-recaptcha|grecaptcha"],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["reCAPTCHA"]},
    {"name": "hCaptcha", "category": "captcha", "vendor": "Intuition Machines",
     "hosts": ["hcaptcha.com"], "patterns": [r"h-captcha"],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["hCaptcha"]},
    {"name": "Friendly Captcha", "category": "captcha", "vendor": "Friendly Captcha",
     "hosts": ["friendlycaptcha.com", "frcapi.com"], "patterns": [r"frc-captcha"],
     "consent": "not_required", "third_country": False,
     "privacy_terms": ["Friendly Captcha"]},
    # --- Payment ---
    {"name": "PayPal", "category": "payment", "vendor": "PayPal",
     "hosts": ["paypal.com", "paypalobjects.com"], "patterns": [r"paypal\.Buttons\(|paypal-sdk"],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["PayPal"]},
    {"name": "Stripe", "category": "payment", "vendor": "Stripe",
     "hosts": ["js.stripe.com", "stripe.network"], "patterns": [],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["Stripe"]},
    {"name": "Klarna", "category": "payment", "vendor": "Klarna",
     "hosts": ["klarna.com", "klarnacdn.net", "klarnaservices.com"], "patterns": [r"Klarna\.Payments|klarna-placement"],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Klarna"]},
    {"name": "Amazon Pay", "category": "payment", "vendor": "Amazon",
     "hosts": ["payments.amazon", "amazonpay"], "patterns": [r"amazon\.Pay\.renderButton"],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["Amazon Pay"]},
    {"name": "Mollie", "category": "payment", "vendor": "Mollie",
     "hosts": ["mollie.com"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Mollie"]},
    {"name": "Unzer", "category": "payment", "vendor": "Unzer",
     "hosts": ["unzer.com", "heidelpay.com"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Unzer", "Heidelpay"]},
    # --- Reviews / trust ---
    {"name": "Trusted Shops", "category": "reviews", "vendor": "Trusted Shops",
     "hosts": ["trustedshops.com", "trustedshops.de", "etrusted.com", "trustbadge"],
     "patterns": [r"trustbadge|etrusted"],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Trusted Shops", "Trustbadge"]},
    {"name": "Trustpilot", "category": "reviews", "vendor": "Trustpilot",
     "hosts": ["trustpilot.com"], "patterns": [r"trustpilot-widget"],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Trustpilot"]},
    {"name": "ProvenExpert", "category": "reviews", "vendor": "ProvenExpert",
     "hosts": ["provenexpert.com", "provenexpert.net"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["ProvenExpert"]},
    # --- Chat / support / newsletter ---
    {"name": "Zendesk", "category": "chat", "vendor": "Zendesk",
     "hosts": ["zdassets.com", "zendesk.com"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Zendesk"]},
    {"name": "Intercom", "category": "chat", "vendor": "Intercom",
     "hosts": ["intercom.io", "intercomcdn.com"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Intercom"]},
    {"name": "Tawk.to", "category": "chat", "vendor": "tawk.to",
     "hosts": ["tawk.to"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["tawk"]},
    {"name": "Mailchimp", "category": "newsletter", "vendor": "Intuit Mailchimp",
     "hosts": ["list-manage.com", "chimpstatic.com", "mailchimp.com"], "patterns": [],
     "consent": "depends", "third_country": True,
     "privacy_terms": ["Mailchimp"]},
    {"name": "Brevo (Sendinblue)", "category": "newsletter", "vendor": "Brevo",
     "hosts": ["sibforms.com", "sendinblue.com", "brevo.com"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["Brevo", "Sendinblue"]},
    {"name": "CleverReach", "category": "newsletter", "vendor": "CleverReach",
     "hosts": ["cleverreach.com"], "patterns": [],
     "consent": "depends", "third_country": False,
     "privacy_terms": ["CleverReach"]},
    {"name": "Klaviyo", "category": "newsletter", "vendor": "Klaviyo",
     "hosts": ["klaviyo.com"], "patterns": [],
     "consent": "required", "third_country": True,
     "privacy_terms": ["Klaviyo"]},
]

# CMS / shop platform fingerprints (first-party; listed for context, not consent)
PLATFORMS = [
    ("Shopware 6", [r"sw-language-id|sw-currency-id|sw-context-token", r"/bundles/storefront/"]),
    ("Shopware 5", [r"/themes/Frontend/|shopware\.php|sw5"]),
    ("Shopify", [r"cdn\.shopify\.com|Shopify\.theme"]),
    ("WooCommerce", [r"woocommerce"]),
    ("WordPress", [r"/wp-content/|/wp-includes/"]),
    ("Magento", [r"Magento_|mage/cookies"]),
    ("JTL-Shop", [r"jtl-shop|JTL-Shop"]),
    ("Wix", [r"static\.wixstatic\.com|wix-code"]),
    ("Squarespace", [r"squarespace\.com|static1\.squarespace"]),
    ("TYPO3", [r"typo3conf|typo3temp"]),
    ("Webflow", [r"webflow\.js|data-wf-site"]),
]

# Cookie names that are strictly first-party/technical in common platforms.
TECHNICAL_COOKIE_PATTERNS = [
    r"^session", r"^PHPSESSID$", r"^sw-", r"^XSRF|^csrf", r"^cookie-preference",
    r"^wordpress_|^wp-", r"^_shopify_s$", r"^cf_|^__cf", r"^timezone$",
]


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _registrable(host: str) -> str:
    """Rough eTLD+1 (good enough for first- vs third-party classification)."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "gv", "ac"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_third_party(resource_url: str, page_url: str) -> bool:
    rh, ph = _host(resource_url), _host(page_url)
    if not rh:
        return False
    return _registrable(rh) != _registrable(ph)


def collect_resource_urls(html: str, base_url: str) -> list:
    """All external resource URLs referenced by the HTML (scripts, styles, frames, images, preconnects)."""
    soup = BeautifulSoup(html, "lxml")
    urls = []
    for tag, attr in (("script", "src"), ("link", "href"), ("iframe", "src"),
                      ("img", "src"), ("source", "src"), ("embed", "src"),
                      ("iframe", "data-src"), ("script", "data-src")):
        for el in soup.find_all(tag):
            val = el.get(attr)
            if val and not val.startswith(("data:", "javascript:", "#")):
                urls.append(urljoin(base_url, val.strip()))
    return urls


def inline_script_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return "\n".join(s.get_text() for s in soup.find_all("script") if not s.get("src"))


def match_signatures(resource_urls: list, html: str, inline_js: str) -> list:
    """Return detected technologies with evidence."""
    found = {}
    lowered = [(u, u.lower()) for u in resource_urls]
    for sig in SIGNATURES:
        evidence = []
        for host in sig["hosts"]:
            for orig, low in lowered:
                if host in low:
                    evidence.append(f"resource: {orig}")
                    break
        for pat in sig["patterns"]:
            m = re.search(pat, inline_js, re.I) or re.search(pat, html, re.I)
            if m:
                evidence.append(f"code: {m.group(0)[:80]}")
        if evidence:
            found[sig["name"]] = {
                "name": sig["name"],
                "category": sig["category"],
                "vendor": sig["vendor"],
                "consent": sig["consent"],
                "third_country": sig["third_country"],
                "privacy_terms": sig["privacy_terms"],
                "evidence": sorted(set(evidence))[:5],
            }
    return list(found.values())


def detect_platform(html: str, headers: dict) -> list:
    blob = html + "\n" + "\n".join(f"{k}: {v}" for k, v in headers.items())
    platforms = []
    for name, pats in PLATFORMS:
        if any(re.search(p, blob, re.I) for p in pats):
            platforms.append(name)
    soup = BeautifulSoup(html, "lxml")
    gen = soup.find("meta", attrs={"name": "generator"})
    if gen and gen.get("content"):
        platforms.append(f"generator: {gen['content'].strip()}")
    return platforms


def classify_cookie(name: str) -> str:
    return "technical" if any(re.search(p, name, re.I) for p in TECHNICAL_COOKIE_PATTERNS) else "unknown"


def static_scan(url: str, timeout: int = 30) -> dict:
    result = {
        "url": url, "mode": "static", "final_url": None, "status_code": None,
        "server": None, "platforms": [], "technologies": [],
        "third_party_hosts": [], "cookies_set_by_server": [], "errors": [],
    }
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        result["errors"].append(f"fetch failed: {exc}")
        return result

    result["final_url"] = resp.url
    result["status_code"] = resp.status_code
    headers = dict(resp.headers or {})
    result["server"] = headers.get("Server") or headers.get("server")
    html = resp.text or ""

    resources = collect_resource_urls(html, resp.url)
    inline_js = inline_script_text(html)
    result["technologies"] = match_signatures(resources, html, inline_js)
    result["platforms"] = detect_platform(html, headers)
    result["third_party_hosts"] = sorted({_host(u) for u in resources if is_third_party(u, resp.url)})

    raw_cookies = []
    raw = getattr(resp, "raw", None)
    if raw is not None and hasattr(raw, "headers") and hasattr(raw.headers, "getlist"):
        raw_cookies = raw.headers.getlist("Set-Cookie")
    elif headers.get("Set-Cookie"):
        raw_cookies = [headers["Set-Cookie"]]
    for c in raw_cookies:
        name = c.split("=", 1)[0].strip()
        result["cookies_set_by_server"].append({"name": name, "class": classify_cookie(name)})
    return result


def browser_scan(url: str, timeout: int = 30) -> dict:
    """Load the page in headless Chromium without consenting; record requests and cookies."""
    out = {"available": False, "third_party_requests": [], "cookies": [],
           "local_storage_keys": [], "technologies_before_consent": [], "errors": []}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        out["errors"].append("playwright not installed; run: python3 -m playwright install chromium")
        return out

    requests_seen = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(locale="de-DE", user_agent=DEFAULT_HEADERS["User-Agent"])
            page = ctx.new_page()
            page.on("request", lambda r: requests_seen.append(r.url))
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            page.wait_for_timeout(2000)  # let deferred tags fire
            final_url = page.url
            out["cookies"] = [
                {"name": c["name"], "domain": c["domain"],
                 "third_party": is_third_party("https://" + c["domain"].lstrip("."), final_url),
                 "class": classify_cookie(c["name"]),
                 "session": c.get("expires", -1) in (-1, None)}
                for c in ctx.cookies()
            ]
            try:
                out["local_storage_keys"] = page.evaluate("Object.keys(window.localStorage)")
            except Exception:  # noqa: BLE001 — storage may be blocked
                pass
            html = page.content()
            browser.close()
    except Exception as exc:  # noqa: BLE001 — report any browser failure as data
        out["errors"].append(f"browser scan failed: {exc}")
        return out

    out["available"] = True
    third = [u for u in requests_seen if is_third_party(u, final_url)]
    out["third_party_requests"] = sorted({_host(u) for u in third})
    techs = match_signatures(third, "", "")
    # Only network evidence counts as "fired before consent" (code presence alone does not).
    out["technologies_before_consent"] = [
        {"name": t["name"], "category": t["category"], "consent": t["consent"], "evidence": t["evidence"]}
        for t in techs
    ]
    out["rendered_html_technologies"] = [t["name"] for t in match_signatures(
        collect_resource_urls(html, final_url), html, inline_script_text(html))]
    return out


def detect(url: str, browser: bool = False, timeout: int = 30) -> dict:
    result = static_scan(url, timeout=timeout)
    if browser:
        result["mode"] = "static+browser"
        result["pre_consent"] = browser_scan(result["final_url"] or url, timeout=timeout)
        violations = [t for t in result["pre_consent"].get("technologies_before_consent", [])
                      if t["consent"] == "required"]
        result["pre_consent"]["consent_required_fired_before_consent"] = violations
    result["consent_manager"] = [t["name"] for t in result["technologies"] if t["category"] == "consent"]
    result["summary"] = {
        "technology_count": len(result["technologies"]),
        "consent_required": sorted(t["name"] for t in result["technologies"] if t["consent"] == "required"),
        "third_country_vendors": sorted({t["vendor"] for t in result["technologies"] if t["third_country"]}),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect technologies and third-party services on a page.")
    parser.add_argument("url")
    parser.add_argument("--browser", action="store_true",
                        help="also load the page in headless Chromium (no consent) and record requests/cookies")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(detect(args.url, browser=args.browser, timeout=args.timeout), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
