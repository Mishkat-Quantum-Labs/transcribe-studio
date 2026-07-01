"""Redirects from pre-project URL scheme."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.database import get_conn
from app.web.deps import get_recording_or_404

router = APIRouter()


@router.get("/recordings")
def legacy_recordings_list():
    return RedirectResponse("/", status_code=302)


@router.get("/upload")
def legacy_upload():
    conn = get_conn()
    row = conn.execute("SELECT id FROM projects ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if row:
        return RedirectResponse(f"/projects/{row['id']}/upload", status_code=302)
    return RedirectResponse("/projects/new", status_code=302)


@router.get("/recordings/{recording_id}")
def legacy_recording(recording_id: int):
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    project_id = rec.get("project_id")
    conn.close()
    if not project_id:
        raise HTTPException(404, "Recording has no project")
    return RedirectResponse(
        f"/projects/{project_id}/recordings/{recording_id}",
        status_code=301,
    )


@router.get("/recordings/{recording_id}/analysis")
def legacy_recording_analysis(recording_id: int):
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    project_id = rec.get("project_id")
    conn.close()
    if not project_id:
        raise HTTPException(404, "Recording has no project")
    return RedirectResponse(
        f"/projects/{project_id}/recordings/{recording_id}/analysis",
        status_code=301,
    )


@router.get("/recordings/{recording_id}/evaluation")
def legacy_recording_evaluation(recording_id: int):
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    project_id = rec.get("project_id")
    conn.close()
    if not project_id:
        raise HTTPException(404, "Recording has no project")
    return RedirectResponse(
        f"/projects/{project_id}/recordings/{recording_id}/evaluation",
        status_code=301,
    )