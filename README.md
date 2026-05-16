# ⚡ THE ZEDICUS v3 — Dashboard de Trading Algorithmique

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/cloud)
[![Python 3.9](https://img.shields.io/badge/python-3.9.18-blue.svg)](https://www.python.org/downloads/release/python-3918/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

> **Usage éducatif uniquement. Le trading comporte un risque de perte en capital.**

---

## Description

THE ZEDICUS v3 est un dashboard de trading algorithmique complet, conçu pour les petits budgets (10 € – 1 000 €). Il propose une analyse technique multi-source en temps réel, un bot de trading simulé (paper trading), un screener d'actifs, un backtester de stratégies et bien plus encore — le tout dans une interface futuriste néon.

---

## Fonctionnalités — 15 onglets

| Onglet | Fonctionnalité |
|--------|---------------|
| 🏠 Accueil | Prix live, santé du marché, graphique principal |
| 🌍 Marché | Vue mondiale : crypto, forex, actions, macro FRED |
| 📊 Analyse | 6 sous-onglets : chandeliers, RSI/MACD, volume, multi-TF, patterns, corrélations |
| 🔍 Screener | Scan parallèle multi-actifs avec filtres RSI + score |
| 📡 Signaux | Score composite 6 conditions + niveaux SL/TP |
| 🤖 Bot | Bot algorithmique configurable (paper trading) |
| 💼 Portefeuille | Positions ouvertes, PnL, répartition |
| ⚠️ Risque | Calculateur de position automatique (ATR) |
| 📈 Performance | Rendements, Sharpe, drawdown, distribution |
| 🔬 Backtest | Test de stratégies sur données historiques |
| 📅 Calendrier | Événements macro 2026 (FOMC, BCE, CPI, NFP) |
| 🎯 Stratégies | Bibliothèque + création de stratégies personnalisées |
| 🔔 Alertes | Alertes prix/RSI configurables |
| ⚗️ StratZed | Composer de stratégies + backtester dédié |
| ❓ Aide | Guide, glossaire, sources, avertissement légal |

---

## APIs gratuites (sans clé)

| API | Usage |
|-----|-------|
| **Binance** (api.binance.com) | Crypto OHLCV + ticker live |
| **CoinGecko** (api.coingecko.com) | Prix batch, market cap, trending |
| **Frankfurter** (api.frankfurter.app) | Taux de change BCE officiels |
| **FRED** (fred.stlouisfed.org) | Macro US (CPI, Fed, chômage) |
| **Yahoo Finance** (via yfinance) | Actions, ETF, indices, commodités |

---

## Installation rapide (local)

```bash
git clone https://github.com/thezedicus/ZEDICUS_FINAL.git
cd ZEDICUS_FINAL
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur http://localhost:8501

---

## Structure du projet

```
ZEDICUS_FINAL/
├── app.py                    ← point d'entrée Streamlit Cloud
├── ZedicusVersionParfaite.py ← application principale (UI + onglets)
├── core/                     ← modules métier (imports from core.*)
│   ├── __init__.py
│   ├── config.py
│   ├── data_providers.py
│   ├── trading_bot.py
│   ├── signal_generator.py
│   ├── portfolio_manager.py
│   ├── risk_manager.py
│   ├── screener.py
│   ├── backtester.py
│   ├── alert_manager.py
│   ├── strategy_manager.py
│   └── firebase_manager.py
├── .streamlit/
│   ├── config.toml           ← thème néon
│   └── secrets.toml          ← secrets (gitignored)
├── requirements.txt
├── runtime.txt               ← python-3.9.18
├── .gitignore
└── LICENSE
```

---

## Déploiement sur Streamlit Cloud

1. Pousser le code sur GitHub : `https://github.com/thezedicus/ZEDICUS_FINAL`
2. Aller sur [share.streamlit.io](https://share.streamlit.io)
3. Connecter le dépôt **ZEDICUS_FINAL**
4. Paramètres :
   - **Main file path** : `app.py`
   - **Python version** : `3.9`
5. Déployer

`firebase-admin` est optionnel : sans credentials, `firebase_manager` dégrade gracieusement.

---

## Avertissement légal

> **THE ZEDICUS v3 est un outil éducatif uniquement.** Il ne constitue pas un conseil en investissement.
> Les signaux sont informatifs et ne garantissent aucun résultat financier.
> **Le trading comporte un risque de perte totale du capital investi.**

---

## Licence

MIT — voir [LICENSE](./LICENSE)
