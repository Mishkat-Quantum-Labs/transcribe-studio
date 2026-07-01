"""Shared route dependencies and data access helpers."""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from app.services.projects import get_project_or_404


def get_recording_or_404(conn: sqlite3.Connection, recording_id: int) -> dict:
    rec = conn.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,)).fetchone()
    if not rec:
        raise HTTPException(404, "Recording not found")
    return dict(rec)


def get_recording_in_project_or_404(
    conn: sqlite3.Connection,
    project_id: int,
    recording_id: int,
) -> dict:
    get_project_or_404(conn, project_id)
    rec = conn.execute(
        "SELECT * FROM recordings WHERE id = ? AND project_id = ?",
        (recording_id, project_id),
    ).fetchone()
    if not rec:
        raise HTTPException(404, "Recording not found in this project")
    return dict(rec)


def recording_segments(conn: sqlite3.Connection, recording_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, start_ms, end_ms, speaker, transcript, sort_order
        FROM segments WHERE recording_id = ?
        ORDER BY start_ms, id
        """,
        (recording_id,),
    ).fetchall()
    return [dict(r) for r in rows]