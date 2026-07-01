"""Parser registry with auto-detection."""

from pathlib import Path

from app.transcript_formats.config import get_transcript_config
from app.transcript_formats.models import ParsedTranscript
from app.transcript_formats.parsers.base import BaseTranscriptParser
from app.transcript_formats.parsers.json_segments import JsonSegmentsParser
from app.transcript_formats.parsers.plain_text import PlainTextParser
from app.transcript_formats.parsers.timestamp_speaker import TimestampSpeakerParser

_BUILTIN_PARSERS: dict[str, BaseTranscriptParser] = {
    "timestamp_speaker": TimestampSpeakerParser(),
    "json_segments": JsonSegmentsParser(),
    "plain_text": PlainTextParser(),
}


def accepted_upload_extensions() -> list[str]:
    """Canonical list of allowed file extensions (from config)."""
    cfg = get_transcript_config()
    exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in cfg.upload.accepted_extensions]
    return sorted(set(exts))


def list_parsers() -> list[dict]:
    """Formats exposed to UI / API."""
    cfg = get_transcript_config()
    out = []
    for parser_id, parser in _ordered_parsers():
        fmt = cfg.formats.get(parser_id)
        if fmt and not fmt.enabled:
            continue
        out.append(
            {
                "id": parser.format_id,
                "name": fmt.name if fmt else parser.format_name,
                "description": fmt.description if fmt else "",
                "extensions": list(fmt.extensions if fmt else parser.extensions),
                "example": fmt.example if fmt else "",
            }
        )
    return out


def _ordered_parsers() -> list[tuple[str, BaseTranscriptParser]]:
    cfg = get_transcript_config()
    order = cfg.detection_order or list(_BUILTIN_PARSERS.keys())
    seen: set[str] = set()
    ordered: list[tuple[str, BaseTranscriptParser]] = []
    for pid in order:
        if pid in _BUILTIN_PARSERS and pid not in seen:
            ordered.append((pid, _BUILTIN_PARSERS[pid]))
            seen.add(pid)
    for pid, parser in _BUILTIN_PARSERS.items():
        if pid not in seen:
            ordered.append((pid, parser))
    return ordered


def parse_transcript(
    content: str,
    *,
    filename: str = "",
    format_hint: str | None = None,
) -> ParsedTranscript:
    """
    Parse transcript content using auto-detection or an explicit format hint.

    Raises ValueError if no parser matches.
    """
    stripped = content.strip()
    if not stripped:
        raise ValueError("Transcript file is empty")

    if format_hint:
        parser = _BUILTIN_PARSERS.get(format_hint)
        if not parser:
            raise ValueError(f"Unknown transcript format: {format_hint}")
        result = parser.parse(stripped, filename=filename)
        if result is None:
            raise ValueError(f"File does not match format '{format_hint}'")
        return result

    errors: list[str] = []
    for parser_id, parser in _ordered_parsers():
        fmt = get_transcript_config().formats.get(parser_id)
        if fmt and not fmt.enabled:
            continue
        try:
            if not parser.can_handle(stripped, filename=filename):
                continue
            result = parser.parse(stripped, filename=filename)
            if result is not None:
                return result
        except Exception as exc:
            errors.append(f"{parser_id}: {exc}")

    ext = Path(filename).suffix.lower() if filename else ""
    hint = f" Supported: {', '.join(p['id'] for p in list_parsers())}."
    if errors:
        raise ValueError("Could not detect transcript format." + hint)
    raise ValueError("Could not detect transcript format." + hint)