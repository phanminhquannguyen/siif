"""
Financial Report → Stable Metrics (Simple CLI)
----------------------------------------------
Usage:
    export DEEPSEEK_API_KEY="..."       # or GOOGLE_API_KEY / OPENAI_API_KEY / HUGGINGFACE_API_KEY
    python main.py /Users/minhquan/Documents/SIIF/HVN_2023-09-28.pdf --ticker HVN

    Check API key
    echo $_API_NAME_
"""

from __future__ import annotations
import os, json, argparse
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional

import pdfplumber
from tqdm import tqdm
import pandas as pd
from jsonschema import validate as jsonschema_validate, ValidationError

from datetime import datetime, UTC
from openai import OpenAI
import google.generativeai as genai
from huggingface_hub import InferenceClient

from api_caller import call_llm_json


# Set the API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyBMmZ9bv_18YTSy3r3UNprlH6-0shbrnJQ"
# Ignore pdfminer warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pdfminer")

# ---------------- Minimal config ----------------
CHUNK_MAX_CHARS = 40000
MAX_JSON_RETRIES = 2

def _pick_default_model() -> str:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    if os.environ.get("HUGGINGFACE_API_KEY"):
        return os.environ.get("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return "mistralai/Mistral-7B-Instruct-v0.3"

DEFAULT_MODEL = _pick_default_model()

# ---------------- Stable JSON Schema ----------------
JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["metadata","units","income_statement","balance_sheet","cash_flow","derived"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["as_of","source"],
            "properties": {
                "ticker": {"type": ["string","null"]},
                "as_of": {"type": "string"},
                "source": {"type": "string"}
            }
        },
        "units": {
            "type": "object",
            "required": ["scale"],
            "properties": {
                "currency": {"type": ["string","null"]},
                "scale": {"type": "number"}
            }
        },
        "income_statement": {
            "type": "object",
            "properties": {
                "revenue": {"type": ["number","null"]},
                "gross_profit": {"type": ["number","null"]},
                "operating_income": {"type": ["number","null"]},
                "net_income": {"type": ["number","null"]},
                "eps_basic": {"type": ["number","null"]},
                "eps_diluted": {"type": ["number","null"]}
            }
        },
        "balance_sheet": {
            "type": "object",
            "properties": {
                "total_assets": {"type": ["number","null"]},
                "total_liabilities": {"type": ["number","null"]},
                "total_equity": {"type": ["number","null"]},
                "shares_outstanding": {"type": ["number","null"]}
            }
        },
        "cash_flow": {
            "type": "object",
            "properties": {
                "operating_cf": {"type": ["number","null"]},
                "investing_cf": {"type": ["number","null"]},
                "financing_cf": {"type": ["number","null"]},
                "free_cf": {"type": ["number","null"]}
            }
        },
        "derived": {
            "type": "object",
            "properties": {
                "pe_ratio_basic": {"type": ["number","null"]},
                "pe_ratio_diluted": {"type": ["number","null"]},
                "profit_margin": {"type": ["number","null"]},
                "return_on_equity": {"type": ["number","null"]},

                # NEW ratios
                "gross_margin": {"type": ["number","null"]},
                "operating_margin": {"type": ["number","null"]},
                "debt_to_equity": {"type": ["number","null"]},
                "asset_turnover": {"type": ["number","null"]},
                "free_cash_flow_margin": {"type": ["number","null"]}
                }
            }
    }
}

INCOME_KEYS   = ["revenue","gross_profit","operating_income","net_income","eps_basic","eps_diluted"]
BALANCE_KEYS  = ["total_assets","total_liabilities","total_equity","shares_outstanding"]
CASHFLOW_KEYS = ["operating_cf","investing_cf","financing_cf","free_cf"]
KEYS_NUMERIC  = [("income_statement", INCOME_KEYS),
                 ("balance_sheet",  BALANCE_KEYS),
                 ("cash_flow",      CASHFLOW_KEYS)]



# ---------------- PDF helpers ----------------
def load_pdf_text(path: str) -> List[str]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for p in tqdm(pdf.pages, desc="Reading PDF", unit="page"):
            pages.append(p.extract_text() or "")
    return pages

def chunk_text(pages: List[str], max_chars: int = CHUNK_MAX_CHARS) -> List[str]:
    chunks, buf = [], ""
    for i, page in enumerate(pages, 1):
        tag = f"\n\n[PAGE {i}]\n"
        if buf and len(buf) + len(tag) + len(page) > max_chars:
            chunks.append(buf); buf = ""
        buf += tag + page
    if buf: chunks.append(buf)
    return chunks

# Derived ratios
def add_derived(report: Dict[str, Any]) -> Dict[str, Any]:
    inc = report["income_statement"]
    bal = report["balance_sheet"]
    cf  = report["cash_flow"]

    # keep free_cf if provided; otherwise try operating + investing
    if cf.get("free_cf") is None and (cf.get("operating_cf") is not None and cf.get("investing_cf") is not None):
        cf["free_cf"] = cf["operating_cf"] + cf["investing_cf"]
    report["cash_flow"] = cf

    report["derived"] = {
        "pe_ratio_basic":   None,  # price not supplied in this simple CLI
        "pe_ratio_diluted": None,
        "profit_margin":    safe_div(inc.get("net_income"), inc.get("revenue")),
        "return_on_equity": safe_div(inc.get("net_income"), bal.get("total_equity")),
        "gross_margin":     safe_div(inc.get("gross_profit"), inc.get("revenue")),
        "operating_margin": safe_div(inc.get("operating_income"), inc.get("revenue")),
        "debt_to_equity":   safe_div(bal.get("total_liabilities"), bal.get("total_equity")),
        "asset_turnover":   safe_div(inc.get("revenue"), bal.get("total_assets")),
        "free_cash_flow_margin": safe_div(cf.get("free_cf"), inc.get("revenue")),
    }
    return report

# ---------------- Prompt ----------------
SCHEMA_INSTRUCTIONS = (
    "Return ONLY a JSON object with these exact keys: metadata, units, income_statement, balance_sheet, cash_flow, derived.\n"
    "metadata: {ticker (string|null), as_of (YYYY-MM-DD), source (string path)}\n"
    "units: {currency (e.g., AUD/USD) or null, scale (1/1000/1000000/1000000000)}\n"
    "income_statement: {revenue, gross_profit, operating_income, net_income, eps_basic, eps_diluted}\n"
    "balance_sheet: {total_assets, total_liabilities, total_equity, shares_outstanding}\n"
    "cash_flow: {operating_cf, investing_cf, financing_cf, free_cf}\n"
    "derived: {\n"
    "  pe_ratio_basic, pe_ratio_diluted, profit_margin, return_on_equity,\n"
    "  gross_margin, operating_margin, debt_to_equity, asset_turnover, free_cash_flow_margin\n"
    "}\n"
    "Rules: use latest annual consolidated figures; apply scaling units to totals (not EPS);\n"
    "numbers only; if unknown or missing -> null.\n"
)
def build_prompt(chunk: str, ticker: Optional[str], source_path: str) -> str:
    today = datetime.now(UTC).date().isoformat()
    return (
        f"Extract the schema below from the report text.\n\n{SCHEMA_INSTRUCTIONS}\n"
        f"Assume ticker={ticker!r}. Use as_of='{today}'. Set source='{source_path}'.\n\n"
        f"TEXT START\n{chunk}\nTEXT END\n"
    )

# ---------------- Merge & derived ----------------
def _extract_json_block(s: str) -> str:
    a, b = s.find("{"), s.rfind("}")
    return s[a:b+1] if a != -1 and b != -1 and b > a else s

def merge_reports(base: Dict[str, Any], inc: Dict[str, Any]) -> Dict[str, Any]:
    out = json.loads(json.dumps(base))
    for section, fields in KEYS_NUMERIC + [("derived", list(base["derived"].keys()))]:
        for f in fields:
            if out[section].get(f) is None and inc.get(section, {}).get(f) is not None:
                out[section][f] = inc[section][f]
    if out["units"].get("currency") is None and inc.get("units", {}).get("currency"):
        out["units"]["currency"] = inc["units"]["currency"]
    if out["units"].get("scale") in (None, 1) and inc.get("units", {}).get("scale") not in (None, 1):
        out["units"]["scale"] = inc["units"]["scale"]
    return out

def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    try:
        if a is None or b in (None, 0): return None
        return a / b
    except Exception:
        return None

def to_table(report: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for sec, block in report.items():
        if isinstance(block, dict):
            for k, v in block.items():
                rows.append({"Section": sec, "Metric": k, "Value": v})
    return pd.DataFrame(rows)

# ---------------- Main ----------------
def run(pdf_path: str, ticker: Optional[str], model: str) -> dict:
    pages  = load_pdf_text(pdf_path)
    chunks = chunk_text(pages)

    # Init with FULL derived set so merge_reports can fill any coming from the LLM
    merged: Dict[str, Any] = {
        "metadata": {"ticker": ticker, "as_of": datetime.now(UTC).date().isoformat(), "source": pdf_path},
        "units": {"currency": None, "scale": 1},
        "income_statement": {k: None for k in INCOME_KEYS},
        "balance_sheet":    {k: None for k in BALANCE_KEYS},
        "cash_flow":        {k: None for k in CASHFLOW_KEYS},
        "derived": {
            "pe_ratio_basic": None,
            "pe_ratio_diluted": None,
            "profit_margin": None,
            "return_on_equity": None,
            "gross_margin": None,
            "operating_margin": None,
            "debt_to_equity": None,
            "asset_turnover": None,
            "free_cash_flow_margin": None,
        },
    }

    for i, chunk in enumerate(tqdm(chunks, desc="Extracting", unit="chunk"), 1):
        prompt = build_prompt(chunk, ticker, pdf_path)
        for attempt in range(MAX_JSON_RETRIES + 1):
            try:
                raw = call_llm_json(prompt, model=model)
                raw = _extract_json_block(raw)
                part = json.loads(raw)
                jsonschema_validate(instance=part, schema=JSON_SCHEMA)
                merged = merge_reports(merged, part)
                break
            except (json.JSONDecodeError, ValidationError):
                if attempt >= MAX_JSON_RETRIES:
                    print(f"[warn] chunk {i}: invalid JSON after retries, skipping")
                else:
                    prompt += "\nYour previous JSON was invalid. Return EXACT keys with values or null."
            except Exception as e:
                print(f"[warn] chunk {i}: {e}")
                break

    merged = add_derived(merged)
    df = to_table(merged)

    # --- Compact console output (still useful in CLI/dev) ---
    print("\n=== Extracted financial metrics (compact) ===")
    print(df.to_string(index=False, max_colwidth=36))

    # --- Auto-save next to PDF ---
    tkr  = (ticker or "UNKNOWN").upper()
    out_dir = os.path.dirname(os.path.abspath(pdf_path))
    json_path = os.path.join(out_dir, f"{tkr}_metrics.json")
    csv_path  = os.path.join(out_dir, f"{tkr}_metrics.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    df.to_csv(csv_path, index=False)

    print(f"\nSaved JSON -> {json_path}")
    print(f"Saved CSV  -> {csv_path}")

    # ✅ Return a dict so Streamlit can render it
    return {"report": merged, "json_path": json_path, "csv_path": csv_path}


# Run in the terminal to test the model
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Extract stable financial metrics from a PDF (simple CLI).")

    # Debug: print which API keys are visible
    print("DEEPSEEK_API_KEY:", bool(os.getenv("DEEPSEEK_API_KEY")))
    print("OPENAI_API_KEY:",   bool(os.getenv("OPENAI_API_KEY")))
    print("GOOGLE_API_KEY:",   bool(os.getenv("GOOGLE_API_KEY")))
    print("HUGGINGFACE_API_KEY:", bool(os.getenv("HUGGINGFACE_API_KEY")))

    ap.add_argument("pdf", help="Path to the financial report PDF")
    ap.add_argument("--ticker", required=True, help="Ticker symbol (e.g., CSL)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="(Optional) model name; auto-picked from available keys")
    args = ap.parse_args()
    run(args.pdf, ticker=args.ticker, model=args.model)


def analyze_pdf(file_bytes: bytes, ticker: str = "DEMO") -> dict:
    import tempfile, json

    # Save uploaded PDF bytes to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # Call the pipeline using default model
    out = run(tmp_path, ticker=ticker, model=DEFAULT_MODEL)

    # If run() already returned the wrapper dict (expected), pass it through
    if isinstance(out, dict) and "report" in out:
        return out

    # Backstop behaviors if someone changes run() later
    if isinstance(out, dict):
        return {"report": out}
    if isinstance(out, str):
        try:
            return {"report": json.loads(out)}
        except Exception:
            return {
                "report": {"raw_output": out},
                "error": "Non-JSON string from run()"
            }

    return {"report": None, "error": "Model returned no data"}
