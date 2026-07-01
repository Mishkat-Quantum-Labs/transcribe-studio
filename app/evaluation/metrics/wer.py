"""
Word Error Rate (WER) metric implementation.

WER = (S + D + I) / N

Where:
- S = Substitutions (word changed)
- D = Deletions (word missing in hypothesis)
- I = Insertions (extra word in hypothesis)
- N = Total words in reference
"""
from typing import Optional

from app.evaluation.metrics.base import BaseMetric, MetricResult
from app.evaluation.normalizers.base import BaseNormalizer


class WordErrorRate(BaseMetric):
    """
    Word Error Rate metric.

    WER measures the edit distance between reference and hypothesis at word level.
    Score is 0-1 where 0 = perfect match, 1 = completely different.
    """

    name = "wer"
    score_direction = "lower_is_better"

    def __init__(
        self,
        normalizer: Optional[BaseNormalizer] = None,
        case_sensitive: bool = False,
    ):
        self.normalizer = normalizer
        self.case_sensitive = case_sensitive

    def compute(
        self,
        reference: str,
        hypothesis: str,
        **kwargs,
    ) -> MetricResult:
        """
        Compute WER between reference and hypothesis.

        Args:
            reference: Reference text (human transcription)
            hypothesis: Hypothesis text (LLM output)
            **kwargs: Additional params (normalizer override)

        Returns:
            MetricResult with WER score
        """
        normalizer = kwargs.get("normalizer", self.normalizer)

        # Normalize texts
        if normalizer:
            ref_result = normalizer.normalize(reference)
            hyp_result = normalizer.normalize(hypothesis)
            ref_normalized = ref_result.text
            hyp_normalized = hyp_result.text
        else:
            ref_normalized = reference.strip()
            hyp_normalized = hypothesis.strip()
            if not self.case_sensitive:
                ref_normalized = ref_normalized.lower()
                hyp_normalized = hyp_normalized.lower()

        # Tokenize
        if normalizer:
            ref_tokens = normalizer.tokenize(ref_normalized)
            hyp_tokens = normalizer.tokenize(hyp_normalized)
        else:
            ref_tokens = ref_normalized.split()
            hyp_tokens = hyp_normalized.split()

        # Handle empty cases
        if not ref_tokens and not hyp_tokens:
            return MetricResult(
                score=0.0,
                raw_score=0.0,
                details={
                    "wer": 0.0,
                    "substitutions": 0,
                    "deletions": 0,
                    "insertions": 0,
                    "reference_words": 0,
                    "hypothesis_words": 0,
                    "reference_normalized": ref_normalized,
                    "hypothesis_normalized": hyp_normalized,
                },
            )

        if not ref_tokens:
            return MetricResult(
                score=1.0,
                raw_score=1.0,
                details={
                    "wer": 1.0,
                    "substitutions": 0,
                    "deletions": 0,
                    "insertions": len(hyp_tokens),
                    "reference_words": 0,
                    "hypothesis_words": len(hyp_tokens),
                    "reference_normalized": ref_normalized,
                    "hypothesis_normalized": hyp_normalized,
                },
            )

        # Compute edit distance (Levenshtein at word level)
        s, d, i = self._word_edit_distance(ref_tokens, hyp_tokens)
        n = len(ref_tokens)

        # WER calculation
        wer = (s + d + i) / n if n > 0 else 0.0
        wer = min(1.0, wer)  # Cap at 1.0

        # Score: 1 - WER (so higher is better)
        score = 1.0 - wer

        return MetricResult(
            score=score,
            raw_score=wer,
            details={
                "wer": wer,
                "accuracy": score,
                "substitutions": s,
                "deletions": d,
                "insertions": i,
                "correct": n - s - d,
                "reference_words": n,
                "hypothesis_words": len(hyp_tokens),
                "reference_normalized": ref_normalized,
                "hypothesis_normalized": hyp_normalized,
            },
        )

    def _word_edit_distance(
        self,
        ref: list[str],
        hyp: list[str],
    ) -> tuple[int, int, int]:
        """
        Compute word-level edit distance using dynamic programming.

        Returns:
            (substitutions, deletions, insertions)
        """
        n = len(ref)
        m = len(hyp)

        # dp[i][j] = min cost to transform ref[0:i] to hyp[0:j]
        dp = [[0] * (m + 1) for _ in range(n + 1)]

        # Initialize base cases
        for i in range(n + 1):
            dp[i][0] = i  # Delete all i words
        for j in range(m + 1):
            dp[0][j] = j  # Insert all j words

        # Fill the table
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if ref[i - 1] == hyp[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]  # Match - no cost
                else:
                    # Substitution cost = 1
                    dp[i][j] = min(
                        dp[i - 1][j - 1] + 1,  # Substitute
                        dp[i - 1][j] + 1,  # Delete from ref
                        dp[i][j - 1] + 1,  # Insert into hyp
                    )

        # Backtrack to count operations
        s, d, i = 0, 0, 0
        i_idx, j_idx = n, m

        while i_idx > 0 or j_idx > 0:
            if i_idx > 0 and j_idx > 0 and ref[i_idx - 1] == hyp[j_idx - 1]:
                i_idx -= 1
                j_idx -= 1
            elif i_idx > 0 and j_idx > 0 and dp[i_idx][j_idx] == dp[i_idx - 1][j_idx - 1] + 1:
                s += 1
                i_idx -= 1
                j_idx -= 1
            elif i_idx > 0 and dp[i_idx][j_idx] == dp[i_idx - 1][j_idx] + 1:
                d += 1
                i_idx -= 1
            elif j_idx > 0:
                i += 1
                j_idx -= 1
            else:
                break

        return s, d, i
