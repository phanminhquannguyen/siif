# app.py
import json, re, math
import pandas as pd
import streamlit as st

from financial_sources import build_report_from_yfinance
from analyze_pdf import analyze_pdf  # your PDF/LLM analyzer

# ---------------- Page setup ----------------
st.set_page_config(page_title="Financial PDF → Dashboard", layout="wide")
st.title("SIIF Financial Dashboard")

# ---------------- Canonical schema & synonyms ----------------
CANON = {
    "income_statement": [
        "revenue","gross_profit","operating_income","net_income","eps_basic","eps_diluted"
    ],
    "balance_sheet": [
        "total_assets","total_liabilities","total_equity","shares_outstanding"
    ],
    "cash_flow": [
        "operating_cf","investing_cf","financing_cf","free_cf"
    ],
    "derived": [
        "profit_margin","gross_margin","operating_margin","free_cash_flow_margin",
        "return_on_equity","asset_turnover","debt_to_equity","pe_ratio_basic","pe_ratio_diluted"
    ],
}

SYNONYMS = {
    # income
    "total_revenue": "revenue",
    "sales": "revenue",
    "turnover": "revenue",
    "grossprofit": "gross_profit",
    "operatingincome": "operating_income",
    "ebit": "operating_income",
    "netincome": "net_income",
    "net_profit": "net_income",
    "eps": "eps_basic",
    "basic_eps": "eps_basic",
    "diluted_eps": "eps_diluted",
    # balance
    "total_assets": "total_assets",
    "assets_total": "total_assets",
    "total_liab": "total_liilities",  # (typo fixed below via canonicalize)
    "total_liabilities": "total_liabilities",
    "total_liabilities_and_equity": "total_assets",  # ignore if misuse
    "equity": "total_equity",
    "shareholders_equity": "total_equity",
    "shares": "shares_outstanding",
    "shares_out": "shares_outstanding",
    # cash flow
    "operating_cash_flow": "operating_cf",
    "cash_from_operations": "operating_cf",
    "investing_cash_flow": "investing_cf",
    "financing_cash_flow": "financing_cf",
    "free_cash_flow": "free_cf",
    "fcf": "free_cf",
    # derived
    "net_margin": "profit_margin",
    "roe": "return_on_equity",
    "d_to_e": "debt_to_equity",
    "pe": "pe_ratio_basic",
}

# ---------------- Helpers: ticker, coercion, canonicalization ----------------
def normalize_ticker(t: str) -> str:
    """Append .AX for likely ASX codes if no suffix provided."""
    t = (t or "").strip().upper()
    if not t: return t
    if "." in t: return t
    if 2 <= len(t) <= 4:  # heuristic for ASX tickers like HVN, CBA, BHP
        return f"{t}.AX"
    return t

def guess_ticker_from_filename(name: str) -> str | None:
    """Heuristic: from 'HVN_2024_AR.pdf' -> 'HVN'."""
    if not name: return None
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    base = base.rsplit(".", 1)[0]
    m = re.match(r"^([A-Z]{2,5})(?:[_\-\s].*)?$", base.upper())
    return m.group(1) if m else None

def _to_num(x):
    if x is None: return None
    if isinstance(x, (int, float)):
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)): return None
        return float(x)
    s = str(x).strip()
    if s == "" or s.lower() in ("nan","none","null","—","-"): return None
    if s.endswith("%"):
        try: return float(s[:-1].strip())/100.0
        except: return None
    s = s.replace(",", "")
    try:
        v = float(s)
        if math.isnan(v) or math.isinf(v): return None
        return v
    except:
        return None

def _canon_key(k: str) -> str:
    k0 = (k or "").strip().lower().replace(" ", "_")
    # Fix the occasional misspelling mapped above
    if k0 == "total_liilities":  # typo path
        k0 = "total_liabilities"
    return SYNONYMS.get(k0, k0)

def canonicalize_report(report: dict) -> dict:
    """Map keys to canonical names, coerce to floats, drop unknowns (except metadata/units)."""
    if not isinstance(report, dict): return {}
    out = {
        "metadata": report.get("metadata") or {},
        "units": report.get("units") or {},
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {},
        "derived": {},
    }
    for section in ("income_statement","balance_sheet","cash_flow","derived"):
        sec = (report.get(section) or {})
        norm = {}
        for k, v in sec.items():
            ck = _canon_key(k)
            norm[ck] = _to_num(v)
        out[section] = {k: norm.get(k) for k in CANON[section]}
    return out

def merge_reports_with_provenance(yrep: dict | None, prep: dict | None):
    """
    Yahoo-first merge with provenance.
    Returns: (final_report, provenance_df)
    provenance_df columns: section, field, yahoo, pdf, chosen, source
    """
    yrep = canonicalize_report(yrep or {})
    prep = canonicalize_report(prep or {})

    # metadata/units: prefer Yahoo, fallback to PDF
    meta = {**(prep.get("metadata") or {}), **(yrep.get("metadata") or {})}
    uy, up = yrep.get("units") or {}, prep.get("units") or {}
    units = {
        "currency": uy.get("currency") or up.get("currency"),
        "scale": uy.get("scale", 1) if uy.get("scale") is not None else up.get("scale", 1),
    }

    final = {"metadata": meta, "units": units}
    rows = []

    for section in ("income_statement","balance_sheet","cash_flow","derived"):
        fy, fp = yrep.get(section) or {}, prep.get(section) or {}
        out_sec = {}
        for field in CANON[section]:
            vy = fy.get(field)
            vp = fp.get(field)
            if vy is not None:
                chosen, src = vy, "yahoo"
            elif vp is not None:
                chosen, src = vp, "pdf"
            else:
                chosen, src = None, "missing"
            out_sec[field] = chosen
            rows.append({"section": section, "field": field, "yahoo": vy, "pdf": vp, "chosen": chosen, "source": src})
        final[section] = out_sec

    prov_df = pd.DataFrame(rows, columns=["section","field","yahoo","pdf","chosen","source"])
    return final, prov_df

def has_missing_fields(report: dict) -> bool:
    """True if any known section empty or any field is None."""
    if not isinstance(report, dict): return True
    for sec in ("income_statement","balance_sheet","cash_flow","derived"):
        block = report.get(sec) or {}
        if not block: return True
        if any(v is None for v in block.values()): return True
    return False

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Input")
    uploaded_pdf = st.file_uploader("Upload a financial PDF report", type=["pdf"])
    allow_edit_ticker = st.checkbox("Edit/override detected ticker", value=False)
    manual_ticker = st.text_input("Override ticker", value="", disabled=not allow_edit_ticker)
    run_btn = st.button("🔎 Analyze")

# ---------------- Formatting helpers for UI ----------------
def _fmt_currency(n, currency, scale):
    if n is None: return "—"
    val = n / (scale or 1)
    suffix = " (in millions)" if scale == 1_000_000 else ("" if scale in (None, 1) else f" (÷{scale:,})")
    cur = f"{currency} " if currency else ""
    return f"{cur}{val:,.2f}{suffix}"

def _fmt_number(n):
    return "—" if n is None else f"{n:,.2f}"

def _fmt_percent(x):
    return "—" if x is None else f"{100*x:.2f}%"

def _kv_table(mapping, value_fmt, order=None, rename=None):
    if not mapping: return
    items, keys = [], (order if order else list(mapping.keys()))
    for k in keys:
        if k not in mapping: continue
        v = mapping.get(k)
        label = (rename or {}).get(k, k.replace("_", " ").title())
        items.append((label, value_fmt(k, v) if callable(value_fmt) else value_fmt(v)))
    df = pd.DataFrame(items, columns=["Metric", "Value"]).set_index("Metric")
    st.dataframe(df, use_container_width=True)

# ---------------- Render function ----------------
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

    # Income Statement (EPS unscaled)
    inc = report.get("income_statement", {}) or {}
    if inc:
        st.subheader("Income Statement")
        inc_order = ["revenue","gross_profit","operating_income","net_income","eps_basic","eps_diluted"]
        def fmt_inc(k, v):
            return _fmt_number(v) if k in ("eps_basic","eps_diluted") else _fmt_currency(v, currency, scale)
        _kv_table(inc, fmt_inc, order=inc_order)

    # Balance Sheet (shares_outstanding unscaled)
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
        _kv_table(
            cf,
            lambda k, v: _fmt_currency(v, currency, scale),
            order=cf_order,
            rename={
                "operating_cf":"Operating Cash Flow",
                "investing_cf":"Investing Cash Flow",
                "financing_cf":"Financing Cash Flow",
                "free_cf":"Free Cash Flow",
            },
        )

    # Derived Ratios
    drv = report.get("derived", {}) or {}
    if drv:
        st.subheader("Derived Ratios")
        drv_order = [
            "profit_margin","gross_margin","operating_margin","free_cash_flow_margin",
            "return_on_equity","asset_turnover","debt_to_equity","pe_ratio_basic","pe_ratio_diluted"
        ]
        def fmt_drv(k, v):
            if v is None: return "—"
            if k in ("pe_ratio_basic","pe_ratio_diluted"): return _fmt_number(v)
            if k == "debt_to_equity": return f"{v:,.2f}x"
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

        # quick margins chart
        plot_cols = [c for c in ["profit_margin","gross_margin","operating_margin","free_cash_flow_margin"] if drv.get(c) is not None]
        if plot_cols:
            st.write("**Margins (%):**")
            st.bar_chart(pd.DataFrame({k: [drv[k]*100] for k in plot_cols}).T.rename(columns={0: "%"}))

# ---------------- Action: ALWAYS Yahoo first; fill gaps from PDF ----------------
if run_btn:
    if uploaded_pdf is None and not manual_ticker.strip():
        st.warning("Upload a PDF or provide an override ticker.")
        st.stop()

    # Figure out ticker (override → filename → extract via PDF metadata)
    ticker_candidate = manual_ticker.strip().upper() if manual_ticker.strip() else None
    prep = None
    pdf_bytes = None

    if not ticker_candidate and uploaded_pdf is not None:
        ticker_candidate = guess_ticker_from_filename(uploaded_pdf.name)

    if not ticker_candidate and uploaded_pdf is not None:
        pdf_bytes = uploaded_pdf.read()
        with st.spinner("Extracting ticker from PDF..."):
            try:
                out_meta = analyze_pdf(pdf_bytes, ticker="DEMO")
                prep = (out_meta or {}).get("report")
                pdf_meta = (prep or {}).get("metadata") or {}
                ticker_candidate = (pdf_meta.get("ticker") or "").strip().upper()
            except Exception:
                ticker_candidate = None

    if not ticker_candidate:
        st.warning("Could not determine a ticker. Provide an override or use a clearer filename.")
        st.stop()

    yf_ticker = normalize_ticker(ticker_candidate)

    # 1) ALWAYS fetch Yahoo first
    with st.spinner(f"Fetching Yahoo Finance data for {yf_ticker}..."):
        try:
            yrep_raw = build_report_from_yfinance(yf_ticker)
        except Exception as e:
            st.error(f"Yahoo Finance error: {e}")
            yrep_raw = None

    # 2) If Yahoo failed or has gaps, run PDF to fill gaps
    need_pdf = True
    if yrep_raw is not None:
        yrep_can = canonicalize_report(yrep_raw)
        need_pdf = has_missing_fields(yrep_can)

    if need_pdf and uploaded_pdf is not None:
        if pdf_bytes is None:
            pdf_bytes = uploaded_pdf.read()
        with st.spinner("Filling missing fields from PDF (LLM)…"):
            try:
                out = analyze_pdf(pdf_bytes, ticker=yf_ticker)
                prep_raw = (out or {}).get("report")
                # optional: persist sidecar paths
                st.session_state["json_path"] = (out or {}).get("json_path")
                st.session_state["csv_path"] = (out or {}).get("csv_path")
            except Exception as e:
                st.error(f"PDF model error: {e}")
                prep_raw = None
    else:
        prep_raw = prep  # could be from earlier metadata-run

    # 3) Merge + provenance and store
    final_report, prov_df = merge_reports_with_provenance(yrep_raw, prep_raw)
    final_report["metadata"] = {**(final_report.get("metadata") or {}), "ticker": yf_ticker}
    st.session_state["report"] = final_report

    with st.expander("Diagnostics: Yahoo vs PDF vs Chosen"):
        st.dataframe(prov_df, use_container_width=True)
        missing = prov_df[prov_df["source"] == "missing"]
        if not missing.empty:
            st.warning(f"Still missing {len(missing)} fields (neither source had them).")

# ---------------- Render ----------------
report = st.session_state.get("report")
if not isinstance(report, dict) or not report:
    st.info("Upload a PDF or enter an override ticker, then click **Analyze**.")
else:
    render_report(report)