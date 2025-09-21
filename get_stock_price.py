import yfinance as yf

# get the current price of the stock on yfinace
def get_current_price(ticker: str) -> float | None:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if hist.empty:
            print(f" No data found for ticker {ticker}")
            return None
        return hist["Close"].iloc[-1] # Latest price
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None
    
stock = yf.Ticker("AAPL")
print(stock.info.keys())   # shows all available fields