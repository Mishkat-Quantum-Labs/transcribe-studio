"""
Base normalizer interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Result of text normalization."""
    text: str
    removed_chars: list[str] = None
    transformations: list[str] = None

    def __post_init__(self):
        if self.removed_chars is None:
            self.removed_chars = []
        if self.transformations is None:
            self.transformations = []


class BaseNormalizer(ABC):
    """Abstract base class for text normalizers."""

    @abstractmethod
    def normalize(self, text: str) -> NormalizationResult:
        """
        Normalize text according to language rules.

        Args:
            text: Input text to normalize

        Returns:
            NormalizationResult with normalized text and metadata
        """
        pass

    @abstractmethod
    def tokenize(self, text: str) -> list[str]:
        """
        Split text into tokens (words).

        Args:
            text: Input text

        Returns:
            List of word tokens
        """
        pass
