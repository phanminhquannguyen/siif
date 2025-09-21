# finance_sources.py
# Build a dashboard-ready report dict from Yahoo Finance (annual, latest column)

from datetime import datetime
import yfinance as yf

def _safe_num(x):
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        return float(str(x).replace(",", ""))
    except Exception:
        return None

def _latest_col(df):
    """Return the latest column in a yfinance statement dataframe (or None)."""
    try:
        if df is None or df.empty:
            return None
        return sorted(df.columns)[-1]
    except Exception:
        return None

def build_report_from_yfinance(ticker: str) -> dict:
    tk = yf.Ticker(ticker)

    # --- metadata / units ---
    info = tk.info or {}
    fast = getattr(tk, "fast_info", {}) or {}
    currency = info.get("currency") or fast.get("currency") or ""
    as_of = datetime.utcnow().date().isoformat()

    # --- statements (annual, latest) ---
    inc_df = tk.financials          # Income statement
    bal_df = tk.balance_sheet       # Balance sheet
    cf_df  = tk.cashflow            # Cash flow

    ic = _latest_col(inc_df)
    bc = _latest_col(bal_df)
    cc = _latest_col(cf_df)

    def _get(df, row, col):
        try:
            if df is None or df.empty or col is None:
                return None
            if row in df.index:
                return _safe_num(df.loc[row, col])
            return None
        except Exception:
            return None

    # Income
    revenue          = _get(inc_df, "Total Revenue", ic) or _get(inc_df, "TotalRevenue", ic)
    gross_profit     = _get(inc_df, "Gross Profit", ic)  or _get(inc_df, "GrossProfit", ic)
    operating_income = _get(inc_df, "Operating Income", ic) or _get(inc_df, "OperatingIncome", ic)
    net_income       = _get(inc_df, "Net Income", ic) or _get(inc_df, "NetIncome", ic)
    eps_basic        = info.get("trailingEps")
    eps_diluted      = eps_basic

    # Balance sheet
    total_assets      = _get(bal_df, "Total Assets", bc) or _get(bal_df, "TotalAssets", bc)
    total_liabilities = _get(bal_df, "Total Liab", bc)   or _get(bal_df, "TotalLiab", bc)
    total_equity      = None
    if total_assets is not None and total_liabilities is not None:
        total_equity = total_assets - total_liabilities
    shares_outstanding = _safe_num(info.get("sharesOutstanding") or fast.get("shares"))

    # Cash flow
    operating_cf  = _get(cf_df, "Total Cash From Operating Activities", cc) or _get(cf_df, "OperatingCashFlow", cc)
    capex         = _get(cf_df, "Capital Expenditures", cc) or _get(cf_df, "CapitalExpenditures", cc)
    investing_cf  = _get(cf_df, "Total Cashflows From Investing Activities", cc) or _get(cf_df, "InvestingCashFlow", cc)
    financing_cf  = _get(cf_df, "Total Cash From Financing Activities", cc) or _get(cf_df, "FinancingCashFlow", cc)
    free_cf       = None
    if operating_cf is not None and capex is not None:
        free_cf = operating_cf - abs(capex)

    # Price (for P/E)
    price = None
    try:
        h = tk.history(period="1d")
        if not h.empty:
            price = float(h["Close"].iloc[-1])
    except Exception:
        pass
    if price is None:
        price = _safe_num(info.get("currentPrice") or fast.get("last_price"))

    # Derived
    def _pct(n, d):
        if n is None or d in (None, 0):
            return None
        return float(n) / float(d)

    profit_margin         = _pct(net_income, revenue)
    gross_margin          = _pct(gross_profit, revenue)
    operating_margin      = _pct(operating_income, revenue)
    free_cf_margin        = _pct(free_cf, revenue)
    return_on_equity      = _pct(net_income, total_equity)
    asset_turnover        = None if (total_assets in (None, 0) or revenue is None) else float(revenue) / float(total_assets)
    debt_to_equity        = None if (total_equity in (None, 0) or total_liabilities is None) else float(total_liabilities) / float(total_equity)
    pe_ratio              = None if (price is None or eps_basic in (None, 0)) else float(price) / float(eps_basic)

    return {
        "metadata": {"ticker": ticker, "as_of": as_of, "source": "Yahoo Finance via yfinance"},
        "units": {"currency": currency, "scale": 1_000_000},  # your UI shows “(in millions)”
        "income_statement": {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "operating_income": operating_income,
            "net_income": net_income,
            "eps_basic": eps_basic,
            "eps_diluted": eps_diluted,
        },
        "balance_sheet": {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "shares_outstanding": shares_outstanding,
        },
        "cash_flow": {
            "operating_cf": operating_cf,
            "investing_cf": investing_cf,
            "financing_cf": financing_cf,
            "free_cf": free_cf,
        },
        "derived": {
            "profit_margin": profit_margin,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "free_cash_flow_margin": free_cf_margin,
            "return_on_equity": return_on_equity,
            "asset_turnover": asset_turnover,
            "debt_to_equity": debt_to_equity,
            "pe_ratio_basic": pe_ratio,
            "pe_ratio_diluted": pe_ratio,
        },
    }