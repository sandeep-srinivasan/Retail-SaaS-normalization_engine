"""
End-to-end run of the normalization pipeline over the sample data.

Usage:
    python main.py [path/to/data.json] [--db path/to/db.sqlite]

By default this both prints the resolved canonical products and persists
them to a local SQLite database (normalization.db), so the pipeline produces
something that actually survives the run, not just stdout output. Pass
--no-db to skip persistence and only print, e.g. for quick iteration.
"""

import argparse
import hashlib
import json

from schema import RawProduct, CanonicalProduct
from dedup import cluster_products
from attribute_extractor import extract_attributes
from db import store_canonical_products, fetch_all_products


def load_raw_products(path: str):
    with open(path) as f:
        records = json.load(f)
    return [RawProduct(**r) for r in records]


def _stable_canonical_id(cluster) -> str:
    """Derives a canonical_id from the cluster's content rather than
    generating a random one. This matters more than it might look: a random
    ID (e.g. uuid4()) means re-running the pipeline against the same input —
    which happens constantly in practice, since batch syncs and recrawls
    overlap — mints a brand-new canonical_id for the same real-world product
    every time, silently duplicating rows in storage instead of updating
    them. Hashing the sorted (platform, raw_title) pairs in the cluster
    keeps the ID stable across runs as long as the underlying listings are
    unchanged, which is the property `store_canonical_products` actually
    needs to be idempotent."""
    fingerprint = "|".join(
        sorted(f"{p.platform}:{p.raw_title}" for p in cluster)
    )
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:12]


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
            canonical_id=_stable_canonical_id(cluster),
            display_title=best_title_product.raw_title,
            brand=attrs.brand,
            attributes=attrs,
            listings=cluster,
        )
        canonical_products.append(canonical)

    return canonical_products


def main():
    parser = argparse.ArgumentParser(description="Run the product normalization pipeline.")
    parser.add_argument("data_path", nargs="?", default="sample_data.json")
    parser.add_argument("--db", default="normalization.db", help="SQLite db path")
    parser.add_argument("--no-db", action="store_true", help="skip persistence, print only")
    args = parser.parse_args()

    raw_products = load_raw_products(args.data_path)
    print(f"Loaded {len(raw_products)} raw records from {args.data_path}\n")

    canonical_products = build_canonical_products(raw_products)
    print(f"Resolved into {len(canonical_products)} canonical products:\n")
    for cp in canonical_products:
        print(json.dumps(cp.as_dict(), indent=2))
        print()

    if args.no_db:
        return

    store_canonical_products(canonical_products, db_path=args.db)
    print(f"Persisted {len(canonical_products)} canonical products to {args.db}\n")

    # Read back as a sanity check that persistence actually round-trips,
    # rather than trusting the write silently.
    stored = fetch_all_products(db_path=args.db)
    print(f"Verified: {len(stored)} canonical products readable from {args.db}")
    for row in stored:
        print(f"  {row['canonical_id']}  {row['brand']:<10}  {row['display_title']}  "
              f"({len(row['listings'])} listings)")


if __name__ == "__main__":
    main()
