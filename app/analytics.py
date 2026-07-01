"""Dashboard and recording-level transcription analytics."""
from __future__ import annotations

import re
from typing import Any


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _segment_duration(seg: dict) -> int:
    return max(0, seg["end_ms"] - seg["start_ms"])


def analyze_segments(segments: list[dict], duration_ms: int | None) -> dict[str, Any]:
    total = len(segments)
    transcribed = sum(1 for s in segments if (s.get("transcript") or "").strip())
    labeled = sum(1 for s in segments if (s.get("speaker") or "").strip())
    seg_ms = sum(_segment_duration(s) for s in segments)
    words = sum(_word_count(s.get("transcript") or "") for s in segments)

    speaker_stats: dict[str, dict[str, int]] = {}
    for s in segments:
        name = (s.get("speaker") or "").strip() or "Unlabeled"
        if name not in speaker_stats:
            speaker_stats[name] = {"segments": 0, "words": 0, "duration_ms": 0}
        speaker_stats[name]["segments"] += 1
        speaker_stats[name]["words"] += _word_count(s.get("transcript") or "")
        speaker_stats[name]["duration_ms"] += _segment_duration(s)

    speakers = [
        {"name": k, **v}
        for k, v in sorted(speaker_stats.items(), key=lambda x: -x[1]["duration_ms"])
    ]

    dur = duration_ms or 0
    coverage_pct = min(100, round(seg_ms / dur * 100)) if dur else 0
    transcript_pct = round(transcribed / total * 100) if total else 0
    speaker_pct = round(labeled / total * 100) if total else 0
    avg_seg_ms = round(seg_ms / total) if total else 0

    return {
        "segment_count": total,
        "transcribed_segments": transcribed,
        "speaker_labeled_segments": labeled,
        "empty_segments": total - transcribed,
        "total_words": words,
        "segmented_duration_ms": seg_ms,
        "coverage_pct": coverage_pct,
        "transcript_pct": transcript_pct,
        "speaker_label_pct": speaker_pct,
        "avg_segment_ms": avg_seg_ms,
        "speakers": speakers,
    }


def analyze_recording(rec: dict, segments: list[dict]) -> dict[str, Any]:
    stats = analyze_segments(segments, rec.get("duration_ms"))
    return {
        "id": rec["id"],
        "title": rec["title"],
        "duration_ms": rec.get("duration_ms"),
        "created_at": rec.get("created_at", "")[:10],
        "notes": rec.get("notes") or "",
        **stats,
    }


def dashboard_stats(conn) -> dict[str, Any]:
    recordings = conn.execute(
        "SELECT id, title, duration_ms, created_at FROM recordings ORDER BY id DESC"
    ).fetchall()

    total_segments = conn.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
    total_duration = conn.execute(
        "SELECT COALESCE(SUM(duration_ms), 0) FROM recordings"
    ).fetchone()[0]

    all_segments = conn.execute(
        "SELECT recording_id, start_ms, end_ms, speaker, transcript FROM segments"
    ).fetchall()
    seg_list = [dict(s) for s in all_segments]
    transcribed = sum(1 for s in seg_list if (s.get("transcript") or "").strip())
    words = sum(_word_count(s.get("transcript") or "") for s in seg_list)
    segmented_ms = sum(_segment_duration(s) for s in seg_list)

    speakers = {
        (s.get("speaker") or "").strip() or "Unlabeled"
        for s in seg_list
        if (s.get("transcript") or "").strip() or (s.get("speaker") or "").strip()
    }

    recording_stats = []
    for rec in recordings:
        rec_segs = [s for s in seg_list if s["recording_id"] == rec["id"]]
        recording_stats.append(analyze_recording(dict(rec), rec_segs))

    overall_transcript_pct = (
        round(transcribed / total_segments * 100) if total_segments else 0
    )
    overall_coverage_pct = (
        min(100, round(segmented_ms / total_duration * 100)) if total_duration else 0
    )

    return {
        "recording_count": len(recordings),
        "segment_count": total_segments,
        "total_duration_ms": total_duration,
        "segmented_duration_ms": segmented_ms,
        "transcribed_segments": transcribed,
        "total_words": words,
        "unique_speakers": len(speakers),
        "transcript_pct": overall_transcript_pct,
        "coverage_pct": overall_coverage_pct,
        "recordings": recording_stats,
    }


def fmt_duration(ms: int | None) -> str:
    if not ms:
        return "—"
    s = ms / 1000
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {sec:.0f}s"
    return f"{sec:.1f}s"