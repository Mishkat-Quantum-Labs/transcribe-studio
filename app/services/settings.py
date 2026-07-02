"""App-wide settings (Supabase integration, etc.)."""

from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from typing import Any

SUPABASE_KEYS = ("supabase_url", "supabase_anon_key", "supabase_db_url")


def _ensure_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    _ensure_settings_table(conn)
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    _ensure_settings_table(conn)
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = datetime('now')
        """,
        (key, value.strip()),
    )
    conn.commit()


def get_supabase_settings(conn: sqlite3.Connection) -> dict[str, str]:
    return {k: get_setting(conn, k) for k in SUPABASE_KEYS}


def save_supabase_settings(
    conn: sqlite3.Connection,
    *,
    url: str,
    anon_key: str,
    db_url: str = "",
) -> dict[str, str]:
    url = url.strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        raise ValueError("Supabase URL must start with http:// or https://")

    set_setting(conn, "supabase_url", url)
    set_setting(conn, "supabase_anon_key", anon_key.strip())
    set_setting(conn, "supabase_db_url", db_url.strip())
    return get_supabase_settings(conn)


def supabase_public_view(settings: dict[str, str]) -> dict[str, Any]:
    """Mask secrets for API/UI display — never expose keys or DB passwords."""
    url = settings.get("supabase_url", "")
    anon = settings.get("supabase_anon_key", "")
    db_url = settings.get("supabase_db_url", "")
    return {
        "configured": bool(url and anon),
        "supabase_url": url,
        "supabase_anon_key_set": bool(anon),
        "supabase_db_url_set": bool(db_url),
    }


def check_supabase_connection(url: str, anon_key: str) -> dict[str, Any]:
    """Ping Supabase REST API with the anon key."""
    url = url.strip().rstrip("/")
    anon_key = anon_key.strip()
    if not url or not anon_key:
        return {"ok": False, "message": "URL and anon key are required"}

    req = urllib.request.Request(
        f"{url}/rest/v1/",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "message": "Connected to Supabase REST API",
            }
    except urllib.error.HTTPError as exc:
        # 401/404 still proves the project URL is reachable
        if exc.code in (401, 404):
            return {
                "ok": True,
                "status": exc.code,
                "message": "Supabase project reachable (verify anon key in dashboard)",
            }
        return {"ok": False, "status": exc.code, "message": str(exc.reason)}
    except urllib.error.URLError as exc:
        return {"ok": False, "message": str(exc.reason)}