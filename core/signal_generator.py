"""signal_generator.py — Générateur de signaux de trading."""
import pandas as pd
import numpy as np


class SignalGenerator:
    def generate_signals(self, df: pd.DataFrame, symbol: str = "",
                         risk_pct: float = 0.02, capital: float = 100.0) -> dict:
        if df.empty or len(df) < 20:
            return {}
        last = df.iloc[-1]
        rsi  = float(last.get("RSI", 50))
        macd = float(last.get("MACD", 0))
        sig  = float(last.get("Signal", 0))
        sma20 = float(last.get("SMA20", last["Close"]))
        close = float(last["Close"])
        score = 0
        if close > sma20:  score += 1
        if macd > sig:     score += 1
        if 30 <= rsi <= 65: score += 1
        direction = "BUY" if score >= 2 else "SELL" if score == 0 else "HOLD"
        return {
            "direction": direction,
            "score": score,
            "rsi": rsi,
            "history": [],
        }
