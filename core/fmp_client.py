import requests
from decouple import config

FMP_BASE = "https://financialmodelingprep.com/stable"
_API_KEY = None


def _key():
    global _API_KEY
    if _API_KEY is None:
        _API_KEY = config("FMP_API_KEY", default="")
    return _API_KEY


def fmp_get(endpoint, params=None):
    url = f"{FMP_BASE}{endpoint}"
    p = {"apikey": _key()}
    if params:
        p.update(params)
    resp = requests.get(url, params=p, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_crypto_quotes():
    """
    Fetch all crypto quotes in one call.
    Returns a list of {symbol, price, ...} dicts.
    """
    return fmp_get("/batch-crypto-quotes")


def get_stock_quotes(symbols: list) -> list:
    """
    Fetch live quotes for a list of stock symbols.
    FMP stable API expects symbol as a query param, not in the path.
    Returns list of {symbol, price, change, changesPercentage, volume, marketCap, pe, eps, ...}
    """
    return fmp_get("/quote", {"symbol": ",".join(symbols)})


def get_stock_profiles(symbols: list) -> list:
    """
    Fetch company profiles (name, sector, description, logo, 52w range, beta, etc.).
    FMP stable API expects symbol as a query param.
    Returns list of profile dicts.
    """
    return fmp_get("/profile", {"symbol": ",".join(symbols)})


def get_stock_price_change(symbol: str) -> dict:
    """
    Fetch percentage price changes (1D, 5D, 1M, 3M, 6M, 1Y).
    Used to reconstruct an approximate sparkline since FMP stable has no EOD history.
    Returns a single dict with change percentages.
    """
    data = fmp_get("/stock-price-change", {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    return {}


def get_news(feed_type="stock", limit=50):
    """
    Fetch latest news from FMP stable API.
    feed_type: 'stock' | 'forex' | 'crypto'
    """
    endpoints = {
        "stock":  "/news/stock-latest",
        "forex":  "/news/forex-latest",
        "crypto": "/news/crypto-latest",
    }
    endpoint = endpoints.get(feed_type, "/news/stock-latest")
    return fmp_get(endpoint, {"limit": limit})
