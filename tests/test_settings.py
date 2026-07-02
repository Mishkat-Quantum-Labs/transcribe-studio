from fastapi.testclient import TestClient

from app.database import get_conn, init_db, migrate_app_settings
from app.main import app
from app.services.settings import (
    get_supabase_settings,
    save_supabase_settings,
    supabase_public_view,
    check_supabase_connection,
)


def test_supabase_settings_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRIBE_STUDIO_DATA", str(tmp_path))
    migrate_app_settings()
    conn = get_conn()
    save_supabase_settings(
        conn,
        url="https://abc.supabase.co",
        anon_key="test-anon-key",
        db_url="postgresql://localhost/db",
    )
    raw = get_supabase_settings(conn)
    conn.close()
    assert raw["supabase_url"] == "https://abc.supabase.co"
    view = supabase_public_view(raw)
    assert view["configured"] is True
    assert view["supabase_anon_key_set"] is True
    assert "supabase_anon_key" not in view


def test_settings_page_and_api_routes(tmp_path, monkeypatch):
    import app.database as db

    monkeypatch.setenv("TRANSCRIBE_STUDIO_DATA", str(tmp_path))
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "transcribe.db")
    init_db()
    migrate_app_settings()
    client = TestClient(app)

    page = client.get("/settings")
    assert page.status_code == 200
    assert "Supabase" in page.text

    api = client.get("/api/settings/supabase")
    assert api.status_code == 200
    assert api.json()["configured"] is False

    monkeypatch.setattr(
        "app.main.setup_supabase",
        lambda url, key, db_url, **kwargs: {
            "ok": True,
            "message": "ready",
            "tables": ["projects", "recordings", "segments"],
            "created": False,
        },
    )
    saved = client.patch(
        "/api/settings/supabase",
        json={
            "supabase_url": "https://abc.supabase.co",
            "supabase_anon_key": "test-anon-key",
            "supabase_db_url": "postgresql://localhost/db",
        },
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["configured"] is True
    assert body["supabase_setup"]["ok"] is True

    merged = client.post(
        "/api/settings/supabase/test",
        json={"supabase_url": "", "supabase_anon_key": "", "supabase_db_url": ""},
    )
    assert merged.status_code == 200
    assert merged.json()["ok"] is True


def test_connection_requires_url_and_key():
    assert check_supabase_connection("", "")["ok"] is False