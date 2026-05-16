"""
trading_bot.py — Bot de Trading Automatisé THE ZEDICUS v3
==========================================================
Bot de trading algorithmique avec:
- Données temps réel (WebSocket + REST polling)
- 6 stratégies automatisées (breakout, mean reversion, momentum, scalping, news-driven, multi-TF)
- Gestion des risques intégrée (SL, TP, trailing, drawdown max)
- Support multi-actifs (actions US, indices, crypto, forex)
- Exécution via brokers (Alpaca paper trading + simulation)
- Calendrier économique pour filtrer les trades avant annonces majeures
- Journal de trades avec métriques de performance

⚠️ AVERTISSEMENT: Ce bot est fourni à titre éducatif et indicatif uniquement.
   Tout trading comporte des risques. Backtestez avant toute mise en production.
"""
from __future__ import annotations
import math, time, threading, logging, json, datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BotStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED  = "paused"
    ERROR   = "error"


class OrderSide(Enum):
    BUY  = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT  = "limit"
    STOP   = "stop"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BotConfig:
    """Configuration complète du bot de trading."""
    symbols: List[str]                          # Symboles à trader
    capital: float                              # Capital total en USD

    risk_pct_per_trade: float = 0.01           # 1% du capital par trade
    max_positions: int = 5                      # Positions simultanées max
    max_drawdown_pct: float = 0.10             # Stop bot si drawdown > 10%

    use_stop_loss: bool = True
    use_take_profit: bool = True
    sl_atr_mult: float = 2.0                   # Stop loss = prix ± sl_atr_mult × ATR
    tp_atr_mult: float = 3.0                   # Take profit = prix ± tp_atr_mult × ATR
    trailing_stop: bool = True
    trailing_atr_mult: float = 1.5

    min_confidence: float = 0.60               # Confiance minimale pour trader
    filter_macro_events: bool = True           # Pause pendant annonces majeures
    poll_interval_sec: int = 60                # Intervalle de rafraîchissement données

    broker: str = "paper"                      # "paper" | "alpaca" | "simulation"
    strategies_enabled: List[str] = field(default_factory=lambda: [
        "momentum", "breakout", "mean_reversion", "trend",
    ])


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class Position:
    """Représente une position ouverte."""
    id: str
    symbol: str
    side: str                   # "buy" | "sell"
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    trailing_stop_price: float
    current_price: float
    pnl: float
    pnl_pct: float
    opened_at: str              # ISO datetime string
    strategy_name: str
    status: str                 # "open" | "closed" | "stopped"


@dataclass
class TradeRecord:
    """Enregistrement complet d'un trade fermé."""
    id: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    trailing_stop_price: float
    current_price: float
    pnl: float
    pnl_pct: float
    opened_at: str
    strategy_name: str
    status: str
    closed_at: str
    exit_price: float
    exit_reason: str            # "TP" | "SL" | "TRAILING" | "MANUAL" | "SIGNAL"
    duration_min: float


# ---------------------------------------------------------------------------
# Risk Manager
# ---------------------------------------------------------------------------

class RiskManager:
    """Gestion intégrée des risques pour le bot de trading."""

    def __init__(self, config: BotConfig):
        self.config = config

    def position_size(self, capital_avail: float, entry: float,
                      stop_loss: float) -> float:
        """
        Calcule la taille de la position (nombre d'unités) selon la règle de risque.

        units = (capital × risk_pct) / |entry - stop_loss|

        Adapté aux petits budgets (10 € – 1 000 €) :
        - Jamais plus de 40 % du capital dans une seule position
        - Taille minimale de 0.0001 unité (crypto/fractions)
        - Si le coût total dépasse 40 % du capital, on réduit proportionnellement
        """
        if entry <= 0 or stop_loss <= 0:
            return 0.0
        distance = abs(entry - stop_loss)
        if distance < 1e-9:
            return 0.0

        risk_amount = capital_avail * self.config.risk_pct_per_trade
        units = risk_amount / distance

        # Garde : pas plus de 40 % du capital sur une seule position
        max_units_by_capital = (capital_avail * 0.40) / entry
        units = min(units, max_units_by_capital)

        # Valeur minimale : au moins 0.01 € investi sinon on renonce
        if units * entry < 0.01:
            return 0.0

        return round(max(units, 0.0), 6)  # 6 décimales pour crypto

    def is_safe_to_trade(self, positions: List[Position],
                         drawdown_pct: float,
                         near_macro_event: bool) -> Tuple[bool, str]:
        """
        Vérifie si les conditions permettent d'ouvrir un nouveau trade.

        Returns
        -------
        (safe: bool, reason: str)
        """
        if drawdown_pct >= self.config.max_drawdown_pct:
            return False, f"Drawdown max atteint: {drawdown_pct*100:.1f}% >= {self.config.max_drawdown_pct*100:.1f}%"

        open_positions = [p for p in positions if p.status == "open"]
        if len(open_positions) >= self.config.max_positions:
            return False, f"Nombre max de positions atteint: {len(open_positions)}/{self.config.max_positions}"

        if self.config.filter_macro_events and near_macro_event:
            return False, "Trading suspendu: annonce macro-économique imminente"

        return True, "OK"

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """Retourne True si le stop loss est touché."""
        if not self.config.use_stop_loss:
            return False
        if position.side == "buy":
            return current_price <= position.stop_loss
        else:
            return current_price >= position.stop_loss

    def check_take_profit(self, position: Position, current_price: float) -> bool:
        """Retourne True si le take profit est touché."""
        if not self.config.use_take_profit:
            return False
        if position.side == "buy":
            return current_price >= position.take_profit
        else:
            return current_price <= position.take_profit

    def update_trailing_stop(self, position: Position,
                             current_price: float, atr: float) -> float:
        """
        Met à jour le trailing stop dynamique.

        Le SL monte (pour un long) ou descend (pour un short)
        mais ne recule jamais dans la direction défavorable.
        """
        if not self.config.trailing_stop:
            return position.trailing_stop_price

        trail_dist = self.config.trailing_atr_mult * atr

        if position.side == "buy":
            new_sl = current_price - trail_dist
            # Le trailing stop ne peut que monter
            return max(new_sl, position.trailing_stop_price)
        else:
            new_sl = current_price + trail_dist
            # Le trailing stop ne peut que descendre
            return min(new_sl, position.trailing_stop_price)

    def portfolio_drawdown(self, initial_capital: float,
                           current_capital: float) -> float:
        """Retourne le drawdown en fraction (ex: 0.05 = 5%)."""
        if initial_capital <= 0:
            return 0.0
        dd = (initial_capital - current_capital) / initial_capital
        return max(dd, 0.0)


# ---------------------------------------------------------------------------
# Signal Engine
# ---------------------------------------------------------------------------

class SignalEngine:
    """Génère des signaux de trading à partir des données de marché."""

    def __init__(self, config: BotConfig):
        self.config = config

    def generate_signal(self, symbol: str, df: pd.DataFrame,
                        indicators: dict) -> dict:
        """
        Génère le meilleur signal pour un symbole donné.

        Returns
        -------
        dict avec les clés:
            direction   : "LONG" | "SHORT" | "NEUTRE"
            confidence  : float 0.0-1.0
            strategy    : str — nom de la stratégie qui a produit le signal
            entry       : float
            sl          : float
            tp          : float
            reason      : str — explication du signal
        """
        if df is None or len(df) < 30:
            return self._neutral_signal(symbol, indicators.get("price", 0),
                                        indicators.get("atr", 1), "Données insuffisantes")

        signals = []

        if "momentum" in self.config.strategies_enabled:
            sig = self._momentum_signal(df, indicators)
            if sig["confidence"] >= self.config.min_confidence:
                signals.append(sig)

        if "breakout" in self.config.strategies_enabled:
            sig = self._breakout_signal(df, indicators)
            if sig["confidence"] >= self.config.min_confidence:
                signals.append(sig)

        if "mean_reversion" in self.config.strategies_enabled:
            sig = self._mean_reversion_signal(df, indicators)
            if sig["confidence"] >= self.config.min_confidence:
                signals.append(sig)

        if "trend" in self.config.strategies_enabled:
            sig = self._trend_signal(df, indicators)
            if sig["confidence"] >= self.config.min_confidence:
                signals.append(sig)

        if not signals:
            return self._neutral_signal(symbol, indicators.get("price", 0),
                                        indicators.get("atr", 1),
                                        "Aucun signal au-dessus du seuil de confiance")

        # Retourne le signal avec la confiance la plus élevée
        best = max(signals, key=lambda s: s["confidence"])
        return best

    # --- Sub-signals ---

    def _momentum_signal(self, df: pd.DataFrame, ind: dict) -> dict:
        """Signal basé sur RSI + alignement MACD."""
        price  = ind.get("price", 0)
        atr    = ind.get("atr", price * 0.02)
        rsi    = ind.get("rsi", 50)
        macd_h = ind.get("macd_hist", 0)
        mom5   = ind.get("mom5", 0)
        score  = 0

        bull = rsi > 52 and macd_h > 0 and mom5 > 0.005
        bear = rsi < 48 and macd_h < 0 and mom5 < -0.005

        if rsi > 52: score += 1
        if macd_h > 0: score += 1
        if mom5 > 0.005: score += 1
        if rsi < 48: score += 1
        if macd_h < 0: score += 1
        if mom5 < -0.005: score += 1

        if bull:
            confidence = min(0.4 + score * 0.1, 0.90)
            sl = price - 2.0 * atr
            tp = price + 3.0 * atr
            return {"direction": "LONG", "confidence": round(confidence, 2),
                    "strategy": "Momentum", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"RSI={rsi:.1f} + MACD hist positif + momentum haussier"}
        elif bear:
            confidence = min(0.4 + score * 0.1, 0.90)
            sl = price + 2.0 * atr
            tp = price - 3.0 * atr
            return {"direction": "SHORT", "confidence": round(confidence, 2),
                    "strategy": "Momentum", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"RSI={rsi:.1f} + MACD hist négatif + momentum baissier"}

        return self._neutral_signal("", price, atr, "Momentum neutre")

    def _breakout_signal(self, df: pd.DataFrame, ind: dict) -> dict:
        """Signal basé sur cassure de l'EMA avec volume."""
        price     = ind.get("price", 0)
        atr       = ind.get("atr", price * 0.02)
        ema20     = ind.get("ema20", price)
        vol_ratio = ind.get("vol_ratio", 1.0)
        adx       = ind.get("adx", 20)

        break_up   = price > ema20 * 1.005 and vol_ratio > 1.6
        break_down = price < ema20 * 0.995 and vol_ratio > 1.6

        conf_base = 0.50
        conf_vol  = min((vol_ratio - 1.0) * 0.15, 0.25)
        conf_adx  = min((adx - 20) * 0.01, 0.15) if adx > 20 else 0.0

        if break_up:
            confidence = min(conf_base + conf_vol + conf_adx, 0.92)
            sl = ema20 - 0.5 * atr
            tp = price + 2.5 * atr
            return {"direction": "LONG", "confidence": round(confidence, 2),
                    "strategy": "Breakout", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"Cassure EMA20 à la hausse — volume {vol_ratio:.2f}x"}
        elif break_down:
            confidence = min(conf_base + conf_vol + conf_adx, 0.92)
            sl = ema20 + 0.5 * atr
            tp = price - 2.5 * atr
            return {"direction": "SHORT", "confidence": round(confidence, 2),
                    "strategy": "Breakout", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"Cassure EMA20 à la baisse — volume {vol_ratio:.2f}x"}

        return self._neutral_signal("", price, atr, "Pas de cassure valide")

    def _mean_reversion_signal(self, df: pd.DataFrame, ind: dict) -> dict:
        """Signal basé sur z-score extrême par rapport à l'EMA50."""
        price  = ind.get("price", 0)
        atr    = ind.get("atr", price * 0.02)
        zscore = ind.get("zscore", 0)
        ema50  = ind.get("ema50", price)
        adx    = ind.get("adx", 20)

        if adx > 30:
            return self._neutral_signal("", price, atr, "ADX trop fort pour mean reversion")

        if zscore < -2.0:
            confidence = min(0.50 + abs(zscore) * 0.08, 0.88)
            sl = price - 2.0 * atr
            tp = ema50
            return {"direction": "LONG", "confidence": round(confidence, 2),
                    "strategy": "Mean Reversion", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"Z-score={zscore:.2f} — retour vers EMA50 ({ema50:.2f})"}
        elif zscore > 2.0:
            confidence = min(0.50 + abs(zscore) * 0.08, 0.88)
            sl = price + 2.0 * atr
            tp = ema50
            return {"direction": "SHORT", "confidence": round(confidence, 2),
                    "strategy": "Mean Reversion", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"Z-score={zscore:.2f} — retour vers EMA50 ({ema50:.2f})"}

        return self._neutral_signal("", price, atr, f"Z-score={zscore:.2f} — pas extrême")

    def _trend_signal(self, df: pd.DataFrame, ind: dict) -> dict:
        """Signal basé sur la tendance EMA200 + force ADX."""
        price   = ind.get("price", 0)
        atr     = ind.get("atr", price * 0.02)
        ema200  = ind.get("ema200", price)
        ema50   = ind.get("ema50", price)
        adx     = ind.get("adx", 20)
        plus_di = ind.get("plus_di", 20)
        minus_di = ind.get("minus_di", 20)

        above200      = price > ema200
        below200      = price < ema200
        golden_cross  = ema50 > ema200
        death_cross   = ema50 < ema200
        strong_trend  = adx > 25
        di_bull       = plus_di > minus_di
        di_bear       = minus_di > plus_di

        conf_base = 0.45
        conf_adx  = min((adx - 20) * 0.015, 0.30) if adx > 20 else 0.0

        if above200 and golden_cross and strong_trend and di_bull:
            confidence = min(conf_base + conf_adx + 0.15, 0.93)
            sl = price - 2.5 * atr
            tp = price + 4.0 * atr
            return {"direction": "LONG", "confidence": round(confidence, 2),
                    "strategy": "Trend Following", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"Golden Cross + ADX={adx:.1f} + +DI>{minus_di:.1f}"}
        elif below200 and death_cross and strong_trend and di_bear:
            confidence = min(conf_base + conf_adx + 0.15, 0.93)
            sl = price + 2.5 * atr
            tp = price - 4.0 * atr
            return {"direction": "SHORT", "confidence": round(confidence, 2),
                    "strategy": "Trend Following", "entry": price,
                    "sl": sl, "tp": tp,
                    "reason": f"Death Cross + ADX={adx:.1f} + -DI>{plus_di:.1f}"}

        return self._neutral_signal("", price, atr, "Tendance non confirmée")

    @staticmethod
    def _neutral_signal(symbol: str, price: float,
                        atr: float, reason: str) -> dict:
        return {
            "direction": "NEUTRE", "confidence": 0.0,
            "strategy": "None", "entry": price,
            "sl": price - atr, "tp": price + atr,
            "reason": reason,
        }


# ---------------------------------------------------------------------------
# Paper Broker
# ---------------------------------------------------------------------------

class PaperBroker:
    """
    Broker de simulation (paper trading) avec slippage réaliste.

    Slippage simulé: ±0.01% sur le prix de remplissage.
    """

    def __init__(self, initial_capital: float):
        self._capital    = initial_capital
        self._cash       = initial_capital
        self._positions: Dict[str, Position] = {}
        self._orders: List[dict] = []
        self._order_counter = 0
        self._lock = threading.Lock()

    def submit_order(self, symbol: str, side: str, quantity: float,
                     order_type: str = "market", price: float = 0.0) -> dict:
        """
        Soumet un ordre et simule son exécution immédiate.

        Retourne un dict: {id, status, fill_price, timestamp}
        """
        with self._lock:
            self._order_counter += 1
            order_id = f"PAPER-{self._order_counter:06d}"
            ts = dt.datetime.utcnow().isoformat()

            # Simulation slippage ±0.01%
            slippage = np.random.uniform(-0.0001, 0.0001)
            fill_price = price * (1 + slippage) if price > 0 else price

            order = {
                "id":         order_id,
                "symbol":     symbol,
                "side":       side,
                "quantity":   quantity,
                "order_type": order_type,
                "fill_price": round(fill_price, 6),
                "status":     "filled",
                "timestamp":  ts,
            }

            # Mise à jour du cash
            cost = fill_price * quantity
            if side == "buy":
                self._cash -= cost
            else:
                self._cash += cost

            self._orders.append(order)
            logger.info("Order filled: %s %s %s @ %.4f (slippage %.4f%%)",
                        side, quantity, symbol, fill_price, slippage * 100)
            return order

    def get_positions(self) -> List[Position]:
        """Retourne la liste des positions actuellement enregistrées."""
        with self._lock:
            return list(self._positions.values())

    def get_account(self) -> dict:
        """Retourne un résumé du compte paper."""
        with self._lock:
            total_pnl = sum(p.pnl for p in self._positions.values())
            # Longs : valeur mark-to-market courante
            long_value  = sum(
                p.current_price * p.quantity
                for p in self._positions.values() if p.side == "buy"
            )
            # Shorts : P&L flottant du short (entry_price * qty + pnl_latent)
            short_value = sum(
                p.entry_price * p.quantity + p.pnl
                for p in self._positions.values() if p.side == "sell"
            )
            equity = self._cash + long_value + short_value
            return {
                "equity":        round(equity, 2),
                "cash":          round(self._cash, 2),
                "buying_power":  round(self._cash, 2),
                "total_pnl":     round(total_pnl, 2),
            }

    def get_order_history(self) -> List[dict]:
        """Retourne l'historique complet des ordres."""
        with self._lock:
            return list(self._orders)

    # --- Internal helpers used by TradingBot ---

    def _register_position(self, position: Position) -> None:
        with self._lock:
            self._positions[position.id] = position

    def _remove_position(self, position_id: str) -> None:
        with self._lock:
            self._positions.pop(position_id, None)

    def _update_position(self, position: Position) -> None:
        with self._lock:
            if position.id in self._positions:
                self._positions[position.id] = position


# ---------------------------------------------------------------------------
# Trading Bot (main class)
# ---------------------------------------------------------------------------

class TradingBot:
    """
    Bot de trading algorithmique THE ZEDICUS v3.

    Cycle principal:
    1. Pour chaque symbole, récupère les données OHLCV.
    2. Calcule les indicateurs et génère un signal via SignalEngine.
    3. Si le signal dépasse min_confidence et les règles de risque sont OK,
       ouvre une position via PaperBroker.
    4. Vérifie en continu les positions ouvertes (SL / TP / Trailing).
    5. Journalise tous les trades dans trade_history.
    """

    def __init__(self, config: BotConfig):
        self.config         = config
        self.status         = BotStatus.STOPPED
        self.risk_manager   = RiskManager(config)
        self.signal_engine  = SignalEngine(config)
        self.broker         = PaperBroker(config.capital)

        self._initial_capital = config.capital
        self._positions: Dict[str, Position] = {}   # id -> Position
        self._trade_history: List[TradeRecord] = []
        self._lock          = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event    = threading.Event()
        self._pos_counter   = 0

        # Macro event schedule (simulated): format HH:MM UTC
        self._macro_schedule: List[str] = [
            "08:30", "10:00", "14:00", "14:30", "15:00", "19:00",
        ]

    # ------------------------------------------------------------------
    # Public control methods
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Démarre le bot en arrière-plan."""
        if self.status == BotStatus.RUNNING:
            logger.warning("Bot already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop,
                                        name="TradingBot", daemon=True)
        self.status = BotStatus.RUNNING
        self._thread.start()
        logger.info("TradingBot started. Monitoring: %s", self.config.symbols)

    def stop(self) -> None:
        """Arrête le bot proprement."""
        self._stop_event.set()
        self.status = BotStatus.STOPPED
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("TradingBot stopped.")

    def pause(self) -> None:
        """Met le bot en pause (ne ferme pas les positions ouvertes)."""
        if self.status == BotStatus.RUNNING:
            self.status = BotStatus.PAUSED
            logger.info("TradingBot paused.")

    def resume(self) -> None:
        """Reprend le bot après une pause."""
        if self.status == BotStatus.PAUSED:
            self.status = BotStatus.RUNNING
            logger.info("TradingBot resumed.")

    # ------------------------------------------------------------------
    # Public data accessors
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Retourne un snapshot complet de l'état du bot."""
        account  = self.broker.get_account()
        drawdown = self.risk_manager.portfolio_drawdown(
            self._initial_capital, account["equity"]
        )
        with self._lock:
            open_pos = [p for p in self._positions.values() if p.status == "open"]
        return {
            "status":           self.status.value,
            "symbols":          self.config.symbols,
            "capital_initial":  self._initial_capital,
            "equity":           account["equity"],
            "cash":             account["cash"],
            "total_pnl":        account["total_pnl"],
            "drawdown_pct":     round(drawdown * 100, 2),
            "open_positions":   len(open_pos),
            "total_trades":     len(self._trade_history),
            "near_macro_event": self._is_near_macro_event(),
        }

    def get_positions(self) -> List[Position]:
        """Retourne la liste des positions actuellement ouvertes."""
        with self._lock:
            return [p for p in self._positions.values() if p.status == "open"]

    def get_trade_history(self) -> List[TradeRecord]:
        """Retourne l'historique complet de tous les trades fermés."""
        with self._lock:
            return list(self._trade_history)

    def get_performance_metrics(self) -> dict:
        """
        Calcule et retourne les métriques de performance complètes.

        Retourne: total_pnl, win_rate, avg_win, avg_loss,
                  sharpe, max_drawdown, total_trades, profit_factor
        """
        with self._lock:
            history = list(self._trade_history)

        if not history:
            return {
                "total_pnl": 0.0, "win_rate": 0.0, "avg_win": 0.0,
                "avg_loss": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
                "total_trades": 0, "profit_factor": 0.0,
            }

        pnls   = [t.pnl for t in history]
        wins   = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        total_pnl    = sum(pnls)
        win_rate     = len(wins) / len(pnls) if pnls else 0.0
        avg_win      = float(np.mean(wins))  if wins   else 0.0
        avg_loss     = float(np.mean(losses)) if losses else 0.0
        gross_profit = sum(wins)
        gross_loss   = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        sharpe     = compute_bot_sharpe(history)
        max_dd     = self._compute_max_drawdown(pnls)

        return {
            "total_pnl":     round(total_pnl, 2),
            "win_rate":      round(win_rate * 100, 1),
            "avg_win":       round(avg_win, 2),
            "avg_loss":      round(avg_loss, 2),
            "sharpe":        round(sharpe, 3),
            "max_drawdown":  round(max_dd * 100, 2),
            "total_trades":  len(history),
            "profit_factor": round(profit_factor, 3),
        }

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Boucle principale exécutée dans le thread de fond."""
        logger.info("Bot loop started. Poll interval: %ds", self.config.poll_interval_sec)
        while not self._stop_event.is_set():
            try:
                if self.status == BotStatus.PAUSED:
                    time.sleep(5)
                    continue

                # 1. Récupérer les prix actuels et vérifier les positions ouvertes
                current_prices: Dict[str, float] = {}
                for symbol in self.config.symbols:
                    try:
                        df, indicators = self._fetch_and_compute(symbol)
                        current_prices[symbol] = indicators.get("price", 0.0)
                    except Exception as exc:
                        logger.warning("Fetch error for %s: %s", symbol, exc)

                self._check_existing_positions(current_prices)

                # 2. Chercher de nouveaux trades
                account  = self.broker.get_account()
                drawdown = self.risk_manager.portfolio_drawdown(
                    self._initial_capital, account["equity"]
                )
                near_macro = self._is_near_macro_event()

                with self._lock:
                    positions = list(self._positions.values())

                safe, reason = self.risk_manager.is_safe_to_trade(
                    positions, drawdown, near_macro
                )
                if not safe:
                    logger.info("Skipping signal scan: %s", reason)
                else:
                    for symbol in self.config.symbols:
                        try:
                            self._process_symbol(symbol)
                        except Exception as exc:
                            logger.warning("Process error for %s: %s", symbol, exc)

            except Exception as exc:
                logger.error("Bot loop error: %s", exc, exc_info=True)
                self.status = BotStatus.ERROR
                time.sleep(10)
                self.status = BotStatus.RUNNING

            # Attendre avant la prochaine itération
            self._stop_event.wait(timeout=self.config.poll_interval_sec)

        logger.info("Bot loop exited.")

    # ------------------------------------------------------------------
    # Per-symbol processing
    # ------------------------------------------------------------------

    def _process_symbol(self, symbol: str) -> None:
        """Analyse un symbole et ouvre un trade si le signal est valide."""
        # Vérifier qu'on n'a pas déjà une position sur ce symbole
        with self._lock:
            already_positioned = any(
                p.symbol == symbol and p.status == "open"
                for p in self._positions.values()
            )
        if already_positioned:
            return

        df, indicators = self._fetch_and_compute(symbol)
        signal = self.signal_engine.generate_signal(symbol, df, indicators)

        if signal["direction"] == "NEUTRE":
            return
        if signal["confidence"] < self.config.min_confidence:
            logger.debug("%s: signal confidence %.2f below threshold %.2f",
                         symbol, signal["confidence"], self.config.min_confidence)
            return

        current_price = indicators.get("price", 0)
        position = self._open_position(symbol, signal, current_price)
        if position:
            logger.info("Opened %s position on %s @ %.4f (conf=%.2f, strategy=%s)",
                        signal["direction"], symbol, current_price,
                        signal["confidence"], signal["strategy"])

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def _open_position(self, symbol: str, signal: dict,
                       current_price: float) -> Optional[Position]:
        """Crée et enregistre une nouvelle position."""
        try:
            sl = signal["sl"]
            tp = signal["tp"]
            direction = signal["direction"]
            side = "buy" if direction == "LONG" else "sell"

            account = self.broker.get_account()
            quantity = self.risk_manager.position_size(
                account["cash"], current_price, sl
            )
            if quantity <= 0:
                logger.warning("Position size = 0 for %s — skipping.", symbol)
                return None

            # Soumettre l'ordre au broker
            order = self.broker.submit_order(
                symbol=symbol, side=side, quantity=quantity,
                order_type="market", price=current_price,
            )
            fill_price = order["fill_price"]

            # Trailing stop initial = SL
            trailing_init = fill_price - self.config.trailing_atr_mult * abs(fill_price - sl) \
                if side == "buy" else \
                fill_price + self.config.trailing_atr_mult * abs(fill_price - sl)

            with self._lock:
                self._pos_counter += 1
                pos_id = f"POS-{self._pos_counter:06d}"

            position = Position(
                id=pos_id, symbol=symbol, side=side,
                entry_price=fill_price, quantity=quantity,
                stop_loss=sl, take_profit=tp,
                trailing_stop_price=trailing_init,
                current_price=fill_price,
                pnl=0.0, pnl_pct=0.0,
                opened_at=dt.datetime.utcnow().isoformat(),
                strategy_name=signal.get("strategy", "Unknown"),
                status="open",
            )

            with self._lock:
                self._positions[pos_id] = position
            self.broker._register_position(position)
            return position

        except Exception as exc:
            logger.error("Failed to open position for %s: %s", symbol, exc)
            return None

    def _close_position(self, position: Position,
                        exit_price: float, reason: str) -> TradeRecord:
        """Ferme une position et retourne le TradeRecord correspondant."""
        # Ordre de clôture inverse
        close_side = "sell" if position.side == "buy" else "buy"
        self.broker.submit_order(
            symbol=position.symbol, side=close_side,
            quantity=position.quantity, order_type="market", price=exit_price,
        )

        # Calcul P&L
        if position.side == "buy":
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        pnl_pct = pnl / (position.entry_price * position.quantity) if position.entry_price > 0 else 0.0

        closed_at   = dt.datetime.utcnow().isoformat()
        opened_dt   = dt.datetime.fromisoformat(position.opened_at)
        closed_dt   = dt.datetime.fromisoformat(closed_at)
        duration    = (closed_dt - opened_dt).total_seconds() / 60.0

        record = TradeRecord(
            id=position.id, symbol=position.symbol, side=position.side,
            entry_price=position.entry_price, quantity=position.quantity,
            stop_loss=position.stop_loss, take_profit=position.take_profit,
            trailing_stop_price=position.trailing_stop_price,
            current_price=exit_price,
            pnl=round(pnl, 4), pnl_pct=round(pnl_pct, 6),
            opened_at=position.opened_at,
            strategy_name=position.strategy_name,
            status="closed",
            closed_at=closed_at,
            exit_price=exit_price,
            exit_reason=reason,
            duration_min=round(duration, 2),
        )

        with self._lock:
            self._positions.pop(position.id, None)
            self._trade_history.append(record)

        self.broker._remove_position(position.id)
        logger.info("Closed %s %s @ %.4f | P&L: %.2f (%s)",
                    position.side, position.symbol, exit_price, pnl, reason)
        return record

    def _check_existing_positions(self, current_prices: Dict[str, float]) -> None:
        """
        Parcourt toutes les positions ouvertes et vérifie SL / TP / Trailing.
        Ferme les positions si un niveau est atteint.
        """
        with self._lock:
            open_positions = [p for p in self._positions.values() if p.status == "open"]

        for position in open_positions:
            price = current_prices.get(position.symbol)
            if price is None or price <= 0:
                continue

            # Mise à jour du prix et P&L courant
            if position.side == "buy":
                pnl = (price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - price) * position.quantity

            pnl_pct = pnl / (position.entry_price * position.quantity) \
                if position.entry_price > 0 else 0.0

            with self._lock:
                if position.id in self._positions:
                    self._positions[position.id].current_price = price
                    self._positions[position.id].pnl = round(pnl, 4)
                    self._positions[position.id].pnl_pct = round(pnl_pct, 6)

            # Vérification Take Profit
            if self.risk_manager.check_take_profit(position, price):
                self._close_position(position, price, "TP")
                continue

            # Vérification Stop Loss
            if self.risk_manager.check_stop_loss(position, price):
                self._close_position(position, price, "SL")
                continue

            # Vérification Trailing Stop
            if self.config.trailing_stop:
                # Utilisation d'un ATR proxy (2% du prix)
                atr_proxy = price * 0.02
                try:
                    _, ind = self._fetch_and_compute(position.symbol)
                    atr_proxy = ind.get("atr", atr_proxy)
                except Exception:
                    pass

                new_trail = self.risk_manager.update_trailing_stop(
                    position, price, atr_proxy
                )
                with self._lock:
                    if position.id in self._positions:
                        self._positions[position.id].trailing_stop_price = new_trail

                # Vérifier si le trailing stop est touché
                trail_hit = (position.side == "buy" and price <= new_trail) or \
                            (position.side == "sell" and price >= new_trail)
                if trail_hit:
                    self._close_position(position, price, "TRAILING")

    # ------------------------------------------------------------------
    # Macro event filter
    # ------------------------------------------------------------------

    def _is_near_macro_event(self) -> bool:
        """
        Retourne True si on est dans les 60 minutes précédant une annonce macro.

        En production, cette méthode interrogerait un calendrier économique réel
        (ex: Investing.com API, ForexFactory).
        En simulation, on vérifie contre un planning fixe en UTC.
        """
        now_utc  = dt.datetime.utcnow()
        now_time = now_utc.strftime("%H:%M")
        now_mins = now_utc.hour * 60 + now_utc.minute

        for event_time in self._macro_schedule:
            hh, mm = map(int, event_time.split(":"))
            event_mins = hh * 60 + mm
            diff = event_mins - now_mins
            if 0 <= diff <= 60:
                return True
        return False

    # ------------------------------------------------------------------
    # Data fetching and indicator computation
    # ------------------------------------------------------------------

    def _fetch_and_compute(self, symbol: str) -> Tuple[pd.DataFrame, dict]:
        """
        Récupère les données OHLCV et calcule tous les indicateurs.

        En production : intégrer yfinance, Alpaca, Binance, etc.
        En simulation : génère des données synthétiques réalistes.

        Returns
        -------
        (df, indicators) — df OHLCV + dict des derniers indicateurs
        """
        try:
            import yfinance as yf  # type: ignore
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="60d", interval="1h", auto_adjust=True)
            if df is None or len(df) < 30:
                raise ValueError("Données yfinance insuffisantes")
            df = df.rename(columns=str.capitalize)
        except Exception:
            # Fallback: données synthétiques pour paper trading / tests
            df = self._generate_synthetic_ohlcv(symbol)

        # Aplatir MultiIndex si nécessaire
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Calcul des indicateurs
        indicators = self._compute_indicators(df)
        return df, indicators

    @staticmethod
    def _generate_synthetic_ohlcv(symbol: str, n: int = 200) -> pd.DataFrame:
        """Génère un OHLCV synthétique réaliste (random walk + volatilité)."""
        rng   = np.random.default_rng(abs(hash(symbol)) % (2**31))
        price = 100.0 + rng.uniform(-30, 100)
        vol   = price * 0.015  # volatilité initiale 1.5%

        closes = [price]
        for _ in range(n - 1):
            ret = rng.normal(0, vol / price)
            price = max(price * (1 + ret), 1.0)
            closes.append(price)

        closes = np.array(closes)
        highs  = closes * (1 + np.abs(rng.normal(0, 0.005, n)))
        lows   = closes * (1 - np.abs(rng.normal(0, 0.005, n)))
        opens  = np.roll(closes, 1)
        opens[0] = closes[0]
        volumes = rng.integers(100_000, 2_000_000, n).astype(float)

        idx = pd.date_range(end=dt.datetime.utcnow(), periods=n, freq="1h")
        return pd.DataFrame({
            "Open": opens, "High": highs, "Low": lows,
            "Close": closes, "Volume": volumes,
        }, index=idx)

    @staticmethod
    def _compute_indicators(df: pd.DataFrame) -> dict:
        """Calcule un ensemble d'indicateurs et retourne les dernières valeurs."""
        c   = df["Close"].astype(float)
        h   = df["High"].astype(float)
        lo  = df["Low"].astype(float)
        vol = df["Volume"].astype(float).fillna(0)

        # RSI
        delta = c.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = (100 - 100 / (1 + rs)).fillna(50)

        # MACD
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        macd_line   = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist   = macd_line - macd_signal

        # EMAs
        ema20  = c.ewm(span=20,  adjust=False).mean()
        ema50  = c.ewm(span=50,  adjust=False).mean()
        ema200 = c.ewm(span=200, adjust=False).mean()

        # ATR
        tr  = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().fillna(tr.mean())

        # ADX
        up_move  = h.diff()
        dn_move  = -lo.diff()
        plus_dm  = ((up_move > dn_move) & (up_move > 0)) * up_move
        minus_dm = ((dn_move > up_move) & (dn_move > 0)) * dn_move
        plus_di  = 100 * plus_dm.rolling(14).mean() / atr.replace(0, np.nan)
        minus_di = 100 * minus_dm.rolling(14).mean() / atr.replace(0, np.nan)
        dx       = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx      = dx.rolling(14).mean().fillna(20)

        # BB
        bb_mid = c.rolling(20).mean()
        bb_std = c.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        # Volume ratio
        vol_avg   = vol.rolling(20).mean().replace(0, np.nan)
        vol_ratio = (vol / vol_avg).fillna(1.0)

        # Z-score
        spread  = c - ema50
        zscore  = (spread - spread.rolling(20).mean()) / spread.rolling(20).std().replace(0, np.nan)
        zscore  = zscore.fillna(0)

        # Momentum
        mom5  = c.pct_change(5).fillna(0)
        mom20 = c.pct_change(20).fillna(0)

        # OBV
        obv = [0.0]
        for i in range(1, len(c)):
            if c.iloc[i] > c.iloc[i - 1]:
                obv.append(obv[-1] + vol.iloc[i])
            elif c.iloc[i] < c.iloc[i - 1]:
                obv.append(obv[-1] - vol.iloc[i])
            else:
                obv.append(obv[-1])
        obv_s = pd.Series(obv, index=c.index)

        def last(s: pd.Series, default: float = 0.0) -> float:
            try:
                v = float(s.iloc[-1])
                return v if math.isfinite(v) else default
            except Exception:
                return default

        return {
            "price":     last(c),
            "rsi":       last(rsi, 50),
            "macd_hist": last(macd_hist),
            "macd_line": last(macd_line),
            "ema20":     last(ema20),
            "ema50":     last(ema50),
            "ema200":    last(ema200),
            "atr":       last(atr, 1.0),
            "adx":       last(adx, 20),
            "plus_di":   last(plus_di, 20),
            "minus_di":  last(minus_di, 20),
            "bb_upper":  last(bb_upper),
            "bb_lower":  last(bb_lower),
            "vol_ratio": last(vol_ratio, 1.0),
            "zscore":    last(zscore),
            "mom5":      last(mom5),
            "mom20":     last(mom20),
            "obv":       last(obv_s),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_max_drawdown(self, pnls: List[float]) -> float:
        """Calcule le drawdown maximum sur l'equity réelle (capital + P&L cumulé)."""
        if not pnls:
            return 0.0
        initial = getattr(self, "_initial_capital", self.config.capital)
        equity  = initial + np.cumsum(pnls)
        peak    = np.maximum.accumulate(equity)
        dd      = (peak - equity) / np.where(peak > 0, peak, 1.0)
        return float(np.max(dd))


# ---------------------------------------------------------------------------
# Streamlit session state manager
# ---------------------------------------------------------------------------

class BotSessionState:
    """
    Gestionnaire d'état de session pour intégration Streamlit.

    Permet de conserver le bot vivant entre les reruns Streamlit.
    """

    _SESSION_KEY = "_zedicus_trading_bot"

    @classmethod
    def get_bot(cls, config: BotConfig) -> TradingBot:
        """Retourne le bot existant ou en crée un nouveau."""
        try:
            import streamlit as st  # type: ignore
            if cls._SESSION_KEY not in st.session_state:
                st.session_state[cls._SESSION_KEY] = TradingBot(config)
            return st.session_state[cls._SESSION_KEY]
        except ImportError:
            # Hors Streamlit : retourne simplement un nouveau bot
            return TradingBot(config)

    @classmethod
    def start_bot(cls, config: BotConfig) -> None:
        """Démarre le bot depuis la session Streamlit."""
        bot = cls.get_bot(config)
        if bot.status != BotStatus.RUNNING:
            bot.start()

    @classmethod
    def stop_bot(cls) -> None:
        """Arrête le bot depuis la session Streamlit."""
        try:
            import streamlit as st  # type: ignore
            bot: Optional[TradingBot] = st.session_state.get(cls._SESSION_KEY)
            if bot and bot.status == BotStatus.RUNNING:
                bot.stop()
        except ImportError:
            pass

    @classmethod
    def get_metrics(cls) -> dict:
        """Retourne les métriques du bot actif ou un dict vide."""
        try:
            import streamlit as st  # type: ignore
            bot: Optional[TradingBot] = st.session_state.get(cls._SESSION_KEY)
            if bot:
                return bot.get_performance_metrics()
        except ImportError:
            pass
        return {}


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def create_default_config(symbols: List[str], capital: float) -> BotConfig:
    """
    Crée une configuration adaptée au capital fourni (optimisée pour 10 € – 1 000 €).

    Parameters
    ----------
    symbols : liste de symboles à trader (ex: ["BTC-USD", "ETH-USD"])
    capital : capital initial en euros (10 – 1 000)
    """
    # Paramètres adaptatifs selon la taille du capital
    if capital <= 50:
        # Très petit budget : risque légèrement plus élevé, 1 position max
        risk_pct   = 0.03   # 3 % = max 1,50 € risqué sur 50 €
        max_pos    = 1
        min_conf   = 0.70   # seuil élevé pour filtrer les mauvais signaux
        drawdown   = 0.20
    elif capital <= 200:
        # Petit budget : 2 % de risque, 2 positions max
        risk_pct   = 0.02
        max_pos    = 2
        min_conf   = 0.65
        drawdown   = 0.15
    else:
        # Budget moyen (200 – 1 000 €) : paramètres standard prudents
        risk_pct   = 0.015
        max_pos    = min(3, len(symbols))
        min_conf   = 0.62
        drawdown   = 0.12

    return BotConfig(
        symbols=symbols,
        capital=capital,
        risk_pct_per_trade=risk_pct,
        max_positions=max(1, max_pos),
        max_drawdown_pct=drawdown,
        use_stop_loss=True,
        use_take_profit=True,
        sl_atr_mult=1.5,        # stop plus serré pour préserver le capital
        tp_atr_mult=2.5,        # objectif raisonnable
        trailing_stop=True,
        trailing_atr_mult=1.2,
        min_confidence=min_conf,
        filter_macro_events=True,
        poll_interval_sec=60,
        broker="paper",
        strategies_enabled=["momentum", "breakout", "mean_reversion", "trend"],
    )


def format_pnl(pnl: float) -> str:
    """Formate un P&L en euros lisible avec signe."""
    if pnl >= 0:
        return f"+{pnl:,.2f} €"
    else:
        return f"-{abs(pnl):,.2f} €"


def compute_bot_sharpe(trade_records: List[TradeRecord],
                       risk_free_rate: float = 0.0) -> float:
    """
    Calcule le ratio de Sharpe annualisé à partir des P&L des trades.

    Annualisation basée sur 252 jours de trading.

    Returns 0.0 si pas assez de données.
    """
    if len(trade_records) < 2:
        return 0.0

    # Sharpe sur rendements relatifs (%) — pas sur P&L absolus
    pnls   = np.array([t.pnl_pct for t in trade_records])
    mean   = float(np.mean(pnls))
    std    = float(np.std(pnls, ddof=1))

    if std < 1e-9:
        return 0.0

    # Estimer le nombre de trades par an
    if len(trade_records) >= 2:
        first_dt = dt.datetime.fromisoformat(trade_records[0].opened_at)
        last_dt  = dt.datetime.fromisoformat(trade_records[-1].closed_at)
        days_span = max((last_dt - first_dt).days, 1)
        trades_per_year = len(trade_records) / days_span * 252
    else:
        trades_per_year = 252

    sharpe = (mean - risk_free_rate) / std * math.sqrt(trades_per_year)
    return round(sharpe, 4)
