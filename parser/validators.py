"""Validation checks for extracted compliance rules, including cosine similarity checks."""

import json
from typing import Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

EXPECTED_BEHAVIORS = {
    "Safe_Walkway_Violation",
    "Unauthorized_Intervention",
    "Opened_Panel_Cover",
    "Carrying_Overload_with_Forklift"
}

def validate_schema(rules: dict[str, Any]) -> tuple[bool, str]:
    """Verify rules conform to expected schema and behaviors."""
    
    missing_behaviors = EXPECTED_BEHAVIORS - set(rules.keys())
    if missing_behaviors:
        return False, f"Missing behaviors: {missing_behaviors}"

    required_fields = {
        "description", "observable_indicator", "detection_approach",
        "default_severity", "default_zone", "default_bounding_box",
        "label_confidence", "policy_section", "policy_signal",
        "tier_justification", "default_context", "escalation_rules"
    }

    for behavior, config in rules.items():
        missing_fields = required_fields - set(config.keys())
        if missing_fields:
            return False, f"Behavior '{behavior}' is missing fields: {missing_fields}"
        
        # Validate severity
        sev = config["default_severity"]
        if sev not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            return False, f"Behavior '{behavior}' has invalid default severity: {sev}"
        
        # Validate escalation rules format
        for rule in config.get("escalation_rules", []):
            if not all(k in rule for k in ("condition", "new_severity", "rationale")):
                return False, f"Behavior '{behavior}' has malformed escalation rules"
            
            new_sev = rule["new_severity"]
            if new_sev not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                return False, f"Behavior '{behavior}' has invalid escalation severity: {new_sev}"

    return True, "Schema validated successfully."

def check_semantic_similarity(extracted_text: str, source_section_text: str) -> float:
    """Calculate TF-IDF based cosine similarity between extracted text and source PDF section."""
    
    if not extracted_text or not source_section_text:
        return 0.0
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([extracted_text, source_section_text])
        similarity = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        return similarity
    except Exception as exc:
        print(f"Warning: Similarity calculation failed: {exc}")
        return 0.0

def validate_extraction_quality(rules: dict[str, Any], sections: dict[str, str]) -> list[dict[str, Any]]:
    """Validate extracted rules against original PDF sections using similarity checks."""
    
    results = []
    
    # Map behavior names to section patterns
    behavior_section_map = {
        "Safe_Walkway_Violation": "Section 4",
        "Unauthorized_Intervention": "Section 7",
        "Opened_Panel_Cover": "Section 5",
        "Carrying_Overload_with_Forklift": "Section 6"
    }
    
    for behavior, config in rules.items():
        sect_key = behavior_section_map.get(behavior)
        source_text = ""
        
        # Find matching section in raw text dictionary
        for k, v in sections.items():
            if sect_key and sect_key.lower() in k.lower():
                source_text = v
                break
                
        # If no direct match, check all sections
        if not source_text:
            source_text = "\n".join(sections.values())
            
        indicator_sim = check_semantic_similarity(config["observable_indicator"], source_text)
        desc_sim = check_semantic_similarity(config["description"], source_text)
        
        results.append({
            "behavior": behavior,
            "observable_indicator_similarity": indicator_sim,
            "description_similarity": desc_sim,
            "valid": indicator_sim >= 0.70 and desc_sim >= 0.70  # stricter verification (>=0.70)
        })
        
    return results
