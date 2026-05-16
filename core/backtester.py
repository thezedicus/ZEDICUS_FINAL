"""backtester.py — Moteur de backtesting.

Corrections v2 :
- Win rate calculé sur trades gagnants / total trades (pas sur barres)
- Frais de transaction 0.1% par côté (0.2% aller-retour)
- Slippage 0.05% par trade
- Drawdown max calculé sur equity réelle (pas sur cumsum P&L)
- Signaux décalés d'1 barre pour éviter le look-ahead bias
- Longs uniquement (pas de shorts synthétiques non disponibles en micro-capital)
"""
import numpy as np
import pandas as pd

COMMISSION = 0.001   # 0.1% par côté (Binance maker)
SLIPPAGE   = 0.0005  # 0.05% par trade


class Backtester:
    def run(self, df: pd.DataFrame, strategy: str = "SMA",
            capital: float = 100.0, risk_pct: float = 0.02) -> dict:
        df = df.copy().dropna()
        if len(df) < 30:
            return {}

        # ── Génération des signaux (long uniquement : 1=long, 0=flat) ──────────
        if "SMA" in strategy or "Croisement" in strategy:
            # Long quand SMA20 > SMA50, flat sinon (pas de short)
            df["sig"] = np.where(df["SMA20"] > df["SMA50"], 1, 0)
        elif "RSI" in strategy:
            df["sig"] = np.where(df["RSI"] < 30, 1, np.where(df["RSI"] > 70, 0, np.nan))
            df["sig"] = df["sig"].ffill().fillna(0)
        else:  # MACD
            df["sig"] = np.where(df["MACD"] > df["Signal"], 1, 0)

        # ── Décalage d'1 barre : signal i exécuté à l'ouverture i+1 ──────────
        df["sig_prev"] = df["sig"].shift(1).fillna(0)
        df["sig_change"] = df["sig_prev"].diff().abs().fillna(0)

        # ── Simulation trade par trade ────────────────────────────────────────
        eq          = capital
        position    = 0
        entry_price = 0.0
        trades_pnl  = []
        equity_curve = [capital]

        for i in range(1, len(df)):
            price = float(df["Close"].iloc[i])
            if price <= 0:
                equity_curve.append(eq)
                continue

            sig_cur = int(df["sig_prev"].iloc[i])

            # Entrée en position (long)
            if position == 0 and sig_cur == 1:
                position    = 1
                entry_price = price * (1 + COMMISSION + SLIPPAGE)

            # Sortie de position
            elif position == 1 and sig_cur == 0:
                exit_price = price * (1 - COMMISSION - SLIPPAGE)
                trade_ret  = (exit_price - entry_price) / entry_price
                pnl        = trade_ret * eq * min(risk_pct * 10, 0.40)
                eq        += pnl
                eq         = max(eq, 0.01)
                trades_pnl.append(pnl)
                position    = 0
                entry_price = 0.0

            # Equity courante
            if position == 1 and entry_price > 0:
                live_eq = eq + (price / entry_price - 1) * eq * min(risk_pct * 10, 0.40)
            else:
                live_eq = eq
            equity_curve.append(max(live_eq, 0.01))

        # ── Métriques ─────────────────────────────────────────────────────────
        final     = equity_curve[-1]
        total_ret = (final - capital) / capital * 100

        n_trades = len(trades_pnl)
        wins     = [t for t in trades_pnl if t > 0]
        losses   = [t for t in trades_pnl if t <= 0]
        win_rate = len(wins) / n_trades if n_trades > 0 else 0.0

        sum_wins   = sum(wins)   if wins   else 0.0
        sum_losses = abs(sum(losses)) if losses else 0.0
        pf = sum_wins / sum_losses if sum_losses > 0 else (9.99 if sum_wins > 0 else 0.0)

        # Sharpe sur rendements journaliers (position × Ret1 de l'actif)
        df["active"] = df["sig_prev"].astype(float)
        df["strat_ret"] = df["active"] * df.get("Ret1", df["Close"].pct_change())
        sr_std = float(df["strat_ret"].std())
        sr_mean = float(df["strat_ret"].mean())
        sharpe = round(sr_mean / sr_std * np.sqrt(252), 2) if sr_std > 0 else 0.0

        # Max drawdown sur equity curve réelle
        eq_arr  = np.array(equity_curve)
        peak    = np.maximum.accumulate(eq_arr)
        max_dd  = float(np.min((eq_arr - peak) / np.where(peak > 0, peak, 1))) * 100

        return {
            "total_return":  round(total_ret, 2),
            "num_trades":    n_trades,
            "win_rate":      round(win_rate, 4),   # fraction 0.0–1.0
            "sharpe":        round(sharpe, 2),
            "max_drawdown":  round(max_dd, 2),
            "profit_factor": round(min(pf, 99.9), 2),
            "final_capital": round(final, 2),
            "equity_curve":  equity_curve,
        }
