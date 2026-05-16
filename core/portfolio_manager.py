"""portfolio_manager.py — Gestionnaire de portefeuille."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class PortfolioPosition:
    symbol: str = ""
    quantity: float = 0.0
    avg_price: float = 0.0
    value: float = 0.0
    unrealized_pnl: float = 0.0
    weight: float = 0.0


@dataclass
class Portfolio:
    positions: List[PortfolioPosition] = field(default_factory=list)
    total_value: float = 0.0
    total_pnl: float = 0.0


class PortfolioManager:
    def __init__(self):
        self._portfolio = Portfolio()

    def get_portfolio(self) -> Portfolio:
        return self._portfolio

    def add_position(self, symbol: str, quantity: float, price: float) -> None:
        pos = PortfolioPosition(symbol=symbol, quantity=quantity,
                                avg_price=price, value=quantity * price)
        self._portfolio.positions.append(pos)
