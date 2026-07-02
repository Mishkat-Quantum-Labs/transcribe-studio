"""Create Transcribe Studio tables in a Supabase (PostgreSQL) project."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from app.services.secrets import redact_secrets

# Mirrors local SQLite schema (app/database.py) for cloud backup / sync.
SUPABASE_TABLES = ("projects", "recordings", "segments")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.projects (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.recordings (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES public.projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    duration_ms INTEGER,
    notes TEXT DEFAULT '',
    llm_transcript_file TEXT DEFAULT '',
    llm_transcript_lang TEXT DEFAULT 'en',
    llm_transcript_format TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.segments (
    id BIGSERIAL PRIMARY KEY,
    recording_id BIGINT NOT NULL REFERENCES public.recordings(id) ON DELETE CASCADE,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    speaker TEXT NOT NULL DEFAULT '',
    transcript TEXT NOT NULL DEFAULT '',
    llm_transcript TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

POST_SCHEMA_SQL = """
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
"""

RLS_POLICIES: list[tuple[str, str]] = [
    (
        "projects",
        """
        ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS ts_projects_all ON public.projects;
        CREATE POLICY ts_projects_all ON public.projects
            FOR ALL TO anon, authenticated, service_role
            USING (true) WITH CHECK (true);
        """,
    ),
    (
        "recordings",
        """
        ALTER TABLE public.recordings ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS ts_recordings_all ON public.recordings;
        CREATE POLICY ts_recordings_all ON public.recordings
            FOR ALL TO anon, authenticated, service_role
            USING (true) WITH CHECK (true);
        """,
    ),
    (
        "segments",
        """
        ALTER TABLE public.segments ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS ts_segments_all ON public.segments;
        CREATE POLICY ts_segments_all ON public.segments
            FOR ALL TO anon, authenticated, service_role
            USING (true) WITH CHECK (true);
        """,
    ),
]


def _rest_headers(anon_key: str) -> dict[str, str]:
    return {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
    }


def supabase_table_exists(url: str, anon_key: str, table: str) -> bool:
    """Return True if PostgREST can see the table."""
    url = url.strip().rstrip("/")
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}?select=id&limit=1",
        headers=_rest_headers(anon_key),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        if exc.code == 404 and (
            "PGRST205" in body
            or "does not exist" in body
            or "Could not find the table" in body
        ):
            return False
        # Table exists but may be empty or blocked; treat other codes as present.
        if exc.code in (401, 403):
            return False
        return exc.code != 404
    except urllib.error.URLError:
        return False


def missing_supabase_tables(url: str, anon_key: str) -> list[str]:
    return [
        table
        for table in SUPABASE_TABLES
        if not supabase_table_exists(url, anon_key, table)
    ]


def _run_sql(db_url: str, sql: str) -> None:
    import psycopg

    with psycopg.connect(db_url, connect_timeout=15) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)


def ensure_supabase_tables(db_url: str) -> dict[str, Any]:
    """Create tables, grants, and RLS policies in the user's Supabase database."""
    db_url = db_url.strip()
    if not db_url:
        return {
            "ok": False,
            "message": "Database URL is required to create tables in Supabase",
        }
    try:
        import psycopg  # noqa: F401
    except ImportError as exc:
        return {
            "ok": False,
            "message": "Install psycopg to create Supabase tables: pip install psycopg[binary]",
        }

    try:
        _run_sql(db_url, SCHEMA_SQL)
        _run_sql(db_url, POST_SCHEMA_SQL)
        for _, policy_sql in RLS_POLICIES:
            _run_sql(db_url, policy_sql)
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Failed to create Supabase tables: {redact_secrets(str(exc))}",
        }

    return {
        "ok": True,
        "message": "Supabase tables created (projects, recordings, segments)",
        "tables": list(SUPABASE_TABLES),
    }


def setup_supabase(
    url: str,
    anon_key: str,
    db_url: str = "",
    *,
    create_if_missing: bool = True,
) -> dict[str, Any]:
    """
    Verify REST access and ensure required tables exist.
    Creates tables via Database URL when they are missing.
    """
    url = url.strip().rstrip("/")
    anon_key = anon_key.strip()
    db_url = db_url.strip()

    if not url or not anon_key:
        return {"ok": False, "message": "URL and anon key are required"}

    missing = missing_supabase_tables(url, anon_key)
    if not missing:
        return {
            "ok": True,
            "message": "Connected — Supabase tables ready",
            "tables": list(SUPABASE_TABLES),
            "created": False,
        }

    if not create_if_missing:
        return {
            "ok": False,
            "message": f"Missing tables: {', '.join(missing)}. Add Database URL to create them.",
            "missing": missing,
        }

    if not db_url:
        return {
            "ok": False,
            "message": (
                f"Missing tables: {', '.join(missing)}. "
                "Add your Supabase Database URL (Project Settings → Database) and save again."
            ),
            "missing": missing,
        }

    created = ensure_supabase_tables(db_url)
    if not created.get("ok"):
        return created

    still_missing = missing_supabase_tables(url, anon_key)
    if still_missing:
        return {
            "ok": False,
            "message": (
                f"Tables were created but REST API still cannot see: {', '.join(still_missing)}. "
                "Wait a few seconds and test again, or check API schema exposure in Supabase."
            ),
            "missing": still_missing,
        }

    return {
        "ok": True,
        "message": created["message"],
        "tables": list(SUPABASE_TABLES),
        "created": True,
    }