from __future__ import annotations

import hashlib
import hmac
import json

from .keys import KEYS


def sign(secret: str, body: dict) -> str:
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify(api_key: str, signature: str, body: dict) -> tuple[bool, str, dict | None]:
    rec = KEYS.get(api_key)
    if not rec:
        return False, "unknown_api_key", None
    expected = sign(rec["secret"], body)
    if not hmac.compare_digest(expected, signature or ""):
        return False, "bad_hmac", rec
    return True, "ok", rec
