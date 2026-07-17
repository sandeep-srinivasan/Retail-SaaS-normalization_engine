"""
Attribute extraction: pulls brand / color / size / material out of a free-text
product title.

This is a heuristic, controlled-vocabulary approach rather than a trained NER
model, which is a deliberate scope decision for a prototype: it is transparent,
fast, and easy to extend with new terms, at the cost of not generalising to
vocabulary it has never seen. A production system would likely layer a small
trained classifier on top of this for the residual cases, rather than replace
it outright, since the vocabulary approach is cheap and gets the common cases
right with no inference cost.
"""

import re
from schema import ExtractedAttributes

# A small seed vocabulary. In production this would be loaded from the
# category-taxonomy service rather than hardcoded, and would be far larger.
# Maps every surface variant to one canonical display form, so that
# "levis" and "levi's" resolve to the same brand rather than being treated
# as a mismatch during dedup (an early bug I caught while testing this
# very prototype against the sample data).
BRAND_CANONICAL_FORM = {
    "nike": "Nike",
    "adidas": "Adidas",
    "puma": "Puma",
    "reebok": "Reebok",
    "levi's": "Levi's",
    "levis": "Levi's",
    "zara": "Zara",
}
KNOWN_BRANDS = list(BRAND_CANONICAL_FORM.keys())

KNOWN_COLORS = [
    "black", "white", "red", "blue", "green", "grey", "gray", "navy",
    "beige", "brown", "pink", "yellow", "orange", "purple", "maroon",
]

KNOWN_MATERIALS = [
    "cotton", "leather", "polyester", "denim", "wool", "silk", "canvas",
    "mesh", "suede", "nylon",
]

# EU shoe size -> US shoe size (men's), a small illustrative slice of the
# conversion table referenced in the design document's dedup discussion.
EU_TO_US_SHOE = {
    "40": "7", "41": "8", "42": "8.5", "43": "9.5", "44": "10.5", "45": "11.5",
}

SIZE_PATTERNS = [
    # "size 8", "size: 8", "sz 8"
    re.compile(r"\bsize\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)\b", re.I),
    re.compile(r"\bsz\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)\b", re.I),
    # bare EU-style size token, e.g. "... Black 42"
    re.compile(r"\b(\d{2})\b"),
    # clothing letter sizes
    re.compile(r"\b(XS|S|M|L|XL|XXL)\b"),
]


def _find_first(vocab, text_lower):
    for term in vocab:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            return term
    return None


def normalize_size_token(token: str) -> str:
    """Normalize a raw size token onto a common (US-numeric-where-possible) scale."""
    if token is None:
        return None
    t = token.strip().upper()
    if t in EU_TO_US_SHOE:
        return f"US {EU_TO_US_SHOE[t]}"
    if t.replace(".", "", 1).isdigit():
        # Ambiguous bare number: could already be US. Leave tagged as-is,
        # a real system would disambiguate using category + platform locale.
        return f"US {t}" if float(t) <= 15 else t
    return t


def extract_attributes(raw_title: str) -> ExtractedAttributes:
    text_lower = raw_title.lower()

    brand = _find_first(KNOWN_BRANDS, text_lower)
    color = _find_first(KNOWN_COLORS, text_lower)
    material = _find_first(KNOWN_MATERIALS, text_lower)

    size_raw = None
    for pattern in SIZE_PATTERNS:
        m = pattern.search(raw_title)
        if m:
            size_raw = m.group(1)
            break
    size = normalize_size_token(size_raw) if size_raw else None

    # Confidence is a simple, explainable heuristic: proportion of the four
    # target fields that were successfully matched. Kept deliberately simple
    # rather than a learned score, so a reviewer can audit it in one line.
    matched = sum(x is not None for x in [brand, color, size, material])
    confidence = matched / 4.0

    return ExtractedAttributes(
        brand=BRAND_CANONICAL_FORM[brand] if brand else None,
        color=color.title() if color else None,
        size=size,
        material=material.title() if material else None,
        confidence=confidence,
    )
