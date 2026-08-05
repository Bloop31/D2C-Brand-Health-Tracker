"""
Computes, per product, the linear-regression trend slope of avg_rating
over time (rating_trend_slope from the original plan). Needs at least 2
different snapshot_dates per product to compute anything - with only one
snapshot, it correctly reports "not enough data yet" instead of a fake 0.

Usage:
    python stats.py

Run this after every weekly scraper.py re-run - the more snapshot dates
you have, the more reliable the slope becomes.
"""

import warnings
import pandas as pd
from scipy import stats as scipy_stats
import psycopg2

from db_config import DB_CONFIG

warnings.filterwarnings("ignore", message=".*only supports SQLAlchemy.*")


def load_snapshots() -> pd.DataFrame:
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(
        """
        SELECT b.brand_name, p.product_name, p.product_id,
               s.snapshot_date, s.avg_rating, s.review_count
        FROM snapshots s
        JOIN products p ON s.product_id = p.product_id
        JOIN brands b ON p.brand_id = b.brand_id
        ORDER BY p.product_id, s.snapshot_date
        """,
        conn,
    )
    conn.close()
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    return df


def rating_trend_slope(product_df: pd.DataFrame):
    """Returns (slope, n_snapshots). Slope is rating-points-per-day.
    None if fewer than 2 distinct dates exist yet."""
    dates = product_df["snapshot_date"].unique()
    if len(dates) < 2:
        return None, len(dates)

    x = (product_df["snapshot_date"] - product_df["snapshot_date"].min()).dt.days
    y = product_df["avg_rating"]
    slope, intercept, r, p, stderr = scipy_stats.linregress(x, y)
    return slope, len(dates)


def review_velocity_change(product_df: pd.DataFrame):
    """Change in review_count between the first and most recent snapshot.
    None if fewer than 2 distinct dates exist yet."""
    dates = sorted(product_df["snapshot_date"].unique())
    if len(dates) < 2:
        return None
    first = product_df[product_df["snapshot_date"] == dates[0]]["review_count"].iloc[0]
    last = product_df[product_df["snapshot_date"] == dates[-1]]["review_count"].iloc[0]
    if first in (0, None) or pd.isna(first):
        return None
    return (last - first) / first * 100  # % change


def main():
    df = load_snapshots()
    n_dates = df["snapshot_date"].nunique()

    print("=" * 60)
    print("TREND STATS")
    print("=" * 60)
    print(f"\nDistinct snapshot dates in the database so far: {n_dates}")

    if n_dates < 2:
        print(
            "\nOnly one snapshot date exists - rating trend slope and review "
            "velocity can't be computed yet (need at least 2 different dates "
            "to draw a line through). Re-run scraper.py + load_to_db.py next "
            "week, then run this script again."
        )
        return

    print("\n--- Per-product rating trend (points/day) & review velocity ---")
    rows = []
    for product_id, group in df.groupby("product_id"):
        brand = group["brand_name"].iloc[0]
        name = group["product_name"].iloc[0]
        slope, n = rating_trend_slope(group)
        velocity = review_velocity_change(group)
        rows.append(
            {
                "brand": brand,
                "product": name,
                "n_snapshots": n,
                "rating_trend_slope": round(slope, 5) if slope is not None else None,
                "review_velocity_pct_change": round(velocity, 1) if velocity is not None else None,
            }
        )

    result = pd.DataFrame(rows)
    print(result.to_string(index=False))

    print("\n--- Per-brand average trend slope ---")
    brand_slopes = (
        result.dropna(subset=["rating_trend_slope"])
        .groupby("brand")["rating_trend_slope"]
        .mean()
        .sort_values()
    )
    if brand_slopes.empty:
        print("No brand has 2+ snapshot dates yet.")
    else:
        print(brand_slopes.round(5).to_string())


if __name__ == "__main__":
    main()
