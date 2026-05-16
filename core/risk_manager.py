"""risk_manager.py — Gestionnaire du risque."""


class RiskManager:
    def get_risk_report(self, capital: float = 100.0) -> dict:
        return {
            "capital": capital,
            "max_position": capital * 0.40,
            "max_risk_per_trade": capital * 0.02,
            "max_drawdown_limit": capital * 0.20,
        }

    def check_position_allowed(self, capital: float, amount: float) -> bool:
        return amount <= capital * 0.40 and amount >= 0.01
