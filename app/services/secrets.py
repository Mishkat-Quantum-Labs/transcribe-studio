"""Redact secrets from user-facing messages and logs."""

from __future__ import annotations

import re

# postgres://user:pass@host → postgres://***@host
_PG_URL = re.compile(
    r"(postgres(?:ql)?://)([^:@/\s]+)(?::([^@\s]*))?@",
    re.IGNORECASE,
)
# Bearer / apikey headers in debug strings
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE)
_APIKEY = re.compile(r"(apikey['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9._\-]+", re.IGNORECASE)
# JWT-shaped tokens
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def redact_secrets(text: str) -> str:
    """Remove passwords, keys, and tokens from error text before showing users."""
    if not text:
        return text
    out = _PG_URL.sub(r"\1***@", text)
    out = _BEARER.sub(r"\1***", out)
    out = _APIKEY.sub(r"\1***", out)
    out = _JWT.sub("***", out)
    return out