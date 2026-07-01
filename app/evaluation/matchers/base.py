"""
Base matcher interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SemanticMatch:
    """A semantic match found between reference and hypothesis."""
    reference_span: str
    hypothesis_span: str
    canonical_form: str
    weight: float  # 0-1, confidence of equivalence
    match_type: str  # e.g., "contraction", "paraphrase", "number"
    position_ref: tuple[int, int]  # (start_idx, end_idx) in reference
    position_hyp: tuple[int, int]  # (start_idx, end_idx) in hypothesis


class BaseMatcher(ABC):
    """Abstract base class for semantic matchers."""

    name: str = "base_matcher"

    @abstractmethod
    def find_matches(
        self,
        reference: str,
        hypothesis: str,
        **kwargs,
    ) -> list[SemanticMatch]:
        """
        Find semantic matches between reference and hypothesis.

        Args:
            reference: Reference text (human transcription)
            hypothesis: Hypothesis text (LLM output)
            **kwargs: Additional parameters

        Returns:
            List of SemanticMatch objects
        """
        pass
