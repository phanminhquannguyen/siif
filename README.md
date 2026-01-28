# siif
# SIIF - Financial Dashboard

A comprehensive Streamlit-based financial dashboard for analyzing Australian Securities Exchange (ASX) companies. This application provides tools for financial data comparison, industry peer analysis, and company similarity detection based on financial metrics.

## 🚀 Features

- **Financial Data Dashboard**: Interactive visualization of key financial metrics
- **Company Comparison**: Find companies with similar financial characteristics
- **Industry Analysis**: Compare companies within the same industry/sector
- **Sector Averages**: View industry benchmarks and contributing companies
- **Report Analysis**: AI-powered financial report analysis (via model integration)

## 📁 Project Structure

### Core Application Files

#### `dashboard/dashboard.py`
Main Streamlit application file containing:
- **Supabase Integration**: Database connection and data loading
- **User Interface**: Interactive dashboard with financial data tables
- **Navigation System**: Multi-page application (Financial Dashboard, Report Analyst)
- **Data Visualization**: Table layouts with metrics, values, and comparisons
- **Real-time Analysis**: Company similarity and industry peer analysis

#### `dashboard/utils.py`
Utility functions for data processing and analysis:
- **`format_number()`**: Formats numeric values for display
- **`find_similar_companies()`**: Identifies companies with similar financial metrics
- **`get_industry_companies_with_metrics()`**: Finds industry peers with metric values
- **`get_financial_data()`**: Fetches financial data from Yahoo Finance API

#### `dashboard/model.py`
Contains AI model integration for financial report analysis:
- **`analyze_report()`**: Processes and analyzes financial reports using AI models

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

### Data Files Structure

```
company_data/
├── TICKER.AX/
│   ├── BalanceSheet.csv
│   ├── CashFlow.csv
│   ├── IncomeStatement.csv
│   └── financial_data.json
└── ...

combined_data/
├── financial_data.csv
├── cash_flow.csv
├── balance_sheet.csv
└── sector_means.csv
```

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

#### `asx_companies_info.json`
Master list of ASX companies containing:
- **Company Information**: Ticker symbols, names, sectors, industries
- **Market Data**: Basic company classification and categorization

## 🛠️ Setup and Installation

### Prerequisites
```bash
pip install streamlit pandas supabase numpy yfinance pathlib json
```

### Database Setup
1. Create a Supabase account and project
2. Set up the following tables:
   - `Financial Data`
   - `Balance Sheet`  
   - `Cash Flow`
   - `Sector Means`

### Configuration
1. Create `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
```

2. Run data aggregation:
```bash
jupyter notebook data_agg.ipynb
```

3. Launch the dashboard:
```bash
streamlit run dashboard/dashboard.py
```

## 📊 Usage

### Financial Dashboard
1. Enter an ASX ticker symbol (e.g., CBA, ANZ, NAB)
2. View comprehensive financial metrics across three categories:
   - **Financial Data**: Income statement metrics
   - **Balance Sheet**: Assets, liabilities, and equity
   - **Cash Flow**: Operating, investing, and financing activities

### Analysis Features
- **Similar Companies**: Find companies with similar metric values (±10% threshold)
- **Industry Peers**: View top companies in the same industry with their metric values
- **Sector Averages**: Compare against industry benchmarks with contributing company details
- **Interactive Definitions**: Click "View" for detailed metric explanations

### Report Analysis
- Upload financial reports for AI-powered analysis
- Get insights and summaries of key financial information

## 🔧 Technical Implementation

### Data Flow
1. **Data Collection**: `data_agg.ipynb` fetches data from Yahoo Finance
2. **Data Processing**: Cleans and structures financial information
3. **Database Storage**: Uploads processed data to Supabase
4. **Dashboard Display**: Real-time analysis and visualization via Streamlit

### Key Algorithms
- **Similarity Detection**: Relative threshold comparison (10% default)
- **Industry Grouping**: Based on sector and industry classifications
- **Ranking System**: Descending order by metric values for peer analysis

## 📈 Future Enhancements

- Historical data trends and charts
- Additional financial ratios and metrics
- Export functionality for analysis results
- Advanced filtering and search capabilities
- Integration with additional data sources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.