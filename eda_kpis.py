"""
Week 3, the parts that don't need multiple weeks of snapshots yet:
- price vs. rating (who's overpriced relative to perceived quality)
- sentiment by brand (from the reviews you already scraped)
- top negative-review keywords per brand (what people actually complain about)

The trend-based pieces (rating slope over time, review velocity decline,
Vulnerability Score) need 2+ different snapshot_dates in the database -
run this again after your next weekly scraper.py re-run and you can add
those on top of this script.

Usage:
    python eda_kpis.py

Outputs:
    - price_vs_rating.png
    - sentiment_by_brand.png
    - a printed KPI summary + top complaint keywords per brand
"""

import re
import warnings
from collections import Counter

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no GUI needed, just save PNGs
import matplotlib.pyplot as plt
import psycopg2

from db_config import DB_CONFIG

warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")

STOPWORDS = set("""
the a an and or but is are was were be been being this that these those
it its it's for of to in on at with as by from into over under skin very
i my me we our you your good nice great product use used using also just
so too not no all one get got will can much more most really so its
""".split())


def load_data():
    conn = psycopg2.connect(**DB_CONFIG)

    snapshots = pd.read_sql(
        """
        SELECT b.brand_name, p.product_name, p.category, s.price, s.avg_rating,
               s.review_count, s.snapshot_date
        FROM snapshots s
        JOIN products p ON s.product_id = p.product_id
        JOIN brands b ON p.brand_id = b.brand_id
        """,
        conn,
    )

    reviews = pd.read_sql(
        """
        SELECT b.brand_name, p.product_name, r.review_text, r.review_rating,
               r.sentiment_score
        FROM reviews r
        JOIN products p ON r.product_id = p.product_id
        JOIN brands b ON p.brand_id = b.brand_id
        """,
        conn,
    )

    conn.close()
    return snapshots, reviews


def price_vs_rating_chart(snapshots: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 6))
    for brand, group in snapshots.groupby("brand_name"):
        ax.scatter(group["avg_rating"], group["price"], label=brand, s=80)
    ax.set_xlabel("Average Rating")
    ax.set_ylabel("Price (₹)")
    ax.set_title("Price vs. Rating by Brand")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig("price_vs_rating.png", dpi=150)
    print("Saved price_vs_rating.png")


def sentiment_by_brand_chart(reviews: pd.DataFrame):
    avg_sentiment = (
        reviews.groupby("brand_name")["sentiment_score"].mean().sort_values()
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#d62728" if v < 0.3 else "#2ca02c" for v in avg_sentiment]
    ax.barh(avg_sentiment.index, avg_sentiment.values, color=colors)
    ax.set_xlabel("Average Review Sentiment (-1 to +1)")
    ax.set_title("Average Sentiment by Brand")
    fig.tight_layout()
    fig.savefig("sentiment_by_brand.png", dpi=150)
    print("Saved sentiment_by_brand.png")


def price_vs_category_average(snapshots: pd.DataFrame):
    snapshots = snapshots.copy()
    cat_avg = snapshots.groupby("category")["price"].transform("mean")
    snapshots["price_vs_category_avg_pct"] = (
        (snapshots["price"] - cat_avg) / cat_avg * 100
    )
    return snapshots[
        ["brand_name", "product_name", "category", "price",
         "price_vs_category_avg_pct"]
    ].sort_values("price_vs_category_avg_pct", ascending=False)


def top_negative_keywords(reviews: pd.DataFrame, brand: str, n=8):
    neg = reviews[
        (reviews["brand_name"] == brand) & (reviews["sentiment_score"] < -0.05)
    ]
    words = []
    for text in neg["review_text"].dropna():
        for w in re.findall(r"[a-zA-Z]+", text.lower()):
            if len(w) > 3 and w not in STOPWORDS:
                words.append(w)
    return Counter(words).most_common(n)


def main():
    snapshots, reviews = load_data()

    print("=" * 60)
    print("KPI SUMMARY")
    print("=" * 60)

    print("\n--- Avg price / rating / review count by brand ---")
    summary = (
        snapshots.groupby("brand_name")
        .agg(avg_price=("price", "mean"),
             avg_rating=("avg_rating", "mean"),
             total_reviews=("review_count", "sum"))
        .round(1)
        .sort_values("avg_rating", ascending=False)
    )
    print(summary.to_string())

    print("\n--- Price vs. category average (overpriced check) ---")
    print(price_vs_category_average(snapshots).round(1).to_string(index=False))

    print("\n--- Average sentiment by brand ---")
    sentiment_summary = (
        reviews.groupby("brand_name")["sentiment_score"].mean().round(3)
        .sort_values()
    )
    print(sentiment_summary.to_string())

    print("\n--- Top negative-review keywords per brand ---")
    for brand in reviews["brand_name"].unique():
        kws = top_negative_keywords(reviews, brand)
        if kws:
            kw_str = ", ".join(f"{w}({c})" for w, c in kws)
            print(f"  {brand}: {kw_str}")
        else:
            print(f"  {brand}: no notably negative reviews found")

    price_vs_rating_chart(snapshots)
    sentiment_by_brand_chart(reviews)

    print("\nDone. Charts saved as PNGs in this folder.")


if __name__ == "__main__":
    main()
