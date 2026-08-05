# Indian D2C Skincare Brand Health Tracker

An end-to-end data analytics project: a self-scraped, weekly-updated
dataset tracking price, rating, and review sentiment across Indian D2C
skincare brands, with a custom Brand Vulnerability Score and a Power BI
dashboard.

## What this project does
- Scrapes product price/rating/review-count and individual reviews for
  6 brands (12 products) from Nykaa.com, on a schedule
- Stores everything in PostgreSQL as a proper longitudinal (time-series)
  dataset - each weekly scrape adds new dated rows, it doesn't overwrite
- Scores every review's sentiment with VADER
- Computes KPIs: price-vs-category-average, sentiment by brand, top
  complaint keywords, and (once 2+ weeks of data exist) a rating trend
  slope, review velocity, and a combined Brand Vulnerability Score
- Visualizes everything in a 2-page Power BI dashboard

## Why Nykaa instead of Amazon
Amazon.in's robots.txt disallows automated access to product pages,
which conflicts with the "respect robots.txt" principle this project
follows. Nykaa was the originally-planned fallback source, its product
pages allow automated access, and it has the same fields (price, rating,
review count, review text).

## Why Selenium instead of plain requests
Nykaa blocks plain HTTP requests (even with realistic browser headers)
with a 403 - it can tell there's no real browser/TLS handshake behind
them. Driving an actual Chrome instance via Selenium resolves this, since
the fingerprint is genuinely a browser's.

## Tech stack
Python (requests/Selenium, BeautifulSoup, pandas) -> PostgreSQL ->
VADER sentiment -> scipy (trend regression) -> Power BI

## Project structure
```
schema.sql               Postgres schema (brands, products, snapshots, reviews)
views.sql                Flattened views for Power BI to connect to
db_config.example.py     Copy to db_config.py and fill in your credentials
setup_db.py              Creates the tables from schema.sql

product_urls.csv         Seed list of product URLs to track
scraper.py                Scrapes price/rating/review_count -> snapshots_raw.csv
load_to_db.py              Loads snapshots_raw.csv into Postgres

reviews_scraper.py        Scrapes individual reviews -> reviews_raw.csv
load_reviews_to_db.py       Loads reviews into Postgres + scores sentiment (VADER)

eda_kpis.py               Price/rating/sentiment KPIs + complaint keywords
stats.py                  Rating trend slope + review velocity (needs 2+ snapshot dates)
vulnerability_score.py    Combined Brand Vulnerability Score (needs 2+ weeks of data)

debug_review_page.py      One-off diagnostic used while building the review scraper
```

## Setup
1. Create a Postgres database called `d2c_tracker` (e.g. via pgAdmin)
2. Copy `db_config.example.py` to `db_config.py` and fill in your real
   credentials (this file is gitignored - never commit real credentials)
3. `pip install -r requirements.txt`
4. `python setup_db.py`
5. In pgAdmin's Query Tool, run `views.sql` once to create the Power BI views

## Weekly run (do this every week for 3-4 weeks to build a real trend)
```
python scraper.py
python load_to_db.py
python reviews_scraper.py
python load_reviews_to_db.py
python eda_kpis.py
python stats.py
python vulnerability_score.py
```
`stats.py` and `vulnerability_score.py` will report "not enough data yet"
until you have 2+ distinct snapshot dates in the database - that's
expected on week 1, and starts producing real numbers from week 2 on.

## Power BI dashboard
Connect Power BI Desktop to Postgres (Get Data -> PostgreSQL database),
load `vw_snapshot_summary` and `vw_review_summary`. Two pages:
- **Overview**: average rating by brand, price-vs-rating scatter, total
  review volume
- **Drill-down**: brand slicer, average sentiment by brand, a table of
  the lowest-sentiment reviews (what people are actually complaining about)

## Interview notes
- **Why this project?** Built a self-scraped longitudinal dataset instead
  of a pre-packaged Kaggle CSV, and designed a custom metric (Vulnerability
  Score) instead of just reporting standard KPIs.
- **What was hard?** Two real obstacles, both solved and documented in
  the code: (1) Amazon's robots.txt blocked the originally-planned source,
  requiring a pivot to Nykaa; (2) Nykaa's bot-detection blocked plain HTTP
  requests, requiring a switch to Selenium, and building the review-text
  extraction regex against the real rendered DOM (not a markdown-rendered
  preview, which included formatting artifacts that don't exist on the
  live page).
- **Why equal weighting on the Vulnerability Score?** Simple and
  interpretable with limited historical data; the plan is to validate
  weights by regressing the score against actual subsequent rating drops
  once more weekly snapshots exist.
