"""Align parsed utterances to recording chunks by time overlap."""

from app.transcript_formats.models import ParsedTranscript, Utterance


def align_utterances_to_segments(
    utterances: list[Utterance],
    segments: list[dict],
    *,
    include_speaker: bool = False,
) -> dict[int, str]:
    """
    Map each segment id → LLM text for utterances overlapping that chunk.

    Overlap rule: utterance.start_ms < seg.end_ms AND utterance.end_ms > seg.start_ms
    """
    result: dict[int, str] = {}

    for seg in segments:
        seg_id = int(seg["id"])
        seg_start = int(seg["start_ms"])
        seg_end = int(seg["end_ms"])

        parts: list[str] = []
        for utt in utterances:
            if not utt.overlaps(seg_start, seg_end):
                continue
            if include_speaker and utt.speaker:
                parts.append(f"{utt.speaker}: {utt.text}")
            else:
                parts.append(utt.text)

        if parts:
            result[seg_id] = " ".join(parts)

    return result


def parsed_to_segment_text(
    parsed: ParsedTranscript,
    segments: list[dict],
    *,
    duration_ms: int | None = None,
    include_speaker: bool = False,
) -> dict[int, str]:
    """
    Convert any ParsedTranscript into segment_id → text mapping.
    """
    if parsed.full:
        return {int(seg["id"]): parsed.full for seg in segments}

    mapping: dict[int, str] = {}

    for seg_id, text in parsed.by_id.items():
        mapping[int(seg_id)] = text

    for seg in segments:
        seg_id = int(seg["id"])
        if seg_id in mapping:
            continue
        start_ms = int(seg["start_ms"])
        if start_ms in parsed.by_start_ms:
            mapping[seg_id] = parsed.by_start_ms[start_ms]

    if parsed.utterances:
        utterances = list(parsed.utterances)
        if duration_ms:
            from app.transcript_formats.parsers.timestamp_speaker import infer_end_times

            infer_end_times(utterances, duration_ms)
        aligned = align_utterances_to_segments(
            utterances, segments, include_speaker=include_speaker
        )
        for seg_id, text in aligned.items():
            mapping.setdefault(seg_id, text)

    return mapping