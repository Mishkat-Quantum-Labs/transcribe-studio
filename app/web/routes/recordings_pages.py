"""Recording workspace screens under a project."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.analytics import analyze_recording
from app.database import get_conn
from app.navigation import evaluation_context_stats, get_recording_with_project
from app.web.context import TEMPLATES, page_ctx, recording_breadcrumbs
from app.web.deps import get_recording_in_project_or_404, recording_segments

router = APIRouter()


@router.get(
    "/projects/{project_id}/recordings/{recording_id}",
    response_class=HTMLResponse,
)
def editor(request: Request, project_id: int, recording_id: int):
    conn = get_conn()
    rec = get_recording_in_project_or_404(conn, project_id, recording_id)
    rec = get_recording_with_project(conn, recording_id) or rec
    conn.close()
    return TEMPLATES.TemplateResponse(
        request,
        "editor.html",
        page_ctx(
            request,
            "editor",
            recording_breadcrumbs(rec),
            project={"id": project_id, "name": rec.get("project_name", "")},
            recording=rec,
            recording_tab="editor",
        ),
    )


@router.get(
    "/projects/{project_id}/recordings/{recording_id}/analysis",
    response_class=HTMLResponse,
)
def recording_analysis(request: Request, project_id: int, recording_id: int):
    conn = get_conn()
    rec = get_recording_in_project_or_404(conn, project_id, recording_id)
    rec = get_recording_with_project(conn, recording_id) or rec
    segs = recording_segments(conn, recording_id)
    conn.close()
    analysis = analyze_recording(rec, segs)
    return TEMPLATES.TemplateResponse(
        request,
        "analysis.html",
        page_ctx(
            request,
            "analysis",
            recording_breadcrumbs(rec) + [{"label": "Analysis", "url": None}],
            project={"id": project_id, "name": rec.get("project_name", "")},
            recording=rec,
            recording_tab="analysis",
            analysis=analysis,
        ),
    )


@router.get(
    "/projects/{project_id}/recordings/{recording_id}/evaluation",
    response_class=HTMLResponse,
)
def evaluation_page(request: Request, project_id: int, recording_id: int):
    conn = get_conn()
    rec = get_recording_in_project_or_404(conn, project_id, recording_id)
    rec = get_recording_with_project(conn, recording_id) or rec
    eval_ctx = evaluation_context_stats(conn, recording_id)
    conn.close()
    return TEMPLATES.TemplateResponse(
        request,
        "evaluation.html",
        page_ctx(
            request,
            "evaluation",
            recording_breadcrumbs(rec) + [{"label": "Evaluation", "url": None}],
            project={"id": project_id, "name": rec.get("project_name", "")},
            recording=rec,
            recording_tab="evaluation",
            eval_ctx=eval_ctx,
        ),
    )