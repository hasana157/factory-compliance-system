"""pipeline/parsers/pdf_extractor.py

Extracts raw text from the EHS Compliance Policy PDF using pdfplumber.
Preserves section headers (e.g. "Section 3.3.2"), callout boxes
("WARNING", "CRITICAL SAFETY NOTICE"), and glossary definitions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class PolicySection:
    """One logical section of the policy document."""

    heading: str
    content: str
    callouts: list[str] = field(default_factory=list)  # e.g. ["WARNING", "CRITICAL SAFETY NOTICE"]
    section_ref: str = ""  # e.g. "Section 3.3.2"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_SECTION_HEADER = re.compile(
    r"^(Section\s+\d+(?:\.\d+){0,3}[:\s\-][\w\s\-\.\(\)\/,]+)",
    re.IGNORECASE,
)
_SECTION_REF = re.compile(r"Section\s+\d+(?:\.\d+){0,3}", re.IGNORECASE)
_CALLOUT = re.compile(
    r"\b(WARNING|CRITICAL\s+SAFETY\s+NOTICE|CAUTION|DANGER|NOTE)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class PDFTextExtractor:
    """Extract structured text from a compliance policy PDF."""

    def __init__(self, pdf_path: str | Path) -> None:
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_sections(self) -> dict[str, PolicySection]:
        """Return an ordered dict of section-heading -> PolicySection."""
        try:
            import pdfplumber
        except ImportError as exc:
            raise ImportError("pdfplumber is required: pip install pdfplumber") from exc

        print(f"[pdf_extractor] Opening: {self.pdf_path}")
        raw_pages: list[str] = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                raw_pages.append(text)

        full_text = "\n".join(raw_pages)
        sections = self._split_into_sections(full_text)
        print(f"[pdf_extractor] Extracted {len(sections)} sections.")
        return sections

    def extract_full_text(self) -> str:
        """Return the entire PDF as a single string."""
        try:
            import pdfplumber
        except ImportError as exc:
            raise ImportError("pdfplumber is required: pip install pdfplumber") from exc

        pages: list[str] = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return "\n".join(pages)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> dict[str, PolicySection]:
        """Parse text into sections keyed by their heading string."""
        sections: dict[str, PolicySection] = {}
        current_heading = "Cover & Preface"
        current_lines: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            m = _SECTION_HEADER.match(stripped)
            if m:
                # Save previous section
                if current_lines:
                    sections[current_heading] = self._build_section(
                        current_heading, current_lines
                    )
                current_heading = m.group(1).strip()
                current_lines = [stripped]
            else:
                current_lines.append(stripped)

        # Save last section
        if current_lines:
            sections[current_heading] = self._build_section(
                current_heading, current_lines
            )

        return sections

    def _build_section(self, heading: str, lines: list[str]) -> PolicySection:
        content = "\n".join(line for line in lines if line)
        callouts: list[str] = []
        for line in lines:
            for match in _CALLOUT.finditer(line):
                label = match.group(1).upper().replace("  ", " ")
                if label not in callouts:
                    callouts.append(label)

        # Extract the first section reference from heading or content
        ref_match = _SECTION_REF.search(heading) or _SECTION_REF.search(content)
        section_ref = ref_match.group(0) if ref_match else ""

        return PolicySection(
            heading=heading,
            content=content,
            callouts=callouts,
            section_ref=section_ref,
        )


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------

def extract_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Convenience wrapper: returns sections as plain dicts."""
    extractor = PDFTextExtractor(pdf_path)
    sections = extractor.extract_sections()
    return {
        heading: {
            "content": sec.content,
            "callouts": sec.callouts,
            "section_ref": sec.section_ref,
        }
        for heading, sec in sections.items()
    }


if __name__ == "__main__":
    import json
    import sys

    pdf = sys.argv[1] if len(sys.argv) > 1 else "Compliance_Policy_Manual.pdf"
    result = extract_pdf(pdf)
    print(json.dumps(result, indent=2))
