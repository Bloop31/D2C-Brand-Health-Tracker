"""
One-off diagnostic: opens a single review page and saves exactly what
Selenium sees (the real rendered text) to review_page_debug.txt, so we can
build the review-extraction regex against ground truth instead of guessing.

Usage:
    python debug_review_page.py
"""

import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://www.nykaa.com/minimalist-light-fluid-spf-50-face-sunscreen/reviews/20540004"

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

driver.get(URL)
WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
time.sleep(3)

# scroll down a bit in case reviews lazy-load on scroll
driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
time.sleep(2)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5);")
time.sleep(2)

page_text = driver.find_element(By.TAG_NAME, "body").text

with open("review_page_debug.txt", "w", encoding="utf-8") as f:
    f.write(page_text)

print(f"Saved {len(page_text)} characters to review_page_debug.txt")
print("\n--- first 2000 characters ---\n")
print(page_text[:2000])

driver.quit()
