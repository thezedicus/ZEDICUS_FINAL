"""
data_providers.py — Sources de données multi-API gratuites, rapides, sans clé obligatoire
==========================================================================================
① Binance Public REST   → crypto OHLCV + ticker temps réel        (~100-600ms)
② CoinGecko API v3      → prix crypto, market cap, dominance BTC  (~300ms)
③ Frankfurter (BCE)     → taux de change EUR officiels             (~400ms)
④ FRED CSV public       → données macro US (CPI, Fed, chômage…)   (~1.5s, caché 1h)
⑤ yfinance              → actions / indices / ETF / commodities    (fallback)

Architecture :
  - Cache thread-safe par TTL pour éviter les doublons d'appel
  - Parallel fetch via ThreadPoolExecutor (jusqu'à 8 workers)
  - Route intelligente : la source la plus rapide selon le type d'actif
  - Fallback automatique en cas d'erreur réseau
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutTimeoutError
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import yfinance as yf

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Cache thread-safe (TTL en secondes)
# ──────────────────────────────────────────────────────────────────────────────

_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()


def _cache_get(key: str, ttl: int = 60) -> Optional[Any]:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return entry["data"]
    return None


def _cache_set(key: str, data: Any) -> None:
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}


def cache_clear() -> None:
    """Vide tout le cache (utile pour les tests)."""
    with _cache_lock:
        _cache.clear()


# ──────────────────────────────────────────────────────────────────────────────
# ① BINANCE PUBLIC REST
#    Documentation : https://binance-docs.github.io/apidocs/spot/en/
#    Limites : 1200 req/min par IP — aucune clé requise pour les endpoints publics
# ──────────────────────────────────────────────────────────────────────────────

BINANCE_BASE = "https://api.binance.com/api/v3"

# Correspondance Yahoo Finance → Binance symbol
BINANCE_MAP: Dict[str, str] = {
    "BTC-USD":   "BTCUSDT",
    "ETH-USD":   "ETHUSDT",
    "BNB-USD":   "BNBUSDT",
    "SOL-USD":   "SOLUSDT",
    "XRP-USD":   "XRPUSDT",
    "ADA-USD":   "ADAUSDT",
    "AVAX-USD":  "AVAXUSDT",
    "DOGE-USD":  "DOGEUSDT",
    "DOT-USD":   "DOTUSDT",
    "LINK-USD":  "LINKUSDT",
    "MATIC-USD": "MATICUSDT",
    "ATOM-USD":  "ATOMUSDT",
    "LTC-USD":   "LTCUSDT",
    "UNI-USD":   "UNIUSDT",
    "SHIB-USD":  "SHIBUSDT",
}

# Correspondance intervalle Yahoo → Binance
BINANCE_INTERVAL_MAP: Dict[str, str] = {
    "1m": "1m", "2m": "3m", "5m": "5m", "15m": "15m",
    "30m": "30m", "60m": "1h", "1h": "1h",
    "1d": "1d", "5d": "3d", "1wk": "1w", "1mo": "1M",
}

# Période → nombre approximatif de bougies selon l'intervalle
_PERIOD_DAYS: Dict[str, int] = {
    "1d": 1, "5d": 5, "10d": 10, "1mo": 30,
    "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
}
_CANDLES_PER_DAY: Dict[str, float] = {
    "1m": 1440, "3m": 480, "5m": 288, "15m": 96,
    "30m": 48, "1h": 24, "1d": 1, "3d": 0.33, "1w": 0.14, "1M": 0.033,
}


def binance_ticker(symbol_yf: str) -> Dict[str, Any]:
    """
    Prix spot 24h Binance en temps réel (< 600ms, cache 10s).

    Retourne : {price, change_pct, volume_usd, high_24h, low_24h, source}
    """
    sym = BINANCE_MAP.get(symbol_yf)
    if not sym:
        return {}
    key = f"bticker_{sym}"
    cached = _cache_get(key, ttl=10)
    if cached is not None:
        return cached
    try:
        r = requests.get(
            f"{BINANCE_BASE}/ticker/24hr",
            params={"symbol": sym},
            timeout=4,
        )
        if r.status_code == 200:
            d = r.json()
            result: Dict[str, Any] = {
                "price":      float(d["lastPrice"]),
                "change_pct": float(d["priceChangePercent"]),
                "volume_usd": float(d["quoteVolume"]),  # volume en USDT
                "high_24h":   float(d["highPrice"]),
                "low_24h":    float(d["lowPrice"]),
                "trades":     int(d["count"]),
                "source":     "Binance",
            }
            _cache_set(key, result)
            return result
    except Exception as e:
        log.debug("binance_ticker %s: %s", sym, e)
    return {}


def binance_klines(
    symbol_yf: str,
    interval: str = "1d",
    period: str = "3mo",
) -> pd.DataFrame:
    """
    Données OHLCV Binance (source la plus rapide pour crypto).
    Cache 30s pour intraday, 120s pour daily+.

    Retourne : DataFrame avec colonnes Open/High/Low/Close/Volume, index datetime UTC.
    """
    sym = BINANCE_MAP.get(symbol_yf)
    if not sym:
        return pd.DataFrame()

    bi = BINANCE_INTERVAL_MAP.get(interval, "1d")
    days = _PERIOD_DAYS.get(period, 90)
    cpd = _CANDLES_PER_DAY.get(bi, 1)
    limit = min(max(int(days * cpd) + 5, 50), 1000)

    key = f"bklines_{sym}_{bi}_{limit}"
    ttl = 30 if bi in ("1m", "3m", "5m", "15m", "30m", "1h") else 120
    cached = _cache_get(key, ttl=ttl)
    if cached is not None:
        return cached.copy()

    try:
        r = requests.get(
            f"{BINANCE_BASE}/klines",
            params={"symbol": sym, "interval": bi, "limit": limit},
            timeout=6,
        )
        if r.status_code != 200:
            return pd.DataFrame()
        cols = [
            "ts", "Open", "High", "Low", "Close", "Volume",
            "close_ts", "qvol", "trades", "tb", "tq", "ign",
        ]
        df = pd.DataFrame(r.json(), columns=cols)
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_localize(None)
        df.set_index("ts", inplace=True)
        for c in ["Open", "High", "Low", "Close", "Volume"]:
            df[c] = df[c].astype(float)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        _cache_set(key, df)
        return df.copy()
    except Exception as e:
        log.debug("binance_klines %s/%s: %s", sym, bi, e)
    return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────────
# ② COINGECKO API v3
#    Documentation : https://www.coingecko.com/api/documentation
#    Limites : ~30 req/min sans clé — parfait pour les besoins du dashboard
# ──────────────────────────────────────────────────────────────────────────────

CG_BASE = "https://api.coingecko.com/api/v3"

# Correspondance Yahoo Finance → CoinGecko ID
CG_MAP: Dict[str, str] = {
    "BTC-USD":   "bitcoin",
    "ETH-USD":   "ethereum",
    "BNB-USD":   "binancecoin",
    "SOL-USD":   "solana",
    "XRP-USD":   "ripple",
    "ADA-USD":   "cardano",
    "AVAX-USD":  "avalanche-2",
    "DOGE-USD":  "dogecoin",
    "DOT-USD":   "polkadot",
    "LINK-USD":  "chainlink",
    "MATIC-USD": "matic-network",
    "ATOM-USD":  "cosmos",
    "LTC-USD":   "litecoin",
    "UNI-USD":   "uniswap",
    "SHIB-USD":  "shiba-inu",
}
_CG_REVERSE: Dict[str, str] = {v: k for k, v in CG_MAP.items()}


def coingecko_prices(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Prix + market cap pour plusieurs cryptos en UN seul appel batch (cache 30s).

    Retourne : {yahoo_symbol: {price, change_pct, market_cap, volume_24h, source}}
    """
    ids = [CG_MAP[s] for s in symbols if s in CG_MAP]
    if not ids:
        return {}
    key = f"cg_prices_{'_'.join(sorted(ids))}"
    cached = _cache_get(key, ttl=30)
    if cached is not None:
        return cached

    try:
        r = requests.get(
            f"{CG_BASE}/simple/price",
            params={
                "ids": ",".join(ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
            timeout=6,
        )
        if r.status_code == 200:
            raw = r.json()
            result = {}
            for cg_id, vals in raw.items():
                yf_sym = _CG_REVERSE.get(cg_id)
                if not yf_sym:
                    continue
                result[yf_sym] = {
                    "price":      float(vals.get("usd", 0)),
                    "change_pct": float(vals.get("usd_24h_change", 0) or 0),
                    "market_cap": float(vals.get("usd_market_cap", 0) or 0),
                    "volume_24h": float(vals.get("usd_24h_vol", 0) or 0),
                    "source":     "CoinGecko",
                }
            _cache_set(key, result)
            return result
    except Exception as e:
        log.debug("coingecko_prices: %s", e)
    return {}


def coingecko_global() -> Dict[str, Any]:
    """
    Données globales du marché crypto (cache 2min).

    Retourne : total_market_cap_usd, market_cap_change_pct, btc_dominance,
               eth_dominance, active_coins, total_volume_usd
    """
    key = "cg_global"
    cached = _cache_get(key, ttl=120)
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{CG_BASE}/global", timeout=6)
        if r.status_code == 200:
            d = r.json().get("data", {})
            mc   = d.get("total_market_cap", {})
            vol  = d.get("total_volume", {})
            domp = d.get("market_cap_percentage", {})
            result = {
                "total_market_cap_usd": mc.get("usd", 0),
                "total_volume_usd":     vol.get("usd", 0),
                "market_cap_change_pct": d.get("market_cap_change_percentage_24h_usd", 0),
                "btc_dominance":  domp.get("btc", 0),
                "eth_dominance":  domp.get("eth", 0),
                "active_coins":   d.get("active_cryptocurrencies", 0),
                "markets":        d.get("markets", 0),
            }
            _cache_set(key, result)
            return result
    except Exception as e:
        log.debug("coingecko_global: %s", e)
    return {}


def coingecko_trending() -> List[Dict[str, Any]]:
    """Top 7 tendances CoinGecko (cache 10min)."""
    key = "cg_trending"
    cached = _cache_get(key, ttl=600)
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{CG_BASE}/search/trending", timeout=6)
        if r.status_code == 200:
            coins = r.json().get("coins", [])
            result = []
            for item in coins[:7]:
                c = item.get("item", {})
                result.append({
                    "name":   c.get("name", ""),
                    "symbol": c.get("symbol", "").upper(),
                    "rank":   c.get("market_cap_rank", "?"),
                    "score":  c.get("score", 0),
                })
            _cache_set(key, result)
            return result
    except Exception as e:
        log.debug("coingecko_trending: %s", e)
    return []


# ──────────────────────────────────────────────────────────────────────────────
# ③ FRANKFURTER (BCE) — taux de change officiels
#    Documentation : https://www.frankfurter.app/docs/
#    Limites : illimité, données BCE (mise à jour 16h CET chaque jour ouvré)
# ──────────────────────────────────────────────────────────────────────────────

FX_BASE = "https://api.frankfurter.app"

# Yahoo Finance → (base, quote) pour Frankfurter
_FX_PAIRS: Dict[str, Tuple[str, str]] = {
    "EURUSD=X": ("EUR", "USD"),
    "GBPUSD=X": ("GBP", "USD"),
    "USDJPY=X": ("USD", "JPY"),
    "USDCHF=X": ("USD", "CHF"),
    "AUDUSD=X": ("AUD", "USD"),
    "USDCAD=X": ("USD", "CAD"),
    "NZDUSD=X": ("NZD", "USD"),
    "EURGBP=X": ("EUR", "GBP"),
}


def frankfurter_rates() -> Dict[str, float]:
    """
    Taux de change BCE — un seul appel pour toutes les devises (cache 60s).
    Retourne : {yahoo_symbol: float_rate}
    """
    key = "fx_latest"
    cached = _cache_get(key, ttl=60)
    if cached is not None:
        return cached
    try:
        r = requests.get(f"{FX_BASE}/latest", params={"from": "EUR"}, timeout=5)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            rates["EUR"] = 1.0  # base
            result: Dict[str, float] = {}
            for yf_sym, (base, quote) in _FX_PAIRS.items():
                try:
                    # Conversion via EUR comme pivot
                    eur_to_base  = 1.0 / rates.get(base, 1) if base != "EUR" else 1.0
                    eur_to_quote = rates.get(quote, 1)
                    result[yf_sym] = round(eur_to_base * eur_to_quote, 6)
                except Exception:
                    pass
            _cache_set(key, result)
            return result
    except Exception as e:
        log.debug("frankfurter_rates: %s", e)
    return {}


# ──────────────────────────────────────────────────────────────────────────────
# ④ FRED (Federal Reserve Economic Data) — CSV public (pas de clé requise)
#    Documentation : https://fred.stlouisfed.org/docs/api/fred/
#    Les CSV publics ne nécessitent PAS de clé API
# ──────────────────────────────────────────────────────────────────────────────

FRED_SERIES_IDS: Dict[str, str] = {
    "CPI (YoY)":        "CPIAUCSL",
    "Fed Funds Rate":   "FEDFUNDS",
    "Chômage US":       "UNRATE",
    "10Y Treasury":     "DGS10",
    "2Y Treasury":      "DGS2",
    "Spread 10-2Y":     "T10Y2Y",
    "PIB Growth":       "A191RL1Q225SBEA",
    "M2 Money Supply":  "M2SL",
    "PCE Inflation":    "PCEPI",
    "Ventes Retail":    "RSAFS",
    "Prod. Industrielle": "INDPRO",
    "High Yield Spread": "BAMLH0A0HYM2",
}


def fred_series(series_id: str, limit: int = 120) -> pd.Series:
    """
    Télécharge une série FRED via CSV public (cache 1h).
    Ne nécessite pas de clé API.

    Retourne : pd.Series avec index datetime, ou Series vide si échec.
    """
    key = f"fred_{series_id}_{limit}"
    cached = _cache_get(key, ttl=3600)
    if cached is not None:
        return cached

    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        df = pd.read_csv(url, index_col=0, parse_dates=True)
        df = df.replace(".", np.nan).dropna()
        s = df.iloc[:, 0].astype(float).tail(limit)
        _cache_set(key, s)
        return s
    except Exception as e:
        log.debug("fred_series %s: %s", series_id, e)
    return pd.Series(dtype=float)


def fred_latest(series_id: str) -> Optional[float]:
    """Dernière valeur d'une série FRED."""
    s = fred_series(series_id, limit=5)
    return float(s.iloc[-1]) if not s.empty else None


# ──────────────────────────────────────────────────────────────────────────────
# ⑤ ROUTEUR INTELLIGENT — choisit la source la plus rapide
# ──────────────────────────────────────────────────────────────────────────────

_CRYPTO_SYMS = set(BINANCE_MAP.keys())
_FOREX_SYMS  = set(_FX_PAIRS.keys())


def _is_crypto(symbol: str) -> bool:
    """Retourne True si le symbole est une cryptomonnaie (supportée par Binance)."""
    return symbol in _CRYPTO_SYMS


def smart_price(symbol: str) -> Dict[str, Any]:
    """
    Prix temps réel en choisissant la source optimale :
      Crypto → Binance (cache 10s) avec fallback CoinGecko
      Forex  → Frankfurter
      Autres → yfinance

    Retourne : {price, change_pct, source} ou {} si échec total.
    """
    # ── Crypto : Binance en priorité ─────────────────────────────────────────
    if symbol in _CRYPTO_SYMS:
        t = binance_ticker(symbol)
        if t:
            return t
        # Fallback CoinGecko batch
        cg = coingecko_prices([symbol])
        if symbol in cg:
            return cg[symbol]

    # ── Forex : Frankfurter BCE ──────────────────────────────────────────────
    if symbol in _FOREX_SYMS:
        rates = frankfurter_rates()
        if symbol in rates:
            return {"price": rates[symbol], "change_pct": 0.0, "source": "Frankfurter (BCE)"}

    # ── Fallback universel : yfinance ────────────────────────────────────────
    key = f"yf_price_{symbol}"
    cached = _cache_get(key, ttl=60)
    if cached is not None:
        return cached
    try:
        h = yf.Ticker(symbol).history(period="2d")
        if not h.empty and len(h) >= 2:
            c0 = float(h["Close"].iloc[-2])
            c1 = float(h["Close"].iloc[-1])
            result = {
                "price":      c1,
                "change_pct": (c1 - c0) / c0 * 100 if c0 else 0.0,
                "source":     "Yahoo Finance",
            }
            _cache_set(key, result)
            return result
        elif not h.empty:
            c1 = float(h["Close"].iloc[-1])
            result = {"price": c1, "change_pct": 0.0, "source": "Yahoo Finance"}
            _cache_set(key, result)
            return result
    except Exception as e:
        log.debug("smart_price yf %s: %s", symbol, e)
    return {}


def smart_ohlcv(
    symbol: str,
    period: str = "3mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    OHLCV multi-source — choisit la source la plus rapide et la plus fiable.

    Crypto  → Binance (< 600ms, cache 30-120s selon interval)
    Autres  → yfinance avec guard-rails période/intervalle
    """
    # ── Crypto : Binance ──────────────────────────────────────────────────────
    if symbol in _CRYPTO_SYMS:
        df = binance_klines(symbol, interval, period)
        if not df.empty:
            return df
        # Fallback yfinance si Binance échoue

    # ── Guard-rails yfinance (intervalles incompatibles) ─────────────────────
    _max_days: Dict[str, int] = {
        "1m": 7, "2m": 59, "5m": 59, "15m": 59, "30m": 59,
        "60m": 729, "1h": 729, "1d": 3649, "1wk": 3649, "1mo": 3649,
    }
    _fallback_period: Dict[str, str] = {
        "1m": "5d", "2m": "5d", "5m": "5d", "15m": "5d", "30m": "5d",
        "60m": "2y", "1h": "2y", "1d": "5y", "1wk": "5y", "1mo": "5y",
    }
    import re as _re
    if interval in _max_days:
        m = _re.match(r"(\d+)(d|mo|y)", period or "3mo")
        if m:
            n, u = int(m.group(1)), m.group(2)
            days = n if u == "d" else (n * 30 if u == "mo" else n * 365)
            if days > _max_days[interval]:
                period = _fallback_period.get(interval, "3mo")

    key = f"yf_ohlcv_{symbol}_{period}_{interval}"
    ttl = 30 if interval in ("1m", "2m", "5m", "15m") else 120
    cached = _cache_get(key, ttl=ttl)
    if cached is not None:
        return cached.copy()

    try:
        df = yf.download(
            symbol, period=period, interval=interval,
            auto_adjust=True, progress=False, timeout=12,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        _cache_set(key, df)
        return df.copy()
    except Exception as e:
        log.debug("smart_ohlcv yf %s: %s", symbol, e)
    return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────────
# FETCH PARALLÈLE — plusieurs actifs simultanément
# ──────────────────────────────────────────────────────────────────────────────

def parallel_prices(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Récupère les prix de N actifs EN PARALLÈLE avec source optimale.

    Stratégie :
      - Batch CoinGecko pour toutes les cryptos (1 seul appel)
      - ThreadPoolExecutor pour les autres actifs (jusqu'à 8 workers)

    Retourne : {symbol: {price, change_pct, source, ...}}
    """
    result: Dict[str, Dict[str, Any]] = {}

    crypto_syms = [s for s in symbols if s in _CRYPTO_SYMS]
    forex_syms  = [s for s in symbols if s in _FOREX_SYMS]
    other_syms  = [s for s in symbols if s not in _CRYPTO_SYMS and s not in _FOREX_SYMS]

    # ── Crypto batch CoinGecko ───────────────────────────────────────────────
    if crypto_syms:
        try:
            cg_data = coingecko_prices(crypto_syms)
            for sym, data in cg_data.items():
                result[sym] = data
        except Exception as e:
            log.debug("parallel_prices CoinGecko: %s", e)
        # Fallback Binance pour les cryptos manquantes
        for sym in crypto_syms:
            if sym not in result:
                t = binance_ticker(sym)
                if t:
                    result[sym] = t

    # ── Forex batch Frankfurter ──────────────────────────────────────────────
    if forex_syms:
        try:
            rates = frankfurter_rates()
            for sym in forex_syms:
                if sym in rates:
                    result[sym] = {
                        "price": rates[sym], "change_pct": 0.0,
                        "source": "Frankfurter (BCE)",
                    }
        except Exception as e:
            log.debug("parallel_prices Frankfurter: %s", e)

    # ── Autres actifs — fetch parallèle ─────────────────────────────────────
    remaining = [s for s in (other_syms + forex_syms) if s not in result]
    if remaining:
        workers = min(len(remaining), 8)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(smart_price, s): s for s in remaining}
            try:
                for fut in as_completed(futs, timeout=12):
                    sym = futs[fut]
                    try:
                        d = fut.result()
                        if d:
                            result[sym] = d
                    except Exception as e:
                        log.debug("parallel_prices fut %s: %s", sym, e)
            except FutTimeoutError:
                log.debug("parallel_prices: timeout on some symbols")

    return result


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS UTILITAIRES
# ──────────────────────────────────────────────────────────────────────────────

def format_large(n: float) -> str:
    """Formate un grand nombre lisible : 2.72e12 → '2.72 T$'."""
    try:
        n = float(n)
        if n >= 1e12:
            return f"{n/1e12:.2f} T$"     # Trillion
        if n >= 1e9:
            return f"{n/1e9:.2f} Md$"     # Milliard
        if n >= 1e6:
            return f"{n/1e6:.2f} M$"      # Million
        if n >= 1e3:
            return f"{n/1e3:.1f} K$"      # Millier
        return f"{n:.2f}$"
    except Exception:
        return "—"
