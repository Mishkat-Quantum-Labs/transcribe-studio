"""Base parser interface."""

from abc import ABC, abstractmethod

from app.transcript_formats.models import ParsedTranscript


class BaseTranscriptParser(ABC):
    """Parse a transcript file into normalized ParsedTranscript."""

    format_id: str = "base"
    format_name: str = "Base"
    extensions: tuple[str, ...] = ()
    auto_detect_patterns: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, content: str, *, filename: str = "") -> ParsedTranscript | None:
        """
        Parse content. Return None if this parser cannot handle the input.
        """
        pass

    def can_handle(self, content: str, *, filename: str = "") -> bool:
        stripped = content.strip()
        if not stripped:
            return False

        if self.extensions and filename:
            from pathlib import Path

            ext = Path(filename).suffix.lower()
            if ext in self.extensions and self.auto_detect_patterns:
                import re

                return any(
                    re.search(pat, stripped, re.MULTILINE)
                    for pat in self.auto_detect_patterns
                )
            if ext in self.extensions and not self.auto_detect_patterns:
                return True

        if self.auto_detect_patterns:
            import re

            return any(
                re.search(pat, stripped, re.MULTILINE) for pat in self.auto_detect_patterns
            )

        return False