"""
Parser for timestamp + speaker lines:

    [MM:SS] Teacher: Hello everyone
    [01:51] Student 1: I agree
    [1:02:24] Speaker: also supports HH:MM:SS
"""

import re

from app.transcript_formats.models import ParsedTranscript, Utterance
from app.transcript_formats.parsers.base import BaseTranscriptParser

LINE_RE = re.compile(
    r"^\[(?P<time>[^\]]+)\]\s*(?P<speaker>[^:]+?):\s*(?P<text>.+?)\s*$",
    re.MULTILINE,
)


def parse_timestamp_to_ms(value: str) -> int:
    """Convert MM:SS or HH:MM:SS to milliseconds."""
    parts = [int(p) for p in value.strip().split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        total_seconds = minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        total_seconds = hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError(f"Unsupported timestamp: {value}")
    return total_seconds * 1000


def infer_end_times(utterances: list[Utterance], duration_ms: int | None = None) -> None:
    """Set end_ms from the next utterance's start (or recording end)."""
    for i, utt in enumerate(utterances):
        if i + 1 < len(utterances):
            utt.end_ms = utterances[i + 1].start_ms
        elif duration_ms and duration_ms > utt.start_ms:
            utt.end_ms = duration_ms
        else:
            utt.end_ms = utt.start_ms + 60_000


class TimestampSpeakerParser(BaseTranscriptParser):
    format_id = "timestamp_speaker"
    format_name = "Timestamp + Speaker"
    extensions = (".txt", ".transcript", ".tsv")
    auto_detect_patterns = (r"^\[\d{1,2}:\d{2}\]", r"^\[\d{1,2}:\d{2}:\d{2}\]")

    def parse(self, content: str, *, filename: str = "") -> ParsedTranscript | None:
        if not self.can_handle(content, filename=filename):
            return None

        utterances: list[Utterance] = []
        for match in LINE_RE.finditer(content):
            try:
                start_ms = parse_timestamp_to_ms(match.group("time"))
            except ValueError:
                continue
            utterances.append(
                Utterance(
                    start_ms=start_ms,
                    speaker=match.group("speaker").strip(),
                    text=match.group("text").strip(),
                )
            )

        if not utterances:
            return None

        utterances.sort(key=lambda u: u.start_ms)
        infer_end_times(utterances)

        return ParsedTranscript(
            format_id=self.format_id,
            format_name=self.format_name,
            utterances=utterances,
            metadata={"line_count": len(utterances)},
        )