"""JSON segment list parsers (id, start_ms, or full text)."""

import json
from pathlib import Path

from app.transcript_formats.models import ParsedTranscript
from app.transcript_formats.parsers.base import BaseTranscriptParser


class JsonSegmentsParser(BaseTranscriptParser):
    format_id = "json_segments"
    format_name = "JSON segments"
    extensions = (".json",)

    def can_handle(self, content: str, *, filename: str = "") -> bool:
        stripped = content.strip()
        if not stripped:
            return False
        if filename and Path(filename).suffix.lower() not in self.extensions:
            # Still try JSON content in .txt uploads
            if Path(filename).suffix.lower() == ".txt":
                try:
                    json.loads(stripped)
                    return True
                except json.JSONDecodeError:
                    return False
            return False
        try:
            json.loads(stripped)
            return True
        except json.JSONDecodeError:
            return False

    def parse(self, content: str, *, filename: str = "") -> ParsedTranscript | None:
        stripped = content.strip()
        if not stripped:
            return None

        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        by_id: dict[int, str] = {}
        by_start_ms: dict[int, str] = {}

        if isinstance(data, dict) and "segments" in data:
            segments = data["segments"]
        elif isinstance(data, list):
            segments = data
        elif isinstance(data, dict) and ("transcript" in data or "text" in data):
            full = data.get("transcript") or data.get("text", "")
            return ParsedTranscript(
                format_id=self.format_id,
                format_name=self.format_name,
                full=full if isinstance(full, str) else "",
            )
        else:
            return None

        for seg in segments:
            if not isinstance(seg, dict):
                continue
            text = seg.get("text") or seg.get("transcript") or seg.get("content", "")
            if not isinstance(text, str):
                continue
            if seg.get("id") is not None:
                by_id[int(seg["id"])] = text
            elif seg.get("start_ms") is not None:
                by_start_ms[int(seg["start_ms"])] = text

        if not by_id and not by_start_ms:
            return None

        return ParsedTranscript(
            format_id=self.format_id,
            format_name=self.format_name,
            by_id=by_id,
            by_start_ms=by_start_ms,
            metadata={"segment_count": len(by_id) + len(by_start_ms)},
        )