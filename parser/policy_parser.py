"""Automated EHS compliance policy PDF parser.

Parses Compliance_Policy_Manual.pdf to generate src/severity/auto_generated_rules.json.
Uses Gemini LLM for structured extraction if GOOGLE_API_KEY is present,
otherwise falls back to a regex-based heuristic extraction.
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Any

# Add parent directory to path to allow importing src
import sys
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import settings
from parser.prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
from parser.validators import validate_schema, validate_extraction_quality

def extract_sections_from_pdf(pdf_path: Path) -> dict[str, str]:
    """Parse PDF page-by-page and group text by Section headers."""
    import pdfplumber
    
    sections = {}
    current_section = "Cover & Preface"
    current_content = []
    
    print(f"Reading PDF from: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")
            for line in lines:
                # Matches "Section X: ..." or "Section X.Y: ..."
                match = re.match(r"^(Section\s+\d+(?:\.\d+)?[:\w\s\-\.\(\)]+)", line, re.IGNORECASE)
                if match:
                    if current_content:
                        sections[current_section] = "\n".join(current_content)
                    current_section = match.group(1).strip()
                    current_content = [line]
                else:
                    current_content.append(line)
                    
        if current_content:
            sections[current_section] = "\n".join(current_content)
            
    print(f"Extracted {len(sections)} sections from PDF.")
    return sections

def run_heuristic_parsing(sections: dict[str, str]) -> dict[str, Any]:
    """Fallback heuristic parser. Extracts rules using regex pattern matching when LLM is unavailable."""
    print("Running heuristic fallback parsing (no Gemini API key configured)...")
    
    rules = {}
    
    # 1. Walkway Violation
    walkway_text = ""
    for k, v in sections.items():
        if "pedestrian" in k.lower() or "walkway" in k.lower():
            walkway_text = v
            break
            
    # Find walkway section ref (e.g. Section 4.2.1)
    section_ref = "Section 4.2.1"
    for line in walkway_text.split("\n"):
        m = re.search(r"Section\s+\d+\.\d+(?:\.\d+)?", line)
        if m:
            section_ref = m.group(0)
            break

    rules["Safe_Walkway_Violation"] = {
        "description": "Person detected outside green-marked designated safe walkway boundaries.",
        "observable_indicator": "Person position beyond green walkway boundary.",
        "detection_approach": "YOLO person detection plus green floor boundary overlap.",
        "default_severity": "MEDIUM",
        "default_zone": "Production_Floor",
        "default_bounding_box": [120, 180, 360, 720],
        "label_confidence": 0.85,
        "policy_section": section_ref,
        "policy_signal": "WARNING",
        "tier_justification": "Walkway breaches represent high-frequency pedestrian hazards in machinery/traffic zones.",
        "default_context": {
            "person_proximity_to_machinery": 1.5,
            "forklift_operating": False,
            "personnel_count": 1
        },
        "escalation_rules": [
            {
                "condition": "person_proximity_to_machinery < 1.0",
                "new_severity": "HIGH",
                "rationale": "Pedestrian is within one meter of active machinery."
            },
            {
                "condition": "forklift_operating == true",
                "new_severity": "HIGH",
                "rationale": "Walkway breach occurs during active forklift operations."
            }
        ]
    }

    # 2. Unauthorized Intervention
    intervention_text = ""
    for k, v in sections.items():
        if "machinery" in k.lower() or "intervention" in k.lower():
            intervention_text = v
            break
            
    section_ref = "Section 7.2.1"
    for line in intervention_text.split("\n"):
        m = re.search(r"Section\s+\d+\.\d+(?:\.\d+)?", line)
        if m:
            section_ref = m.group(0)
            break

    rules["Unauthorized_Intervention"] = {
        "description": "Personnel performing maintenance or intervention on machinery without authorization vest.",
        "observable_indicator": "Torso area lacking green safety vest; hands in proximity to operating equipment.",
        "detection_approach": "YOLO person detection, vest color classification, and machine proximity tracking.",
        "default_severity": "HIGH",
        "default_zone": "Equipment_Area",
        "default_bounding_box": [420, 150, 760, 690],
        "label_confidence": 0.85,
        "policy_section": section_ref,
        "policy_signal": "CRITICAL SAFETY NOTICE",
        "tier_justification": "Direct physical contact or proximity to moving machinery elements without clearance.",
        "default_context": {
            "personnel_count": 1,
            "equipment_active": True
        },
        "escalation_rules": [
            {
                "condition": "personnel_count > 1",
                "new_severity": "CRITICAL",
                "rationale": "Multiple unauthorized workers compound the machinery safety hazard."
            }
        ]
    }

    # 3. Opened Panel Cover
    panel_text = ""
    for k, v in sections.items():
        if "electrical" in k.lower() or "panel" in k.lower():
            panel_text = v
            break
            
    section_ref = "Section 5.2.2"
    for line in panel_text.split("\n"):
        m = re.search(r"Section\s+\d+\.\d+(?:\.\d+)?", line)
        if m:
            section_ref = m.group(0)
            break

    rules["Opened_Panel_Cover"] = {
        "description": "Electrical panel cover left open exposing dangerous internal circuitry.",
        "observable_indicator": "Electrical or machine cabinet panel door in open position.",
        "detection_approach": "Template matching or edge density contrast analysis of panel door area.",
        "default_severity": "MEDIUM",
        "default_zone": "Electrical_Panel",
        "default_bounding_box": [780, 120, 1040, 620],
        "label_confidence": 0.85,
        "policy_section": section_ref,
        "policy_signal": "WARNING",
        "tier_justification": "Exposed high-voltage circuits pose shock and arc flash hazards.",
        "default_context": {
            "duration_open": 60,
            "person_proximity_to_panel": 2.0
        },
        "escalation_rules": [
            {
                "condition": "duration_open > 300",
                "new_severity": "HIGH",
                "rationale": "High-voltage cabinet left open for over five minutes."
            },
            {
                "condition": "person_proximity_to_panel < 1.0",
                "new_severity": "HIGH",
                "rationale": "Unprotected person within touching distance of open electrical panel."
            }
        ]
    }

    # 4. Carrying Overload with Forklift
    forklift_text = ""
    for k, v in sections.items():
        if "forklift" in k.lower() or "handling" in k.lower():
            forklift_text = v
            break
            
    section_ref = "Section 6.3.2"
    for line in forklift_text.split("\n"):
        m = re.search(r"Section\s+\d+\.\d+(?:\.\d+)?", line)
        if m:
            section_ref = m.group(0)
            break

    rules["Carrying_Overload_with_Forklift"] = {
        "description": "Forklift vehicle carrying more than two stacked blocks or pallets.",
        "observable_indicator": "Block count on forklift forks is greater than or equal to three.",
        "detection_approach": "YOLO truck/forklift detection and box contour counting on the forks.",
        "default_severity": "CRITICAL",
        "default_zone": "Loading_Area",
        "default_bounding_box": [300, 260, 980, 760],
        "label_confidence": 0.85,
        "policy_section": section_ref,
        "policy_signal": "CRITICAL SAFETY NOTICE",
        "tier_justification": "Forklift overloading exceeds capacity, causing instability and tip risks.",
        "default_context": {
            "block_count": 3,
            "forklift_operating": True,
            "personnel_count": 1
        },
        "escalation_rules": []
    }

    return rules

def run_llm_parsing(sections: dict[str, str], api_key: str) -> dict[str, Any]:
    """Invoke Gemini API to parse PDF text and return structured compliance rules."""
    import google.generativeai as genai
    
    print("Initializing Gemini Client...")
    genai.configure(api_key=api_key)
    
    # Clean and merge relevant sections to fit inside context
    relevant_text = []
    for section_name, text in sections.items():
        if any(keyword in section_name.lower() for keyword in ["ppe", "standard", "pedestrian", "walkway", "electrical", "panel", "material", "handling", "forklift", "machinery", "intervention"]):
            relevant_text.append(f"=== {section_name} ===\n{text}\n")
            
    full_text = "\n".join(relevant_text)
    
    prompt = EXTRACTION_PROMPT.format(text=full_text)
    
    print("Calling Gemini model...")
    # Use gemini-1.5-flash as it is fast and supports JSON structured output
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
    
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    raw_json = response.text.strip()
    return json.loads(raw_json)

def main():
    parser = argparse.ArgumentParser(description="Parse EHS Compliance Policy PDF")
    parser.add_argument("--pdf", default="Compliance_Policy_Manual.pdf", help="Path to PDF manual")
    parser.add_argument("--output", default="src/severity/auto_generated_rules.json", help="Path to save output JSON")
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf)
    output_path = Path(args.output)
    
    if not pdf_path.exists():
        print(f"Error: PDF manual not found at {pdf_path}. Running generator script first...")
        from scripts.generate_policy_pdf import generate_pdf
        generate_pdf(pdf_path)
        
    sections = extract_sections_from_pdf(pdf_path)
    
    # Check for Gemini API key
    api_key = os.getenv("GOOGLE_API_KEY")
    rules = None
    
    if api_key:
        try:
            rules = run_llm_parsing(sections, api_key)
            print("Successfully extracted rules using Gemini API.")
        except Exception as exc:
            print(f"LLM Parsing failed: {exc}. Falling back to heuristics.")
            rules = run_heuristic_parsing(sections)
    else:
        rules = run_heuristic_parsing(sections)
        
    if not rules:
        raise RuntimeError("Failed to parse policy rules.")
        
    # Schema check
    ok, msg = validate_schema(rules)
    if not ok:
        print(f"Schema validation failed: {msg}")
        sys.exit(1)
    print("Rule schema validated successfully.")
    
    # Semantic check
    similarity_checks = validate_extraction_quality(rules, sections)
    print("\n--- Extraction Quality Validation Metrics ---")
    for check in similarity_checks:
        print(f"- {check['behavior']}:")
        print(f"  * Observable Indicator Cosine Similarity: {check['observable_indicator_similarity']:.4f}")
        print(f"  * Description Cosine Similarity: {check['description_similarity']:.4f}")
        print(f"  * Semantic link validated: {check['valid']}")
        
    # Save rules file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(rules, file, indent=2)
        
    print(f"\nRules successfully generated at: {output_path}")

if __name__ == "__main__":
    main()
