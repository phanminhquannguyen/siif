import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
import time

# This will automatically download and manage the appropriate ChromeDriver
service = webdriver.chrome.service.Service()
chrome_options = Options()
# Set the page load strategy to 'eager' or 'none'
chrome_options.page_load_strategy = 'eager'  # 'none' is also an option

# Add the following arguments to run headless
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service = service, options=chrome_options)

ticker = input("Pass in your ticker: ")

try:

    # Retrieve Income statement
    # Navigate to the Yahoo Finance homepage
    driver.get(f"https://au.finance.yahoo.com/quote/{ticker}/financials/")

    expand_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.link2-btn[data-ylk*='expand']"))
    )
    
    # Click the button
    expand_button.click()

    # --- Wait for the table to be present ---
    # We will wait up to 20 seconds for the main table container to be visible.
    # This ensures we don't try to scrape data before it has loaded.
    print("Waiting for the financial data table to load...")
    table_container = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.tableContainer"))
    )
    print("Table found. Starting scrape.")

    # --- 1. Scrape the Headers ---
    # Find all header columns within the tableHeader div
    header_elements = table_container.find_elements(By.CSS_SELECTOR, ".tableHeader .column")
    # Extract the text from each header element
    headers = [header.text for header in header_elements]

    # --- 2. Scrape the Table Body Rows ---
    all_rows_data = []
    # Find all row divs within the tableBody div
    row_elements = table_container.find_elements(By.CSS_SELECTOR, ".tableBody .row")

    for row_element in row_elements:
        # For each row, get the title from the 'sticky' column first
        # This is more reliable than assuming it's always the first element
        try:
            row_title = row_element.find_element(By.CSS_SELECTOR, "div.rowTitle").text
        except:
            # Handle cases where a row might not have a title (if any)
            row_title = "N/A"
            
        # Get all the data columns (the ones that are not the title column)
        data_columns = row_element.find_elements(By.CSS_SELECTOR, "div.column:not(.sticky)")
        
        # Extract the text from each data column
        row_values = [col.text for col in data_columns]
        
        # Combine the title and the values to form a full row
        full_row = [row_title] + row_values
        all_rows_data.append(full_row)

    # --- 3. Build the Pandas DataFrame ---
    # Create the DataFrame using the scraped rows and headers
    df = pd.DataFrame(all_rows_data, columns=headers)

    # --- Display the result ---
    print("\n--- Scraped Financial Data ---")
    print(df)
    print("\nScraping completed successfully.")

    # You can also save the data to a CSV file
    df.to_csv('financial_data.csv', index=False)
    print("\nData saved to financial_data.csv")

    #---------------------------------------------------------------------------------

    # Retrieve Cash Flow
    # Navigate to the Yahoo Finance homepage
    driver.get(f"https://au.finance.yahoo.com/quote/{ticker}/cash-flow/")

    expand_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.link2-btn[data-ylk*='expand']"))
    )
    
    # Click the button
    expand_button.click()

    print("Waiting for the financial data table to load...")
    table_container = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.tableContainer"))
    )

    # --- 1. Scrape the Headers ---
    # Find all header columns within the tableHeader div
    header_elements = table_container.find_elements(By.CSS_SELECTOR, ".tableHeader .column")
    # Extract the text from each header element
    headers = [header.text for header in header_elements]

    # --- 2. Scrape the Table Body Rows ---
    all_rows_data = []
    # Find all row divs within the tableBody div
    row_elements = table_container.find_elements(By.CSS_SELECTOR, ".tableBody .row")

    for row_element in row_elements:
        # For each row, get the title from the 'sticky' column first
        # This is more reliable than assuming it's always the first element
        try:
            row_title = row_element.find_element(By.CSS_SELECTOR, "div.rowTitle").text
        except:
            # Handle cases where a row might not have a title (if any)
            row_title = "N/A"
            
        # Get all the data columns (the ones that are not the title column)
        data_columns = row_element.find_elements(By.CSS_SELECTOR, "div.column:not(.sticky)")
        
        # Extract the text from each data column
        row_values = [col.text for col in data_columns]
        
        # Combine the title and the values to form a full row
        full_row = [row_title] + row_values
        all_rows_data.append(full_row)

    # --- 3. Build the Pandas DataFrame ---
    # Create the DataFrame using the scraped rows and headers
    df = pd.DataFrame(all_rows_data, columns=headers)

    # You can also save the data to a CSV file
    df.to_csv('CashFlow.csv', index=False)

    #---------------------------------------------------------------------------------

    # Retrieve Balance Sheet

    # Navigate to the Yahoo Finance homepage
    driver.get(f"https://au.finance.yahoo.com/quote/{ticker}/balance-sheet/")

    expand_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.link2-btn[data-ylk*='expand']"))
    )
    
    # Click the button
    expand_button.click()


    print("Waiting for the financial data table to load...")
    table_container = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.tableContainer"))
    )

    # --- 1. Scrape the Headers ---
    # Find all header columns within the tableHeader div
    header_elements = table_container.find_elements(By.CSS_SELECTOR, ".tableHeader .column")
    # Extract the text from each header element
    headers = [header.text for header in header_elements]

    # --- 2. Scrape the Table Body Rows ---
    all_rows_data = []
    # Find all row divs within the tableBody div
    row_elements = table_container.find_elements(By.CSS_SELECTOR, ".tableBody .row")

    for row_element in row_elements:
        # For each row, get the title from the 'sticky' column first
        # This is more reliable than assuming it's always the first element
        try:
            row_title = row_element.find_element(By.CSS_SELECTOR, "div.rowTitle").text
        except:
            # Handle cases where a row might not have a title (if any)
            row_title = "N/A"
            
        # Get all the data columns (the ones that are not the title column)
        data_columns = row_element.find_elements(By.CSS_SELECTOR, "div.column:not(.sticky)")
        
        # Extract the text from each data column
        row_values = [col.text for col in data_columns]
        
        # Combine the title and the values to form a full row
        full_row = [row_title] + row_values
        all_rows_data.append(full_row)

    # --- 3. Build the Pandas DataFrame ---
    # Create the DataFrame using the scraped rows and headers
    df = pd.DataFrame(all_rows_data, columns=headers)

    # You can also save the data to a CSV file
    df.to_csv('BalanceSheet.csv', index=False)



except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # --- Clean up and close the browser ---
    print("Closing the browser.")
    driver.quit()