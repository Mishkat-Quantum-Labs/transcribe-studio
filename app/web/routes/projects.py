"""Project screens: detail, create, settings, upload."""

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.database import get_conn
from app.services.projects import (
    create_project,
    delete_project,
    get_project_or_404,
    project_stats,
    update_project,
)
from app.web.context import TEMPLATES, page_ctx, project_breadcrumbs

router = APIRouter()


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


@router.get("/projects/new", response_class=HTMLResponse)
def project_new_page(request: Request):
    return TEMPLATES.TemplateResponse(
        request,
        "screens/project_form.html",
        page_ctx(
            request,
            "project_new",
            [
                {"label": "Dashboard", "url": "/"},
                {"label": "New project", "url": None},
            ],
            form_mode="create",
            project={"name": "", "description": ""},
        ),
    )


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: int):
    conn = get_conn()
    stats = project_stats(conn, project_id)
    conn.close()
    return TEMPLATES.TemplateResponse(
        request,
        "screens/project_detail.html",
        page_ctx(
            request,
            "project",
            project_breadcrumbs(stats),
            project=stats,
        ),
    )


@router.get("/projects/{project_id}/settings", response_class=HTMLResponse)
def project_settings_page(request: Request, project_id: int):
    conn = get_conn()
    project = get_project_or_404(conn, project_id)
    conn.close()
    return TEMPLATES.TemplateResponse(
        request,
        "screens/project_form.html",
        page_ctx(
            request,
            "project_settings",
            project_breadcrumbs(project, "Settings"),
            form_mode="edit",
            project=project,
        ),
    )


@router.get("/projects/{project_id}/upload", response_class=HTMLResponse)
def project_upload_page(request: Request, project_id: int):
    conn = get_conn()
    project = get_project_or_404(conn, project_id)
    conn.close()
    return TEMPLATES.TemplateResponse(
        request,
        "screens/project_upload.html",
        page_ctx(
            request,
            "upload",
            project_breadcrumbs(project, "Upload"),
            project=project,
        ),
    )


@router.post("/api/projects")
def api_create_project(body: ProjectIn):
    conn = get_conn()
    project = create_project(conn, body.name, body.description)
    conn.close()
    return {"ok": True, "project": project}


@router.patch("/api/projects/{project_id}")
def api_update_project(project_id: int, body: ProjectIn):
    conn = get_conn()
    project = update_project(conn, project_id, body.name, body.description)
    conn.close()
    return {"ok": True, "project": project}


@router.delete("/api/projects/{project_id}")
def api_delete_project(project_id: int):
    conn = get_conn()
    delete_project(conn, project_id)
    conn.close()
    return {"ok": True}