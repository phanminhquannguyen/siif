import os
import time
import pandas as pd
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- Driver ----------
def make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        # New headless is more stable
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    # Selenium Manager (built-in) will fetch a compatible driver automatically:
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    return driver

# ---------- Helpers ----------
def asx_to_yahoo_symbol(ticker: str) -> str:
    t = ticker.strip().upper()
    # If already has a suffix, keep it. Otherwise append .AX
    return t if "." in t else f"{t}.AX"

def scrape_fin_table(driver: webdriver.Chrome, url: str, out_csv: Path) -> pd.DataFrame:
    driver.get(url)

    wait = WebDriverWait(driver, 30)

    # Try clicking "Expand" if present, but don't fail if it’s missing
    try:
        # Common patterns Yahoo uses (may change over time)
        expand_candidates = [
            (By.CSS_SELECTOR, "button[aria-label*='Expand']"),
            (By.CSS_SELECTOR, "button[data-ylk*='expand']"),
            (By.XPATH, "//button[contains(., 'Expand')]"),
        ]
        for how, sel in expand_candidates:
            try:
                btn = wait.until(EC.element_to_be_clickable((how, sel)))
                btn.click()
                time.sleep(0.5)
                break
            except Exception:
                continue
    except Exception:
        pass

    # Wait for the table container
    table = wait.until(
        EC.presence_of_element_located(
            # Try a few robust hooks
            (By.CSS_SELECTOR, "div.tableContainer, section[data-testid='financials'], div#Main")
        )
    )

    # Grab headers (years/periods). Keep it tolerant.
    header_texts = []
    for css in [
        ".tableHeader .column",                    # older
        "div[role='columnheader']",                # aria
        "div.tableHeader div",                     # fallback
    ]:
        els = table.find_elements(By.CSS_SELECTOR, css)
        header_texts = [e.text.strip() for e in els if e.text.strip()]
        if header_texts:
            break

    # Make sure we have a label for the metric/title column
    if header_texts:
        if header_texts[0].lower() not in {"metric", "breakdown", "account", "item"}:
            headers = ["Metric"] + header_texts[1:]
        else:
            headers = header_texts
    else:
        # Fallback if headers not captured
        headers = ["Metric"]

    # Rows
    rows = []
    row_blocks = table.find_elements(By.CSS_SELECTOR, ".tableBody .row, [data-test='fin-row']")
    for r in row_blocks:
        # Metric / row title
        title = ""
        for css in ["div.rowTitle", ".sticky", "[data-test='fin-col']"]:
            try:
                title_el = r.find_element(By.CSS_SELECTOR, css)
                if title_el.text.strip():
                    title = title_el.text.strip()
                    break
            except Exception:
                continue
        if not title:
            # last resort
            title = (r.text.split("\n", 1)[0] or "N/A").strip()

        # Data cells (exclude sticky/title)
        data_cells = r.find_elements(By.CSS_SELECTOR, "div.column:not(.sticky), [data-test='fin-col']")
        values = [c.text.strip() for c in data_cells if c.text.strip()]

        row = [title] + values
        rows.append(row)

    # Normalize row widths to match headers
    max_len = max((len(r) for r in rows), default=1)
    if len(headers) < max_len:
        # extend headers with placeholders
        headers = (headers + [f"Col{i}" for i in range(len(headers), max_len)])[:max_len]
    elif len(headers) > max_len:
        headers = headers[:max_len]

    df = pd.DataFrame(rows, columns=headers)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    return df

# ---------- Orchestrator ----------
def get_financial_data(ticker: str, base_dir: Path | None = None):
    y_ticker = asx_to_yahoo_symbol(ticker)
    base = (base_dir or (Path.cwd() / "company_data" / ticker.upper()))
    base.mkdir(parents=True, exist_ok=True)

    driver = make_driver(headless=True)
    try:
        print(f"Saving outputs to: {base}")

        urls = {
            "financials": f"https://au.finance.yahoo.com/quote/{y_ticker}/financials/",
            "cash_flow":  f"https://au.finance.yahoo.com/quote/{y_ticker}/cash-flow/",
            "balance":    f"https://au.finance.yahoo.com/quote/{y_ticker}/balance-sheet/",
        }
        outputs = {
            "financials": base / "IncomeStatement.csv",
            "cash_flow":  base / "CashFlow.csv",
            "balance":    base / "BalanceSheet.csv",
        }

        for key in ["financials", "cash_flow", "balance"]:
            print(f"Scraping {key} …")
            df = scrape_fin_table(driver, urls[key], outputs[key])
            print(f"Saved {key} → {outputs[key]} (rows={len(df)})")

    finally:
        print("Closing the browser.")
        driver.quit()

# Example:
# get_financial_data("CBA")  # will use CBA.AX