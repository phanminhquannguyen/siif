import streamlit as st
import pandas as pd
import json

from model import analyze_pdf # Import our model function

# Page setup 
st.set_page_config(page_title="Financial PDF → Dashboard", layout="wide")
st.title("SIIF Financial Dashboard")

# Sidebar (inputs)
with st.sidebar:
    st.header("Input")
    ticker = st.text_input("Ticker", value="DEMO") # Company ticker, probably can use this get time series data
    # model_name = st.text_input("Model name (optional)", value="auto")
    uploaded_pdf = st.file_uploader("Upload a PDF report", type=["pdf"])
    run_btn = st.button("🔎 Analyze")


def human_currency(n, currency, scale):
    """Show totals in 'millions' (or whatever scale) with commas. EPS is handled elsewhere."""
    if n is None:
        return "—"
    # display in units of 'scale' (e.g., millions if scale=1_000_000)
    val = n / (scale or 1)
    suffix = " (in millions)" if scale == 1_000_000 else ("" if scale in (None, 1) else f" (÷{scale:,})")
    return f"{currency or ''} {val:,.2f}{suffix}".strip()

def human_number(n):
    return "—" if n is None else f"{n:,.2f}"

def human_percent(x):
    return "—" if x is None else f"{100*x:.2f}%"

def section_table_simple(section_dict, value_fmt):
    """Render a {key: value} dict into a 2-col table with formatting."""
    if not section_dict:
        return
    df = (
        pd.DataFrame(
            [(k.replace("_", " ").title(), value_fmt(v)) for k, v in section_dict.items()],
            columns=["Metric", "Value"],
        )
        .set_index("Metric")
    )
    st.dataframe(df, use_container_width=True)

def _fmt_currency(n, currency, scale):
    if n is None:
        return "—"
    # Display values divided by 'scale' (e.g., in millions if scale=1_000_000)
    val = n / (scale or 1)
    suffix = " (in millions)" if scale == 1_000_000 else ("" if scale in (None, 1) else f" (÷{scale:,})")
    cur = f"{currency} " if currency else ""
    return f"{cur}{val:,.2f}{suffix}"

def _fmt_number(n):
    return "—" if n is None else f"{n:,.2f}"

def _fmt_percent(x):
    return "—" if x is None else f"{100*x:.2f}%"

def _kv_table(mapping, value_fmt, order=None, rename=None):
    """Render a {key: value} mapping as a 2-col table with optional key order/rename."""
    if not mapping:
        return
    items = []
    keys = order if order else list(mapping.keys())
    for k in keys:
        if k not in mapping:
            continue
        v = mapping.get(k)
        label = (rename or {}).get(k, k.replace("_", " ").title())
        items.append((label, value_fmt(k, v) if callable(value_fmt) else value_fmt(v)))
    df = pd.DataFrame(items, columns=["Metric", "Value"]).set_index("Metric")
    st.dataframe(df, use_container_width=True)

# ---------- main presenter for your schema ----------
def render_report(report: dict):
    if not report:
        st.info("No report to display yet.")
        return

    meta  = report.get("metadata", {}) or {}
    units = report.get("units", {}) or {}
    currency = units.get("currency")
    scale    = units.get("scale", 1)

    # Header
    left, right = st.columns([2, 1])
    with left:
        st.subheader(f"🏷️ Ticker: {meta.get('ticker','—')} • As of: {meta.get('as_of','—')}")
        st.caption(f"Source: {meta.get('source','—')}")
    with right:
        st.write(f"**Currency:** {currency or '—'}")
        st.write(f"**Scale:** {scale:,}")
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(report, indent=2).encode("utf-8"),
            file_name=f"{(meta.get('ticker') or 'report')}_metrics.json",
            mime="application/json"
        )

    st.markdown("---")

    # Income Statement (EPS not scaled)
    inc = report.get("income_statement", {}) or {}
    if inc:
        st.subheader("Income Statement")
        inc_order = ["revenue","gross_profit","operating_income","net_income","eps_basic","eps_diluted"]
        def fmt_inc(k, v):
            return _fmt_number(v) if k in ("eps_basic","eps_diluted") else _fmt_currency(v, currency, scale)
        _kv_table(inc, fmt_inc, order=inc_order)

    # Balance Sheet (shares_outstanding not scaled)
    bal = report.get("balance_sheet", {}) or {}
    if bal:
        st.subheader("Balance Sheet")
        bal_order = ["total_assets","total_liabilities","total_equity","shares_outstanding"]
        def fmt_bal(k, v):
            return _fmt_number(v) if k == "shares_outstanding" else _fmt_currency(v, currency, scale)
        _kv_table(bal, fmt_bal, order=bal_order)

    # Cash Flow (all scaled)
    cf = report.get("cash_flow", {}) or {}
    if cf:
        st.subheader("Cash Flow")
        cf_order = ["operating_cf","investing_cf","financing_cf","free_cf"]
        _kv_table(cf, lambda k,v: _fmt_currency(v, currency, scale), order=cf_order,
                  rename={"operating_cf":"Operating Cash Flow",
                          "investing_cf":"Investing Cash Flow",
                          "financing_cf":"Financing Cash Flow",
                          "free_cf":"Free Cash Flow"})

    # Derived ratios (ALL as %)
    drv = report.get("derived", {}) or {}
    if drv:
        st.subheader("Derived Ratios")
        drv_order = [
            "profit_margin","gross_margin","operating_margin","free_cash_flow_margin",
            "return_on_equity","asset_turnover","debt_to_equity",
            "pe_ratio_basic","pe_ratio_diluted"
        ]
        # For P/E we usually show plain numbers, not percents.
        def fmt_drv(k, v):
            if k in ("pe_ratio_basic","pe_ratio_diluted"):
                return "—" if v is None else _fmt_number(v)
            if k == "debt_to_equity":  # often shown as ratio, but % is acceptable too; choose format
                return "—" if v is None else f"{v:,.2f}x"
            return _fmt_percent(v)
        rename = {
            "pe_ratio_basic":"P/E (Basic)",
            "pe_ratio_diluted":"P/E (Diluted)",
            "profit_margin":"Profit Margin",
            "gross_margin":"Gross Margin",
            "operating_margin":"Operating Margin",
            "free_cash_flow_margin":"Free Cash Flow Margin",
            "return_on_equity":"Return on Equity",
            "debt_to_equity":"Debt / Equity",
            "asset_turnover":"Asset Turnover",
        }
        _kv_table(drv, fmt_drv, order=drv_order, rename=rename)

    # Optional: quick chart of margins if present
    plot_cols = [c for c in ["profit_margin","gross_margin","operating_margin","free_cash_flow_margin"] if drv.get(c) is not None]
    if plot_cols:
        st.write("**Margins (%):**")
        st.bar_chart(pd.DataFrame({k: [drv[k]*100] for k in plot_cols}).T.rename(columns={0: "%"}))


# --- Run model when button is clicked and PDF is uploaded ---
if run_btn:
    if not uploaded_pdf:
        st.warning("Please upload a PDF first.")
        st.stop()

    pdf_bytes = uploaded_pdf.read()

    with st.spinner("Running your model..."):
        try:
            out = analyze_pdf(pdf_bytes, ticker=ticker)  # returns {"report", "json_path", "csv_path"}
        except Exception as e:
            st.error(f"Model error: {e}")
            st.stop()

    # Unpack & persist
    st.session_state["report"] = out.get("report")
    st.session_state["json_path"] = out.get("json_path")
    st.session_state["csv_path"] = out.get("csv_path")

# --------------- Render the report if available ---------------
report = st.session_state.get("report")
if not isinstance(report, dict) or not report:
    st.info("Upload a PDF and click **Analyze** to get started.")
else:
    render_report(report)

