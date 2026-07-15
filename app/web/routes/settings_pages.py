"""Settings screens."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.database import get_conn
from app.services.settings import get_supabase_settings, supabase_public_view
from app.services import s3 as s3_service
from app.web.context import TEMPLATES, page_ctx

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    conn = get_conn()
    raw = get_supabase_settings(conn)
    conn.close()

    s3_configured = s3_service.is_s3_configured()
    s3_status = s3_service.check_connection() if s3_configured else {"ok": False, "message": "Not configured"}

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
            s3={
                "configured": s3_configured,
                "ok": s3_status.get("ok", False),
                "bucket": s3_status.get("bucket", ""),
                "region": s3_status.get("region", ""),
                "message": s3_status.get("message", ""),
            },
        ),
    )