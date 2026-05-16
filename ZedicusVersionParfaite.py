"""
ZedicusVersionParfaite.py — THE ZEDICUS v3 · Dashboard de Trading Algorithmique
Design : Futuriste · Dali x Dragon Ball Z · Néons · Or · Argent · Gemmes
Capital : 10 € – 1 000 €
APIs : Binance · CoinGecko · Frankfurter (BCE) · FRED · Yahoo Finance
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed as _asc

from core.config import (
    ASSET_CATEGORIES, PERIODS_UI, INTERVALS_UI,
    COLOR_BULLISH, COLOR_BEARISH, COLOR_NEUTRAL,
    COLOR_BG, COLOR_CARD, COLOR_TEXT, COLOR_ACCENT,
)
from core.trading_bot import TradingBot, BotConfig, BotStatus, create_default_config
from core.signal_generator import SignalGenerator
from core.portfolio_manager import PortfolioManager
from core.risk_manager import RiskManager
from core.screener import Screener
from core.backtester import Backtester
from core.alert_manager import AlertManager
from core.strategy_manager import StrategyManager
from core.firebase_manager import FirebaseManager
from core.data_providers import (
    smart_ohlcv, smart_price, parallel_prices,
    coingecko_global, coingecko_trending, coingecko_prices,
    binance_ticker, frankfurter_rates, fred_series, fred_latest,
    format_large,
)

# ══════════════════════════════════════════════════════════════════════════════
# PALETTE NÉON / FUTURISTE
# ══════════════════════════════════════════════════════════════════════════════
C_BG      = "#030712"
C_BG2     = "#060f20"
C_CARD    = "#0a1628"
C_BORDER  = "#0f2a4a"
C_CYAN    = "#00D4FF"
C_GREEN   = "#00FF88"
C_RED     = "#FF3366"
C_GOLD    = "#FFD700"
C_SILVER  = "#C0C0C0"
C_PURPLE  = "#9B59B6"
C_ORANGE  = "#FF6B35"
C_WHITE   = "#FFFFFF"
C_MUTED   = "#6b8db5"  # ratio ~4.6:1 sur C_BG — WCAG AA
C_TEXT    = "#CBD5E1"

# Config Plotly partagée — désactive scrollZoom (conflit scroll/zoom mobile)
PLOTLY_CFG = {
    "responsive": True,
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": "reset",
}

# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL — DESIGN ÉPIQUE
# ══════════════════════════════════════════════════════════════════════════════

# Font preload séparé (non-bloquant) — injecté avant le CSS principal
FONT_PRELOAD = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
<meta name="theme-color" content="#030712">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="ZEDICUS v3">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<style>
  /* Injecté tôt pour éviter le FOUC (Flash of Unstyled Content) */
  html { background: #030712 !important; color-scheme: dark; }
</style>
"""

GLOBAL_CSS = f"""
<style>

/* ═══════════════════════ RESET & BOX MODEL ═══════════════════════ */
*, *::before, *::after {{
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}}

/* ═══════════════════════ FOND & COULEURS ═══════════════════════ */
html, body {{
    background-color: {C_BG} !important;
    color: {C_TEXT};
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    min-height: 100vh;
    min-height: 100dvh;                /* iOS 15.4+ hauteur dynamique */
    -webkit-text-size-adjust: 100%;    /* Empêche ajustement auto iOS paysage */
    text-size-adjust: 100%;
    scrollbar-gutter: stable;          /* Évite layout shift Windows Chrome */
    overscroll-behavior-y: none;       /* Bloque pull-to-refresh Android */
    color-scheme: dark;
}}
[data-testid="stAppViewContainer"], .main {{
    background-color: {C_BG} !important;
}}
[data-testid="stHeader"] {{
    background: {C_BG} !important;
    border-bottom: 1px solid {C_BORDER};
    -webkit-backdrop-filter: blur(10px);
    backdrop-filter: blur(10px);
}}
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #020b18 0%, #040f1e 40%, #030c1a 100%) !important;
    border-right: 1px solid {C_CYAN}18;
    box-shadow: 4px 0 20px rgba(0,0,0,0.5);
}}
section[data-testid="stSidebarContent"] {{ padding-top: 1rem; }}

/* ═══════════════════════ CONTENEUR PRINCIPAL ═══════════════════════ */
/* Streamlit 1.50 layout="wide" — plein écran, header dégagé */
.main .block-container,
[data-testid="stMainBlockContainer"],
section.main > div.block-container {{
    width: 100% !important;
    max-width: 100% !important;
    padding: 1rem 1.75rem calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
    margin: 0 auto !important;
    box-sizing: border-box !important;
}}
/* Streamlit 1.50 — stMain scroll libre (ne pas mettre overflow:hidden ici) */
[data-testid="stMain"] {{
    overflow-x: hidden !important;
    overflow-y: auto !important;
    padding-top: 0 !important;
    scroll-behavior: auto;
}}
/* Header Streamlit — toujours au-dessus */
[data-testid="stHeader"] {{
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
    height: auto !important;
}}
/* Supprime le padding inutile de l'AppView */
[data-testid="stAppViewContainer"] {{
    padding-top: 0 !important;
}}

/* ═══════════════════════ ANIMATIONS ═══════════════════════ */
@keyframes glow-pulse {{
  0%,100% {{ box-shadow: 0 0 12px {C_CYAN}33, 0 0 24px {C_CYAN}11; }}
  50%     {{ box-shadow: 0 0 22px {C_CYAN}66, 0 0 44px {C_CYAN}33, 0 0 70px {C_CYAN}11; }}
}}
@keyframes gold-pulse {{
  0%,100% {{ box-shadow: 0 0 12px {C_GOLD}44; }}
  50%     {{ box-shadow: 0 0 28px {C_GOLD}88, 0 0 50px {C_GOLD}33; }}
}}
@keyframes float {{
  0%,100% {{ transform: translateY(0px) rotate(0deg); }}
  33%     {{ transform: translateY(-8px) rotate(1deg); }}
  66%     {{ transform: translateY(-4px) rotate(-1deg); }}
}}
@keyframes shimmer {{
  0%   {{ background-position: -200% center; }}
  100% {{ background-position: 200% center; }}
}}
@keyframes energy-ring {{
  0%   {{ transform: scale(0.96); opacity:0.6; }}
  50%  {{ transform: scale(1.04); opacity:1; }}
  100% {{ transform: scale(0.96); opacity:0.6; }}
}}
@keyframes slide-in {{
  from {{ opacity:0; transform: translateX(-16px); }}
  to   {{ opacity:1; transform: translateX(0); }}
}}
@keyframes fade-up {{
  from {{ opacity:0; transform: translateY(10px); }}
  to   {{ opacity:1; transform: translateY(0); }}
}}
@keyframes neon-flicker {{
  0%,19%,21%,23%,25%,54%,56%,100% {{ opacity:1; }}
  20%,24%,55% {{ opacity:0.45; }}
}}
@keyframes scan-line {{
  0%   {{ transform: translateY(-100%); }}
  100% {{ transform: translateY(100vh); }}
}}
/* Classe CSS pour energy-ring — permet à prefers-reduced-motion d'agir */
.zed-ring {{
  animation: energy-ring 2.5s infinite;
}}
@media (prefers-reduced-motion: reduce) {{
  .zed-ring {{ animation: none !important; }}
}}

/* ═══════════════════════ ONGLETS PRINCIPAUX ═══════════════════════ */
.stTabs [data-baseweb="tab-list"] {{
    background: linear-gradient(90deg, {C_BG2} 0%, {C_BG} 100%);
    border-radius: 14px;
    padding: 5px 6px;
    gap: 2px;
    border: 1px solid {C_CYAN}1a;
    box-shadow: 0 0 25px {C_CYAN}0d, inset 0 1px 0 rgba(255,255,255,0.03);
    flex-wrap: wrap;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 9px;
    color: {C_MUTED};
    font-weight: 600;
    font-size: 0.80rem;
    padding: 6px 12px;
    transition: all 0.2s ease;
    white-space: nowrap;
    letter-spacing: 0.02em;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: {C_TEXT} !important;
    background: {C_CYAN}0d !important;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {C_CYAN}20, {C_CYAN}0d) !important;
    color: {C_CYAN} !important;
    font-weight: 800;
    border: 1px solid {C_CYAN}40 !important;
    box-shadow: 0 0 14px {C_CYAN}2a, inset 0 1px 0 {C_CYAN}22;
}}
/* Sous-onglets (nested tabs) */
.stTabs .stTabs [data-baseweb="tab-list"] {{
    background: {C_BG2};
    border-radius: 10px;
    border-color: {C_GOLD}18;
    margin-top: 4px;
}}
.stTabs .stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, {C_GOLD}18, {C_GOLD}0a) !important;
    color: {C_GOLD} !important;
    border-color: {C_GOLD}38 !important;
    box-shadow: 0 0 10px {C_GOLD}22;
}}

/* Navigation principale (segmented_control) — même look que .stTabs */
section[data-testid="stMain"] [data-testid="stSegmentedControl"] {{
    width: 100%;
}}
section[data-testid="stMain"] [data-testid="stSegmentedControl"] > div {{
    background: linear-gradient(90deg, {C_BG2} 0%, {C_BG} 100%) !important;
    border-radius: 14px !important;
    padding: 5px 6px !important;
    gap: 2px !important;
    border: 1px solid {C_CYAN}1a !important;
    box-shadow: 0 0 25px {C_CYAN}0d, inset 0 1px 0 rgba(255,255,255,0.03) !important;
    flex-wrap: wrap !important;
}}
section[data-testid="stMain"] [data-testid="stSegmentedControl"] button {{
    border-radius: 9px !important;
    color: {C_MUTED} !important;
    font-weight: 600 !important;
    font-size: 0.80rem !important;
    padding: 6px 12px !important;
    white-space: nowrap !important;
    letter-spacing: 0.02em !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    min-height: 44px !important;
}}
section[data-testid="stMain"] [data-testid="stSegmentedControl"] button:hover {{
    color: {C_TEXT} !important;
    background: {C_CYAN}0d !important;
}}
section[data-testid="stMain"] [data-testid="stSegmentedControl"] button[aria-checked="true"],
section[data-testid="stMain"] [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
    background: linear-gradient(135deg, {C_CYAN}20, {C_CYAN}0d) !important;
    color: {C_CYAN} !important;
    font-weight: 800 !important;
    border: 1px solid {C_CYAN}40 !important;
    box-shadow: 0 0 14px {C_CYAN}2a, inset 0 1px 0 {C_CYAN}22 !important;
}}

/* ═══════════════════════ BOUTONS ═══════════════════════ */
.stButton > button {{
    border-radius: 10px;
    font-weight: 700;
    font-size: 0.87rem;
    border: 1px solid {C_CYAN}40;
    background: linear-gradient(135deg, {C_CYAN}12, {C_BG2});
    color: {C_CYAN};
    transition: all 0.22s ease;
    letter-spacing: 0.03em;
    position: relative;
    overflow: hidden;
}}
.stButton > button::before {{
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, {C_CYAN}15, transparent);
    transition: left 0.4s;
}}
.stButton > button:active {{ transform: scale(0.97); }}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {C_CYAN}55, {C_CYAN}22) !important;
    color: {C_WHITE} !important;
    border-color: {C_CYAN}99 !important;
    font-size: 0.91rem;
    box-shadow: 0 0 16px {C_CYAN}33;
}}
/* Hover uniquement sur appareils avec pointeur précis (souris) — pas sur touch */
@media (hover: hover) and (pointer: fine) {{
    .stButton > button:hover::before {{ left: 100%; }}
    .stButton > button:hover {{
        border-color: {C_CYAN}77;
        background: linear-gradient(135deg, {C_CYAN}28, {C_CYAN}0d);
        box-shadow: 0 0 18px {C_CYAN}3a, 0 2px 8px rgba(0,0,0,0.4);
        transform: translateY(-1px);
        color: {C_WHITE};
    }}
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, {C_CYAN}77, {C_CYAN}44) !important;
        box-shadow: 0 0 26px {C_CYAN}55 !important;
    }}
}}

/* ═══════════════════════ INPUTS & SLIDERS ═══════════════════════ */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    background: {C_BG2} !important;
    border: 1px solid {C_CYAN}28 !important;
    border-radius: 9px !important;
    color: {C_WHITE} !important;
    font-size: 0.88rem !important;
    transition: border-color 0.2s;
}}
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border-color: {C_CYAN}88 !important;
    box-shadow: 0 0 10px {C_CYAN}22 !important;
    outline: none !important;
}}
[data-testid="stSelectbox"] > div > div {{
    background: {C_BG2} !important;
    border: 1px solid {C_CYAN}28 !important;
    border-radius: 9px !important;
    color: {C_TEXT} !important;
    transition: border-color 0.2s;
}}
[data-testid="stSelectbox"] > div > div:hover {{
    border-color: {C_CYAN}66 !important;
}}
[data-testid="stMultiSelect"] > div > div {{
    background: {C_BG2} !important;
    border: 1px solid {C_CYAN}28 !important;
    border-radius: 9px !important;
}}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background: {C_CYAN}22 !important;
    color: {C_CYAN} !important;
    border: 1px solid {C_CYAN}44 !important;
    border-radius: 20px !important;
}}
.stSlider > label {{ color: {C_TEXT} !important; font-size: 0.82rem; }}
.stSlider [data-baseweb="slider"] {{ margin-top: 4px; }}
.stSlider [data-baseweb="thumb"] {{
    background: {C_CYAN} !important;
    border: 2px solid {C_BG} !important;
    box-shadow: 0 0 10px {C_CYAN}99 !important;
    width: 16px !important;
    height: 16px !important;
}}
.stSlider [data-baseweb="track-fill"] {{
    background: linear-gradient(90deg, {C_CYAN}, {C_GREEN}) !important;
}}
.stSlider [data-baseweb="track"] {{
    background: {C_BORDER} !important;
}}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label {{
    color: {C_TEXT} !important;
    font-size: 0.88rem;
}}
[data-testid="stCheckbox"] [data-testid="stCheckboxWidget"] {{
    accent-color: {C_CYAN};
}}

/* ═══════════════════════ DATAFRAME ═══════════════════════ */
[data-testid="stDataFrame"] {{
    border-radius: 12px;
    overflow-x: auto !important;
    width: 100% !important;
    max-width: 100% !important;
    border: 1px solid {C_CYAN}18;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    animation: fade-up 0.3s ease;
}}
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {{
    background: {C_BG2} !important;
}}
/* Table header */
[data-testid="stDataFrame"] th {{
    background: linear-gradient(135deg, {C_CARD}, {C_BG2}) !important;
    color: {C_CYAN} !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid {C_CYAN}22 !important;
    padding: 10px 14px !important;
}}
/* Table rows */
[data-testid="stDataFrame"] td {{
    background: {C_BG2} !important;
    color: {C_TEXT} !important;
    font-size: 0.84rem !important;
    border-bottom: 1px solid {C_BORDER}88 !important;
    padding: 8px 14px !important;
    transition: background 0.15s;
}}
@media (hover: hover) and (pointer: fine) {{
    [data-testid="stDataFrame"] tr:hover td {{
        background: {C_CYAN}08 !important;
    }}
}}

/* ═══════════════════════ MÉTRIQUES STREAMLIT ═══════════════════════ */
div[data-testid="stMetric"] {{
    background: linear-gradient(135deg, {C_CARD}ee, {C_BG2});
    border-radius: 13px;
    border: 1px solid {C_CYAN}1e;
    padding: 14px 18px;
    transition: transform 0.2s, box-shadow 0.2s;
    animation: fade-up 0.3s ease;
}}
@media (hover: hover) and (pointer: fine) {{
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 20px {C_CYAN}15;
        border-color: {C_CYAN}38;
    }}
}}
div[data-testid="stMetric"] label {{
    color: {C_MUTED} !important;
    font-size: 0.74rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-size: 1.45rem !important;
    font-weight: 800 !important;
    color: {C_WHITE} !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}}

/* ═══════════════════════ PROGRESS BAR ═══════════════════════ */
.stProgress > div > div > div {{
    background: linear-gradient(90deg, {C_CYAN}, {C_GREEN}) !important;
    border-radius: 4px;
    box-shadow: 0 0 8px {C_CYAN}44;
}}
.stProgress > div > div {{
    background: {C_BORDER} !important;
    border-radius: 4px;
}}

/* ═══════════════════════ EXPANDER ═══════════════════════ */
[data-testid="stExpander"] {{
    background: {C_BG2} !important;
    border: 1px solid {C_CYAN}1a !important;
    border-radius: 12px !important;
    overflow: hidden;
    transition: border-color 0.2s;
}}
[data-testid="stExpander"]:hover {{
    border-color: {C_CYAN}38 !important;
}}
[data-testid="stExpander"] summary {{
    font-weight: 700;
    font-size: 0.88rem;
    color: {C_CYAN};
    padding: 10px 14px;
    cursor: pointer;
    letter-spacing: 0.03em;
}}
[data-testid="stExpander"] summary:hover {{
    color: {C_WHITE};
}}

/* ═══════════════════════ ALERTES STREAMLIT ═══════════════════════ */
[data-testid="stAlert"] {{
    border-radius: 11px !important;
    font-size: 0.87rem !important;
    animation: fade-up 0.25s ease;
}}
[data-testid="stAlert"][data-type="success"] {{
    background: {C_GREEN}0d !important;
    border-color: {C_GREEN}44 !important;
    color: {C_GREEN} !important;
}}
[data-testid="stAlert"][data-type="error"] {{
    background: {C_RED}0d !important;
    border-color: {C_RED}44 !important;
}}
[data-testid="stAlert"][data-type="warning"] {{
    background: {C_GOLD}0d !important;
    border-color: {C_GOLD}44 !important;
}}
[data-testid="stAlert"][data-type="info"] {{
    background: {C_CYAN}0d !important;
    border-color: {C_CYAN}33 !important;
}}

/* ═══════════════════════ SPINNER ═══════════════════════ */
[data-testid="stSpinner"] > div > div {{
    border-color: {C_CYAN}44 !important;
    border-top-color: {C_CYAN} !important;
}}

/* ═══════════════════════ SCROLLBAR ═══════════════════════ */
/* Scrollbar principal de la page — visible, stylisée, navigable */
html {{ scrollbar-width: thin; scrollbar-color: {C_CYAN} {C_BG2}; }}
::-webkit-scrollbar {{ width: 10px; height: 8px; }}
::-webkit-scrollbar-track {{
    background: {C_BG2};
    border-left: 1px solid {C_BORDER};
}}
::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, {C_CYAN}, {C_PURPLE});
    border-radius: 10px;
    border: 2px solid {C_BG2};
    min-height: 40px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: linear-gradient(180deg, {C_CYAN}, {C_CYAN});
    box-shadow: 0 0 8px rgba(0,212,255,0.6);
}}
::-webkit-scrollbar-corner {{ background: {C_BG}; }}

/* ═══════════════════════ DIVIDER HR ═══════════════════════ */
hr {{
    border: none !important;
    border-top: 1px solid {C_CYAN}18 !important;
    margin: 18px 0 !important;
    background: linear-gradient(90deg, transparent, {C_CYAN}22, transparent) !important;
    height: 1px !important;
}}

/* ═══════════════════════ SIDEBAR ═══════════════════════ */
[data-testid="stSidebar"] label {{
    color: {C_TEXT} !important;
    font-size: 0.82rem;
    font-weight: 500;
}}
[data-testid="stSidebar"] .stSelectbox label {{ color: {C_CYAN} !important; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stSlider"] label {{
    color: {C_GREEN} !important;
    font-weight: 600;
}}
[data-testid="stSidebar"] [data-testid="stNumberInput"] label {{
    color: {C_GREEN} !important;
    font-weight: 600;
}}

/* ═══════════════════════ CODE BLOCK ═══════════════════════ */
[data-testid="stCode"] {{
    background: {C_BG2} !important;
    border: 1px solid {C_BORDER} !important;
    border-radius: 10px !important;
    font-size: 0.78rem !important;
}}

/* ═══════════════════════ MARKDOWN TABLES ═══════════════════════ */
[data-testid="stMarkdown"] table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
    border-radius: 10px;
    overflow: hidden;
    display: block;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    max-width: 100%;
}}
[data-testid="stMarkdown"] th {{
    background: {C_CARD} !important;
    color: {C_CYAN} !important;
    font-weight: 700;
    padding: 10px 16px;
    text-align: left;
    border-bottom: 1px solid {C_CYAN}28;
    text-transform: uppercase;
    font-size: 0.78rem;
    letter-spacing: 0.06em;
}}
[data-testid="stMarkdown"] td {{
    padding: 8px 16px;
    border-bottom: 1px solid {C_BORDER}66;
    color: {C_TEXT};
}}
[data-testid="stMarkdown"] tr:nth-child(even) td {{
    background: {C_BG2}88;
}}
[data-testid="stMarkdown"] tr:hover td {{
    background: {C_CYAN}06;
}}

/* ═══════════════════════ CAPTION ═══════════════════════ */
[data-testid="stCaption"] {{
    color: {C_MUTED} !important;
    font-size: 0.78rem !important;
    font-style: italic;
}}

/* ═══════════════════════ SPINNER OVERLAY ═══════════════════════ */
[data-testid="stStatusWidget"] {{
    background: {C_BG2}ee !important;
    border: 1px solid {C_CYAN}22 !important;
    border-radius: 10px !important;
    color: {C_TEXT} !important;
}}

/* ═══════════════════════ PLOTLY CHART CONTAINER ═══════════════════════ */
[data-testid="stPlotlyChart"] {{
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid {C_CYAN}0f;
    background: {C_BG} !important;
    width: 100% !important;
    max-width: 100% !important;
}}
[data-testid="stPlotlyChart"] > div,
[data-testid="stPlotlyChart"] .js-plotly-plot {{
    width: 100% !important;
    max-width: 100% !important;
}}

/* ═══════════════════════ COLONNES & GRILLES ═══════════════════════ */
/* Colonnes Streamlit — jamais de débordement, toujours flexibles */
[data-testid="column"] {{
    min-width: 0 !important;
    flex-shrink: 1 !important;
    overflow: visible !important;
}}
[data-testid="stHorizontalBlock"] {{
    align-items: flex-start !important;
    gap: 1rem !important;
    width: 100% !important;
}}

/* Textes longs — retour à la ligne automatique */
[data-testid="stMarkdown"] {{
    word-break: break-word;
    overflow-wrap: break-word;
}}

/* ═══════════════════════ RESPONSIVE — TOUS SUPPORTS ═══════════════════════ */

/* ── MacBook / Desktop standard (> 1024px) ── */
@media screen and (min-width: 1025px) {{
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-bottom: calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
    }}
}}

/* ── Grands écrans (> 1600px — 4K, iMac 27", Ultra-wide) ── */
@media screen and (min-width: 1600px) {{
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        padding-bottom: calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-size: 0.88rem !important;
        padding: 7px 18px !important;
    }}
}}

/* ── Tablettes paysage + petit laptop (768px – 1024px) ── */
@media screen and (max-width: 1024px) {{
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-size: 0.74rem !important;
        padding: 5px 8px !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-size: 1.2rem !important;
    }}
}}

/* ── Tablettes portrait + mobiles larges (< 768px) ── */
@media screen and (max-width: 768px) {{
    html, body {{ font-size: 13px !important; }}
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-bottom: calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        flex-wrap: wrap !important;
        gap: 2px !important;
        padding: 4px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-size: 0.68rem !important;
        padding: 4px 6px !important;
    }}
    /* Colonnes en colonne sur mobile */
    [data-testid="stHorizontalBlock"] {{
        flex-direction: column !important;
    }}
    [data-testid="column"] {{
        width: 100% !important;
        flex: 1 1 100% !important;
    }}
    div[data-testid="stMetric"] {{
        padding: 8px 10px !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-size: 1.1rem !important;
    }}
    div[data-testid="stMetric"] label {{ font-size: 0.66rem !important; }}
    [data-testid="stPlotlyChart"] {{ border-radius: 8px !important; }}
    .stButton > button {{
        font-size: 0.82rem !important;
        padding: 8px 12px !important;
    }}
}}

/* ── Très petits écrans (< 480px — iPhone SE, petits Android) ── */
@media screen and (max-width: 480px) {{
    html, body {{ font-size: 12px !important; }}
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-bottom: calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-size: 0.62rem !important;
        padding: 3px 5px !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-size: 1rem !important;
    }}
}}

/* ═══════════════════════ iOS / SAFARI MOBILE ═══════════════════════ */

/* Viewport safe-area — iPhone notch, Dynamic Island, rounded corners */
.main .block-container,
[data-testid="stMainBlockContainer"] {{
    padding-left: max(0.75rem, env(safe-area-inset-left)) !important;
    padding-right: max(0.75rem, env(safe-area-inset-right)) !important;
    padding-bottom: calc(9rem + env(safe-area-inset-bottom, 0px)) !important;
}}

/* Empêche le zoom automatique iOS sur les inputs (font-size >= 16px) */
input, select, textarea {{
    font-size: 16px !important;
}}

/* Cible touch plus large sur mobile (Apple HIG: 44×44px min) */
@media (hover: none) and (pointer: coarse) {{
    .stButton > button {{
        min-height: 44px !important;
        min-width: 44px !important;
        padding: 10px 16px !important;
    }}
    [data-baseweb="tab"] {{
        min-height: 44px !important;
        padding: 10px 10px !important;
    }}
    /* Désactive les effets hover qui n'ont pas de sens sur touch */
    .zed-scroll-btn:hover {{
        transform: none !important;
        box-shadow: 0 0 14px rgba(0,212,255,0.25), 0 4px 12px rgba(0,0,0,0.5) !important;
    }}
    /* Empêche le pull-to-refresh pendant le scroll des charts */
    [data-testid="stPlotlyChart"] {{
        overscroll-behavior: contain;
        -webkit-overflow-scrolling: touch;
        touch-action: pan-y;
    }}
}}

/* GPU compositing ciblé — uniquement sur les éléments animés, pas les conteneurs */
.zed-scroll-btn {{
    will-change: transform;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
}}

/* ═══════════════════════ WINDOWS HIGH CONTRAST MODE ═══════════════════════ */
@media (forced-colors: active) {{
    /* Restaure les bordures visibles en mode contraste élevé Windows */
    .stButton > button {{
        border: 2px solid ButtonText !important;
        forced-color-adjust: none;
    }}
    [data-testid="stPlotlyChart"] {{
        border: 1px solid CanvasText !important;
    }}
    /* Préserve les couleurs sémantiques (vert=gain, rouge=perte) */
    [data-testid="stMetricDelta"] {{
        forced-color-adjust: none;
    }}
}}

/* ═══════════════════════ FIREFOX — SCROLLBAR & PREFIXES ═══════════════════════ */
/* Firefox utilise scrollbar-width/color (standard CSS, pas -webkit-) */
* {{
    scrollbar-width: thin;
    scrollbar-color: {C_CYAN} {C_BG2};
}}

/* ═══════════════════════ FOCUS VISIBLE — NAVIGATION CLAVIER ═══════════════════════ */
:focus-visible {{
    outline: 2px solid {C_CYAN} !important;
    outline-offset: 2px !important;
    border-radius: 4px !important;
}}
:focus:not(:focus-visible) {{
    outline: none !important;
}}

/* ═══════════════════════ FONT FALLBACK — HORS LIGNE ═══════════════════════ */
/* Si Google Fonts indisponible (Linux hors réseau, pare-feu), fallback propre */
html, body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, Helvetica, Arial, sans-serif !important;
}}

/* ═══════════════════════ TOUCH — FEEDBACK ACTIF ═══════════════════════ */
.stButton > button:active {{
    transform: scale(0.97) translateZ(0);
    transition: transform 0.08s ease;
}}

/* ═══════════════════════ CSS CONTAINMENT — PERFORMANCE ═══════════════════════ */
/* contain: layout style sur column INTERDIT — bloque le scroll natif */
/* Containment léger uniquement sur les charts — n'affecte pas le scroll */
[data-testid="stPlotlyChart"] {{
    contain: style;
}}
div[data-testid="stMetric"] {{
    contain: style;
}}

/* ═══════════════════════ POINTER: COARSE — TOUCH GÉNÉRIQUE ═══════════════════════ */
@media (pointer: coarse) {{
    /* Scrollbar invisible sur touch (espace précieux) */
    ::-webkit-scrollbar {{ width: 4px !important; height: 4px !important; }}
    /* Sidebar ferméee par défaut traitée par Streamlit — pas besoin de CSS */
}}

/* ═══════════════════════ PREFERS COLOR SCHEME LIGHT — COMPATIBILITÉ ═══════════════════════ */
/* Le thème est dark-only — on force explicitement pour éviter un flash blanc */
@media (prefers-color-scheme: light) {{
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background-color: {C_BG} !important;
        color: {C_TEXT} !important;
        color-scheme: dark;
    }}
}}
html {{
    color-scheme: dark;
}}

/* ── Impression / export PDF ── */
@media print {{
    [data-testid="stSidebar"],
    [data-testid="stHeader"],
    .stButton {{ display: none !important; }}
    .main .block-container {{ padding: 0 !important; }}
    [data-testid="stPlotlyChart"] {{
        border: 1px solid #ccc !important;
        break-inside: avoid;
    }}
}}

/* ── Accessibilité WCAG 2.1 — respect prefers-reduced-motion ── */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
    /* Désactive les animations néon flicker et pulse pour les utilisateurs sensibles */
    .neon-title, [style*="animation"] {{
        animation: none !important;
    }}
}}
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _eur(v: float, sign: bool = False) -> str:
    try:
        v = float(v)
        p = "+" if (sign and v > 0) else ""
        return f"{p}{v:,.2f} €"
    except Exception:
        return "— €"


def _scalar(val) -> float:
    try:
        v = float(val.iloc[-1]) if isinstance(val, pd.Series) else float(val)
        return 0.0 if (v != v) else v  # NaN check
    except Exception:
        return 0.0


def _hex_rgba(hex6: str, alpha: float) -> str:
    """Convertit #RRGGBB → rgba(r,g,b,alpha). Compatible CSS3 + Plotly."""
    try:
        h = hex6.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.3f})"
    except Exception:
        return hex6


def _color_var(val: str) -> str:
    """Style CSS pour pandas style.map — colore en vert/rouge selon +/-."""
    s = str(val)
    if "+" in s:
        return f"color: {C_GREEN}; font-weight: 700"
    if "-" in s and "—" not in s:
        return f"color: {C_RED}; font-weight: 700"
    return f"color: {C_TEXT}"


def _card(title: str, value: str, delta: str = "",
          color: str = C_CYAN, icon: str = "◆") -> None:
    glow = _hex_rgba(color, 0.27)
    border_dim = _hex_rgba(color, 0.20)
    if delta:
        dcolor = C_GREEN if "+" in delta else C_RED
        d_html = (
            f"<div style='font-size:0.82rem;color:{dcolor};"
            f"margin-top:4px;font-weight:600'>{delta}</div>"
        )
    else:
        d_html = ""
    st.markdown(
        f"<div style='"
        f"background:linear-gradient(135deg,{C_CARD} 0%,{C_BG2} 100%);"
        f"border:1px solid {border_dim};"
        f"border-left:3px solid {color};"
        f"border-radius:14px;"
        f"padding:16px 20px;"
        f"margin-bottom:10px;"
        f"box-shadow:0 0 18px {glow},inset 0 1px 0 rgba(255,255,255,0.04);"
        f"position:relative;overflow:hidden;"
        f"animation:slide-in 0.4s ease'>"
        f"<div style='position:absolute;top:-12px;right:-12px;"
        f"width:44px;height:44px;"
        f"background:{color}15;"
        f"transform:rotate(45deg);border-radius:6px;"
        f"border:1px solid {color}22'></div>"
        f"<div style='font-size:0.7rem;color:{C_MUTED};"
        f"text-transform:uppercase;letter-spacing:0.12em;"
        f"margin-bottom:6px;font-weight:600'>"
        f"{icon} {title}</div>"
        f"<div style='font-size:clamp(1.1rem,1.8vw,1.45rem);font-weight:800;"
        f"background:linear-gradient(90deg,{C_WHITE},{color});"
        f"-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        f"background-clip:text;line-height:1.2'>{value}</div>"
        f"{d_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def _badge(txt: str, color: str = C_CYAN) -> str:
    bg = color + "22"
    return (
        f"<span style='background:{bg};color:{color};"
        f"border:1px solid {color}66;"
        f"padding:3px 12px;border-radius:20px;"
        f"font-size:0.78rem;font-weight:700;"
        f"letter-spacing:0.05em'>{txt}</span>"
    )


def _section_title(txt: str, color: str = C_CYAN, icon: str = "▶") -> None:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"margin:22px 0 14px;animation:slide-in 0.3s ease'>"
        f"<div style='width:4px;height:24px;background:linear-gradient(180deg,{color},{color}66);"
        f"border-radius:3px;box-shadow:0 0 10px {color}88;flex-shrink:0'></div>"
        f"<span style='font-size:1.02rem;font-weight:800;color:{color};"
        f"letter-spacing:0.05em;text-shadow:0 0 12px {color}44'>{icon} {txt}</span>"
        f"<div style='flex:1;height:1px;background:linear-gradient(90deg,{color}22,transparent);margin-left:8px'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _hero_banner(symbol: str, capital: float) -> None:
    st.markdown(
        f"<div style='"
        f"background:linear-gradient(135deg,{C_BG2} 0%,#071428 50%,{C_BG2} 100%);"
        f"border:1px solid {C_CYAN}33;"
        f"border-radius:20px;"
        f"padding:22px 28px;"
        f"margin-top:0.5rem;margin-bottom:20px;"
        f"box-shadow:0 0 40px {C_CYAN}15,0 0 80px {C_CYAN}08;"
        f"position:relative;overflow:hidden'>"
        f"<div style='position:absolute;top:-30px;right:-30px;"
        f"width:120px;height:120px;"
        f"background:radial-gradient({C_CYAN}11,transparent 70%);"
        f"border-radius:50%;pointer-events:none'></div>"
        f"<div style='position:absolute;bottom:-20px;left:10%;width:80px;height:80px;"
        f"background:radial-gradient({C_GOLD}08,transparent 70%);"
        f"border-radius:50%;pointer-events:none'></div>"
        f"<div style='display:flex;align-items:center;gap:18px'>"
        f"<div style='font-size:2.8rem;filter:drop-shadow(0 0 12px {C_GOLD}88)'>🚀</div>"
        f"<div>"
        f"<div style='"
        f"font-family:Orbitron,sans-serif;"
        f"font-size:1.9rem;font-weight:900;"
        f"background:linear-gradient(90deg,{C_CYAN},{C_GOLD},{C_GREEN});"
        f"background-size:200% auto;"
        f"animation:shimmer 3s linear infinite;"
        f"-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        f"background-clip:text'>THE ZEDICUS v3</div>"
        f"<div style='color:{C_MUTED};font-size:0.85rem;margin-top:3px'>"
        f"⚡ Trading Algorithmique · "
        f"<span style='color:{C_CYAN}'>{symbol}</span> · "
        f"<span style='color:{C_GOLD}'>{_eur(capital)}</span></div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DONNÉES (CACHÉ)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=120, show_spinner=False)
def _load(symbol: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """
    OHLCV + indicateurs — source optimale selon l'actif :
      Crypto → Binance (rapide, fiable)
      Autres → Yahoo Finance avec guard-rails période/intervalle
    Cache 2 min (120s).
    """
    try:
        # ── Récupération multi-source ──────────────────────────────────────
        df = smart_ohlcv(symbol, period, interval)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        need = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[need].copy()
        df.dropna(subset=["Close"], inplace=True)
        if len(df) < 5:
            return pd.DataFrame()

        # ── Indicateurs techniques ─────────────────────────────────────────
        c = df["Close"]
        df["SMA20"]  = c.rolling(20, min_periods=1).mean()
        df["SMA50"]  = c.rolling(50, min_periods=1).mean()
        df["EMA12"]  = c.ewm(span=12, adjust=False).mean()
        df["EMA26"]  = c.ewm(span=26, adjust=False).mean()
        df["EMA50"]  = c.ewm(span=50, adjust=False).mean()
        df["EMA200"] = c.ewm(span=200, adjust=False).mean()
        df["MACD"]   = df["EMA12"] - df["EMA26"]
        df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["Hist"]   = df["MACD"] - df["Signal"]
        # RSI — min_periods=14 pour éviter les pseudo-valeurs sur les 13 premières bougies
        d = c.diff()
        gain = d.clip(lower=0).rolling(14, min_periods=14).mean()
        loss = (-d.clip(upper=0)).rolling(14, min_periods=14).mean()
        df["RSI"] = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)
        # OBV
        vol_s = df.get("Volume", pd.Series(0, index=df.index))
        df["OBV"] = (np.sign(c.diff()) * vol_s).fillna(0).cumsum()
        # Bollinger Bands
        bm = c.rolling(20, min_periods=1).mean()
        bs = c.rolling(20, min_periods=1).std().fillna(0)
        df["BB_upper"] = bm + 2 * bs
        df["BB_lower"] = bm - 2 * bs
        df["BB_mid"]   = bm
        # BB %B (position dans les bandes)
        bb_range = df["BB_upper"] - df["BB_lower"]
        df["BB_pct"] = ((c - df["BB_lower"]) / bb_range.replace(0, np.nan)).fillna(0.5)
        # ATR
        if "High" in df.columns and "Low" in df.columns:
            tr = pd.concat([
                df["High"] - df["Low"],
                (df["High"] - c.shift()).abs(),
                (df["Low"]  - c.shift()).abs(),
            ], axis=1).max(axis=1)
            df["ATR"] = tr.rolling(14, min_periods=1).mean()
        # Momentum
        df["Mom5"]  = c.pct_change(5).fillna(0)
        df["Mom10"] = c.pct_change(10).fillna(0)
        # Volume ratio
        if "Volume" in df.columns:
            avgv = df["Volume"].rolling(20, min_periods=1).mean().replace(0, np.nan)
            df["VolRatio"] = (df["Volume"] / avgv).fillna(1.0)
        # Z-score (mean reversion)
        roll_mean = c.rolling(20, min_periods=5).mean()
        roll_std  = c.rolling(20, min_periods=5).std().replace(0, np.nan)
        df["ZScore"] = ((c - roll_mean) / roll_std).fillna(0)
        # Rendements
        df["Ret1"]  = c.pct_change()
        df["Vol20"] = df["Ret1"].rolling(20, min_periods=5).std() * np.sqrt(252)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def _multi_tf(symbol: str) -> dict:
    res, cfgs = {}, [("5m","5d"),("1h","60d"),("1d","6mo"),("1wk","2y")]
    for tf, per in cfgs:
        try:
            df = _load(symbol, per, tf)
            if df.empty or len(df) < 10:
                res[tf] = "–"; continue
            last = df.iloc[-1]
            close = _scalar(last.get("Close", 0))
            sma20 = _scalar(last.get("SMA20", close * 0.99))
            sma50 = _scalar(last.get("SMA50", close * 0.98))
            rsi   = float(last.get("RSI", 50) or 50)
            if rsi != rsi: rsi = 50.0  # NaN guard
            macd  = _scalar(last.get("MACD", 0))
            sig   = _scalar(last.get("Signal", 0))
            sc = sum([
                close > sma20 if sma20 > 0 else False,
                close > sma50 if sma50 > 0 else False,
                rsi > 55,
                macd > sig,
            ])
            res[tf] = "🟢 Haussier" if sc >= 3 else "🔴 Baissier" if sc <= 1 else "🟡 Neutre"
        except Exception:
            res[tf] = "–"
    return res


def _market_health(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {}
    try:
        last  = df.iloc[-1]
        close = _scalar(last["Close"])
        sma20 = _scalar(last["SMA20"])
        sma50 = _scalar(last["SMA50"])
        rsi   = float(last.get("RSI", 50))
        if np.isnan(rsi): rsi = 50.0
        macd  = _scalar(last["MACD"])
        sig   = _scalar(last["Signal"])
        vol_raw = last.get("Volume", 0)
        vol   = float(vol_raw) if vol_raw is not None and not (isinstance(vol_raw, float) and np.isnan(vol_raw)) else 0.0
        avgv  = float(df["Volume"].rolling(20, min_periods=1).mean().iloc[-1]) if "Volume" in df.columns else 1.0
        if np.isnan(avgv) or avgv == 0: avgv = 1.0
        vol20 = float(last.get("Vol20", 0.2))
        if np.isnan(vol20): vol20 = 0.2
        s = {
            "Tendance":   85 if close > sma20 > sma50 else 60 if close > sma20 else 30,
            "Momentum":   80 if 45 <= rsi <= 70 else 40 if rsi > 70 else 35,
            "MACD":       75 if macd > sig else 35,
            "Volume":     75 if (vol > avgv and vol > 0) else 45,
            "Volatilité": max(0, min(100, int(100 - min(vol20, 0.5) * 200))),
        }
        s["Total"] = max(0, min(100, int(sum(s.values()) / len(s))))
        return s
    except Exception:
        return {}


def _patterns(df: pd.DataFrame) -> list:
    out = []
    if len(df) < 3 or "Open" not in df.columns: return out
    for i in range(max(1, len(df) - 10), len(df)):
        try:
            r = df.iloc[i]; pv = df.iloc[i-1]
            o,h,l,c = (_scalar(r["Open"]),_scalar(r["High"]),
                       _scalar(r["Low"]),_scalar(r["Close"]))
            po,pc = _scalar(pv["Open"]),_scalar(pv["Close"])
            body = abs(c-o); rng = (h-l) if h!=l else 0.0001
            uw = h-max(o,c); lw = min(o,c)-l
            dt = str(df.index[i])[:10]
            if body/rng < 0.1:
                out.append({"Date":dt,"Pattern":"🌀 Doji","Signal":"⚪ Indécision"})
            elif lw > 2*body and uw < body:
                out.append({"Date":dt,"Pattern":"🔨 Marteau","Signal":"🟢 Retournement ↑"})
            elif uw > 2*body and lw < body:
                out.append({"Date":dt,"Pattern":"⭐ Étoile filante","Signal":"🔴 Retournement ↓"})
            elif c > o and body/rng > 0.85:
                out.append({"Date":dt,"Pattern":"💚 Marubozu haussier","Signal":"🟢 Force acheteurs"})
            elif c < o and body/rng > 0.85:
                out.append({"Date":dt,"Pattern":"❤️ Marubozu baissier","Signal":"🔴 Force vendeurs"})
            elif c > o and pc < po and c > po and o < pc:
                out.append({"Date":dt,"Pattern":"🌟 Engloutissement ↑","Signal":"🟢 Signal fort achat"})
            elif c < o and pc > po and c < po and o > pc:
                out.append({"Date":dt,"Pattern":"💥 Engloutissement ↓","Signal":"🔴 Signal fort vente"})
        except Exception:
            continue
    return out[-5:]


def _cal_events() -> list:
    today = datetime.now()
    raw = [
        # — Passé récent (archivé) —
        (datetime(2026,4, 2), "NFP",       "🟠"),
        (datetime(2026,4,10), "CPI US",    "🟠"),
        (datetime(2026,4,17), "BCE",        "🔴"),
        (datetime(2026,5, 1), "FOMC",       "🔴"),
        (datetime(2026,5, 2), "NFP",        "🟠"),
        (datetime(2026,5,13), "CPI US",     "🟠"),
        # — À venir 2026 —
        (datetime(2026,6, 5), "BCE",        "🔴"),
        (datetime(2026,6, 5), "NFP",        "🟠"),
        (datetime(2026,6,10), "FOMC",       "🔴"),
        (datetime(2026,6,12), "CPI US",     "🟠"),
        (datetime(2026,7, 2), "NFP",        "🟠"),
        (datetime(2026,7,14), "CPI US",     "🟠"),
        (datetime(2026,7,24), "BCE",        "🔴"),
        (datetime(2026,7,29), "FOMC",       "🔴"),
        (datetime(2026,8, 7), "NFP",        "🟠"),
        (datetime(2026,8,12), "CPI US",     "🟠"),
        (datetime(2026,9,10), "BCE",        "🔴"),
        (datetime(2026,9,16), "FOMC",       "🔴"),
        (datetime(2026,9,11), "CPI US",     "🟠"),
        (datetime(2026,10, 2),"NFP",        "🟠"),
        (datetime(2026,10,14),"CPI US",     "🟠"),
        (datetime(2026,10,29),"BCE",        "🔴"),
        (datetime(2026,11, 4),"FOMC",       "🔴"),
        (datetime(2026,11, 6),"NFP",        "🟠"),
        (datetime(2026,11,12),"CPI US",     "🟠"),
        (datetime(2026,12,10),"BCE",        "🔴"),
        (datetime(2026,12,15),"FOMC",       "🔴"),
        # — Prévisions 2027 —
        (datetime(2027,1, 8), "NFP",        "🟠"),
        (datetime(2027,1,28), "FOMC",       "🔴"),
        (datetime(2027,3,18), "FOMC",       "🔴"),
        (datetime(2027,5, 6), "FOMC",       "🔴"),
    ]
    evs = [{"date":d,"ev":e,"impact":i,"delta":(d-today).days} for d,e,i in raw]
    return sorted(evs, key=lambda x: x["delta"])


def _next_event() -> str:
    evs = [e for e in _cal_events() if e["delta"] >= 0]
    if not evs: return "Aucun événement proche"
    e = evs[0]
    return f"{e['impact']} {e['ev']} dans {e['delta']}j"


def _sym_list(cat: str) -> list:
    items = ASSET_CATEGORIES.get(cat, [])
    return [x[0] if isinstance(x,(tuple,list)) else x for x in items]


def _sym_names(cat: str) -> list:
    items = ASSET_CATEGORIES.get(cat, [])
    return [f"{x[0]} — {x[1]}" if isinstance(x,(tuple,list)) else x for x in items]


def _chart_layout(height: int = 500, title: str = "") -> dict:
    return dict(
        height=height,
        title=dict(text=title, font=dict(color=C_CYAN, size=13, family="Orbitron,sans-serif")) if title else None,
        paper_bgcolor=C_BG, plot_bgcolor=C_BG2,
        font=dict(color=C_TEXT, family="Inter", size=11),
        margin=dict(l=60, r=20, t=48 if title else 24, b=44),
        xaxis=dict(
            gridcolor="#0d1f35", zeroline=False, showgrid=True,
            tickfont=dict(color=C_MUTED, size=10),
            linecolor=C_BORDER, tickcolor=C_BORDER,
        ),
        yaxis=dict(
            gridcolor="#0d1f35", zeroline=False, showgrid=True,
            tickfont=dict(color=C_MUTED, size=10),
            linecolor=C_BORDER, tickcolor=C_BORDER,
        ),
        legend=dict(
            bgcolor="rgba(6,15,32,0.85)", font=dict(color=C_TEXT, size=11),
            bordercolor=C_BORDER, borderwidth=1,
        ),
        hoverlabel=dict(
            bgcolor=C_CARD, font_color=C_WHITE,
            bordercolor=C_CYAN, font_size=12,
        ),
        hovermode="x unified",
    )


def _candle_fig(df: pd.DataFrame, title: str = "") -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.58, 0.24, 0.18],
        vertical_spacing=0.03,
        subplot_titles=("", "RSI (14)", "Volume"),
    )
    # Certains indices (ex: ^GSPC, ^FCHI) peuvent manquer de colonnes OHLC
    has_ohlc = all(c in df.columns for c in ["Open","High","Low","Close"])
    if has_ohlc:
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            increasing_line_color=C_GREEN, decreasing_line_color=C_RED,
            increasing_fillcolor="rgba(0,255,136,0.33)", decreasing_fillcolor="rgba(255,51,102,0.33)",
            name="Prix"), row=1, col=1)
    else:
        # Fallback : ligne simple si OHLC incomplet
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            line=dict(color=C_CYAN, width=2), name="Prix"), row=1, col=1)
    for col, col_c, nm in [("SMA20",C_GOLD,"SMA 20"),("SMA50",C_PURPLE,"SMA 50")]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col],
                line=dict(color=col_c, width=1.5), name=nm, opacity=0.9), row=1, col=1)
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"],
            line=dict(color=C_SILVER, width=0.8, dash="dot"), name="BB+",
            opacity=0.6), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"],
            line=dict(color=C_SILVER, width=0.8, dash="dot"),
            fill="tonexty", fillcolor=f"rgba(192,192,192,0.04)",
            name="BB-", opacity=0.6), row=1, col=1)
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"],
            line=dict(color=C_CYAN, width=2), name="RSI"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color=C_RED,   row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color=C_GREEN, row=2, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor=f"rgba(0,212,255,0.03)", row=2, col=1)
    if "Volume" in df.columns:
        if "Open" in df.columns:
            vc = [C_GREEN if c >= o else C_RED
                  for c, o in zip(df["Close"].tolist(), df["Open"].tolist())]
        else:
            vc = [C_CYAN] * len(df)
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"],
            marker_color=vc, name="Vol", opacity=0.75), row=3, col=1)
    layout = _chart_layout(660, title)
    layout["xaxis_rangeslider_visible"] = False
    layout["showlegend"] = True
    layout["hovermode"] = "x unified"
    grid = dict(gridcolor="#0d1f35", zeroline=False, showgrid=True,
                tickfont=dict(color=C_MUTED, size=10), linecolor=C_BORDER)
    for k in ["xaxis", "xaxis2", "xaxis3"]:
        layout[k] = dict(**grid, showticklabels=(k == "xaxis3"))
    for k in ["yaxis", "yaxis2", "yaxis3"]:
        layout[k] = dict(**grid)
    layout["yaxis2"]["title"] = dict(text="RSI", font=dict(color=C_MUTED, size=9), standoff=4)
    layout["yaxis3"]["title"] = dict(text="Vol", font=dict(color=C_MUTED, size=9), standoff=4)
    # Mettre à jour les annotations existantes (subplot_titles) — style cohérent
    # Note : fig.layout.annotations retourne des objets Annotation plotly (pas des dicts)
    styled_annotations = []
    for a in (fig.layout.annotations or []):
        txt = getattr(a, "text", "") or ""
        if txt:
            styled_annotations.append(dict(
                text=txt,
                xref=getattr(a, "xref", "paper"),
                yref=getattr(a, "yref", "paper"),
                x=getattr(a, "x", 0.5),
                y=getattr(a, "y", 0),
                showarrow=False,
                font=dict(color=C_MUTED, size=10, family="Inter"),
                xanchor=getattr(a, "xanchor", "center"),
                yanchor=getattr(a, "yanchor", "bottom"),
            ))
    if styled_annotations:
        layout["annotations"] = styled_annotations
    fig.update_layout(**layout)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:10px 0 16px'>"
            f"<div style='font-family:Orbitron,sans-serif;font-size:1.3rem;"
            f"font-weight:900;background:linear-gradient(90deg,{C_CYAN},{C_GOLD});"
            f"-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
            f"background-clip:text;animation:neon-flicker 12s infinite'>⚡ ZEDICUS v3</div>"
            f"<div style='color:{C_MUTED};font-size:0.72rem;margin-top:2px'>"
            f"🚀 Trading · Petit Budget</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<hr style='border-color:{C_CYAN}22'>", unsafe_allow_html=True)

        st.markdown(f"<div style='color:{C_CYAN};font-size:0.75rem;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.1em;"
                    f"margin-bottom:4px'>◆ Actif</div>", unsafe_allow_html=True)
        cat = st.selectbox("Catégorie", list(ASSET_CATEGORIES.keys()), label_visibility="collapsed")
        noms = _sym_names(cat)
        syms = _sym_list(cat)
        idx  = st.selectbox("Actif", range(len(noms)),
                             format_func=lambda i: noms[i], label_visibility="collapsed")
        symbol = syms[idx]

        st.markdown(f"<div style='color:{C_GOLD};font-size:0.75rem;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.1em;"
                    f"margin:10px 0 4px'>◆ Période & Intervalle</div>",
                    unsafe_allow_html=True)
        periode_lbl    = st.selectbox("Période",    list(PERIODS_UI.keys()),
                                      index=3, label_visibility="collapsed")
        intervalle_lbl = st.selectbox("Intervalle", list(INTERVALS_UI.keys()),
                                      index=4, label_visibility="collapsed")

        # Validation combo période / intervalle (yfinance a des limites strictes)
        _p_val = PERIODS_UI[periode_lbl]
        _i_val = INTERVALS_UI[intervalle_lbl]
        from core.config import INTERVALS as _VALID_INTERVALS
        _valid_for_period = _VALID_INTERVALS.get(_p_val, [])
        if _valid_for_period and _i_val not in _valid_for_period:
            _suggest = _valid_for_period[-1]   # le plus grossier = le plus compatible
            st.warning(
                f"⚠️ **{intervalle_lbl}** n'est pas disponible sur **{periode_lbl}** "
                f"(limite yfinance). Utilisé automatiquement : **{_suggest}**."
            )
            intervalle_lbl = next(
                (k for k, v in INTERVALS_UI.items() if v == _suggest),
                intervalle_lbl
            )

        st.markdown(f"<hr style='border-color:{C_CYAN}22'>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:{C_GREEN};font-size:0.75rem;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.1em;"
                    f"margin-bottom:6px'>💎 Capital de Trading</div>",
                    unsafe_allow_html=True)

        # Capital synchronisé via session_state — partagé avec tab_bot et tab_risque
        _cap_default = float(st.session_state.get("shared_capital", 100.0))
        capital  = st.number_input("Capital (€)", 10.0, 1_000.0, _cap_default, 10.0,
                                   label_visibility="collapsed", key="sidebar_capital")
        st.session_state["shared_capital"] = capital
        risk_pct = st.slider("Risque / trade (%)", 0.5, 5.0, 2.0, 0.5)

        # Budget badge
        if capital <= 50:
            budget_color, budget_txt = C_ORANGE, "⚡ MICRO (≤50€) · 1 pos max"
        elif capital <= 200:
            budget_color, budget_txt = C_CYAN, "💡 PETIT (≤200€) · 2 pos max"
        else:
            budget_color, budget_txt = C_GREEN, "🏆 STANDARD (>200€) · 3 pos max"

        st.markdown(
            f"<div style='background:{budget_color}15;border:1px solid {budget_color}44;"
            f"border-radius:10px;padding:8px 12px;margin:8px 0;"
            f"color:{budget_color};font-size:0.78rem;font-weight:700;"
            f"text-align:center'>{budget_txt}</div>",
            unsafe_allow_html=True,
        )

        st.markdown(f"<hr style='border-color:{C_CYAN}22'>", unsafe_allow_html=True)
        next_ev = _next_event()
        st.markdown(
            f"<div style='background:{C_RED}11;border:1px solid {C_RED}33;"
            f"border-radius:10px;padding:8px 12px;font-size:0.78rem;"
            f"color:{C_TEXT}'>"
            f"<div style='color:{C_RED};font-weight:700;margin-bottom:2px'>"
            f"📆 Prochain Macro</div>{next_ev}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"<hr style='border-color:{C_CYAN}22'>", unsafe_allow_html=True)

        # ── Statut du bot — visible depuis n'importe quel onglet ────────────
        _bot_live = st.session_state.get("_zedicus_trading_bot")
        if _bot_live is not None:
            try:
                _bstatus = _bot_live.status
                if _bstatus == BotStatus.RUNNING:
                    _bs_color, _bs_icon, _bs_label = C_GREEN, "🤖", "BOT ACTIF"
                elif _bstatus == BotStatus.PAUSED:
                    _bs_color, _bs_icon, _bs_label = C_GOLD, "⏸️", "BOT EN PAUSE"
                else:
                    _bs_color, _bs_icon, _bs_label = C_MUTED, "⏹️", "BOT ARRÊTÉ"
            except Exception:
                _bs_color, _bs_icon, _bs_label = C_MUTED, "⏹️", "BOT ARRÊTÉ"
        else:
            _bs_color, _bs_icon, _bs_label = C_MUTED, "⏹️", "BOT ARRÊTÉ"
        st.markdown(
            f"<div style='background:{_bs_color}18;border:1px solid {_bs_color}55;"
            f"border-radius:10px;padding:7px 10px;margin:8px 0;"
            f"text-align:center;font-size:0.78rem;font-weight:700;"
            f"color:{_bs_color}'>{_bs_icon} {_bs_label}</div>",
            unsafe_allow_html=True,
        )

        # Bouton de rafraîchissement
        if st.button("🔄 Rafraîchir les données", use_container_width=True, key="sidebar_refresh"):
            st.cache_data.clear()
            st.rerun()

        st.markdown(
            f"<div style='text-align:center;color:{C_MUTED};font-size:0.68rem;margin-top:6px'>"
            f"⚠️ Usage éducatif uniquement</div>",
            unsafe_allow_html=True,
        )

    return {
        "symbol":    symbol,
        "categorie": cat,
        "periode":   PERIODS_UI[periode_lbl],
        "intervalle": INTERVALS_UI[intervalle_lbl],
        "capital":   float(capital),
        "risk_pct":  risk_pct / 100,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — ACCUEIL
# ══════════════════════════════════════════════════════════════════════════════

def tab_accueil(p: dict) -> None:
    _hero_banner(p["symbol"], p["capital"])

    df = _load(p["symbol"], p["periode"], p["intervalle"])

    # Prix live (source la plus rapide selon l'actif)
    live_data = smart_price(p["symbol"])
    if not isinstance(live_data, dict):
        live_data = {}

    c1, c2, c3, c4 = st.columns(4)
    if not df.empty and len(df) > 1:
        # Préférer le prix live si disponible
        last_hist = _scalar(df["Close"].iloc[-1])
        last  = live_data.get("price", last_hist) if live_data else last_hist
        prev  = _scalar(df["Close"].iloc[-2])
        # Si on a une variation live directe
        if live_data and "change_pct" in live_data:
            chg = live_data["change_pct"]
        else:
            chg = (last - prev) / prev * 100 if prev else 0.0
        rsi   = float(df["RSI"].iloc[-1]) if "RSI" in df.columns else 50.0
        if np.isnan(rsi): rsi = 50.0
        vol20 = float(df["Vol20"].iloc[-1]) * 100 if "Vol20" in df.columns else 0.0
        if np.isnan(vol20): vol20 = 0.0
        src_lbl = live_data.get("source", "yf") if live_data else "yf"
        chg_str = f"+{chg:.2f} %" if chg >= 0 else f"{chg:.2f} %"
        with c1:
            _card(f"Prix actuel [{src_lbl}]", _eur(last), chg_str,
                  C_GREEN if chg >= 0 else C_RED, "💲")
        with c2:
            if rsi > 70:   rt, rc = f"Suracheté {rsi:.0f}", C_RED
            elif rsi < 30: rt, rc = f"Survendu {rsi:.0f}", C_GREEN
            else:           rt, rc = f"Neutre {rsi:.0f}", C_CYAN
            _card("RSI (14)", rt, color=rc, icon="📊")
        with c3: _card("Volatilité ann.", f"{vol20:.1f} %", color=C_GOLD, icon="🌊")
        with c4: _card("Prochain macro", _next_event(), color=C_RED, icon="📆")
        # Timestamp de fraîcheur
        _ts = datetime.now().strftime("%H:%M:%S")
        st.caption(f"🕐 Données mises à jour à {_ts} · Source : {src_lbl}")
    else:
        for col in [c1, c2, c3, c4]:
            with col:
                st.markdown(
                    f"<div style='background:{C_CARD};border:1px solid {C_CYAN}22;"
                    f"border-radius:14px;padding:20px;text-align:center;"
                    f"color:{C_MUTED}'>Chargement…</div>",
                    unsafe_allow_html=True,
                )

    left, right = st.columns([3, 1])
    with left:
        if not df.empty:
            st.plotly_chart(_candle_fig(df, p["symbol"]),
                            use_container_width=True)
        else:
            st.warning(f"Impossible de charger {p['symbol']}")

    with right:
        _section_title("Santé du marché", C_GOLD, "💓")
        health = _market_health(df)
        if health:
            total = health.get("Total", 0)
            hcol  = C_GREEN if total > 65 else C_GOLD if total > 40 else C_RED
            power_label = "🔥 FORT" if total > 65 else "⚡ MOYEN" if total > 40 else "❄️ FAIBLE"
            st.markdown(
                f"<div style='text-align:center;padding:12px 0 8px'>"
                f"<div class='zed-ring' style='font-family:Orbitron,sans-serif;"
                f"font-size:3rem;font-weight:900;color:{hcol};"
                f"text-shadow:0 0 24px {hcol}88;line-height:1'>"
                f"{total}</div>"
                f"<div style='height:6px;background:{C_BORDER};border-radius:3px;"
                f"margin:8px 12px;overflow:hidden'>"
                f"<div style='width:{total}%;height:100%;"
                f"background:linear-gradient(90deg,{hcol}88,{hcol});"
                f"border-radius:3px;box-shadow:0 0 8px {hcol}66'></div></div>"
                f"<div style='color:{hcol};font-size:0.72rem;letter-spacing:0.12em;"
                f"font-weight:700'>{power_label} · {total}/100</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            for k, v in health.items():
                if k == "Total": continue
                kc = C_GREEN if v >= 70 else C_GOLD if v >= 50 else C_RED
                st.markdown(
                    f"<div style='margin-bottom:6px'>"
                    f"<div style='display:flex;justify-content:space-between;"
                    f"font-size:0.75rem;color:{C_TEXT};margin-bottom:2px'>"
                    f"<span>{k}</span><span style='color:{kc};font-weight:700'>{v}</span></div>"
                    f"<div style='height:5px;background:{C_BORDER};border-radius:3px'>"
                    f"<div style='width:{v}%;height:100%;background:linear-gradient(90deg,{kc},{kc}88);"
                    f"border-radius:3px;box-shadow:0 0 6px {kc}66'></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

        _section_title("Guide rapide", C_CYAN, "🚀")
        st.markdown(
            f"<div style='font-size:0.82rem;color:{C_TEXT};line-height:1.7'>"
            f"<b style='color:{C_CYAN}'>1.</b> Choisissez un actif (sidebar)<br>"
            f"<b style='color:{C_GOLD}'>2.</b> Analysez (onglet Analyse)<br>"
            f"<b style='color:{C_GREEN}'>3.</b> Vérifiez les signaux<br>"
            f"<b style='color:{C_PURPLE}'>4.</b> Configurez le bot<br>"
            f"<b style='color:{C_RED}'>5.</b> Gérez votre risque<br><br>"
            f"<span style='color:{C_MUTED};font-size:0.73rem'>"
            f"⚠️ Trading = risque de perte en capital</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — MARCHÉ
# ══════════════════════════════════════════════════════════════════════════════

def tab_marche(p: dict) -> None:
    _section_title("Vue du marché mondial", C_CYAN, "🌍")

    # ── Bloc CoinGecko Global (crypto) ────────────────────────────────────────
    try:
        cg_glob = coingecko_global()
        if cg_glob:
            mc_chg_c = C_GREEN if cg_glob.get("market_cap_change_pct", 0) >= 0 else C_RED
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                _card("Cap. Crypto Totale",
                      format_large(cg_glob.get("total_market_cap_usd", 0)),
                      f"{cg_glob.get('market_cap_change_pct',0):+.2f}%",
                      color=mc_chg_c, icon="🌐")
            with g2:
                _card("Volume 24h",
                      format_large(cg_glob.get("total_volume_usd", 0)),
                      color=C_CYAN, icon="📦")
            with g3:
                btc_dom = cg_glob.get("btc_dominance", 0)
                _card("Dominance BTC",
                      f"{btc_dom:.1f}%",
                      color=C_GOLD, icon="₿")
            with g4:
                _card("Cryptos actives",
                      f"{cg_glob.get('active_coins',0):,}",
                      color=C_PURPLE, icon="🔮")
    except Exception:
        pass

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Tableau multi-source parallèle ────────────────────────────────────────
    _section_title("Cours en temps réel", C_GOLD, "⚡")
    watched_map = {
        "BTC-USD": "₿ Bitcoin",      "ETH-USD": "Ξ Ethereum",
        "SOL-USD": "◎ Solana",       "BNB-USD": "◆ BNB",
        "^GSPC":   "📈 S&P 500",     "^IXIC":   "📊 Nasdaq",
        "^FCHI":   "🇫🇷 CAC 40",      "^GDAXI":  "🇩🇪 DAX",
        "EURUSD=X":"💶 EUR/USD",      "GBPUSD=X":"💷 GBP/USD",
        "GC=F":    "🥇 Or",           "CL=F":    "🛢️ Pétrole WTI",
    }
    syms = list(watched_map.keys())

    with st.spinner("Récupération multi-source (Binance · CoinGecko · BCE · Yahoo)…"):
        prices = parallel_prices(syms)

    if prices:
        rows = []
        for sym, name in watched_map.items():
            d = prices.get(sym)
            if not d:
                continue
            price = d.get("price", 0)
            chg   = d.get("change_pct", 0)
            src   = d.get("source", "—")
            # Frankfurter (BCE) ne fournit pas de variation 24h → on n'affiche pas 0.00% trompeur
            chg_str = ("N/D" if (chg == 0.0 and src in ("frankfurter", "bce"))
                       else (f"+{chg:.2f} %" if chg >= 0 else f"{chg:.2f} %"))
            rows.append({
                "Actif":     name,
                "Prix":      f"{price:,.4f}" if price < 1000 else f"{price:,.2f}",
                "Var. 24h":  chg_str,
                "Tendance":  ("—" if chg_str == "N/D"
                              else "🟢 Hausse" if chg > 0.8
                              else "🔴 Baisse" if chg < -0.8
                              else "🟡 Stable"),
                "Source":    src,
            })
        if rows:
            df_m = pd.DataFrame(rows)
            st.dataframe(
                df_m.style.map(_color_var, subset=["Var. 24h"]),
                use_container_width=True, hide_index=True,
            )
    else:
        st.warning("Données de marché indisponibles — vérifiez votre connexion.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Tendances CoinGecko ───────────────────────────────────────────────────
    col_trend, col_fred = st.columns([1, 1])

    with col_trend:
        _section_title("🔥 Trending CoinGecko", C_ORANGE, "🔥")
        try:
            trending = coingecko_trending()
            if trending:
                for i, coin in enumerate(trending):
                    _medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣"]
                    _medal_colors = [C_GOLD, C_SILVER, C_ORANGE, C_CYAN, C_CYAN, C_CYAN, C_CYAN]
                    medal = _medals[i] if i < len(_medals) else "·"
                    mc = _medal_colors[i] if i < len(_medal_colors) else C_MUTED
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;"
                        f"align-items:center;padding:8px 10px;margin-bottom:4px;"
                        f"border-radius:8px;background:{mc}08;"
                        f"border:1px solid {mc}18;transition:background 0.15s'>"
                        f"<span style='display:flex;align-items:center;gap:8px'>"
                        f"<span style='font-size:1.1rem'>{medal}</span>"
                        f"<span><b style='color:{C_WHITE};font-size:0.88rem'>{coin['name']}</b> "
                        f"<span style='color:{mc};font-size:0.75rem;font-weight:700;"
                        f"background:{mc}18;padding:2px 6px;border-radius:10px'>"
                        f"{coin['symbol']}</span></span></span>"
                        f"<span style='color:{C_MUTED};font-size:0.75rem'>#<b style='color:{mc}'>{coin['rank']}</b></span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Données trending indisponibles.")
        except Exception:
            st.info("Données trending indisponibles.")

    with col_fred:
        _section_title("📊 Macro FRED (Fed)", C_RED, "🏛️")
        fred_display = [
            ("Fed Funds Rate",  "FEDFUNDS",    "%"),
            ("CPI (YoY)",       "CPIAUCSL",    "pts"),
            ("Chômage US",      "UNRATE",      "%"),
            ("Spread 10-2Y",    "T10Y2Y",      "%"),
        ]
        for name_f, sid, unit in fred_display:
            try:
                val = fred_latest(sid)
                if val is not None:
                    col_f = C_RED if (sid == "FEDFUNDS" and val > 4) or \
                                     (sid == "UNRATE" and val > 5) or \
                                     (sid == "T10Y2Y" and val < 0) else C_GREEN
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;"
                        f"padding:6px 0;border-bottom:1px solid {C_BORDER}'>"
                        f"<span style='color:{C_TEXT};font-size:0.85rem'>{name_f}</span>"
                        f"<span style='color:{col_f};font-weight:700;font-size:0.9rem'>"
                        f"{val:.2f} {unit}</span></div>",
                        unsafe_allow_html=True,
                    )
            except Exception:
                pass

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Graphique principal ───────────────────────────────────────────────────
    _section_title(f"Graphique complet — {p['symbol']}", C_GOLD, "📊")
    df = _load(p["symbol"], p["periode"], p["intervalle"])
    if not df.empty:
        st.plotly_chart(_candle_fig(df, p["symbol"]), use_container_width=True, config=PLOTLY_CFG)

    # ── Forex BCE temps réel ──────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Taux de change BCE (temps réel)", C_CYAN, "💱")
    try:
        fx = frankfurter_rates()
        if fx:
            fx_names = {
                "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY",
                "USDCHF=X":"USD/CHF","AUDUSD=X":"AUD/USD","EURGBP=X":"EUR/GBP",
            }
            fx_cols = st.columns(3)
            for i, (sym, name) in enumerate(fx_names.items()):
                if sym in fx:
                    with fx_cols[i % 3]:
                        _card(name, f"{fx[sym]:.5f}", color=C_CYAN, icon="💱")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — ANALYSE
# ══════════════════════════════════════════════════════════════════════════════

def tab_analyse(p: dict) -> None:
    _section_title(f"Analyse technique — {p['symbol']}", C_CYAN, "📊")
    df = _load(p["symbol"], p["periode"], p["intervalle"])
    if df.empty:
        st.error(f"⚠️ Impossible de charger les données pour **{p['symbol']}**. "
                 f"Vérifiez votre connexion internet ou changez de symbole dans la barre latérale.")
        return

    a1,a2,a3,a4,a5,a6 = st.tabs([
        "🕯️ Chandeliers","📈 RSI & MACD","📦 Volume & OBV",
        "⏱️ Multi-TF","🔍 Patterns","🔗 Corrélations",
    ])

    with a1:
        last = df.iloc[-1]
        k1,k2,k3 = st.columns(3)
        with k1: _card("Prix", _eur(_scalar(last["Close"])), icon="💲")
        with k2: _card("SMA 20", _eur(_scalar(last["SMA20"])), color=C_GOLD, icon="📉")
        with k3: _card("SMA 50", _eur(_scalar(last["SMA50"])), color=C_PURPLE, icon="📉")
        st.plotly_chart(_candle_fig(df, p["symbol"]), use_container_width=True, config=PLOTLY_CFG)

    with a2:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            subplot_titles=("RSI (14)","MACD (12/26/9)"),
                            vertical_spacing=0.1)
        if "RSI" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["RSI"],
                line=dict(color=C_CYAN, width=2.5), name="RSI",
                fill="tozeroy", fillcolor=f"rgba(0,212,255,0.06)"), row=1, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color=C_RED,   row=1, col=1,
                          annotation_text="Suracheté", annotation_font_color=C_RED)
            fig.add_hline(y=30, line_dash="dash", line_color=C_GREEN, row=1, col=1,
                          annotation_text="Survendu", annotation_font_color=C_GREEN)
            fig.add_hrect(y0=30, y1=70, fillcolor=f"rgba(0,212,255,0.03)", row=1, col=1)
        if "Hist" in df.columns and "MACD" in df.columns and "Signal" in df.columns:
            hv = df["Hist"].tolist()
            hc = [C_GREEN if v >= 0 else C_RED for v in hv]
            fig.add_trace(go.Bar(x=df.index, y=df["Hist"], marker_color=hc,
                                 name="Histogramme", opacity=0.8), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["MACD"],
                line=dict(color=C_GOLD, width=2), name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["Signal"],
                line=dict(color=C_PURPLE, width=2), name="Signal"), row=2, col=1)
        fig.update_layout(**_chart_layout(540))
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)

    with a3:
        fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             subplot_titles=("Volume","OBV (On-Balance Volume)"),
                             vertical_spacing=0.1)
        if "Open" in df.columns:
            vc = [C_GREEN if c >= o else C_RED
                  for c, o in zip(df["Close"].tolist(), df["Open"].tolist())]
        else:
            vc = [C_CYAN] * len(df)
        if "Volume" in df.columns:
            fig2.add_trace(go.Bar(x=df.index, y=df["Volume"],
                marker_color=vc, name="Volume", opacity=0.85), row=1, col=1)
        if "OBV" in df.columns:
            fig2.add_trace(go.Scatter(x=df.index, y=df["OBV"],
                line=dict(color=C_CYAN, width=2), name="OBV",
                fill="tozeroy", fillcolor=f"rgba(0,212,255,0.07)"), row=2, col=1)
        fig2.update_layout(**_chart_layout(480))
        st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CFG)

    with a4:
        _section_title("Consensus multi-temporel", C_GOLD, "⏱️")
        st.caption("Analyse simultanée sur 4 horizons — 5 min · 1 h · 1 j · 1 sem")
        with st.spinner("Analyse des 4 horizons temporels…"):
            cons = _multi_tf(p["symbol"])

        labels = {"5m":"5 minutes","1h":"1 heure","1d":"1 jour","1wk":"1 semaine"}
        m1,m2,m3,m4 = st.columns(4)
        for (tf, res), col in zip(cons.items(), [m1,m2,m3,m4]):
            color = C_GREEN if "Haussier" in str(res) else C_RED if "Baissier" in str(res) else C_GOLD
            tf_icon = {"5m":"⚡","1h":"🕐","1d":"📅","1wk":"🗓️"}.get(tf,"⏱️")
            with col:
                st.markdown(
                    f"<div style='background:{color}0e;border:1px solid {color}40;"
                    f"border-radius:14px;padding:18px 12px;text-align:center;"
                    f"box-shadow:0 0 15px {color}0f;transition:transform 0.2s;"
                    f"animation:fade-up 0.3s ease'>"
                    f"<div style='font-size:1.3rem;margin-bottom:6px'>{tf_icon}</div>"
                    f"<div style='color:{C_MUTED};font-size:0.70rem;margin-bottom:8px;"
                    f"text-transform:uppercase;letter-spacing:0.1em'>{labels.get(tf,tf)}</div>"
                    f"<div style='font-size:0.95rem;font-weight:800;color:{color};"
                    f"text-shadow:0 0 8px {color}55'>{res}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        bull = sum(1 for v in cons.values() if "Haussier" in str(v))
        bear = sum(1 for v in cons.values() if "Baissier" in str(v))
        st.markdown("<br>", unsafe_allow_html=True)
        if bull >= 3:
            st.success(f"✅ **CONSENSUS HAUSSIER** — {bull}/4 horizons alignés vers le haut")
        elif bear >= 3:
            st.error(f"⛔ **CONSENSUS BAISSIER** — {bear}/4 horizons alignés vers le bas")
        else:
            st.warning("⚠️ **Marché indécis** — attendez une confirmation plus claire")

    with a5:
        _section_title("Patterns de chandeliers", C_CYAN, "🔍")
        pts = _patterns(df)
        if pts:
            for pt in pts:
                color = C_GREEN if "↑" in pt["Signal"] or "achat" in pt["Signal"] else C_RED if "↓" in pt["Signal"] or "vente" in pt["Signal"] else C_GOLD
                st.markdown(
                    f"<div style='background:{color}0d;border-left:3px solid {color};"
                    f"border-radius:0 10px 10px 0;padding:10px 16px;margin-bottom:8px'>"
                    f"<span style='color:{C_MUTED};font-size:0.75rem'>{pt['Date']}</span>"
                    f" · <span style='font-weight:700;color:{C_WHITE}'>{pt['Pattern']}</span>"
                    f" → <span style='color:{color}'>{pt['Signal']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Aucun pattern significatif sur les 10 dernières bougies.")

    with a6:
        _section_title("Matrice de corrélations", C_PURPLE, "🔗")
        peers = ["BTC-USD","ETH-USD","^GSPC","GC=F","EURUSD=X","^FCHI"]
        sym_main = p["symbol"]
        corr_data: dict = {}
        if "Close" in df.columns and len(df) > 5:
            corr_data[sym_main] = df["Close"].copy()
        for peer_s in peers:
            if peer_s == sym_main:
                continue
            try:
                d_peer = smart_ohlcv(peer_s, p["periode"], "1d")
                if not d_peer.empty and "Close" in d_peer.columns:
                    if isinstance(d_peer.columns, pd.MultiIndex):
                        d_peer.columns = d_peer.columns.get_level_values(0)
                    if "Close" in d_peer.columns:
                        corr_data[peer_s] = d_peer["Close"].dropna()
            except Exception:
                pass
        if len(corr_data) > 1:
            corr_df = pd.DataFrame(corr_data).dropna()
            if len(corr_df) > 5:
                corr_mat = corr_df.corr()
                fig_c = px.imshow(corr_mat, text_auto=".2f",
                                  color_continuous_scale="RdBu_r",
                                  zmin=-1, zmax=1)
                fig_c.update_layout(**_chart_layout(420, "Corrélations"))
                fig_c.update_traces(textfont=dict(color=C_WHITE, size=11))
                st.plotly_chart(fig_c, use_container_width=True, config=PLOTLY_CFG)
            else:
                st.info("Pas assez de données communes pour la corrélation.")
        else:
            st.info("Données insuffisantes pour la matrice.")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 4 — SCREENER
# ══════════════════════════════════════════════════════════════════════════════

def tab_screener(p: dict) -> None:
    _section_title("Screener d'actifs", C_GOLD, "🔍")
    st.caption("Scannez une catégorie entière et filtrez par RSI + score de confiance.")

    cat = st.selectbox("Catégorie", list(ASSET_CATEGORIES.keys()), key="sc_cat")
    syms = _sym_list(cat)
    if not syms:
        st.warning("Aucun actif dans cette catégorie.")
        return

    c1, c2, c3 = st.columns(3)
    with c1: min_rsi = st.slider("RSI min", 0, 100, 25, key="sc_rmin")
    with c2: max_rsi = st.slider("RSI max", 0, 100, 75, key="sc_rmax")
    with c3: min_sc  = st.slider("Score min (%)", 0, 100, 50, key="sc_score")

    # Validation bornes RSI
    if min_rsi > max_rsi:
        st.warning(f"⚠️ RSI min ({min_rsi}) est supérieur à RSI max ({max_rsi}) — aucun actif ne sera trouvé. Ajustez les sliders.")

    if st.button("🚀 Lancer le scan", type="primary", disabled=(min_rsi > max_rsi)):
        results = []
        st.info(f"⚡ Scan parallèle de {len(syms)} actifs (Binance + Yahoo Finance)…")
        prog = st.progress(0)

        def _scan_one(sym: str):
            df = _load(sym, "1mo", "1d")
            if df.empty or len(df) < 20:
                return None
            last = df.iloc[-1]
            rsi  = float(last.get("RSI", 50))
            if np.isnan(rsi) or not (min_rsi <= rsi <= max_rsi):
                return None
            sc = 0
            if _scalar(last["Close"]) > _scalar(last["SMA20"]): sc += 25
            if _scalar(last["Close"]) > _scalar(last["SMA50"]): sc += 25
            if _scalar(last["MACD"])  > _scalar(last["Signal"]): sc += 25
            avgv = float(df["Volume"].rolling(20, min_periods=1).mean().iloc[-1]) if "Volume" in df.columns else 1.0
            if avgv != avgv or avgv <= 0: avgv = 1.0  # NaN / zéro guard
            vol_raw = last.get("Volume", 0)
            vol_v   = 0.0 if pd.isna(vol_raw) else float(vol_raw)
            if vol_v > avgv: sc += 25
            if sc < min_sc:
                return None
            prev = _scalar(df["Close"].iloc[-2]) if len(df) > 1 else _scalar(last["Close"])
            chg  = (_scalar(last["Close"]) - prev) / prev * 100 if prev else 0.0
            # Récupère le ticker live (Binance pour crypto, yf pour le reste)
            live = smart_price(sym)
            live_price = live.get("price", _scalar(last["Close"]))
            live_src   = live.get("source", "yf")
            return {
                "Symbole":  sym,
                "Prix":     _eur(live_price),
                "RSI":      f"{rsi:.1f}",
                "BB%":      f"{float(last.get('BB_pct',0.5))*100:.0f}",
                "Score":    f"{sc} %",
                "Variation":f"+{chg:.2f} %" if chg >= 0 else f"{chg:.2f} %",
                "Source":   live_src,
                "_score":   sc,
            }

        done = 0
        workers = min(len(syms), 10)
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(_scan_one, s): s for s in syms}
                for fut in _asc(futs, timeout=30):
                    done += 1
                    prog.progress(done / max(len(syms), 1))
                    try:
                        r = fut.result()
                        if r:
                            results.append(r)
                    except Exception:
                        pass
        finally:
            prog.empty()

        if results:
            df_r = pd.DataFrame(sorted(results, key=lambda x: -x["_score"]))
            st.success(f"✅ {len(df_r)} actif(s) détecté(s) sur {len(syms)} analysés")
            st.dataframe(
                df_r[["Symbole","Prix","RSI","BB%","Score","Variation","Source"]
                     ].style.map(_color_var, subset=["Variation"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.warning("Aucun actif ne correspond aux filtres.")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 5 — SIGNAUX
# ══════════════════════════════════════════════════════════════════════════════

def tab_signaux(p: dict) -> None:
    _section_title(f"Signaux — {p['symbol']}", C_CYAN, "📡")
    st.caption("🧪 Signaux générés à titre éducatif uniquement — aucune décision financière réelle.")

    df = _load(p["symbol"], p["periode"], p["intervalle"])
    if df.empty:
        st.error(f"⚠️ Données introuvables pour **{p['symbol']}** sur la période **{p['periode']}**. "
                 f"Essayez une période plus courte ou un autre symbole.")
        return

    last      = df.iloc[-1]
    close     = _scalar(last["Close"])
    rsi       = float(last.get("RSI", 50))
    if np.isnan(rsi): rsi = 50.0
    macd_b    = _scalar(last["MACD"]) > _scalar(last["Signal"])
    above_20  = close > _scalar(last["SMA20"])
    above_50  = close > _scalar(last["SMA50"])
    above_200 = close > _scalar(last.get("EMA200", last["Close"]))
    zscore    = float(last.get("ZScore", 0))
    if np.isnan(zscore): zscore = 0.0
    bb_pct    = float(last.get("BB_pct", 0.5))
    if np.isnan(bb_pct): bb_pct = 0.5
    mom5      = float(last.get("Mom5", 0))
    if np.isnan(mom5): mom5 = 0.0
    vol_ratio = float(last.get("VolRatio", 1.0))
    if np.isnan(vol_ratio): vol_ratio = 1.0

    # ── 6 conditions d'analyse ────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        col = C_GREEN if above_20 else C_RED
        _card("Tendance SMA20", "Au-dessus ↑" if above_20 else "En-dessous ↓",
              color=col, icon="📈")
    with c2:
        _card("MACD", "Haussier ↑" if macd_b else "Baissier ↓",
              color=C_GREEN if macd_b else C_RED, icon="⚡")
    with c3:
        if rsi > 70:   rt, rc = f"Suracheté {rsi:.0f}", C_RED
        elif rsi < 30: rt, rc = f"Survendu {rsi:.0f}", C_GREEN
        else:           rt, rc = f"Neutre {rsi:.0f}", C_CYAN
        _card("RSI", rt, color=rc, icon="🌀")

    c4, c5, c6 = st.columns(3)
    with c4:
        zc = C_GREEN if zscore < -1.5 else C_RED if zscore > 1.5 else C_GOLD
        zt = "Survendu Z" if zscore < -1.5 else "Suracheté Z" if zscore > 1.5 else "Neutre Z"
        _card(f"Z-Score ({zscore:.2f})", zt, color=zc, icon="🔢")
    with c5:
        bb_c = C_GREEN if bb_pct < 0.2 else C_RED if bb_pct > 0.8 else C_CYAN
        bb_t = "Bas BB ↑" if bb_pct < 0.2 else "Haut BB ↓" if bb_pct > 0.8 else f"BB {bb_pct*100:.0f}%"
        _card("Position Bollinger", bb_t, color=bb_c, icon="📐")
    with c6:
        vc = C_GREEN if vol_ratio > 1.5 else C_MUTED
        _card(f"Volume ratio", f"{vol_ratio:.2f}×",
              color=vc, icon="📦")

    # ── Score composite (6 conditions) ────────────────────────────────────────
    # RSI : survendu (<45) = haussier ; suracheté (>65) = baissier
    # Correction : ancienne logique RSI < 65 biaisait systématiquement vers ACHAT
    rsi_bull = rsi < 45                          # uniquement zone survendue/basse
    rsi_bear = rsi > 65                          # zone surachetée (seuil abaissé)
    bull = sum([
        above_20,
        macd_b,
        rsi_bull,
        zscore < -1.0,       # mean reversion haussier
        bb_pct < 0.3,        # prix bas dans les bandes
        mom5 > 0.0,          # momentum positif
    ])
    bear = sum([
        not above_20,
        not macd_b,
        rsi_bear,            # uniquement RSI > 70 comme signal baissier
        zscore > 1.0,
        bb_pct > 0.7,
        mom5 < 0.0,
    ])

    # Signal principal
    if bull >= 4:
        sig_color, sig_icon, sig_txt = C_GREEN, "🟢", f"SIGNAL ACHAT FORT ({bull}/6)"
    elif bull >= 3:
        sig_color, sig_icon, sig_txt = C_GREEN, "🟢", f"SIGNAL ACHAT ({bull}/6)"
    elif bear >= 4:
        sig_color, sig_icon, sig_txt = C_RED, "🔴", f"SIGNAL VENTE FORT ({bear}/6)"
    elif bear >= 3:
        sig_color, sig_icon, sig_txt = C_RED, "🔴", f"SIGNAL VENTE ({bear}/6)"
    else:
        sig_color, sig_icon, sig_txt = C_GOLD, "🟡", f"SIGNAL MIXTE {bull}/6"

    score_pct = int(bull / 6 * 100)
    st.markdown(
        f"<div class='zed-ring' style='background:{sig_color}0e;border:2px solid {sig_color}55;"
        f"border-radius:18px;padding:22px 28px;text-align:center;margin:18px 0;"
        f"box-shadow:0 0 35px {sig_color}1e,inset 0 1px 0 rgba(255,255,255,0.04)'>"
        f"<div style='font-family:Orbitron,sans-serif;font-size:1.55rem;"
        f"font-weight:900;color:{sig_color};text-shadow:0 0 18px {sig_color}88;letter-spacing:0.04em'>"
        f"{sig_icon} {sig_txt}</div>"
        f"<div style='margin:14px auto 6px;max-width:360px'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:0.72rem;color:{C_MUTED};margin-bottom:4px'>"
        f"<span>Score composite</span><span style='color:{sig_color};font-weight:700'>{bull}/6 haussières</span></div>"
        f"<div style='height:8px;background:{C_BORDER};border-radius:4px;overflow:hidden'>"
        f"<div style='width:{score_pct}%;height:100%;"
        f"background:linear-gradient(90deg,{sig_color}aa,{sig_color});"
        f"border-radius:4px;box-shadow:0 0 8px {sig_color}66;transition:width 0.5s'></div>"
        f"</div></div>"
        f"<div style='color:{C_MUTED};font-size:0.80rem;margin-top:4px'>"
        f"Z-Score: <span style='color:{C_CYAN}'>{zscore:+.2f}</span> · "
        f"Momentum 5j: <span style='color:{C_GREEN if mom5>0 else C_RED}'>{mom5*100:+.2f}%</span> · "
        f"BB%: <span style='color:{C_GOLD}'>{bb_pct*100:.0f}%</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Niveaux clés
    _section_title("Niveaux clés", C_GOLD, "🎯")
    sl  = close * (1 - p["risk_pct"] * 2)
    tp1 = close * (1 + p["risk_pct"] * 3)
    tp2 = close * (1 + p["risk_pct"] * 5)
    n1,n2,n3,n4 = st.columns(4)
    with n1: _card("Entrée", _eur(close), icon="📍")
    with n2: _card("Stop-Loss", _eur(sl), color=C_RED, icon="🛑")
    tp1_lbl = "+{:.0f}%".format(p["risk_pct"]*300)
    tp2_lbl = "+{:.0f}%".format(p["risk_pct"]*500)
    with n3: _card(f"TP1 ({tp1_lbl})", _eur(tp1), color=C_GREEN, icon="🎯")
    with n4: _card(f"TP2 ({tp2_lbl})", _eur(tp2), color=C_PURPLE, icon="💎")

    diff = close - sl
    units = min(p["capital"] * p["risk_pct"] / diff, p["capital"] * 0.40 / close) if diff > 0 and close > 0 else 0.0
    invested = units * close
    if invested >= 0.01:
        st.info(
            f"💶 Capital **{_eur(p['capital'])}** · Risque **{p['risk_pct']*100:.1f} %** "
            f"→ Taille position : **{units:.4f}** unités · Investi : **{_eur(invested)}**"
        )

    # Graphique niveaux
    fig_s = go.Figure()
    nb = min(len(df), 60)
    fig_s.add_trace(go.Scatter(x=df.index[-nb:], y=df["Close"].iloc[-nb:],
        line=dict(color=C_CYAN, width=2), name="Prix"))
    for lvl, col, nm in [(sl,C_RED,"Stop"),(close,C_GOLD,"Entrée"),(tp1,C_GREEN,"TP1"),(tp2,C_PURPLE,"TP2")]:
        fig_s.add_hline(y=lvl, line_dash="dash", line_color=col,
                        annotation_text=nm, annotation_font_color=col,
                        annotation_position="right")
    layout_s = _chart_layout(300, "Niveaux sur le graphique")
    layout_s["margin"]["r"] = 70
    fig_s.update_layout(**layout_s)
    st.plotly_chart(fig_s, use_container_width=True, config=PLOTLY_CFG)


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 6 — BOT
# ══════════════════════════════════════════════════════════════════════════════

def tab_bot(p: dict) -> None:
    _section_title("Bot de trading automatique", C_GREEN, "🤖")

    # ── Bandeau PAPER TRADING — ne peut pas être manqué ──────────────────────
    st.markdown(
        f"<div style='background:{C_ORANGE}35;border:2px solid {C_ORANGE};"
        f"border-radius:14px;padding:16px 22px;text-align:center;"
        f"margin-bottom:18px;box-shadow:0 0 18px {C_ORANGE}55'>"
        f"<div style='font-weight:900;font-size:1.1rem;color:{C_ORANGE};"
        f"letter-spacing:0.08em'>🧪 PAPER TRADING — SIMULATION UNIQUEMENT</div>"
        f"<div style='color:{C_TEXT};font-size:0.84rem;margin-top:6px;font-weight:600'>"
        f"Aucun ordre réel · Aucun vrai argent · Données de marché simulées en temps réel"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    capital = p["capital"]

    # ── Bandeau budget adaptatif ──────────────────────────────────────────────
    if capital <= 50:
        bc, bt = C_ORANGE, "⚡ MICRO-BUDGET (≤50€) · Risque 3% · 1 position max · Stop 20%"
    elif capital <= 200:
        bc, bt = C_CYAN, "💡 PETIT BUDGET (≤200€) · Risque 2% · 2 positions max · Stop 15%"
    else:
        bc, bt = C_GREEN, "🏆 BUDGET STANDARD (>200€) · Risque 1.5% · 3 positions max · Stop 12%"
    st.markdown(
        f"<div style='background:{bc}0d;border:1px solid {bc}44;"
        f"border-radius:12px;padding:12px 18px;color:{bc};"
        f"font-weight:700;font-size:0.88rem;margin-bottom:16px'>{bt}</div>",
        unsafe_allow_html=True,
    )

    # ── Initialisation session state ──────────────────────────────────────────
    if "bot_config" not in st.session_state:
        st.session_state.bot_config = create_default_config(
            _sym_list(p["categorie"]), capital
        )
        st.session_state["_bot_last_capital"] = capital
    elif st.session_state.get("_bot_last_capital") != capital:
        # Capital sidebar a changé → réinitialiser la config par défaut avec le nouveau capital
        st.session_state.bot_config = create_default_config(
            _sym_list(p["categorie"]), capital
        )
        st.session_state["_bot_last_capital"] = capital
    if "_zedicus_trading_bot" not in st.session_state:
        st.session_state._zedicus_trading_bot = None

    cfg = st.session_state.bot_config

    # ── Configuration ─────────────────────────────────────────────────────────
    with st.expander("⚙️ Configuration du bot", expanded=True):
        b1, b2, b3 = st.columns(3)
        with b1:
            # Lit depuis le capital partagé (synchronisé avec la sidebar)
            cap_def = max(10.0, min(float(st.session_state.get("shared_capital", capital)), 1_000.0))
            cap_cfg = st.number_input("Capital (€)", 10.0, 1_000.0, cap_def, 10.0, key="bot_cap",
                                      help="Synchronisé avec la sidebar")
        with b2:
            rdef = round(float(getattr(cfg, "risk_pct_per_trade", 0.02)) * 100, 1)
            rdef = max(0.5, min(5.0, rdef))
            risk_cfg = st.slider("Risque / trade (%)", 0.5, 5.0, rdef, 0.5, key="bot_rsk")
        with b3:
            mp = max(1, min(5, int(getattr(cfg, "max_positions", 1))))
            max_pos = st.number_input("Positions max", 1, 5, mp, key="bot_mp")

        syms_all = _sym_list(p["categorie"])
        default_syms = syms_all[:min(2, len(syms_all))]
        syms_sel = st.multiselect(
            "Actifs à trader", syms_all,
            default=default_syms, key="bot_sym",
        )

        show_adv = st.checkbox("⚙️ Paramètres avancés", value=False, key="bot_adv")
        if show_adv:
            adv1, adv2 = st.columns(2)
            with adv1:
                raw_conf = int(round(getattr(cfg, "min_confidence", 0.62) * 100 / 5.0) * 5)
                min_conf = st.slider("Confiance min (%)", 50, 95,
                                     max(50, min(95, raw_conf)), 5, key="bot_conf")
                raw_poll = max(15, min(300, int(getattr(cfg, "poll_interval_sec", 60))))
                poll_int = st.slider("Intervalle poll (s)", 15, 300,
                                     raw_poll, 15, key="bot_poll")
            with adv2:
                raw_dd = max(5, min(30, int(round(getattr(cfg, "max_drawdown_pct", 0.12) * 100))))
                max_dd = st.slider("Drawdown max (%)", 5, 30, raw_dd, 1, key="bot_dd")
                strats = st.multiselect(
                    "Stratégies activées",
                    ["momentum", "breakout", "mean_reversion", "trend"],
                    default=getattr(cfg, "strategies_enabled",
                                    ["momentum", "breakout", "mean_reversion", "trend"]),
                    key="bot_strats",
                )

            st.markdown(f"<div style='color:{C_GOLD};font-size:0.75rem;font-weight:700;"
                        f"margin:10px 0 4px'>⚙️ Multiplicateurs ATR (Stop / Take profit / Trailing)</div>",
                        unsafe_allow_html=True)
            atr1, atr2, atr3 = st.columns(3)
            with atr1:
                sl_atr = st.slider(
                    "SL × ATR", 0.5, 5.0,
                    float(round(getattr(cfg, "sl_atr_mult", 2.0), 1)), 0.5,
                    key="bot_sl_atr",
                    help="Stop-loss = entrée − SL×ATR(14). Plus petit = risque réduit."
                )
            with atr2:
                tp_atr = st.slider(
                    "TP × ATR", 0.5, 8.0,
                    float(round(getattr(cfg, "tp_atr_mult", 3.0), 1)), 0.5,
                    key="bot_tp_atr",
                    help="Take-profit = entrée + TP×ATR(14). Ratio R/R = TP/SL."
                )
            with atr3:
                tr_atr = st.slider(
                    "Trailing × ATR", 0.5, 4.0,
                    float(round(getattr(cfg, "trailing_atr_mult", 1.5), 1)), 0.5,
                    key="bot_tr_atr",
                    help="Trailing stop remonte avec le prix (protection gains)."
                )
            st.caption(
                f"📐 R/R actuel : **{tp_atr/sl_atr:.1f}:1** "
                f"(TP={tp_atr}×ATR / SL={sl_atr}×ATR)"
            )
        else:
            min_conf = int(round(getattr(cfg, "min_confidence", 0.62) * 100 / 5.0) * 5)
            poll_int = max(15, min(300, int(getattr(cfg, "poll_interval_sec", 60))))
            max_dd   = max(5, min(30, int(round(getattr(cfg, "max_drawdown_pct", 0.12) * 100))))
            strats   = getattr(cfg, "strategies_enabled",
                               ["momentum", "breakout", "mean_reversion", "trend"])
            sl_atr   = float(getattr(cfg, "sl_atr_mult", 2.0))
            tp_atr   = float(getattr(cfg, "tp_atr_mult", 3.0))
            tr_atr   = float(getattr(cfg, "trailing_atr_mult", 1.5))

        if st.button("💾 Appliquer la configuration", type="primary", key="bot_apply"):
            chosen = syms_sel if syms_sel else syms_all[:1]
            new_cfg = BotConfig(
                symbols=chosen,
                capital=float(cap_cfg),
                risk_pct_per_trade=risk_cfg / 100,
                max_positions=int(max_pos),
                max_drawdown_pct=max_dd / 100,
                min_confidence=min_conf / 100,
                poll_interval_sec=int(poll_int),
                strategies_enabled=strats,
                use_stop_loss=True,
                use_take_profit=True,
                trailing_stop=True,
                filter_macro_events=True,
                broker="paper",
                sl_atr_mult=sl_atr,
                tp_atr_mult=tp_atr,
                trailing_atr_mult=tr_atr,
            )
            st.session_state.bot_config = new_cfg
            # Si bot actif → reconfigurer à la volée
            bot_live = st.session_state.get("_zedicus_trading_bot")
            if bot_live and bot_live.status == BotStatus.RUNNING:
                bot_live.stop()
                st.session_state._zedicus_trading_bot = None
                st.warning("⚠️ Bot redémarré avec la nouvelle configuration")
            st.success("✅ Configuration enregistrée")
            st.rerun()

    # ── Contrôles ─────────────────────────────────────────────────────────────
    _section_title("Contrôles", C_CYAN, "🎮")
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
    with ctrl1:
        if st.button("▶️ Démarrer", type="primary", use_container_width=True, key="bot_start"):
            try:
                new_bot = TradingBot(st.session_state.bot_config)
                new_bot.start()
                st.session_state._zedicus_trading_bot = new_bot
                st.success("✅ Bot démarré ! Il tourne en arrière-plan.")
            except Exception as e:
                st.error(f"Erreur démarrage : {e}")
    _bot_active = bool(st.session_state.get("_zedicus_trading_bot"))
    with ctrl2:
        if st.button("⏸️ Pause", use_container_width=True, key="bot_pause",
                     disabled=not _bot_active):
            bot_live = st.session_state.get("_zedicus_trading_bot")
            if bot_live:
                try:
                    bot_live.pause()
                    st.warning("⏸️ Bot en pause — positions maintenues")
                except Exception as e:
                    st.error(str(e))
    with ctrl3:
        if st.button("▶ Reprendre", use_container_width=True, key="bot_resume",
                     disabled=not _bot_active):
            bot_live = st.session_state.get("_zedicus_trading_bot")
            if bot_live:
                try:
                    bot_live.resume()
                    st.success("▶ Bot repris")
                except Exception as e:
                    st.error(str(e))
    with ctrl4:
        if st.button("⏹️ Arrêter", use_container_width=True, key="bot_stop",
                     disabled=not _bot_active):
            bot_live = st.session_state.get("_zedicus_trading_bot")
            if bot_live:
                try:
                    bot_live.stop()
                    st.session_state._zedicus_trading_bot = None
                    st.info("⏹️ Bot arrêté proprement")
                except Exception as e:
                    st.error(str(e))

    # ── État du bot ────────────────────────────────────────────────────────────
    bot = st.session_state.get("_zedicus_trading_bot")

    # Bandeau statut
    if bot:
        try:
            sv = bot.status.value
        except Exception:
            sv = "stopped"
        smap = {
            "running": (C_GREEN, "🟢 EN COURS — analyse les marchés"),
            "paused":  (C_GOLD,  "🟡 EN PAUSE — positions maintenues"),
            "stopped": (C_RED,   "🔴 ARRÊTÉ"),
            "error":   (C_RED,   "🔴 ERREUR — vérifiez les logs"),
        }
        status_col, st_txt = smap.get(sv, (C_MUTED, "⚫ INCONNU"))
        st.markdown(
            f"<div style='background:{status_col}12;border:1px solid {status_col}44;"
            f"border-radius:12px;padding:10px 18px;color:{status_col};"
            f"font-weight:700;font-size:0.9rem;margin:12px 0;"
            f"display:flex;align-items:center;gap:10px;"
            f"box-shadow:0 0 14px {status_col}18'>{st_txt}</div>",
            unsafe_allow_html=True,
        )

        # ── Métriques live ───────────────────────────────────────────────────
        _section_title("Tableau de bord live", C_GOLD, "📊")
        try:
            bst = bot.get_status()
            eq  = bst.get("equity", capital)
            pnl_tot = bst.get("total_pnl", 0)
            dd_pct  = bst.get("drawdown_pct", 0)
            bm1, bm2, bm3, bm4 = st.columns(4)
            with bm1:
                _card("Équité", _eur(eq),
                      f"{(eq - capital) / capital * 100:+.2f}% vs initial",
                      color=C_GREEN if eq >= capital else C_RED, icon="💰")
            with bm2:
                _card("PnL total", _eur(pnl_tot, sign=True),
                      color=C_GREEN if pnl_tot >= 0 else C_RED, icon="📈")
            with bm3:
                dd_col = C_RED if dd_pct > 10 else C_GOLD if dd_pct > 5 else C_GREEN
                _card("Drawdown", f"{dd_pct:.1f}%",
                      f"Max autorisé : {getattr(bot.config,'max_drawdown_pct',0.12)*100:.0f}%",
                      color=dd_col, icon="⬇️")
            with bm4:
                n_pos = bst.get("open_positions", 0)
                max_p = getattr(bot.config, "max_positions", 3)
                _card("Positions ouvertes", f"{n_pos} / {max_p}",
                      color=C_CYAN if n_pos < max_p else C_GOLD, icon="📋")
        except Exception:
            pass

        # ── Métriques de performance (si trades effectués) ───────────────────
        try:
            perf = bot.get_performance_metrics()
            n_tr = perf.get("total_trades", 0)
            if n_tr > 0:
                _section_title(f"Performance — {n_tr} trade(s)", C_PURPLE, "🏆")
                pm1, pm2, pm3, pm4 = st.columns(4)
                with pm1:
                    _card("Trades", str(n_tr), color=C_CYAN, icon="⚡")
                with pm2:
                    wr = perf.get("win_rate", 0)  # déjà en % (ex: 60.0)
                    _card("Win rate", f"{wr:.1f}%",
                          color=C_GREEN if wr > 50 else C_RED, icon="🎯")
                with pm3:
                    pf = perf.get("profit_factor", 0)
                    _card("Profit factor", f"{pf:.2f}",
                          color=C_GREEN if pf > 1 else C_RED, icon="💎")
                with pm4:
                    sh = perf.get("sharpe", 0)
                    _card("Sharpe", f"{sh:.2f}",
                          color=C_GREEN if sh > 1 else C_GOLD, icon="📊")
        except Exception:
            pass

        # ── Signal live + Panel d'indications clair ─────────────────────────
        _section_title(f"📡 Signal temps réel — {p['symbol']}", C_CYAN, "⚡")
        st.caption("⚠️ Indicatif uniquement — ne constitue pas un conseil en investissement")
        try:
            live_price_data = smart_price(p["symbol"])
            df_l = _load(p["symbol"], "5d", "15m")
            if not df_l.empty:
                ll      = df_l.iloc[-1]
                rsi_l   = float(ll.get("RSI", 50) or 50)
                if rsi_l != rsi_l: rsi_l = 50.0
                mb      = _scalar(ll.get("MACD", 0)) > _scalar(ll.get("Signal", 0))
                sma20_bull = _scalar(ll.get("Close", 0)) > _scalar(ll.get("SMA20", 0))
                ep_live = (live_price_data.get("price", _scalar(ll["Close"]))
                           if live_price_data else _scalar(ll["Close"]))
                chg_live = live_price_data.get("change_pct", 0) if live_price_data else 0.0
                src_live = live_price_data.get("source", "yf") if live_price_data else "yf"
                _z_raw   = ll.get("ZScore", 0)
                zscore_l = 0.0 if (_z_raw is None or (isinstance(_z_raw, float) and np.isnan(_z_raw))) else float(_z_raw)
                _bb_raw  = ll.get("BB_pct", 0.5)
                bb_pct_l = 0.5 if (_bb_raw is None or (isinstance(_bb_raw, float) and np.isnan(_bb_raw))) else float(_bb_raw)
                atr_l    = _scalar(ll.get("ATR", ep_live * 0.02))

                # Score d'achat / vente sur 5 conditions
                bull_sigs = [
                    (rsi_l < 65 and mb,       "MACD haussier + RSI OK"),
                    (zscore_l < -0.5,          f"Z-Score survendu ({zscore_l:+.2f})"),
                    (bb_pct_l < 0.4,           f"Bas des Bollinger ({bb_pct_l*100:.0f}%)"),
                    (chg_live > 0,             f"Momentum positif (+{chg_live:.2f}%)"),
                    (sma20_bull,               "Prix au-dessus SMA20"),
                ]
                bear_sigs = [
                    (rsi_l > 70,               f"RSI suracheté ({rsi_l:.0f})"),
                    (not mb,                   "MACD baissier"),
                    (zscore_l > 0.5,           f"Z-Score suracheté ({zscore_l:+.2f})"),
                    (bb_pct_l > 0.6,           f"Haut des Bollinger ({bb_pct_l*100:.0f}%)"),
                    (chg_live < -0.5,          f"Momentum négatif ({chg_live:.2f}%)"),
                ]
                n_bull = sum(1 for ok, _ in bull_sigs if ok)
                n_bear = sum(1 for ok, _ in bear_sigs if ok)

                if n_bull >= 3 and n_bear <= 1:
                    sig_color, sig_txt, sig_emoji = C_GREEN, "ACHAT (indicatif)", "🟢"
                    sig_msg = "Plusieurs conditions favorables alignées — signal haussier."
                elif n_bear >= 3 and n_bull <= 1:
                    sig_color, sig_txt, sig_emoji = C_RED, "VENTE / SORTIE (indicatif)", "🔴"
                    sig_msg = "Pression vendeuse détectée — prudence ou sortie de position."
                elif n_bull >= 2:
                    sig_color, sig_txt, sig_emoji = C_GREEN, "LÉGÈREMENT HAUSSIER", "🟡"
                    sig_msg = "Quelques signaux positifs — attendez une confirmation."
                else:
                    sig_color, sig_txt, sig_emoji = C_GOLD, "NEUTRE — ATTENDRE", "⏳"
                    sig_msg = "Signal mixte — pas d'opportunité claire. Patience."

                # Grand panneau de décision
                st.markdown(
                    f"<div style='background:{sig_color}12;border:2.5px solid {sig_color};"
                    f"border-radius:18px;padding:20px 28px;text-align:center;"
                    f"margin:12px 0;box-shadow:0 0 30px {sig_color}22'>"
                    f"<div style='font-size:2.5rem;margin-bottom:6px'>{sig_emoji}</div>"
                    f"<div style='font-family:Orbitron,\"Courier New\",monospace;font-size:1.2rem;"
                    f"font-weight:900;color:{sig_color};letter-spacing:0.05em'>{sig_txt}</div>"
                    f"<div style='color:{C_TEXT};font-size:0.85rem;margin-top:8px'>{sig_msg}</div>"
                    f"<div style='color:{C_MUTED};font-size:0.75rem;margin-top:4px'>"
                    f"Score haussier : {n_bull}/5 · Score baissier : {n_bear}/5"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

                # Prix, ATR et niveaux TP/SL suggérés
                s1, s2, s3, s4 = st.columns(4)
                with s1: _card(f"Prix [{src_live}]", f"{ep_live:,.4f}",
                               f"{chg_live:+.2f}% / 24h",
                               color=C_GREEN if chg_live >= 0 else C_RED, icon="💲")
                with s2: _card("RSI 15m", f"{rsi_l:.1f}",
                               "Suracheté" if rsi_l > 70 else "Survendu" if rsi_l < 30 else "Zone neutre",
                               color=C_RED if rsi_l > 70 else C_GREEN if rsi_l < 30 else C_CYAN, icon="📊")
                with s3:
                    sl_sugg = ep_live * (1 - atr_l / ep_live * 2) if ep_live > 0 and atr_l > 0 else ep_live * 0.98
                    _card("Stop-Loss suggéré", f"{sl_sugg:,.4f}",
                          f"−{abs(sl_sugg - ep_live) / ep_live * 100:.2f}%",
                          color=C_RED, icon="🛑")
                with s4:
                    tp_sugg = ep_live * (1 + atr_l / ep_live * 3) if ep_live > 0 and atr_l > 0 else ep_live * 1.03
                    _card("Take-Profit suggéré", f"{tp_sugg:,.4f}",
                          f"+{abs(tp_sugg - ep_live) / ep_live * 100:.2f}%",
                          color=C_GREEN, icon="🎯")

                # Détail des conditions actives
                with st.expander("🔍 Détail des signaux", expanded=False):
                    col_b, col_s = st.columns(2)
                    with col_b:
                        st.markdown(f"**🟢 Signaux ACHAT ({n_bull}/5)**")
                        for ok, lbl in bull_sigs:
                            icon = "✅" if ok else "❌"
                            color_txt = C_GREEN if ok else C_MUTED
                            st.markdown(
                                f"<div style='color:{color_txt};font-size:0.82rem;padding:3px 0'>"
                                f"{icon} {lbl}</div>",
                                unsafe_allow_html=True,
                            )
                    with col_s:
                        st.markdown(f"**🔴 Signaux VENTE ({n_bear}/5)**")
                        for ok, lbl in bear_sigs:
                            icon = "⚠️" if ok else "✅"
                            color_txt = C_RED if ok else C_MUTED
                            st.markdown(
                                f"<div style='color:{color_txt};font-size:0.82rem;padding:3px 0'>"
                                f"{icon} {lbl}</div>",
                                unsafe_allow_html=True,
                            )

        except Exception:
            st.info("Signal live indisponible pour cet actif.")

        # ── Positions ouvertes ────────────────────────────────────────────────
        _section_title("Positions ouvertes", C_CYAN, "📋")
        try:
            positions = bot.get_positions()
            if positions:
                rows = []
                for pos in positions:
                    pnl_v  = float(getattr(pos, "pnl", 0))
                    pnl_pc = float(getattr(pos, "pnl_pct", 0)) * 100
                    sl_v2  = float(getattr(pos, "stop_loss", 0))
                    tp_v2  = float(getattr(pos, "take_profit", 0))
                    strat  = getattr(pos, "strategy_name", "—")
                    rows.append({
                        "Symbole":   getattr(pos, "symbol", ""),
                        "Côté":      "🟢 LONG" if getattr(pos, "side", "") == "buy" else "🔴 SHORT",
                        "Qté":       f"{float(getattr(pos,'quantity',0)):.4f}",
                        "Entrée":    _eur(float(getattr(pos, "entry_price", 0))),
                        "Actuel":    _eur(float(getattr(pos, "current_price", 0))),
                        "PnL":       f"{'+' if pnl_v>=0 else ''}{pnl_v:.2f}€ ({pnl_pc:+.2f}%)",
                        "Stop-Loss": _eur(sl_v2),
                        "Take-Profit": _eur(tp_v2),
                        "Stratégie": strat,
                    })
                df_pos = pd.DataFrame(rows)
                st.dataframe(df_pos.style.map(_color_var, subset=["PnL"]),
                             use_container_width=True, hide_index=True)
            else:
                st.info("🔍 Aucune position ouverte — le bot analyse les marchés.")
        except Exception as e:
            st.warning(f"Erreur positions : {e}")

        # ── Historique des trades ─────────────────────────────────────────────
        _section_title("Historique des trades", C_GOLD, "📜")
        try:
            history = bot.get_trade_history()
            if history:
                hrows = []
                for t in history:
                    pnl_v = float(getattr(t, "pnl", 0))
                    reason = getattr(t, "exit_reason", "—")
                    reason_icon = {"TP": "🎯", "SL": "🛑", "TRAILING": "🔄", "MANUAL": "✋"}.get(reason, "⚪")
                    hrows.append({
                        "Date":      str(getattr(t, "closed_at", ""))[:16].replace("T", " "),
                        "Symbole":   getattr(t, "symbol", ""),
                        "Côté":      "🟢" if getattr(t, "side", "") == "buy" else "🔴",
                        "Durée":     f"{getattr(t,'duration_min',0):.0f} min",
                        "Entrée":    _eur(float(getattr(t, "entry_price", 0))),
                        "Sortie":    _eur(float(getattr(t, "exit_price", 0))),
                        "PnL":       f"{'+' if pnl_v>=0 else ''}{pnl_v:.2f}€",
                        "Raison":    f"{reason_icon} {reason}",
                        "Stratégie": getattr(t, "strategy_name", "—"),
                    })
                st.dataframe(pd.DataFrame(hrows).style.map(_color_var, subset=["PnL"]),
                             use_container_width=True, hide_index=True)

                # Courbe de capital — utiliser le capital initial du bot, pas le sidebar courant
                bot_initial = getattr(bot, "_initial_capital", capital)
                pnls   = [float(getattr(t, "pnl", 0)) for t in history]
                equity = list(np.cumsum(pnls) + bot_initial)
                fc_eq  = C_GREEN if equity[-1] >= bot_initial else C_RED
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(
                    y=equity, mode="lines+markers",
                    line=dict(color=fc_eq, width=2.5),
                    fill="tozeroy",
                    fillcolor=f"rgba(0,255,136,0.08)" if fc_eq == C_GREEN else f"rgba(255,51,102,0.08)",
                    marker=dict(size=6, color=C_GOLD, line=dict(color=C_BG, width=1)),
                    hovertemplate="Trade #%{x}<br>Équité : %{y:.2f}€<extra></extra>",
                    name="Équité",
                ))
                fig_eq.add_hline(y=bot_initial, line_dash="dot", line_color=C_SILVER,
                                 annotation_text=f"Capital initial {_eur(bot_initial)}",
                                 annotation_font_color=C_SILVER)
                fig_eq.update_layout(**_chart_layout(300, "Courbe de capital du bot (€)"))
                st.plotly_chart(fig_eq, use_container_width=True, config=PLOTLY_CFG)

                # Stats rapides en 3 cols
                pnls_pos = [x for x in pnls if x > 0]
                pnls_neg = [x for x in pnls if x <= 0]
                qq1, qq2, qq3 = st.columns(3)
                with qq1:
                    _card("Meilleur trade",
                          _eur(max(pnls_pos)) if pnls_pos else "—",
                          color=C_GREEN, icon="🏆")
                with qq2:
                    _card("Pire trade",
                          _eur(min(pnls_neg)) if pnls_neg else "—",
                          color=C_RED, icon="💔")
                with qq3:
                    avg = float(np.mean(pnls)) if pnls else 0.0
                    _card("Moyenne / trade",
                          _eur(avg, sign=True),
                          color=C_GREEN if avg >= 0 else C_RED, icon="📐")
            else:
                st.markdown(
                    f"<div style='background:{C_CARD};border:1px dashed {C_GOLD}22;"
                    f"border-radius:12px;padding:20px;text-align:center;color:{C_MUTED}'>"
                    f"⏳ Aucun trade fermé pour l'instant.<br>"
                    f"<span style='font-size:0.8rem'>Le bot génère un signal dès que les conditions "
                    f"de confiance ({getattr(bot.config,'min_confidence',0.62)*100:.0f}%) sont atteintes.</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.warning(f"Erreur historique : {e}")

    else:
        # Bot non démarré
        st.markdown(
            f"<div style='background:{C_CARD};border:1px dashed {C_CYAN}33;"
            f"border-radius:16px;padding:32px;text-align:center'>"
            f"<div style='font-size:3rem;margin-bottom:12px'>🤖</div>"
            f"<div style='color:{C_WHITE};font-weight:700;font-size:1.1rem;margin-bottom:8px'>"
            f"Bot de trading prêt à démarrer</div>"
            f"<div style='color:{C_MUTED};font-size:0.85rem;line-height:1.7;max-width:500px;margin:0 auto'>"
            f"1. Configurez le capital, le risque et les actifs ci-dessus<br>"
            f"2. Cliquez sur <b style='color:{C_GREEN}'>▶️ Démarrer</b><br>"
            f"3. Le bot tourne en arrière-plan et génère des signaux toutes les "
            f"{getattr(cfg,'poll_interval_sec',60)}s<br>"
            f"4. <b style='color:{C_ORANGE}'>Paper trading uniquement</b> — aucun vrai ordre exécuté"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        # Afficher quand même le signal live même si le bot est arrêté
        _section_title(f"Signal live — {p['symbol']} (sans bot actif)", C_MUTED, "📡")
        try:
            df_l = _load(p["symbol"], "5d", "15m")
            if not df_l.empty:
                ll    = df_l.iloc[-1]
                live  = smart_price(p["symbol"])
                ep    = live.get("price", _scalar(ll["Close"])) if live else _scalar(ll["Close"])
                chg   = live.get("change_pct", 0) if live else 0.0
                rsi_l = float(ll.get("RSI", 50))
                if np.isnan(rsi_l): rsi_l = 50.0
                src   = live.get("source", "yf") if live else "yf"
                sc1, sc2, sc3 = st.columns(3)
                with sc1: _card(f"Prix [{src}]", _eur(ep), f"{chg:+.2f}%",
                                color=C_GREEN if chg >= 0 else C_RED, icon="💲")
                with sc2:
                    rsi_col = C_RED if rsi_l > 70 else C_GREEN if rsi_l < 30 else C_CYAN
                    _card("RSI 15m", f"{rsi_l:.1f}", color=rsi_col, icon="📊")
                with sc3:
                    zr = float(ll.get("ZScore", 0))
                    if zr != zr: zr = 0.0
                    _card("Z-Score", f"{zr:+.2f}", color=C_GOLD, icon="🔢")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 7 — PORTEFEUILLE
# ══════════════════════════════════════════════════════════════════════════════

def tab_portefeuille(p: dict) -> None:
    _section_title("Mon portefeuille", C_GOLD, "💼")

    # Intégration avec le bot actif
    bot_active = st.session_state.get("_zedicus_trading_bot")
    if bot_active is not None:
        try:
            bst  = bot_active.get_status()
            perf = bot_active.get_performance_metrics()
            b1, b2, b3, b4 = st.columns(4)
            with b1: _card("Équité", _eur(bst.get("equity", p["capital"])), color=C_GOLD, icon="💰")
            with b2: _card("Cash", _eur(bst.get("cash", p["capital"])), color=C_SILVER, icon="💵")
            with b3: _card("PnL total", _eur(bst.get("total_pnl", 0), sign=True),
                            color=C_GREEN if bst.get("total_pnl", 0) >= 0 else C_RED, icon="📈")
            with b4: _card("Drawdown", f"{bst.get('drawdown_pct', 0):.1f}%",
                            color=C_RED if bst.get("drawdown_pct", 0) > 10 else C_GOLD, icon="⬇️")
        except Exception as e:
            st.warning(f"Bot status: {e}")

    try:
        pm = PortfolioManager()
        portfolio = pm.get_portfolio()
    except Exception:
        portfolio = None

    if portfolio and hasattr(portfolio, "positions") and portfolio.positions:
        positions = portfolio.positions
        tv  = sum(float(getattr(x,"value",0))          for x in positions)
        tp  = sum(float(getattr(x,"unrealized_pnl",0)) for x in positions)
        tc  = tv - tp
        p1,p2,p3 = st.columns(3)
        with p1: _card("Valeur totale", _eur(tv), color=C_GOLD, icon="💎")
        with p2: _card("PnL non réalisé", _eur(tp, sign=True),
                       color=C_GREEN if tp>=0 else C_RED, icon="📈")
        with p3: _card("Coût total", _eur(tc), color=C_SILVER, icon="💵")

        rows = [{
            "Actif":  getattr(x,"symbol",""),
            "Qté":    f"{float(getattr(x,'quantity',0)):.4f}",
            "P. moy": _eur(float(getattr(x,"avg_price",0))),
            "Valeur": _eur(float(getattr(x,"value",0))),
            "PnL":    _eur(float(getattr(x,"unrealized_pnl",0)), sign=True),
            "Poids":  f"{float(getattr(x,'weight',0))*100:.1f}%",
        } for x in positions]
        st.dataframe(
            pd.DataFrame(rows).style.map(_color_var, subset=["PnL"]),
            use_container_width=True, hide_index=True,
        )
        if len(positions) > 1:
            vals  = [float(getattr(x,"value",0)) for x in positions]
            names = [getattr(x,"symbol","") for x in positions]
            fig_p = go.Figure(go.Pie(
                labels=names, values=vals, hole=0.45,
                marker=dict(colors=[C_CYAN,C_GOLD,C_GREEN,C_PURPLE,C_ORANGE],
                            line=dict(color=C_BG, width=2)),
            ))
            fig_p.update_layout(**_chart_layout(340, "Répartition du portefeuille"))
            st.plotly_chart(fig_p, use_container_width=True, config=PLOTLY_CFG)
    else:
        st.markdown(
            f"<div style='background:{C_CARD};border:1px dashed {C_GOLD}33;"
            f"border-radius:14px;padding:28px;text-align:center;color:{C_MUTED}'>"
            f"💼 Aucune position en portefeuille.<br>"
            f"<span style='font-size:0.82rem'>Démarrez le bot pour commencer à accumuler des positions.</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 8 — RISQUE
# ══════════════════════════════════════════════════════════════════════════════

def tab_risque(p: dict) -> None:
    _section_title("Gestion du risque", C_RED, "⚠️")
    st.caption("🧪 Simulation uniquement — les calculs sont éducatifs, aucun trade réel n'est exécuté.")

    cap = p["capital"]
    r1,r2,r3 = st.columns(3)
    with r1: _card("Capital total", _eur(cap), color=C_GOLD, icon="💰")
    with r2: _card("Risque / trade", _eur(cap * p["risk_pct"]), color=C_ORANGE, icon="🎯")
    with r3: _card("Perte max (20%)", _eur(cap * 0.20), color=C_RED, icon="🛑")

    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Calculateur de position", C_CYAN, "🧮")

    df = _load(p["symbol"], "1mo", "1d")
    # Capital synchronisé avec la sidebar
    cap_r = max(10.0, min(float(st.session_state.get("shared_capital", cap)), 1_000.0))
    c_in  = st.number_input("Capital (€)", 10.0, 1_000.0, cap_r, 10.0, key="rc_cap",
                            help="Synchronisé avec la sidebar")
    _rsk_default = max(0.5, min(5.0, round(p["risk_pct"] * 100, 1)))
    rsk   = st.slider("% à risquer", 0.5, 5.0, _rsk_default, 0.5, key="rc_rsk")

    if not df.empty:
        lc   = _scalar(df["Close"].iloc[-1])
        atr  = _scalar(df["ATR"].iloc[-1]) if "ATR" in df.columns else lc * 0.02
        if np.isnan(atr) or atr <= 0: atr = lc * 0.02
        sl_p = lc - atr
        ra   = c_in * rsk / 100
        diff = lc - sl_p
        units = min(ra / diff, (c_in * 0.40) / lc) if diff > 0 and lc > 0 else 0.0
        inv   = units * lc

        k1,k2,k3,k4 = st.columns(4)
        with k1: _card("Prix actuel", _eur(lc), icon="💲")
        with k2: _card("Stop-Loss (ATR)", _eur(sl_p), color=C_RED, icon="🛑")
        with k3: _card("À risquer", _eur(ra), color=C_ORANGE, icon="⚡")
        with k4: _card("Unités", f"{units:.4f}", color=C_GREEN, icon="📦")

        if inv >= 0.01:
            pct = inv/c_in*100
            sl_dist = lc - sl_p
            tp_dist = atr * 2
            rr  = tp_dist / sl_dist if sl_dist > 0 else 2.0
            st.success(
                f"💶 Investir **{_eur(inv)}** ({pct:.1f}% du capital) "
                f"pour **{units:.4f}** unités · R/R ≈ 1:{rr:.1f}"
            )
        else:
            st.error("Capital insuffisant pour cette position — augmentez le capital ou réduisez le risque.")

        tp = lc + atr * 2
        fig_rr = go.Figure()
        nb = min(len(df), 30)
        fig_rr.add_trace(go.Scatter(x=df.index[-nb:], y=df["Close"].iloc[-nb:],
            line=dict(color=C_CYAN, width=2), name="Prix"))
        for lvl, col, nm in [(sl_p,C_RED,"Stop-Loss"),(lc,C_GOLD,"Entrée"),(tp,C_GREEN,"TP estimé")]:
            fig_rr.add_hline(y=lvl, line_dash="dash", line_color=col,
                             annotation_text=nm, annotation_font_color=col,
                             annotation_position="right")
        layout_rr = _chart_layout(280, "Risk / Reward")
        layout_rr["margin"]["r"] = 80
        fig_rr.update_layout(**layout_rr)
        st.plotly_chart(fig_rr, use_container_width=True, config=PLOTLY_CFG)

    st.markdown("<hr>", unsafe_allow_html=True)
    # ── Données macro FRED pour le contexte de risque ─────────────────────────
    _section_title("Contexte macro (FRED)", C_RED, "🏛️")
    with st.expander("📊 Courbes macro-économiques US (Fed, CPI, chômage)", expanded=False):
        fred_pairs = [
            ("Fed Funds Rate", "FEDFUNDS"),
            ("CPI (YoY)",      "CPIAUCSL"),
            ("Spread 10-2Y",   "T10Y2Y"),
        ]
        for (fname, fid) in fred_pairs:
            try:
                s = fred_series(fid, limit=60)
                if not s.empty:
                    last_val = float(s.iloc[-1])
                    fc = C_RED if (fid == "FEDFUNDS" and last_val > 4) or \
                                  (fid == "T10Y2Y" and last_val < 0) else C_GREEN
                    _card(fname, f"{last_val:.2f} %", color=fc, icon="📊")
                    fig_f = go.Figure(go.Scatter(
                        x=list(s.index), y=s.values,
                        line=dict(color=fc, width=2.5),
                        fill="tozeroy",
                        fillcolor=f"rgba(255,51,102,0.08)" if fc == C_RED else f"rgba(0,255,136,0.08)",
                        hovertemplate="%{y:.2f}<extra></extra>",
                    ))
                    fig_f.update_layout(**_chart_layout(220, fname))
                    st.plotly_chart(fig_f, use_container_width=True, config=PLOTLY_CFG)
            except Exception:
                pass

    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Règles d'or", C_GOLD, "📋")
    rules = [
        (C_RED,    "Ne risquez jamais plus de 2-3% par trade"),
        (C_ORANGE, "Max 40% du capital sur une seule position"),
        (C_GOLD,   "Posez votre stop-loss AVANT d'entrer"),
        (C_GREEN,  "Diversifiez — ne misez pas tout sur un actif"),
        (C_CYAN,   "Micro-budget (<50€) : 1 seule position à la fois"),
        (C_PURPLE, "Ne tradez pas avant/pendant les annonces FOMC/BCE"),
    ]
    for col, rule in rules:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;"
            f"padding:8px 0;border-bottom:1px solid {C_BORDER}'>"
            f"<div style='width:8px;height:8px;background:{col};"
            f"border-radius:50%;box-shadow:0 0 6px {col};flex-shrink:0'></div>"
            f"<span style='color:{C_TEXT};font-size:0.88rem'>{rule}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 9 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

def tab_performance(p: dict) -> None:
    _section_title("Performance historique", C_GREEN, "📈")

    df = _load(p["symbol"], p["periode"], p["intervalle"])
    if df.empty:
        st.error(f"⚠️ Impossible de calculer les performances de **{p['symbol']}** — "
                 f"données historiques non disponibles. Vérifiez votre connexion ou élargissez la période.")
        return

    ret = df["Ret1"].dropna()
    if len(ret) < 5:
        st.warning("Pas assez de données.")
        return

    vol    = float(ret.std() * np.sqrt(252) * 100) if len(ret) > 1 else 0.0
    mean_r = float(ret.mean() * 252 * 100)
    if np.isnan(vol): vol = 0.0
    if np.isnan(mean_r): mean_r = 0.0
    sharpe = round(mean_r / vol, 2) if vol > 0.0001 else 0.0
    cummax = df["Close"].cummax()
    max_dd = float(((df["Close"] / cummax.replace(0, np.nan)) - 1).min() * 100) if not cummax.empty else 0.0
    if np.isnan(max_dd): max_dd = 0.0
    c0, c1_v = _scalar(df["Close"].iloc[0]), _scalar(df["Close"].iloc[-1])
    tot_r  = float((c1_v / c0 - 1) * 100) if c0 > 0 and len(df) > 1 else 0.0

    m1,m2,m3,m4,m5 = st.columns(5)
    with m1: _card("Rendement total", f"+{tot_r:.1f}%" if tot_r>=0 else f"{tot_r:.1f}%",
                   color=C_GREEN if tot_r>=0 else C_RED, icon="🏆")
    with m2: _card("Rend. annualisé", f"{mean_r:.1f}%",
                   color=C_GREEN if mean_r>=0 else C_RED, icon="📈")
    with m3: _card("Volatilité ann.", f"{vol:.1f}%", color=C_GOLD, icon="🌊")
    with m4: _card("Sharpe ratio", f"{sharpe:.2f}",
                   color=C_GREEN if sharpe>1 else C_ORANGE if sharpe>0 else C_RED, icon="⚡")
    with m5: _card("Drawdown max", f"{max_dd:.1f}%",
                   color=C_RED if max_dd<-15 else C_GOLD, icon="⬇️")

    cum = (1 + ret).cumprod() - 1
    ccol = C_GREEN if float(cum.iloc[-1])>=0 else C_RED
    fig_c = go.Figure(go.Scatter(x=cum.index, y=cum*100, mode="lines",
        line=dict(color=ccol, width=2.5),
        fill="tozeroy", fillcolor=f"rgba(0,255,136,0.07)" if ccol==C_GREEN else f"rgba(255,51,102,0.07)"))
    fig_c.add_hline(y=0, line_dash="dot", line_color=C_SILVER, opacity=0.5)
    fig_c.update_layout(**_chart_layout(320, "Rendements cumulés (%)"))
    st.plotly_chart(fig_c, use_container_width=True, config=PLOTLY_CFG)

    dd = (df["Close"] / df["Close"].cummax().replace(0, np.nan) - 1) * 100
    fig_dd = go.Figure(go.Scatter(x=df.index, y=dd, mode="lines",
        line=dict(color=C_RED, width=1.5),
        fill="tozeroy", fillcolor=f"rgba(255,51,102,0.12)"))
    fig_dd.update_layout(**_chart_layout(200, "Drawdown (%)"))
    st.plotly_chart(fig_dd, use_container_width=True, config=PLOTLY_CFG)

    fig_d = px.histogram(x=ret.values*100, nbins=50,
                         color_discrete_sequence=[C_CYAN],
                         labels={"x": "Rendement (%)"})
    fig_d.update_layout(**_chart_layout(240, "Distribution des rendements journaliers (%)"),
                        showlegend=False)
    st.plotly_chart(fig_d, use_container_width=True, config=PLOTLY_CFG)


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 10 — BACKTEST
# ══════════════════════════════════════════════════════════════════════════════

def tab_backtest(p: dict) -> None:
    _section_title("Backtesting de stratégie", C_PURPLE, "🔬")
    st.caption("Testez une stratégie sur les données historiques avant de l'utiliser en conditions réelles.")
    st.markdown(
        f"<div style='background:{C_GOLD}12;border-left:3px solid {C_GOLD};"
        f"border-radius:0 10px 10px 0;padding:10px 16px;margin-bottom:12px;"
        f"font-size:0.82rem;color:{C_GOLD}'>"
        f"⚠️ <strong>Avertissement :</strong> Les résultats de backtesting sont basés sur des "
        f"données historiques. Ils ne garantissent aucun gain futur. Le trading comporte "
        f"un risque de perte en capital.</div>",
        unsafe_allow_html=True,
    )

    df = _load(p["symbol"], p["periode"], p["intervalle"])
    if df.empty:
        st.error(f"⚠️ Backtest impossible — données introuvables pour **{p['symbol']}**. "
                 f"Essayez une période plus courte (ex. 6mo) ou vérifiez votre connexion.")
        return

    s1, s2 = st.columns([2, 1])
    with s1:
        strat = st.selectbox("Stratégie", [
            "Croisement SMA 20/50", "RSI Retournement (30/70)", "MACD Signal",
        ])
    with s2:
        cap_bt = st.number_input("Capital (€)", 10.0, 1_000.0, p["capital"], 10.0, key="bt_c")
        if cap_bt != st.session_state.get("shared_capital"):
            st.session_state["shared_capital"] = cap_bt
    rsk_bt = st.slider("Risque / trade (%)", 0.5, 5.0, p["risk_pct"]*100, 0.5, key="bt_r")

    st.caption("ℹ️ Frais de transaction inclus (0.1% / côté) · Longs uniquement · Signaux décalés d'1 barre (sans look-ahead bias)")
    if st.button("⚙️ Lancer le backtest", type="primary"):
        with st.spinner("Simulation en cours…"):
            results = {}
            try:
                bt = Backtester()
                _strat_key = "SMA" if "SMA" in strat else "RSI" if "RSI" in strat else "MACD"
                results = bt.run(df=df, strategy=_strat_key,
                                 capital=cap_bt, risk_pct=rsk_bt/100)
            except Exception:
                pass
            if not results:
                results = _simple_bt(df, strat, cap_bt)

        tr  = results.get("total_return", 0)
        wr  = results.get("win_rate", 0)
        pf_bt  = results.get("profit_factor", 0)
        dd_bt  = results.get("max_drawdown", 0)
        sh_bt  = results.get("sharpe", 0)
        b1,b2,b3,b4,b5,b6,b7 = st.columns(7)
        with b1: _card("Rendement", f"{tr:.1f}%",
                       color=C_GREEN if tr>=0 else C_RED, icon="🏆")
        with b2: _card("Trades", str(results.get("num_trades",0)),
                       color=C_CYAN, icon="⚡")
        with b3: _card("Win rate", f"{wr*100:.1f}%",
                       color=C_GREEN if wr>0.5 else C_RED, icon="🎯")
        with b4: _card("Profit factor", f"{min(pf_bt,99.9):.2f}",
                       color=C_GREEN if pf_bt>1 else C_RED, icon="💎")
        with b5: _card("Drawdown max", f"{dd_bt:.1f}%",
                       color=C_RED if dd_bt < -10 else C_GOLD, icon="⬇️")
        with b6: _card("Sharpe", f"{sh_bt:.2f}",
                       color=C_GREEN if sh_bt>1 else C_GOLD if sh_bt>0 else C_RED,
                       icon="📐")
        with b7: _card("Capital final", _eur(results.get("final_capital",cap_bt)),
                       color=C_GOLD, icon="💰")

        eq = results.get("equity_curve", [])
        if eq:
            fc = C_GREEN if eq[-1] >= cap_bt else C_RED
            fig_bt = go.Figure(go.Scatter(
                y=eq, mode="lines",
                line=dict(color=fc, width=2.5),
                fill="tozeroy",
                fillcolor=f"rgba(0,255,136,0.07)" if fc==C_GREEN else f"rgba(255,51,102,0.07)",
            ))
            fig_bt.add_hline(y=cap_bt, line_dash="dot", line_color=C_SILVER,
                             annotation_text="Capital initial", annotation_font_color=C_SILVER)
            fig_bt.update_layout(**_chart_layout(320, "Courbe de capital — backtest"))
            st.plotly_chart(fig_bt, use_container_width=True, config=PLOTLY_CFG)


def _simple_bt(df: pd.DataFrame, strat: str, capital: float) -> dict:
    """Backtest simplifié — frais 0.1%/côté, longs uniquement, décalage 1 barre."""
    needed = ["Close", "SMA20", "SMA50", "MACD", "Signal", "RSI"]
    df = df.copy().dropna(subset=[c for c in needed if c in df.columns])
    if len(df) < 10:
        return {}

    # Signaux : long uniquement (0 = flat, 1 = long)
    if "SMA" in strat:
        df["sig"] = np.where(df["SMA20"] > df["SMA50"], 1, 0)
    elif "RSI" in strat:
        df["sig"] = np.where(df["RSI"] < 30, 1, np.where(df["RSI"] > 70, 0, np.nan))
        df["sig"] = df["sig"].ffill().fillna(0)
    else:
        df["sig"] = np.where(df["MACD"] > df["Signal"], 1, 0)

    # Rendement journalier de l'actif
    ret1 = df["Ret1"] if "Ret1" in df.columns else df["Close"].pct_change()

    # Frais : 0.1% à chaque changement de signal
    fee_rate  = 0.001
    sig_shift = df["sig"].shift(1).fillna(0)
    sig_chg   = sig_shift.diff().abs().fillna(0)
    df["sr"]  = sig_shift * ret1 - sig_chg * fee_rate
    df["eq"]  = capital * (1 + df["sr"].fillna(0)).cumprod()

    final  = float(df["eq"].iloc[-1])
    # Win rate par trade — utilise sig_shift (décalé) pour éviter le look-ahead bias
    in_pos  = False
    trade_rets, t_start = [], None
    for i in range(len(df)):
        s = int(sig_shift.iloc[i])   # signal de la barre précédente, pas du bar courant
        if not in_pos and s == 1:
            in_pos = True; t_start = i
        elif in_pos and s == 0:
            trade_rets.append(float(df["sr"].iloc[t_start:i].sum()))
            in_pos = False
    wins = sum(1 for r in trade_rets if r > 0)
    n_tr = len(trade_rets)

    # Max drawdown
    eq_arr = df["eq"].values
    peak   = np.maximum.accumulate(eq_arr)
    max_dd = float(np.min((eq_arr - peak) / np.where(peak > 0, peak, 1))) * 100

    return {
        "total_return":  round((final - capital) / capital * 100, 2),
        "num_trades":    n_tr,
        "win_rate":      round(wins / max(n_tr, 1), 4),
        "final_capital": round(final, 2),
        "max_drawdown":  round(max_dd, 2),
        "profit_factor": 0.0,
        "sharpe":        0.0,
        "equity_curve":  df["eq"].tolist(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 11 — CALENDRIER
# ══════════════════════════════════════════════════════════════════════════════

def tab_calendrier(p: dict) -> None:
    _section_title("Calendrier économique 2026-2027", C_RED, "📅")
    st.caption("Événements macro-économiques majeurs susceptibles de créer des mouvements de marché.")

    evs = _cal_events()
    up  = [e for e in evs if e["delta"] >= 0]
    past= [e for e in evs if e["delta"] < 0]

    _section_title("Prochains événements", C_ORANGE, "📌")
    if up:
        for e in up[:8]:
            col  = C_RED if e["impact"] == "🔴" else C_GOLD
            days = "**Aujourd'hui !**" if e["delta"] == 0 else f"dans **{e['delta']}j**"
            st.markdown(
                f"<div style='background:{col}0a;border-left:4px solid {col};"
                f"border-radius:0 12px 12px 0;padding:10px 16px;margin-bottom:8px;"
                f"display:flex;justify-content:space-between;align-items:center'>"
                f"<span>{e['impact']} <b style='color:{C_WHITE}'>{e['ev']}</b>"
                f" — <span style='color:{C_MUTED};font-size:0.82rem'>"
                f"{e['date'].strftime('%d/%m/%Y')}</span></span>"
                f"<span style='color:{col};font-weight:700;font-size:0.85rem'>{days}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun événement à venir.")

    with st.expander("🕐 Événements passés"):
        for e in past[:5]:
            st.markdown(
                f"{e['impact']} {e['ev']} — {e['date'].strftime('%d/%m/%Y')} "
                f"(il y a {abs(e['delta'])}j)"
            )

    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Impact typique", C_GOLD, "💥")
    st.markdown(f"""
| Événement | Impact | Actifs les plus touchés |
|-----------|--------|------------------------|
| 🔴 FOMC (Fed) | **Très fort** | USD, BTC, S&P 500 |
| 🔴 BCE | **Très fort** | EUR, CAC 40 |
| 🟠 CPI US | Fort | USD, Or, Obligations |
| 🟠 NFP | Fort | USD, Actions US |
""")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 12 — STRATÉGIES
# ══════════════════════════════════════════════════════════════════════════════

def tab_strategies(p: dict) -> None:
    _section_title("Bibliothèque de stratégies", C_PURPLE, "🎯")

    try:
        sm = StrategyManager()
        custom = sm.list_strategies() if hasattr(sm, "list_strategies") else []
    except Exception:
        sm, custom = None, []

    builtin = [
        {"Nom":"Croisement SMA 20/50","Type":"Tendance","Budget min":"10 €","Complexité":"⭐"},
        {"Nom":"RSI Retournement","Type":"Contra-tendance","Budget min":"10 €","Complexité":"⭐"},
        {"Nom":"MACD + RSI","Type":"Momentum","Budget min":"50 €","Complexité":"⭐⭐"},
        {"Nom":"Bollinger Bands","Type":"Volatilité","Budget min":"100 €","Complexité":"⭐⭐"},
        {"Nom":"Multi-Timeframe","Type":"Confirmation","Budget min":"200 €","Complexité":"⭐⭐⭐"},
    ]
    st.dataframe(pd.DataFrame(builtin), use_container_width=True, hide_index=True)

    if custom:
        _section_title("Vos stratégies", C_GOLD, "✏️")
        st.dataframe(pd.DataFrame(custom), use_container_width=True, hide_index=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Créer une stratégie", C_GREEN, "➕")
    ca, cb = st.columns(2)
    with ca: nom = st.text_input("Nom", key="sn")
    with cb:
        stype = st.selectbox("Type", ["Tendance","Momentum","Contra-tendance","Volatilité","Autre"], key="st")
    desc = st.text_area("Description (optionnel)", key="sd")
    if st.button("💾 Enregistrer", type="primary"):
        if nom.strip():
            try:
                if sm and hasattr(sm, "save_strategy"):
                    sm.save_strategy({"name":nom,"type":stype,"description":desc,
                                      "created":datetime.now().isoformat()})
                st.success(f"✅ Stratégie « {nom} » enregistrée")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("Entrez un nom.")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 13 — ALERTES
# ══════════════════════════════════════════════════════════════════════════════

def tab_alertes(p: dict) -> None:
    _section_title("Gestionnaire d'alertes", C_ORANGE, "🔔")
    try:
        am     = AlertManager()
        active = am.get_active_alerts() if hasattr(am, "get_active_alerts") else []
    except Exception:
        am, active = None, []

    _section_title("Créer une alerte", C_CYAN, "➕")
    a1,a2,a3 = st.columns(3)
    with a1: sym = st.text_input("Symbole", value=p["symbol"], key="al_s")
    with a2:
        atype = st.selectbox("Condition", [
            "Prix ≥ cible","Prix ≤ cible",
            "RSI > 70 (suracheté)","RSI < 30 (survendu)",
            "Croisement SMA haussier","Volume anormal",
        ], key="al_t")
    with a3: aval = st.number_input("Valeur cible", 0.0, 1e6, 0.0, 0.01, key="al_v")

    _needs_value = atype in ("Prix ≥ cible", "Prix ≤ cible")
    if st.button("➕ Ajouter l'alerte", type="primary"):
        if _needs_value and aval <= 0:
            st.warning("⚠️ La valeur cible doit être supérieure à 0 pour ce type d'alerte.")
        elif am and hasattr(am, "add_alert"):
            try:
                am.add_alert({"symbol":sym,"type":atype,"value":aval,
                              "created":datetime.now().isoformat()})
                st.success(f"✅ Alerte ajoutée : {sym} — {atype}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Alertes actives", C_GOLD, "📋")
    if active:
        st.dataframe(pd.DataFrame(active), use_container_width=True, hide_index=True)
        col_del, col_conf = st.columns([2, 3])
        with col_del:
            if st.button("🗑️ Tout supprimer", type="secondary"):
                st.session_state["_confirm_delete_alerts"] = True
        if st.session_state.get("_confirm_delete_alerts"):
            with col_conf:
                st.warning("⚠️ Confirmer la suppression de toutes les alertes ?")
            c_yes, c_no = st.columns(2)
            with c_yes:
                if st.button("✅ Oui, supprimer", type="primary"):
                    if am and hasattr(am, "clear_alerts"):
                        am.clear_alerts()
                    st.session_state["_confirm_delete_alerts"] = False
                    st.rerun()
            with c_no:
                if st.button("❌ Annuler"):
                    st.session_state["_confirm_delete_alerts"] = False
                    st.rerun()
    else:
        st.info("Aucune alerte active.")

    st.markdown("<hr>", unsafe_allow_html=True)
    _section_title("Vérification RSI rapide", C_RED, "⚡")
    syms_check = _sym_list(p["categorie"])[:6]
    if st.button("🔍 Vérifier maintenant"):
        triggered = []
        bar = st.progress(0)
        for i, s in enumerate(syms_check):
            try:
                d = _load(s, "5d", "1d")
                if not d.empty:
                    rsi = float(d["RSI"].iloc[-1])
                    if not np.isnan(rsi):
                        if rsi > 70:   triggered.append((s, rsi, "suracheté", C_RED))
                        elif rsi < 30: triggered.append((s, rsi, "survendu",  C_GREEN))
            except Exception:
                pass
            bar.progress((i+1)/max(len(syms_check),1))
        bar.empty()
        if triggered:
            for s, rsi, state, col in triggered:
                st.markdown(
                    f"<div style='background:{col}0d;border-left:3px solid {col};"
                    f"border-radius:0 10px 10px 0;padding:8px 14px;margin-bottom:6px'>"
                    f"<b style='color:{col}'>{s}</b> · RSI {rsi:.1f} · <span style='color:{C_TEXT}'>{state}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("✅ Aucune alerte RSI déclenchée.")


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 14 — AIDE
# ══════════════════════════════════════════════════════════════════════════════

def tab_aide(p: dict) -> None:
    _section_title("Centre d'aide", C_CYAN, "❓")

    h1,h2,h3,h4 = st.tabs([
        "📖 Guide démarrage","📚 Glossaire",
        "🔗 Sources & légal","🤖 Comprendre le bot",
    ])

    with h1:
        steps = [
            (C_CYAN,   "1", "Choisissez votre actif", "Sidebar → catégorie → actif, période, intervalle"),
            (C_GOLD,   "2", "Analysez le marché", "Onglet Analyse → 6 sous-onglets : chandeliers, RSI/MACD, Volume, Multi-TF, Patterns, Corrélations"),
            (C_GREEN,  "3", "Vérifiez les signaux", "Onglet Signaux → score composite 0/6 à 6/6 (RSI, MACD, Z-Score, BB%, Momentum) + niveaux SL/TP"),
            (C_PURPLE, "4", "Configurez le bot", "Onglet Bot → capital (10€-1000€), risque, actifs"),
            (C_ORANGE, "5", "Gérez le risque", "Onglet Risque → calculateur de position automatique"),
            (C_RED,    "6", "Suivez les performances", "Onglets Performance et Backtest → statistiques et courbes"),
        ]
        for col, num, title, desc in steps:
            st.markdown(
                f"<div style='display:flex;gap:14px;align-items:flex-start;"
                f"padding:12px 0;border-bottom:1px solid {C_BORDER}'>"
                f"<div style='width:32px;height:32px;background:{col}22;"
                f"border:2px solid {col}66;border-radius:50%;display:flex;"
                f"align-items:center;justify-content:center;font-weight:900;"
                f"color:{col};font-size:0.9rem;flex-shrink:0'>{num}</div>"
                f"<div><div style='font-weight:700;color:{C_WHITE};margin-bottom:2px'>{title}</div>"
                f"<div style='color:{C_MUTED};font-size:0.82rem'>{desc}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    with h2:
        terms = [
            ("RSI","Relative Strength Index (0-100). >70 = suracheté, <30 = survendu"),
            ("MACD","Croisement de moyennes mobiles — indique les retournements de tendance"),
            ("SMA","Moyenne mobile simple — lisse les prix sur N périodes"),
            ("EMA","Moyenne mobile exponentielle — réagit plus vite aux variations récentes"),
            ("Bollinger Bands","Bandes de volatilité à ±2σ autour de la SMA(20)"),
            ("ATR","Average True Range — mesure la volatilité pour calibrer les stops"),
            ("OBV","On-Balance Volume — confirme les tendances par les flux de volume"),
            ("Stop-Loss","Ordre automatique pour limiter une perte à un niveau défini"),
            ("Take Profit","Ordre automatique pour sécuriser un gain à un niveau cible"),
            ("PnL","Profit & Loss — gains ou pertes d'une position ouverte"),
            ("Drawdown","Perte maximale depuis un pic — indicateur de risque clé"),
            ("Sharpe","Rendement ÷ volatilité — plus c'est élevé, mieux c'est (>1 = bon)"),
            ("Doji","Bougie sans corps : acheteurs et vendeurs à égalité — indécision"),
            ("Marteau","Longue mèche basse — signe de retournement haussier"),
            ("Marubozu","Bougie sans mèche — force absolue d'un camp"),
            ("Engloutissement","Grande bougie qui avale la précédente — signal fort"),
        ]
        for term, definition in terms:
            st.markdown(
                f"<div style='display:flex;gap:12px;padding:8px 0;"
                f"border-bottom:1px solid {C_BORDER}'>"
                f"<div style='color:{C_CYAN};font-weight:700;font-size:0.85rem;"
                f"min-width:120px'>{term}</div>"
                f"<div style='color:{C_TEXT};font-size:0.83rem'>{definition}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with h3:
        st.markdown(f"""
### Sources de données (5 APIs gratuites, sans clé)

| API | Source | Usage | Fréquence |
|-----|--------|-------|-----------|
| **Binance** | api.binance.com | Crypto OHLCV + ticker live | Cache 10-120s |
| **CoinGecko** | api.coingecko.com | Prix batch, market cap, trending | Cache 30s-10min |
| **Frankfurter** | api.frankfurter.app | Taux de change BCE officiels | Cache 60s |
| **FRED** | fred.stlouisfed.org | Macro US (CPI, Fed, chômage) | Cache 1h |
| **Yahoo Finance** | via yfinance | Actions, ETF, indices, commodités | Cache 120s |

### Ressources pour progresser
- **Investopedia** — définitions et tutoriels sur tous les indicateurs
- **TradingView** — graphiques avancés pour valider vos analyses
- **AMF France** (amf-france.org) — protection des investisseurs français
- **CoinGecko** — données crypto exhaustives
- **Federal Reserve** (fred.stlouisfed.org) — données macro US

### ⚠️ Avertissement légal
> **THE ZEDICUS v3 est un outil éducatif uniquement.** Il ne constitue pas un conseil en investissement.
> Les signaux générés sont informatifs et ne garantissent aucun résultat.
> **Le trading comporte un risque de perte totale du capital investi.**
> Investissez uniquement ce que vous pouvez vous permettre de perdre.
        """)

    with h4:
        stages = [
            (C_CYAN,   "Étape 1 — Collecte",     "Données OHLCV récupérées via Yahoo Finance (polling 60s)"),
            (C_GOLD,   "Étape 2 — Indicateurs",  "RSI(14) · MACD(12/26/9) · BB(20,2σ) · ATR(14) · OBV"),
            (C_GREEN,  "Étape 3 — Score",        "Chaque condition haussière ajoute des points (0→1.0)"),
            (C_PURPLE, "Étape 4 — Filtres risque","Position max 40% · Min 0.01€ investi · Drawdown max"),
            (C_ORANGE, "Étape 5 — Exécution",    "Si score ≥ min_confidence → ordre simulé (paper trading)"),
        ]
        for col, title, desc in stages:
            st.markdown(
                f"<div style='background:{col}08;border-left:3px solid {col};"
                f"border-radius:0 12px 12px 0;padding:12px 16px;margin-bottom:8px'>"
                f"<div style='color:{col};font-weight:700;font-size:0.88rem'>{title}</div>"
                f"<div style='color:{C_TEXT};font-size:0.82rem;margin-top:3px'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(f"""
| Capital | Risque/trade | Positions | Drawdown stop |
|---------|-------------|-----------|--------------|
| ≤ 50 €  | **3 %**     | **1**     | 20 %         |
| ≤ 200 € | **2 %**     | **2**     | 15 %         |
| > 200 € | **1,5 %**   | **3**     | 12 %         |
        """)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 15 — STRATZED
# ══════════════════════════════════════════════════════════════════════════════

def tab_stratzed(p: dict) -> None:
    _section_title("StratZed — Composeur de stratégies", C_GOLD, "⚗️")
    st.caption("Créez, testez et sauvegardez vos propres stratégies en combinant librement les indicateurs.")

    df = _load(p["symbol"], p["periode"], p["intervalle"])
    if df.empty:
        st.error(f"⚠️ StratZed ne peut pas analyser **{p['symbol']}** — données manquantes. "
                 f"Changez de symbole ou de période dans la barre latérale.")
        return

    last = df.iloc[-1]

    # ── Sélecteur de style de trading ────────────────────────────────────────
    TRADING_STYLES = {
        "⚡ Scalping":      {
            "desc":      "Trades de quelques minutes à quelques heures. Petit TP, petit SL.",
            "timeframe": "1m / 5m / 15m",
            "hold":      "Secondes à quelques heures",
            "sl_pct":    1.0,
            "tp_pct":    1.5,
            "rr":        "1:1.5",
            "risk":      0.5,
            "indicators":["RSI court (7-9)", "MACD court (5/13/5)", "Volume spike", "BB étroites"],
            "tips": [
                "Entrez uniquement sur des setups à haute probabilité (RSI + volume)",
                "Stop-loss serré obligatoire — ne jamais élargir en cours de trade",
                "Évitez les actualités macro (FOMC, NFP) — volatilité imprévisible",
                "Target : 1.5× votre risque minimum avant de viser plus loin",
                "Maximum 0.5% du capital par trade pour limiter l'exposition",
            ],
            "color": C_CYAN,
            "icon": "⚡",
        },
        "📅 Day Trading":   {
            "desc":      "Positions ouvertes et fermées dans la même journée.",
            "timeframe": "15m / 30m / 1h",
            "hold":      "Quelques heures, fermé avant clôture",
            "sl_pct":    2.5,
            "tp_pct":    5.0,
            "rr":        "1:2",
            "risk":      1.0,
            "indicators":["SMA 20 / 50", "RSI (14)", "MACD (12/26/9)", "Support / Résistance"],
            "tips": [
                "Ne jamais conserver une position overnight — risque gap nocturne",
                "Meilleur timing : 30 min après l'ouverture, 1h avant la clôture",
                "Confirmez le signal sur 2 timeframes avant d'entrer",
                "Risk/Reward minimum 1:2 — refusez les trades sous ce seuil",
                "Maximum 1% du capital par trade",
            ],
            "color": C_GREEN,
            "icon": "📅",
        },
        "🌊 Swing Trading": {
            "desc":      "Positions de plusieurs jours à semaines. Suit les tendances moyennes.",
            "timeframe": "4h / 1j / 1sem",
            "hold":      "2-10 jours typiquement",
            "sl_pct":    5.0,
            "tp_pct":    12.0,
            "rr":        "1:2.4",
            "risk":      1.5,
            "indicators":["SMA 20 / 50 / 200", "RSI (14)", "Z-Score", "Bollinger Bands"],
            "tips": [
                "Entrez sur un pullback vers la SMA20 en tendance haussière",
                "Le Z-Score < −1 est un excellent signal de mean reversion",
                "Trailing stop à 5% pour protéger les gains après +8%",
                "Évitez d'entrer avant une publication macro importante",
                "Maximum 1.5% du capital, jusqu'à 3 positions simultanées",
            ],
            "color": C_GOLD,
            "icon": "🌊",
        },
        "🏔️ Position Trading": {
            "desc":      "Positions longues de semaines à mois. Suit la macro-tendance.",
            "timeframe": "1j / 1sem / 1mois",
            "hold":      "Semaines à plusieurs mois",
            "sl_pct":    10.0,
            "tp_pct":    30.0,
            "rr":        "1:3",
            "risk":      2.0,
            "indicators":["SMA 50 / 200", "Golden/Death Cross", "Volume OBV", "Macro FRED"],
            "tips": [
                "Analysez le contexte macro avant d'entrer (taux, inflation, VIX)",
                "Golden Cross (SMA50 > SMA200) = signal d'entrée fort en position",
                "Le trailing stop large (10%) tolère les corrections intermédiaires",
                "Réévaluez la position chaque semaine — ne pas se marier à un trade",
                "Maximum 2% du capital, portefeuille concentré 3-5 positions",
            ],
            "color": C_PURPLE,
            "icon": "🏔️",
        },
    }

    style_sel = st.selectbox(
        "🎯 Style de trading",
        list(TRADING_STYLES.keys()),
        key="sz_style",
        help="Chaque style adapte automatiquement le TP/SL suggéré et les recommandations.",
    )
    sty = TRADING_STYLES[style_sel]

    # Bandeau style de trading
    st.markdown(
        f"<div style='background:{sty['color']}12;border:1.5px solid {sty['color']}55;"
        f"border-radius:14px;padding:16px 20px;margin-bottom:18px'>"
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:10px'>"
        f"<span style='font-size:1.6rem'>{sty['icon']}</span>"
        f"<div>"
        f"<div style='font-weight:800;font-size:1rem;color:{sty['color']}'>{style_sel}</div>"
        f"<div style='color:{C_TEXT};font-size:0.82rem'>{sty['desc']}</div>"
        f"</div></div>"
        f"<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px'>"
        f"<div style='text-align:center;background:{C_BG2};border-radius:10px;padding:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>Timeframe</div>"
        f"<div style='color:{sty['color']};font-weight:700;font-size:0.85rem'>{sty['timeframe']}</div>"
        f"</div>"
        f"<div style='text-align:center;background:{C_BG2};border-radius:10px;padding:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>TP suggéré</div>"
        f"<div style='color:{C_GREEN};font-weight:700;font-size:0.85rem'>+{sty['tp_pct']}%</div>"
        f"</div>"
        f"<div style='text-align:center;background:{C_BG2};border-radius:10px;padding:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>SL suggéré</div>"
        f"<div style='color:{C_RED};font-weight:700;font-size:0.85rem'>−{sty['sl_pct']}%</div>"
        f"</div>"
        f"</div>"
        f"<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px'>"
        f"<div style='text-align:center;background:{C_BG2};border-radius:10px;padding:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>R/R min</div>"
        f"<div style='color:{C_GOLD};font-weight:700;font-size:0.85rem'>{sty['rr']}</div>"
        f"</div>"
        f"<div style='text-align:center;background:{C_BG2};border-radius:10px;padding:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>Durée type</div>"
        f"<div style='color:{C_TEXT};font-weight:700;font-size:0.85rem'>{sty['hold']}</div>"
        f"</div>"
        f"<div style='text-align:center;background:{C_BG2};border-radius:10px;padding:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>Risque/trade</div>"
        f"<div style='color:{C_ORANGE};font-weight:700;font-size:0.85rem'>{sty['risk']}%</div>"
        f"</div>"
        f"</div>"
        f"<div style='margin-bottom:8px'>"
        f"<div style='color:{C_MUTED};font-size:0.72rem;text-transform:uppercase;margin-bottom:6px'>Indicateurs recommandés</div>"
        f"<div style='display:flex;flex-wrap:wrap;gap:6px'>"
        + "".join(f"<span style='background:{sty['color']}20;color:{sty['color']};"
                  f"border-radius:20px;padding:3px 10px;font-size:0.75rem;font-weight:600'>{ind}</span>"
                  for ind in sty["indicators"])
        + f"</div></div>"
        f"<div>"
        f"<div style='color:{C_MUTED};font-size:0.72rem;text-transform:uppercase;margin-bottom:6px'>💡 Conseils pour ce style</div>"
        + "".join(f"<div style='display:flex;gap:8px;padding:4px 0;border-bottom:1px solid {C_BORDER}'>"
                  f"<span style='color:{sty['color']};font-weight:700'>›</span>"
                  f"<span style='color:{C_TEXT};font-size:0.80rem'>{tip}</span></div>"
                  for tip in sty["tips"])
        + f"</div></div>",
        unsafe_allow_html=True,
    )

    # Calcul TP/SL sur le prix actuel
    current_price = _scalar(last.get("Close", 0))
    if current_price > 0:
        atr_val = _scalar(last.get("ATR", 0)) if "ATR" in last.index else 0
        tp_price = current_price * (1 + sty["tp_pct"] / 100)
        sl_price = current_price * (1 - sty["sl_pct"] / 100)
        # Devise : USD pour les crypto en -USD, sinon €
        _sym_upper = p.get("symbol", "").upper()
        _currency  = "USD" if "-USD" in _sym_upper or "USDT" in _sym_upper else "€"
        tp2, tp3 = st.columns(2)
        with tp2:
            st.markdown(
                f"<div style='background:{C_GREEN}12;border:1px solid {C_GREEN}44;"
                f"border-radius:12px;padding:12px 16px;text-align:center'>"
                f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>Take Profit suggéré</div>"
                f"<div style='color:{C_GREEN};font-size:1.3rem;font-weight:900'>{tp_price:,.2f} {_currency}</div>"
                f"<div style='color:{C_MUTED};font-size:0.75rem'>+{sty['tp_pct']}% depuis {current_price:,.2f} {_currency}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with tp3:
            st.markdown(
                f"<div style='background:{C_RED}12;border:1px solid {C_RED}44;"
                f"border-radius:12px;padding:12px 16px;text-align:center'>"
                f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase'>Stop Loss suggéré</div>"
                f"<div style='color:{C_RED};font-size:1.3rem;font-weight:900'>{sl_price:,.2f} {_currency}</div>"
                f"<div style='color:{C_MUTED};font-size:0.75rem'>−{sty['sl_pct']}% depuis {current_price:,.2f} {_currency}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("<hr>", unsafe_allow_html=True)

    sz_tab1, sz_tab2 = st.tabs(["⚗️ Composer & Backtester", "📚 Mes stratégies StratZed"])

    with sz_tab1:
        # ── Règles d'achat ────────────────────────────────────────────────────
        _section_title("Conditions d'ACHAT", C_GREEN, "🟢")
        br1, br2 = st.columns(2)
        with br1:
            use_rsi_buy = st.checkbox("RSI < seuil (survendu)", value=True, key="sz_rsi_buy_en")
            rsi_buy_thr = st.slider("Seuil RSI achat", 10, 50, 35, key="sz_rsi_buy") if use_rsi_buy else 35
            use_macd_buy = st.checkbox("MACD > Signal (haussier)", value=True, key="sz_macd_buy_en")
            use_sma_buy  = st.checkbox("Prix > SMA 20 (tendance)", value=False, key="sz_sma_buy_en")
        with br2:
            use_bb_buy   = st.checkbox("BB% < seuil (bas des bandes)", value=False, key="sz_bb_buy_en")
            bb_buy_thr   = st.slider("Seuil BB% achat", 5, 45, 20, key="sz_bb_buy") if use_bb_buy else 20
            use_zs_buy   = st.checkbox("Z-Score < −seuil (mean reversion)", value=True, key="sz_zs_buy_en")
            zs_buy_thr   = st.slider("Seuil Z-Score achat", 0.5, 2.5, 1.0, 0.1, key="sz_zs_buy") if use_zs_buy else 1.0
            use_vol_buy  = st.checkbox("Volume ratio > 1.2× (confirmation)", value=False, key="sz_vol_buy_en")

        # ── Règles de vente ───────────────────────────────────────────────────
        _section_title("Conditions de VENTE / SORTIE", C_RED, "🔴")
        sr1, sr2 = st.columns(2)
        with sr1:
            use_rsi_sell  = st.checkbox("RSI > seuil (suracheté)", value=True, key="sz_rsi_sell_en")
            rsi_sell_thr  = st.slider("Seuil RSI vente", 55, 90, 70, key="sz_rsi_sell") if use_rsi_sell else 70
            use_macd_sell = st.checkbox("MACD < Signal (baissier)", value=False, key="sz_macd_sell_en")
        with sr2:
            use_bb_sell   = st.checkbox("BB% > seuil (haut des bandes)", value=False, key="sz_bb_sell_en")
            bb_sell_thr   = st.slider("Seuil BB% vente", 55, 95, 80, key="sz_bb_sell") if use_bb_sell else 80
            use_zs_sell   = st.checkbox("Z-Score > +seuil (suracheté Z)", value=False, key="sz_zs_sell_en")
            zs_sell_thr   = st.slider("Seuil Z-Score vente", 0.5, 2.5, 1.5, 0.1, key="sz_zs_sell") if use_zs_sell else 1.5

        # ── Score live ────────────────────────────────────────────────────────
        st.markdown("<hr>", unsafe_allow_html=True)
        _section_title("Score live de votre stratégie", C_CYAN, "⚡")

        _rsi = last.get("RSI", 50);          rsi_now   = 50.0 if (not isinstance(_rsi, (int,float)) or (_rsi != _rsi)) else float(_rsi)
        macd_bull  = _scalar(last.get("MACD", 0)) > _scalar(last.get("Signal", 0)) if ("MACD" in df.columns and "Signal" in df.columns) else False
        sma_bull   = _scalar(last.get("Close", 0)) > _scalar(last.get("SMA20", 0)) if "SMA20" in df.columns else False
        _bb  = last.get("BB_pct",  0.5);     bb_now    = 0.5  if (not isinstance(_bb,  (int,float)) or (_bb  != _bb))  else float(_bb)
        _zs  = last.get("ZScore",  0.0);     zs_now    = 0.0  if (not isinstance(_zs,  (int,float)) or (_zs  != _zs))  else float(_zs)
        _vr  = last.get("VolRatio",1.0);     vol_r_now = 1.0  if (not isinstance(_vr,  (int,float)) or (_vr  != _vr))  else float(_vr)

        buy_conds = []
        if use_rsi_buy:  buy_conds.append(("RSI",     f"{rsi_now:.1f} < {rsi_buy_thr}",         rsi_now < rsi_buy_thr))
        if use_macd_buy: buy_conds.append(("MACD",    "Haussier ↑" if macd_bull else "Baissier ↓", macd_bull))
        if use_sma_buy:  buy_conds.append(("SMA20",   "Au-dessus ↑" if sma_bull else "En-dessous ↓", sma_bull))
        if use_bb_buy:   buy_conds.append(("BB%",     f"{bb_now*100:.0f}% < {bb_buy_thr}%",     bb_now * 100 < bb_buy_thr))
        if use_zs_buy:   buy_conds.append(("Z-Score", f"{zs_now:+.2f} < −{zs_buy_thr:.1f}",    zs_now < -zs_buy_thr))
        if use_vol_buy:  buy_conds.append(("Volume",  f"{vol_r_now:.2f}× > 1.2×",               vol_r_now > 1.2))

        sell_conds = []
        if use_rsi_sell:  sell_conds.append(("RSI vente",     f"{rsi_now:.1f} > {rsi_sell_thr}",       rsi_now > rsi_sell_thr))
        if use_macd_sell: sell_conds.append(("MACD vente",    "Baissier ↓" if not macd_bull else "OK",  not macd_bull))
        if use_bb_sell:   sell_conds.append(("BB% vente",     f"{bb_now*100:.0f}% > {bb_sell_thr}%",   bb_now * 100 > bb_sell_thr))
        if use_zs_sell:   sell_conds.append(("Z-Score vente", f"{zs_now:+.2f} > +{zs_sell_thr:.1f}",   zs_now > zs_sell_thr))

        buy_score  = sum(1 for _, _, ok in buy_conds if ok)
        buy_total  = max(len(buy_conds), 1)
        sell_score = sum(1 for _, _, ok in sell_conds if ok)
        sell_total = max(len(sell_conds), 1)
        buy_pct    = int(buy_score / buy_total * 100)
        sell_pct   = int(sell_score / sell_total * 100)

        lv1, lv2 = st.columns(2)
        for col_ui, score, total, pct, conds, label, base_col, is_buy in [
            (lv1, buy_score, buy_total, buy_pct, buy_conds, "ACHAT", C_GREEN, True),
            (lv2, sell_score, sell_total, sell_pct, sell_conds, "VENTE", C_RED, False),
        ]:
            with col_ui:
                bar_col = base_col if pct >= 50 else C_MUTED
                st.markdown(
                    f"<div style='background:{bar_col}0e;border:2px solid {bar_col}44;"
                    f"border-radius:14px;padding:16px;text-align:center;margin-bottom:12px'>"
                    f"<div style='color:{C_MUTED};font-size:0.72rem;text-transform:uppercase;"
                    f"letter-spacing:0.1em;margin-bottom:6px'>Score {label}</div>"
                    f"<div style='font-family:Orbitron,sans-serif;font-size:2.2rem;font-weight:900;"
                    f"color:{bar_col};text-shadow:0 0 18px {bar_col}88;line-height:1'>"
                    f"{score}/{total}</div>"
                    f"<div style='height:6px;background:{C_BORDER};border-radius:3px;margin:8px 8px 0'>"
                    f"<div style='width:{pct}%;height:100%;background:linear-gradient(90deg,{bar_col}88,{bar_col});"
                    f"border-radius:3px'></div></div></div>",
                    unsafe_allow_html=True,
                )
                for cname, cval, cok in conds:
                    icon_ok = "✅" if cok else "❌"
                    ccolor  = base_col if cok else C_MUTED
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:8px;padding:5px 0;"
                        f"border-bottom:1px solid {C_BORDER}'>"
                        f"<span style='font-size:1rem'>{icon_ok}</span>"
                        f"<span style='color:{C_TEXT};font-size:0.83rem;flex:1'>{cname}</span>"
                        f"<span style='color:{ccolor};font-size:0.80rem;font-weight:700'>{cval}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        # Décision globale
        if buy_pct >= 66 and sell_pct < 33:
            dec_c, dec_t, dec_i = C_GREEN, "SIGNAL ACHAT StratZed", "🟢"
        elif sell_pct >= 66 and buy_pct < 33:
            dec_c, dec_t, dec_i = C_RED, "SIGNAL VENTE StratZed", "🔴"
        elif buy_pct >= 50:
            dec_c, dec_t, dec_i = C_GREEN, "TENDANCE ACHAT", "🟢"
        elif sell_pct >= 50:
            dec_c, dec_t, dec_i = C_RED, "TENDANCE VENTE", "🔴"
        else:
            dec_c, dec_t, dec_i = C_GOLD, "NEUTRE — attendre confirmation", "🟡"

        st.markdown(
            f"<div class='zed-ring' style='background:{dec_c}0e;border:2px solid {dec_c}55;"
            f"border-radius:18px;padding:18px 24px;text-align:center;margin:16px 0;"
            f"box-shadow:0 0 30px {dec_c}1a'>"
            f"<div style='font-family:Orbitron,sans-serif;font-size:1.4rem;font-weight:900;"
            f"color:{dec_c};text-shadow:0 0 16px {dec_c}88'>{dec_i} {dec_t}</div>"
            f"<div style='color:{C_MUTED};font-size:0.80rem;margin-top:6px'>"
            f"Achat {buy_score}/{buy_total} · Vente {sell_score}/{sell_total} · {p['symbol']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Backtest de la stratégie ──────────────────────────────────────────
        st.markdown("<hr>", unsafe_allow_html=True)
        _section_title("Backtest de votre stratégie StratZed", C_PURPLE, "🔬")

        cap_sz  = st.number_input("Capital (€)", 10.0, 1_000.0, float(p["capital"]), 10.0, key="sz_cap")
        if cap_sz != st.session_state.get("shared_capital"):
            st.session_state["shared_capital"] = cap_sz
        _sl_col, _ps_col = st.columns(2)
        _sl_default = max(1, min(20, int(sty["sl_pct"])))
        _ps_default = max(5, min(40, int(sty["risk"] * 10)))
        with _sl_col:
            sl_pct_sz = st.slider("Stop-loss (%)", 1, 20, _sl_default, 1, key="sz_sl",
                                  help=f"Recommandé {style_sel}: {sty['sl_pct']}%")
        with _ps_col:
            pos_size_pct = st.slider("Taille position (%)", 5, 40, _ps_default, 5, key="sz_ps",
                                     help=f"Risque recommandé {style_sel}: {sty['risk']}% / trade")

        _no_buy_cond  = not any([use_rsi_buy, use_macd_buy, use_sma_buy, use_bb_buy, use_zs_buy, use_vol_buy])
        _no_sell_cond = not any([use_rsi_sell, use_macd_sell, use_bb_sell, use_zs_sell])
        if _no_buy_cond or _no_sell_cond:
            st.warning("⚠️ Activez au moins 1 condition d'achat ET 1 condition de vente pour lancer le backtest.")
        if st.button("⚗️ Lancer le backtest StratZed", type="primary", key="sz_bt", disabled=(_no_buy_cond or _no_sell_cond)):
            with st.spinner("Simulation StratZed en cours…"):
                df_bt = df.copy().dropna(subset=["Close"])

                # Construire les séries de signaux
                buy_sig  = pd.Series(True, index=df_bt.index)
                sell_sig = pd.Series(True, index=df_bt.index)

                if use_rsi_buy and "RSI" in df_bt.columns:
                    buy_sig &= df_bt["RSI"].fillna(50) < rsi_buy_thr
                if use_macd_buy and "MACD" in df_bt.columns and "Signal" in df_bt.columns:
                    buy_sig &= df_bt["MACD"] > df_bt["Signal"]
                if use_sma_buy and "SMA20" in df_bt.columns:
                    buy_sig &= df_bt["Close"] > df_bt["SMA20"]
                if use_bb_buy and "BB_pct" in df_bt.columns:
                    buy_sig &= df_bt["BB_pct"].fillna(0.5) * 100 < bb_buy_thr
                if use_zs_buy and "ZScore" in df_bt.columns:
                    buy_sig &= df_bt["ZScore"].fillna(0) < -zs_buy_thr
                if use_vol_buy and "VolRatio" in df_bt.columns:
                    buy_sig &= df_bt["VolRatio"].fillna(1.0) > 1.2

                if use_rsi_sell and "RSI" in df_bt.columns:
                    sell_sig &= df_bt["RSI"].fillna(50) > rsi_sell_thr
                if use_macd_sell and "MACD" in df_bt.columns and "Signal" in df_bt.columns:
                    sell_sig &= df_bt["MACD"] < df_bt["Signal"]
                if use_bb_sell and "BB_pct" in df_bt.columns:
                    sell_sig &= df_bt["BB_pct"].fillna(0.5) * 100 > bb_sell_thr
                if use_zs_sell and "ZScore" in df_bt.columns:
                    sell_sig &= df_bt["ZScore"].fillna(0) > zs_sell_thr

                # ── Décalage d'1 barre pour éviter le look-ahead bias ─────────
                # Le signal de la barre i → exécution à l'ouverture de la barre i+1
                buy_sig_shifted  = buy_sig.shift(1).fillna(False)
                sell_sig_shifted = sell_sig.shift(1).fillna(False)

                # Position sizing : depuis le slider (5-40% du capital par trade)
                position_frac  = pos_size_pct / 100.0
                sl_threshold   = sl_pct_sz / 100.0          # stop-loss en fraction

                # Frais de transaction simulés (0.1% par côté = 0.2% aller-retour)
                FEE = 0.001

                # Simuler les trades barre par barre
                position    = 0
                eq          = cap_sz
                entry_price = 0.0
                trades      = []
                equity_curve = [cap_sz]
                max_eq      = cap_sz  # pour calcul drawdown

                for i in range(1, len(df_bt)):
                    price = _scalar(df_bt["Close"].iloc[i])
                    if price <= 0:           # barre invalide / NaN → on ignore
                        equity_curve.append(eq)
                        continue
                    # Entrée : signal de la barre précédente exécuté au prix courant
                    if position == 0 and buy_sig_shifted.iloc[i]:
                        position    = 1
                        entry_price = price * (1 + FEE)   # frais d'achat
                    elif position == 1 and entry_price > 0:
                        # Stop-loss automatique si perte > seuil configuré
                        sl_triggered = (price < entry_price * (1 - sl_threshold))
                        sell_triggered = sell_sig_shifted.iloc[i]
                        if sl_triggered or sell_triggered:
                            exit_price = price * (1 - FEE)    # frais de vente
                            trade_ret  = (exit_price - entry_price) / entry_price
                            pnl        = trade_ret * eq * position_frac
                            eq        += pnl
                            eq         = max(eq, 0.01)        # floor à 0.01€
                            trades.append(pnl)
                            position    = 0
                            entry_price = 0.0
                    # Equity courante (avec PnL latent si position ouverte)
                    if position == 1 and entry_price > 0:
                        live_eq = eq + (price / entry_price - 1) * eq * position_frac
                    else:
                        live_eq = eq
                    live_eq = max(live_eq, 0.01)
                    equity_curve.append(live_eq)
                    max_eq = max(max_eq, live_eq)

            n_tr    = len(trades)
            wins    = [t for t in trades if t > 0]
            losses  = [t for t in trades if t <= 0]
            final_e = equity_curve[-1] if equity_curve else cap_sz
            tot_ret = (final_e - cap_sz) / cap_sz * 100 if cap_sz > 0 else 0.0
            wr      = len(wins) / n_tr if n_tr > 0 else 0.0
            avg_w   = float(np.mean(wins))   if wins   else 0.0
            avg_l   = float(np.mean(losses)) if losses else 0.0
            # Profit factor : ∞ si aucune perte (on affiche "∞" clairement)
            sum_losses = abs(sum(losses)) if losses else 0.0
            sum_wins   = sum(wins) if wins else 0.0
            pf_txt  = ("∞" if sum_losses == 0 and sum_wins > 0
                       else "0.00" if sum_wins == 0
                       else f"{min(sum_wins / sum_losses, 99.9):.2f}")
            pf_num  = 99.9 if sum_losses == 0 and sum_wins > 0 else (sum_wins / sum_losses if sum_losses > 0 else 0.0)
            # Max drawdown réel sur la courbe d'équité
            eq_arr  = np.array(equity_curve)
            peak    = np.maximum.accumulate(eq_arr)
            max_dd_pct = float(np.min((eq_arr - peak) / np.where(peak > 0, peak, 1))) * 100

            bm1, bm2, bm3, bm4, bm5, bm6 = st.columns(6)
            with bm1: _card("Rendement", f"{tot_ret:+.1f}%",
                            color=C_GREEN if tot_ret >= 0 else C_RED, icon="🏆")
            with bm2: _card("Trades", str(n_tr), color=C_CYAN, icon="⚡")
            with bm3: _card("Win rate", f"{wr*100:.1f}%",
                            color=C_GREEN if wr > 0.5 else C_RED, icon="🎯")
            with bm4: _card("Profit factor", pf_txt,
                            color=C_GREEN if pf_num > 1 else C_RED, icon="💎")
            with bm5: _card("Drawdown max", f"{max_dd_pct:.1f}%",
                            color=C_RED if max_dd_pct < -10 else C_GOLD, icon="⬇️")
            with bm6: _card("Capital final", _eur(final_e), color=C_GOLD, icon="💰")

            if equity_curve:
                fc_eq = C_GREEN if equity_curve[-1] >= cap_sz else C_RED
                fig_sz = go.Figure(go.Scatter(
                    y=equity_curve, mode="lines",
                    line=dict(color=fc_eq, width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(0,255,136,0.07)" if fc_eq == C_GREEN else "rgba(255,51,102,0.07)",
                    hovertemplate="Barre #%{x}<br>Équité : %{y:.2f}€<extra></extra>",
                ))
                fig_sz.add_hline(y=cap_sz, line_dash="dot", line_color=C_SILVER,
                                 annotation_text="Capital initial", annotation_font_color=C_SILVER)
                fig_sz.update_layout(**_chart_layout(320, "Courbe de capital — StratZed"))
                st.plotly_chart(fig_sz, use_container_width=True, config=PLOTLY_CFG)

            if n_tr > 0:
                qa, qb = st.columns(2)
                with qa: _card("Gain moyen / trade",  _eur(avg_w, sign=True) if wins   else "—", color=C_GREEN, icon="🏆")
                with qb: _card("Perte moyenne / trade", _eur(avg_l, sign=True) if losses else "—", color=C_RED,   icon="💔")
            else:
                st.warning("⚠️ Aucun trade généré — élargissez vos conditions d'achat ou de vente.")

        # ── Sauvegarder la stratégie ──────────────────────────────────────────
        st.markdown("<hr>", unsafe_allow_html=True)
        _section_title("Sauvegarder cette stratégie", C_GREEN, "💾")
        sz_nom = st.text_input("Nom de la stratégie", placeholder="Ex : RSI + Z-Score contra-tendance", key="sz_nom")
        if st.button("💾 Sauvegarder dans StratZed", type="primary", key="sz_save"):
            if sz_nom.strip():
                rules_dict = {
                    "buy": {
                        "rsi":    {"enabled": use_rsi_buy,  "threshold": rsi_buy_thr  if use_rsi_buy  else None},
                        "macd":   {"enabled": use_macd_buy},
                        "sma20":  {"enabled": use_sma_buy},
                        "bb_pct": {"enabled": use_bb_buy,   "threshold": bb_buy_thr   if use_bb_buy   else None},
                        "zscore": {"enabled": use_zs_buy,   "threshold": zs_buy_thr   if use_zs_buy   else None},
                        "volume": {"enabled": use_vol_buy},
                    },
                    "sell": {
                        "rsi":    {"enabled": use_rsi_sell,  "threshold": rsi_sell_thr if use_rsi_sell else None},
                        "macd":   {"enabled": use_macd_sell},
                        "bb_pct": {"enabled": use_bb_sell,   "threshold": bb_sell_thr  if use_bb_sell  else None},
                        "zscore": {"enabled": use_zs_sell,   "threshold": zs_sell_thr  if use_zs_sell  else None},
                    },
                }
                try:
                    sm = StrategyManager()
                    if hasattr(sm, "save_strategy"):
                        sm.save_strategy({
                            "name": sz_nom, "type": "StratZed",
                            "description": f"StratZed — {p['symbol']}",
                            "rules": str(rules_dict),
                            "created": datetime.now().isoformat(),
                        })
                    st.success(f"✅ Stratégie « {sz_nom} » sauvegardée !")
                    st.session_state["shared_capital"] = cap_sz
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur sauvegarde : {e}")
            else:
                st.warning("Entrez un nom pour la stratégie.")

    with sz_tab2:
        _section_title("Mes stratégies StratZed", C_GOLD, "📚")
        try:
            sm_list = StrategyManager()
            saved   = sm_list.list_strategies() if hasattr(sm_list, "list_strategies") else []
            sz_strats = [s for s in saved if isinstance(s, dict) and s.get("type") == "StratZed"]
        except Exception:
            sz_strats = []

        if sz_strats:
            st.dataframe(pd.DataFrame(sz_strats), use_container_width=True, hide_index=True)
        else:
            st.markdown(
                f"<div style='background:{C_CARD};border:1px dashed {C_GOLD}33;"
                f"border-radius:14px;padding:28px;text-align:center;color:{C_MUTED}'>"
                f"⚗️ Aucune stratégie StratZed sauvegardée.<br>"
                f"<span style='font-size:0.82rem'>Composez votre stratégie dans "
                f"<b style='color:{C_GOLD}'>⚗️ Composer & Backtester</b> puis sauvegardez-la.</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        _section_title("Presets StratZed", C_CYAN, "🎓")
        presets = [
            {"Nom":"⚗️ RSI + Z-Score",   "Achat":"RSI < 35 ET Z-Score < −1.0","Vente":"RSI > 70",               "Style":"Contra-tendance","Risque":"⭐⭐"},
            {"Nom":"⚗️ MACD + Volume",   "Achat":"MACD ↑ ET Volume > 1.2×",   "Vente":"MACD ↓",                 "Style":"Momentum",       "Risque":"⭐⭐"},
            {"Nom":"⚗️ Bollinger Squeeze","Achat":"BB% < 20% ET RSI < 45",     "Vente":"BB% > 80%",              "Style":"Retournement",   "Risque":"⭐⭐⭐"},
            {"Nom":"⚗️ Triple confirm",  "Achat":"SMA20 ↑ ET MACD ↑ ET RSI<65","Vente":"RSI > 72 OU MACD ↓",    "Style":"Tendance forte", "Risque":"⭐"},
        ]
        st.dataframe(pd.DataFrame(presets), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="⚡ THE ZEDICUS v3",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(FONT_PRELOAD, unsafe_allow_html=True)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # Injection JS pour mesurer et compenser la hauteur exacte du header Streamlit
    st.markdown("""
<style>
/* Garantit que le contenu commence SOUS le header — fix universel Streamlit 1.50 */
section[data-testid="stMain"] > div:first-child {
    padding-top: 1rem !important;
}
div[data-testid="stDecoration"] {
    display: none !important;
}

/* ── Barre de navigation flottante (haut / bas) ── */
#zed-scroll-nav {
    position: fixed;
    right: max(18px, env(safe-area-inset-right, 0px));
    bottom: calc(80px + env(safe-area-inset-bottom, 0px));
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.zed-scroll-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 1.5px solid rgba(0,212,255,0.5);
    background: linear-gradient(135deg, #0a1628, #060f20);
    color: #00D4FF;
    font-size: 1.2rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 14px rgba(0,212,255,0.25), 0 4px 12px rgba(0,0,0,0.5);
    transition: all 0.2s ease;
    text-decoration: none;
    line-height: 1;
}
.zed-scroll-btn:hover {
    background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.05));
    border-color: rgba(0,212,255,0.9);
    box-shadow: 0 0 22px rgba(0,212,255,0.5), 0 4px 16px rgba(0,0,0,0.5);
    transform: scale(1.1);
    color: #ffffff;
}
#zed-scroll-indicator {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 1.5px solid rgba(0,212,255,0.2);
    background: rgba(6,15,32,0.85);
    color: rgba(0,212,255,0.7);
    font-size: 0.6rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
</style>

<div id="zed-scroll-nav">
  <button class="zed-scroll-btn" onclick="zedScrollTo(0)" title="Haut de page" aria-label="Retour en haut de page">▲</button>
  <div id="zed-scroll-indicator" aria-live="polite" aria-label="Position de défilement">TOP</div>
  <button class="zed-scroll-btn" onclick="zedScrollTo('bottom')" title="Bas de page" aria-label="Aller en bas de page">▼</button>
</div>

<script>
(function() {
  /* Nettoyer les anciens listeners si Streamlit réinjecte le script */
  if (window._zedScrollHandler && window._zedScrollEl) {
    window._zedScrollEl.removeEventListener('scroll', window._zedScrollHandler, {passive:true});
  }
  if (window._zedScrollHandler) {
    window.removeEventListener('resize', window._zedScrollHandler, {passive:true});
  }
  if (window.visualViewport && window._zedVvpHandler) {
    window.visualViewport.removeEventListener('resize', window._zedVvpHandler, {passive:true});
  }

  /* Conteneur qui scroll réellement — stMain en priorité (Streamlit 1.50) */
  function getScrollEl() {
    var candidates = [
      document.querySelector('[data-testid="stMain"]'),
      document.querySelector('[data-testid="stAppViewContainer"]'),
      document.scrollingElement,
      document.documentElement
    ];
    for (var i = 0; i < candidates.length; i++) {
      var el = candidates[i];
      if (!el) continue;
      if (el.scrollHeight > el.clientHeight + 2) return el;
    }
    return document.querySelector('[data-testid="stMain"]')
        || document.querySelector('[data-testid="stAppViewContainer"]')
        || document.scrollingElement
        || document.documentElement;
  }

  function scrollMaxTop(el) {
    if (!el) return 0;
    return Math.max(0, (el.scrollHeight || 0) - (el.clientHeight || 0));
  }

  /* Scroll respectant prefers-reduced-motion */
  window.zedScrollTo = function(target) {
    var el = getScrollEl();
    var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var behavior = reducedMotion ? 'auto' : 'smooth';
    var top = (target === 'bottom') ? scrollMaxTop(el) : 0;
    try {
      el.scrollTo({top: top, behavior: behavior});
    } catch(e) {
      el.scrollTop = top;
    }
    requestAnimationFrame(updateIndicator);
  };

  /* Indicateur de position */
  var ind = document.getElementById('zed-scroll-indicator');
  function updateIndicator() {
    if (!ind) { ind = document.getElementById('zed-scroll-indicator'); }
    if (!ind) return;
    var el = getScrollEl();
    var scrolled = el.scrollTop || 0;
    var maxScroll = scrollMaxTop(el);
    var pct = maxScroll > 0 ? Math.min(Math.round(scrolled / maxScroll * 100), 100) : 0;
    ind.textContent = pct > 0 ? pct + '%' : 'TOP';
  }

  window._zedScrollHandler = updateIndicator;
  var scrollEl = getScrollEl();
  window._zedScrollEl = scrollEl;
  if (scrollEl) {
    scrollEl.addEventListener('scroll', updateIndicator, {passive: true});
  }
  window.addEventListener('resize', updateIndicator, {passive: true});
  if (window.visualViewport) {
    window._zedVvpHandler = updateIndicator;
    window.visualViewport.addEventListener('resize', updateIndicator, {passive: true});
  }

  /* Recalcul après injection Plotly / tableaux (rerun Streamlit) */
  var mainRoot = document.querySelector('[data-testid="stMain"]');
  if (mainRoot && !window._zedMutationObserver) {
    window._zedMutationObserver = new MutationObserver(function() {
      requestAnimationFrame(updateIndicator);
    });
    window._zedMutationObserver.observe(mainRoot, {
      childList: true,
      subtree: true,
      attributes: true,
      characterData: true
    });
  }

  /* Pause animations quand onglet masqué — économie batterie mobile */
  document.addEventListener('visibilitychange', function() {
    document.body.style.setProperty('--anim-state', document.hidden ? 'paused' : 'running');
  });

  /* Auto-collapse sidebar sur mobile (< 768px) — une seule fois par session */
  if (window.innerWidth < 768 && !sessionStorage.getItem('zed_sidebar_done')) {
    setTimeout(function() {
      var btn = document.querySelector('[data-testid="collapsedControl"]');
      if (btn) { btn.click(); sessionStorage.setItem('zed_sidebar_done', '1'); }
    }, 300);
  }

  updateIndicator();
})();
</script>
""", unsafe_allow_html=True)

    try:
        fb = FirebaseManager()
        fb.log_strategy_run(symbol="dashboard", strategy="view", params={})
    except Exception:
        pass

    params = render_sidebar()

    main_tab_labels = [
        "🏠 Accueil", "🌍 Marché",  "📊 Analyse",   "🔍 Screener",
        "📡 Signaux", "🤖 Bot",     "💼 Portef.",    "⚠️ Risque",
        "📈 Perfo",   "🔬 Backtest","📅 Calendrier",
        "🎯 Stratégies","🔔 Alertes","⚗️ StratZed","❓ Aide",
    ]

    handlers = [
        tab_accueil,   tab_marche,   tab_analyse,    tab_screener,
        tab_signaux,   tab_bot,      tab_portefeuille, tab_risque,
        tab_performance, tab_backtest, tab_calendrier,
        tab_strategies, tab_alertes, tab_stratzed, tab_aide,
    ]

    if "zed_main_tab" not in st.session_state:
        st.session_state.zed_main_tab = main_tab_labels[0]

    st.segmented_control(
        "Navigation principale",
        options=main_tab_labels,
        key="zed_main_tab",
        label_visibility="collapsed",
    )

    active_tab = st.session_state.zed_main_tab
    if active_tab not in main_tab_labels:
        active_tab = main_tab_labels[0]
        st.session_state.zed_main_tab = active_tab

    active_handler = handlers[main_tab_labels.index(active_tab)]
    try:
        active_handler(params)
    except Exception:
        st.markdown(
            f"<div style='background:{C_RED}0d;border:1px solid {C_RED}44;"
            f"border-radius:12px;padding:16px;color:{C_RED}'>"
            f"⚠️ Une erreur s'est produite dans cet onglet."
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.expander("🔧 Détails techniques"):
            st.code(traceback.format_exc(), language="python")


if __name__ == "__main__":
    main()
