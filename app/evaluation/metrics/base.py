"""
Base metric interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    """Result of a metric computation."""
    score: float  # 0-1 scale (higher is better for some, lower for others)
    raw_score: Any  # Raw metric value (e.g., WER as percentage)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "raw_score": self.raw_score,
            "details": self.details,
        }


class BaseMetric(ABC):
    """
    Abstract base class for evaluation metrics.

    Metrics should implement:
    - compute(): Calculate the metric between two texts
    - score_direction: "higher_is_better" or "lower_is_better"
    """

    name: str = "base_metric"
    score_direction: str = "lower_is_better"  # or "higher_is_better"

    @abstractmethod
    def compute(
        self,
        reference: str,
        hypothesis: str,
        **kwargs,
    ) -> MetricResult:
        """
        Compute the metric between reference and hypothesis texts.

        Args:
            reference: Ground truth / human transcription
            hypothesis: System output / LLM transcription
            **kwargs: Additional parameters (language, normalizer, etc.)

        Returns:
            MetricResult with score and details
        """
        pass

    def normalize_score(self, result: MetricResult) -> MetricResult:
        """
        Normalize score to 0-1 scale where appropriate.
        Override in subclasses if needed.
        """
        return result
