"""strategy_manager.py — Gestionnaire de stratégies personnalisées."""
import json
import os

_STORE = os.path.join(os.path.dirname(__file__), ".strategies.json")


def _load() -> list:
    try:
        with open(_STORE) as f:
            return json.load(f)
    except Exception:
        return []


def _save(strategies: list) -> None:
    try:
        with open(_STORE, "w") as f:
            json.dump(strategies, f)
    except Exception:
        pass


class StrategyManager:
    def list_strategies(self) -> list:
        return _load()

    def save_strategy(self, strategy: dict) -> None:
        strategies = _load()
        strategies.append(strategy)
        _save(strategies)

    def delete_strategy(self, name: str) -> None:
        strategies = [s for s in _load() if s.get("name") != name]
        _save(strategies)
