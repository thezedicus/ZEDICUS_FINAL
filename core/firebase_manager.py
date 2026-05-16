"""firebase_manager.py — Firebase / Firestore integration with graceful degradation.

All functions are designed to never raise exceptions to callers.  If Firebase is
unavailable or misconfigured the module degrades silently and every public
function returns a safe default value.

Datetime usage: always ``dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)``
to produce a naive UTC datetime — never ``datetime.utcnow()`` (deprecated).
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Optional

import streamlit as st

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level Firebase state
# ---------------------------------------------------------------------------
_firebase_app: Optional[Any] = None
_firestore_db: Optional[Any] = None
_firebase_enabled: bool = False


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_firebase(secrets: Optional[dict] = None) -> bool:
    """Initialise Firebase / Firestore.

    Parameters
    ----------
    secrets:
        Optional dictionary containing Firebase credentials.  When *None* the
        function falls back to ``st.secrets.get("firebase", {})``.

    Returns
    -------
    bool
        True when Firebase was initialised successfully, False otherwise.
    """
    global _firebase_app, _firestore_db, _firebase_enabled

    # Already initialised — return current state.
    if _firebase_enabled and _firestore_db is not None:
        return True

    try:
        import firebase_admin  # type: ignore[import]
        from firebase_admin import credentials, firestore  # type: ignore[import]

        if secrets is None:
            try:
                secrets = dict(st.secrets.get("firebase", {}))
            except Exception:
                secrets = {}

        if not secrets:
            log.info("firebase_manager: no Firebase credentials found — running in offline mode.")
            return False

        # Convert AttrDict / Streamlit secrets mapping to plain dict.
        cred_dict: dict = {k: v for k, v in secrets.items()}

        # Avoid re-initialising if another module already did it.
        try:
            _firebase_app = firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(cred_dict)
            _firebase_app = firebase_admin.initialize_app(cred)

        _firestore_db = firestore.client()
        _firebase_enabled = True
        log.info("firebase_manager: Firestore connected successfully.")
        return True

    except ImportError:
        log.warning(
            "firebase_manager: 'firebase-admin' package not installed — "
            "running in offline mode."
        )
    except Exception as exc:  # noqa: BLE001
        log.error("firebase_manager: initialisation failed — %s", exc)

    _firebase_enabled = False
    return False


def is_firebase_enabled() -> bool:
    """Return True when Firebase is currently active and available."""
    return _firebase_enabled and _firestore_db is not None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_utc() -> dt.datetime:
    """Return a naive UTC datetime (tzinfo stripped for Firestore compatibility)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _col(name: str):  # type: ignore[return]
    """Return a Firestore collection reference, or None when offline."""
    if not is_firebase_enabled():
        return None
    try:
        return _firestore_db.collection(name)  # type: ignore[union-attr]
    except Exception as exc:
        log.debug("firebase_manager._col(%r) failed: %s", name, exc)
        return None


# ---------------------------------------------------------------------------
# Generic event logging
# ---------------------------------------------------------------------------

def log_event(session_id: str, event_type: str, data: dict) -> None:
    """Append an analytics event document to the ``events`` collection.

    Parameters
    ----------
    session_id:
        Unique identifier for the current user session.
    event_type:
        Short label describing the event (e.g. ``"symbol_search"``).
    data:
        Arbitrary metadata to store alongside the event.
    """
    col = _col("events")
    if col is None:
        return
    try:
        doc: dict[str, Any] = {
            "session_id": str(session_id),
            "event_type": str(event_type),
            "timestamp":  _now_utc(),
            **{k: v for k, v in data.items()},
        }
        col.add(doc)
    except Exception as exc:  # noqa: BLE001
        log.debug("firebase_manager.log_event failed: %s", exc)


def log_symbol_search(session_id: str, symbol: str) -> None:
    """Log a ticker-symbol lookup event.

    Parameters
    ----------
    session_id:
        Current user session identifier.
    symbol:
        The ticker symbol that was searched.
    """
    log_event(session_id, "symbol_search", {"symbol": str(symbol).upper()})


def log_tab_view(session_id: str, tab_name: str) -> None:
    """Log a dashboard tab navigation event.

    Parameters
    ----------
    session_id:
        Current user session identifier.
    tab_name:
        Human-readable name of the tab that was opened.
    """
    log_event(session_id, "tab_view", {"tab": str(tab_name)})


def log_strategy_run(
    session_id: str,
    strategy_name: str,
    direction: str,
    confidence: float,
) -> None:
    """Log the execution of a trading strategy analysis.

    Parameters
    ----------
    session_id:
        Current user session identifier.
    strategy_name:
        Name of the strategy that was executed.
    direction:
        Signal direction, e.g. ``"LONG"``, ``"SHORT"``, or ``"NEUTRE"``.
    confidence:
        Confidence score in the range [0, 1].
    """
    log_event(
        session_id,
        "strategy_run",
        {
            "strategy":   str(strategy_name),
            "direction":  str(direction),
            "confidence": float(confidence),
        },
    )


# ---------------------------------------------------------------------------
# Rate limiting via Firestore
# ---------------------------------------------------------------------------

def check_rate_limit_firebase(
    session_id: str,
    window_seconds: int = 60,
    max_calls: int = 30,
) -> bool:
    """Server-side rate-limit check using a Firestore counter document.

    This is a secondary defence layer — the primary limiter is
    :class:`rate_limiter.SessionRateLimiter` running client-side.

    Parameters
    ----------
    session_id:
        The session whose quota is being checked.
    window_seconds:
        Duration of the rate-limit window in seconds.
    max_calls:
        Maximum calls allowed within the window.

    Returns
    -------
    bool
        True when the call is permitted, False when the limit is exceeded.
        Always returns True when Firebase is offline (fail-open design).
    """
    if not is_firebase_enabled():
        return True

    try:
        now = _now_utc()
        cutoff = now - dt.timedelta(seconds=window_seconds)

        col = _col("rate_limits")
        if col is None:
            return True

        # Count recent calls for this session.
        docs = (
            col.where("session_id", "==", str(session_id))
               .where("timestamp", ">=", cutoff)
               .stream()
        )
        call_count = sum(1 for _ in docs)

        if call_count >= max_calls:
            log.debug(
                "firebase_manager.check_rate_limit_firebase: session %s exceeded limit (%d/%d).",
                session_id, call_count, max_calls,
            )
            return False

        # Record this call.
        col.add({"session_id": str(session_id), "timestamp": now})
        return True

    except Exception as exc:  # noqa: BLE001
        log.debug("firebase_manager.check_rate_limit_firebase failed: %s", exc)
        return True          # fail-open


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def firebase_health_check() -> bool:
    """Perform a lightweight read to verify the Firestore connection is alive.

    Returns
    -------
    bool
        True when the connection is healthy, False otherwise.
    """
    if not is_firebase_enabled():
        return False

    try:
        # Attempt to list a single document from the health-check collection.
        col = _col("_health")
        if col is None:
            return False
        list(col.limit(1).stream())
        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("firebase_manager.firebase_health_check failed: %s", exc)
        return False


class FirebaseManager:
    """Classe wrapper pour une utilisation orientée objet du firebase_manager."""

    def log_strategy_run(self, symbol: str, strategy: str, params: dict) -> None:
        try:
            log_strategy_run(
                session_id="dashboard",
                strategy_name=strategy,
                direction=symbol,
                confidence=0.0,
            )
        except Exception:
            pass

    def health_check(self) -> bool:
        return firebase_health_check()
