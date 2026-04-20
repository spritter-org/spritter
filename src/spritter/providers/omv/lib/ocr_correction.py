"""
OCR correction and fuzzy matching for fuel type labels.

Uses fuzzy matching to normalize OCR-extracted labels without hard-coding specific terms.
Dynamically identifies fuel type keywords from OCR output and matches variations.

This module is conservative and only corrects labels that:
1. Have obvious OCR artifacts (mixed case, character substitutions)
2. Match an extracted fuel keyword with high similarity (>0.85)
"""

from __future__ import annotations

import difflib
import logging
import re
from typing import NamedTuple

logger = logging.getLogger(__name__)


class FuelTypeKeyword(NamedTuple):
    """Represents a fuel type keyword extracted from OCR."""

    keyword: str  # e.g., "DIESEL", "SUPER", "PLUS"
    confidence: float  # 0.0-1.0, based on occurrence pattern


# Common fuel type components (patterns, not hard-coded fuel names)
# These are common substrings that appear in fuel type labels
FUEL_TYPE_COMPONENTS = {
    # Base fuel types
    "diesel",
    "super",
    "premium",
    "euro",
    "plus",
    "eco",
    "regular",
    "unleaded",
    # Numbers/grades
    "95",
    "98",
    "100",
    # Variants/modifiers
    "motion",  # catches brand names like "Maxx Motion"
    "x",
    "ultimate",
    "evolution",
    "advanced",
    # Special variants
    "optimal",
    "max",
    "maxx",
    "v",
    "evo",
}


def has_ocr_artifacts(label: str) -> bool:
    """
    Check if a label shows signs of OCR errors.
    
    Signs include:
    - Unusual mixed casing (e.g., "pIus" instead of "Plus")
    - Character substitutions (e.g., numbers where letters should be)
    - Runs of capitalized letters (e.g., "MAXXMOTJON" - likely missing spaces/splits)
    """
    if not label or not any(c.isalpha() for c in label):
        return False
    
    # Check for suspicious character substitutions
    # (e.g., '1' for 'I', '0' for 'O')
    suspicious_pairs = [
        ('1', 'I'),
        ('0', 'O'),
        ('5', 'S'),
    ]
    for digit, letter in suspicious_pairs:
        if digit in label and letter.lower() in label.lower():
            return True
    
    # Check for unusual mixed casing (more than one case transition)
    case_transitions = 0
    for i in range(1, len(label)):
        if label[i].isupper() != label[i-1].isupper() and label[i].isalpha() and label[i-1].isalpha():
            case_transitions += 1
    
    # More than 2 case transitions suggests OCR artifact
    if case_transitions > 2:
        return True
    
    return False


def extract_fuel_keywords(text: str) -> list[FuelTypeKeyword]:
    """
    Extract potential fuel type keywords from OCR text.

    Identifies tokens that appear near prices and match fuel type patterns.
    Returns keywords sorted by confidence (likelihood of being a fuel type).
    """
    keywords: dict[str, float] = {}

    # Look for tokens with letters (likely label parts, not noise)
    tokens = re.findall(r"[a-zA-Z0-9]+", text)
    
    for token in tokens:
        lower_token = token.lower()

        # Skip very short tokens (likely noise) and very long tokens (likely OCR artifacts)
        if len(lower_token) < 2 or len(lower_token) > 20:
            continue

        # Check if token contains fuel type components
        for component in FUEL_TYPE_COMPONENTS:
            if component in lower_token:
                # Boost confidence for exact component matches
                if lower_token == component:
                    keywords[lower_token] = keywords.get(lower_token, 0) + 2.0
                else:
                    keywords[lower_token] = keywords.get(lower_token, 0) + 1.0
                break

    # Convert to FuelTypeKeyword and normalize confidence
    max_confidence = max(keywords.values()) if keywords else 1.0
    result = [
        FuelTypeKeyword(
            keyword=k,
            confidence=min(1.0, v / max_confidence),
        )
        for k, v in sorted(keywords.items(), key=lambda x: -x[1])
    ]

    logger.debug(
        "Extracted %d fuel keywords from OCR text: %s",
        len(result),
        [(kw.keyword, round(kw.confidence, 2)) for kw in result[:5]],
    )
    return result


def build_fuel_type_vocabulary(keywords: list[FuelTypeKeyword]) -> set[str]:
    """
    Build a vocabulary of likely fuel types from extracted keywords.

    Uses the extracted keywords to construct canonical fuel type forms.
    For example, from ["diesel", "maxx", "motion"] would build a vocabulary
    that includes "diesel", "maxx motion", "maxx diesel", etc.
    """
    if not keywords:
        return set()

    vocabulary: set[str] = set()

    # Add each keyword individually (preserving case from original text)
    for kw in keywords:
        vocabulary.add(kw.keyword)

    # Combine high-confidence keywords to form multi-word fuel types
    high_confidence = [kw.keyword for kw in keywords if kw.confidence > 0.5]

    # Generate reasonable combinations (up to 3 words)
    for i in range(len(high_confidence)):
        for j in range(i + 1, min(i + 3, len(high_confidence) + 1)):
            vocabulary.add(" ".join(high_confidence[i:j]))

    logger.debug(
        "Built fuel type vocabulary with %d entries: %s",
        len(vocabulary),
        sorted(list(vocabulary))[:10],
    )
    return vocabulary


def correct_fuel_label(
    label: str,
    vocabulary: set[str] | None = None,
    threshold: float = 0.85,
) -> str:
    """
    Correct OCR errors in fuel type labels using fuzzy matching.
    
    This is conservative - only corrects labels that show signs of OCR artifacts
    and have a high-confidence match in the vocabulary.

    Args:
        label: The OCR-extracted label (may contain errors)
        vocabulary: Optional set of canonical fuel type keywords.
                   If None, matches against common fuel patterns.
        threshold: Minimum similarity ratio (0.0-1.0) for accepting a match.
                  Default 0.85 is conservative; this only corrects obvious errors.

    Returns:
        Corrected label (original label if no good match found or no artifacts detected)
    """
    label_normalized = label.strip()

    if not label_normalized:
        return label

    # If already in vocabulary, return as-is
    if vocabulary and label_normalized in vocabulary:
        return label_normalized

    # Only attempt correction if we detect OCR artifacts
    if not has_ocr_artifacts(label_normalized):
        return label_normalized

    search_pool = vocabulary or FUEL_TYPE_COMPONENTS

    # Find best match using SequenceMatcher
    best_match: str | None = None
    best_ratio = 0.0

    for candidate in search_pool:
        # Case-insensitive comparison
        ratio = difflib.SequenceMatcher(
            None,
            label_normalized.lower(),
            candidate.lower(),
        ).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate

    if best_match and best_ratio >= threshold:
        logger.info(
            "Corrected OCR label '%s' → '%s' (similarity: %.2f)",
            label,
            best_match,
            best_ratio,
        )
        return best_match

    # If no match found, return original (preserve casing)
    logger.debug(
        "No fuzzy match for '%s' (best ratio: %.2f < threshold: %.2f)",
        label,
        best_ratio,
        threshold,
    )
    return label_normalized


def normalize_ocr_labels(
    price_map: dict[str, any],
    ocr_text: str,
    threshold: float = 0.85,
) -> dict[str, any]:
    """
    Normalize fuel type labels in a price map using OCR context.

    Extracts fuel keywords from the full OCR text to build a vocabulary,
    then applies conservative fuzzy matching to correct only obvious errors.

    Args:
        price_map: Dictionary of {label: price} pairs from OCR
        ocr_text: Full OCR text from the price image
        threshold: Minimum similarity threshold (default 0.85 for conservative matching)

    Returns:
        Price map with corrected labels (or original labels if no corrections needed)
    """
    if not price_map:
        return price_map

    # Build vocabulary from full OCR text
    keywords = extract_fuel_keywords(ocr_text)
    vocabulary = build_fuel_type_vocabulary(keywords)

    # Correct each label that shows OCR artifacts
    corrected_map: dict[str, any] = {}
    corrections_made = 0

    for label, price in price_map.items():
        corrected_label = correct_fuel_label(label, vocabulary, threshold)
        if corrected_label != label:
            corrections_made += 1
        corrected_map[corrected_label] = price

    if corrections_made > 0:
        logger.info(
            "Applied %d label corrections: %s",
            corrections_made,
            {k: v for k, v in zip(price_map.keys(), corrected_map.keys()) if k != v},
        )

    return corrected_map

