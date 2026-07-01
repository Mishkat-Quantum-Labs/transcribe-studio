"""Tests for pluggable transcript format parsers."""

from app.transcript_formats import parse_transcript, parsed_to_segment_text
from app.transcript_formats.parsers.timestamp_speaker import parse_timestamp_to_ms

SAMPLE_TIMESTAMP_TRANSCRIPT = """\
[00:07] Teacher: At the beginning of the freshman year, we give students a diagnostic assessment.
[00:22] Teacher: To give my students the education they deserve, I need to have an attitude that says I'll do whatever it takes.
[07:23] Teacher: Okay, better. We'll get it.
[10:13] Teacher: I was a bad teacher my first year of teaching.
"""


def test_parse_timestamp_speaker_format():
    parsed = parse_transcript(SAMPLE_TIMESTAMP_TRANSCRIPT, filename="llm.txt")
    assert parsed.format_id == "timestamp_speaker"
    assert len(parsed.utterances) == 4
    assert parsed.utterances[0].start_ms == 7_000
    assert parsed.utterances[0].speaker == "Teacher"
    assert "freshman year" in parsed.utterances[0].text


def test_parse_timestamp_hh_mm_ss():
    assert parse_timestamp_to_ms("01:51") == 111_000
    assert parse_timestamp_to_ms("10:13") == 613_000
    assert parse_timestamp_to_ms("1:02:24") == 3_744_000


def test_align_utterances_to_30s_chunks():
    parsed = parse_transcript(SAMPLE_TIMESTAMP_TRANSCRIPT, filename="llm.txt")
    segments = [
        {"id": 1, "start_ms": 0, "end_ms": 30_000},
        {"id": 2, "start_ms": 30_000, "end_ms": 60_000},
        {"id": 3, "start_ms": 600_000, "end_ms": 630_000},
    ]
    mapping = parsed_to_segment_text(
        parsed, segments, duration_ms=630_000
    )

    assert 1 in mapping
    assert "freshman year" in mapping[1]
    assert "whatever it takes" in mapping[1]
    assert 3 in mapping
    assert "bad teacher" in mapping[3]


def test_json_segments_still_works():
    content = '{"segments": [{"id": 5, "text": "hello"}, {"start_ms": 12000, "text": "world"}]}'
    parsed = parse_transcript(content, filename="data.json")
    assert parsed.format_id == "json_segments"
    assert parsed.by_id[5] == "hello"
    assert parsed.by_start_ms[12000] == "world"


def test_auto_detect_timestamp_over_plain_text():
    parsed = parse_transcript(SAMPLE_TIMESTAMP_TRANSCRIPT, filename="notes.txt")
    assert parsed.format_id == "timestamp_speaker"


def test_accepted_upload_extensions_from_config():
    from app.transcript_formats.registry import accepted_upload_extensions

    exts = accepted_upload_extensions()
    assert ".json" in exts
    assert ".txt" in exts
    assert ".transcript" in exts