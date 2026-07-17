"""
Deduplication: clusters raw product records that refer to the same underlying
product, even when titles differ in wording, word order, or size/colour
formatting.

Deliberately built on the Python standard library only (difflib), rather than
rapidfuzz/thefuzz, so the prototype has zero external dependencies. The
matching approach layers three signals, matching the reasoning in Part 3.2 of
the design document: brand agreement, token-overlap title similarity, and
size/colour reconciliation via the attribute extractor.
"""

import re
from difflib import SequenceMatcher

from attribute_extractor import extract_attributes

STOPWORDS = {"the", "a", "an", "for", "with", "and", "of"}


def _tokenize(title: str):
    tokens = re.findall(r"[a-z0-9\.]+", title.lower())
    return [t for t in tokens if t not in STOPWORDS]


def _token_set_ratio(a: str, b: str) -> float:
    """Order-independent similarity: compares the sorted, deduplicated token
    sets rather than the raw strings, so word-order differences and repeated
    filler words don't unfairly depress the score."""
    tokens_a = sorted(set(_tokenize(a)))
    tokens_b = sorted(set(_tokenize(b)))
    return SequenceMatcher(None, " ".join(tokens_a), " ".join(tokens_b)).ratio()


def is_likely_duplicate(title_a: str, title_b: str, threshold: float = 0.55) -> bool:
    """Returns True if two raw titles likely refer to the same product.

    Brand mismatch is treated as a hard veto (a wrong-brand match is a worse
    error than a missed match, per the design doc's reasoning), while title
    similarity and size/colour agreement combine into a soft score.
    """
    attrs_a = extract_attributes(title_a)
    attrs_b = extract_attributes(title_b)

    if attrs_a.brand and attrs_b.brand and attrs_a.brand != attrs_b.brand:
        return False

    title_score = _token_set_ratio(title_a, title_b)

    # Size/colour agreement nudges the score up, but does not gate the match
    # on its own, since colour is frequently missing rather than genuinely
    # different.
    bonus = 0.0
    if attrs_a.color and attrs_b.color and attrs_a.color == attrs_b.color:
        bonus += 0.1
    if attrs_a.size and attrs_b.size and attrs_a.size == attrs_b.size:
        bonus += 0.15

    return (title_score + bonus) >= threshold


def cluster_products(raw_products):
    """Greedy clustering: O(n^2) comparisons, which is fine for a prototype
    and for the batch-reconciliation use case, but would need blocking
    (e.g. by brand + category) before this scaled to millions of records."""
    clusters = []  # list[list[RawProduct]]

    for product in raw_products:
        placed = False
        for cluster in clusters:
            representative = cluster[0]
            if is_likely_duplicate(representative.raw_title, product.raw_title):
                cluster.append(product)
                placed = True
                break
        if not placed:
            clusters.append([product])

    return clusters
