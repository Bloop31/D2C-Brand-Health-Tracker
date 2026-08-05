"""
Loads reviews_raw.csv into Postgres and scores each review with VADER
sentiment (compound score, -1 to +1). Safe to re-run - skips a review if
the exact same text already exists for that product.

Usage:
    python load_reviews_to_db.py
"""

import csv
from datetime import datetime

import psycopg2
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from db_config import DB_CONFIG

analyzer = SentimentIntensityAnalyzer()

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()


def get_product_id(product_url: str):
    cur.execute("SELECT product_id FROM products WHERE product_url = %s", (product_url,))
    row = cur.fetchone()
    return row[0] if row else None


def main():
    with open("reviews_raw.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    inserted = 0
    skipped_no_product = 0
    skipped_duplicate = 0

    for row in rows:
        product_id = get_product_id(row["product_url"])
        if product_id is None:
            # this product hasn't been through load_to_db.py yet -
            # run that first so the product row exists
            skipped_no_product += 1
            continue

        # skip exact duplicate review text for this product
        cur.execute(
            "SELECT 1 FROM reviews WHERE product_id = %s AND review_text = %s",
            (product_id, row["review_text"]),
        )
        if cur.fetchone():
            skipped_duplicate += 1
            continue

        try:
            review_date = datetime.strptime(row["review_date"], "%d/%m/%Y").date()
        except ValueError:
            review_date = None

        sentiment = analyzer.polarity_scores(row["review_text"])["compound"]

        cur.execute(
            """
            INSERT INTO reviews (product_id, review_date, review_text, review_rating, sentiment_score)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (product_id, review_date, row["review_text"], int(row["review_rating"]), sentiment),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Inserted {inserted} new reviews with sentiment scores.")
    if skipped_no_product:
        print(f"Skipped {skipped_no_product} rows - product not in database yet "
              f"(run load_to_db.py first).")
    if skipped_duplicate:
        print(f"Skipped {skipped_duplicate} duplicate reviews already in the database.")


if __name__ == "__main__":
    main()
