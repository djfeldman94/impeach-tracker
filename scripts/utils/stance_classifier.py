"""
Keyword-based heuristic stance classifier for impeachment-related text.

Used by scrape_stances.py to classify press releases, statements,
and news articles into stance categories.
"""

import re

# Keyword patterns by stance (order matters — checked top to bottom, first match wins)
STANCE_PATTERNS = [
    # Strong support signals
    (
        "cosponsor",
        [
            r"\bco-?sponsor(?:ed|ing|s)?\b.*\bimpeach",
            r"\bimpeach.*\bco-?sponsor(?:ed|ing|s)?\b",
            r"\bintroduc(?:ed|ing)\b.*\barticles?\s+of\s+impeachment\b",
            r"\bfiled?\b.*\barticles?\s+of\s+impeachment\b",
        ],
    ),
    # Public support
    (
        "publicly-supports",
        [
            r"\bsupport(?:s|ed|ing)?\b.*\bimpeach(?:ment|ing)?\b",
            r"\bimpeach(?:ment|ing)?\b.*\bsupport(?:s|ed|ing)?\b",
            r"\bvot(?:e|ed|ing)\b.*\bimpeach\b",
            r"\bcall(?:s|ed|ing)?\s+for\b.*\bimpeach",
            r"\burge[sd]?\b.*\bimpeach",
            r"\bmust\s+be\s+impeached\b",
            r"\bimpeach(?:ment)?\s+is\s+necessary\b",
        ],
    ),
    # Leaning support
    (
        "leaning-support",
        [
            r"\bopen\s+to\b.*\bimpeach",
            r"\bconsidering\b.*\bimpeach",
            r"\binvestigat(?:e|ion|ing)\b.*\bimpeach",
            r"\baccountability\b.*\bimpeach",
            r"\bserious(?:ly)?\s+consider",
        ],
    ),
    # Leaning oppose
    (
        "leaning-oppose",
        [
            r"\bconcern(?:s|ed)?\b.*\bimpeach",
            r"\bpremature\b.*\bimpeach",
            r"\bnot\s+(?:yet|the\s+time)\b.*\bimpeach",
            r"\bwait\s+for\b.*\bevidence\b",
            r"\bdivisive\b.*\bimpeach",
        ],
    ),
    # Strong opposition
    (
        "publicly-opposes",
        [
            r"\boppose[sd]?\b.*\bimpeach",
            r"\bimpeach.*\boppose[sd]?\b",
            r"\bagainst\b.*\bimpeach",
            r"\bimpeach.*\bwitch\s*hunt\b",
            r"\bimpeach.*\bsham\b",
            r"\bimpeach.*\bhoax\b",
            r"\bimpeach.*\bpartisan\b.*\b(?:attack|abuse|stunt)\b",
            r"\bimpeach.*\bunconstitutional\b",
            r"\bno\s+grounds?\s+for\b.*\bimpeach",
        ],
    ),
]


def classify_text(text: str) -> str | None:
    """
    Classify a text snippet into a stance category.

    Returns the stance string or None if no match.
    Text is matched case-insensitively.
    """
    text_lower = text.lower()

    for stance, patterns in STANCE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return stance

    return None


def classify_texts(texts: list[str]) -> str | None:
    """
    Classify multiple text snippets, returning the strongest signal.

    Priority: cosponsor > publicly-supports > publicly-opposes >
              leaning-support > leaning-oppose > None
    """
    priority = [
        "cosponsor",
        "publicly-supports",
        "publicly-opposes",
        "leaning-support",
        "leaning-oppose",
    ]

    found = set()
    for text in texts:
        result = classify_text(text)
        if result:
            found.add(result)

    for stance in priority:
        if stance in found:
            return stance

    return None
