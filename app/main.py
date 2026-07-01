import shutil
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.analytics import analyze_recording, dashboard_stats
from app.database import (
    DATA_DIR,
    get_conn,
    init_db,
    migrate_add_llm_transcript,
    migrate_add_projects,
    migrate_add_recording_llm_fields,
)
from app.paths import STATIC_DIR
from app.web.deps import get_recording_or_404, recording_segments
from app.web.routes import register_page_routes
from app.export_formats import export_recording as build_export
from app.evaluation.engine import EvaluationEngine
from app.transcript_formats import list_parsers, parse_transcript, parsed_to_segment_text
from app.transcript_formats.registry import accepted_upload_extensions
from app.transcript_formats.config import get_transcript_config

AUDIO_DIR = DATA_DIR / "audio"

app = FastAPI(title="Transcribe Studio")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
register_page_routes(app)


class SegmentIn(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    speaker: str = ""
    transcript: str = ""


class SegmentUpdate(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    speaker: str = ""
    transcript: str = ""


class NotesUpdate(BaseModel):
    notes: str = ""


class EqualSegmentsIn(BaseModel):
    unit: str = "seconds"
    value: float = Field(gt=0)
    duration_ms: int | None = None


class DivideChunksIn(BaseModel):
    mode: str = "duration"  # duration | count
    unit: str = "seconds"
    value: float = Field(gt=0)
    replace: bool = True
    duration_ms: int | None = None


MAX_AUTO_SEGMENTS = 150


@app.on_event("startup")
def startup() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    migrate_add_llm_transcript()
    migrate_add_recording_llm_fields()
    migrate_add_projects()


@app.post("/api/recordings")
async def upload_recording(
    title: str = Form(...),
    file: UploadFile = File(...),
    project_id: int | None = Form(None),
):
    if not file.filename:
        raise HTTPException(400, "No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        raise HTTPException(400, "Unsupported audio format")

    stored = f"{uuid.uuid4().hex}{ext}"
    dest = AUDIO_DIR / stored
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    conn = get_conn()
    if project_id is None:
        default = conn.execute(
            "SELECT id FROM projects ORDER BY id LIMIT 1"
        ).fetchone()
        project_id = default["id"] if default else None

    cur = conn.execute(
        "INSERT INTO recordings (title, filename, project_id) VALUES (?, ?, ?)",
        (title.strip() or file.filename, stored, project_id),
    )
    conn.commit()
    rec_id = cur.lastrowid
    conn.close()
    return {"id": rec_id, "title": title, "filename": stored}


@app.get("/api/recordings/{recording_id}")
def get_recording(recording_id: int):
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    segments = recording_segments(conn, recording_id)
    conn.close()
    return {"recording": rec, "segments": segments}


@app.get("/api/dashboard/stats")
def api_dashboard_stats():
    conn = get_conn()
    stats = dashboard_stats(conn)
    conn.close()
    return stats


@app.get("/api/recordings/{recording_id}/analysis")
def api_recording_analysis(recording_id: int):
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    segs = recording_segments(conn, recording_id)
    conn.close()
    return analyze_recording(rec, segs)


@app.patch("/api/recordings/{recording_id}")
def update_recording(recording_id: int, body: NotesUpdate):
    conn = get_conn()
    cur = conn.execute(
        "UPDATE recordings SET notes = ? WHERE id = ?",
        (body.notes, recording_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Recording not found")
    return {"ok": True}


@app.patch("/api/recordings/{recording_id}/duration")
def set_duration(recording_id: int, duration_ms: int = Form(...)):
    conn = get_conn()
    cur = conn.execute(
        "UPDATE recordings SET duration_ms = ? WHERE id = ?",
        (duration_ms, recording_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Recording not found")
    return {"duration_ms": duration_ms}


@app.get("/api/recordings/{recording_id}/audio")
def stream_audio(recording_id: int):
    conn = get_conn()
    rec = conn.execute(
        "SELECT filename FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone()
    conn.close()
    if not rec:
        raise HTTPException(404, "Recording not found")
    path = AUDIO_DIR / rec["filename"]
    if not path.exists():
        raise HTTPException(404, "Audio file missing")
    return FileResponse(path)


@app.post("/api/recordings/{recording_id}/segments/overlap")
def create_overlap_segment(recording_id: int, source_segment_id: int):
    """Duplicate time range for another speaker/label at the same time."""
    conn = get_conn()
    src = conn.execute(
        "SELECT * FROM segments WHERE id = ? AND recording_id = ?",
        (source_segment_id, recording_id),
    ).fetchone()
    if not src:
        conn.close()
        raise HTTPException(404, "Source segment not found")
    order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM segments WHERE recording_id = ?",
        (recording_id,),
    ).fetchone()[0]
    cur = conn.execute(
        """
        INSERT INTO segments (recording_id, start_ms, end_ms, speaker, transcript, sort_order)
        VALUES (?, ?, ?, '', '', ?)
        """,
        (recording_id, src["start_ms"], src["end_ms"], order),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM segments WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


@app.post("/api/recordings/{recording_id}/segments")
def create_segment(recording_id: int, body: SegmentIn):
    if body.end_ms <= body.start_ms:
        raise HTTPException(400, "end_ms must be greater than start_ms")
    conn = get_conn()
    if not conn.execute(
        "SELECT 1 FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone():
        conn.close()
        raise HTTPException(404, "Recording not found")
    order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM segments WHERE recording_id = ?",
        (recording_id,),
    ).fetchone()[0]
    cur = conn.execute(
        """
        INSERT INTO segments (recording_id, start_ms, end_ms, speaker, transcript, sort_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            recording_id,
            body.start_ms,
            body.end_ms,
            body.speaker.strip(),
            body.transcript.strip(),
            order,
        ),
    )
    conn.commit()
    seg_id = cur.lastrowid
    row = conn.execute("SELECT * FROM segments WHERE id = ?", (seg_id,)).fetchone()
    conn.close()
    return dict(row)


@app.put("/api/segments/{segment_id}")
def update_segment(segment_id: int, body: SegmentUpdate):
    if body.end_ms <= body.start_ms:
        raise HTTPException(400, "end_ms must be greater than start_ms")
    conn = get_conn()
    cur = conn.execute(
        """
        UPDATE segments
        SET start_ms = ?, end_ms = ?, speaker = ?, transcript = ?,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            body.start_ms,
            body.end_ms,
            body.speaker.strip(),
            body.transcript.strip(),
            segment_id,
        ),
    )
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(404, "Segment not found")
    row = conn.execute("SELECT * FROM segments WHERE id = ?", (segment_id,)).fetchone()
    conn.close()
    return dict(row)


@app.delete("/api/recordings/{recording_id}/segments")
def delete_all_segments(recording_id: int):
    conn = get_conn()
    if not conn.execute(
        "SELECT 1 FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone():
        conn.close()
        raise HTTPException(404, "Recording not found")
    cur = conn.execute(
        "DELETE FROM segments WHERE recording_id = ?", (recording_id,)
    )
    conn.commit()
    conn.close()
    return {"deleted": cur.rowcount}


@app.delete("/api/segments/{segment_id}")
def delete_segment(segment_id: int):
    conn = get_conn()
    cur = conn.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Segment not found")
    return {"ok": True}


def _divide_segments(duration: int, mode: str, unit: str, value: float) -> list[tuple[int, int]]:
    """Return list of (start_ms, end_ms) chunk boundaries."""
    if mode == "count":
        count = int(value)
        if count < 1 or count > MAX_AUTO_SEGMENTS:
            raise HTTPException(
                400,
                f"Segment count must be between 1 and {MAX_AUTO_SEGMENTS}",
            )
        step = duration // count
        if step < 100:
            raise HTTPException(400, "Too many segments — audio would be split finer than 100ms")
        ranges: list[tuple[int, int]] = []
        start = 0
        for i in range(count):
            end = duration if i == count - 1 else min(start + step, duration)
            if end <= start:
                break
            ranges.append((start, end))
            start = end
        return ranges

    step = int(value) if unit == "milliseconds" else int(value * 1000)
    if step < 100:
        raise HTTPException(400, "Chunk length must be at least 100ms")
    estimated = (duration + step - 1) // step
    if estimated > MAX_AUTO_SEGMENTS:
        raise HTTPException(
            400,
            f"This would create ~{estimated} segments (max {MAX_AUTO_SEGMENTS}). "
            "Use longer chunks or fewer splits.",
        )
    ranges = []
    start = 0
    while start < duration:
        end = min(start + step, duration)
        ranges.append((start, end))
        start = end
    return ranges


@app.post("/api/recordings/{recording_id}/divide-chunks")
def divide_chunks(recording_id: int, body: DivideChunksIn):
    conn = get_conn()
    rec = conn.execute(
        "SELECT duration_ms FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone()
    if not rec:
        conn.close()
        raise HTTPException(404, "Recording not found")
    duration = rec["duration_ms"] or body.duration_ms
    if not duration:
        conn.close()
        raise HTTPException(400, "Audio duration unknown — wait for waveform to load")

    if body.duration_ms and not rec["duration_ms"]:
        conn.execute(
            "UPDATE recordings SET duration_ms = ? WHERE id = ?",
            (body.duration_ms, recording_id),
        )

    try:
        ranges = _divide_segments(duration, body.mode, body.unit, body.value)
    except HTTPException:
        conn.close()
        raise

    if body.replace:
        conn.execute("DELETE FROM segments WHERE recording_id = ?", (recording_id,))

    order = 0
    created = []
    for start, end in ranges:
        order += 1
        cur = conn.execute(
            """
            INSERT INTO segments (recording_id, start_ms, end_ms, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (recording_id, start, end, order),
        )
        row = conn.execute(
            "SELECT * FROM segments WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        created.append(dict(row))

    conn.commit()
    conn.close()
    return {"created": created, "count": len(created), "replaced": body.replace}


@app.post("/api/recordings/{recording_id}/equal-segments")
def generate_equal_segments(recording_id: int, body: EqualSegmentsIn):
    conn = get_conn()
    rec = conn.execute(
        "SELECT duration_ms FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone()
    if not rec:
        conn.close()
        raise HTTPException(404, "Recording not found")
    return divide_chunks(
        recording_id,
        DivideChunksIn(
            mode="duration",
            unit=body.unit,
            value=body.value,
            replace=False,
            duration_ms=body.duration_ms,
        ),
    )


@app.get("/api/recordings/{recording_id}/export")
def export_recording_endpoint(recording_id: int, format: str = "json"):
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    segments = conn.execute(
        """
        SELECT start_ms, end_ms, speaker, transcript
        FROM segments WHERE recording_id = ?
        ORDER BY start_ms, id
        """,
        (recording_id,),
    ).fetchall()
    conn.close()

    try:
        filename, media_type, content = build_export(
            rec, [dict(s) for s in segments], format
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/recordings/{recording_id}")
def delete_recording(recording_id: int):
    conn = get_conn()
    rec = conn.execute(
        "SELECT filename FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone()
    if not rec:
        conn.close()
        raise HTTPException(404, "Recording not found")
    conn.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
    conn.commit()
    conn.close()
    path = AUDIO_DIR / rec["filename"]
    if path.exists():
        path.unlink()
    return {"ok": True}


def run() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=8082, reload=False)


# ============================================================
# LLM Transcript & Evaluation Endpoints
# ============================================================

LLM_TRANSCRIPT_DIR = DATA_DIR / "llm_transcripts"


class LLMTranscriptPaste(BaseModel):
    content: str = Field(min_length=1)
    language: str = "en"
    format_hint: str = ""


class SegmentLLMUpdate(BaseModel):
    llm_transcript: str = ""


class EvaluationConfigUpdate(BaseModel):
    language: str = "en"
    reference_key: str = "transcript"
    hypothesis_key: str = "llm_transcript"


def _ensure_llm_dir():
    LLM_TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)


def _apply_llm_transcript(conn, recording_id: int, parsed) -> dict[str, Any]:
    """Map parsed transcript onto recording chunks. Returns stats."""
    segments = conn.execute(
        """
        SELECT id, start_ms, end_ms FROM segments
        WHERE recording_id = ? ORDER BY start_ms, id
        """,
        (recording_id,),
    ).fetchall()
    if not segments:
        return {"updated": 0, "matched_segments": 0, "total_segments": 0}

    rec = conn.execute(
        "SELECT duration_ms FROM recordings WHERE id = ?", (recording_id,)
    ).fetchone()
    cfg = get_transcript_config()
    mapping = parsed_to_segment_text(
        parsed,
        [dict(s) for s in segments],
        duration_ms=rec["duration_ms"] if rec else None,
        include_speaker=cfg.include_speaker_in_alignment,
    )

    updated = 0
    for seg_id, text in mapping.items():
        cur = conn.execute(
            "UPDATE segments SET llm_transcript = ? WHERE id = ? AND recording_id = ?",
            (text, seg_id, recording_id),
        )
        updated += cur.rowcount

    return {
        "updated": updated,
        "matched_segments": len(mapping),
        "total_segments": len(segments),
        "utterance_count": len(parsed.utterances),
    }


@app.get("/api/transcript-formats")
def get_transcript_formats():
    """List supported transcript import formats (for UI + contributors)."""
    exts = accepted_upload_extensions()
    cfg = get_transcript_config()
    return {
        "formats": list_parsers(),
        "accepted_extensions": exts,
        "accepted_extensions_label": ", ".join(exts),
        "max_upload_bytes": cfg.upload.max_bytes,
        "max_upload_mb": round(cfg.upload.max_bytes / (1024 * 1024), 1),
    }


def _virtual_filename_for_paste(format_hint: str | None) -> str:
    if format_hint == "json_segments":
        return "paste.json"
    return "paste.txt"


def _ingest_llm_transcript(
    conn,
    recording_id: int,
    text_content: str,
    *,
    language: str,
    format_hint: str | None,
    virtual_filename: str,
    stored_filename: str,
) -> dict[str, Any]:
    """Parse, apply to segments, and update recording metadata."""
    try:
        parsed = parse_transcript(
            text_content,
            filename=virtual_filename,
            format_hint=format_hint,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    apply_stats = _apply_llm_transcript(conn, recording_id, parsed)
    conn.execute(
        """
        UPDATE recordings
        SET llm_transcript_file = ?, llm_transcript_lang = ?, llm_transcript_format = ?
        WHERE id = ?
        """,
        (stored_filename, language, parsed.format_id, recording_id),
    )
    conn.commit()

    return {
        "ok": True,
        "filename": stored_filename,
        "language": language,
        "format": parsed.format_id,
        "format_name": parsed.format_name,
        "segments_updated": apply_stats["updated"],
        "matched_segments": apply_stats["matched_segments"],
        "total_segments": apply_stats["total_segments"],
        "utterance_count": apply_stats.get("utterance_count", 0),
    }


@app.post("/api/recordings/{recording_id}/llm-transcript")
async def upload_llm_transcript(
    request: Request,
    recording_id: int,
    file: UploadFile = File(...),
    language: str = Form("en"),
    format_hint: str = Form(""),
):
    """
    Upload LLM-generated transcript JSON file.

    Expected JSON format:
    {
        "segments": [
            {"id": 1, "text": "Hello world"},
            {"id": 2, "text": "How are you?"}
        ]
    }

    Or with timestamps:
    {
        "segments": [
            {"start_ms": 0, "end_ms": 5000, "text": "Hello"},
            {"start_ms": 5000, "end_ms": 10000, "text": "World"}
        ]
    }
    """
    _ensure_llm_dir()

    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    conn.close()

    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    allowed = set(accepted_upload_extensions())
    if ext not in allowed:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Accepted: {', '.join(sorted(allowed))}",
        )

    content = await file.read()
    max_bytes = get_transcript_config().upload.max_bytes
    if len(content) > max_bytes:
        raise HTTPException(
            400,
            f"File too large (max {max_bytes // (1024 * 1024)} MB).",
        )

    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded")

    stored_filename = f"{uuid.uuid4().hex}{ext}"
    stored_path = LLM_TRANSCRIPT_DIR / stored_filename
    stored_path.write_text(text_content, encoding="utf-8")

    conn = get_conn()
    try:
        return _ingest_llm_transcript(
            conn,
            recording_id,
            text_content,
            language=language,
            format_hint=format_hint or None,
            virtual_filename=file.filename or stored_filename,
            stored_filename=stored_filename,
        )
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()


@app.post("/api/recordings/{recording_id}/llm-transcript/paste")
def paste_llm_transcript(recording_id: int, body: LLMTranscriptPaste):
    """Paste LLM transcript text directly (no file required)."""
    _ensure_llm_dir()

    conn = get_conn()
    get_recording_or_404(conn, recording_id)

    hint = body.format_hint or None
    virtual_name = _virtual_filename_for_paste(hint)
    stored_filename = f"pasted-{uuid.uuid4().hex}.txt"
    stored_path = LLM_TRANSCRIPT_DIR / stored_filename
    stored_path.write_text(body.content.strip(), encoding="utf-8")

    try:
        return _ingest_llm_transcript(
            conn,
            recording_id,
            body.content,
            language=body.language,
            format_hint=hint,
            virtual_filename=virtual_name,
            stored_filename=stored_filename,
        )
    except HTTPException:
        stored_path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()


@app.patch("/api/segments/{segment_id}/llm-transcript")
def update_segment_llm_transcript(segment_id: int, body: SegmentLLMUpdate):
    """Update LLM transcript for a single segment."""
    conn = get_conn()
    cur = conn.execute(
        "UPDATE segments SET llm_transcript = ?, updated_at = datetime('now') WHERE id = ?",
        (body.llm_transcript, segment_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Segment not found")
    return {"ok": True}


@app.get("/api/recordings/{recording_id}/evaluation")
def evaluate_recording(
    recording_id: int,
    language: str = "en",
    reference_key: str = "transcript",
    hypothesis_key: str = "llm_transcript",
):
    """
    Evaluate recording against LLM transcript.

    Computes WER and semantic similarity for each segment.
    """
    conn = get_conn()
    rec = get_recording_or_404(conn, recording_id)
    segments = conn.execute(
        """
        SELECT id, start_ms, end_ms, speaker, transcript, llm_transcript
        FROM segments WHERE recording_id = ?
        ORDER BY start_ms, id
        """,
        (recording_id,),
    ).fetchall()
    conn.close()

    if not segments:
        raise HTTPException(400, "No segments found")

    # Check if we have LLM transcripts
    has_llm = any(s["llm_transcript"] for s in segments)
    if not has_llm:
        raise HTTPException(400, "No LLM transcripts found. Upload an LLM transcript first.")

    # Run evaluation
    engine = EvaluationEngine()
    seg_dicts = [dict(s) for s in segments]

    result = engine.evaluate_recording(
        recording_id=recording_id,
        segments=seg_dicts,
        reference_key=reference_key,
        hypothesis_key=hypothesis_key,
        language=language,
    )

    return result.to_dict()


@app.get("/api/evaluation/config")
def get_evaluation_config():
    """Expose evaluation settings for contributors / UI."""
    from app.evaluation.config import get_config

    cfg = get_config()
    return {
        "version": cfg.version,
        "default_language": cfg.default_language,
        "languages": [
            {"code": code, "name": lang.name}
            for code, lang in cfg.languages.items()
        ],
        "metrics": {
            name: {"enabled": m.enabled, "weight": m.weight}
            for name, m in cfg.metrics.items()
        },
    }


@app.get("/api/recordings/{recording_id}/llm-transcript/status")
def get_llm_transcript_status(recording_id: int):
    """Get status of LLM transcript for a recording."""
    conn = get_conn()
    rec = conn.execute(
        "SELECT llm_transcript_file, llm_transcript_lang, llm_transcript_format FROM recordings WHERE id = ?",
        (recording_id,),
    ).fetchone()
    segments = conn.execute(
        """
        SELECT COUNT(*) as total,
               SUM(CASE WHEN llm_transcript != '' THEN 1 ELSE 0 END) as with_transcript
        FROM segments WHERE recording_id = ?
        """,
        (recording_id,),
    ).fetchone()
    conn.close()

    if not rec:
        raise HTTPException(404, "Recording not found")

    return {
        "has_file": bool(rec["llm_transcript_file"]),
        "filename": rec["llm_transcript_file"],
        "language": rec["llm_transcript_lang"],
        "format": rec["llm_transcript_format"] or None,
        "segments": {
            "total": segments["total"],
            "with_transcript": segments["with_transcript"],
            "coverage_percent": round(segments["with_transcript"] / segments["total"] * 100, 1)
                if segments["total"] > 0 else 0,
        },
    }


@app.delete("/api/recordings/{recording_id}/llm-transcript")
def delete_llm_transcript(recording_id: int):
    """Delete LLM transcript for a recording."""
    conn = get_conn()

    # Get filename to delete
    rec = conn.execute(
        "SELECT llm_transcript_file FROM recordings WHERE id = ?",
        (recording_id,),
    ).fetchone()

    if rec and rec["llm_transcript_file"]:
        path = LLM_TRANSCRIPT_DIR / rec["llm_transcript_file"]
        if path.exists():
            path.unlink()

    # Clear from database
    conn.execute(
        "UPDATE recordings SET llm_transcript_file = '', llm_transcript_lang = 'en', llm_transcript_format = '' WHERE id = ?",
        (recording_id,),
    )
    conn.execute(
        "UPDATE segments SET llm_transcript = '' WHERE recording_id = ?",
        (recording_id,),
    )
    conn.commit()
    conn.close()

    return {"ok": True}


if __name__ == "__main__":
    run()