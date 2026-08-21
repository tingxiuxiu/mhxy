import hashlib
import hmac
from typing import Optional

from ..config import settings


def _canonicalize(params: dict) -> str:
    keys = sorted(params.keys())
    parts = []
    for k in keys:
        if k.lower() in ("x-sign", "signature"):
            continue
        v = params[k]
        if v is None:
            continue
        parts.append(f"{k}={v}")
    return "&".join(parts)


def sign_request(params: dict, body: str = "", secret: Optional[str] = None) -> str:
    secret = secret or settings.REQUEST_SIGN_SECRET
    base = _canonicalize(params) + "&body=" + str(body or "")
    sig = hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
    return sig


def verify_request_signature(params: dict, body: str, signature: str, secret: Optional[str] = None) -> bool:
    expected = sign_request(params, body, secret)
    return hmac.compare_digest(expected, signature)
