"""
Data models for evaluation.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticRule:
    """A single semantic matching rule."""
    variants: list[str] = field(default_factory=list)
    canonical: str = ""
    weight: float = 1.0
    pattern: str = ""


@dataclass
class SemanticGroup:
    """A group of semantic rules."""
    name: str = ""
    description: str = ""
    enabled: bool = True
    rules: list[SemanticRule] = field(default_factory=list)


@dataclass
class SegmentResult:
    """Result for a single segment comparison."""
    segment_id: int
    start_ms: int
    end_ms: int
    reference_text: str
    hypothesis_text: str

    # Raw metrics
    wer: float = 0.0  # Strict WER after text normalization (0-1, lower is better)
    semantic_wer: float = 0.0  # WER after semantic canonicalization
    cer: float = 0.0  # Character Error Rate (0-1)

    # Semantic scoring
    semantic_score: float = 0.0  # 0-1, higher is better (1 - semantic_wer)
    semantic_matches: list[dict] = field(default_factory=list)

    # Normalized texts
    reference_normalized: str = ""
    hypothesis_normalized: str = ""
    reference_canonical: str = ""
    hypothesis_canonical: str = ""

    # Detailed breakdown
    correct_words: int = 0
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0
    total_reference_words: int = 0


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all segments."""
    overall_wer: float = 0.0
    overall_semantic_wer: float = 0.0
    overall_cer: float = 0.0
    overall_semantic_score: float = 0.0

    total_segments: int = 0
    evaluated_segments: int = 0
    empty_reference_segments: int = 0
    empty_hypothesis_segments: int = 0

    total_reference_words: int = 0
    total_correct: int = 0
    total_substitutions: int = 0
    total_deletions: int = 0
    total_insertions: int = 0

    # Weighted scores (if semantic weights are used)
    weighted_semantic_score: float = 0.0


@dataclass
class EvaluationResult:
    """Complete evaluation result for a recording."""
    recording_id: int
    language: str
    segments: list[SegmentResult] = field(default_factory=list)
    aggregated: AggregatedMetrics = field(default_factory=AggregatedMetrics)

    # Summary for UI
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recording_id": self.recording_id,
            "language": self.language,
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "start_ms": s.start_ms,
                    "end_ms": s.end_ms,
                    "wer": round(s.wer, 4),
                    "semantic_wer": round(s.semantic_wer, 4),
                    "cer": round(s.cer, 4),
                    "semantic_score": round(s.semantic_score, 4),
                    "semantic_matches": s.semantic_matches,
                    "reference": s.reference_text,
                    "hypothesis": s.hypothesis_text,
                    "reference_normalized": s.reference_normalized,
                    "hypothesis_normalized": s.hypothesis_normalized,
                    "reference_canonical": s.reference_canonical,
                    "hypothesis_canonical": s.hypothesis_canonical,
                    "correct": s.correct_words,
                    "substitutions": s.substitutions,
                    "deletions": s.deletions,
                    "insertions": s.insertions,
                }
                for s in self.segments
            ],
            "aggregated": {
                "wer": round(self.aggregated.overall_wer, 4),
                "semantic_wer": round(self.aggregated.overall_semantic_wer, 4),
                "cer": round(self.aggregated.overall_cer, 4),
                "semantic_score": round(self.aggregated.overall_semantic_score, 4),
                "total_segments": self.aggregated.total_segments,
                "evaluated_segments": self.aggregated.evaluated_segments,
                "total_words": self.aggregated.total_reference_words,
                "correct_words": self.aggregated.total_correct,
                "substitutions": self.aggregated.total_substitutions,
                "deletions": self.aggregated.total_deletions,
                "insertions": self.aggregated.total_insertions,
            },
            "summary": self.summary,
        }
