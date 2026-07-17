"""
Canonical schema for the Product Normalization Engine.

This intentionally uses plain dataclasses rather than an ORM model, since the
prototype has no database dependency. In production these would map onto the
`canonical_product` / `product_variant` / `platform_listing` tables described
in the accompanying design document (section 1.4).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawProduct:
    """A single messy, platform-sourced record, as it arrives from a crawler."""

    platform: str
    raw_title: str
    price: Optional[float] = None
    rating: Optional[float] = None
    source_url: Optional[str] = None


@dataclass
class ExtractedAttributes:
    """Structured fields pulled out of a raw title. Unmatched fields are None,
    not guessed, in keeping with the partial-data philosophy in the design doc."""

    brand: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    confidence: float = 0.0


@dataclass
class CanonicalProduct:
    """A deduplicated, cross-platform product record."""

    canonical_id: str
    display_title: str
    brand: Optional[str]
    attributes: ExtractedAttributes
    listings: list = field(default_factory=list)  # list[RawProduct]

    def as_dict(self) -> dict:
        return {
            "canonical_id": self.canonical_id,
            "display_title": self.display_title,
            "brand": self.brand,
            "attributes": {
                "color": self.attributes.color,
                "size": self.attributes.size,
                "material": self.attributes.material,
                "confidence": round(self.attributes.confidence, 2),
            },
            "listings": [
                {
                    "platform": l.platform,
                    "raw_title": l.raw_title,
                    "price": l.price,
                    "rating": l.rating,
                }
                for l in self.listings
            ],
        }
