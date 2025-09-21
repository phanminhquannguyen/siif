from typing import Dict, Any

# Prefer an existing model if you already have one (keeps your current pipeline working).
try:
    # If your project already has a module like `model.analyze_pdf`, this will be used.
    from model import analyze_pdf as _model_analyze_pdf  # type: ignore

    def analyze_pdf(file_bytes: bytes, ticker: str = "DEMO") -> Dict[str, Any]:
        """Call your existing PDF analyzer."""
        return _model_analyze_pdf(file_bytes, ticker=ticker)

except Exception:
    # Fallback stub so the app doesn't crash if the model package isn't present.
    # You can replace this with your real implementation later.
    def analyze_pdf(file_bytes: bytes, ticker: str = "DEMO") -> Dict[str, Any]:
        """Fallback: returns a minimal empty report structure."""
        return {
            "report": {
                "metadata": {"ticker": ticker, "as_of": None, "source": "PDF model (stub)"},
                "units": {"currency": "", "scale": 1_000_000},
                "income_statement": {},
                "balance_sheet": {},
                "cash_flow": {},
                "derived": {},
            },
            "json_path": None,
            "csv_path": None,
        }