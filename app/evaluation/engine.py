"""
Main evaluation engine - orchestrates metrics, matchers, and normalizers.
"""
from typing import Optional

from app.evaluation.config import EvaluationConfig, get_config, NormalizationConfig
from app.evaluation.models import (
    AggregatedMetrics,
    EvaluationResult,
    SegmentResult,
)
from app.evaluation.metrics.wer import WordErrorRate
from app.evaluation.metrics.base import MetricResult
from app.evaluation.matchers.semantic import SemanticMatcher
from app.evaluation.normalizers.en import EnglishNormalizer


class EvaluationEngine:
    """
    Main evaluation engine.

    Orchestrates:
    - Text normalization
    - WER calculation
    - Semantic matching
    - Result aggregation
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        Initialize evaluation engine.

        Args:
            config: Evaluation configuration (loads from TOML if not provided)
        """
        self.config = config or get_config()

        # Initialize normalizer based on config
        norm_cfg = self.config.normalization
        self.normalizer = EnglishNormalizer(
            lowercase=norm_cfg.lowercase,
            trim_whitespace=norm_cfg.trim_whitespace,
            remove_punctuation=norm_cfg.remove_punctuation,
            normalize_quotes=norm_cfg.normalize_quotes,
            remove_special_chars=norm_cfg.remove_special_chars,
        )

        # Initialize metrics
        self.wer_metric = WordErrorRate(normalizer=self.normalizer)

        # Semantic matcher (initialized per-language)
        self._semantic_matchers: dict[str, SemanticMatcher] = {}

    def get_semantic_matcher(self, language: str = "en") -> SemanticMatcher:
        """Get or create semantic matcher for a language."""
        if language not in self._semantic_matchers:
            lang_cfg = self.config.get_language_config(language)
            self._semantic_matchers[language] = SemanticMatcher(
                rules=lang_cfg.semantic_matchers,
                normalizer=self.normalizer,
            )
        return self._semantic_matchers[language]

    def evaluate_segment(
        self,
        segment_id: int,
        start_ms: int,
        end_ms: int,
        reference_text: str,
        hypothesis_text: str,
        language: str = "en",
    ) -> SegmentResult:
        """
        Evaluate a single segment.

        Args:
            segment_id: Database ID of segment
            start_ms: Segment start time
            end_ms: Segment end time
            reference_text: Human transcription (reference)
            hypothesis_text: LLM transcription (hypothesis)
            language: Language code

        Returns:
            SegmentResult with all metrics
        """
        result = SegmentResult(
            segment_id=segment_id,
            start_ms=start_ms,
            end_ms=end_ms,
            reference_text=reference_text,
            hypothesis_text=hypothesis_text,
        )

        # Normalize texts
        ref_norm = self.normalizer.normalize(reference_text)
        hyp_norm = self.normalizer.normalize(hypothesis_text)
        result.reference_normalized = ref_norm.text
        result.hypothesis_normalized = hyp_norm.text

        # Check if we have content to evaluate
        has_ref = bool(ref_norm.text.strip())
        has_hyp = bool(hyp_norm.text.strip())

        semantic_matcher = self.get_semantic_matcher(language)

        # Strict WER (normalization only)
        wer_result = self.wer_metric.compute(reference_text, hypothesis_text)
        result.wer = wer_result.raw_score
        result.cer = 0.0
        result.correct_words = wer_result.details.get("correct", 0)
        result.substitutions = wer_result.details.get("substitutions", 0)
        result.deletions = wer_result.details.get("deletions", 0)
        result.insertions = wer_result.details.get("insertions", 0)
        result.total_reference_words = wer_result.details.get("reference_words", 0)

        # Semantic-aware WER (canonicalize informal speech, contractions, etc.)
        if has_ref and has_hyp:
            ref_canon = semantic_matcher.canonicalize(reference_text)
            hyp_canon = semantic_matcher.canonicalize(hypothesis_text)
            result.reference_canonical = ref_canon
            result.hypothesis_canonical = hyp_canon

            semantic_wer_result = self.wer_metric.compute(ref_canon, hyp_canon)
            result.semantic_wer = semantic_wer_result.raw_score
            result.semantic_score = 1.0 - result.semantic_wer

            semantic_matches = semantic_matcher.find_matches(
                reference_text, hypothesis_text
            )
            result.semantic_matches = [
                {
                    "ref": m.reference_span,
                    "hyp": m.hypothesis_span,
                    "canonical": m.canonical_form,
                    "weight": m.weight,
                    "type": m.match_type,
                }
                for m in semantic_matches
            ]
        elif has_ref and not has_hyp:
            result.semantic_wer = 1.0
            result.semantic_score = 0.0

        return result

    def evaluate_recording(
        self,
        recording_id: int,
        segments: list[dict],
        reference_key: str = "transcript",
        hypothesis_key: str = "llm_transcript",
        language: str = "en",
    ) -> EvaluationResult:
        """
        Evaluate all segments of a recording.

        Args:
            recording_id: Database ID of recording
            segments: List of segment dicts with transcript data
            reference_key: Key for human transcription in segments
            hypothesis_key: Key for LLM transcription in segments
            language: Language code

        Returns:
            EvaluationResult with all segment results and aggregation
        """
        result = EvaluationResult(
            recording_id=recording_id,
            language=language,
        )

        total_ref_words = 0
        total_correct = 0
        total_subs = 0
        total_dels = 0
        total_ins = 0
        total_semantic_wer_weighted = 0.0
        total_semantic_ref_words = 0
        total_semantic_score = 0.0
        evaluated_count = 0
        empty_ref_count = 0
        empty_hyp_count = 0

        for seg in segments:
            ref_text = seg.get(reference_key, "") or ""
            hyp_text = seg.get(hypothesis_key, "") or ""

            seg_result = self.evaluate_segment(
                segment_id=seg.get("id", 0),
                start_ms=seg.get("start_ms", 0),
                end_ms=seg.get("end_ms", 0),
                reference_text=ref_text,
                hypothesis_text=hyp_text,
                language=language,
            )
            result.segments.append(seg_result)

            # Aggregate stats
            total_ref_words += seg_result.total_reference_words
            total_correct += seg_result.correct_words
            total_subs += seg_result.substitutions
            total_dels += seg_result.deletions
            total_ins += seg_result.insertions
            total_semantic_score += seg_result.semantic_score
            if seg_result.total_reference_words > 0 and hyp_text.strip():
                total_semantic_wer_weighted += (
                    seg_result.semantic_wer * seg_result.total_reference_words
                )
                total_semantic_ref_words += seg_result.total_reference_words

            if ref_text.strip():
                if hyp_text.strip():
                    evaluated_count += 1
                else:
                    empty_hyp_count += 1
            else:
                empty_ref_count += 1

        # Calculate aggregated metrics
        agg = AggregatedMetrics()
        agg.total_segments = len(segments)
        agg.evaluated_segments = evaluated_count
        agg.empty_reference_segments = empty_ref_count
        agg.empty_hypothesis_segments = empty_hyp_count

        if total_ref_words > 0:
            agg.overall_wer = (total_subs + total_dels + total_ins) / total_ref_words
            agg.overall_wer = min(1.0, agg.overall_wer)

        agg.total_reference_words = total_ref_words
        agg.total_correct = total_correct
        agg.total_substitutions = total_subs
        agg.total_deletions = total_dels
        agg.total_insertions = total_ins

        if total_semantic_ref_words > 0:
            agg.overall_semantic_wer = min(
                1.0, total_semantic_wer_weighted / total_semantic_ref_words
            )
        if evaluated_count > 0:
            agg.overall_semantic_score = total_semantic_score / evaluated_count
        elif empty_ref_count == len(segments):
            agg.overall_semantic_score = 1.0

        result.aggregated = agg

        # Build summary for UI
        result.summary = self._build_summary(result)

        return result

    def _build_summary(self, result: EvaluationResult) -> dict:
        """Build human-readable summary."""
        agg = result.aggregated

        wer_pct = agg.overall_wer * 100
        semantic_wer_pct = agg.overall_semantic_wer * 100
        accuracy_pct = (1 - agg.overall_wer) * 100
        semantic_accuracy_pct = (1 - agg.overall_semantic_wer) * 100
        semantic_pct = agg.overall_semantic_score * 100

        # Quality tier uses semantic WER (fairer for classroom speech)
        if agg.overall_semantic_wer <= 0.05:
            quality = "excellent"
        elif agg.overall_semantic_wer <= 0.15:
            quality = "good"
        elif agg.overall_semantic_wer <= 0.30:
            quality = "fair"
        else:
            quality = "needs_review"

        return {
            "wer_percent": round(wer_pct, 1),
            "semantic_wer_percent": round(semantic_wer_pct, 1),
            "accuracy_percent": round(accuracy_pct, 1),
            "semantic_accuracy_percent": round(semantic_accuracy_pct, 1),
            "semantic_score_percent": round(semantic_pct, 1),
            "quality": quality,
            "total_segments": agg.total_segments,
            "evaluated_segments": agg.evaluated_segments,
            "total_words": agg.total_reference_words,
            "errors": {
                "substitutions": agg.total_substitutions,
                "deletions": agg.total_deletions,
                "insertions": agg.total_insertions,
                "total": agg.total_substitutions + agg.total_deletions + agg.total_insertions,
            },
        }
