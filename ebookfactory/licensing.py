"""Pro license check (Gumroad license keys).

Open-core model: the build pipeline (Markdown -> PDF, TOC, phone edition) is MIT and
always unlocked. Pro features (sampler, marketing assets, premium themes) run without a
key in *preview mode*: output is complete but carries a small "ebook-factory Pro preview"
watermark. A license key bought on Gumroad removes it.

How it works
- `ebookfactory activate <KEY>` checks the key once against Gumroad's license API
  (POST https://api.gumroad.com/v2/licenses/verify) and caches the result in
  ~/.config/ebookfactory/license.json.
- Every run re-checks online at most once a day. If the network is down, a key that
  verified within the last 30 days keeps working (offline grace).
- Refunded, disputed or chargebacked purchases are rejected.
- EBOOKFACTORY_KEY can be set instead of running `activate` (CI, Docker).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Gumroad product that sells the Pro license. Override with EBOOKFACTORY_GUMROAD_PRODUCT.
GUMROAD_PRODUCT_ID = os.environ.get("EBOOKFACTORY_GUMROAD_PRODUCT", "xlakcPhVf29S5hrrzOxZzA==")
VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"
RECHECK_SECONDS = 24 * 3600
GRACE_SECONDS = 30 * 24 * 3600
WATERMARK = "ebook-factory Pro preview"


def _config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ebookfactory"


def _cache_path() -> Path:
    return _config_dir() / "license.json"


def _load_cache() -> dict:
    try:
        return json.loads(_cache_path().read_text())
    except (OSError, ValueError):
        return {}


def _save_cache(data: dict) -> None:
    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    try:
        p.chmod(0o600)
    except OSError:
        pass


def verify_online(key: str, increment: bool = False, timeout: float = 8.0) -> tuple[bool, str]:
    """Ask Gumroad whether `key` is a valid, non-refunded license. Returns (ok, message).

    Raises OSError on network failure so callers can fall back to the offline grace period.
    """
    body = urllib.parse.urlencode({
        "product_id": GUMROAD_PRODUCT_ID,
        "license_key": key.strip(),
        "increment_uses_count": "true" if increment else "false",
    }).encode()
    req = urllib.request.Request(VERIFY_URL, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:  # Gumroad answers 404 for an unknown key
        try:
            data = json.loads(e.read().decode())
        except ValueError:
            return False, f"license server error ({e.code})"
    if not data.get("success"):
        return False, data.get("message", "invalid license key")
    purchase = data.get("purchase", {})
    for flag in ("refunded", "disputed", "chargebacked"):
        if purchase.get(flag):
            return False, f"license purchase was {flag}"
    return True, purchase.get("email", "ok")


def activate(key: str) -> tuple[bool, str]:
    ok, msg = verify_online(key, increment=True)
    if ok:
        _save_cache({"key": key.strip(), "verified_at": time.time()})
    return ok, msg


def current_key() -> str | None:
    return os.environ.get("EBOOKFACTORY_KEY") or _load_cache().get("key")


def is_pro() -> bool:
    key = current_key()
    if not key:
        return False
    cache = _load_cache()
    last = cache.get("verified_at", 0) if cache.get("key") == key else 0
    if time.time() - last < RECHECK_SECONDS:
        return True
    try:
        ok, _ = verify_online(key)
    except OSError:
        return time.time() - last < GRACE_SECONDS
    if ok:
        _save_cache({"key": key, "verified_at": time.time()})
    return ok
