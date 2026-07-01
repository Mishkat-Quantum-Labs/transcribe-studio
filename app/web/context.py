"""Template engine and page context builder."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.analytics import fmt_duration
from app.database import get_conn
from app.navigation import get_recording_with_project, sidebar_tree
from app.paths import TEMPLATES_DIR
from app.services.projects import get_project_or_404

TEMPLATES = Jinja2Templates(directory=TEMPLATES_DIR)
TEMPLATES.env.globals["fmt_duration"] = fmt_duration


def recording_url(
    project_id: int,
    recording_id: int,
    view: str = "editor",
) -> str:
    base = f"/projects/{project_id}/recordings/{recording_id}"
    if view == "analysis":
        return f"{base}/analysis"
    if view == "evaluation":
        return f"{base}/evaluation"
    return base


TEMPLATES.env.globals["recording_url"] = recording_url


def page_ctx(
    request: Request,
    nav_active: str,
    breadcrumbs: list[dict[str, str | None]] | None = None,
    *,
    project: dict | None = None,
    recording: dict | None = None,
    recording_tab: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    conn = get_conn()
    tree = sidebar_tree(conn)

    if project and project.get("id") and "recording_count" not in project:
        project = get_project_or_404(conn, project["id"])

    if recording and recording.get("id"):
        recording = get_recording_with_project(conn, recording["id"]) or recording
        if not project and recording.get("project_id"):
            project = get_project_or_404(conn, recording["project_id"])

    conn.close()
    return {
        "request": request,
        "nav_active": nav_active,
        "breadcrumbs": breadcrumbs or [],
        "project": project,
        "recording": recording,
        "recording_tab": recording_tab,
        "sidebar_tree": tree,
        **extra,
    }


def project_breadcrumbs(project: dict, leaf: str | None = None) -> list[dict[str, str | None]]:
    crumbs = [
        {"label": "Dashboard", "url": "/"},
        {"label": project["name"], "url": f"/projects/{project['id']}"},
    ]
    if leaf:
        crumbs.append({"label": leaf, "url": None})
    return crumbs


def recording_breadcrumbs(rec: dict) -> list[dict[str, str | None]]:
    pid = rec.get("project_id")
    pname = rec.get("project_name")
    crumbs: list[dict[str, str | None]] = [{"label": "Dashboard", "url": "/"}]
    if pid and pname:
        crumbs.append({"label": pname, "url": f"/projects/{pid}"})
    crumbs.append({"label": rec["title"], "url": None})
    return crumbs