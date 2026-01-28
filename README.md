# siif
# SIIF - Financial Dashboard

A comprehensive Streamlit-based financial dashboard for analyzing Australian Securities Exchange (ASX) companies. This application provides tools for financial data comparison, industry peer analysis, and company similarity detection based on financial metrics.

## Features

- **Financial Data Dashboard**: Interactive visualization of key financial metrics
- **Company Comparison**: Find companies with similar financial characteristics
- **Industry Analysis**: Compare companies within the same industry/sector
- **Sector Averages**: View industry benchmarks and contributing companies
- **Report Analysis**: AI-powered financial report analysis (coming soon)

## 📁 Project Structure

### Core Application Files

#### `dashboard/dashboard.py`
Main Streamlit application file containing:
- **Supabase Integration**: Database connection and data loading
- **User Interface**: Interactive dashboard with financial data tables
- **Navigation System**: Multi-page application (Financial Dashboard, Report Analyst)
- **Data Visualization**: Table layouts with metrics, values, and comparisons

#### `dashboard/utils.py`
Utility functions for data processing and analysis:
- **`format_number()`**: Formats numeric values for display
- **`find_similar_companies()`**: Identifies companies with similar financial metrics
- **`get_industry_companies_with_metrics()`**: Finds industry peers with metric values
- **`get_financial_data()`**: Fetches financial data from Yahoo Finance API

### Data Processing Files

#### `data_agg.ipynb`
Jupyter notebook for data aggregation and preprocessing:
- **Yahoo Finance Data Collection**: Fetches financial statements for ASX companies
- **Data Cleaning**: Processes balance sheets, income statements, and cash flow data
- **Sector Analysis**: Calculates sector averages and industry benchmarks
- **Data Export**: Generates CSV files for dashboard consumption

### Configuration Files

#### `dashboard/definitions.json`
Financial metrics definitions and documentation:
- **Metric Definitions**: Detailed explanations of financial terms
- **Aliases**: Alternative names for financial metrics
- **Help System**: Powers the interactive "Notes" popover in the dashboard

#### `.gitignore`
Git configuration to exclude:
- Environment variables and secrets
- Python cache files
- Data files (CSV, JSON)
- IDE-specific files
- Temporary files



#### Company Data Directory (`company_data/`)
- **Individual Company Folders**: Each ASX ticker has its own folder
- **Financial Statements**: Balance sheet, income statement, and cash flow data
- **Raw Data**: JSON files with complete financial information from Yahoo Finance

#### Combined Data Directory (`combined_data/`)
- **`financial_data.csv`**: Consolidated income statement metrics for all companies
- **`cash_flow.csv`**: Combined cash flow statements with sector information
- **`balance_sheet.csv`**: Aggregated balance sheet data across companies
- **`sector_means.csv`**: Calculated sector averages for benchmarking

### External Data Sources



### Configuration
1. Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "our-supabase-url"
SUPABASE_KEY = "our-supabase-key"
```
Contact current director to have supabase access

2. Run data aggregation (since the data need to be updated every quarter)
```bash
jupyter notebook data_agg.ipynb
```

3. Launch the dashboard (locally)
```bash
streamlit run dashboard/dashboard.py
```

4. To update the production dashboard, the newly generated data in the `combined_data` folder must be manually uploaded to the SIIF Supabase database.

### Report Analysis
Coming soon :D!



