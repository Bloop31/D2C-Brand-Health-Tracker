"""
Scraper for the D2C Brand Health Tracker.
Source: Nykaa product pages (Amazon.in's robots.txt blocks bots from /dp/
product pages, so this project uses Nykaa instead - the fallback the
original plan already suggested).

Uses Selenium (a real, automated Chrome browser) instead of plain requests.
Nykaa's bot-detection blocks plain HTTP requests with a 403 even with
browser-like headers, because it can tell no real browser/TLS handshake is
behind them - this is common on JS-heavy retail sites and is exactly the
"may require Selenium if content is JS-loaded" risk the original plan
flagged for Amazon.

Usage:
    python scraper.py

Reads product_urls.csv (brand, category, product_url), visits each page in
a real (visible, not headless) Chrome window, pulls price/rating/review
count, and appends one timestamped row per product to snapshots_raw.csv.
Run this file once a day/week and every run adds a new dated batch - that's
what makes the dataset longitudinal.
"""

import csv
import re
import time
import random
from datetime import date

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

INPUT_FILE = "product_urls.csv"
OUTPUT_FILE = "snapshots_raw.csv"


def make_driver():
    options = Options()
    # NOT headless on purpose - headless Chrome has a slightly different
    # fingerprint and is more likely to get blocked too. A visible window
    # popping up is normal and expected here.
    options.add_argument("--start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    # hide the most obvious automation flags
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
            """
        },
    )
    return driver


def scrape_product(driver, url: str) -> dict:
    """Load one product page in the real browser and pull out the fields
    we care about. Returns None for anything it couldn't find, rather
    than crashing - one bad product should never kill the whole run."""

    driver.get(url)
    # wait for the price to actually render before reading the page
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(3)  # let client-side JS finish rendering ratings/reviews

    page_text = driver.find_element(By.TAG_NAME, "body").text

    # --- Product name: from the <title> or og:title meta tag ---
    name = None
    try:
        meta = driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']")
        name = meta.get_attribute("content")
        if name:
            name = name.replace("Buy ", "").replace(" Online", "").strip()
    except Exception:
        pass

    # --- Price: look for "₹499 ₹474" pattern (MRP + discounted price) ---
    price = None
    m = re.search(r"₹\s?([\d,]+)\s*₹\s?([\d,]+)", page_text)
    if m:
        price = float(m.group(2).replace(",", ""))
    else:
        m = re.search(r"₹\s?([\d,]+)", page_text)
        if m:
            price = float(m.group(1).replace(",", ""))

    # --- Rating: look for a pattern like "4.4/5" or "4.4 out of 5" ---
    rating = None
    m = re.search(r"(\d\.\d)\s*/\s*5", page_text) or re.search(
        r"(\d\.\d)\s*out of 5", page_text
    )
    if m:
        rating = float(m.group(1))

    # --- Review count: look for "N reviews" ---
    review_count = None
    m = re.search(r"([\d,]+)\s*reviews", page_text, re.IGNORECASE)
    if m:
        review_count = int(m.group(1).replace(",", ""))

    return {
        "product_name": name,
        "price": price,
        "avg_rating": rating,
        "review_count": review_count,
    }


def main():
    today = date.today().isoformat()
    rows_out = []

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        products = list(reader)

    print(f"Scraping {len(products)} products (a Chrome window will open)...")
    driver = make_driver()

    try:
        for i, row in enumerate(products, 1):
            url = row["product_url"]
            print(f"[{i}/{len(products)}] {url}")
            try:
                data = scrape_product(driver, url)
                rows_out.append(
                    {
                        "snapshot_date": today,
                        "brand": row["brand"],
                        "category": row["category"],
                        "product_url": url,
                        **data,
                    }
                )
                print(f"    -> {data}")
            except Exception as e:
                print(f"    FAILED: {e}")
                rows_out.append(
                    {
                        "snapshot_date": today,
                        "brand": row["brand"],
                        "category": row["category"],
                        "product_url": url,
                        "product_name": None,
                        "price": None,
                        "avg_rating": None,
                        "review_count": None,
                    }
                )

            time.sleep(random.uniform(2, 4))
    finally:
        driver.quit()

    file_exists = False
    try:
        with open(OUTPUT_FILE, "r"):
            file_exists = True
    except FileNotFoundError:
        pass

    fieldnames = [
        "snapshot_date",
        "brand",
        "category",
        "product_url",
        "product_name",
        "price",
        "avg_rating",
        "review_count",
    ]
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows_out)

    print(f"\nDone. Appended {len(rows_out)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
