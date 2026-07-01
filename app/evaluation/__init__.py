"""
Transcribe Studio Evaluation Module.

Provides WER, semantic matching, and extensible evaluation metrics
for comparing human transcriptions against LLM-generated transcripts.
"""
from app.evaluation.config import EvaluationConfig, get_config, reload_config
from app.evaluation.engine import EvaluationEngine
from app.evaluation.models import EvaluationResult, SegmentResult

__all__ = [
    "EvaluationEngine",
    "EvaluationConfig",
    "EvaluationResult",
    "SegmentResult",
    "get_config",
    "reload_config",
]
