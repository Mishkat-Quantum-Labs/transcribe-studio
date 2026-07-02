"""Settings screens."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.database import get_conn
from app.services.settings import get_supabase_settings, supabase_public_view
from app.web.context import TEMPLATES, page_ctx

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    conn = get_conn()
    raw = get_supabase_settings(conn)
    conn.close()
    return TEMPLATES.TemplateResponse(
        request,
        "screens/settings.html",
        page_ctx(
            request,
            "settings",
            [
                {"label": "Dashboard", "url": "/"},
                {"label": "Settings", "url": None},
            ],
            supabase=supabase_public_view(raw),
        ),
    )