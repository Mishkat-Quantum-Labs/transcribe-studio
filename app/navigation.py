"""Sidebar tree and recording workspace context."""

from __future__ import annotations

import sqlite3
from typing import Any


def sidebar_tree(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Projects with nested recordings for the sidebar tree."""
    projects = conn.execute(
        "SELECT id, name, description FROM projects ORDER BY name COLLATE NOCASE, id"
    ).fetchall()
    tree = []
    for project in projects:
        recs = conn.execute(
            """
            SELECT id, title, duration_ms,
                   (SELECT COUNT(*) FROM segments s WHERE s.recording_id = r.id) AS segment_count
            FROM recordings r
            WHERE project_id = ?
            ORDER BY title COLLATE NOCASE, id DESC
            """,
            (project["id"],),
        ).fetchall()
        tree.append(
            {
                "id": project["id"],
                "name": project["name"],
                "description": project["description"] or "",
                "recordings": [dict(r) for r in recs],
            }
        )
    return tree


def list_projects(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT p.id, p.name, p.description,
               COUNT(r.id) AS recording_count
        FROM projects p
        LEFT JOIN recordings r ON r.project_id = p.id
        GROUP BY p.id
        ORDER BY p.name COLLATE NOCASE, p.id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_recording_with_project(conn: sqlite3.Connection, recording_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT r.*, p.name AS project_name, p.id AS project_id
        FROM recordings r
        LEFT JOIN projects p ON p.id = r.project_id
        WHERE r.id = ?
        """,
        (recording_id,),
    ).fetchone()
    if not row:
        return {}
    return dict(row)


def evaluation_context_stats(conn: sqlite3.Connection, recording_id: int) -> dict[str, Any]:
    """Stats for the reference vs hypothesis comparison card."""
    rows = conn.execute(
        """
        SELECT transcript, llm_transcript FROM segments WHERE recording_id = ?
        """,
        (recording_id,),
    ).fetchall()
    total = len(rows)
    human_chunks = sum(1 for r in rows if (r["transcript"] or "").strip())
    llm_chunks = sum(1 for r in rows if (r["llm_transcript"] or "").strip())
    human_words = sum(len((r["transcript"] or "").split()) for r in rows)

    try:
        rec = conn.execute(
            "SELECT llm_transcript_file, llm_transcript_format FROM recordings WHERE id = ?",
            (recording_id,),
        ).fetchone()
        llm_format = rec["llm_transcript_format"] if rec else ""
        has_llm = bool(rec and rec["llm_transcript_file"])
    except Exception:
        rec = conn.execute(
            "SELECT llm_transcript_file FROM recordings WHERE id = ?",
            (recording_id,),
        ).fetchone()
        llm_format = ""
        has_llm = bool(rec and rec["llm_transcript_file"])

    return {
        "total_chunks": total,
        "human_chunks": human_chunks,
        "human_words": human_words,
        "human_coverage_pct": round(human_chunks / total * 100, 1) if total else 0,
        "llm_chunks": llm_chunks,
        "llm_coverage_pct": round(llm_chunks / total * 100, 1) if total else 0,
        "has_llm_source": has_llm,
        "llm_format": llm_format or "",
    }