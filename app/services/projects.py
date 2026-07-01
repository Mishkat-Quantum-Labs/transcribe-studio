"""Project CRUD and per-project statistics."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from app.analytics import analyze_recording, analyze_segments


def get_project_or_404(conn: sqlite3.Connection, project_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    return dict(row)


def list_projects_summary(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT p.id, p.name, p.description, p.created_at,
               COUNT(r.id) AS recording_count,
               COALESCE(SUM(r.duration_ms), 0) AS total_duration_ms
        FROM projects p
        LEFT JOIN recordings r ON r.project_id = p.id
        GROUP BY p.id
        ORDER BY p.name COLLATE NOCASE, p.id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def project_stats(conn: sqlite3.Connection, project_id: int) -> dict[str, Any]:
    project = get_project_or_404(conn, project_id)
    recordings = conn.execute(
        "SELECT * FROM recordings WHERE project_id = ? ORDER BY id DESC",
        (project_id,),
    ).fetchall()

    total_segments = 0
    transcribed = 0
    total_words = 0
    total_duration = 0
    segmented_ms = 0
    recording_rows = []

    for rec in recordings:
        rec_dict = dict(rec)
        segs = conn.execute(
            "SELECT start_ms, end_ms, speaker, transcript FROM segments WHERE recording_id = ?",
            (rec_dict["id"],),
        ).fetchall()
        seg_list = [dict(s) for s in segs]
        analyzed = analyze_recording(rec_dict, seg_list)
        recording_rows.append(analyzed)
        total_segments += analyzed["segment_count"]
        transcribed += analyzed["transcribed_segments"]
        total_words += analyzed["total_words"]
        total_duration += rec_dict.get("duration_ms") or 0
        segmented_ms += analyzed["segmented_duration_ms"]

    return {
        **project,
        "recording_count": len(recordings),
        "segment_count": total_segments,
        "transcribed_segments": transcribed,
        "total_words": total_words,
        "total_duration_ms": total_duration,
        "segmented_duration_ms": segmented_ms,
        "transcript_pct": round(transcribed / total_segments * 100) if total_segments else 0,
        "coverage_pct": (
            min(100, round(segmented_ms / total_duration * 100)) if total_duration else 0
        ),
        "recordings": recording_rows,
    }


def create_project(conn: sqlite3.Connection, name: str, description: str = "") -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise HTTPException(400, "Project name is required")
    cur = conn.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (name, description.strip()),
    )
    conn.commit()
    return get_project_or_404(conn, cur.lastrowid)


def update_project(
    conn: sqlite3.Connection,
    project_id: int,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise HTTPException(400, "Project name is required")
    get_project_or_404(conn, project_id)
    conn.execute(
        "UPDATE projects SET name = ?, description = ? WHERE id = ?",
        (name, description.strip(), project_id),
    )
    conn.commit()
    return get_project_or_404(conn, project_id)


def list_projects_with_stats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Lightweight per-project stats for dashboard cards."""
    summaries = list_projects_summary(conn)
    for project in summaries:
        row = conn.execute(
            """
            SELECT COUNT(s.id) AS segment_count,
                   SUM(CASE WHEN TRIM(s.transcript) != '' THEN 1 ELSE 0 END) AS transcribed
            FROM recordings r
            LEFT JOIN segments s ON s.recording_id = r.id
            WHERE r.project_id = ?
            """,
            (project["id"],),
        ).fetchone()
        seg_count = row["segment_count"] or 0
        transcribed = row["transcribed"] or 0
        project["segment_count"] = seg_count
        project["transcribed_segments"] = transcribed
        project["transcript_pct"] = (
            round(transcribed / seg_count * 100) if seg_count else 0
        )
    return summaries


def dashboard_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    """Aggregate stats for the home dashboard."""
    projects = list_projects_summary(conn)
    total_recordings = sum(p["recording_count"] for p in projects)
    total_duration = sum(p["total_duration_ms"] for p in projects)

    seg_row = conn.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN transcript != '' THEN 1 ELSE 0 END) AS transcribed
        FROM segments
        """
    ).fetchone()
    total_segments = seg_row["total"] or 0
    transcribed = seg_row["transcribed"] or 0

    for p in projects:
        if p["recording_count"] == 0:
            p["transcript_pct"] = 0
            p["coverage_pct"] = 0
            continue
        stats = project_stats(conn, p["id"])
        p["transcript_pct"] = stats["transcript_pct"]
        p["coverage_pct"] = stats["coverage_pct"]
        p["segment_count"] = stats["segment_count"]

    return {
        "project_count": len(projects),
        "recording_count": total_recordings,
        "total_duration_ms": total_duration,
        "segment_count": total_segments,
        "transcript_pct": round(transcribed / total_segments * 100) if total_segments else 0,
        "projects": projects,
    }


def delete_project(conn: sqlite3.Connection, project_id: int) -> None:
    get_project_or_404(conn, project_id)
    count = conn.execute(
        "SELECT COUNT(*) FROM recordings WHERE project_id = ?",
        (project_id,),
    ).fetchone()[0]
    if count > 0:
        raise HTTPException(
            400,
            f"Project has {count} recording(s). Delete or move them first.",
        )
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()