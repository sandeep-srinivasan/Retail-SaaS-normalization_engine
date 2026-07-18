import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schema import RawProduct, CanonicalProduct, ExtractedAttributes
from db import store_canonical_products, fetch_all_products


def _sample_canonical_products():
    attrs = ExtractedAttributes(brand="Nike", color="Black", size="US 8.5", confidence=0.75)
    listings = [
        RawProduct("amazon", "Nike Air Max Black 42", price=8999.0, rating=4.3),
        RawProduct("flipkart", "Nike Airmax Shoes Size 8 Black", price=8499.0, rating=4.1),
    ]
    return [
        CanonicalProduct(
            canonical_id="test0001",
            display_title="Nike Air Max Black 42",
            brand="Nike",
            attributes=attrs,
            listings=listings,
        )
    ]


def test_store_and_fetch_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        products = _sample_canonical_products()

        store_canonical_products(products, db_path=db_path)
        stored = fetch_all_products(db_path=db_path)

        assert len(stored) == 1
        assert stored[0]["canonical_id"] == "test0001"
        assert stored[0]["brand"] == "Nike"
        assert len(stored[0]["listings"]) == 2
        platforms = {l["platform"] for l in stored[0]["listings"]}
        assert platforms == {"amazon", "flipkart"}


def test_rerunning_pipeline_is_idempotent():
    """Storing the same canonical products twice should not duplicate rows,
    since a real pipeline re-runs against overlapping data constantly
    (batch sync overlapping with a recrawl, for instance)."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        products = _sample_canonical_products()

        store_canonical_products(products, db_path=db_path)
        store_canonical_products(products, db_path=db_path)  # run again

        stored = fetch_all_products(db_path=db_path)
        assert len(stored) == 1
        assert len(stored[0]["listings"]) == 2  # not 4


def test_full_pipeline_rerun_is_idempotent():
    """Exercises the actual main.py pipeline (build_canonical_products +
    store_canonical_products) end to end, not just db.py in isolation. This
    is the test that would have caught the original bug: canonical_id was
    generated with uuid4() and changed on every run, so this exact test
    failed until canonical_id was switched to a content-derived hash."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from main import load_raw_products, build_canonical_products

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        data_path = os.path.join(os.path.dirname(__file__), "..", "sample_data.json")

        raw_products = load_raw_products(data_path)

        first_run = build_canonical_products(raw_products)
        store_canonical_products(first_run, db_path=db_path)

        second_run = build_canonical_products(raw_products)
        store_canonical_products(second_run, db_path=db_path)

        stored = fetch_all_products(db_path=db_path)
        assert len(stored) == len(first_run), (
            f"expected {len(first_run)} canonical products after two runs, "
            f"got {len(stored)} -- canonical_id is likely non-deterministic again"
        )


if __name__ == "__main__":
    test_store_and_fetch_roundtrip()
    test_rerunning_pipeline_is_idempotent()
    test_full_pipeline_rerun_is_idempotent()
    print("All db tests passed.")
