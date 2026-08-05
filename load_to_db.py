"""
Loads snapshots_raw.csv into your Postgres database (brands, products,
snapshots tables). Safe to re-run - brands/products are upserted. If a
snapshot for this product+date already exists but has a NULL price (e.g.
from an earlier failed scrape), it gets updated with the new data instead
of silently skipped - that's what caused the Minimalist/Mamaearth NaN bug.

Usage:
    python load_to_db.py
"""

import csv
import psycopg2
from db_config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()


def get_or_create_brand(brand_name: str) -> int:
    cur.execute(
        """
        INSERT INTO brands (brand_name) VALUES (%s)
        ON CONFLICT (brand_name) DO UPDATE SET brand_name = EXCLUDED.brand_name
        RETURNING brand_id
        """,
        (brand_name,),
    )
    return cur.fetchone()[0]


def get_or_create_product(brand_id: int, name: str, category: str, url: str) -> int:
    cur.execute(
        """
        INSERT INTO products (brand_id, product_name, category, product_url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (product_url) DO UPDATE SET product_name = EXCLUDED.product_name
        RETURNING product_id
        """,
        (brand_id, name, category, url),
    )
    return cur.fetchone()[0]


def main():
    with open("snapshots_raw.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = 0
    updated = 0
    for row in rows:
        brand_id = get_or_create_brand(row["brand"])
        product_id = get_or_create_product(
            brand_id,
            row.get("product_name") or "Unknown",
            row["category"],
            row["product_url"],
        )

        price = float(row["price"]) if row.get("price") else None
        rating = float(row["avg_rating"]) if row.get("avg_rating") else None
        reviews = int(row["review_count"]) if row.get("review_count") else None

        cur.execute(
            "SELECT snapshot_id, price FROM snapshots WHERE product_id = %s AND snapshot_date = %s",
            (product_id, row["snapshot_date"]),
        )
        existing = cur.fetchone()

        if existing is None:
            cur.execute(
                """
                INSERT INTO snapshots (product_id, snapshot_date, price, avg_rating, review_count)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (product_id, row["snapshot_date"], price, rating, reviews),
            )
            inserted += 1
        elif existing[1] is None and price is not None:
            # a prior row exists for this date but has no price (failed
            # scrape) - overwrite it now that we have real data
            cur.execute(
                """
                UPDATE snapshots SET price = %s, avg_rating = %s, review_count = %s
                WHERE snapshot_id = %s
                """,
                (price, rating, reviews, existing[0]),
            )
            updated += 1
        # else: a real snapshot already exists for this date - leave it alone

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {inserted} new snapshot rows, updated {updated} incomplete rows.")


if __name__ == "__main__":
    main()

