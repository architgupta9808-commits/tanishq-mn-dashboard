"""
============================================================================
 TANISHQ MALVIYA NAGAR — PERFORMANCE, INCENTIVE & TEAM COMMAND CENTRE
 Single-file Streamlit application (app.py)
----------------------------------------------------------------------------
 Run:  streamlit run app.py
 Needs (same folder):  Sales_Data.xlsx   +   ghs_OPENING.xlsx
============================================================================

 BUSINESS LOGIC CHEAT-SHEET (read before editing):
 -------------------------------------------------
 STUDDED      : a sales row is studded  <=>  FLAG == 'S'   (final rule)
 PLAIN/OTHER  : FLAG in P / C / O        -> not studded
 VOLUME       : WT (grams). Negative WT = return / credit note.
 VALUE        : CMTOTAL (lakhs) = full customer invoice value.
                AMT (lakhs) ~ making charge / value-add only (do NOT use as ticket).
 HVS          : High-Value Studded piece -> FLAG=='S' AND CMTOTAL >= HVS_THRESHOLD
                (configurable in the Admin panel; default = Rs 5 lakh).
 RSO          : ALWAYS attribute on 'RSO CHANGE' (corrected salesperson).
 GHS / RGA    : live book lives in ghs_OPENING.xlsx.
                live account  -> REFUND DATE is null
                redeemed       -> REFUND DATE present
                monthly opens  -> OP-MONTH ; monthly redeems -> REF-MONTH

 INCENTIVE STRUCTURE (official — Tanishq MN):
   Studded pieces / month :  10-19 -> 500 | 20-29 -> 1500 | 30 -> 5000 |
                             31+   -> 5000 + 200*(pieces-30)   (uncapped)
   HVS pieces             :  flat 750 each
   GHS+RGA opens / month  :  10-14 -> 1000 | 15-19 -> 2000 | 20+ -> 3000
   Sludge                 :  flat 1% of selling value of each aged piece moved
   Coach bonus            :  500 to coach when mentee hits 30+ studded
   Team studded gate      :  +1000 to every target-hitter IF store studded share >= 30%
   Teaching stipend       :  Ritesh 2500/mo (studded), Nikhar 2500/mo (GHS)
   Pool                   :  Rs 19.8 L / yr, fully funded only at 200 Cr & 30% studded;
                             scales down below 30% (Admin can toggle the gate).
============================================================================
"""

import os
import datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
try:
    from analytics_engine import (
        load_hist, load_stock, yoy_summary, monthly_seasonality,
        customer_rfm, rso_history, stock_summary, stock_push_recommendations,
        october_forecast, studded_decline_alert, FESTIVAL_MONTHS, MONTH_NAMES,
    )
    AE_AVAILABLE = True
except ImportError:
    AE_AVAILABLE = False
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# 0. PAGE CONFIG + THEME
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Tanishq MN — Command Centre",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# PWA meta tags — enable "Add to Home Screen" on mobile browsers
st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#C9A227">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Tanishq MN">
<meta name="mobile-web-app-capable" content="yes">
<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js');
}
</script>
""", unsafe_allow_html=True)

GOLD = "#C9A227"          # antique gold — primary accent
GOLD_SOFT = "#E0C868"     # soft gold for hovers
GOLD_DEEP = "#A37E12"     # darker gold for text on light
RUBY = "#7B1E3B"          # Tanishq deep maroon — headers, sidebar
RUBY_LT = "#A8324A"       # lighter ruby accent
EMERALD = "#1B7A5A"       # gemstone green — positive
IVORY = "#FBF7F0"         # warm page background
CREAM = "#FFFCF7"         # card surface
SAND = "#F1E8DA"          # subtle panel / divider
ESPRESSO = "#3E2723"      # warm body text
MUTED = "#8A7A6B"         # muted captions

# Back-compat aliases (older code referenced these names)
NAVY = RUBY
NAVY2 = RUBY_LT
INK = IVORY
PAPER = CREAM
GREEN = EMERALD
AMBER = "#D08A1E"
RED = "#C0392B"

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Inter:wght@300;400;500;600;700&display=swap');

  /* ─── ROOT TOKENS ─────────────────────────────────────────────── */
  :root {{
    --gold:      {GOLD};
    --gold-deep: {GOLD_DEEP};
    --ruby:      {RUBY};
    --ruby-lt:   {RUBY_LT};
    --emerald:   {EMERALD};
    --ivory:     {IVORY};
    --cream:     {CREAM};
    --sand:      {SAND};
    --espresso:  {ESPRESSO};
    --muted:     {MUTED};
    --shadow-sm: 0 2px 8px rgba(62,39,35,0.08);
    --shadow-md: 0 4px 20px rgba(62,39,35,0.12);
    --shadow-lg: 0 8px 40px rgba(62,39,35,0.16);
    --radius-sm: 10px;
    --radius-md: 16px;
    --radius-lg: 24px;
    --border: 1px solid rgba(201,162,39,0.18);
  }}

  /* ─── PAGE BACKGROUND — layered warm gradient ─────────────────── */
  .stApp {{
    background:
      radial-gradient(ellipse 1400px 500px at 100% -5%, rgba(201,162,39,0.12) 0%, transparent 55%),
      radial-gradient(ellipse 1000px 600px at -5% 110%, rgba(123,30,59,0.09) 0%, transparent 50%),
      radial-gradient(ellipse 600px 400px at 50% 50%, rgba(241,232,218,0.40) 0%, transparent 60%),
      {IVORY};
    font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  }}

  /* ─── FORCE READABLE TEXT (safety net against dark system themes) ─ */
  .stApp, .main, .block-container,
  .block-container p, .block-container li, .block-container label,
  .block-container .stMarkdown, .stMarkdown p,
  [data-testid="stMetricLabel"], [data-testid="stWidgetLabel"] label,
  .stRadio label, .stSelectbox label, .stTextInput label, .stNumberInput label,
  .stCheckbox label, .stCaption, .stDataFrame {{ color: {ESPRESSO}; }}
  .block-container .stCaption, .block-container small {{ color: {MUTED} !important; }}

  /* ─── SIDEBAR ─────────────────────────────────────────────────── */
  [data-testid="stSidebar"] {{
    background:
      linear-gradient(180deg,
        rgba(123,30,59,0.97) 0%,
        rgba(90,20,40,0.99) 60%,
        rgba(62,10,28,1.00) 100%) !important;
    border-right: none !important;
    box-shadow: 4px 0 32px rgba(62,39,35,0.25);
  }}
  [data-testid="stSidebar"] * {{ color: #F5E8D0 !important; }}
  [data-testid="stSidebar"] .stRadio > label span {{
    background: rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
    padding: 6px 12px !important;
    transition: background 0.2s;
  }}
  [data-testid="stSidebar"] .stRadio > label span:hover {{
    background: rgba(201,162,39,0.20) !important;
  }}
  [data-testid="stSidebar"] .stRadio [aria-checked="true"] span {{
    background: rgba(201,162,39,0.30) !important;
    border-left: 3px solid {GOLD} !important;
  }}
  [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {{
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(201,162,39,0.30) !important;
    border-radius: 8px !important;
    color: #F5E8D0 !important;
  }}
  [data-testid="stSidebar"] .stDivider {{
    border-color: rgba(201,162,39,0.20) !important;
  }}
  [data-testid="stSidebar"] button {{
    background: rgba(201,162,39,0.15) !important;
    border: 1px solid rgba(201,162,39,0.30) !important;
    color: {GOLD} !important;
    border-radius: 8px !important;
  }}
  [data-testid="stSidebar"] button:hover {{
    background: rgba(201,162,39,0.28) !important;
  }}
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {{ color: #F4D77E !important; }}
  [data-testid="stSidebar"] .stSelectbox svg {{ fill: {GOLD} !important; }}

  /* ─── MAIN CONTENT AREA ──────────────────────────────────────── */
  .main .block-container {{
    padding: 1.5rem 2.5rem 3rem;
    max-width: 1400px;
  }}

  /* ─── SECTION HEADERS ─────────────────────────────────────────── */
  h1, h2, h3, h4 {{
    font-family: 'Cormorant Garamond', serif !important;
    color: {RUBY} !important;
    letter-spacing: -0.3px;
  }}
  h1 {{ font-size: 38px !important; font-weight: 700 !important; }}
  h2 {{ font-size: 28px !important; font-weight: 600 !important; }}
  h3 {{ font-size: 22px !important; font-weight: 600 !important; }}

  /* ─── PAGE TITLE BANNER ───────────────────────────────────────── */
  .page-title-bar {{
    background: linear-gradient(135deg,
      rgba(123,30,59,0.06) 0%,
      rgba(201,162,39,0.04) 100%);
    border: var(--border);
    border-radius: var(--radius-lg);
    padding: 20px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  .page-title-icon {{
    font-size: 28px;
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, {RUBY}, {RUBY_LT});
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(123,30,59,0.30);
  }}
  .page-title-text {{ flex: 1; }}
  .page-title-main {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 28px;
    font-weight: 700;
    color: {RUBY};
    line-height: 1.1;
  }}
  .page-title-sub {{
    font-size: 13px;
    color: {MUTED};
    margin-top: 2px;
  }}

  /* ─── KPI CARDS ──────────────────────────────────────────────── */
  .kpi-card {{
    background: linear-gradient(145deg, {CREAM} 0%, rgba(255,252,247,0.95) 100%);
    border: var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    height: 100%;
  }}
  .kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {GOLD}, {RUBY_LT});
    border-radius: var(--radius-md) var(--radius-md) 0 0;
  }}
  .kpi-card:hover {{
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }}
  .kpi-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: {MUTED};
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .kpi-value {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 32px;
    font-weight: 700;
    color: {RUBY};
    line-height: 1.05;
    word-break: break-word;
    margin-bottom: 4px;
  }}
  .kpi-sub {{
    font-size: 12px;
    color: {MUTED};
    line-height: 1.45;
    margin-top: 2px;
  }}

  /* ─── METRIC ANIMATIONS ────────────────────────────────────────── */
  @keyframes slideUp {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .kpi-card {{ animation: slideUp 0.35s ease both; }}
  .kpi-card:nth-child(1) {{ animation-delay: 0.04s; }}
  .kpi-card:nth-child(2) {{ animation-delay: 0.08s; }}
  .kpi-card:nth-child(3) {{ animation-delay: 0.12s; }}
  .kpi-card:nth-child(4) {{ animation-delay: 0.16s; }}
  .kpi-card:nth-child(5) {{ animation-delay: 0.20s; }}
  .kpi-card:nth-child(6) {{ animation-delay: 0.24s; }}

  /* ─── FROZEN TOP BAR ──────────────────────────────────────────── */
  .frozen-bar {{
    background: linear-gradient(90deg,
      rgba(255,252,247,0.97) 0%,
      rgba(251,247,240,0.95) 100%);
    border: var(--border);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    margin-bottom: 18px;
    box-shadow: var(--shadow-sm);
  }}

  /* ─── RSO HERO CARD ───────────────────────────────────────────── */
  .rso-hero {{
    background: linear-gradient(120deg, {RUBY} 0%, #8E2440 55%, #A8324A 100%);
    border: 1px solid rgba(201,162,39,0.45);
    border-radius: var(--radius-lg);
    padding: 24px 28px;
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(123,30,59,0.22);
  }}
  .rso-hero::before {{
    content: '';
    position: absolute;
    top: -40px; right: -30px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(201,162,39,0.30), transparent 68%);
  }}
  .rso-hero::after {{
    content: '◆';
    position: absolute;
    bottom: -18px; right: 24px;
    font-size: 120px;
    color: rgba(255,255,255,0.05);
    line-height: 1;
  }}
  .rso-avatar {{
    width: 76px; height: 76px;
    border-radius: 22px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: 700;
    color: {RUBY};
    font-family: 'Cormorant Garamond', serif;
    flex-shrink: 0;
    box-shadow: 0 6px 20px rgba(0,0,0,0.25), inset 0 0 0 2px rgba(255,255,255,0.4);
  }}
  .rso-greeting {{ font-size: 14px; color: #F0D9B5; margin: 0; font-weight: 500; }}
  .rso-name {{
    font-size: 32px; font-weight: 700;
    color: #FFF8EC;
    font-family: 'Cormorant Garamond', serif;
    margin: 2px 0; line-height: 1.05;
  }}
  .rso-role-pill {{
    display: inline-block;
    background: rgba(255,248,236,0.16);
    color: #F4D77E;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px; font-weight: 600;
    border: 1px solid rgba(244,215,126,0.35);
  }}

  /* ─── STAT CHIPS (in RSO hero) ────────────────────────────────── */
  .stat-chip {{
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(244,215,126,0.30);
    border-radius: 16px;
    padding: 11px 16px;
    text-align: center;
    backdrop-filter: blur(4px);
  }}
  .stat-chip-val {{
    font-size: 24px; font-weight: 700;
    color: #F4D77E;
    font-family: 'Cormorant Garamond', serif;
    line-height: 1;
  }}
  .stat-chip-lbl {{
    font-size: 10px; color: #EAD3B0;
    text-transform: uppercase; letter-spacing: 0.6px;
    margin-top: 5px;
  }}

  /* ─── TABS ─────────────────────────────────────────────────────── */
  [data-testid="stTabs"] [role="tab"] {{
    font-family: Inter, sans-serif;
    font-size: 13px; font-weight: 500;
    color: {MUTED};
    padding: 10px 18px;
    border-radius: 10px 10px 0 0;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }}
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: {RUBY};
    border-bottom: 2px solid {GOLD};
    background: rgba(201,162,39,0.06);
    font-weight: 600;
  }}
  [data-testid="stTabs"] [role="tab"]:hover {{
    color: {RUBY};
    background: rgba(201,162,39,0.04);
  }}
  /* Legacy tab selector (older Streamlit versions) */
  .stTabs [data-baseweb="tab-list"] {{ gap: 4px; flex-wrap: wrap; border-bottom: 2px solid {SAND}; }}
  .stTabs [data-baseweb="tab"] {{
    background: {SAND}; border-radius: 10px 10px 0 0;
    padding: 9px 18px; color: {RUBY}; font-size: 13px; font-weight: 600;
  }}
  .stTabs [aria-selected="true"] {{
    background: linear-gradient(180deg,{GOLD},{GOLD_DEEP}); color: #fff;
  }}

  /* ─── BUTTONS ──────────────────────────────────────────────────── */
  .stButton > button {{
    background: linear-gradient(135deg, {GOLD} 0%, {GOLD_DEEP} 100%);
    color: #FFF; border: none; border-radius: 10px;
    font-weight: 600; font-size: 13px; padding: 8px 20px;
    box-shadow: 0 4px 12px rgba(201,162,39,0.35);
    transition: all 0.2s ease; letter-spacing: 0.3px;
  }}
  .stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(201,162,39,0.45);
    background: linear-gradient(135deg, #D4AA2C 0%, {GOLD} 100%);
  }}

  /* ─── DATA TABLES ──────────────────────────────────────────────── */
  [data-testid="stDataFrame"] {{
    border-radius: var(--radius-md) !important;
    border: var(--border) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow-sm) !important;
  }}
  [data-testid="stDataFrame"] th {{
    background: linear-gradient(135deg, {RUBY}, {RUBY_LT}) !important;
    color: #FFF !important;
    font-size: 11px !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    padding: 10px 12px !important;
  }}
  [data-testid="stDataFrame"] tr:nth-child(even) td {{
    background: rgba(201,162,39,0.04) !important;
  }}

  /* ─── METRIC WIDGET ───────────────────────────────────────────── */
  div[data-testid="stMetricValue"] {{
    color: {RUBY}; font-family: 'Cormorant Garamond', serif;
  }}

  /* ─── INPUTS ─────────────────────────────────────────────────── */
  .stTextInput input {{
    background: {CREAM} !important;
    border: var(--border) !important;
    border-radius: 10px !important;
    color: {ESPRESSO} !important;
    font-size: 13px !important;
  }}
  .stTextInput input:focus {{
    border-color: {GOLD} !important;
    box-shadow: 0 0 0 3px rgba(201,162,39,0.12) !important;
  }}

  /* ─── INCENTIVE TABLE ROWS ─────────────────────────────────────── */
  .incentive-row {{
    display: flex; justify-content: space-between;
    padding: 9px 2px; gap: 10px;
    border-bottom: 1px dashed rgba(201,162,39,0.28);
  }}
  .incentive-row > span:first-child {{ flex: 1; min-width: 0; color: {ESPRESSO}; }}

  /* ─── PILLS & BADGES ───────────────────────────────────────────── */
  .pill {{
    display: inline-block; padding: 3px 11px;
    border-radius: 20px; font-size: 11px; font-weight: 600;
  }}

  /* ─── INSIGHT / WARNING BANNERS ────────────────────────────────── */
  .insight-banner {{
    background: linear-gradient(135deg, rgba(27,122,90,0.08) 0%, rgba(27,122,90,0.04) 100%);
    border: 1px solid rgba(27,122,90,0.20);
    border-left: 4px solid {EMERALD};
    border-radius: var(--radius-md); padding: 14px 18px; margin: 12px 0;
  }}
  .warning-banner {{
    background: linear-gradient(135deg, rgba(208,138,30,0.08) 0%, rgba(208,138,30,0.04) 100%);
    border: 1px solid rgba(208,138,30,0.25);
    border-left: 4px solid {AMBER};
    border-radius: var(--radius-md); padding: 14px 18px; margin: 12px 0;
  }}
  .danger-banner {{
    background: linear-gradient(135deg, rgba(192,57,43,0.08) 0%, rgba(192,57,43,0.04) 100%);
    border: 1px solid rgba(192,57,43,0.20);
    border-left: 4px solid {RED};
    border-radius: var(--radius-md); padding: 14px 18px; margin: 12px 0;
  }}

  /* ─── GOLD RULE ─────────────────────────────────────────────────── */
  .gold-rule {{
    height: 2px;
    background: linear-gradient(90deg, transparent, {GOLD}, {GOLD_DEEP}, transparent);
    border: none; margin: 20px 0; border-radius: 2px;
  }}

  /* ─── EXPANDERS ─────────────────────────────────────────────────── */
  [data-testid="stExpander"] {{
    border: var(--border) !important;
    border-radius: var(--radius-md) !important;
    background: {CREAM} !important;
  }}
  [data-testid="stExpander"] summary {{
    font-weight: 600 !important; color: {RUBY} !important;
  }}

  /* ─── MISC HELPERS ──────────────────────────────────────────────── */
  .gold {{ color: {GOLD_DEEP}; font-weight: 600; }}
  .ruby {{ color: {RUBY}; }}
  .muted {{ color: {MUTED}; }}
  .small-muted {{ color: {MUTED}; font-size: 12px; letter-spacing: 0.4px; }}

  /* ─── MOBILE ────────────────────────────────────────────────────── */
  @media (max-width: 640px) {{
    .main .block-container {{ padding: 1rem 0.8rem 2rem; }}
    h1 {{ font-size: 28px !important; }}
    h2 {{ font-size: 22px !important; }}
    .kpi-value {{ font-size: 26px; }}
    .kpi-card {{ padding: 14px 16px; }}
    .rso-hero {{ padding: 18px; }}
    .rso-name {{ font-size: 26px; }}
    .rso-avatar {{ width: 60px; height: 60px; font-size: 26px; border-radius: 16px; }}
    .stat-chip-val {{ font-size: 20px; }}
    .page-title-main {{ font-size: 22px; }}
    [data-testid="stHorizontalBlock"] > div {{
      min-width: 45% !important;
      flex-basis: 45% !important;
    }}
  }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 1. CONSTANTS — incentive engine, RSO intelligence, roles
# ---------------------------------------------------------------------------
HVS_THRESHOLD_DEFAULT = 5.0       # lakhs (CMTOTAL) for a studded piece to count as HVS
ANNUAL_POOL = 19_80_000           # Rs 19.8 L RSO pool
STORE_TARGET_CR = 200             # Rs Cr turnover for full pool
STUDDED_SHARE_GATE = 30.0         # % studded share gate

TEACHING_STIPEND = {"RITESH BHATNAGAR": 2500, "NIKHAR AGARWAL": 2500}
COACH_BONUS = 500
TEAM_GATE_BONUS = 1000

# --- RSO intelligence layer (from the Multiplier work) ------------------------
# native_genius / pressure / team relationship / coaching pairing.
RSO_PROFILE = {
    "RAKESH JAIN":      dict(role="Sales Anchor",     archetype="The Anchor",
        pressure="RISE", team="Influential", coach=None, mentees=["KALYANI SONI", "NANDNI TIWARI"],
        genius="Finishes target in 12 days, huge loyal customer base, most influential on the floor.",
        watch="Own studded share only ~26% — a gold engine. Can crowd out juniors."),
    "MANDA BONDE":      dict(role="Volume Engine",    archetype="The Volume Engine",
        pressure="RISE", team="Lone Wolf", coach=None, mentees=[],
        genius="Highest total productivity, strong repeat customers.",
        watch="Lowest studded share among top sellers — push diamond, same volume."),
    "SUNITA UDAY":      dict(role="High-Value Specialist", archetype="Specialist→Coach",
        pressure="RISE/FREEZE", team="Influential", coach=None, mentees=["ARCHANA SINGH"],
        genius="2nd best RSO; top studded share; brilliant at high-value & sludge.",
        watch="Cherry-picks only high-value customers; just scrapes target."),
    "RITESH BHATNAGAR": dict(role="Studded Coach",    archetype="Specialist→Coach",
        pressure="DEFLECT", team="Social", coach=None, mentees=["MANDA BONDE", "INDRALAL PATEL"],
        genius="Certified diamond expert — reads real vs synthetic instantly. THE studded teacher.",
        watch="Deflects ownership; frame coaching as an honour, not a chore."),
    "RUCHI AGARWAL":    dict(role="Sludge Squad Lead", archetype="Specialist→Coach",
        pressure="DEFLECT", team="Social", coach=None, mentees=[],
        genius="Highest studded-piece average; strong sludge & HCG.",
        watch="Explicitly underutilised — sits in comfort zone."),
    "NIKHAR AGARWAL":   dict(role="GHS Coach",        archetype="Specialist→Coach",
        pressure="RISE", team="Social", coach=None, mentees=["ABHISHEK SAINI", "KALYANI SONI"],
        genius="GHS/RGA king and highest total productivity. Receptive, coachable.",
        watch="Studded focus can plateau — keep stretching to 22+ studded."),
    "SANDHYA SONI":     dict(role="Volume Engine",    archetype="The Volume Engine",
        pressure="RISE", team="Lone Wolf", coach=None, mentees=[],
        genius="Fast, highest GHS in store, reputation for studded conversion.",
        watch="Say-do gap: 'good at studded' but sitting ~26% share."),
    "ANITA VERMA":      dict(role="Volume Engine",    archetype="The Volume Engine",
        pressure="RISE", team="Social", coach=None, mentees=[],
        genius="High volume, rises when pushed, good with people.",
        watch="Handle with unusual care — carrying heavy personal loss. Never pressure."),
    "INDRALAL PATEL":   dict(role="Quiet All-Rounder", archetype="The Volume Engine",
        pressure="DEFLECT", team="Invisible", coach="RITESH BHATNAGAR", mentees=[],
        genius="Quietly does big volume with nobody noticing. Dependable.",
        watch="Invisible & under-appreciated — make him seen in the War Room."),
    "AMOL MITTAL":      dict(role="Veteran", archetype="The Veteran to Convince",
        pressure="DEFLECT", team="Social", coach=None, mentees=[],
        genius="10-yr veteran with good ideas, decent studded share.",
        watch="Believes 'more stock = more sales'; debate with data, give one experiment."),
    "ABHISHEK SAINI":   dict(role="Talent to Save", archetype="The Talent to Save",
        pressure="FREEZE", team="Social", coach="NIKHAR AGARWAL", mentees=[],
        genius="HIGHEST studded share in the store. Rare diamond instinct.",
        watch="On notice for lowest GHS. Freezes — one Liberator conversation, pair with Nikhar."),
    "KALYANI SONI":     dict(role="Talent to Save", archetype="The Talent to Save",
        pressure="FREEZE", team="Invisible", coach="NIKHAR AGARWAL", mentees=[],
        genius="High studded share, a 33-piece best month — real ceiling.",
        watch="Struggles with account-opening; freezes. Safety first, never shout."),
    "ARCHANA SINGH":    dict(role="One to Protect", archetype="The One to Protect",
        pressure="FREEZE", team="Invisible", coach="SUNITA UDAY", mentees=[],
        genius="Strong studded share plus PJWS & HCG.",
        watch="Caregiver at home (parents' Alzheimer's). Flexibility + protect, don't pile on."),
    "NANDNI TIWARI":    dict(role="Rising One", archetype="The Rising One",
        pressure="RISE", team="Social", coach="RAKESH JAIN", mentees=[],
        genius="Turning around fast; rises under pressure. Trajectory up.",
        watch="Lowest studded pieces — ride the momentum with public credit."),
    "RANJANA GUBRELAY": dict(role="Hard Decision", archetype="The Hard Decision",
        pressure="DEFLECT", team="Social", coach=None, mentees=[],
        genius="Was genuinely good at PJWS & HCG once.",
        watch="Lowest volume; constant leaves cut off walk-ins. Attendance conversation, once."),
}
DEFAULT_PROFILE = dict(role="RSO", archetype="—", pressure="—", team="—",
    coach=None, mentees=[], genius="—", watch="—")

PRESSURE_COLOR = {"RISE": GREEN, "FREEZE": "#5B8DEF", "DEFLECT": AMBER,
                  "RISE/FREEZE": "#9A7BD0", "—": "#666"}

# --- Roles / logins (prototype, hardcoded) -----------------------------------
MANAGEMENT_USERS = {
    "admin":   dict(pwd="admin",   role="Admin",          name="Admin"),
    "swaroop": dict(pwd="mn2026",  role="Store Manager",  name="Swaroop"),
    "rashmi":  dict(pwd="fm2026",  role="Floor Manager",  name="Rashmi"),
    "deepesh": dict(pwd="fm2026",  role="Floor Manager",  name="Deepesh"),
    "archit":  dict(pwd="md2026",  role="MD",             name="Archit"),
    "rakesh":  dict(pwd="md2026",  role="MD",             name="Rakesh"),
}
RSO_PWD = "rso2026"   # shared simple password for every RSO login (prototype)

# --- RSO name normalisation (handles typos / spelling variants across Excel files) ---
RSO_NAME_MAP = {
    "NEHA GOYAL":    "NEHA GOEL",   # sales file variant → targets canonical
    "NEHA GOEL":     "NEHA GOEL",
    "PRACHI SHARMA": "PRACHI SHARMA",
    "SUKUMAR SARKAR":"SUKUMAR SARKAR",
    # Add new variants here: "EXCEL SPELLING": "CANONICAL SPELLING"
}

def normalize_rso_name(name: str) -> str:
    """Return canonical RSO name, resolving known spelling variants."""
    n = str(name).strip().upper()
    return RSO_NAME_MAP.get(n, n)

# ---------------------------------------------------------------------------
# 2. DATA LOADING  (both Excel files, cached, manual refresh aware)
# ---------------------------------------------------------------------------
SALES_FILE = "Sales_Data.xlsx"
GHS_FILE = "ghs_OPENING.xlsx"
TARGETS_FILE = "targets.xlsx"
SLUDGE_FILE = "sludge.xlsx"
CN_FILE = "pendingCN.xlsx"

# GHS/RGA account maturity windows (days since opening before it goes inactive)
GHS_INACTIVE_DAYS = 400
RGA_INACTIVE_DAYS = 330

# Product catalogue image endpoint. The image name is MID(itemcode, 3, 7) + ".jpg".
IMAGE_BASE = "https://jewbridge.titanjew.in/CatalogImages/api/ImageFetch/?Type=ProductImages&ImageName="


def theme_code(itemcode) -> str:
    """Excel MID(code, 3, 7): characters 3..9 (1-indexed) -> 7-char theme code."""
    s = str(itemcode).strip()
    return s[2:9] if len(s) >= 9 else s


def product_image_url(itemcode) -> str:
    """Full catalogue image URL for a given SKU / item code."""
    return f"{IMAGE_BASE}{theme_code(itemcode)}.jpg"


@st.cache_data(show_spinner=False)
def load_targets(_token: float) -> tuple:
    """Load RSO-wise and store targets from targets.xlsx. All RSO targets are in VALUE (lakhs)."""
    rso_targets = pd.read_excel(TARGETS_FILE, sheet_name="rso wise targets")
    store_targets = pd.read_excel(TARGETS_FILE, sheet_name="store targets")
    # Strip whitespace from column names (RSO sheet has '  PLAIN  ', '   STUD   ' etc)
    rso_targets.columns = [str(c).strip() for c in rso_targets.columns]
    store_targets.columns = [str(c).strip() for c in store_targets.columns]
    # Clean up RSO targets: convert MONTH, STUD, GHS, TOTAL to numeric
    rso_targets["MONTH"] = pd.to_numeric(rso_targets["MONTH"], errors="coerce").astype("Int64")
    rso_targets["EMPLOYEE NAME"] = rso_targets["EMPLOYEE NAME"].astype(str).str.strip().str.upper()
    rso_targets["EMPLOYEE NAME"] = rso_targets["EMPLOYEE NAME"].apply(normalize_rso_name)
    for c in ["STUD", "GHS", "PLAIN", "HCG", "PJWS", "TOTAL"]:
        if c in rso_targets.columns:
            rso_targets[c] = pd.to_numeric(rso_targets[c], errors="coerce")
    # Strip column name whitespace from RSO targets (e.g. '    GHS    ' → 'GHS')
    rso_targets.columns = [str(c).strip() for c in rso_targets.columns]
    return rso_targets, store_targets


def store_target(store_targets, row_idx, month, default=0.0):
    """Robust lookup of a store target cell, regardless of whether the month
       columns are stored as ints (202606) or strings ('202606')."""
    for key in (int(month), str(int(month))):
        if key in store_targets.columns:
            try:
                val = store_targets.loc[row_idx, key]
                return float(val) if pd.notna(val) else default
            except (KeyError, ValueError, TypeError):
                continue
    return default


@st.cache_data(show_spinner=False)
def load_sales(_token: float) -> pd.DataFrame:
    """Load + clean the transaction file. _token busts cache on manual refresh."""
    df = pd.read_excel(SALES_FILE)
    df.columns = [str(c).strip() for c in df.columns]
    # Final RSO attribution = RSO CHANGE (fallback to RSO if ever blank)
    df["RSO_FINAL"] = df["RSO CHANGE"].fillna(df["RSO"]).astype(str).str.strip().str.upper()
    df["RSO_FINAL"] = df["RSO_FINAL"].apply(normalize_rso_name)
    # Numeric coercions
    # NOTE on units: CMTOTAL / AMT / WT are in LAKHS & grams; GHS-AMT & GEP-AMT are in RUPEES.
    # Convert GHS/GEP rupee columns to lakhs before mixing with CMTOTAL (see Upsell %).
    for c in ["WT", "AMT", "CMTOTAL", "GHS-AMT", "GHS-RED", "GEP-WT", "GEP-AMT", "QTY"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # BUG FIX: For multi-line bills, CMTOTAL is only on the first line.
    # Subsequent lines have CMTOTAL=NaN but AMT holds each line's value portion.
    # Fill null CMTOTAL with AMT only for sale rows (WT > 0), not returns.
    null_cmtotal = df["CMTOTAL"].isna() & (df["WT"].fillna(0) > 0)
    df.loc[null_cmtotal, "CMTOTAL"] = df.loc[null_cmtotal, "AMT"]
    df["CMTOTAL"] = df["CMTOTAL"].fillna(0)  # zero out any remaining nulls (e.g. return rows)
    df["MONTH"] = pd.to_numeric(df["MONTH"], errors="coerce").astype("Int64")
    df["FLAG"] = df["FLAG"].astype(str).str.strip().str.upper()
    df["IS_STUDDED"] = df["FLAG"] == "S"          # the one studded rule
    # A "piece" = a positive-quantity sale line (ignore pure returns for piece counts)
    df["QTY"] = df["QTY"].fillna(1)
    df["IS_RETURN"] = df["WT"].fillna(0) < 0      # fillna guards against NaN WT
    df["CUSTTYPE"] = df["CUSTTYPE"].astype(str).str.strip().str.upper()
    return df


@st.cache_data(show_spinner=False)
def load_ghs(_token: float) -> pd.DataFrame:
    df = pd.read_excel(GHS_FILE)
    df.columns = [str(c).strip() for c in df.columns]
    # Normalise column name to match sales file so join/merge logic works
    if "CUSTOMER NAME" in df.columns:
        df = df.rename(columns={"CUSTOMER NAME": "CUSTOMERNAME"})
    df["RSO NAME"] = df["RSO NAME"].astype(str).str.strip().str.upper()
    df["TYPE"] = df["TYPE"].astype(str).str.strip().str.upper()
    df["ACCOUNT.1"] = pd.to_numeric(df["ACCOUNT.1"], errors="coerce")
    df["OP-MONTH"] = pd.to_numeric(df["OP-MONTH"], errors="coerce").astype("Int64")
    df["REF-MONTH"] = pd.to_numeric(df["REF-MONTH"], errors="coerce").astype("Int64")
    df["OPENING"] = pd.to_datetime(df["OPENING"], errors="coerce")
    df["REFUND DATE"] = pd.to_datetime(df["REFUND DATE"], errors="coerce")
    df["IS_LIVE"] = df["REFUND DATE"].isna()       # live = not yet refunded

    # Account health: days since opening vs type-specific maturity window.
    # GHS matures/goes inactive after 400 days; RGA after 330 days.
    today = pd.Timestamp(dt.date.today())
    df["DAYS_OPEN"] = (today - df["OPENING"]).dt.days
    ghs_stale = (df["TYPE"] == "GHS") & (df["DAYS_OPEN"] > GHS_INACTIVE_DAYS)
    rga_stale = (df["TYPE"] == "RGA") & (df["DAYS_OPEN"] > RGA_INACTIVE_DAYS)
    # Inactive only matters for still-live (un-refunded) accounts.
    df["IS_INACTIVE"] = (ghs_stale | rga_stale) & df["IS_LIVE"]
    df["IS_ACTIVE"] = df["IS_LIVE"] & (~df["IS_INACTIVE"])
    return df


def hvs_threshold() -> float:
    return st.session_state.get("hvs_threshold", HVS_THRESHOLD_DEFAULT)


@st.cache_data(show_spinner=False, ttl=300)
def load_sludge(_token: float) -> pd.DataFrame:
    """Load the aged-stock (sludge) list. Optional file — returns empty if absent."""
    try:
        df = pd.read_excel(SLUDGE_FILE)
    except FileNotFoundError:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    for c in ["Wt", "Cur-Final", "INCENTIVE", "Age"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "ItemCode" in df.columns:
        df["THEME"] = df["ItemCode"].apply(theme_code)
        df["IMG"] = df["ItemCode"].apply(product_image_url)
    return df


@st.cache_data(show_spinner=False, ttl=300)
def load_cn(_token: float) -> pd.DataFrame:
    try:
        df = pd.read_excel(CN_FILE)
    except FileNotFoundError:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    df["DAYS"]   = pd.to_numeric(df["DAYS"],   errors="coerce").fillna(0)
    df["AMOUNT"] = pd.to_numeric(df["AMOUNT"], errors="coerce").fillna(0)
    df["RSO NAME"] = df["RSO NAME"].astype(str).str.strip().str.upper().apply(normalize_rso_name)
    df["MOBILE"]   = df["MOBILE"].astype(str).str.strip()

    cur   = df["CUR STATUS"].astype(str).str.upper().str.strip()
    cn_t  = df["CN TYPE"].astype(str).str.upper().str.strip()
    trans = df["TRANS-UID"].astype(str).str.upper()
    days  = df["DAYS"]

    flag_free    = cur == "FREE"
    flag_ghs     = (cn_t == "GHS") & (days > 400)
    flag_advbook = trans.str.contains("ADVBOOK", na=False) & (days > 30)
    flag_co      = trans.str.contains(r"\bCO\b", regex=True, na=False) & (days > 60)

    df["ALERT"] = flag_free | flag_ghs | flag_advbook | flag_co

    def _reason(row):
        r = []
        if row["_free"]:    r.append("FREE — must be booked")
        if row["_ghs"]:     r.append("GHS overdue >400 days")
        if row["_advbook"]: r.append("ADVBOOK overdue >30 days")
        if row["_co"]:      r.append("CO overdue >60 days")
        return ", ".join(r)

    df["_free"]    = flag_free
    df["_ghs"]     = flag_ghs
    df["_advbook"] = flag_advbook
    df["_co"]      = flag_co
    df["ALERT REASON"] = df.apply(_reason, axis=1)
    df.drop(columns=["_free", "_ghs", "_advbook", "_co"], inplace=True)
    return df


# ---------------------------------------------------------------------------
# 3. METRIC ENGINE  (per RSO per month, store rollups)
# ---------------------------------------------------------------------------
def studded_pieces(df: pd.DataFrame) -> int:
    """Count studded SALE lines (exclude returns)."""
    return int(((df["IS_STUDDED"]) & (~df["IS_RETURN"])).sum())


def hvs_pieces(df: pd.DataFrame) -> int:
    thr = hvs_threshold()
    return int(((df["IS_STUDDED"]) & (~df["IS_RETURN"]) & (df["CMTOTAL"] >= thr)).sum())


def rso_month_slice(sales: pd.DataFrame, rso: str, month: int) -> pd.DataFrame:
    return sales[(sales["RSO_FINAL"] == rso) & (sales["MONTH"] == month)]


def ghs_opens_in_month(ghs: pd.DataFrame, rso: str, month: int) -> dict:
    """Net GHS + RGA opens for an RSO in a month.
       NET = accounts opened this month − accounts refunded this month
       (a refund counts against the month it happens in, regardless of when opened).
    """
    opened = ghs[(ghs["RSO NAME"] == rso) & (ghs["OP-MONTH"] == month)]
    refunded = ghs[(ghs["RSO NAME"] == rso) & (ghs["REF-MONTH"] == month)]

    ghs_open = int((opened["TYPE"] == "GHS").sum())
    rga_open = int((opened["TYPE"] == "RGA").sum())
    ghs_ref = int((refunded["TYPE"] == "GHS").sum())
    rga_ref = int((refunded["TYPE"] == "RGA").sum())

    net_ghs = ghs_open - ghs_ref
    net_rga = rga_open - rga_ref
    return {
        "GHS": net_ghs, "RGA": net_rga, "TOTAL": net_ghs + net_rga,
        "GHS_OPEN": ghs_open, "RGA_OPEN": rga_open,
        "GHS_REF": ghs_ref, "RGA_REF": rga_ref,
        "OPENED": ghs_open + rga_open, "REFUNDED": ghs_ref + rga_ref,
    }


def store_ghs_net(ghs: pd.DataFrame, month: int) -> dict:
    """Store-wide net opens for a month (opens − refunds)."""
    opened = ghs[ghs["OP-MONTH"] == month]
    refunded = ghs[ghs["REF-MONTH"] == month]
    return {
        "OPENED": int(len(opened)),
        "REFUNDED": int(len(refunded)),
        "NET": int(len(opened) - len(refunded)),
    }


def store_studded_share(sales: pd.DataFrame, month: int) -> float:
    """Studded share by VALUE (CMTOTAL) for the month — drives the 30% gate."""
    m = sales[(sales["MONTH"] == month) & (~sales["IS_RETURN"])]
    tot = m["CMTOTAL"].clip(lower=0).sum()
    stud = m.loc[m["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
    return float(stud / tot * 100) if tot > 0 else 0.0


# ---------------------------------------------------------------------------
# 4. INCENTIVE ENGINE  (transparent, component-by-component)
# ---------------------------------------------------------------------------
def studded_slab(pieces: int) -> int:
    if pieces >= 31:
        return 5000 + 200 * (pieces - 30)
    if pieces == 30:
        return 5000
    if 20 <= pieces <= 29:
        return 1500
    if 10 <= pieces <= 19:
        return 500
    return 0


def ghs_slab(opens: int) -> int:
    if opens >= 20:
        return 3000
    if opens >= 15:
        return 2000
    if opens >= 10:
        return 1000
    return 0


def compute_incentive(sales, ghs, rso, month, *,
                      sludge_value_lakhs=0.0, mentee_hit=False,
                      store_gate_open=None, studded_target=30):
    """
    Returns a transparent dict of every incentive component for one RSO/month.
    sludge_value_lakhs : selling value (lakhs) of aged sludge this RSO moved (manual input).
    mentee_hit         : did this RSO's mentee cross 30 studded? (coach bonus)
    store_gate_open    : did store studded share >= 30 this month? (team gate)
    """
    sl = rso_month_slice(sales, rso, month)
    s_pieces = studded_pieces(sl)
    h_pieces = hvs_pieces(sl)
    opens = ghs_opens_in_month(ghs, rso, month)["TOTAL"]

    c_stud = studded_slab(s_pieces)
    c_hvs = 750 * h_pieces
    c_ghs = ghs_slab(opens)
    c_sludge = int(round(sludge_value_lakhs * 100000 * 0.01))   # 1% of value (lakhs->rupees)

    # multiplier layer
    c_coach = COACH_BONUS if mentee_hit else 0
    hit_target = s_pieces >= studded_target
    if store_gate_open is None:
        store_gate_open = store_studded_share(sales, month) >= STUDDED_SHARE_GATE
    c_team = TEAM_GATE_BONUS if (hit_target and store_gate_open) else 0
    c_stipend = TEACHING_STIPEND.get(rso, 0)

    total = c_stud + c_hvs + c_ghs + c_sludge + c_coach + c_team + c_stipend
    return dict(
        studded_pieces=s_pieces, hvs_pieces=h_pieces, ghs_opens=opens,
        c_stud=c_stud, c_hvs=c_hvs, c_ghs=c_ghs, c_sludge=c_sludge,
        c_coach=c_coach, c_team=c_team, c_stipend=c_stipend,
        hit_target=hit_target, store_gate_open=store_gate_open, total=total,
    )


def next_slab_hint(pieces: int) -> str:
    """'What more is needed' nudge for studded."""
    if pieces < 10:
        return f"{10 - pieces} more studded pieces unlock ₹500."
    if pieces < 20:
        return f"{20 - pieces} more unlock ₹1,500 (a ₹1,000 jump)."
    if pieces < 30:
        return f"{30 - pieces} more unlock ₹5,000 — the big jump."
    return f"Every extra piece above 30 = +₹200 (no ceiling). You're in the open field."


def pace_stats(month: int) -> dict:
    """How far through the month are we today? Returns days/pct/days_left."""
    import calendar as _cal
    y, m = int(str(int(month))[:4]), int(str(int(month))[4:])
    _, days_in_month = _cal.monthrange(y, m)
    today = dt.date.today()
    # clamp — if selected month is in the past, show it as complete
    if (y, m) < (today.year, today.month):
        return dict(day=days_in_month, days_in_month=days_in_month,
                    days_left=0, elapsed_pct=100.0)
    if (y, m) > (today.year, today.month):
        return dict(day=0, days_in_month=days_in_month,
                    days_left=days_in_month, elapsed_pct=0.0)
    day = min(today.day, days_in_month)
    return dict(day=day, days_in_month=days_in_month,
                days_left=days_in_month - day,
                elapsed_pct=day / days_in_month * 100)


def follow_up_lists(sales: pd.DataFrame, ghs: pd.DataFrame,
                    rso: str = None) -> dict:
    """Build three follow-up lists for an RSO (or whole store if rso=None).

    Returns:
        lapsed   — customers not seen in 60+ days, sorted by lifetime value
        maturing — GHS/RGA accounts entering their maturity window (next 30 days)
        upsell   — customers who have never bought a studded piece
    """
    today = pd.Timestamp(dt.date.today())
    s = sales[~sales["IS_RETURN"]].copy()
    if rso:
        s = s[s["RSO_FINAL"] == rso]

    # ── lapsed: last purchase > 60 days ago ──
    last_buy = (s.groupby("CUSTOMERNAME")
                 .agg(last_date=("DATE", "max"),
                      lifetime_val=("CMTOTAL", "sum"),
                      visits=("DATE", "count"),
                      mobile=("MOBILE", "last"),
                      rso=("RSO_FINAL", "last"))
                 .reset_index())
    last_buy["days_since"] = (today - last_buy["last_date"]).dt.days
    lapsed = (last_buy[last_buy["days_since"] > 60]
              .sort_values("lifetime_val", ascending=False)
              .reset_index(drop=True))

    # ── maturing: GHS (370-400d) or RGA (300-330d) still live ──
    g = ghs.copy()
    if rso:
        g = g[g["RSO NAME"] == rso]
    live = g[g["IS_LIVE"]].copy()
    ghs_win = live[(live["TYPE"] == "GHS") & (live["DAYS_OPEN"].between(370, 400))]
    rga_win = live[(live["TYPE"] == "RGA") & (live["DAYS_OPEN"].between(300, 330))]
    maturing = (pd.concat([ghs_win, rga_win])
                  .sort_values("DAYS_OPEN", ascending=False)
                  .reset_index(drop=True))

    # ── upsell: customers with ZERO studded history ──
    has_studded = set(sales.loc[sales["IS_STUDDED"], "CUSTOMERNAME"].unique())
    plain_only = last_buy[~last_buy["CUSTOMERNAME"].isin(has_studded)].copy()
    if rso:
        # re-filter to only this RSO's customers
        rso_custs = set(s["CUSTOMERNAME"].unique())
        plain_only = plain_only[plain_only["CUSTOMERNAME"].isin(rso_custs)]
    upsell = plain_only.sort_values("lifetime_val", ascending=False).reset_index(drop=True)

    return dict(lapsed=lapsed, maturing=maturing, upsell=upsell)


def inr(x) -> str:
    """Indian-format rupee string."""
    try:
        x = int(round(x))
    except Exception:
        return "₹0"
    s = str(abs(x)); 
    if len(s) > 3:
        last3 = s[-3:]; rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:]); rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    return ("-" if x < 0 else "") + "₹" + s

# ---------------------------------------------------------------------------
# 5. UI HELPERS  (gauges, progress bars, kpi cards)
# ---------------------------------------------------------------------------
def progress_bar(label, value, target, unit="", money=False):
    pct = (value / target * 100) if target else 0
    color = GREEN if pct >= 100 else (AMBER if pct >= 75 else RED)
    shown_v = inr(value) if money else f"{value:,.0f}{unit}"
    shown_t = inr(target) if money else f"{target:,.0f}{unit}"
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;
                  font-size:12px;color:#8A7A6B;flex-wrap:wrap;">
        <span style="white-space:nowrap;">{label}</span>
        <span style="white-space:nowrap;"><b style="color:#7B1E3B;">{shown_v}</b> / {shown_t}</span>
      </div>
      <div style="background:#EFE4D2;border-radius:8px;height:10px;margin-top:4px;overflow:hidden;">
        <div style="width:{min(pct,100):.0f}%;height:100%;background:{color};border-radius:8px;
                    transition:width .4s ease;"></div>
      </div>
      <div style="font-size:11px;color:{color};margin-top:2px;">{pct:.0f}% of target</div>
    </div>
    """, unsafe_allow_html=True)


def kpi(label, value, sub="", spark=None, ring_pct=None):
    """KPI card. spark = list of numbers → tiny trend sparkline.
       ring_pct = 0-100 → circular progress arc around the value."""
    spark_html = ""
    if spark and len(spark) >= 2:
        mn, mx = min(spark), max(spark)
        rng = mx - mn if mx != mn else 1
        w, h = 80, 28
        pts = " ".join(
            f"{int(i/(len(spark)-1)*w)},{int(h-(v-mn)/rng*(h-4)+2)}"
            for i, v in enumerate(spark))
        tc = EMERALD if spark[-1] >= spark[0] else RED
        spark_html = (f'<svg width="{w}" height="{h}" style="margin-top:6px;display:block;">'
                      f'<polyline points="{pts}" fill="none" stroke="{tc}" stroke-width="2.5"'
                      f' stroke-linejoin="round" stroke-linecap="round"/>'
                      f'<circle cx="{w}" cy="{int(h-(spark[-1]-mn)/rng*(h-4)+2)}"'
                      f' r="3.5" fill="{tc}"/></svg>')
    ring_html = ""
    if ring_pct is not None:
        p = max(0, min(100, ring_pct))
        circ = 2 * 3.14159 * 28
        dash = circ * p / 100
        rc = EMERALD if p >= 100 else (AMBER if p >= 70 else RED)
        ring_html = (f'<svg width="66" height="66" style="position:absolute;top:10px;right:10px;">'
                     f'<circle cx="33" cy="33" r="28" fill="none" stroke="#EFE4D2" stroke-width="4"/>'
                     f'<circle cx="33" cy="33" r="28" fill="none" stroke="{rc}" stroke-width="4"'
                     f' stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"'
                     f' transform="rotate(-90 33 33)"/>'
                     f'<text x="33" y="38" text-anchor="middle" font-size="12" font-weight="700"'
                     f' fill="{rc}" font-family="Cormorant Garamond,serif">{p:.0f}%</text></svg>')
    pad = "padding-right:76px;" if ring_html else ""
    st.markdown(
        f'<div class="kpi-card" style="position:relative;{pad}">' +
        ring_html +
        f'<div class="kpi-label">{label}</div>' +
        f'<div class="kpi-value">{value}</div>' +
        f'<div class="kpi-sub">{sub}</div>' +
        spark_html +
        '</div>',
        unsafe_allow_html=True)



def donut_ring(pct: float, center_text: str, label: str, sub: str = "",
               color: str = None, size: int = 150) -> str:
    """Premium SVG donut ring. pct=0-100, shows value inside with arc fill."""
    r, sw = 52, 11
    circ = 2 * 3.14159265 * r
    p = max(0.0, min(float(pct), 100.0))
    dash = circ * p / 100
    cx = cy = size / 2
    if color is None:
        color = EMERALD if p >= 100 else (GOLD if p >= 70 else (AMBER if p >= 40 else RED))
    track = "#EFE4D2"
    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;padding:6px 4px;">' +
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">' +
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{track}" stroke-width="{sw}"/>' +
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{sw}"' +
        f' stroke-dasharray="{dash:.2f} {circ - dash:.2f}" stroke-linecap="round"' +
        f' transform="rotate(-90 {cx} {cy})"/>' +
        f'<text x="{cx}" y="{cy-7}" text-anchor="middle"' +
        f' font-family="Cormorant Garamond,Georgia,serif"' +
        f' font-size="19" font-weight="700" fill="{RUBY}">{center_text}</text>' +
        f'<text x="{cx}" y="{cy+12}" text-anchor="middle"' +
        f' font-family="Inter,sans-serif"' +
        f' font-size="13" font-weight="600" fill="{color}">{p:.0f}%</text>' +
        f'</svg>' +
        f'<div style="font-size:11px;font-weight:700;color:{RUBY};text-align:center;' +
        f'letter-spacing:0.6px;text-transform:uppercase;margin-top:2px;">{label}</div>' +
        (f'<div style="font-size:10px;color:{MUTED};text-align:center;margin-top:1px;">{sub}</div>' if sub else "") +
        '</div>'
    )


def ring_row(rings: list) -> str:
    """Render a horizontal row of donut rings. rings = [(pct,text,label,sub,color), ...]"""
    items = "".join(donut_ring(p, t, l, s, clr) for p, t, l, s, clr in rings)
    return (
        '<div style="display:flex;justify-content:center;gap:8px;flex-wrap:wrap;' +
        'background:{CREAM};border:1px solid rgba(201,162,39,0.22);border-radius:20px;' +
        'padding:18px 12px;margin-bottom:14px;box-shadow:0 3px 14px rgba(123,30,59,0.07);">' +
        items + '</div>'
    ).replace("{CREAM}", CREAM)



def pressure_pill(p):
    c = PRESSURE_COLOR.get(p, "#666")
    return f'<span class="pill" style="background:{c}22;color:{c};border:1px solid {c}55;">{p}</span>'


def page_header(icon: str, title: str, subtitle: str = ""):
    """Premium page title banner — icon box + title + optional subtitle."""
    sub_html = f'<div class="page-title-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="page-title-bar">
      <div class="page-title-icon">{icon}</div>
      <div class="page-title-text">
        <div class="page-title-main">{title}</div>
        {sub_html}
      </div>
    </div>
    """, unsafe_allow_html=True)


def apply_chart_style(fig, height=340, legend_pos="top"):
    """Apply consistent Tanishq chart theming to any Plotly figure."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=ESPRESSO, size=12),
        legend=dict(
            orientation="h",
            y=1.12 if legend_pos == "top" else -0.18,
            x=0.5, xanchor="center",
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
        margin=dict(l=12, r=12, t=40, b=12),
        hoverlabel=dict(
            bgcolor=CREAM, bordercolor=GOLD,
            font=dict(family="Inter", color=ESPRESSO, size=12),
        ),
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False,
        linecolor="rgba(201,162,39,0.20)",
        tickfont=dict(size=11, color=MUTED),
        title_font=dict(size=12, color=MUTED),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="rgba(201,162,39,0.10)",
        zeroline=False,
        tickfont=dict(size=11, color=MUTED),
        title_font=dict(size=12, color=MUTED),
    )
    return fig


# --- Personalisation helpers -------------------------------------------------
AVATAR_GRADIENTS = [
    ("#F6D365", "#FDA085"), ("#A1C4FD", "#C2E9FB"), ("#FBC2EB", "#A6C1EE"),
    ("#84FAB0", "#8FD3F4"), ("#FFD3A5", "#FD6585"), ("#F5D76E", "#E8B923"),
    ("#D4AF37", "#E8CE7B"), ("#B79891", "#94716B"),
]

def avatar_for(name: str) -> tuple:
    """Deterministic initials + gradient for an RSO, so each person feels distinct."""
    parts = [p for p in str(name).split() if p]
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper() if parts else "?"
    idx = sum(ord(c) for c in str(name)) % len(AVATAR_GRADIENTS)
    g1, g2 = AVATAR_GRADIENTS[idx]
    return initials, g1, g2

def greeting_word() -> str:
    """Time-of-day greeting (server local time)."""
    h = dt.datetime.now().hour
    if h < 12:   return "Good morning"
    if h < 17:   return "Good afternoon"
    return "Good evening"

def rso_hero_card(name: str, role: str, sub_metrics: list):
    """Personalised hero banner: avatar, greeting, name, and 3-4 stat chips.
       sub_metrics = list of (value, label) tuples."""
    initials, g1, g2 = avatar_for(name)
    chips = "".join(
        f'<div class="stat-chip"><div class="stat-chip-val">{v}</div>'
        f'<div class="stat-chip-lbl">{l}</div></div>'
        for v, l in sub_metrics
    )
    st.markdown(f"""
    <div class="rso-hero">
      <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
        <div class="rso-avatar" style="background:linear-gradient(135deg,{g1},{g2});">{initials}</div>
        <div style="flex:1; min-width:160px;">
          <p class="rso-greeting">{greeting_word()}, welcome back 👋</p>
          <div class="rso-name">{name.title()}</div>
          <span class="rso-role-pill">{role}</span>
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">{chips}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 6. AUTH
# ---------------------------------------------------------------------------
def do_login(sales):
    st.markdown(f"""
    <div style="text-align:center; margin:18px 0 8px;">
      <div style="font-family:'Cormorant Garamond',serif; font-size:15px; letter-spacing:6px;
                  text-transform:uppercase; color:{GOLD_DEEP};">A House of Fine Jewellery</div>
      <h1 style="margin:6px 0 0; font-size:52px;">Tanishq <span style="color:{GOLD_DEEP}">Malviya Nagar</span></h1>
      <p style="color:{MUTED}; margin-top:4px; letter-spacing:0.5px;">
        Performance &nbsp;·&nbsp; Incentive &nbsp;·&nbsp; Team Command Centre</p>
      <div style="width:80px; height:3px; margin:14px auto 0;
                  background:linear-gradient(90deg,transparent,{GOLD},transparent);"></div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("####  ")
        kind = st.radio("Login as", ["RSO (salesperson)", "Manager / Admin / MD"], horizontal=False)
        if kind.startswith("RSO"):
            rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
            who = st.selectbox("Your name", rsos)
            pwd = st.text_input("Password", type="password", value="", help="Prototype password: rso2026")
            if st.button("Sign in", use_container_width=True):
                if pwd == RSO_PWD:
                    st.session_state.update(auth=True, role="RSO", name=who.title(), rso=who)
                    st.rerun()
                else:
                    st.error("Wrong password. (Prototype: rso2026)")
        else:
            user = st.text_input("Username", help="admin / swaroop / rashmi / deepesh / archit")
            pwd = st.text_input("Password", type="password")
            if st.button("Sign in", use_container_width=True):
                u = MANAGEMENT_USERS.get(user.strip().lower())
                if u and pwd == u["pwd"]:
                    st.session_state.update(auth=True, role=u["role"], name=u["name"], rso=None)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.caption("Prototype logins — RSO pwd `rso2026`; admin `admin`/`admin`; swaroop `mn2026`.")

# ---------------------------------------------------------------------------
# 7. FROZEN TOP BAR  (sticky-ish summary on every screen, VALUE-based targets)
# ---------------------------------------------------------------------------
def frozen_bar(sales, ghs, rso_targets, store_targets, month, focus_rso=None):
    """Top summary bar. Personalised hero for an RSO; store rollup for overview."""

    # ---------- PERSONALISED RSO VIEW ----------
    if focus_rso:
        rsl = rso_month_slice(sales, focus_rso, month)
        rsl = rsl[~rsl["IS_RETURN"]]
        r_value = rsl["CMTOTAL"].clip(lower=0).sum()                              # total value (lakhs)
        r_stud_value = rsl.loc[rsl["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()  # studded value (lakhs)
        opens = ghs_opens_in_month(ghs, focus_rso, month)["TOTAL"]
        sp = studded_pieces(rsl)

        # RSO targets — ALL VALUE in lakhs. TOTAL=col M, STUD=col L, GHS=col N.
        rso_tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"] == focus_rso.upper()) &
                                  (rso_targets["MONTH"] == int(month))]
        r_total_tgt = float(rso_tgt_row["TOTAL"].iloc[0]) if len(rso_tgt_row) > 0 else 100.0
        r_stud_tgt = float(rso_tgt_row["STUD"].iloc[0]) if len(rso_tgt_row) > 0 else 30.0
        r_ghs_tgt = float(rso_tgt_row["GHS"].iloc[0]) if len(rso_tgt_row) > 0 else 20.0

        res = compute_incentive(sales, ghs, focus_rso, month)
        prof = RSO_PROFILE.get(focus_rso, DEFAULT_PROFILE)
        rso_hero_card(
            focus_rso, prof.get("role", "RSO"),
            [(f"₹{r_value:.0f}L", "Value"), (f"{sp}", "Stud Pcs"),
             (f"{opens}", "GHS"), (inr(res["total"]), "Incentive")],
        )

        # ── PACE STRIP ─────────────────────────────────────────────────────────
        pace = pace_stats(month)
        ep = pace["elapsed_pct"]
        val_pct = (r_value / r_total_tgt * 100) if r_total_tgt else 0
        pace_color = EMERALD if val_pct >= ep else (AMBER if val_pct >= ep * 0.8 else RED)
        # daily run-rate needed to close
        days_left = max(pace["days_left"], 1)
        gap = max(r_total_tgt - r_value, 0)
        need_per_day = gap / days_left

        # next studded slab nudge
        next_slab_pieces = (10 if sp < 10 else 20 if sp < 20 else 30 if sp < 30 else None)
        if next_slab_pieces:
            need_pcs = next_slab_pieces - sp
            gain = studded_slab(next_slab_pieces) - studded_slab(sp)
            slab_msg = (f"<b>{need_pcs} more studded piece{'s' if need_pcs!=1 else ''}</b> "
                        f"→ ₹{gain:,} more incentive")
        else:
            slab_msg = f"<b>Every extra piece = +₹200</b> — no ceiling from here"

        # next GHS slab nudge
        next_ghs = (10 if opens < 10 else 15 if opens < 15 else 20 if opens < 20 else None)
        if next_ghs:
            need_ghs = next_ghs - opens
            ghs_gain = ghs_slab(next_ghs) - ghs_slab(opens)
            ghs_msg = f"{need_ghs} more GHS open{'s' if need_ghs!=1 else ''} → ₹{ghs_gain:,} more"
        else:
            ghs_msg = "Max GHS slab reached ✅"

        st.markdown(f"""
        <div style="background:{CREAM};border:1px solid rgba(123,30,59,0.12);border-radius:18px;
                    padding:16px 20px;margin-bottom:10px;box-shadow:0 2px 10px rgba(123,30,59,0.06);">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
            <span style="font-size:13px;color:{MUTED};font-weight:600;">
              Day {pace['day']} of {pace['days_in_month']}
            </span>
            <div style="flex:1;min-width:120px;background:#EFE4D2;border-radius:8px;height:8px;">
              <div style="width:{ep:.0f}%;height:100%;background:{RUBY};border-radius:8px;opacity:0.35;"></div>
            </div>
            <div style="flex:1;min-width:120px;background:#EFE4D2;border-radius:8px;height:8px;">
              <div style="width:{min(val_pct,100):.0f}%;height:100%;background:{pace_color};border-radius:8px;"></div>
            </div>
            <span style="font-size:13px;font-weight:700;color:{pace_color};">{val_pct:.0f}% achieved</span>
            <span style="font-size:13px;color:{MUTED};">vs {ep:.0f}% of month elapsed</span>
          </div>
          <div style="display:flex;gap:24px;flex-wrap:wrap;">
            <div>
              <span style="font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:1px;">
                Need per day to close</span><br>
              <span style="font-size:22px;font-weight:700;color:{RUBY};
                           font-family:'Cormorant Garamond',serif;">₹{need_per_day:.1f}L</span>
              <span style="font-size:12px;color:{MUTED};"> over {days_left} day{'s' if days_left!=1 else ''}</span>
            </div>
            <div style="border-left:2px solid {SAND};padding-left:24px;">
              <span style="font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:1px;">
                Next studded slab</span><br>
              <span style="font-size:14px;color:{RUBY};">{slab_msg}</span>
            </div>
            <div style="border-left:2px solid {SAND};padding-left:24px;">
              <span style="font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:1px;">
                GHS nudge</span><br>
              <span style="font-size:14px;color:{RUBY};">{ghs_msg}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="frozen-bar">', unsafe_allow_html=True)
        rc = st.columns(3)
        with rc[0]:
            progress_bar("Total Value vs Target", r_value, r_total_tgt, unit=" L")
        with rc[1]:
            progress_bar("Studded Value vs Target", r_stud_value, r_stud_tgt, unit=" L")
        with rc[2]:
            progress_bar("GHS Opens vs Target", opens, r_ghs_tgt)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ---------- STORE OVERVIEW (managers / admin / MD) ----------
    msl = sales[(sales["MONTH"] == month) & (~sales["IS_RETURN"])]
    store_total_value = msl["CMTOTAL"].clip(lower=0).sum()
    store_stud_value = msl.loc[msl["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()

    # Store-targets rows: 0=OVERALL, 2=STUDDED (value in lakhs), 5=GHS QTY (count).
    store_overall_tgt = store_target(store_targets, 0, month, default=1000.0)
    store_stud_tgt = store_target(store_targets, 2, month, default=300.0)
    ghs_month = ghs[ghs["OP-MONTH"] == month]
    ghs_opens = len(ghs_month)
    ghs_tgt = store_target(store_targets, 5, month, default=250.0)

    st.markdown('<div class="frozen-bar">', unsafe_allow_html=True)
    cols = st.columns([1.1, 1.1, 1.1, 1.3])
    with cols[0]:
        progress_bar("Store · Total Value", store_total_value, store_overall_tgt, unit=" L")
    with cols[1]:
        progress_bar("Store · Studded Value", store_stud_value, store_stud_tgt, unit=" L")
    with cols[2]:
        progress_bar("Store · GHS opens", ghs_opens, ghs_tgt)
    with cols[3]:
        share = (store_stud_value / store_total_value * 100) if store_total_value else 0
        gate = "OPEN ✅" if share >= STUDDED_SHARE_GATE else "BELOW ⚠️"
        gate_c = GREEN if share >= STUDDED_SHARE_GATE else AMBER
        st.markdown(f"""
        <div style="text-align:center">
          <div class="kpi-label">Studded Share (value)</div>
          <div style="font-size:28px;font-weight:700;color:{gate_c};font-family:'Cormorant Garamond',serif">{share:.1f}%</div>
          <div style="font-size:11px;color:{gate_c}">Gate {gate} · need {STUDDED_SHARE_GATE:.0f}%</div>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 8. PAGE — PERFORMANCE
# ---------------------------------------------------------------------------
def page_performance(sales, ghs, rso_targets, month, view_rso, role):
    page_header("📊", "Performance", f"Month · {str(month)[4:]}/{str(month)[:4]}")
    months = sorted(sales["MONTH"].dropna().unique().tolist())
    prev_month = months[months.index(month) - 1] if months.index(month) > 0 else None

    rsl = rso_month_slice(sales, view_rso, month) if view_rso else sales[sales["MONTH"] == month]
    rsl_pos = rsl[~rsl["IS_RETURN"]]

    total_value = rsl_pos["CMTOTAL"].clip(lower=0).sum()
    stud_value = rsl_pos.loc[rsl_pos["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
    plain_value = total_value - stud_value
    sp = studded_pieces(rsl)
    hv = hvs_pieces(rsl)
    ghs_red_lakhs = rsl_pos["GHS-AMT"].sum() / 100000.0
    gep_bills = int((rsl_pos["GEP-AMT"].fillna(0) > 0).sum())
    total_bills = int(len(rsl_pos))
    gep_bill_pct = (gep_bills / total_bills * 100) if total_bills > 0 else 0
    gep_val_lakhs = rsl_pos["GEP-AMT"].sum() / 100000.0
    aev = (total_value / total_bills) if total_bills else 0
    share = (stud_value / total_value * 100) if total_value else 0

    # Targets
    rso_tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"] == (view_rso or "").upper()) &
                               (rso_targets["MONTH"] == int(month))] if view_rso else pd.DataFrame()
    tgt_val  = float(rso_tgt_row["TOTAL"].iloc[0]) if len(rso_tgt_row) else None
    tgt_stud = float(rso_tgt_row["STUD"].iloc[0])  if len(rso_tgt_row) else None

    if view_rso:
        # ── PERSONAL RSO VIEW: beautiful donut rings ──────────────────────────
        val_pct  = (total_value / tgt_val  * 100) if tgt_val  else 0
        stud_pct = (stud_value  / tgt_stud * 100) if tgt_stud else 0
        gate_pct = share / 30 * 100
        hvs_pct  = min(hv / 5 * 100, 100) if hv else 0   # 5 HVS as a soft benchmark

        rings = [
            (val_pct,  f"₹{total_value:.0f}L",  "Total Value",
             f"of ₹{tgt_val:.0f}L target" if tgt_val else "", None),
            (stud_pct, f"₹{stud_value:.0f}L",   "Studded Value",
             f"of ₹{tgt_stud:.0f}L target" if tgt_stud else "", RUBY),
            (gate_pct, f"{share:.1f}%",           "Studded Share",
             "gate needs 30%",
             EMERALD if share >= 30 else (AMBER if share >= 20 else RED)),
            (min(sp/30*100,100), f"{sp} pcs",    "Studded Pcs",
             next_slab_hint(sp)[:28], GOLD),
            (min(hv/3*100,100), f"{hv} HVS",     "HVS (₹5L+)",
             f"₹{inr(hv*750)} earned", RUBY_LT),
        ]
        st.markdown(
            '<div style="display:flex;justify-content:center;gap:4px;flex-wrap:wrap;'
            f'background:{CREAM};border:1px solid rgba(201,162,39,0.22);border-radius:20px;'
            'padding:16px 8px;margin-bottom:14px;box-shadow:0 3px 14px rgba(123,30,59,0.07);">' +
            "".join(donut_ring(p, t, l, s, clr) for p, t, l, s, clr in rings) +
            "</div>",
            unsafe_allow_html=True,
        )
        # secondary stats strip
        sc1, sc2, sc3 = st.columns(3)
        with sc1: kpi("GEP Contribution", f"{gep_bill_pct:.1f}%",
                      f"{gep_bills}/{total_bills} bills · {inr(gep_val_lakhs*100000)}")
        with sc2: kpi("Avg Bill Value", f"₹{aev:,.2f}L", f"{total_bills} bills")
        with sc3: kpi("Upsell % (GHS/CM)", f"{(ghs_red_lakhs/total_value*100) if total_value else 0:.1f}%",
                      "GHS redemption vs CM total")
    else:
        # ── STORE / MANAGER VIEW: KPI cards with sparklines ───────────────────
        def _spark(metric_fn):
            vals = []
            for m in months:
                sl = sales[sales["MONTH"] == m]; sl = sl[~sl["IS_RETURN"]]
                vals.append(metric_fn(sl))
            return vals

        val_spark  = _spark(lambda sl: sl["CMTOTAL"].clip(lower=0).sum())
        stud_spark = _spark(lambda sl: sl.loc[sl["IS_STUDDED"],"CMTOTAL"].clip(lower=0).sum())
        gate_c = EMERALD if share >= 30 else (AMBER if share >= 20 else RED)

        c = st.columns(4)
        with c[0]: kpi("Total Value", f"₹{total_value:,.1f}L",
                       f"Studded ₹{stud_value:.1f}L · Plain ₹{plain_value:.1f}L", spark=val_spark)
        with c[1]: kpi("Studded Value", f"₹{stud_value:,.1f}L",
                       next_slab_hint(sp), spark=stud_spark)
        with c[2]: kpi("Studded Share", f"{share:.1f}%",
                       f'<span style="color:{gate_c}">{"✅ gate open" if share>=30 else f"need {30-share:.1f}% more"}</span>')
        with c[3]: kpi("HVS Pieces", f"{hv}", f"@ ₹750 = {inr(hv*750)}")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        c2 = st.columns(3)
        with c2[0]: kpi("Bills", f"{total_bills}", f"Avg ₹{aev:.2f}L per bill")
        with c2[1]: kpi("GEP Contribution", f"{gep_bill_pct:.1f}%", f"{gep_bills}/{total_bills} bills")
        with c2[2]: kpi("Studded Pieces", f"{sp}", next_slab_hint(sp))

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # CHARTS
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("#### Studded vs Plain — value (₹L) by month")
        scope = sales[sales["RSO_FINAL"] == view_rso] if view_rso else sales
        scope = scope[~scope["IS_RETURN"]]
        g = scope.groupby(["MONTH", "IS_STUDDED"])["CMTOTAL"].sum().reset_index()
        g["Type"] = g["IS_STUDDED"].map({True: "Studded", False: "Plain/Other"})
        # Format month as MMYY for readability (e.g., 202604 -> "Apr 26")
        month_map = {202604: "Apr 26", 202605: "May 26", 202606: "Jun 26", 202607: "Jul 26", 
                     202608: "Aug 26", 202609: "Sep 26", 202610: "Oct 26", 202611: "Nov 26",
                     202612: "Dec 26", 202701: "Jan 27", 202702: "Feb 27", 202703: "Mar 27"}
        g["Month_Label"] = g["MONTH"].map(month_map).fillna(g["MONTH"].astype(str))
        fig = px.bar(g, x="Month_Label", y="CMTOTAL", color="Type", barmode="group",
                     color_discrete_map={"Studded": GOLD, "Plain/Other": "#7B1E3B"},
                     labels={"CMTOTAL": "Value (₹ Lakhs)"})
        fig.update_layout(bargap=0.28)
        fig.update_traces(marker_line_width=0, marker_cornerradius=4)
        apply_chart_style(fig, height=320)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### This month vs last (value)")
        if prev_month is not None:
            prev = rso_month_slice(sales, view_rso, prev_month) if view_rso else sales[sales["MONTH"] == prev_month]
            prev = prev[~prev["IS_RETURN"]]
            prev_total_value = prev["CMTOTAL"].clip(lower=0).sum()
            prev_stud_value = prev.loc[prev["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
            comp = pd.DataFrame({
                "Metric": ["Total Value (L)", "Studded Value (L)", "Studded Pcs", "HVS Pcs"],
                "This": [total_value, stud_value, sp, hv],
                "Last": [prev_total_value, prev_stud_value, studded_pieces(prev), hvs_pieces(prev)],
            })
            comp["Δ%"] = ((comp["This"] - comp["Last"]) / comp["Last"].replace(0, np.nan) * 100).round(0)
            st.dataframe(comp, hide_index=True, use_container_width=True)
        else:
            st.caption("No previous month in data.")

        # Profitable bill mix
        if "PROF" in rsl_pos:
            prof = (rsl_pos["PROF"].fillna(0) == 1).sum()
            st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Profitable bills</div>"
                        f"<div class='kpi-value'>{prof}</div>"
                        f"<div class='kpi-sub'>of {len(rsl_pos)} line items</div></div>",
                        unsafe_allow_html=True)

    # RSO intelligence card (managers + the RSO themselves)
    if view_rso:
        prof = RSO_PROFILE.get(view_rso, DEFAULT_PROFILE)
        st.markdown("#### 🧭 Coaching lens")
        ic1, ic2 = st.columns([1.4, 1])
        with ic1:
            st.markdown(f"""
            <div class="kpi-card">
              <b class="gold">{prof['archetype']}</b> &nbsp; {pressure_pill(prof['pressure'])}
              &nbsp;<span class="pill" style="background:#F1E8DA;color:#7B1E3B;border:1px solid rgba(123,30,59,0.2);">{prof['team']}</span><br><br>
              <span class="small-muted">NATIVE GENIUS</span><br>{prof['genius']}<br><br>
              <span class="small-muted">WATCH</span><br>{prof['watch']}
            </div>""", unsafe_allow_html=True)
        with ic2:
            coach = prof.get("coach")
            mentees = prof.get("mentees") or []
            st.markdown(f"""
            <div class="kpi-card">
              <span class="small-muted">ROLE</span><br><b>{prof['role']}</b><br><br>
              <span class="small-muted">COACH</span><br>{coach.title() if coach else '—'}<br><br>
              <span class="small-muted">MENTEES</span><br>{', '.join(m.title() for m in mentees) if mentees else '—'}
            </div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 9. PAGE — INCENTIVE CALCULATOR
# ---------------------------------------------------------------------------
def page_incentive(sales, ghs, rso_targets, month, view_rso, role):
    page_header("💰", "Incentive Calculator", "Auto-calculated · fully transparent · component-by-component")

    is_mgr = role in ("Admin", "Store Manager", "Floor Manager", "MD")
    rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
    target_rso = view_rso
    if is_mgr:
        target_rso = st.selectbox("RSO", rsos, index=rsos.index(view_rso) if view_rso in rsos else 0)

    colB, colC = st.columns(2)
    with colB:
        prof = RSO_PROFILE.get(target_rso, DEFAULT_PROFILE)
        has_mentees = bool(prof.get("mentees"))
        mentee_hit = st.checkbox("A mentee hit 30+ studded (coach bonus)",
                                 value=False, disabled=not has_mentees,
                                 help="Only RSOs with assigned mentees can earn the coach bonus.")
    with colC:
        share = store_studded_share(sales, month)
        gate_default = share >= STUDDED_SHARE_GATE
        gate = st.checkbox(f"Store studded gate open (now {share:.1f}%)",
                           value=gate_default,
                           help="Team gate bonus only pays when store studded share ≥ 30%.")

    res = compute_incentive(sales, ghs, target_rso, month,
                            mentee_hit=mentee_hit, store_gate_open=gate)

    # headline
    h1, h2, h3 = st.columns([1.2, 1, 1])
    with h1:
        st.markdown(f"""
        <div class="kpi-card" style="text-align:center">
          <div class="kpi-label">{target_rso.title()} · {month} incentive</div>
          <div style="font-size:46px;font-weight:700;color:{RUBY};font-family:'Cormorant Garamond',serif;line-height:1.1">{inr(res['total'])}</div>
          <div class="kpi-sub">projected annual ≈ {inr(res['total']*12)}</div>
        </div>""", unsafe_allow_html=True)
    with h2:
        kpi("Studded pieces", res["studded_pieces"], next_slab_hint(res["studded_pieces"]))
    with h3:
        kpi("GHS+RGA opens", res["ghs_opens"],
            "→ next slab" if res["ghs_opens"] < 20 else "max slab ✅")

    # transparent breakdown
    st.markdown("#### How this number was built")
    rows = [
        ("💎 Studded pieces", f"{res['studded_pieces']} pcs → slab", res["c_stud"]),
        ("👑 HVS pieces", f"{res['hvs_pieces']} × ₹750", res["c_hvs"]),
        ("🏦 GHS / RGA opens", f"{res['ghs_opens']} opens → slab", res["c_ghs"]),
        ("🤝 Coach bonus", "mentee hit 30+" if res["c_coach"] else "—", res["c_coach"]),
        ("🏆 Team studded gate", "target + store ≥30%" if res["c_team"] else "not unlocked", res["c_team"]),
        ("🎓 Teaching stipend", "fixed" if res["c_stipend"] else "—", res["c_stipend"]),
    ]
    for label, detail, amt in rows:
        amt_c = RUBY if amt else "#BCAE9C"
        st.markdown(f"""
        <div class="incentive-row">
          <span>{label} &nbsp;<span class="small-muted">{detail}</span></span>
          <span style="color:{amt_c};font-weight:600">{inr(amt)}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="incentive-row" style="border-top:2px solid {GOLD};margin-top:6px;">
      <span style="font-weight:700;color:{ESPRESSO}">TOTAL</span>
      <span style="color:{GOLD_DEEP};font-weight:800;font-size:20px;font-family:'Cormorant Garamond',serif">{inr(res['total'])}</span>
    </div>""", unsafe_allow_html=True)

    # what-if simulator
    with st.expander("🔮 What-if simulator — push the sliders"):
        s1, s2, s3 = st.columns(3)
        sim_stud = s1.slider("Studded pieces", 0, 55, int(res["studded_pieces"]))
        sim_hvs = s2.slider("HVS pieces", 0, 10, int(res["hvs_pieces"]))
        sim_ghs = s3.slider("GHS+RGA opens", 0, 30, int(res["ghs_opens"]))
        sim_total = (studded_slab(sim_stud) + 750 * sim_hvs + ghs_slab(sim_ghs)
                     + res["c_coach"]
                     + (TEAM_GATE_BONUS if (sim_stud >= 30 and gate) else 0)
                     + res["c_stipend"])
        st.markdown(f"### Simulated month: <span class='gold'>{inr(sim_total)}</span> "
                    f"<span class='small-muted'>(annual ≈ {inr(sim_total*12)})</span>",
                    unsafe_allow_html=True)

    # manager-only: whole team incentive table + pool status
    if is_mgr:
        st.markdown("#### 🏛️ Whole-team incentive — this month")
        gate_open = gate
        team_rows = []
        for r in rsos:
            rr = compute_incentive(sales, ghs, r, month,
                                   sludge_value_lakhs=0.0, mentee_hit=False,
                                   store_gate_open=gate_open)
            team_rows.append(dict(RSO=r.title(), **{
                "Studded": rr["studded_pieces"], "HVS": rr["hvs_pieces"],
                "GHS": rr["ghs_opens"], "Studded ₹": rr["c_stud"],
                "HVS ₹": rr["c_hvs"], "GHS ₹": rr["c_ghs"],
                "Stipend": rr["c_stipend"], "Total ₹": rr["total"]}))
        tdf = pd.DataFrame(team_rows).sort_values("Total ₹", ascending=False)
        st.dataframe(tdf, hide_index=True, use_container_width=True)

        monthly_payout = tdf["Total ₹"].sum()
        annual_proj = monthly_payout * 12
        pool_pct = annual_proj / ANNUAL_POOL * 100
        pc1, pc2, pc3 = st.columns(3)
        with pc1: kpi("Team payout (this month)", inr(monthly_payout))
        with pc2: kpi("Projected annual", inr(annual_proj), f"{pool_pct:.0f}% of pool")
        with pc3:
            pool_c = GREEN if pool_pct <= 100 else RED
            st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Pool status</div>
            <div class="kpi-value" style="color:{pool_c}">{inr(ANNUAL_POOL)}</div>
            <div class="kpi-sub">RSO pool ceiling · {'within budget' if pool_pct<=100 else 'OVER — review'}</div></div>""",
            unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 10. PAGE — GHS / RGA DATA  (from ghs_OPENING.xlsx only)
# ---------------------------------------------------------------------------
def page_ghs(sales, ghs, month, view_rso, role):
    page_header("🏦", "GHS & RGA Book",
                f"Net opens = opened − refunded · inactive after GHS {GHS_INACTIVE_DAYS}d / RGA {RGA_INACTIVE_DAYS}d")

    scope = ghs[ghs["RSO NAME"] == view_rso] if view_rso else ghs
    is_mgr = role in ("Admin", "Store Manager", "Floor Manager", "MD")
    if is_mgr:
        rsos = ["(whole store)"] + sorted(ghs["RSO NAME"].dropna().unique().tolist())
        pick = st.selectbox("RSO", rsos, index=0 if not view_rso else
                            (rsos.index(view_rso) if view_rso in rsos else 0))
        scope = ghs if pick == "(whole store)" else ghs[ghs["RSO NAME"] == pick]

    tab_ghs, tab_rga = st.tabs(["💠 GHS (Gold Harvest Scheme)", "🔁 RGA (Recurring Gold)"])

    for tab, typ in [(tab_ghs, "GHS"), (tab_rga, "RGA")]:
        with tab:
            sub = scope[scope["TYPE"] == typ]
            live = sub[sub["IS_LIVE"]]
            redeemed = sub[~sub["IS_LIVE"]]
            opens_m = sub[sub["OP-MONTH"] == month]
            redeem_m = sub[sub["REF-MONTH"] == month]
            net_m = len(opens_m) - len(redeem_m)
            inactive = sub[sub["IS_INACTIVE"]]
            win = GHS_INACTIVE_DAYS if typ == "GHS" else RGA_INACTIVE_DAYS

            c = st.columns(4)
            with c[0]: kpi("Net opens (this month)", f"{net_m:,}",
                           f"{len(opens_m)} opened − {len(redeem_m)} refunded")
            with c[1]: kpi(f"Active {typ} accounts", f"{int(sub['IS_ACTIVE'].sum()):,}",
                           f"live & within {win} days")
            with c[2]: kpi("Going inactive", f"{len(inactive):,}",
                           f"live but aged > {win} days")
            with c[3]: kpi("Total ever (in book)", f"{len(sub):,}",
                           f"{len(redeemed):,} refunded")

            # opens trend
            tr = sub.groupby("OP-MONTH").size().reset_index(name="Opens")
            month_map2 = {202604: "Apr 26", 202605: "May 26", 202606: "Jun 26", 202607: "Jul 26",
                          202608: "Aug 26", 202609: "Sep 26", 202610: "Oct 26", 202611: "Nov 26",
                          202612: "Dec 26", 202701: "Jan 27", 202702: "Feb 27", 202703: "Mar 27"}
            tr["Label"] = tr["OP-MONTH"].map(month_map2).fillna(tr["OP-MONTH"].astype(str))
            fig = px.line(tr, x="Label", y="Opens", markers=True)
            fig.update_traces(line_color=GOLD_DEEP, line_width=3,
                              marker=dict(size=9, color=GOLD, line=dict(width=2, color="#fff")))
            fig.update_layout(title=dict(text=f"{typ} opens by month", font=dict(color=RUBY, size=16)))
            apply_chart_style(fig, height=240)
            st.plotly_chart(fig, use_container_width=True)

            view = st.radio(f"Show {typ}", ["Live", "Redeemed"], horizontal=True, key=f"v{typ}")
            show = live if view == "Live" else redeemed
            cols = ["OPENING", "CUSTOMERNAME", "MOBILE", "ACCOUNT.1", "RSO NAME",
                    "OP-MONTH", "REFUND DATE"]
            cols = [c for c in cols if c in show.columns]
            st.dataframe(show[cols].sort_values("OPENING", ascending=False).head(500),
                         hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 11. PAGE — CUSTOMER DATA
# ---------------------------------------------------------------------------
def page_customers(sales, ghs, cn, month, view_rso, role):
    page_header("👥", "Customer Data", "Search · follow-up lists · upsell opportunities")
    scope = sales[sales["RSO_FINAL"] == view_rso] if view_rso else sales
    is_mgr = role in ("Admin", "Store Manager", "Floor Manager", "MD")
    if is_mgr and not view_rso:
        st.caption("Whole-store customer base.")

    q = st.text_input("🔎 Search by name or mobile number",
                      placeholder="e.g.  Priya  or  9425  or  Rathore")

    base = scope.copy()
    # Clean both search columns once — handle ints stored as int64 (no trailing .0)
    base["_name_s"] = base["CUSTOMERNAME"].fillna("").astype(str).str.lower().str.strip()
    base["_mob_s"]  = base["MOBILE"].apply(
        lambda x: str(int(x)) if pd.notna(x) and str(x).replace(".","").isdigit() else str(x)
    ).str.strip()

    if q and q.strip():
        ql = q.strip().lower()
        # Match every word in the query against the name (so "priya rathore" and "rathore priya" both work)
        words = ql.split()
        name_hit = base["_name_s"].apply(lambda n: all(w in n for w in words))
        mob_hit  = base["_mob_s"].str.contains(ql.replace(" ", ""), na=False)
        base = base[name_hit | mob_hit]

    # customer-level rollup
    grp = base[~base["IS_RETURN"]].groupby(["CUSTOMERNAME", "MOBILE"]).agg(
        Bills=("DOCNO", "nunique") if "DOCNO" in base else ("CUSTOMERNAME", "size"),
        Total_Value_L=("CMTOTAL", "sum"),
        Total_WT=("WT", "sum"),
        Studded_pcs=("IS_STUDDED", "sum"),
        Type=("CUSTTYPE", "last"),
        RSO=("RSO_FINAL", "last"),
    ).reset_index().sort_values("Total_Value_L", ascending=False)

    c = st.columns(3)
    with c[0]: kpi("Unique customers", f"{grp.shape[0]:,}")
    with c[1]: kpi("New : Existing",
                   f"{(base['CUSTTYPE']=='NEW').sum()} : {(base['CUSTTYPE']=='EXIST').sum()}")
    with c[2]: kpi("Avg ticket (₹L)",
                   f"{grp['Total_Value_L'].mean():.2f}" if len(grp) else "0")

    st.dataframe(grp.head(400), hide_index=True, use_container_width=True)

    # detail view
    if len(grp):
        st.markdown("#### Customer detail")
        pick = st.selectbox("Pick a customer", grp["CUSTOMERNAME"].head(200).tolist())
        det = base[base["CUSTOMERNAME"] == pick].copy()
        # SKU column = item code (shown so RSO can read/copy it)
        det["SKU"] = det["ITEMCODE"].astype(str)
        dcols = ["DATE", "SKU", "CATEGORY", "PRODUCT", "FLAG", "WT", "CMTOTAL", "CUSTTYPE", "RSO_FINAL"]
        dcols = [c for c in dcols if c in det.columns]
        st.dataframe(det[dcols], hide_index=True, use_container_width=True)

        # Click-to-view: pick any SKU from this customer's purchases to open its image.
        if "ITEMCODE" in det.columns and len(det):
            buys = det[~det["IS_RETURN"]].drop_duplicates(subset="ITEMCODE").reset_index(drop=True)
            sku_labels = [f"{r['ITEMCODE']} · {r.get('PRODUCT','')} ({r.get('CATEGORY','')})"
                          for _, r in buys.iterrows()]
            if sku_labels:
                st.markdown("##### 🔍 View product by SKU")
                chosen = st.selectbox("Select a SKU to open its image", sku_labels,
                                      key=f"sku_pick_{pick}")
                row = buys.iloc[sku_labels.index(chosen)]
                ic1, ic2 = st.columns([1, 1.4])
                with ic1:
                    val = row.get("CMTOTAL", 0) or 0
                    lines = [
                        ("SKU", str(row.get("ITEMCODE", "—"))),
                        ("Value", f"₹{val:.2f} L"),
                        ("Weight", f"{row.get('WT', 0):.2f} g"),
                        ("Category", str(row.get("CATEGORY", "—"))),
                        ("Type", "Studded" if row.get("IS_STUDDED") else "Plain / Other"),
                    ]
                    st.markdown(product_card(product_image_url(row.get("ITEMCODE", "")),
                                             str(row.get("PRODUCT", "Product")), lines),
                                unsafe_allow_html=True)
                with ic2:
                    st.caption("Tip: studded/designer pieces have catalogue images. "
                               "Plain gold and coins may show 'Image unavailable'.")

    # ── PENDING CREDIT NOTES for selected customer ────────────────────────────
    if len(grp) and cn is not None and not cn.empty:
        pick_mob = grp.loc[grp["CUSTOMERNAME"] == pick, "MOBILE"].values
        pick_mob_str = str(pick_mob[0]).strip() if len(pick_mob) else ""
        cust_cns = cn[
            cn["MOBILE"].astype(str).str.strip() == pick_mob_str
        ] if pick_mob_str else pd.DataFrame()
        if not cust_cns.empty:
            alert_cns = cust_cns[cust_cns["ALERT"]]
            label = f"📋 Pending Credit Notes — {len(cust_cns)} CN(s)"
            if len(alert_cns):
                label += f"  🔴 {len(alert_cns)} require action"
            with st.expander(label, expanded=bool(len(alert_cns))):
                def _style_cn(row):
                    if row.get("ALERT", False):
                        return ["background-color:#FFF0F0;color:#8B0000;font-weight:500"] * len(row)
                    return [""] * len(row)
                cn_disp = cust_cns[["CN TYPE", "AMOUNT", "DAYS", "CUR STATUS", "ALERT REASON"]].copy()
                cn_disp["AMOUNT"] = cn_disp["AMOUNT"].apply(lambda x: f"₹{x:,.0f}")
                cn_disp["DAYS"]   = cn_disp["DAYS"].apply(lambda x: f"{int(x)} days")
                cn_disp["ALERT"]  = cust_cns["ALERT"].values
                st.dataframe(
                    cn_disp.drop(columns=["ALERT"]).style.apply(
                        lambda r: _style_cn(cust_cns.iloc[r.name]), axis=1
                    ),
                    hide_index=True, use_container_width=True,
                )

    # ── FOLLOW-UP LIST ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔔 Follow-up List")
    st.caption("Powered by your sales and GHS data. Prioritised by opportunity size.")
    fl = follow_up_lists(sales, ghs, rso=view_rso)

    t_lapsed, t_mature, t_upsell = st.tabs([
        f"⏰ Lapsed ({len(fl['lapsed'])})",
        f"⚠️ GHS Maturing ({len(fl['maturing'])})",
        f"💡 Upsell Opportunity ({len(fl['upsell'])})",
    ])

    with t_lapsed:
        st.caption("Customers who haven't visited in **60+ days**, sorted by lifetime value. Call them first.")
        df = fl["lapsed"].copy()
        if len(df):
            df["mobile"] = df["mobile"].apply(
                lambda x: str(int(x)) if pd.notna(x) and str(x).replace(".","").isdigit() else str(x))
            df["last_visit"] = df["last_date"].dt.strftime("%d %b %Y")
            df["lifetime_val"] = df["lifetime_val"].round(1).astype(str) + " L"
            show = df[["CUSTOMERNAME","mobile","days_since","last_visit","lifetime_val","rso"]].copy()
            show.columns = ["Customer","Mobile","Days Since Visit","Last Visit","Lifetime Value","RSO"]
            st.dataframe(show.head(100), hide_index=True, use_container_width=True)
        else:
            st.success("No lapsed customers — great retention! ✅")

    with t_mature:
        st.caption("GHS/RGA accounts entering their maturity window. Reach out now before they go inactive.")
        df = fl["maturing"].copy()
        if len(df):
            df["days_left"] = df.apply(
                lambda r: (GHS_INACTIVE_DAYS if r["TYPE"] == "GHS" else RGA_INACTIVE_DAYS) - int(r["DAYS_OPEN"]), axis=1)
            df["MOBILE"] = df["MOBILE"].apply(
                lambda x: str(int(x)) if pd.notna(x) and str(x).replace(".","").isdigit() else str(x))
            def urgency(r):
                return "🔴" if r["days_left"] <= 7 else ("🟡" if r["days_left"] <= 15 else "🟢")
            df["⚡"] = df.apply(urgency, axis=1)
            show = df[["⚡","CUSTOMERNAME","MOBILE","TYPE","DAYS_OPEN","days_left","RSO NAME"]].copy()
            show.columns = ["","Customer","Mobile","Type","Days Open","Days Left","RSO"]
            st.dataframe(show.sort_values("Days Left").head(200), hide_index=True, use_container_width=True)
        else:
            st.success("No accounts maturing this month ✅")

    with t_upsell:
        st.caption("Customers who have **never bought a studded piece** — your best conversion targets.")
        df = fl["upsell"].copy()
        if len(df):
            df["mobile"] = df["mobile"].apply(
                lambda x: str(int(x)) if pd.notna(x) and str(x).replace(".","").isdigit() else str(x))
            df["last_visit"] = df["last_date"].dt.strftime("%d %b %Y")
            df["lifetime_val"] = df["lifetime_val"].round(1).astype(str) + " L"
            show = df[["CUSTOMERNAME","mobile","visits","last_visit","lifetime_val","rso"]].copy()
            show.columns = ["Customer","Mobile","Visits","Last Visit","Plain Value","RSO"]
            st.dataframe(show.head(100), hide_index=True, use_container_width=True)
        else:
            st.info("All customers have bought at least one studded piece!")

# ---------------------------------------------------------------------------
# 11b. PAGE — ANALYTICS (5-Year Intelligence)
# ---------------------------------------------------------------------------
def page_analytics():
    page_header("📈", "5-Year Business Intelligence", "Revenue trends · seasonality · customer RFM · RSO history")
    if not AE_AVAILABLE:
        st.info("Analytics engine not available. Ensure `analytics_engine.py` is in the same folder.")
        return

    hist = load_hist()
    if hist.empty:
        st.warning("Could not load `sales.xlsx`. Place it in the app folder.")
        return

    # ── STUDDED DECLINE ALERT (most important insight) ───────────────────────
    alert = studded_decline_alert(hist)
    if alert:
        gap = alert["gap_pts"]
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{RUBY},{RUBY_LT});border-radius:18px;
                    padding:20px 24px;margin-bottom:18px;color:#FFF8EC;">
          <div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;
                      color:#F4D77E;font-weight:700;">⚠️  Critical Insight</div>
          <div style="font-size:26px;font-weight:700;font-family:Cormorant Garamond,serif;
                      margin:6px 0;">Studded share has fallen {alert['decline_pts']:.1f} pts
                      since {int(alert['peak_year'])}</div>
          <div style="font-size:15px;color:#EAD3B0;">
            Peak: <b>{alert['peak_pct']:.1f}%</b> in {int(alert['peak_year'])} →
            Now: <b>{alert['current_pct']:.1f}%</b> →
            Target: <b>35%</b> &nbsp;|&nbsp;
            Gap: <b style="color:#F4D77E;">{gap:.1f} pts to close</b></div>
        </div>
        """, unsafe_allow_html=True)

    # ── YoY REVENUE ──────────────────────────────────────────────────────────
    yoy = yoy_summary(hist)
    if not yoy.empty:
        st.markdown("### Revenue & Studded Share by Year")
        rc1, rc2 = st.columns(2)
        with rc1:
            fig = px.bar(yoy, x="YEAR", y="Total_L", color_discrete_sequence=[GOLD],
                         labels={"Total_L":"Value (₹L)","YEAR":"Year"})
            fig.add_scatter(x=yoy["YEAR"], y=yoy["Studded_L"], name="Studded",
                            line=dict(color=RUBY, width=3), marker=dict(size=7))
            apply_chart_style(fig, height=300)
            st.plotly_chart(fig, use_container_width=True)
        with rc2:
            fig2 = px.line(yoy, x="YEAR", y="Studded_Share_Pct",
                           markers=True, labels={"Studded_Share_Pct":"Studded Share %","YEAR":"Year"})
            fig2.add_hline(y=35, line_dash="dash", line_color=GOLD_DEEP,
                           annotation_text="35% target")
            fig2.update_traces(line_color=RUBY, line_width=3, marker_size=9)
            apply_chart_style(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)

    # ── OCTOBER FORECAST ─────────────────────────────────────────────────────
    oct = october_forecast(hist)
    if oct:
        st.markdown("### 🪔 October (Dhanteras) Intelligence")
        oc1, oc2, oc3, oc4 = st.columns(4)
        with oc1: kpi("5-Yr Avg October", f"₹{oct['avg_oct_value_L']:.0f}L", "annual peak month")
        with oc2: kpi("2026 Forecast", f"₹{oct['forecast_2026_L']:.0f}L",
                      f"avg growth {oct['avg_yoy_growth_pct']:.1f}%/yr")
        with oc3: kpi("Oct Studded Share", f"{oct['avg_stud_share_oct']:.1f}%",
                      "highest of the year")
        with oc4:
            d = oct["days_to_oct"]
            kpi("Days to Oct 1", f"{d}", "start prep now" if d < 100 else f"~{d//30} months")
        st.info("💡 October alone = 16% of annual revenue (10× an average month). "
                "Stock fresh studded inventory by mid-September. "
                "Start customer outreach in August.")

    # ── SEASONAL CALENDAR ────────────────────────────────────────────────────
    seas = monthly_seasonality(hist)
    if not seas.empty:
        st.markdown("### Seasonal Revenue Calendar")
        fig3 = px.bar(seas, x="Month", y="Avg_L",
                      color="Is_Festival",
                      color_discrete_map={True: RUBY, False: GOLD},
                      labels={"Avg_L":"Avg monthly value (₹L)"},
                      text=seas["Festival_Label"])
        fig3.update_traces(marker_cornerradius=5, marker_line_width=0)
        fig3.update_layout(showlegend=False)
        apply_chart_style(fig3, height=300)
        st.plotly_chart(fig3, use_container_width=True)

    # ── RSO HISTORICAL PERFORMANCE ───────────────────────────────────────────
    rso_h = rso_history(hist)
    if not rso_h.empty:
        st.markdown("### RSO Performance History (Active Team)")
        rso_pivot = rso_h.pivot_table(index="RSO_H", columns="YEAR",
                                       values="Value_L", aggfunc="sum").fillna(0)
        rso_pivot.index = rso_pivot.index.str.title()
        rso_pivot.columns = [str(int(c)) for c in rso_pivot.columns]
        rso_pivot["5-Yr Total"] = rso_pivot.sum(axis=1)
        rso_pivot = rso_pivot.sort_values("5-Yr Total", ascending=False)
        st.dataframe(rso_pivot.round(0), use_container_width=True)

    # ── CUSTOMER SEGMENTS ─────────────────────────────────────────────────────
    st.markdown("### Customer Base Health")
    rfm = customer_rfm(hist)
    if not rfm.empty:
        seg_counts = rfm["segment"].value_counts()
        sc1, sc2, sc3, sc4 = st.columns(4)
        for col, (seg, color) in zip(
            [sc1,sc2,sc3,sc4],
            [("🔥 Active",EMERALD),("⚡ Warm",GOLD_DEEP),
             ("⏰ At Risk",AMBER),("💤 Lost",RED)]
        ):
            count = seg_counts.get(seg[2:].strip(), seg_counts.get(seg, 0))
            val   = rfm.loc[rfm["segment"]==seg,"monetary"].sum() if seg in rfm["segment"].values else 0
            col.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{seg}</div>'
                f'<div class="kpi-value" style="color:{color}">{int(count):,}</div>'
                f'<div class="kpi-sub">₹{val:.0f}L lifetime</div></div>',
                unsafe_allow_html=True)
        st.caption("Active <60 days · Warm 60-180 · At Risk 180-365 · Lost 365+ days since last visit")


# ---------------------------------------------------------------------------
# 11c. PAGE — STOCK INTELLIGENCE
# ---------------------------------------------------------------------------
def page_stock_intel(view_rso=None):
    page_header("🏪", "Stock Intelligence", "Push recommendations · browse inventory · category breakdown")
    if not AE_AVAILABLE:
        st.info("Analytics engine not available. Ensure `analytics_engine.py` is in the same folder.")
        return

    stock = load_stock()
    hist  = load_hist()

    if stock.empty:
        st.warning("Could not load `stock.xlsx`. Place it in the app folder.")
        return

    # ── STOCK OVERVIEW ───────────────────────────────────────────────────────
    summ = stock_summary(stock)
    sv1,sv2,sv3,sv4 = st.columns(4)
    with sv1: kpi("Total Items", f"{summ.get('total_items',0):,}", "in current inventory")
    with sv2: kpi("Total Value", f"₹{summ.get('total_value_L',0):.0f}L", "at current price")
    with sv3: kpi("Studded Value", f"₹{summ.get('studded_value_L',0):.0f}L",
                  f"{summ.get('studded_items',0)} pieces")
    with sv4: kpi("Plain Value", f"₹{summ.get('plain_value_L',0):.0f}L", "including coins")

    st.markdown("---")
    tab_push, tab_browse, tab_cat = st.tabs([
        "🎯 Push Recommendations", "🖼️ Browse Stock", "📊 By Category"])

    with tab_push:
        st.markdown("#### 🎯 SKU-level customer push recommendations")
        st.caption(
            "Each card = one specific piece matched to the best-fit customer in that RSO's book. "
            "Matching uses: category preference · price band · recency of last visit. "
            "Studded push is prioritised to improve share."
        )
        if hist.empty:
            st.warning("Place `sales.xlsx` in the folder for customer matching.")
        else:
            rfm = customer_rfm(hist)
            recs = stock_push_recommendations(stock, rfm, rso_filter=view_rso, top_n=80)
            if recs.empty:
                st.info("No strong matches found for current filters.")
            else:
                stud_recs = recs[recs["IS_STUDDED"] == True].reset_index(drop=True)
                plain_recs = recs[recs["IS_STUDDED"] == False].reset_index(drop=True)

                # RSO filter (optional override)
                all_rsos_push = sorted(recs["RSO"].dropna().unique().tolist())
                push_rso = st.selectbox("Filter by RSO (push view)",
                                        ["All RSOs"] + all_rsos_push, key="push_rso_filter")

                def filter_and_render(df, label, per_page=12):
                    if df.empty:
                        st.info(f"No {label} recommendations.")
                        return
                    if push_rso != "All RSOs":
                        df = df[df["RSO"] == push_rso].reset_index(drop=True)
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                        f'<span style="font-size:14px;font-weight:700;color:{RUBY};">'
                        f'{len(df)} pieces to push</span>'
                        f'<span style="font-size:13px;color:{MUTED};">·</span>'
                        f'<span style="font-size:13px;color:{MUTED};">'
                        f'₹{df["Value (₹L)"].sum():.1f}L total value</span></div>',
                        unsafe_allow_html=True)
                    show_n = st.slider(f"Show top N {label} pieces", 6, min(60, len(df)),
                                       min(per_page, len(df)), step=3,
                                       key=f"push_n_{label.replace(' ','_')}")
                    for i in range(0, show_n, 3):
                        cols = st.columns(3)
                        for col, (_, row) in zip(cols, df.iloc[i:i+3].iterrows()):
                            col.markdown(push_rec_card(row), unsafe_allow_html=True)

                push_tab_stud, push_tab_plain = st.tabs([
                    f"💎 Studded Push  ({len(stud_recs)})",
                    f"🪙 Plain Gold Push  ({len(plain_recs)})",
                ])
                with push_tab_stud:
                    st.markdown(
                        f'<div style="background:linear-gradient(90deg,{RUBY}18,transparent);'
                        f'border-left:3px solid {RUBY};border-radius:8px;padding:10px 14px;'
                        f'margin-bottom:12px;font-size:13px;color:{ESPRESSO};">'
                        f'<b>Studded share is in structural decline</b> — these pieces improve it. '
                        f'Each card shows one specific SKU + the best customer to call for it.</div>',
                        unsafe_allow_html=True)
                    filter_and_render(stud_recs, "studded")
                with push_tab_plain:
                    filter_and_render(plain_recs, "plain gold")

    with tab_browse:
        st.markdown("#### Browse inventory with images")
        cats = ["All"] + sorted(stock["Category"].dropna().unique().tolist())
        bc1, bc2 = st.columns([1,2])
        with bc1:
            cat_f = st.selectbox("Category", cats, key="stock_cat")
            flag_f = st.radio("Type", ["All","Studded","Plain"], horizontal=True, key="stock_flag")
        with bc2:
            price_min, price_max = st.slider("Price range (₹L)", 0.0,
                                             float(stock["AMT_L"].quantile(0.99)),
                                             (0.0, float(stock["AMT_L"].quantile(0.95))),
                                             key="stock_price")
        df_s = stock.copy()
        if cat_f != "All": df_s = df_s[df_s["Category"] == cat_f]
        if flag_f == "Studded": df_s = df_s[df_s["IS_STUDDED"]]
        elif flag_f == "Plain":  df_s = df_s[~df_s["IS_STUDDED"]]
        df_s = df_s[(df_s["AMT_L"] >= price_min) & (df_s["AMT_L"] <= price_max)]
        st.caption(f"{len(df_s)} items · ₹{df_s['AMT_L'].sum():.0f}L total")

        for i in range(0, min(len(df_s), 30), 3):
            cols = st.columns(3)
            for col, (_, r) in zip(cols, df_s.iloc[i:i+3].iterrows()):
                lines = [
                    ("Price", f"₹{r['AMT_L']:.2f}L"),
                    ("Weight", f"{r['WT']:.2f} g"),
                    ("Category", str(r.get("Category","—"))),
                    ("Karat", str(r.get("KARAT","—"))),
                ]
                with col:
                    st.markdown(product_card(r.get("IMG",""),
                                             str(r.get("Product","Product")), lines),
                                unsafe_allow_html=True)

    with tab_cat:
        st.markdown("#### Stock breakdown by category")
        cat_df = stock.groupby("Category").agg(
            Items=("ItemCode","count"),
            Value_L=("AMT_L","sum"),
            Wt_g=("WT","sum"),
        ).sort_values("Value_L", ascending=False).round(1)
        cat_df.columns = ["Items","Value (₹L)","Weight (g)"]
        st.dataframe(cat_df, use_container_width=True)

        fig = px.bar(cat_df.reset_index().head(12), x="Value (₹L)", y="Category",
                     orientation="h", color_discrete_sequence=[GOLD])
        fig.update_traces(marker_cornerradius=5, marker_line_width=0)
        apply_chart_style(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)



def product_card(img_url, title, lines, badge=None):
    """A framed product tile: image in a box on top, details below.
       lines = list of (label, value) tuples."""
    detail = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:8px;padding:3px 0;'
        f'border-bottom:1px solid rgba(123,30,59,0.08);">'
        f'<span style="color:{MUTED};font-size:12px;">{l}</span>'
        f'<span style="color:{ESPRESSO};font-size:13px;font-weight:600;">{v}</span></div>'
        for l, v in lines
    )
    badge_html = (f'<div style="position:absolute;top:10px;right:10px;background:{GOLD};color:#fff;'
                  f'font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">{badge}</div>'
                  if badge else "")
    return (
        f'<div class="kpi-card" style="padding:0;overflow:hidden;">' +
        f'<div style="position:relative;background:#F1E8DA;height:190px;display:flex;' +
        f'align-items:center;justify-content:center;flex-direction:column;">' +
        badge_html +
        f'<img src="{img_url}" loading="lazy" ' +
        f'style="max-width:100%;max-height:186px;object-fit:contain;" ' +
        f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';" />' +
        f'<div style="display:none;flex-direction:column;align-items:center;justify-content:center;' +
        f'color:{MUTED};font-size:28px;gap:6px;">' +
        f'<span>💍</span>' +
        f'<span style="font-size:11px;letter-spacing:1px;text-transform:uppercase;">No image</span>' +
        f'</div></div>' +
        f'<div style="padding:12px 14px 14px;">' +
        f'<div style="font-family:Cormorant Garamond,serif;font-size:17px;color:{RUBY};' +
        f'font-weight:700;line-height:1.2;margin-bottom:8px;">{title}</div>' +
        detail +
        f'</div></div>'
    )


def push_rec_card(r):
    """Push-recommendation card: product image + SKU details + best-fit customer match block."""
    is_stud = bool(r.get("IS_STUDDED", False))
    badge_bg   = RUBY        if is_stud else GOLD_DEEP
    badge_txt  = "💎 Studded" if is_stud else "🪙 Plain Gold"
    seg        = str(r.get("Segment", ""))
    seg_color  = (EMERALD   if "Active" in seg else
                  GOLD_DEEP  if "Warm"   in seg else
                  AMBER      if "Risk"   in seg else RED)
    img_url    = r.get("IMG", "")
    last_days  = r.get("Last Visit (days)", "—")
    return f"""
<div class="kpi-card" style="padding:0;overflow:hidden;margin-bottom:14px;">
  <div style="position:relative;background:#F1E8DA;height:170px;display:flex;
       align-items:center;justify-content:center;flex-direction:column;overflow:hidden;">
    <div style="position:absolute;top:8px;left:10px;background:{badge_bg};color:#fff;
         font-size:10px;font-weight:700;padding:2px 9px;border-radius:20px;z-index:1;">
      {badge_txt}</div>
    <img src="{img_url}" loading="lazy"
         style="max-width:100%;max-height:166px;object-fit:contain;"
         onerror="this.style.display='none';this.nextElementSibling.style.display='flex';" />
    <div style="display:none;flex-direction:column;align-items:center;justify-content:center;
         color:{MUTED};font-size:26px;gap:4px;">
      <span>💍</span>
      <span style="font-size:10px;letter-spacing:1px;text-transform:uppercase;">No image</span>
    </div>
  </div>
  <div style="padding:11px 13px 13px;">
    <div style="font-family:'Cormorant Garamond',serif;font-size:16px;color:{RUBY};
         font-weight:700;line-height:1.2;margin-bottom:4px;">{r.get("Product","—")}</div>
    <div style="font-size:11px;color:{MUTED};margin-bottom:8px;">
      SKU: <b style="color:{ESPRESSO}">{r.get("ItemCode","—")}</b>
      &nbsp;·&nbsp; {r.get("Category","—")}</div>
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;">
      <span style="font-size:17px;font-weight:700;color:{GOLD_DEEP};">₹{r.get("Value (₹L)",0):.2f}L</span>
      <span style="font-size:12px;color:{MUTED};">{r.get("Wt (g)",0):.1f} g</span>
    </div>
    <div style="border-top:1px dashed rgba(201,162,39,0.45);padding-top:9px;">
      <div style="font-size:10px;letter-spacing:1.3px;text-transform:uppercase;color:{MUTED};margin-bottom:5px;">
        Best Customer Match</div>
      <div style="font-weight:700;color:{ESPRESSO};font-size:14px;">{r.get("Best Customer","—")}</div>
      <div style="font-size:12px;color:{MUTED};margin-bottom:6px;">{r.get("Customer Mobile","—")}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:11px;color:{MUTED};">
          Last visit: <b style="color:{ESPRESSO}">{last_days}d ago</b></span>
        <span style="background:rgba(123,30,59,0.08);color:{seg_color};font-size:10px;
             font-weight:700;padding:2px 7px;border-radius:10px;">{seg}</span>
      </div>
      <div style="font-size:11px;color:{MUTED};margin-top:4px;">RSO: {r.get("RSO","—")}
        &nbsp;·&nbsp; Score: {r.get("Match Score",0):.2f}</div>
    </div>
  </div>
</div>"""


def page_sludge(sludge, month):
    page_header("📦", "Sludge — Aged Stock", "1% incentive on selling value · tap a category to filter")
    if sludge is None or sludge.empty:
        st.info(f"Drop **{SLUDGE_FILE}** in the app folder to see the aged-stock catalogue here.")
        return

    st.caption("Each piece earns its listed incentive plus the extra discount you can offer to close it. "
               "Tap a category to filter. Images load from the Titan catalogue.")

    # ---- filters & summary ----
    cats = ["All"] + sorted([c for c in sludge["Category"].dropna().unique()]) \
        if "Category" in sludge.columns else ["All"]
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        cat = st.selectbox("Category", cats)
    with fc2:
        sort_by = st.selectbox("Sort by", ["Age (oldest)", "Value (highest)", "Incentive (highest)"])
    with fc3:
        search = st.text_input("Search product / SKU", placeholder="ring, 50W4M...")
    with fc4:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Pieces in list</div>"
                    f"<div class='kpi-value'>{len(sludge)}</div>"
                    f"<div class='kpi-sub'>total incentive ₹{sludge['INCENTIVE'].sum():,.0f}</div></div>",
                    unsafe_allow_html=True)

    df = sludge.copy()
    if cat != "All" and "Category" in df.columns:
        df = df[df["Category"] == cat]
    if search:
        s = search.lower()
        mask = df.get("Product", pd.Series("", index=df.index)).astype(str).str.lower().str.contains(s) | \
               df.get("ItemCode", pd.Series("", index=df.index)).astype(str).str.lower().str.contains(s)
        df = df[mask]

    if "Age" in df.columns and sort_by.startswith("Age"):
        df = df.sort_values("Age", ascending=False)
    elif "Cur-Final" in df.columns and sort_by.startswith("Value"):
        df = df.sort_values("Cur-Final", ascending=False)
    elif "INCENTIVE" in df.columns:
        df = df.sort_values("INCENTIVE", ascending=False)

    st.markdown(f"<div class='small-muted' style='margin:6px 0 12px'>{len(df)} pieces shown</div>",
                unsafe_allow_html=True)

    # ---- product grid (3 per row) ----
    rows = df.to_dict("records")
    for i in range(0, len(rows), 3):
        cols = st.columns(3)
        for col, r in zip(cols, rows[i:i+3]):
            price = r.get("Cur-Final", 0) or 0
            incentive = r.get("INCENTIVE", 0) or 0
            disc = r.get("EXTRA DISC", "—")
            wt = r.get("Wt", 0) or 0
            age = r.get("Age", "—")
            lines = [
                ("Price", f"₹{price:,.0f}"),
                ("Weight", f"{wt:.2f} g"),
                ("Category", str(r.get("Category", "—"))),
                ("Incentive", f"₹{incentive:,.0f}"),
                ("Extra discount", str(disc)),
            ]
            title = str(r.get("Product", "Product"))
            badge = f"{int(age)}d aged" if isinstance(age, (int, float)) and not pd.isna(age) else None
            with col:
                st.markdown(product_card(r.get("IMG", ""), title, lines, badge=badge),
                            unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 13. PAGE — CREDIT NOTES
# ---------------------------------------------------------------------------
def page_cn(cn: pd.DataFrame, view_rso, role):
    page_header("📋", "Credit Notes", "Pending CNs · action required · overdue alerts")

    if cn is None or cn.empty:
        st.info(f"Upload **{CN_FILE}** via the Data Manager to see pending credit notes here.")
        return

    is_mgr = role in ("Admin", "Store Manager", "Floor Manager", "MD")

    # scope to RSO if not a manager
    scope = cn.copy()
    if not is_mgr and view_rso:
        scope = scope[scope["RSO NAME"] == view_rso.upper()]

    alerts = scope[scope["ALERT"]].copy()
    clean  = scope[~scope["ALERT"]].copy()

    DISPLAY_COLS = ["CN TYPE", "AMOUNT", "CUSTOMER NAME", "MOBILE", "DAYS", "ALERT REASON"]
    # column name in file is "CUSTOMER NAME"
    disp_cols = [c for c in DISPLAY_COLS if c in scope.columns]

    def _fmt_amount(df):
        d = df[disp_cols].copy()
        d["AMOUNT"] = d["AMOUNT"].apply(lambda x: f"₹{x:,.0f}")
        d["DAYS"]   = d["DAYS"].apply(lambda x: f"{int(x)} days")
        return d

    # ── summary bar ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Total CNs", f"{len(scope):,}")
    with c2: kpi("🔴 Alerts", f"{len(alerts):,}")
    with c3: kpi("Alert Amount", f"₹{alerts['AMOUNT'].sum():,.0f}")
    with c4: kpi("Total Amount", f"₹{scope['AMOUNT'].sum():,.0f}")

    # ── alert table (always expanded) ────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### 🔴 Action Required — {len(alerts)} CNs")
    st.caption("These CNs must be closed or booked. FREE CNs must be applied to a bill.")

    if len(alerts):
        def _red_style(row):
            return ["background-color: #FFF0F0; color: #8B0000; font-weight: 500"] * len(row)

        alert_display = _fmt_amount(alerts.sort_values("DAYS", ascending=False))
        st.dataframe(
            alert_display.style.apply(_red_style, axis=1),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("No alerts — all CNs are within acceptable thresholds.")

    # ── full list ─────────────────────────────────────────────────────────────
    with st.expander(f"📄 All CNs — {len(scope)} rows", expanded=False):
        if is_mgr:
            rso_filter = ["(all RSOs)"] + sorted(scope["RSO NAME"].dropna().unique().tolist())
            sel_rso = st.selectbox("Filter by RSO", rso_filter, key="cn_rso_filter")
            view = scope if sel_rso == "(all RSOs)" else scope[scope["RSO NAME"] == sel_rso]
        else:
            view = scope
        st.dataframe(_fmt_amount(view.sort_values("DAYS", ascending=False)),
                     hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 13. PAGE — TICKETING / TASKS  (in-session prototype store)
# ---------------------------------------------------------------------------
def page_tickets(sales, ghs, month, view_rso, role):
    page_header("✅", "Tasks & Tickets", "Assign · track · close — manager-assigned daily priorities")
    if "tickets" not in st.session_state:
        # seed a few realistic tasks
        st.session_state.tickets = [
            dict(id=1, title="Run Wednesday studded masterclass", assignee="RITESH BHATNAGAR",
                 due=dt.date.today() + dt.timedelta(days=2), status="Open", by="Swaroop"),
            dict(id=2, title="GHS account-opening session for Saini & Kalyani",
                 assignee="NIKHAR AGARWAL", due=dt.date.today() - dt.timedelta(days=1),
                 status="Open", by="Swaroop"),
            dict(id=3, title="Pick 5 sludge pieces to own this month", assignee="RUCHI AGARWAL",
                 due=dt.date.today() + dt.timedelta(days=4), status="Open", by="Deepesh"),
        ]
    tickets = st.session_state.tickets
    overdue = [t for t in tickets if t["status"] == "Open" and t["due"] < dt.date.today()]

    # notification bell
    bell = "🔔" if overdue else "🔕"
    st.markdown(f"### {bell} {len(overdue)} overdue · {sum(t['status']=='Open' for t in tickets)} open")
    if overdue:
        for t in overdue:
            st.markdown(f"<div class='kpi-card' style='border-color:{RED}55'>"
                        f"⚠️ <b>{t['title']}</b> → {t['assignee'].title()} "
                        f"<span class='small-muted'>(due {t['due']}, WhatsApp alert simulated)</span></div>",
                        unsafe_allow_html=True)

    is_mgr = role in ("Admin", "Store Manager", "Floor Manager", "MD")
    if is_mgr:
        with st.expander("➕ Assign a new task"):
            rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
            t_title = st.text_input("Task")
            t_who = st.selectbox("Assign to", rsos)
            t_due = st.date_input("Due", dt.date.today() + dt.timedelta(days=3))
            if st.button("Create task"):
                nid = max([t["id"] for t in tickets], default=0) + 1
                tickets.append(dict(id=nid, title=t_title, assignee=t_who,
                                    due=t_due, status="Open", name=view_rso, by=role))
                st.success("Task created.")
                st.rerun()

    st.markdown("#### Task board")
    mine = tickets if (is_mgr or not view_rso) else [t for t in tickets if t["assignee"] == view_rso]
    for t in mine:
        cc = st.columns([4, 2, 1.4, 1.4])
        overdue_flag = t["status"] == "Open" and t["due"] < dt.date.today()
        col = RED if overdue_flag else (GREEN if t["status"] == "Done" else "#8A7A6B")
        cc[0].markdown(f"<span style='color:{col}'>{'✓' if t['status']=='Done' else '○'} "
                       f"<b>{t['title']}</b></span>", unsafe_allow_html=True)
        cc[1].markdown(f"<span class='small-muted'>{t['assignee'].title()}</span>", unsafe_allow_html=True)
        cc[2].markdown(f"<span class='small-muted'>{t['due']}</span>", unsafe_allow_html=True)
        if t["status"] == "Open":
            if cc[3].button("Done", key=f"done{t['id']}"):
                t["status"] = "Done"; st.rerun()
        else:
            cc[3].markdown("✅")


# ---------------------------------------------------------------------------
# 13. AI SEARCH  (rule-based natural-language over the data)
# ---------------------------------------------------------------------------
def _rso_metric_table(sales, ghs, rso_targets, month, metric):
    """Build a (rso, value) table for any supported metric. Returns list of tuples."""
    rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
    out = []
    for r in rsos:
        rsl = rso_month_slice(sales, r, month)
        rsl_pos = rsl[~rsl["IS_RETURN"]]
        val = rsl_pos["CMTOTAL"].clip(lower=0).sum()
        stud_val = rsl_pos.loc[rsl_pos["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
        bills = len(rsl_pos)
        if metric == "value":           m = val
        elif metric == "studded_value": m = stud_val
        elif metric == "studded_pcs":   m = studded_pieces(rsl)
        elif metric == "hvs":           m = hvs_pieces(rsl)
        elif metric == "ghs":           m = ghs_opens_in_month(ghs, r, month)["TOTAL"]
        elif metric == "bills":         m = bills
        elif metric == "aev":           m = (val / bills) if bills else 0
        elif metric == "studded_share":
            m = (stud_val / val * 100) if val else 0
        elif metric == "gep_pct":
            gb = int((rsl_pos["GEP-AMT"].fillna(0) > 0).sum())
            m = (gb / bills * 100) if bills else 0
        elif metric == "upsell":
            red = rsl_pos["GHS-AMT"].sum() / 100000.0
            m = (red / val * 100) if val else 0
        elif metric == "incentive":
            m = compute_incentive(sales, ghs, r, month)["total"]
        elif metric == "achievement":
            tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"]==r.upper()) &
                                  (rso_targets["MONTH"]==int(month))]
            tgt = float(tgt_row["TOTAL"].iloc[0]) if len(tgt_row) else 100.0
            m = (val / tgt * 100) if tgt else 0
        else:
            m = val
        out.append((r, m))
    return out


# How each metric is labelled and formatted in answers
_METRIC_META = {
    "value":         ("total value", lambda v: f"₹{v:,.1f}L"),
    "studded_value": ("studded value", lambda v: f"₹{v:,.1f}L"),
    "studded_pcs":   ("studded pieces", lambda v: f"{int(v)} pcs"),
    "hvs":           ("HVS pieces", lambda v: f"{int(v)} pcs"),
    "ghs":           ("net GHS+RGA opens", lambda v: f"{int(v)}"),
    "bills":         ("bills", lambda v: f"{int(v)}"),
    "aev":           ("avg bill value", lambda v: f"₹{v:,.2f}L"),
    "studded_share": ("studded share", lambda v: f"{v:.1f}%"),
    "gep_pct":       ("GEP contribution", lambda v: f"{v:.1f}%"),
    "upsell":        ("upsell %", lambda v: f"{v:.1f}%"),
    "incentive":     ("incentive", lambda v: inr(v)),
    "achievement":   ("target achievement", lambda v: f"{v:.0f}%"),
}


def _detect_metric(q):
    """Map free text to a metric key."""
    if "hvs" in q or "high value" in q or "high-value" in q: return "hvs"
    if "ghs" in q or "rga" in q or "account" in q or "opens" in q or "scheme" in q: return "ghs"
    if "incentive" in q or "payout" in q or "earning" in q or "earn" in q: return "incentive"
    if "share" in q: return "studded_share"
    if "gep" in q or "exchange" in q or "old gold" in q: return "gep_pct"
    if "upsell" in q: return "upsell"
    if "achievement" in q or "target" in q or "vs target" in q or "% of target" in q: return "achievement"
    if "bill" in q or "transaction" in q or "invoice" in q: return "bills"
    if "aev" in q or "avg" in q or "average" in q or "ticket" in q: return "aev"
    if "studded value" in q or "studded val" in q: return "studded_value"
    if "studded" in q or "stud" in q or "diamond" in q: return "studded_pcs"
    if "value" in q or "sales" in q or "revenue" in q or "turnover" in q: return "value"
    return None


def ai_search(sales, ghs, rso_targets, month, query):
    q = query.lower().strip()
    rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
    found = [r for r in rsos if r.lower() in q or r.split()[0].lower() in q]
    months = sorted(sales["MONTH"].dropna().unique().tolist())

    # direction: lowest vs highest
    wants_low = any(w in q for w in ["lowest", "worst", "bottom", "least", "weakest", "poorest", "min"])
    wants_high = any(w in q for w in ["highest", "top", "best", "most", "max", "leading", "strongest"])

    # how many to show
    n = 5
    for tok in q.split():
        if tok.isdigit() and 1 <= int(tok) <= 20:
            n = int(tok)

    # ── intent: ranked list by metric (highest OR lowest) ──
    metric = _detect_metric(q)
    if metric and (wants_low or wants_high or "rank" in q or "list" in q or "all rso" in q):
        label, fmt = _METRIC_META[metric]
        tab = _rso_metric_table(sales, ghs, rso_targets, month, metric)
        tab.sort(key=lambda x: x[1], reverse=not wants_low)
        head = f"**{'Lowest' if wants_low else 'Top'} {n} by {label}** ({int(month)}):"
        lines = [head, ""]
        for i, (r, v) in enumerate(tab[:n]):
            lines.append(f"{i+1}. {r.title()} — {fmt(v)}")
        # add store context
        vals = [v for _, v in tab]
        if metric in ("value","studded_value","incentive","bills"):
            lines.append(f"\n_Store total: {fmt(sum(vals))} · average: {fmt(sum(vals)/len(vals))}_")
        else:
            lines.append(f"\n_Store average: {fmt(sum(vals)/len(vals))}_")
        return "\n".join(lines)

    # ── intent: compare two+ named RSOs (multi-metric, optional multi-month) ──
    if "compare" in q or len(found) >= 2:
        if len(found) >= 2:
            mscope = months if ("all" in q or "trend" in q) else \
                     (months[-2:] if ("2 month" in q or "last 2" in q or "two month" in q) else [month])
            picks = found[:4]
            lines = [f"**Comparison — {', '.join(p.title() for p in picks)}**", ""]
            for m in mscope:
                lines.append(f"**{int(m)}:**")
                for r in picks:
                    rsl = rso_month_slice(sales, r, m)
                    rp = rsl[~rsl["IS_RETURN"]]
                    v = rp["CMTOTAL"].clip(lower=0).sum()
                    sv = rp.loc[rp["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
                    sp = studded_pieces(rsl)
                    op = ghs_opens_in_month(ghs, r, m)["TOTAL"]
                    inc = compute_incentive(sales, ghs, r, m)["total"]
                    lines.append(f"  • {r.title()}: ₹{v:.1f}L value · {sp} stud pcs · "
                                 f"₹{sv:.1f}L studded · {op} GHS · {inr(inc)}")
                lines.append("")
            return "\n".join(lines)

    # ── intent: single RSO deep summary (optionally month-over-month) ──
    if len(found) == 1:
        r = found[0]
        res = compute_incentive(sales, ghs, r, month)
        prof = RSO_PROFILE.get(r, DEFAULT_PROFILE)
        rsl = rso_month_slice(sales, r, month)
        rp = rsl[~rsl["IS_RETURN"]]
        v = rp["CMTOTAL"].clip(lower=0).sum()
        sv = rp.loc[rp["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
        share = (sv / v * 100) if v else 0
        tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"]==r.upper()) &
                              (rso_targets["MONTH"]==int(month))]
        tgt = float(tgt_row["TOTAL"].iloc[0]) if len(tgt_row) else 0
        ach = (v / tgt * 100) if tgt else 0
        # month trend
        trend = []
        for m in months:
            mp = rso_month_slice(sales, r, m)
            mp = mp[~mp["IS_RETURN"]]
            trend.append(f"{int(m)}: ₹{mp['CMTOTAL'].clip(lower=0).sum():.0f}L")
        return (f"**{r.title()} — {int(month)}**\n\n"
                f"- Total value: ₹{v:.1f}L" + (f" ({ach:.0f}% of ₹{tgt:.0f}L target)" if tgt else "") + "\n"
                f"- Studded: ₹{sv:.1f}L · {res['studded_pieces']} pcs · {share:.1f}% share\n"
                f"- HVS pieces: {res['hvs_pieces']} · GHS+RGA opens: {res['ghs_opens']}\n"
                f"- Incentive so far: **{inr(res['total'])}**\n"
                f"- {next_slab_hint(res['studded_pieces'])}\n"
                f"- Trend: {' → '.join(trend)}\n"
                f"- Archetype: {prof['archetype']} · pressure: {prof['pressure']}\n"
                f"- Coaching note: {prof['watch']}")

    # ── intent: store-wide snapshot ──
    if any(w in q for w in ["store", "overall", "total", "summary", "how are we", "team"]):
        msl = sales[(sales["MONTH"]==month) & (~sales["IS_RETURN"])]
        tv = msl["CMTOTAL"].clip(lower=0).sum()
        sv = msl.loc[msl["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
        share = (sv/tv*100) if tv else 0
        opens = store_ghs_net(ghs, month)
        return (f"**Store snapshot — {int(month)}**\n\n"
                f"- Total value: ₹{tv:.1f}L · Studded: ₹{sv:.1f}L ({share:.1f}% share)\n"
                f"- Studded gate: {'OPEN ✅' if share>=30 else 'BELOW ⚠️ (need 30%)'}\n"
                f"- GHS net opens: {opens['NET']} ({opens['OPENED']} opened − {opens['REFUNDED']} refunded)\n"
                f"- Active RSOs: {msl['RSO_FINAL'].nunique()}")

    # ── fallback: list what it can do ──
    return ("I can answer questions like:\n\n"
            "**Rankings** (highest *or* lowest):\n"
            "- *“lowest GHS opens”* · *“top 3 by value”* · *“worst studded share”*\n"
            "- *“highest incentive”* · *“bottom 5 by target achievement”* · *“lowest avg bill”*\n\n"
            "**Comparisons:**\n"
            "- *“compare Rakesh and Sunita”* · *“compare Manda and Anita all months”*\n\n"
            "**Individuals:** type any RSO's name for a full breakdown with trend.\n\n"
            "**Store:** *“store summary”* · *“how are we doing overall”*\n\n"
            "Metrics I know: value, studded value/pieces/share, HVS, GHS/RGA opens, "
            "bills, avg bill value, GEP %, upsell %, incentive, target achievement.")

# ---------------------------------------------------------------------------
# 14. PAGE — ADMIN
# ---------------------------------------------------------------------------
def page_admin(sales, ghs, rso_targets, store_targets, month):
    page_header("⚙️", "Admin Panel", "Leaderboard · exceptions · targets · data health · pool simulation")
    
    # Create tabs
    tab_rso, tab_tgt, tab_inc, tab_data, tab_lb, tab_exc, tab_cmp = st.tabs([
        "🔍 RSO Search", "📊 Targets", "💰 Incentive", "📈 Data",
        "🏆 Leaderboard", "🚨 Exceptions", "⚖️ Compare"])
    
    with tab_rso:
        st.markdown("### Search & Filter RSOs")
        rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
        search_q = st.text_input("Search RSO name", placeholder="Rakesh, Sunita...")
        filtered = [r for r in rsos if search_q.lower() in r.lower()] if search_q else rsos
        
        if filtered:
            pick = st.selectbox("Select RSO", filtered, key="admin_rso_pick")
            res = compute_incentive(sales, ghs, pick, month)
            prof = RSO_PROFILE.get(pick, DEFAULT_PROFILE)
            rsl = rso_month_slice(sales, pick, month)[~rso_month_slice(sales, pick, month)["IS_RETURN"]]
            val = rsl["CMTOTAL"].clip(lower=0).sum()
            stud_val = rsl.loc[rsl["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
            bills = len(rsl)
            rso_tgt = rso_targets[(rso_targets["EMPLOYEE NAME"]==pick.upper()) & (rso_targets["MONTH"]==int(month))]
            tgt_val = float(rso_tgt["TOTAL"].iloc[0]) if len(rso_tgt)>0 and "TOTAL" in rso_tgt.columns else 100.0
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: kpi("Value (L)", f"{val:.1f}", f"Target: {tgt_val:.0f}L")
            with c2: kpi("Studded (L)", f"{stud_val:.1f}", f"Pcs: {res['studded_pieces']}")
            with c3: kpi("HVS", f"{res['hvs_pieces']}", f"GHS: {res['ghs_opens']}")
            with c4: kpi("Incentive", inr(res["total"]), f"Annual: {inr(res['total']*12)}")
            
            st.markdown("#### Metrics")
            metrics_df = pd.DataFrame({
                "Metric": ["Value", "Studded Value", "Plain Value", "Bills", "GEP Bills %", "Avg Ticket", "Pieces", "HVS", "GHS", "Upsell %"],
                "Value": [f"₹{val:.1f}L", f"₹{stud_val:.1f}L", f"₹{rsl.loc[~rsl['IS_STUDDED'], 'CMTOTAL'].clip(lower=0).sum():.1f}L",
                         f"{bills}", f"{int((rsl['GEP-AMT'].fillna(0)>0).sum())}/{bills}", f"₹{val/bills:.2f}L" if bills else "—",
                         f"{res['studded_pieces']}", f"{res['hvs_pieces']}", f"{res['ghs_opens']}",
                         f"{(rsl['GHS-AMT'].sum()/100000)/val*100:.1f}%" if val else "—"]
            })
            st.dataframe(metrics_df, hide_index=True, use_container_width=True)
            
            st.markdown(f"#### Profile: {pick.title()}")
            pc1, pc2 = st.columns(2)
            with pc1:
                role_txt = f"**Role:** {prof['role']}\n**Archetype:** {prof['archetype']}\n**Pressure:** {prof['pressure']}\n**Team:** {prof['team']}"
                st.markdown(role_txt)
            with pc2:
                mentor_str = ', '.join(prof.get('mentees',[])) if prof.get('mentees') else '—'
                coach_txt = f"**Coach:** {prof.get('coach','—')}\n**Mentees:** {mentor_str}\n**Genius:** {prof['genius'][:70]}...\n**Watch:** {prof['watch'][:70]}..."
                st.markdown(coach_txt)
    
    with tab_tgt:
        st.markdown("#### Store Targets")
        store_df = pd.DataFrame({
            "Category": ["Overall", "Plain", "Studded", "Coin", "GHS Opens"],
            "Target": [
                f"₹{store_target(store_targets, 0, month):.0f} L",
                f"₹{store_target(store_targets, 1, month):.0f} L",
                f"₹{store_target(store_targets, 2, month):.0f} L",
                f"₹{store_target(store_targets, 3, month):.0f} L",
                f"{store_target(store_targets, 5, month):.0f} accounts",
            ],
        })
        st.dataframe(store_df, hide_index=True, use_container_width=True)

        st.markdown("#### RSO Targets — Value in ₹L (GHS = count)")
        rso_tgt_m = rso_targets[rso_targets["MONTH"]==int(month)][["EMPLOYEE NAME","PLAIN","HCG","PJWS","STUD","TOTAL","GHS"]].sort_values("TOTAL",ascending=False)
        if len(rso_tgt_m) > 0:
            rso_tgt_m.columns = ["RSO","Plain (L)","HCG (L)","PJWS (L)","Studded (L)","Total (L)","GHS (#)"]
            st.dataframe(rso_tgt_m, hide_index=True, use_container_width=True)
    
    with tab_inc:
        st.markdown("#### Settings")
        cc = st.columns(2)
        st.session_state.hvs_threshold = cc[0].number_input("HVS threshold (₹L)", value=float(st.session_state.get("hvs_threshold", 5.0)), step=0.5)
        st.session_state.pool_gate = cc[1].toggle("Pool gate (30% studded share required)", value=st.session_state.get("pool_gate", True))
        
        share = store_studded_share(sales, month)
        st.metric("Live Studded Share", f"{share:.1f}%", "✓ Gate open" if share>=30 else "✗ Below gate")
        
        st.markdown("#### Pool Sim")
        pool_used = sum(compute_incentive(sales, ghs, r, month, store_gate_open=share>=30)["total"] for r in sorted(sales["RSO_FINAL"].dropna().unique()))
        pc0, pc1, pc2 = st.columns(3)
        pc0.metric("Month payout", inr(pool_used))
        pc1.metric("Annual proj", inr(pool_used*12), f"{pool_used*12/ANNUAL_POOL*100:.0f}% of pool")
        pc2.metric("Pool ceiling", inr(ANNUAL_POOL), "✓ OK" if pool_used*12<=ANNUAL_POOL else "✗ OVER")
    
    with tab_data:
        st.write(f"Sales: **{len(sales):,}** rows | GHS: **{len(ghs):,}** rows | Months: **{sorted(sales['MONTH'].dropna().unique().tolist())}**")
        st.caption(f"Last refresh: {st.session_state.get('refresh_stamp','—')}")
        # Data health: RSO name alignment check
        st.markdown("#### 🩺 Data Health")
        sales_rsos = set(sales["RSO_FINAL"].dropna().unique())
        tgt_rsos = set(rso_targets["EMPLOYEE NAME"].dropna().unique())
        orphan_rsos = sales_rsos - tgt_rsos
        if orphan_rsos:
            st.warning(
                f"⚠️ **RSOs in sales but missing from targets** (showing 0% achievement): "
                f"{', '.join(sorted(orphan_rsos))}\n\n"
                "Fix: Add them to `targets.xlsx` OR add their name mapping to `RSO_NAME_MAP` in `app.py`."
            )
        else:
            st.success("✅ All RSOs in sales are matched in targets.")
        null_sale = (sales["WT"].fillna(0) > 0) & (sales["CMTOTAL"] == 0)
        st.metric("Sale rows with ₹0 CMTOTAL (after fix)", int(null_sale.sum()),
                  help="Should be 0 after the CMTOTAL→AMT backfill fix.")

    with tab_lb:
        st.markdown("#### RSO Leaderboard — " + str(int(month)))
        share = store_studded_share(sales, month)
        gate_open = share >= STUDDED_SHARE_GATE
        rows = []
        for r in sorted(sales["RSO_FINAL"].dropna().unique()):
            rsl = rso_month_slice(sales, r, month)
            rsl_pos = rsl[~rsl["IS_RETURN"]]
            val = rsl_pos["CMTOTAL"].clip(lower=0).sum()
            stud_val = rsl_pos.loc[rsl_pos["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
            sp = studded_pieces(rsl)
            opens_d = ghs_opens_in_month(ghs, r, month)
            inc = compute_incentive(sales, ghs, r, month, store_gate_open=gate_open)
            tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"]==r.upper()) &
                                  (rso_targets["MONTH"]==int(month))]
            tgt = float(tgt_row["TOTAL"].iloc[0]) if len(tgt_row) else 100.0
            pct = round(val / tgt * 100, 1) if tgt else 0
            rows.append(dict(RSO=r.title(), Value_L=round(val,1), Target_L=round(tgt,1),
                             Achievement=f"{pct}%", Studded_L=round(stud_val,1),
                             Stud_Pcs=sp, GHS_Net=opens_d["TOTAL"],
                             Incentive=inr(inc["total"])))
        lb = pd.DataFrame(rows).sort_values("Value_L", ascending=False).reset_index(drop=True)
        lb.index = lb.index + 1   # rank from 1
        # colour coding hint
        def ach_emoji(a):
            p = float(str(a).replace("%",""))
            return "🟢" if p >= 100 else ("🟡" if p >= 75 else "🔴")
        lb[""] = lb["Achievement"].apply(ach_emoji)
        lb = lb[["","RSO","Value_L","Target_L","Achievement","Studded_L","Stud_Pcs","GHS_Net","Incentive"]]
        lb.columns = ["","RSO","Value (L)","Target (L)","Achievement","Stud Val (L)","Stud Pcs","GHS Net","Incentive"]
        st.dataframe(lb, use_container_width=True)

        # summary callouts
        pace = pace_stats(month)
        ep = pace["elapsed_pct"]
        ahead = lb[lb["Achievement"].str.replace("%","").astype(float) >= ep]
        behind = lb[lb["Achievement"].str.replace("%","").astype(float) < ep * 0.7]
        ca, cb = st.columns(2)
        ca.metric("On/ahead of pace 🟢", f"{len(ahead)} RSOs")
        cb.metric("Significantly behind 🔴", f"{len(behind)} RSOs",
                  delta=f"need urgent attention" if len(behind) else None,
                  delta_color="inverse" if len(behind) else "off")

    with tab_exc:
        st.markdown("#### 🚨 Exception Report — things needing attention now")
        pace = pace_stats(month)
        ep = pace["elapsed_pct"]

        # Exception 1: below 50% of target with <40% of month left
        msl = sales[(sales["MONTH"]==month) & (~sales["IS_RETURN"])]
        exc_rows = []
        for r in sorted(sales["RSO_FINAL"].dropna().unique()):
            rsl = rso_month_slice(sales, r, month)[lambda d: ~d["IS_RETURN"]]
            val = rsl["CMTOTAL"].clip(lower=0).sum()
            tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"]==r.upper()) &
                                  (rso_targets["MONTH"]==int(month))]
            tgt = float(tgt_row["TOTAL"].iloc[0]) if len(tgt_row) else 100.0
            pct = val/tgt*100 if tgt else 0
            sp = studded_pieces(rsl)
            opens = ghs_opens_in_month(ghs, r, month)["TOTAL"]
            issues = []
            if pct < ep * 0.7: issues.append(f"Value only {pct:.0f}% of target")
            if sp < 5 and ep > 50: issues.append(f"Only {sp} studded pcs this month")
            if opens < 3 and ep > 50: issues.append(f"Only {opens} net GHS opens")
            if issues:
                exc_rows.append(dict(RSO=r.title(), Achievement=f"{pct:.0f}%",
                                     Issues=" · ".join(issues)))
        if exc_rows:
            st.dataframe(pd.DataFrame(exc_rows), hide_index=True, use_container_width=True)
        else:
            st.success("No critical exceptions this month ✅")

        # Exception 2: GHS accounts going inactive this month
        st.markdown("#### ⏳ GHS/RGA accounts about to go inactive")
        fl = follow_up_lists(sales, ghs, rso=None)
        mat = fl["maturing"]
        if len(mat):
            mat = mat.copy()
            mat["days_left"] = mat.apply(
                lambda r: (GHS_INACTIVE_DAYS if r["TYPE"]=="GHS" else RGA_INACTIVE_DAYS) - int(r["DAYS_OPEN"]), axis=1)
            show = mat[["CUSTOMERNAME","TYPE","days_left","RSO NAME"]].copy()
            show.columns = ["Customer","Type","Days Left","RSO"]
            st.dataframe(show.sort_values("Days Left").head(50),
                         hide_index=True, use_container_width=True)
            st.caption(f"{len(mat)} accounts total — sorted by urgency. Assign to RSOs immediately.")

    with tab_cmp:
        st.markdown("### ⚖️ RSO Comparison")
        all_rsos = sorted(sales["RSO_FINAL"].dropna().unique().tolist())
        months_avail = sorted(sales["MONTH"].dropna().unique().tolist())
        month_labels = {m: {202604:"Apr 26",202605:"May 26",202606:"Jun 26",
                            202607:"Jul 26",202608:"Aug 26",202609:"Sep 26",
                            202610:"Oct 26",202611:"Nov 26",202612:"Dec 26",
                            202701:"Jan 27",202702:"Feb 27",202703:"Mar 27"}.get(int(m),str(int(m)))
                        for m in months_avail}

        cmp_mode = st.radio("Compare mode", ["RSO vs RSO (same month)", "RSO vs Themselves (trend)"], horizontal=True)

        if cmp_mode == "RSO vs RSO (same month)":
            cmp_rsos = st.multiselect("Select RSOs to compare (2–6)", all_rsos,
                                      default=all_rsos[:3] if len(all_rsos) >= 3 else all_rsos)
            cmp_month = st.selectbox("Month", months_avail,
                                     index=len(months_avail)-1,
                                     format_func=lambda m: month_labels[m],
                                     key="cmp_month_vs")
            metrics_pick = st.multiselect("Metrics", [
                "Total Value (L)", "Studded Value (L)", "Studded Pieces",
                "Studded Share %", "HVS Pieces", "GHS Net Opens",
                "Avg Bill Value (L)", "Target Achievement %", "Incentive (₹)"
            ], default=["Total Value (L)", "Studded Pieces", "GHS Net Opens", "Target Achievement %"])

            if cmp_rsos and metrics_pick:
                rows = []
                for r in cmp_rsos:
                    rsl = rso_month_slice(sales, r, cmp_month)
                    rp = rsl[~rsl["IS_RETURN"]]
                    v = rp["CMTOTAL"].clip(lower=0).sum()
                    sv = rp.loc[rp["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
                    sp = studded_pieces(rsl)
                    hv = hvs_pieces(rsl)
                    op = ghs_opens_in_month(ghs, r, cmp_month)["TOTAL"]
                    bills = len(rp)
                    aev = v/bills if bills else 0
                    share = sv/v*100 if v else 0
                    inc = compute_incentive(sales, ghs, r, cmp_month)["total"]
                    tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"]==r.upper()) &
                                         (rso_targets["MONTH"]==int(cmp_month))]
                    tgt = float(tgt_row["TOTAL"].iloc[0]) if len(tgt_row) else 100.0
                    ach = v/tgt*100 if tgt else 0
                    row = {"RSO": r.title()}
                    if "Total Value (L)" in metrics_pick: row["Value (L)"] = round(v,1)
                    if "Studded Value (L)" in metrics_pick: row["Stud Val (L)"] = round(sv,1)
                    if "Studded Pieces" in metrics_pick: row["Stud Pcs"] = sp
                    if "Studded Share %" in metrics_pick: row["Stud Share"] = f"{share:.1f}%"
                    if "HVS Pieces" in metrics_pick: row["HVS"] = hv
                    if "GHS Net Opens" in metrics_pick: row["GHS Net"] = op
                    if "Avg Bill Value (L)" in metrics_pick: row["AEV (L)"] = round(aev,2)
                    if "Target Achievement %" in metrics_pick: row["Achievement"] = f"{ach:.0f}%"
                    if "Incentive (₹)" in metrics_pick: row["Incentive"] = inr(inc)
                    rows.append(row)

                cmp_df = pd.DataFrame(rows).set_index("RSO")
                st.dataframe(cmp_df, use_container_width=True)

                # bar chart for the first numeric metric
                num_cols = [c for c in cmp_df.columns
                            if cmp_df[c].dtype in (float, int) or
                            (hasattr(cmp_df[c],'str') and
                             cmp_df[c].astype(str).str.replace('.','',1).str.isdigit().all())]
                if num_cols:
                    chart_col = num_cols[0]
                    chart_df = pd.DataFrame({
                        "RSO": [r.title() for r in cmp_rsos],
                        chart_col: [float(str(cmp_df.loc[r.title(), chart_col]).replace("L","").strip())
                                    for r in cmp_rsos if r.title() in cmp_df.index]
                    })
                    fig = px.bar(chart_df, x="RSO", y=chart_col,
                                 color="RSO", color_discrete_sequence=[GOLD, RUBY, EMERALD, AMBER, "#A78BFA", "#34D399"])
                    fig.update_traces(marker_cornerradius=6, marker_line_width=0)
                    fig.update_layout(showlegend=False)
                    apply_chart_style(fig, height=300)
                    st.plotly_chart(fig, use_container_width=True)

        else:  # RSO vs Themselves (trend)
            self_rsos = st.multiselect("Select RSOs (1–4)", all_rsos,
                                       default=all_rsos[:2] if len(all_rsos) >= 2 else all_rsos,
                                       key="self_cmp_rsos")
            self_metric = st.selectbox("Metric to trend", [
                "Total Value (L)", "Studded Pieces", "Studded Share %",
                "GHS Net Opens", "HVS Pieces", "Target Achievement %", "Incentive (₹)"
            ])

            if self_rsos:
                metric_map = {
                    "Total Value (L)": "value", "Studded Pieces": "studded_pcs",
                    "Studded Share %": "studded_share", "GHS Net Opens": "ghs",
                    "HVS Pieces": "hvs", "Target Achievement %": "achievement",
                    "Incentive (₹)": "incentive"
                }
                mk = metric_map[self_metric]
                trend_rows = []
                for m in months_avail:
                    for r in self_rsos:
                        rsl = rso_month_slice(sales, r, m)
                        rp = rsl[~rsl["IS_RETURN"]]
                        v = rp["CMTOTAL"].clip(lower=0).sum()
                        sv = rp.loc[rp["IS_STUDDED"], "CMTOTAL"].clip(lower=0).sum()
                        sp = studded_pieces(rsl)
                        op = ghs_opens_in_month(ghs, r, m)["TOTAL"]
                        if mk == "value": val = v
                        elif mk == "studded_pcs": val = sp
                        elif mk == "studded_share": val = (sv/v*100) if v else 0
                        elif mk == "ghs": val = op
                        elif mk == "hvs": val = hvs_pieces(rsl)
                        elif mk == "achievement":
                            tgt_row = rso_targets[(rso_targets["EMPLOYEE NAME"]==r.upper()) &
                                                  (rso_targets["MONTH"]==int(m))]
                            tgt = float(tgt_row["TOTAL"].iloc[0]) if len(tgt_row) else 100.0
                            val = v/tgt*100 if tgt else 0
                        elif mk == "incentive":
                            val = compute_incentive(sales, ghs, r, m)["total"]
                        else: val = v
                        trend_rows.append({"Month": month_labels[m], "RSO": r.title(), "Value": val})

                tdf = pd.DataFrame(trend_rows)
                fig = px.line(tdf, x="Month", y="Value", color="RSO", markers=True,
                              color_discrete_sequence=[RUBY, GOLD_DEEP, EMERALD, AMBER],
                              labels={"Value": self_metric})
                fig.update_traces(line_width=3, marker_size=9)
                apply_chart_style(fig, height=360)
                st.plotly_chart(fig, use_container_width=True)

                # table below chart
                pivot = tdf.pivot(index="RSO", columns="Month", values="Value").round(1)
                st.dataframe(pivot, use_container_width=True)


# ---------------------------------------------------------------------------
# 15. PAGE — DATA MANAGER (file upload for admins / store managers)
# ---------------------------------------------------------------------------
def page_data_manager(role):
    """Allow admins and store managers to upload fresh data files via browser."""
    st.markdown("## 📤 Data Manager")
    st.caption("Upload fresh Excel files here. Dashboard refreshes automatically after upload.")

    if role not in ("Admin", "Store Manager", "Floor Manager", "MD"):
        st.warning("Only managers can upload data files.")
        return

    import shutil

    FILE_CONFIG = {
        "Sales_Data.xlsx": {
            "label": "📊 Sales Data (Current Month)",
            "description": "3-month sales file from POSReports.",
            "required_cols": ["MONTH", "FLAG", "RSO CHANGE", "CMTOTAL", "WT"],
            "key": "upload_sales",
        },
        "ghs_OPENING.xlsx": {
            "label": "🏦 GHS Account Book",
            "description": "GHS/RGA account opening and refund records.",
            "required_cols": ["RSO NAME", "TYPE", "OPENING", "OP-MONTH"],
            "key": "upload_ghs",
        },
        "targets.xlsx": {
            "label": "🎯 RSO Targets",
            "description": "Monthly RSO and store targets. Sheets: 'rso wise targets' and 'store targets'.",
            "required_cols": ["EMPLOYEE NAME", "MONTH", "TOTAL"],
            "key": "upload_targets",
        },
        "stock.xlsx": {
            "label": "🏪 Stock Inventory",
            "description": "Full current inventory from Jewbridge.",
            "required_cols": ["Flag", "Category", "ItemCode", "Wt", "Amt"],
            "key": "upload_stock",
        },
        "sludge.xlsx": {
            "label": "⚠️ Aged Stock (Sludge)",
            "description": "Aged inventory incentive list.",
            "required_cols": ["ItemCode", "Cur-Final"],
            "key": "upload_sludge",
        },
        "pendingCN.xlsx": {
            "label": "📋 Pending Credit Notes",
            "description": "Open credit notes from POSReports. Columns: CN TYPE, AMOUNT, CUSTOMER NAME, MOBILE, DAYS, CUR STATUS, TRANS-UID, RSO NAME.",
            "required_cols": ["CN TYPE", "AMOUNT", "DAYS", "CUR STATUS", "RSO NAME"],
            "key": "upload_cn",
        },
    }

    upload_results = []

    for filename, cfg in FILE_CONFIG.items():
        with st.expander(f"{cfg['label']} — `{filename}`", expanded=False):
            st.caption(cfg["description"])
            if os.path.exists(filename):
                mtime = dt.datetime.fromtimestamp(os.path.getmtime(filename))
                size_kb = os.path.getsize(filename) // 1024
                st.success(f"✅ {filename} · {size_kb} KB · Updated: {mtime.strftime('%d %b %Y, %H:%M')}")
            else:
                st.error(f"❌ File missing: {filename}")

            uploaded = st.file_uploader(
                f"Upload new {filename}",
                type=["xlsx", "xls"],
                key=cfg["key"],
                help=f"Required columns: {', '.join(cfg['required_cols'])}",
            )

            if uploaded is not None:
                try:
                    test_df = pd.read_excel(uploaded, nrows=5)
                    test_df.columns = [str(c).strip() for c in test_df.columns]
                    missing_cols = [c for c in cfg["required_cols"] if c not in test_df.columns]
                    if missing_cols:
                        st.error(f"❌ Upload failed. Missing columns: {', '.join(missing_cols)}")
                        st.caption(f"Found: {', '.join(test_df.columns.tolist())}")
                    else:
                        uploaded.seek(0)
                        with open(filename, "wb") as f:
                            f.write(uploaded.read())
                        backup_dir = "backups"
                        os.makedirs(backup_dir, exist_ok=True)
                        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                        shutil.copy2(filename, f"{backup_dir}/{filename.replace('.xlsx','')}_{stamp}.xlsx")
                        upload_results.append(filename)
                        st.success(f"✅ {filename} uploaded & backed up.")
                except Exception as e:
                    st.error(f"❌ Could not read file: {e}")

    if upload_results:
        st.divider()
        st.success(f"✅ {len(upload_results)} file(s) uploaded: {', '.join(upload_results)}")
        if st.button("🔄 Refresh Dashboard with New Data", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.session_state.refresh_token = dt.datetime.now().timestamp()
            st.session_state.refresh_stamp = dt.datetime.now().strftime("%d %b %Y, %H:%M:%S")
            st.rerun()

    st.divider()
    st.markdown("#### 🗂️ Recent Backups")
    backup_dir = "backups"
    if os.path.exists(backup_dir):
        backups = sorted(os.listdir(backup_dir), reverse=True)[:10]
        if backups:
            for b in backups:
                btime = dt.datetime.fromtimestamp(os.path.getmtime(f"{backup_dir}/{b}"))
                st.caption(f"📄 {b} · {btime.strftime('%d %b %Y, %H:%M')}")
        else:
            st.caption("No backups yet.")
    else:
        st.caption("No backups folder found.")


def main():
    # data files present?
    if not (os.path.exists(SALES_FILE) and os.path.exists(GHS_FILE)):
        st.markdown("## 💎 Tanishq MN Dashboard")
        st.info("👋 Welcome! Data files aren't loaded yet.")
        st.markdown("**If you're the admin:** Log in below and upload your Excel files from the Data Manager.")
        st.markdown("**If you're an RSO:** Ask Swaroop to upload the latest data files.")
        if not st.session_state.get("auth"):
            do_login(pd.DataFrame())
        else:
            page_data_manager(st.session_state.role)
        st.stop()

    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = dt.datetime.now().timestamp()
        st.session_state.refresh_stamp = dt.datetime.now().strftime("%d %b %Y, %H:%M:%S")

    sales = load_sales(st.session_state.refresh_token)
    ghs = load_ghs(st.session_state.refresh_token)
    rso_targets, store_targets = load_targets(st.session_state.refresh_token)
    sludge = load_sludge(st.session_state.refresh_token)
    cn = load_cn(st.session_state.refresh_token)

    # auth gate
    if not st.session_state.get("auth"):
        do_login(sales)
        st.stop()

    role = st.session_state.role
    name = st.session_state.name
    my_rso = st.session_state.get("rso")          # set only for RSO logins

    months = sorted(sales["MONTH"].dropna().unique().tolist())

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.markdown(f"### 💎 Tanishq <span class='gold'>MN</span>", unsafe_allow_html=True)
        st.markdown(f"**{name}**  \n<span class='small-muted'>{role}</span>", unsafe_allow_html=True)
        st.divider()
        month = st.selectbox("📅 Month", months, index=len(months) - 1,
                             format_func=lambda m: f"{str(m)[4:]}/{str(m)[:4]}")

        # manager staff picker
        is_mgr = role in ("Admin", "Store Manager", "Floor Manager", "MD")
        view_rso = my_rso
        if is_mgr:
            rsos = ["(store overview)"] + sorted(sales["RSO_FINAL"].dropna().unique().tolist())
            pick = st.selectbox("👤 Focus RSO", rsos)
            view_rso = None if pick == "(store overview)" else pick

        pages = ["Performance", "Incentive", "GHS / RGA", "Customers",
                 "Stock", "Sludge", "Tasks", "Analytics", "Credit Notes"]
        if is_mgr:
            pages += ["Admin", "Data Manager"]
        page = st.radio("Navigate", pages)

        st.divider()
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state.refresh_token = dt.datetime.now().timestamp()
            st.session_state.refresh_stamp = dt.datetime.now().strftime("%d %b %Y, %H:%M:%S")
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Last refresh: {st.session_state.get('refresh_stamp','—')}")

        # AI search lives in the sidebar so it's always reachable
        st.divider()
        st.markdown("#### 🤖 Ask the data")
        q = st.text_input("Natural-language query", key="ai_q",
                          placeholder="top studded sellers")
        if q:
            st.markdown(ai_search(sales, ghs, rso_targets, month, q))

        st.divider()
        if st.button("Sign out", use_container_width=True):
            for k in ["auth", "role", "name", "rso"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ---------- FROZEN TOP BAR ----------
    frozen_bar(sales, ghs, rso_targets, store_targets, month, focus_rso=view_rso)

    # ---------- ROUTE ----------
    if page == "Performance":
        page_performance(sales, ghs, rso_targets, month, view_rso, role)
    elif page == "Incentive":
        page_incentive(sales, ghs, rso_targets, month, view_rso, role)
    elif page == "GHS / RGA":
        page_ghs(sales, ghs, month, view_rso, role)
    elif page == "Customers":
        page_customers(sales, ghs, cn, month, view_rso, role)
    elif page == "Stock":
        page_stock_intel(view_rso=view_rso)
    elif page == "Sludge":
        page_sludge(sludge, month)
    elif page == "Analytics":
        page_analytics()
    elif page == "Tasks":
        page_tickets(sales, ghs, month, view_rso, role)
    elif page == "Credit Notes":
        page_cn(cn, view_rso, role)
    elif page == "Admin":
        page_admin(sales, ghs, rso_targets, store_targets, month)
    elif page == "Data Manager":
        page_data_manager(role)


if __name__ == "__main__":
    main()
