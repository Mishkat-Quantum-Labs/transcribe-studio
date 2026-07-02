import sys
from unittest.mock import MagicMock, patch

from app.services.supabase_schema import (
    SUPABASE_TABLES,
    ensure_supabase_tables,
    missing_supabase_tables,
    setup_supabase,
    supabase_table_exists,
)


def test_supabase_table_exists_true_on_200():
    resp = MagicMock()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        assert supabase_table_exists("https://x.supabase.co", "key", "projects") is True


def test_supabase_table_exists_false_on_pgrst205():
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://x",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=MagicMock(read=MagicMock(return_value=b'{"code":"PGRST205"}')),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        assert supabase_table_exists("https://x.supabase.co", "key", "projects") is False


def test_missing_supabase_tables():
    with patch(
        "app.services.supabase_schema.supabase_table_exists",
        side_effect=lambda _u, _k, t: t == "projects",
    ):
        assert missing_supabase_tables("https://x.supabase.co", "key") == [
            "recordings",
            "segments",
        ]


def test_setup_supabase_ready_when_tables_exist():
    with patch(
        "app.services.supabase_schema.missing_supabase_tables",
        return_value=[],
    ):
        result = setup_supabase("https://x.supabase.co", "anon", "postgresql://localhost/db")
    assert result["ok"] is True
    assert result["created"] is False
    assert result["tables"] == list(SUPABASE_TABLES)


def test_setup_supabase_requires_db_url_to_create():
    with patch(
        "app.services.supabase_schema.missing_supabase_tables",
        return_value=["projects"],
    ):
        result = setup_supabase("https://x.supabase.co", "anon", "")
    assert result["ok"] is False
    assert "Database URL" in result["message"]


def test_ensure_supabase_tables_runs_sql():
    with (
        patch.dict(sys.modules, {"psycopg": MagicMock()}),
        patch("app.services.supabase_schema._run_sql") as mock_run,
    ):
        result = ensure_supabase_tables("postgresql://postgres:pw@localhost/postgres")

    assert result["ok"] is True
    assert mock_run.call_count >= 3


def test_setup_supabase_creates_then_verifies():
    with (
        patch(
            "app.services.supabase_schema.missing_supabase_tables",
            side_effect=[["projects"], []],
        ),
        patch(
            "app.services.supabase_schema.ensure_supabase_tables",
            return_value={"ok": True, "message": "created"},
        ),
    ):
        result = setup_supabase(
            "https://x.supabase.co",
            "anon",
            "postgresql://localhost/db",
        )
    assert result["ok"] is True
    assert result["created"] is True