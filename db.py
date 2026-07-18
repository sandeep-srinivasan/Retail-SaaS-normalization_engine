"""
SQLite persistence for the normalization pipeline's output.

This is the piece that turns the prototype from a script that prints JSON
into something closer to a genuinely working system: canonical products and
their listings are actually stored, queryable, and survive between runs,
rather than existing only for the duration of one `python main.py` call.

Schema mirrors `canonical_product` / `platform_listing` from the design
document's data model (section 1.4), simplified to fit a single-file
prototype (variants and listings are collapsed into one listings table,
since the sample data has no independent variant dimension worth splitting
out on its own). SQLite is used rather than Postgres so the prototype has
zero setup cost; `store()` is written so that swapping in a real Postgres
connection later is a matter of changing the connection object, not the
calling code.
"""

import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS canonical_product (
    canonical_id    TEXT PRIMARY KEY,
    display_title   TEXT NOT NULL,
    brand           TEXT,
    color           TEXT,
    size            TEXT,
    material        TEXT,
    confidence      REAL,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_listing (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id    TEXT NOT NULL REFERENCES canonical_product(canonical_id),
    platform        TEXT NOT NULL,
    raw_title       TEXT NOT NULL,
    price           REAL,
    rating          REAL,
    source_url      TEXT,
    UNIQUE(canonical_id, platform, raw_title)
);

CREATE INDEX IF NOT EXISTS idx_listing_canonical ON platform_listing(canonical_id);
CREATE INDEX IF NOT EXISTS idx_product_brand ON canonical_product(brand);
"""


@contextmanager
def connect(db_path: str = "normalization.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = "normalization.db"):
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def store_canonical_products(canonical_products, db_path: str = "normalization.db"):
    """Upserts canonical products and their listings. Re-running the pipeline
    against the same data is idempotent: canonical products are replaced by
    id, and duplicate listing rows are skipped via the UNIQUE constraint
    rather than erroring the whole batch."""
    init_db(db_path)

    with connect(db_path) as conn:
        for cp in canonical_products:
            conn.execute(
                """
                INSERT INTO canonical_product
                    (canonical_id, display_title, brand, color, size, material, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_id) DO UPDATE SET
                    display_title=excluded.display_title,
                    brand=excluded.brand,
                    color=excluded.color,
                    size=excluded.size,
                    material=excluded.material,
                    confidence=excluded.confidence
                """,
                (
                    cp.canonical_id,
                    cp.display_title,
                    cp.brand,
                    cp.attributes.color,
                    cp.attributes.size,
                    cp.attributes.material,
                    cp.attributes.confidence,
                ),
            )
            for listing in cp.listings:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO platform_listing
                        (canonical_id, platform, raw_title, price, rating, source_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cp.canonical_id,
                        listing.platform,
                        listing.raw_title,
                        listing.price,
                        listing.rating,
                        listing.source_url,
                    ),
                )


def fetch_all_products(db_path: str = "normalization.db"):
    """Reads canonical products back out, joined with their listings — a
    sanity check that what was written is actually queryable, not just
    write-only."""
    with connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        products = conn.execute("SELECT * FROM canonical_product").fetchall()
        result = []
        for p in products:
            listings = conn.execute(
                "SELECT platform, raw_title, price, rating FROM platform_listing WHERE canonical_id = ?",
                (p["canonical_id"],),
            ).fetchall()
            result.append({**dict(p), "listings": [dict(l) for l in listings]})
        return result
