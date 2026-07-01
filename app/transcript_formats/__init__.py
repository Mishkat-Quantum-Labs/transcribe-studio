"""
Pluggable transcript format parsers.

Add a new format:
1. Create app/transcript_formats/parsers/your_format.py
2. Register in registry.py _BUILTIN_PARSERS
3. Document in config/transcript_formats.toml
"""

from app.transcript_formats.align import align_utterances_to_segments, parsed_to_segment_text
from app.transcript_formats.models import ParsedTranscript, Utterance
from app.transcript_formats.registry import list_parsers, parse_transcript

__all__ = [
    "ParsedTranscript",
    "Utterance",
    "parse_transcript",
    "list_parsers",
    "parsed_to_segment_text",
    "align_utterances_to_segments",
]