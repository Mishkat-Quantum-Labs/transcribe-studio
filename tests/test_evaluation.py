"""Tests for the modular evaluation pipeline."""

from app.evaluation.engine import EvaluationEngine
from app.evaluation.metrics.wer import WordErrorRate
from app.evaluation.matchers.semantic import SemanticMatcher
from app.evaluation.config import get_config, reload_config
from app.transcript_formats import parse_transcript


def test_import_evaluation_package():
    import app.evaluation as evaluation

    assert evaluation.EvaluationEngine is not None
    assert evaluation.get_config is not None


def test_strict_wer_exact_match():
    metric = WordErrorRate()
    result = metric.compute("hello world", "hello world")
    assert result.raw_score == 0.0


def test_strict_wer_mismatch():
    metric = WordErrorRate()
    result = metric.compute("hello world", "hello there")
    assert result.raw_score > 0.0


def test_semantic_canonicalize_gonna():
    reload_config()
    engine = EvaluationEngine()
    matcher = engine.get_semantic_matcher("en")

    ref = matcher.canonicalize("i am gonna leave")
    hyp = matcher.canonicalize("I am going to leave")
    assert ref == hyp


def test_semantic_wer_gonna_vs_going_to():
    reload_config()
    engine = EvaluationEngine()
    result = engine.evaluate_segment(
        segment_id=1,
        start_ms=0,
        end_ms=5000,
        reference_text="i am gonna do it",
        hypothesis_text="I am going to do it",
        language="en",
    )
    assert result.wer > 0.0
    assert result.semantic_wer == 0.0
    assert result.semantic_score == 1.0


def test_parse_llm_transcript_by_id_and_start_ms():
    content = """
    {
      "segments": [
        {"id": 3, "text": "by id"},
        {"start_ms": 12000, "end_ms": 15000, "text": "by time"}
      ]
    }
    """
    parsed = parse_transcript(content, filename="out.json")
    assert parsed.by_id[3] == "by id"
    assert parsed.by_start_ms[12000] == "by time"
    assert parsed.full is None


def test_parse_plain_text_transcript():
    parsed = parse_transcript("Full LLM output here.", filename="llm.txt")
    assert parsed.format_id == "plain_text"
    assert parsed.full == "Full LLM output here."


def test_english_config_loads_semantic_rules():
    cfg = reload_config()
    en = cfg.get_language_config("en")
    assert en.code == "en"
    assert len(en.semantic_matchers) > 0
    assert any(g.name == "contractions_informal" for g in en.semantic_matchers)