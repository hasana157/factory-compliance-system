# Policy Extraction Process

The compliance policy content in the project plan defines four observable unsafe behavior domains. Instead of manual transcription, the system uses an automated LLM-grounded pipeline to parse the policy document (`Compliance_Policy_Manual.pdf`) and generate structured rules.

## Automated Parsing Pipeline

1. **Document Ingestion**: The system uses `pdfplumber` to extract text from the official factory EHS compliance policy PDF.
2. **LLM Extraction**: The raw text is passed to Google's Gemini LLM via the `google-generativeai` package, using a strict structured output prompt. The LLM extracts behaviors, default severity tiers, escalation rules, and policy section references.
3. **Structured Validation**: The `parser/validators.py` module ensures the LLM's output matches the expected JSON schema.
4. **Cosine Similarity Check**: To prevent hallucination, the extracted rules are vectorized using `scikit-learn`'s TfidfVectorizer and compared against the original PDF text using cosine similarity. Only rules grounded in the source text pass validation (enforced by a strict `>= 0.70` similarity threshold for both visual indicators and semantic descriptions).
5. **JSON Generation**: The validated rules are automatically saved to `src/severity/auto_generated_rules.json`.

## Behavior Rules (Auto-Generated)

### Safe_Walkway_Violation
- **Policy Reference**: Section 3.3.2
- **Default Severity**: MEDIUM
- **Escalation**: Escalates to HIGH when the person is within one meter of machinery or during forklift operation.

### Unauthorized_Intervention
- **Policy Reference**: Section 4.3.2
- **Default Severity**: HIGH
- **Escalation**: Escalates to CRITICAL when multiple unauthorized personnel are involved.

### Opened_Panel_Cover
- **Policy Reference**: Section 5.2.2
- **Default Severity**: MEDIUM
- **Escalation**: Escalates to HIGH after five minutes or when personnel are within one meter.

### Carrying_Overload_with_Forklift
- **Policy Reference**: Section 6.3.2
- **Default Severity**: CRITICAL
- **Escalation**: None specified.

## Source of Truth

The `src/severity/auto_generated_rules.json` file serves as the single source of truth for the detector, classifier, API, and documentation. By automating this pipeline, any updates to the policy PDF can be instantly reflected in the system's runtime rules without manual code changes.
