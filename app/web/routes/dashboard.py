from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.database import get_conn
from app.services.projects import dashboard_overview
from app.web.context import TEMPLATES, page_ctx

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = get_conn()
    overview = dashboard_overview(conn)
    conn.close()
    totals = {
        "project_count": overview["project_count"],
        "recording_count": overview["recording_count"],
        "total_duration_ms": overview["total_duration_ms"],
        "segment_count": overview["segment_count"],
        "transcript_pct": overview["transcript_pct"],
    }
    projects = overview["projects"]
    return TEMPLATES.TemplateResponse(
        request,
        "screens/dashboard.html",
        page_ctx(
            request,
            "dashboard",
            [{"label": "Dashboard", "url": None}],
            projects=projects,
            totals=totals,
        ),
    )