import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schema import RawProduct
from dedup import is_likely_duplicate, cluster_products


def test_matches_reworded_same_product():
    assert is_likely_duplicate(
        "Nike Air Max Black 42", "Nike Airmax Shoes Size 8 Black"
    )


def test_rejects_different_brands():
    assert not is_likely_duplicate(
        "Nike Air Max Black 42", "Adidas Ultraboost Black 42"
    )


def test_clusters_full_sample_set():
    raw = [
        RawProduct("amazon", "Nike Air Max Black 42"),
        RawProduct("flipkart", "Nike Airmax Shoes Size 8 Black"),
        RawProduct("myntra", "Nike Air Max Running Shoes - Black"),
        RawProduct("amazon", "Adidas Ultraboost Running Shoes White Size 9"),
        RawProduct("flipkart", "Adidas Ultraboost White Sz 9"),
    ]
    clusters = cluster_products(raw)
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [2, 3]  # one Adidas pair, one Nike triple


if __name__ == "__main__":
    test_matches_reworded_same_product()
    test_rejects_different_brands()
    test_clusters_full_sample_set()
    print("All dedup tests passed.")
