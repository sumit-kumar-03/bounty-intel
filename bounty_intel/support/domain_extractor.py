import ipaddress
from urllib.parse import urlsplit

import tldextract

_extractor = tldextract.TLDExtract(suffix_list_urls=())

_SKIP_BUGCROWD_CATEGORIES = {"android", "ios", "hardware"}
_SKIP_HACKERONE_ASSET_TYPES = {
    "SOURCE_CODE",
    "GOOGLE_PLAY_APP_ID",
    "OTHER_APK",
    "APPLE_STORE_APP_ID",
    "OTHER_IPA",
    "TESTFLIGHT",
    "WINDOWS_APP_STORE_APP_ID",
    "DOWNLOADABLE_EXECUTABLES",
    "SMART_CONTRACT",
    "AI_MODEL",
    "HARDWARE",
    "CIDR",
    "IP_ADDRESS",
}


def extract_registrable_domain(
    identifier: str, asset_type: str | None, platform: str
) -> str | None:
    """Extract a registrable parent domain (e.g. "example.com" or
    "example.co.uk") from a scope target identifier, or None if it isn't
    a domain-shaped identifier (IP/CIDR, mobile app ID, free text, etc.)."""
    if not identifier or not identifier.strip():
        return None
    if platform == "bugcrowd" and asset_type in _SKIP_BUGCROWD_CATEGORIES:
        return None
    if platform == "hackerone" and asset_type in _SKIP_HACKERONE_ASSET_TYPES:
        return None

    try:
        s = identifier.strip()
        # "//" trick: forces urlsplit to parse a bare "host[:port][/path]"
        # as netloc instead of path, same as it would for a real URL.
        parsed = urlsplit(s if "://" in s else "//" + s)
        host = parsed.hostname
        if not host:
            return None

        try:
            ipaddress.ip_address(host)
            return None
        except ValueError:
            pass

        result = _extractor(host)
        if not result.domain or not result.suffix:
            return None
        return f"{result.domain}.{result.suffix}".lower()
    except Exception:
        return None
