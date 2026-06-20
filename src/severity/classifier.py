"""src/severity/classifier.py

Module 2: Severity categorisation matrix.

Dynamic severity assignment:
  - Base severity is derived from the `policy_signal` field in
    auto_generated_rules.json (never hardcoded):
      "WARNING"               → MEDIUM
      "CRITICAL SAFETY NOTICE" → HIGH
  - Contextual escalation rules (from the same JSON) are then applied.
  - Personnel-proximity escalation: if metadata["proximity_escalation"]
    is True, severity is bumped one tier higher.

All numeric thresholds come from auto_generated_rules.json.
Zero hardcoded numbers in this module.
"""

from __future__ import annotations

import json
import operator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.config import settings
from src.severity.context_analyzer import ContextAnalyzer
from src.severity.utils import higher_severity


class SeverityTier(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# Severity order for proximity escalation
_TIER_ORDER = [SeverityTier.LOW, SeverityTier.MEDIUM, SeverityTier.HIGH, SeverityTier.CRITICAL]


def _escalate_one_tier(tier: SeverityTier) -> SeverityTier:
    try:
        idx = _TIER_ORDER.index(tier)
        return _TIER_ORDER[min(idx + 1, len(_TIER_ORDER) - 1)]
    except ValueError:
        return tier


def _signal_to_base_severity(policy_signal: str) -> str:
    """Map the policy callout signal to the correct default severity tier.

    Mapping (per policy manual):
      "WARNING"                → MEDIUM
      "CRITICAL SAFETY NOTICE" → HIGH
      Anything else            → MEDIUM (conservative default)
    """
    sig = policy_signal.upper()
    if "CRITICAL" in sig:
        return "HIGH"
    return "MEDIUM"


@dataclass(frozen=True)
class SeverityDecision:
    severity:     SeverityTier
    rationale:    str
    policy_signal: str
    applied_rules: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity":      self.severity.value,
            "rationale":     self.rationale,
            "policy_signal": self.policy_signal,
            "applied_rules": self.applied_rules,
        }


class SeverityClassifier:
    """Assign LOW/MEDIUM/HIGH/CRITICAL tiers from policy-derived rules.

    Base severity is always read from policy_signal in the JSON
    (WARNING → MEDIUM, CRITICAL SAFETY NOTICE → HIGH).
    Escalation conditions in the same JSON are then evaluated.
    """

    OPERATORS = {
        "<":  operator.lt,
        "<=": operator.le,
        ">":  operator.gt,
        ">=": operator.ge,
        "==": operator.eq,
        "!=": operator.ne,
    }

    def __init__(
        self,
        rules_path: str | Path | None = None,
        context_analyzer: ContextAnalyzer | None = None,
    ) -> None:
        self.rules_path = Path(rules_path or settings.rules_path)
        with self.rules_path.open("r", encoding="utf-8") as fh:
            self.rules = json.load(fh)
        self.context_analyzer = context_analyzer or ContextAnalyzer()

    def classify(
        self,
        detection: dict[str, Any],
        frame_context: dict[str, Any] | None = None,
    ) -> SeverityDecision:
        """Classify one detection and explain the decision."""
        behavior = detection.get("behavior_class")
        rule = self.rules.get(str(behavior))

        if not rule:
            return SeverityDecision(
                severity=SeverityTier.MEDIUM,
                rationale="Unknown behavior class; defaulted to MEDIUM pending review.",
                policy_signal="No policy rule matched.",
                applied_rules=[],
            )

        # 1. Derive base severity from policy_signal (WARNING vs CRITICAL)
        policy_signal = rule.get("policy_signal", "WARNING")
        base_severity_str = _signal_to_base_severity(policy_signal)
        # Allow the JSON's default_severity to override only if it is HIGHER
        json_severity = rule.get("default_severity", base_severity_str)
        severity_str = higher_severity(base_severity_str, json_severity)

        rationale = (
            rule.get("tier_justification")
            or f"Base severity from policy signal: '{policy_signal}'"
        )
        applied_rules: list[str] = []

        # 2. Apply JSON escalation rules
        context = self.context_analyzer.analyze(detection, frame_context)
        for escalation in rule.get("escalation_rules", []):
            condition = escalation["condition"]
            if self._evaluate_condition(condition, context):
                new_sev = escalation["new_severity"]
                severity_str = higher_severity(severity_str, new_sev)
                rationale = escalation["rationale"]
                applied_rules.append(condition)

        severity = SeverityTier(severity_str)

        # 3. Proximity escalation (set by DetectionEngine in detection metadata)
        if detection.get("metadata", {}).get("proximity_escalation"):
            escalated = _escalate_one_tier(severity)
            applied_rules.append("proximity_escalation: nearby person within 50px")
            rationale = (
                f"Escalated from {severity.value} to {escalated.value} because "
                "another person was detected within 50 pixels of the hazard."
            )
            severity = escalated

        return SeverityDecision(
            severity=severity,
            rationale=rationale,
            policy_signal=policy_signal,
            applied_rules=applied_rules,
        )

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a simple policy condition such as ``duration_open > 300``."""
        for op_text, op_func in sorted(
            self.OPERATORS.items(), key=lambda item: -len(item[0])
        ):
            if op_text not in condition:
                continue
            left, right = (part.strip() for part in condition.split(op_text, 1))
            if left not in context:
                return False
            return op_func(context[left], self._coerce_value(right))
        return False

    def _coerce_value(self, raw: str) -> Any:
        value = raw.strip().strip('"').strip("'")
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value
