"""Fallback: entire file is one transcript blob."""

from app.transcript_formats.models import ParsedTranscript
from app.transcript_formats.parsers.base import BaseTranscriptParser


class PlainTextParser(BaseTranscriptParser):
    format_id = "plain_text"
    format_name = "Plain text"
    extensions = (".txt",)

    def parse(self, content: str, *, filename: str = "") -> ParsedTranscript | None:
        stripped = content.strip()
        if not stripped:
            return None

        return ParsedTranscript(
            format_id=self.format_id,
            format_name=self.format_name,
            full=stripped,
        )