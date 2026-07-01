"""Human-readable and machine-readable transcription export formats."""
import csv
import io
import json
from typing import Any


def ms_to_timestamp(ms: int, sep: str = ".") -> str:
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    milli = ms % 1_000
    if h:
        return f"{h}:{m:02d}:{s:02d}{sep}{milli:03d}"
    return f"{m}:{s:02d}{sep}{milli:03d}"


def ms_to_srt(ms: int) -> str:
    h = ms // 3_600_000
    m = (ms % 3_600_000) // 60_000
    s = (ms % 60_000) // 1_000
    milli = ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def _segments(recording: dict, segments: list[dict]) -> list[dict]:
    return sorted(segments, key=lambda s: (s["start_ms"], s.get("id", 0)))


def build_payload(recording: dict, segments: list[dict]) -> dict[str, Any]:
    return {
        "recording_id": recording["id"],
        "title": recording["title"],
        "duration_ms": recording["duration_ms"],
        "notes": recording.get("notes") or "",
        "segments": [
            {
                "start_ms": s["start_ms"],
                "end_ms": s["end_ms"],
                "speaker": s.get("speaker") or "",
                "transcript": s.get("transcript") or "",
            }
            for s in _segments(recording, segments)
        ],
    }


def export_json(recording: dict, segments: list[dict]) -> str:
    return json.dumps(build_payload(recording, segments), indent=2, ensure_ascii=False)


def export_txt(recording: dict, segments: list[dict]) -> str:
    lines = [
        recording["title"],
        "=" * len(recording["title"]),
        "",
    ]
    if recording.get("duration_ms"):
        lines.append(f"Duration: {ms_to_timestamp(recording['duration_ms'])}")
    if recording.get("notes"):
        lines.append(f"Notes: {recording['notes']}")
    lines.append("")
    lines.append("TRANSCRIPT")
    lines.append("-" * 40)
    lines.append("")

    for i, seg in enumerate(_segments(recording, segments), 1):
        start = ms_to_timestamp(seg["start_ms"])
        end = ms_to_timestamp(seg["end_ms"])
        speaker = (seg.get("speaker") or "").strip() or "Unknown speaker"
        text = (seg.get("transcript") or "").strip() or "(no transcript)"
        lines.append(f"[{start} → {end}]  {speaker}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def export_markdown(recording: dict, segments: list[dict]) -> str:
    lines = [f"# {recording['title']}", ""]
    if recording.get("duration_ms"):
        lines.append(f"**Duration:** {ms_to_timestamp(recording['duration_ms'])}  ")
    if recording.get("notes"):
        lines.append(f"**Notes:** {recording['notes']}  ")
    lines.extend(["", "---", ""])

    for i, seg in enumerate(_segments(recording, segments), 1):
        start = ms_to_timestamp(seg["start_ms"])
        end = ms_to_timestamp(seg["end_ms"])
        speaker = (seg.get("speaker") or "").strip() or "_Unknown speaker_"
        text = (seg.get("transcript") or "").strip() or "_(no transcript)_"
        lines.append(f"## {i}. {start} – {end}")
        lines.append(f"**Speaker:** {speaker}")
        lines.append("")
        lines.append(f"> {text.replace(chr(10), chr(10) + '> ')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def export_srt(recording: dict, segments: list[dict]) -> str:
    blocks = []
    for i, seg in enumerate(_segments(recording, segments), 1):
        text = (seg.get("transcript") or "").strip()
        if not text:
            continue
        speaker = (seg.get("speaker") or "").strip()
        caption = f"{speaker}: {text}" if speaker else text
        blocks.append(
            f"{i}\n"
            f"{ms_to_srt(seg['start_ms'])} --> {ms_to_srt(seg['end_ms'])}\n"
            f"{caption}\n"
        )
    return "\n".join(blocks)


def export_vtt(recording: dict, segments: list[dict]) -> str:
    lines = ["WEBVTT", f"NOTE {recording['title']}", ""]
    for seg in _segments(recording, segments):
        text = (seg.get("transcript") or "").strip()
        if not text:
            continue
        speaker = (seg.get("speaker") or "").strip()
        start = ms_to_srt(seg["start_ms"]).replace(",", ".")
        end = ms_to_srt(seg["end_ms"]).replace(",", ".")
        caption = f"<v {speaker}>{text}" if speaker else text
        lines.extend([f"{start} --> {end}", caption, ""])
    return "\n".join(lines).rstrip() + "\n"


def export_csv(recording: dict, segments: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "segment",
            "start_ms",
            "end_ms",
            "start_time",
            "end_time",
            "speaker",
            "transcript",
        ]
    )
    for i, seg in enumerate(_segments(recording, segments), 1):
        writer.writerow(
            [
                i,
                seg["start_ms"],
                seg["end_ms"],
                ms_to_timestamp(seg["start_ms"]),
                ms_to_timestamp(seg["end_ms"]),
                seg.get("speaker") or "",
                seg.get("transcript") or "",
            ]
        )
    return buf.getvalue()


EXPORTERS: dict[str, tuple[str, str, str]] = {
    "json": ("application/json", ".json", export_json),
    "txt": ("text/plain; charset=utf-8", ".txt", export_txt),
    "md": ("text/markdown; charset=utf-8", ".md", export_markdown),
    "markdown": ("text/markdown; charset=utf-8", ".md", export_markdown),
    "srt": ("application/x-subrip; charset=utf-8", ".srt", export_srt),
    "vtt": ("text/vtt; charset=utf-8", ".vtt", export_vtt),
    "csv": ("text/csv; charset=utf-8", ".csv", export_csv),
}


def export_recording(recording: dict, segments: list[dict], fmt: str) -> tuple[str, str, str]:
    key = fmt.lower().strip()
    if key not in EXPORTERS:
        raise ValueError(f"Unknown format: {fmt}")
    media_type, ext, fn = EXPORTERS[key]
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in recording["title"])
    filename = f"{safe_title}{ext}"
    return filename, media_type, fn(recording, segments)