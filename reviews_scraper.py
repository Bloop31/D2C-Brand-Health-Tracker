"""
Scrapes reviews for each product in product_urls.csv from Nykaa's review
pages (same product, URL pattern swaps /p/<id> for /reviews/<id>).

Usage:
    python reviews_scraper.py

Appends rows to reviews_raw.csv: product_url, review_date, review_text,
review_rating. Sentiment scoring happens later in load_reviews_to_db.py,
matching the original plan's design (sentiment filled in during cleaning).

Run this whenever you run scraper.py - re-scraping reviews weekly means
you'll pick up newly posted reviews too, not just repeats.
"""

import csv
import re
import time
import random

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

INPUT_FILE = "product_urls.csv"
OUTPUT_FILE = "reviews_raw.csv"
MAX_REVIEWS_PER_PRODUCT = 20  # matches the original plan's 20-30 target

# Matches blocks like:
#   5
#   03/06/2026
#   "Excellent application"
#   Great work and I got free bees too.
#   Helpful
# Built and verified against real Selenium-rendered page text (not the
# markdown-formatted version web-fetch tools show, which adds artifacts
# like asterisks that never appear in the live DOM).
REVIEW_PATTERN = re.compile(
    r"(?:^|\n)(\d)\n"              # star rating, alone on its own line
    r"(\d{2}/\d{2}/\d{4})\n"       # date DD/MM/YYYY
    r'"([^"]*)"\n'                 # quoted title
    r"(.*?)\n"                     # body text
    r"Helpful",                    # up to the "Helpful" (vote) marker
    re.DOTALL,
)


def make_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def to_review_url(product_url: str) -> str:
    return product_url.replace("/p/", "/reviews/")


def scrape_reviews(driver, product_url: str) -> list:
    review_url = to_review_url(product_url)
    driver.get(review_url)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(3)
    # scroll partway down twice - some reviews lazy-load as you scroll
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5);")
    time.sleep(2)

    page_text = driver.find_element(By.TAG_NAME, "body").text
    matches = REVIEW_PATTERN.findall(page_text)

    reviews = []
    for rating, date_str, title, body in matches[:MAX_REVIEWS_PER_PRODUCT]:
        body_clean = re.sub(r"\.\.\.Read More\s*$", "", body.strip())
        full_text = f"{title.strip()}. {body_clean}".strip(". ").strip()
        reviews.append(
            {
                "product_url": product_url,
                "review_date": date_str,
                "review_text": full_text,
                "review_rating": int(rating),
            }
        )
    return reviews


def main():
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        products = list(csv.DictReader(f))

    print(f"Scraping reviews for {len(products)} products (Chrome window will open)...")
    driver = make_driver()
    all_reviews = []

    try:
        for i, row in enumerate(products, 1):
            url = row["product_url"]
            print(f"[{i}/{len(products)}] {url}")
            try:
                reviews = scrape_reviews(driver, url)
                all_reviews.extend(reviews)
                print(f"    -> found {len(reviews)} reviews")
            except Exception as e:
                print(f"    FAILED: {e}")
            time.sleep(random.uniform(2, 4))
    finally:
        driver.quit()

    file_exists = False
    try:
        with open(OUTPUT_FILE, "r"):
            file_exists = True
    except FileNotFoundError:
        pass

    fieldnames = ["product_url", "review_date", "review_text", "review_rating"]
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(all_reviews)

    print(f"\nDone. Appended {len(all_reviews)} reviews to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
