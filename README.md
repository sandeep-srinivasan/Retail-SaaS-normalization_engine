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
code. It does persist its output to SQLite (`normalization.db`), so it is a
genuinely working system rather than a script that only prints JSON — but it
still does **not** include:

- A message queue or streaming ingestion. It runs in batch, in-process,
  against `sample_data.json` or any JSON file you point it at.
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
- Postgres. SQLite is used so the prototype has zero setup cost; `db.py` is
  written so that swapping in a real Postgres connection is a change to the
  connection object, not to the calling code or SQL shape.

**A bug worth being upfront about:** the first version of `canonical_id`
generation used `uuid4()`, which meant re-running the pipeline against the
same input silently duplicated rows in storage instead of updating them,
since every run minted fresh, unrelated IDs for the same real-world products.
`main.py` now derives `canonical_id` from a hash of the cluster's underlying
listings, so the same input always resolves to the same ID and reruns are
genuinely idempotent. `tests/test_db.py::test_full_pipeline_rerun_is_idempotent`
exercises this against the real pipeline path specifically because the
original unit test (`test_rerunning_pipeline_is_idempotent`) used a
hardcoded ID and would not have caught the bug.

## Running it

No external dependencies; standard library only (SQLite is part of the
Python standard library via `sqlite3`).

```bash
cd normalization_engine
python3 main.py                    # runs against sample_data.json, persists to normalization.db
python3 main.py path/to/other.json # or against your own input
python3 main.py --db custom.db     # persist to a specific db file
python3 main.py --no-db            # skip persistence, print only

python3 tests/test_attributes.py
python3 tests/test_dedup.py
python3 tests/test_db.py
```

Re-running `main.py` against the same input is idempotent: `canonical_id` is
derived from the underlying listings' content, so the same real-world
product resolves to the same row on every run rather than being duplicated
(see "A bug worth being upfront about" below).

## How this would plug into the full pipeline

In the architecture described in the design document, this logic would live
inside the "Normalization & Enrichment Workers" consuming from the
`raw.products` Kafka topic. `RawProduct` in `schema.py` maps onto the message
schema on that topic; `CanonicalProduct` maps onto a write into the
`canonical_product` / `product_variant` / `platform_listing` tables, which
`db.py` already approximates with real SQL (simplified to two tables rather
than three, and SQLite rather than Postgres). The `cluster_products` function
in `dedup.py` would need to be reworked from a batch, in-memory operation
into an incremental one, matching each new record against existing canonical
products already in the database rather than reclustering from scratch, and
using a blocking key (brand + coarse category) to avoid comparing every new
record against the entire catalog.

## Files

```
normalization_engine/
├── schema.py               # RawProduct / ExtractedAttributes / CanonicalProduct
├── attribute_extractor.py  # title -> structured attributes
├── dedup.py                # clustering of likely-duplicate raw records
├── db.py                   # SQLite persistence (canonical_product, platform_listing)
├── main.py                 # end-to-end pipeline runner: load -> cluster -> extract -> persist
├── sample_data.json        # nine messy, cross-platform sample listings
├── requirements.txt        # empty on purpose - stdlib only
└── tests/
    ├── test_attributes.py
    ├── test_dedup.py
    └── test_db.py           # persistence + end-to-end idempotency
```
