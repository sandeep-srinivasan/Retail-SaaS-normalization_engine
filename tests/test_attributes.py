import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from attribute_extractor import extract_attributes, normalize_size_token


def test_extracts_brand_color_size():
    attrs = extract_attributes("Nike Air Max Black 42")
    assert attrs.brand == "Nike"
    assert attrs.color == "Black"
    assert attrs.size == "US 8.5"  # EU 42 -> US 8.5


def test_extracts_material_and_letter_size():
    attrs = extract_attributes("Puma Cotton T-Shirt Grey L")
    assert attrs.brand == "Puma"
    assert attrs.material == "Cotton"
    assert attrs.color == "Grey"
    assert attrs.size == "L"


def test_missing_fields_stay_unknown_not_guessed():
    attrs = extract_attributes("Mystery Item")
    assert attrs.brand is None
    assert attrs.color is None
    assert attrs.confidence == 0.0


def test_brand_surface_variants_normalize_to_same_form():
    a = extract_attributes("Levi's 511 Slim Fit Jeans Blue Denim 32")
    b = extract_attributes("Levis Men Blue Denim Slim Jeans Size: 32")
    assert a.brand == b.brand == "Levi's"


def test_eu_to_us_size_conversion():
    assert normalize_size_token("42") == "US 8.5"
    assert normalize_size_token("9") == "US 9"


if __name__ == "__main__":
    test_extracts_brand_color_size()
    test_extracts_material_and_letter_size()
    test_missing_fields_stay_unknown_not_guessed()
    test_brand_surface_variants_normalize_to_same_form()
    test_eu_to_us_size_conversion()
    print("All attribute_extractor tests passed.")
