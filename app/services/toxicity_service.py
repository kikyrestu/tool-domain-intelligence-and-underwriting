"""
Toxicity scanner — keyword-based flag detection on Wayback snapshot text.

Categories: parking, adult, gambling, pharma, malware, language_mismatch, young_domain.
Severity: high (auto-discard) or medium (penalty).
"""

import re
import logging
from datetime import datetime, date, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateDomain

logger = logging.getLogger(__name__)

# Keyword patterns per category
TOXICITY_PATTERNS: dict[str, list[str]] = {
    "parking": [
        r"buy this domain", r"domain for sale", r"this domain is for sale",
        r"domain parking", r"parked domain", r"is available for purchase",
        r"domain may be for sale", r"hugedomains", r"sedoparking",
        r"this page is parked", r"domain has expired",
    ],
    "adult": [
        r"\bporn\b", r"\bxxx\b", r"adult content", r"\b18\+",
        r"adult entertainment", r"explicit content",
    ],
    "gambling": [
        r"\bcasino\b", r"\bpoker\b", r"slot machine", r"\bbetting\b",
        r"\bgambling\b", r"\broulette\b", r"\bblackjack\b",
        r"sports betting", r"online casino",
    ],
    "pharma": [
        r"\bviagra\b", r"\bcialis\b", r"buy pills", r"cheap meds",
        r"online pharmacy", r"\berectile\b", r"prescription drugs",
    ],
    "malware": [
        r"free download crack", r"\bkeygen\b", r"\bwarez\b",
        r"serial key generator", r"hack tool",
    ],
}

# Severity mapping
SEVERITY: dict[str, str] = {
    "parking": "medium",
    "adult": "high",
    "gambling": "high",
    "pharma": "high",
    "malware": "high",
    "language_mismatch": "medium",
    "young_domain": "medium",
}


def scan_text(text: str) -> list[dict]:
    """
    Scan text for toxicity flags.
    Returns list of {"category", "matched", "severity"}.
    """
    flags = []
    if not text:
        return flags

    text_lower = text.lower()

    for category, patterns in TOXICITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                flags.append({
                    "category": category,
                    "matched": pattern,
                    "severity": SEVERITY[category],
                })
                break  # One match per category is enough

    return flags


def check_language_mismatch(dominant_lang: str | None, niche: str) -> dict | None:
    """Flag if dominant language doesn't match expected niche language."""
    # Most niches expect English content
    english_niches = {
        "Technology", "Finance", "Health", "Business", "Marketing",
        "Education", "E-commerce", "SaaS", "Real Estate", "Legal",
        "Travel", "Food", "Entertainment", "Sports", "News", "Crypto",
        "AI & Machine Learning",
    }

    if not dominant_lang or dominant_lang == "unknown":
        return None

    if niche in english_niches and dominant_lang not in ("en", "unknown"):
        return {
            "category": "language_mismatch",
            "matched": f"Expected English for {niche}, got {dominant_lang}",
            "severity": SEVERITY["language_mismatch"],
        }
    return None


def check_young_domain(created_date: date | None) -> dict | None:
    """Flag if domain was created less than 1 year ago."""
    if not created_date:
        return None

    today = date.today()
    age_days = (today - created_date).days
    if age_days < 365:
        return {
            "category": "young_domain",
            "matched": f"Domain age {age_days} days (< 1 year)",
            "severity": SEVERITY["young_domain"],
        }
    return None


def scan_candidate(candidate: CandidateDomain, snapshot_texts: list[str]) -> list[dict]:
    """
    Full toxicity scan for a candidate combining text flags + metadata flags.
    """
    all_flags = []

    # Text-based flags from all snapshots
    for text in snapshot_texts:
        text_flags = scan_text(text)
        for flag in text_flags:
            # Deduplicate by category
            if not any(f["category"] == flag["category"] for f in all_flags):
                all_flags.append(flag)

    # Language mismatch
    lang_flag = check_language_mismatch(candidate.dominant_language, candidate.niche)
    if lang_flag:
        all_flags.append(lang_flag)

    # Young domain
    young_flag = check_young_domain(candidate.whois_created_date)
    if young_flag:
        all_flags.append(young_flag)

    return all_flags
