"""config.py — Configuration centrale THE ZEDICUS v3"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
COLOR_PRIMARY  = "#5BA8D4"
COLOR_SUCCESS  = "#4CAF93"
COLOR_DANGER   = "#E05252"
COLOR_WARNING  = "#E8A838"
COLOR_BG       = "#0F1923"
COLOR_CARD     = "#162233"
COLOR_BORDER   = "#243447"

# Aliases sémantiques utilisés dans le dashboard
COLOR_BULLISH  = COLOR_SUCCESS   # "#4CAF93" vert
COLOR_BEARISH  = COLOR_DANGER    # "#E05252" rouge
COLOR_NEUTRAL  = COLOR_WARNING   # "#E8A838" ambre
COLOR_TEXT     = "#E2E8F0"       # blanc cassé
COLOR_ACCENT   = COLOR_PRIMARY   # "#5BA8D4" bleu

# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------
DEFAULT_SYMBOL   = "AAPL"
DEFAULT_PERIOD   = "6mo"
DEFAULT_INTERVAL = "1d"
FRED_API_KEY     = "DEMO"  # Override via st.secrets["fred"]["api_key"]

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
MAX_PORTFOLIO_SYMBOLS     = 15
SCREENER_BATCH_SIZE       = 10
BACKTEST_MIN_BARS         = 60
ALERT_CHECK_INTERVAL_SEC  = 30
EXPORT_FORMATS            = ["Markdown", "CSV", "JSON", "TXT"]
MC_HORIZON                = 30
MC_SIMULATIONS            = 1000
VAR_CONFIDENCE            = 0.95

# ---------------------------------------------------------------------------
# GARCH parameters (MLE optimised)
# ---------------------------------------------------------------------------
GARCH_ALPHA = 0.094
GARCH_BETA  = 0.849

# ---------------------------------------------------------------------------
# Periods and intervals
# ---------------------------------------------------------------------------
PERIODS   = ["1d","5d","10d","1mo","3mo","6mo","1y","2y","5y","10y","max"]

# Dicts français pour la sidebar du dashboard
PERIODS_UI: dict = {
    "1 jour":   "1d",
    "5 jours":  "5d",
    "1 mois":   "1mo",
    "3 mois":   "3mo",
    "6 mois":   "6mo",
    "1 an":     "1y",
    "2 ans":    "2y",
    "5 ans":    "5y",
}
INTERVALS_UI: dict = {
    "5 minutes":  "5m",
    "15 minutes": "15m",
    "30 minutes": "30m",
    "1 heure":    "1h",
    "1 jour":     "1d",
    "1 semaine":  "1wk",
}
INTERVALS = {
    "1d":  ["1m","2m","5m","15m","30m","60m","90m","1h","1d"],
    "5d":  ["5m","15m","30m","1h","1d"],
    "10d": ["15m","30m","1h","1d"],
    "1mo": ["30m","1h","1d","5d"],
    "3mo": ["1h","1d","5d","1wk"],
    "6mo": ["1d","5d","1wk"],
    "1y":  ["1d","5d","1wk","1mo"],
    "2y":  ["1d","1wk","1mo"],
    "5y":  ["1d","1wk","1mo"],
}

# ---------------------------------------------------------------------------
# Watchlist (symbol -> display name)
# ---------------------------------------------------------------------------
WATCHLIST_NAMES = {
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"Nvidia","TSLA":"Tesla",
    "AMZN":"Amazon","META":"Meta","GOOGL":"Alphabet","NFLX":"Netflix",
    "AMD":"AMD","INTC":"Intel","JPM":"JPMorgan","GS":"Goldman Sachs",
    "SPY":"S&P 500 ETF","QQQ":"Nasdaq ETF","GLD":"Or ETF","TLT":"Obligations 20Y",
    "BTC-USD":"Bitcoin","ETH-USD":"Ethereum","BNB-USD":"BNB","SOL-USD":"Solana",
    "^GSPC":"S&P 500","^FCHI":"CAC 40","^GDAXI":"DAX","^N225":"Nikkei 225",
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY",
    "CL=F":"Pétrole WTI","GC=F":"Or Futures","SI=F":"Argent",
}
WATCHLIST = ["AAPL","MSFT","NVDA","TSLA","BTC-USD","ETH-USD","SPY","^FCHI"]

# ---------------------------------------------------------------------------
# Asset categories
# ---------------------------------------------------------------------------
ASSET_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "🇺🇸 Actions US": [
        ("AAPL","Apple"),("MSFT","Microsoft"),("NVDA","Nvidia"),("TSLA","Tesla"),
        ("AMZN","Amazon"),("META","Meta"),("GOOGL","Alphabet"),("NFLX","Netflix"),
        ("AMD","AMD"),("INTC","Intel"),("JPM","JPMorgan"),("GS","Goldman Sachs"),
        ("ORCL","Oracle"),("CRM","Salesforce"),("PYPL","PayPal"),("UBER","Uber"),
    ],
    "🇪🇺 Actions Europe": [
        ("MC.PA","LVMH"),("AIR.PA","Airbus"),("SAN.PA","Sanofi"),("BNP.PA","BNP Paribas"),
        ("OR.PA","L'Oréal"),("SU.PA","Schneider"),("CS.PA","AXA"),("ORA.PA","Orange"),
        ("SAP.DE","SAP"),("SIE.DE","Siemens"),("BMW.DE","BMW"),("VOW3.DE","Volkswagen"),
    ],
    "📊 ETFs": [
        ("SPY","S&P 500 ETF"),("QQQ","Nasdaq ETF"),("GLD","Or ETF"),("TLT","Obligations 20Y"),
        ("IWM","Russell 2000"),("EEM","Marchés émergents"),("VNQ","Immobilier US"),
        ("XLE","Énergie"),("XLF","Finance"),("XLK","Tech"),("ARKK","ARK Innovation"),
    ],
    "₿ Cryptomonnaies": [
        ("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("BNB-USD","BNB"),("SOL-USD","Solana"),
        ("XRP-USD","XRP"),("ADA-USD","Cardano"),("AVAX-USD","Avalanche"),("DOGE-USD","Dogecoin"),
        ("DOT-USD","Polkadot"),("LINK-USD","Chainlink"),("MATIC-USD","Polygon"),("ATOM-USD","Cosmos"),
    ],
    "💱 Forex": [
        ("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("USDJPY=X","USD/JPY"),
        ("USDCHF=X","USD/CHF"),("AUDUSD=X","AUD/USD"),("USDCAD=X","USD/CAD"),
        ("NZDUSD=X","NZD/USD"),("EURGBP=X","EUR/GBP"),
    ],
    "📈 Indices": [
        ("^GSPC","S&P 500"),("^IXIC","Nasdaq"),("^DJI","Dow Jones"),("^RUT","Russell 2000"),
        ("^FCHI","CAC 40"),("^GDAXI","DAX"),("^FTSE","FTSE 100"),("^N225","Nikkei 225"),
        ("^HSI","Hang Seng"),("^VIX","VIX"),
    ],
    "🛢️ Matières premières": [
        ("CL=F","Pétrole WTI"),("BZ=F","Brent"),("GC=F","Or Futures"),
        ("SI=F","Argent"),("HG=F","Cuivre"),("NG=F","Gaz Naturel"),
        ("ZW=F","Blé"),("ZC=F","Maïs"),
    ],
}

# ---------------------------------------------------------------------------
# Screener universe
# ---------------------------------------------------------------------------
SCREENER_UNIVERSE = [
    "AAPL","MSFT","NVDA","TSLA","AMZN","META","GOOGL","AMD","INTC","JPM",
    "GS","NFLX","ORCL","CRM","SPY","QQQ","GLD","TLT","IWM","XLE",
    "MC.PA","AIR.PA","SAP.DE","SIE.DE",
]
SCREENER_CRYPTO = [
    "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD",
    "ADA-USD","AVAX-USD","DOGE-USD","DOT-USD","LINK-USD",
]

# ---------------------------------------------------------------------------
# FRED series
# ---------------------------------------------------------------------------
FRED_SERIES: dict[str, str] = {
    "CPI (YoY)":         "CPIAUCSL",
    "Fed Funds Rate":    "FEDFUNDS",
    "Unemployment":      "UNRATE",
    "10Y Treasury":      "DGS10",
    "2Y Treasury":       "DGS2",
    "Spread 10-2Y":      "T10Y2Y",
    "GDP Growth":        "A191RL1Q225SBEA",
    "M2 Money Supply":   "M2SL",
    "PCE Inflation":     "PCEPI",
    "Retail Sales":      "RSAFS",
    "Industrial Prod.":  "INDPRO",
    "HY Spread":         "BAMLH0A0HYM2",
}
