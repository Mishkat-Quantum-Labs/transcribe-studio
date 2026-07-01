"""Shared models for transcript import/export."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Utterance:
    """A single time-stamped line of speech."""

    start_ms: int
    text: str
    speaker: str = ""
    end_ms: int | None = None

    def overlaps(self, seg_start: int, seg_end: int) -> bool:
        end = self.end_ms if self.end_ms is not None else self.start_ms + 1
        return self.start_ms < seg_end and end > seg_start


@dataclass
class ParsedTranscript:
    """
    Normalized output from any transcript parser.

    Parsers may populate one or more of:
    - utterances: time-aligned lines (best for chunk matching)
    - by_id: explicit segment id → text
    - by_start_ms: exact start_ms → text
    - full: one blob applied to every chunk
    """

    format_id: str
    format_name: str = ""
    utterances: list[Utterance] = field(default_factory=list)
    by_id: dict[int, str] = field(default_factory=dict)
    by_start_ms: dict[int, str] = field(default_factory=dict)
    full: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_segment_mapping(self) -> bool:
        return bool(self.utterances or self.by_id or self.by_start_ms or self.full)