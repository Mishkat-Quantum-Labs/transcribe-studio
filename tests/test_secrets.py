from app.services.secrets import redact_secrets
from app.services.settings import supabase_public_view


def test_redact_postgres_url():
    raw = "connect postgresql://postgres:SECRET@db.x.supabase.co:5432/postgres failed"
    out = redact_secrets(raw)
    assert "SECRET" not in out
    assert "postgresql://***@" in out


def test_redact_jwt():
    token = "eyJhbGciOiJIUzI1NiJ9.abc.def"
    assert token not in redact_secrets(f"key={token}")


def test_public_view_never_exposes_secrets():
    view = supabase_public_view(
        {
            "supabase_url": "https://x.supabase.co",
            "supabase_anon_key": "super-secret-anon-key",
            "supabase_db_url": "postgresql://u:p@host/db",
        }
    )
    assert "super-secret" not in str(view)
    assert "supabase_anon_key" not in view
    assert "supabase_db_url" not in view
    assert view["supabase_anon_key_set"] is True
    assert view["supabase_db_url_set"] is True