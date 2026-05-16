"""screener.py — Screener d'opportunités."""
import yfinance as yf
import pandas as pd


class Screener:
    def get_top_opportunities(self, category: str = "", capital: float = 100.0) -> list:
        return []

    def scan(self, symbols: list, filters: dict = None) -> list:
        results = []
        for sym in symbols[:10]:
            try:
                t = yf.Ticker(sym)
                h = t.history(period="5d")
                if len(h) >= 2:
                    chg = (float(h["Close"].iloc[-1]) - float(h["Close"].iloc[-2])) / float(h["Close"].iloc[-2]) * 100
                    results.append({"symbol": sym, "change_pct": round(chg, 2)})
            except Exception:
                pass
        return sorted(results, key=lambda x: -abs(x["change_pct"]))
