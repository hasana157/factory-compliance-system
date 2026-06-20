"""pipeline/parsers/validator.py

Faithfulness validator for extracted compliance rules.

For every rule, embeds the source PDF chunk and the extracted JSON
description/indicator using sentence-transformers (all-MiniLM-L6-v2).
Raises ValueError if cosine similarity < 0.85, preventing LLM hallucination.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Minimum acceptable cosine similarity between extracted rule text
# and the original PDF source chunk that the rule was derived from.
SIMILARITY_THRESHOLD = 0.85

# Behavior → section keyword mapping for finding the right source chunk.
BEHAVIOR_SECTION_KEYWORDS: dict[str, list[str]] = {
    "Safe_Walkway_Violation":          ["pedestrian", "walkway", "3.3", "4.2"],
    "Unauthorized_Intervention":       ["intervention", "machinery", "7.2", "4.3"],
    "Opened_Panel_Cover":              ["electrical", "panel", "5.2"],
    "Carrying_Overload_with_Forklift": ["forklift", "handling", "overload", "6.3"],
}


class FaithfulnessValidator:
    """Validate extracted rules against their PDF source using semantic similarity."""

    def __init__(self, threshold: float = SIMILARITY_THRESHOLD) -> None:
        self.threshold = threshold
        self._model = None  # lazy load

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_all(
        self,
        rules: dict[str, Any],
        sections: dict[str, Any],
        raise_on_failure: bool = True,
    ) -> list[dict[str, Any]]:
        """Validate every rule in *rules* against PDF *sections*.

        Parameters
        ----------
        rules:
            The auto-generated rules dict (behavior → rule dict).
        sections:
            The sections dict from PDFTextExtractor (heading → section info).
        raise_on_failure:
            If True (default), raise ValueError when similarity < threshold.

        Returns
        -------
        List of per-behavior validation results.
        """
        results: list[dict[str, Any]] = []
        for behavior, rule in rules.items():
            result = self._validate_one(behavior, rule, sections)
            results.append(result)
            if not result["valid"] and raise_on_failure:
                msg = (
                    f"[validator] FAITHFULNESS FAILURE — {behavior}\n"
                    f"  indicator similarity : {result['indicator_similarity']:.4f}\n"
                    f"  description similarity: {result['description_similarity']:.4f}\n"
                    f"  threshold            : {self.threshold}\n"
                    f"  Action: The LLM may have hallucinated. "
                    f"Review the extracted rule and re-run the parser."
                )
                logger.error(msg)
                raise ValueError(msg)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required: pip install sentence-transformers"
                ) from exc
            print("[validator] Loading sentence-transformers model (all-MiniLM-L6-v2)…")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _find_source_chunk(
        self, behavior: str, sections: dict[str, Any]
    ) -> str:
        """Return the most relevant PDF section text for *behavior*."""
        keywords = BEHAVIOR_SECTION_KEYWORDS.get(behavior, [])
        best_text = ""
        for heading, sec in sections.items():
            heading_lower = heading.lower()
            content = sec.get("content", sec) if isinstance(sec, dict) else str(sec)
            if any(kw in heading_lower or kw in content.lower() for kw in keywords):
                best_text += "\n" + content

        # Fallback: use all section text
        if not best_text:
            best_text = "\n".join(
                sec.get("content", str(sec)) if isinstance(sec, dict) else str(sec)
                for sec in sections.values()
            )
        return best_text.strip()

    def _validate_one(
        self,
        behavior: str,
        rule: dict[str, Any],
        sections: dict[str, Any],
    ) -> dict[str, Any]:
        source_text = self._find_source_chunk(behavior, sections)
        indicator = rule.get("observable_indicator", "")
        description = rule.get("description", "")

        if not source_text:
            logger.warning("[validator] No source chunk found for %s — skipping.", behavior)
            return {
                "behavior": behavior,
                "indicator_similarity": 0.0,
                "description_similarity": 0.0,
                "valid": False,
                "warning": "No source PDF chunk found",
            }

        model = self._get_model()
        embeddings = model.encode(
            [indicator, description, source_text],
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        ind_sim = float(self._cosine_numpy(embeddings[0], embeddings[2]))
        desc_sim = float(self._cosine_numpy(embeddings[1], embeddings[2]))

        valid = ind_sim >= self.threshold or desc_sim >= self.threshold

        result = {
            "behavior": behavior,
            "indicator_similarity": round(ind_sim, 4),
            "description_similarity": round(desc_sim, 4),
            "valid": valid,
        }
        return result

    @staticmethod
    def _cosine_numpy(a, b) -> float:  # type: ignore[override]
        import numpy as np
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def validate_rules(
    rules: dict[str, Any],
    sections: dict[str, Any],
    threshold: float = SIMILARITY_THRESHOLD,
    raise_on_failure: bool = True,
) -> list[dict[str, Any]]:
    """Module-level shorthand for FaithfulnessValidator.validate_all."""
    validator = FaithfulnessValidator(threshold=threshold)
    return validator.validate_all(rules, sections, raise_on_failure=raise_on_failure)
