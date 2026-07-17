"""
End-to-end run of the normalization pipeline over the sample data.

Usage:
    python main.py [path/to/data.json]
"""

import json
import sys
import uuid

from schema import RawProduct, CanonicalProduct
from dedup import cluster_products
from attribute_extractor import extract_attributes


def load_raw_products(path: str):
    with open(path) as f:
        records = json.load(f)
    return [RawProduct(**r) for r in records]


def build_canonical_products(raw_products):
    clusters = cluster_products(raw_products)
    canonical_products = []

    for cluster in clusters:
        # Use the longest title as the display title; it tends to carry the
        # most descriptive information (a simple, explainable heuristic
        # rather than a learned "best title" model).
        best_title_product = max(cluster, key=lambda p: len(p.raw_title))
        attrs = extract_attributes(best_title_product.raw_title)

        canonical = CanonicalProduct(
            canonical_id=str(uuid.uuid4())[:8],
            display_title=best_title_product.raw_title,
            brand=attrs.brand,
            attributes=attrs,
            listings=cluster,
        )
        canonical_products.append(canonical)

    return canonical_products


def main():
    data_path = sys.argv[1] if len(sys.argv) > 1 else "sample_data.json"
    raw_products = load_raw_products(data_path)

    print(f"Loaded {len(raw_products)} raw records from {data_path}\n")

    canonical_products = build_canonical_products(raw_products)

    print(f"Resolved into {len(canonical_products)} canonical products:\n")
    for cp in canonical_products:
        print(json.dumps(cp.as_dict(), indent=2))
        print()


if __name__ == "__main__":
    main()
