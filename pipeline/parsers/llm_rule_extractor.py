"""pipeline/parsers/llm_rule_extractor.py

Main entry-point for the automated policy parsing pipeline.

Flow:
  PDF → PDFTextExtractor → sections
      → LLM (Gemini) or heuristic fallback → raw rules dict
      → schema validation
      → FaithfulnessValidator (sentence-transformers, threshold=0.85)
      → auto_generated_rules.json

Usage:
  python -m pipeline.parsers.llm_rule_extractor
  python -m pipeline.parsers.llm_rule_extractor --pdf path/to/manual.pdf --output path/to/out.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.parsers.pdf_extractor import PDFTextExtractor
from pipeline.parsers.validator import FaithfulnessValidator, SIMILARITY_THRESHOLD

# Default output path (read by src/config.py)
DEFAULT_OUTPUT = _ROOT / "src" / "severity" / "auto_generated_rules.json"
DEFAULT_PDF    = _ROOT / "Compliance_Policy_Manual.pdf"

# ---------------------------------------------------------------------------
# Prompts (identical to parser/prompts.py — kept local to this module)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a highly analytical EHS compliance parsing assistant.
Your task is to parse sections of a factory compliance manual and extract
structured behavioral rules, safety signals, severity mappings, and escalation logic.

You must output a single valid JSON object. Do not include any markdown or
code fences. Strictly follow the schema below.

Schema:
{
  "<behavior_class_name>": {
    "description": "...",
    "observable_indicator": "...",
    "detection_approach": "...",
    "default_severity": "MEDIUM",   // LOW | MEDIUM | HIGH | CRITICAL
    "default_zone": "Production_Floor",
    "default_bounding_box": [120, 180, 360, 720],
    "label_confidence": 0.85,
    "policy_section": "Section X.Y.Z",
    "policy_signal": "WARNING",     // exact callout text from manual
    "tier_justification": "...",
    "threshold_values": {           // numeric thresholds extracted from policy
      "max_blocks": 2,
      "min_green_ratio": 0.05,
      "proximity_meters": 1.0,
      "duration_seconds": 300
    },
    "default_context": { ... },
    "escalation_rules": [
      {
        "condition": "person_proximity_to_machinery < 1.0",
        "new_severity": "HIGH",
        "rationale": "..."
      }
    ]
  }
}

Severity mapping rules (MANDATORY):
  - "WARNING" callout          → default_severity = "MEDIUM"
  - "CRITICAL SAFETY NOTICE"   → default_severity = "HIGH"
  - Immediate life-safety risk → default_severity = "CRITICAL"

Behavior keys MUST be exactly:
  Safe_Walkway_Violation
  Unauthorized_Intervention
  Opened_Panel_Cover
  Carrying_Overload_with_Forklift
"""

EXTRACTION_PROMPT = """\
Analyze the policy text below and extract all four safety behavior rules.

Policy text:
---
{text}
---

Rules to extract:
1. Safe_Walkway_Violation    — pedestrian outside green walkway lines
2. Unauthorized_Intervention — person without authorization vest near equipment
3. Opened_Panel_Cover        — electrical/machine panel left open
4. Carrying_Overload_with_Forklift — forklift carrying > allowed block count

Requirements:
- Map WARNING callouts → MEDIUM severity.
- Map CRITICAL SAFETY NOTICE callouts → HIGH severity.
- Extract numeric threshold_values (block limits, proximity distances, durations).
- observable_indicator must quote exact visual cues from the policy text.
- Output raw JSON only. No markdown.
"""

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

REQUIRED_BEHAVIORS = {
    "Safe_Walkway_Violation",
    "Unauthorized_Intervention",
    "Opened_Panel_Cover",
    "Carrying_Overload_with_Forklift",
}

REQUIRED_FIELDS = {
    "description", "observable_indicator", "detection_approach",
    "default_severity", "default_zone", "default_bounding_box",
    "label_confidence", "policy_section", "policy_signal",
    "tier_justification", "default_context", "escalation_rules",
}

VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def validate_schema(rules: dict[str, Any]) -> None:
    """Raise ValueError if rules do not conform to the expected schema."""
    missing = REQUIRED_BEHAVIORS - set(rules.keys())
    if missing:
        raise ValueError(f"Schema error: missing behaviors: {missing}")

    for behavior, config in rules.items():
        missing_fields = REQUIRED_FIELDS - set(config.keys())
        if missing_fields:
            raise ValueError(
                f"Schema error: '{behavior}' missing fields: {missing_fields}"
            )
        sev = config["default_severity"]
        if sev not in VALID_SEVERITIES:
            raise ValueError(
                f"Schema error: '{behavior}' has invalid severity: {sev}"
            )
        for esc in config.get("escalation_rules", []):
            if not all(k in esc for k in ("condition", "new_severity", "rationale")):
                raise ValueError(
                    f"Schema error: '{behavior}' has malformed escalation rule"
                )
            if esc["new_severity"] not in VALID_SEVERITIES:
                raise ValueError(
                    f"Schema error: '{behavior}' escalation has invalid severity"
                )


# ---------------------------------------------------------------------------
# LLM extraction (Gemini)
# ---------------------------------------------------------------------------

def _run_llm_extraction(sections: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Send relevant PDF sections to Gemini and return parsed rules."""
    import google.generativeai as genai

    print("[extractor] Initialising Gemini client…")
    genai.configure(api_key=api_key)

    keywords = [
        "ppe", "standard", "pedestrian", "walkway", "electrical",
        "panel", "material", "handling", "forklift", "machinery", "intervention",
    ]
    chunks: list[str] = []
    for heading, sec in sections.items():
        content = sec.get("content", str(sec)) if isinstance(sec, dict) else str(sec)
        if any(kw in heading.lower() or kw in content.lower() for kw in keywords):
            chunks.append(f"=== {heading} ===\n{content}\n")

    full_text = "\n".join(chunks) or "\n".join(
        sec.get("content", str(sec)) if isinstance(sec, dict) else str(sec)
        for sec in sections.values()
    )

    prompt = EXTRACTION_PROMPT.format(text=full_text)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    print("[extractor] Calling Gemini…")
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    return json.loads(response.text.strip())


# ---------------------------------------------------------------------------
# Heuristic fallback extraction
# ---------------------------------------------------------------------------

_SEC_REF_RE = re.compile(r"Section\s+\d+(?:\.\d+){0,3}", re.IGNORECASE)
_CALLOUT_RE = re.compile(r"\b(WARNING|CRITICAL\s+SAFETY\s+NOTICE)\b", re.IGNORECASE)


def _first_section_ref(sections: dict[str, Any], *keywords: str) -> str:
    """Find the first section reference in sections matching any keyword."""
    for heading, sec in sections.items():
        content = sec.get("content", str(sec)) if isinstance(sec, dict) else str(sec)
        if any(kw in heading.lower() or kw in content.lower() for kw in keywords):
            m = _SEC_REF_RE.search(heading) or _SEC_REF_RE.search(content)
            if m:
                return m.group(0)
    return ""


def _first_callout(sections: dict[str, Any], *keywords: str) -> str:
    """Return 'WARNING' or 'CRITICAL SAFETY NOTICE' found in matching sections."""
    for heading, sec in sections.items():
        content = sec.get("content", str(sec)) if isinstance(sec, dict) else str(sec)
        if any(kw in heading.lower() or kw in content.lower() for kw in keywords):
            m = _CALLOUT_RE.search(content)
            if m:
                return m.group(1).upper()
    return "WARNING"


def _signal_to_severity(signal: str) -> str:
    sig = signal.upper()
    if "CRITICAL" in sig:
        return "HIGH"
    return "MEDIUM"


def _run_heuristic_extraction(sections: dict[str, Any]) -> dict[str, Any]:
    """Regex-based fallback when no LLM API key is available."""
    print("[extractor] Running heuristic fallback (no GOOGLE_API_KEY found)…")

    walkway_ref    = _first_section_ref(sections, "pedestrian", "walkway")     or "Section 3.3.2"
    walkway_signal = _first_callout(sections, "pedestrian", "walkway")         or "WARNING"

    inter_ref    = _first_section_ref(sections, "intervention", "machinery", "vest") or "Section 4.3.2"
    inter_signal = _first_callout(sections, "intervention", "machinery")             or "CRITICAL SAFETY NOTICE"

    panel_ref    = _first_section_ref(sections, "electrical", "panel")  or "Section 5.2.2"
    panel_signal = _first_callout(sections, "electrical", "panel")      or "WARNING"

    fork_ref    = _first_section_ref(sections, "forklift", "handling", "overload") or "Section 6.3.2"
    fork_signal = _first_callout(sections, "forklift", "handling")                  or "CRITICAL SAFETY NOTICE"

    return {
        "Safe_Walkway_Violation": {
            "description": "Person detected outside green-marked designated safe walkway boundaries.",
            "observable_indicator": "Person position beyond green walkway boundary; feet not overlapping green floor markings.",
            "detection_approach": "YOLO person detection plus HSV green floor polygon overlap check.",
            "default_severity": _signal_to_severity(walkway_signal),
            "default_zone": "Production_Floor",
            "default_bounding_box": [120, 180, 360, 720],
            "label_confidence": 0.85,
            "policy_section": walkway_ref,
            "policy_signal": walkway_signal,
            "tier_justification": (
                "Walkway breaches placed under a 'WARNING' callout in the policy manual. "
                "Default MEDIUM; escalates to HIGH when proximity to machinery < 1.0 m."
            ),
            "threshold_values": {
                "min_green_ratio": 0.05,
                "proximity_meters": 1.0,
            },
            "default_context": {
                "person_proximity_to_machinery": 1.5,
                "forklift_operating": False,
                "personnel_count": 1,
            },
            "escalation_rules": [
                {
                    "condition": "person_proximity_to_machinery < 1.0",
                    "new_severity": "HIGH",
                    "rationale": "Pedestrian within one metre of active machinery.",
                },
                {
                    "condition": "forklift_operating == true",
                    "new_severity": "HIGH",
                    "rationale": "Walkway breach concurrent with active forklift operation.",
                },
            ],
        },
        "Unauthorized_Intervention": {
            "description": "Personnel interacting with equipment without an authorisation safety vest.",
            "observable_indicator": "Torso area lacking green safety vest; hands in proximity to operating equipment.",
            "detection_approach": (
                "YOLO person detection, upper-torso crop, HSV green pixel ratio check, "
                "machine proximity tracking."
            ),
            "default_severity": _signal_to_severity(inter_signal),
            "default_zone": "Equipment_Area",
            "default_bounding_box": [420, 150, 760, 690],
            "label_confidence": 0.85,
            "policy_section": inter_ref,
            "policy_signal": inter_signal,
            "tier_justification": (
                "Unauthorized interventions are under a 'CRITICAL SAFETY NOTICE' in the policy. "
                "Default HIGH; escalates to CRITICAL when multiple personnel are present."
            ),
            "threshold_values": {
                "min_vest_green_ratio": 0.15,
                "proximity_pixels": 50,
            },
            "default_context": {
                "personnel_count": 1,
                "equipment_active": True,
            },
            "escalation_rules": [
                {
                    "condition": "personnel_count > 1",
                    "new_severity": "CRITICAL",
                    "rationale": "Multiple unauthorized workers compound the machinery safety hazard.",
                },
            ],
        },
        "Opened_Panel_Cover": {
            "description": "Electrical panel cover left open exposing dangerous internal circuitry during operations.",
            "observable_indicator": "Panel door visible in open position; hinge angle > 20 degrees or interior circuitry visible.",
            "detection_approach": (
                "Edge-density aspect-ratio check on panel region; "
                "binary classifier (open/closed) using ResNet-18 or template matching."
            ),
            "default_severity": _signal_to_severity(panel_signal),
            "default_zone": "Electrical_Panel",
            "default_bounding_box": [780, 120, 1040, 620],
            "label_confidence": 0.85,
            "policy_section": panel_ref,
            "policy_signal": panel_signal,
            "tier_justification": (
                "Open panel placed under a 'WARNING' callout. Default MEDIUM; "
                "escalates to HIGH after 5 minutes or when personnel within 1.0 m."
            ),
            "threshold_values": {
                "max_open_seconds": 300,
                "proximity_meters": 1.0,
                "edge_density_threshold": 0.3,
            },
            "default_context": {
                "duration_open": 60,
                "person_proximity_to_panel": 2.0,
            },
            "escalation_rules": [
                {
                    "condition": "duration_open > 300",
                    "new_severity": "HIGH",
                    "rationale": "High-voltage cabinet left open for over five minutes.",
                },
                {
                    "condition": "person_proximity_to_panel < 1.0",
                    "new_severity": "HIGH",
                    "rationale": "Unprotected person within touching distance of open electrical panel.",
                },
            ],
        },
        "Carrying_Overload_with_Forklift": {
            "description": "Forklift carrying more than the permitted number of stacked blocks.",
            "observable_indicator": "Block or pallet count on forklift forks is three or more.",
            "detection_approach": (
                "YOLO truck/forklift detection and contour counter on fork region; "
                "block stacking geometry analysis."
            ),
            "default_severity": _signal_to_severity(fork_signal),
            "default_zone": "Loading_Area",
            "default_bounding_box": [300, 260, 980, 760],
            "label_confidence": 0.85,
            "policy_section": fork_ref,
            "policy_signal": fork_signal,
            "tier_justification": (
                "Forklift overloading is under a 'CRITICAL SAFETY NOTICE'. "
                "Default HIGH; elevated to CRITICAL immediately due to tip-over risk."
            ),
            "threshold_values": {
                "max_blocks": 2,
            },
            "default_context": {
                "block_count": 3,
                "forklift_operating": True,
                "personnel_count": 1,
            },
            "escalation_rules": [],
        },
    }


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def generate_rules(
    pdf_path: Path,
    output_path: Path,
    skip_validation: bool = False,
    validation_threshold: float = SIMILARITY_THRESHOLD,
) -> dict[str, Any]:
    """Full pipeline: PDF → LLM/heuristic → validate → write JSON."""

    # 1. Extract sections from PDF
    extractor = PDFTextExtractor(pdf_path)
    sections  = extractor.extract_sections()

    # Convert PolicySection objects to plain dicts for downstream use
    sections_dict = {
        heading: {
            "content":     sec.content,
            "callouts":    sec.callouts,
            "section_ref": sec.section_ref,
        }
        for heading, sec in sections.items()
    }

    # 2. LLM extraction or heuristic fallback
    api_key = os.getenv("GOOGLE_API_KEY")
    rules: dict[str, Any] | None = None
    if api_key:
        try:
            rules = _run_llm_extraction(sections_dict, api_key)
            print("[extractor] LLM extraction succeeded.")
        except Exception as exc:
            print(f"[extractor] LLM failed ({exc}). Falling back to heuristics.")
    if rules is None:
        rules = _run_heuristic_extraction(sections_dict)

    # 3. Schema validation
    print("[extractor] Validating schema…")
    validate_schema(rules)
    print("[extractor] Schema OK.")

    # 4. Faithfulness validation (sentence-transformers)
    if not skip_validation:
        print("[extractor] Running faithfulness validation (sentence-transformers)…")
        try:
            validator = FaithfulnessValidator(threshold=validation_threshold)
            results   = validator.validate_all(rules, sections_dict, raise_on_failure=True)
            print("\n--- Faithfulness Validation Results ---")
            for r in results:
                status = "✅ PASS" if r["valid"] else "❌ FAIL"
                print(
                    f"  {status} {r['behavior']}: "
                    f"indicator={r['indicator_similarity']:.4f}, "
                    f"description={r['description_similarity']:.4f}"
                )
        except ImportError:
            print(
                "[extractor] WARNING: sentence-transformers not installed. "
                "Skipping faithfulness check. Install with: pip install sentence-transformers"
            )
    else:
        print("[extractor] Faithfulness validation skipped (--skip-validation flag).")

    # 5. Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(rules, fh, indent=2)
    print(f"\n[extractor] ✅ Rules written to: {output_path}")

    return rules


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Generate auto_generated_rules.json from the EHS PDF policy."
    )
    parser.add_argument(
        "--pdf",
        default=str(DEFAULT_PDF),
        help="Path to the compliance policy PDF.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Destination path for auto_generated_rules.json.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip sentence-transformers faithfulness check (useful if library unavailable).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SIMILARITY_THRESHOLD,
        help=f"Cosine similarity threshold for faithfulness check (default: {SIMILARITY_THRESHOLD}).",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        # Auto-generate the PDF from the generator script if missing
        print(f"[extractor] PDF not found at {pdf_path}. Attempting to generate…")
        try:
            gen_script = _ROOT / "scripts" / "generate_policy_pdf.py"
            if gen_script.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("gen", gen_script)
                mod  = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                mod.generate_pdf(pdf_path)
            else:
                print("[extractor] Generator script not found. Provide --pdf manually.")
                sys.exit(1)
        except Exception as exc:
            print(f"[extractor] Could not generate PDF: {exc}")
            sys.exit(1)

    generate_rules(
        pdf_path=pdf_path,
        output_path=Path(args.output),
        skip_validation=args.skip_validation,
        validation_threshold=args.threshold,
    )


if __name__ == "__main__":
    _cli()
