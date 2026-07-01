"""
Semantic matcher - finds semantically equivalent phrases.

Handles cases like:
- "gonna" ↔ "going to"
- "I'm" ↔ "I am"
- "sort of" ↔ "sorta"
"""
import re
from typing import Optional

from app.evaluation.matchers.base import BaseMatcher, SemanticMatch
from app.evaluation.models import SemanticGroup, SemanticRule


class SemanticMatcher(BaseMatcher):
    """
    Configurable semantic matcher using rule-based phrase matching.

    Uses TOML-defined rules to find semantically equivalent expressions
    and give partial credit for near-matches.
    """

    name = "semantic"

    def __init__(
        self,
        rules: list[SemanticGroup] | None = None,
        normalizer=None,
    ):
        """
        Initialize semantic matcher with rules.

        Args:
            rules: List of SemanticGroup from config
            normalizer: Optional text normalizer
        """
        self.rules = rules or []
        self.normalizer = normalizer
        self._compiled_patterns: dict[str, re.Pattern] = {}

    def find_matches(
        self,
        reference: str,
        hypothesis: str,
        **kwargs,
    ) -> list[SemanticMatch]:
        """
        Find semantic matches between reference and hypothesis.

        Returns matches for phrases that are semantically equivalent
        even if they differ in exact wording.
        """
        matches = []

        # Normalize texts
        if self.normalizer:
            ref_norm = self.normalizer.normalize(reference).text
            hyp_norm = self.normalizer.normalize(hypothesis).text
        else:
            ref_norm = reference.lower().strip()
            hyp_norm = hypothesis.lower().strip()

        # Find matches for each enabled group
        for group in self.rules:
            if not group.enabled:
                continue

            for rule in group.rules:
                rule_matches = self._match_rule(
                    rule, ref_norm, hyp_norm, reference, hypothesis
                )
                matches.extend(rule_matches)

        return matches

    def _match_rule(
        self,
        rule: SemanticRule,
        ref_norm: str,
        hyp_norm: str,
        ref_original: str,
        hyp_original: str,
    ) -> list[SemanticMatch]:
        """Match a single semantic rule against both directions."""
        matches = []

        # Check each variant
        for variant in rule.variants:
            # Case 1: Reference uses variant, hypothesis uses canonical
            match = self._find_variant_in_text(
                variant,
                rule.canonical,
                ref_norm,
                hyp_norm,
                ref_original,
                hyp_original,
                rule.weight,
                f"{rule.variants[0]}_to_canonical",
            )
            if match:
                matches.append(match)

            # Case 2: Reference uses canonical, hypothesis uses variant
            match = self._find_variant_in_text(
                rule.canonical,
                variant,
                ref_norm,
                hyp_norm,
                ref_original,
                hyp_original,
                rule.weight,
                f"canonical_to_{variant}",
            )
            if match:
                matches.append(match)

            # Case 3: Both use different variants (variant1 ↔ variant2)
            for other_variant in rule.variants:
                if other_variant == variant:
                    continue
                match = self._find_variant_in_text(
                    variant,
                    other_variant,
                    ref_norm,
                    hyp_norm,
                    ref_original,
                    hyp_original,
                    rule.weight,
                    f"{variant}_to_{other_variant}",
                )
                if match:
                    matches.append(match)

        return matches

    def _find_variant_in_text(
        self,
        ref_variant: str,
        hyp_variant: str,
        ref_norm: str,
        hyp_norm: str,
        ref_original: str,
        hyp_original: str,
        weight: float,
        match_type: str,
    ) -> Optional[SemanticMatch]:
        """Find if ref_variant appears in reference and hyp_variant in hypothesis."""

        # Word boundary aware matching
        pattern_ref = r'\b' + re.escape(ref_variant) + r'\b'
        pattern_hyp = r'\b' + re.escape(hyp_variant) + r'\b'

        match_ref = re.search(pattern_ref, ref_norm, re.IGNORECASE)
        match_hyp = re.search(pattern_hyp, hyp_norm, re.IGNORECASE)

        if match_ref and match_hyp:
            return SemanticMatch(
                reference_span=ref_variant,
                hypothesis_span=hyp_variant,
                canonical_form=f"{ref_variant} ↔ {hyp_variant}",
                weight=weight,
                match_type=match_type,
                position_ref=(match_ref.start(), match_ref.end()),
                position_hyp=(match_hyp.start(), match_hyp.end()),
            )

        return None

    def compute_semantic_score(
        self,
        reference: str,
        hypothesis: str,
    ) -> tuple[float, list[SemanticMatch]]:
        """
        Compute semantic similarity score.

        Returns:
            Tuple of (score 0-1, list of matches found)
        """
        matches = self.find_matches(reference, hypothesis)

        if not matches:
            return 0.0, matches

        # Calculate weighted score based on matches
        # Higher weight = better match
        if not matches:
            return 0.0, []

        # Simple scoring: average weight of matches
        # But penalize for unmatched content
        total_weight = sum(m.weight for m in matches)
        match_count = len(matches)

        # Base score from matches
        avg_match_score = total_weight / match_count if match_count > 0 else 0

        # Normalize to 0-1 (this is simplified - could be more sophisticated)
        return avg_match_score, matches

    def canonicalize(self, text: str) -> str:
        """
        Replace known variants with canonical forms for semantic-aware WER.

        Example: "i am gonna leave" → "i am going to leave"
        """
        if not text:
            return ""

        if self.normalizer:
            text = self.normalizer.normalize(text).text
        else:
            text = text.lower().strip()

        replacements: list[tuple[str, str]] = []
        for group in self.rules:
            if not group.enabled:
                continue
            for rule in group.rules:
                if not rule.canonical:
                    continue
                for variant in rule.variants:
                    replacements.append((variant, rule.canonical))

        # Longest phrases first so "going to" wins over "going"
        replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

        for variant, canonical in replacements:
            pattern = r"\b" + re.escape(variant) + r"\b"
            text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)

        if self.normalizer:
            return self.normalizer.normalize(text).text
        return text.strip()

    def add_rule(self, rule: SemanticRule) -> None:
        """Add a rule dynamically."""
        # Create a default group if none exists
        if not self.rules:
            self.rules.append(
                SemanticGroup(name="dynamic", description="Dynamically added rules")
            )
        self.rules[-1].rules.append(rule)
