"""
English language normalizer.
"""
import re
from typing import Optional

from app.evaluation.normalizers.base import BaseNormalizer, NormalizationResult


class EnglishNormalizer(BaseNormalizer):
    """
    English text normalizer with configurable rules.

    Handles:
    - Quotation normalization (smart quotes → straight)
    - Whitespace normalization
    - Optional punctuation removal
    - Contraction expansion
    """

    # Smart/curly quotes → straight quotes
    SMART_QUOTE_MAP = {
        "\u2018": "'",  # '
        "\u2019": "'",  # '
        "\u201c": '"',  # "
        "\u201d": '"',  # "
        "\u2013": "-",  # –
        "\u2014": "--",  # —
    }

    def __init__(
        self,
        lowercase: bool = True,
        trim_whitespace: bool = True,
        remove_punctuation: bool = False,
        normalize_quotes: bool = True,
        remove_special_chars: bool = False,
    ):
        self.lowercase = lowercase
        self.trim_whitespace = trim_whitespace
        self.remove_punctuation = remove_punctuation
        self.normalize_quotes = normalize_quotes
        self.remove_special_chars = remove_special_chars

    def normalize(self, text: str) -> NormalizationResult:
        """
        Normalize English text.

        Args:
            text: Input text

        Returns:
            NormalizationResult with normalized text
        """
        if not text:
            return NormalizationResult(text="")

        transformations = []
        removed_chars = []

        # Normalize smart quotes
        if self.normalize_quotes:
            for smart, straight in self.SMART_QUOTE_MAP.items():
                if smart in text:
                    transformations.append(f"'{smart}' → '{straight}'")
                    text = text.replace(smart, straight)

        # Normalize whitespace
        if self.trim_whitespace:
            original = text
            text = " ".join(text.split())  # Collapse multiple spaces
            if original != text:
                transformations.append("whitespace normalized")

        # Remove special characters
        if self.remove_special_chars:
            original = text
            text = re.sub(r"[^\w\s'-]", "", text)
            if original != text:
                removed = set(original) - set(text)
                removed_chars.extend(removed)

        # Remove punctuation
        if self.remove_punctuation:
            original = text
            text = re.sub(r"[^\w\s]", "", text)
            if original != text:
                removed = set(original) - set(text)
                removed_chars.extend(removed)

        # Lowercase
        if self.lowercase:
            text = text.lower()
            transformations.append("lowercased")

        return NormalizationResult(
            text=text,
            removed_chars=removed_chars,
            transformations=transformations,
        )

    def tokenize(self, text: str) -> list[str]:
        """
        Split English text into word tokens.

        Handles:
        - Contractions as single tokens (I'm, don't, etc.)
        - Hyphenated words
        - Apostrophes in words

        Args:
            text: Input text (should be normalized first)

        Returns:
            List of word tokens
        """
        if not text:
            return []

        # Split on whitespace first
        tokens = text.split()

        # Clean up tokens
        cleaned = []
        for token in tokens:
            # Strip leading/trailing punctuation (but keep hyphens and apostrophes)
            cleaned_token = token.strip(".,!?;:\"")
            if cleaned_token:
                cleaned.append(cleaned_token)

        return cleaned

    def word_tokenize(self, text: str) -> list[str]:
        """
        Alias for tokenize - split into words.
        """
        return self.tokenize(text)
