# Product Normalization Engine

A prototype for the "clean, structured catalog" stage of the Multi-Platform
Catalog Intelligence Engine (see `../Rubick_AI_Catalog_Intelligence_Engine_Design.pdf` for the full HLD/LLD).
It takes messy, platform-sourced product listings and resolves them into
deduplicated canonical products with structured attributes.

## Why this option

Of the three implementation options in the assignment, this one exercises the
part of the pipeline that most directly determines data quality: turning
"Nike Air Max Black 42" and "Nike Airmax Shoes Size 8 Black" into a single
product record. Crawling and API-serving are largely infrastructure work
already specified in the design document; this is the piece with the more
interesting logic.

## Scope and honest limitations

This is a prototype meant to be read in about fifteen minutes, not production
code. Specifically, it does **not** include:

- A database or queue. It runs in-memory against `sample_data.json`.
- A learned similarity model. Deduplication uses token-set overlap
  (`difflib.SequenceMatcher` over sorted, deduplicated tokens) plus a small
  brand/size/colour reconciliation layer, not embeddings. This works well on
  the sample data but would need a proper embedding-based approach (or at
  minimum a much larger controlled vocabulary and a blocking strategy) to
  hold up at real scale, where an O(n^2) comparison also stops being viable.
- A full size-conversion table. `EU_TO_US_SHOE` in `attribute_extractor.py`
  covers a handful of sizes as an illustration of the approach described in
  the design document; a production version would need a complete,
  category-aware conversion table.

## Running it

No external dependencies; standard library only.

```bash
cd Retail-SaaS-normalization_engine
python3 main.py                    # runs against sample_data.json
python3 main.py path/to/other.json # or against your own input

python3 tests/test_attributes.py
python3 tests/test_dedup.py
```

## How this would plug into the full pipeline

In the architecture described in the design document, this logic would live
inside the "Normalization & Enrichment Workers" consuming from the
`raw.products` Kafka topic. `RawProduct` in `schema.py` maps onto the message
schema on that topic; `CanonicalProduct` maps onto a write into the
`canonical_product` / `product_variant` / `platform_listing` tables. The
`cluster_products` function in `dedup.py` would need to be reworked from a
batch, in-memory operation into an incremental one, matching each new record
against existing canonical products already in Postgres rather than
reclustering from scratch, and using a blocking key (brand + coarse category)
to avoid comparing every new record against the entire catalog.

## Files

```
Retail-SaaS-normalization_engine/
├── schema.py               # RawProduct / ExtractedAttributes / CanonicalProduct
├── attribute_extractor.py  # title -> structured attributes
├── dedup.py                # clustering of likely-duplicate raw records
├── main.py                 # end-to-end pipeline runner
├── sample_data.json        # nine messy, cross-platform sample listings
├── requirements.txt        # empty on purpose - stdlib only
└── tests/
    ├── test_attributes.py
    └── test_dedup.py
```
