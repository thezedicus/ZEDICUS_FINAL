"""alert_manager.py — Gestionnaire d'alertes."""
import json
import os

_STORE = os.path.join(os.path.dirname(__file__), ".alerts.json")


def _load() -> list:
    try:
        with open(_STORE) as f:
            return json.load(f)
    except Exception:
        return []


def _save(alerts: list) -> None:
    try:
        with open(_STORE, "w") as f:
            json.dump(alerts, f)
    except Exception:
        pass


class AlertManager:
    def get_active_alerts(self) -> list:
        return _load()

    def add_alert(self, alert: dict) -> None:
        alerts = _load()
        alerts.append(alert)
        _save(alerts)

    def clear_alerts(self) -> None:
        _save([])

    def remove_alert(self, index: int) -> None:
        alerts = _load()
        if 0 <= index < len(alerts):
            alerts.pop(index)
        _save(alerts)
