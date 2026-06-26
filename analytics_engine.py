"""
analytics_engine.py  —  Tanishq MN 5-Year Intelligence Engine
==============================================================
Processes historical sales + current stock for deep insights.
Import in app.py: from analytics_engine import *
"""
import pandas as pd
import numpy as np
import datetime as dt

HIST_FILE  = "sales.xlsx"
STOCK_FILE = "stock.xlsx"

ACTIVE_RSOS = [
    "ABHISHEK SAINI","AMOL MITTAL","ANITA VERMA","ARCHANA SINGH",
    "INDRALAL PATEL","KALYANI SONI","MANDA BONDE","NANDNI TIWARI",
    "NIKHAR AGARWAL","RAKESH JAIN","RANJANA GUBRELAY","RITESH BHATNAGAR",
    "RUCHI AGARWAL","SANDHYA SONI","SUNITA UDAY",
]

MONTH_NAMES = {
    1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
    7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec",
}

FESTIVAL_MONTHS = {
    10: "Dhanteras / Navratri 🪔",
    11: "Post-Diwali / Wedding Season 💒",
    4:  "Akshaya Tritiya ✨",
    8:  "Wedding / Raksha Bandhan 🎗️",
}

# ── LOADERS ──────────────────────────────────────────────────────────────────

def load_hist(path=HIST_FILE) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name="Sales5Yrs")
    except Exception:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    df["DATE"]      = pd.to_datetime(df["DATE"], errors="coerce")
    df["CMTOTAL"]   = pd.to_numeric(df["CMTOTAL"], errors="coerce")
    df["AMT"]       = pd.to_numeric(df.get("AMT", pd.Series(dtype=float)), errors="coerce")
    # Multi-line bill fix: CMTOTAL only on first line; subsequent lines use AMT
    null_mask = df["CMTOTAL"].isna() & (df["WT"].fillna(0) > 0)
    df.loc[null_mask, "CMTOTAL"] = df.loc[null_mask, "AMT"]
    df["CMTOTAL"]   = df["CMTOTAL"].fillna(0)
    df["IS_RETURN"] = df["WT"].fillna(0) < 0
    df["IS_STUDDED"]= df["FLAG"].astype(str).str.strip().str.upper() == "S"
    df["RSO_H"]     = df["RSO CHANGE"].astype(str).str.strip().str.upper()
    df["YEAR"]      = df["DATE"].dt.year
    df["MONTH_NUM"] = df["DATE"].dt.month
    df["THEME"]     = df.get("THEME", pd.Series("", index=df.index)).fillna("").astype(str)
    df["MOBILE"]    = pd.to_numeric(df["MOBILE"], errors="coerce")
    return df[~df["IS_RETURN"]].copy()


def load_stock(path=STOCK_FILE) -> pd.DataFrame:
    try:
        df = pd.read_excel(path)
    except Exception:
        return pd.DataFrame()
    df.columns = [c.strip() for c in df.columns]
    df["Flag"]       = df["Flag"].astype(str).str.strip().str.upper()
    df["IS_STUDDED"] = df["Flag"] == "S"
    df["AMT"]        = pd.to_numeric(df.get("Amt", 0), errors="coerce").fillna(0)
    df["AMT_L"]      = df["AMT"] / 1e5
    df["WT"]         = pd.to_numeric(df.get("Wt",  0), errors="coerce").fillna(0)
    df["THEME"]      = df["ItemCode"].apply(
        lambda x: str(x)[2:9] if len(str(x)) >= 9 else str(x))
    df["IMG"]        = ("https://jewbridge.titanjew.in/CatalogImages/api/"
                        "ImageFetch/?Type=ProductImages&ImageName="
                        + df["THEME"] + ".jpg")
    return df


# ── ANALYTICS ────────────────────────────────────────────────────────────────

def yoy_summary(hist: pd.DataFrame) -> pd.DataFrame:
    """Year-over-year value + studded share per year."""
    if hist.empty:
        return pd.DataFrame()
    g = hist.groupby("YEAR").agg(
        Total_L=("CMTOTAL","sum"),
        Studded_L=("IS_STUDDED", lambda x: hist.loc[x.index, "CMTOTAL"][x].sum()),
    ).reset_index()
    g["Studded_Share_Pct"] = (g["Studded_L"] / g["Total_L"] * 100).round(1)
    g["YoY_Growth_Pct"] = g["Total_L"].pct_change() * 100
    return g


def monthly_seasonality(hist: pd.DataFrame) -> pd.DataFrame:
    """Average monthly revenue across all years (excl partial 2026 if needed)."""
    if hist.empty:
        return pd.DataFrame()
    full_years = hist[hist["YEAR"] < 2026]
    g = full_years.groupby("MONTH_NUM")["CMTOTAL"].mean().reset_index()
    g.columns = ["MONTH_NUM", "Avg_L"]
    g["Month"] = g["MONTH_NUM"].map(MONTH_NAMES)
    g["Is_Festival"] = g["MONTH_NUM"].isin(FESTIVAL_MONTHS)
    g["Festival_Label"] = g["MONTH_NUM"].map(FESTIVAL_MONTHS).fillna("")
    return g.sort_values("MONTH_NUM")


def customer_rfm(hist: pd.DataFrame) -> pd.DataFrame:
    """RFM scoring for all customers."""
    if hist.empty:
        return pd.DataFrame()
    today = pd.Timestamp(dt.date.today())
    rfm = hist.groupby("CUSTOMERNAME").agg(
        last_date  =("DATE",    "max"),
        frequency  =("DATE",    "count"),
        monetary   =("CMTOTAL", "sum"),
        has_studded=("IS_STUDDED", "any"),
        fav_cat    =("CATEGORY", lambda x: x.value_counts().index[0]),
        mobile     =("MOBILE",  "last"),
        rso        =("RSO_H",   "last"),
    ).reset_index()
    rfm["recency_days"] = (today - rfm["last_date"]).dt.days
    rfm["segment"] = pd.cut(
        rfm["recency_days"],
        bins=[0, 60, 180, 365, 99999],
        labels=["🔥 Active","⚡ Warm","⏰ At Risk","💤 Lost"],
    )
    # Price band preference
    avg_val = hist.groupby("CUSTOMERNAME")["CMTOTAL"].mean()
    rfm["avg_ticket_L"] = rfm["CUSTOMERNAME"].map(avg_val)
    return rfm.sort_values("monetary", ascending=False)


def rso_history(hist: pd.DataFrame) -> pd.DataFrame:
    """Per-RSO yearly performance for active RSOs."""
    if hist.empty:
        return pd.DataFrame()
    active = hist[hist["RSO_H"].isin(ACTIVE_RSOS)]
    g = active.groupby(["RSO_H","YEAR"]).agg(
        Value_L=("CMTOTAL","sum"),
        Stud_L =("IS_STUDDED", lambda x: active.loc[x.index,"CMTOTAL"][x].sum()),
    ).reset_index()
    g["Stud_Pct"] = (g["Stud_L"] / g["Value_L"] * 100).round(1)
    return g


# ── STOCK INTELLIGENCE ───────────────────────────────────────────────────────

def stock_summary(stock: pd.DataFrame) -> dict:
    if stock.empty:
        return {}
    return {
        "total_items": len(stock),
        "total_value_L": stock["AMT_L"].sum(),
        "studded_value_L": stock.loc[stock["IS_STUDDED"],"AMT_L"].sum(),
        "studded_items": stock["IS_STUDDED"].sum(),
        "plain_value_L": stock.loc[~stock["IS_STUDDED"],"AMT_L"].sum(),
    }


STUDDED_CATS = {"Gold Studded", "Studded - Solitaire", "Studded - Color Stones",
                "Gold intensive studded", "High Value Studded", "MIA Studded",
                "Ultra-Low diamond", "Glass Kundan", "Plain Jewellery with Stones"}

def stock_push_recommendations(stock: pd.DataFrame, rfm: pd.DataFrame,
                                rso_filter: str = None,
                                top_n: int = 40) -> pd.DataFrame:
    """
    For each stock piece, find the best-fit customer from the RSO's book.
    Scoring: category_match(0/1) + price_proximity(0-1) + urgency(0-1 from recency)
    Studded and plain pools are ranked independently so studded is never crowded out.
    """
    if stock.empty or rfm.empty:
        return pd.DataFrame()

    rfm_active = rfm.copy()
    if rso_filter:
        rfm_active = rfm_active[rfm_active["rso"] == rso_filter.upper()]
    rfm_active = rfm_active[rfm_active["recency_days"].between(30, 730)]
    if rfm_active.empty:
        return pd.DataFrame()

    studded_pool = rfm_active[rfm_active["has_studded"] == True].copy()
    plain_pool   = rfm_active[rfm_active["has_studded"] == False].copy()

    def _match_items(subset: pd.DataFrame) -> list:
        rows = []
        for _, item in subset.iterrows():
            cat    = item.get("Category", "")
            amt_l  = item["AMT_L"]
            is_stud = item["IS_STUDDED"]

            pool = studded_pool if is_stud else plain_pool
            if pool.empty:
                pool = rfm_active

            cat_match = pool[pool["fav_cat"] == cat].copy()
            if cat_match.empty:
                cat_match = pool.copy()
            if cat_match.empty:
                continue

            cat_match["price_score"] = 1 / (
                1 + abs(cat_match["avg_ticket_L"] - amt_l) / max(amt_l, 0.1))
            cat_match["urgency"] = cat_match["recency_days"].apply(
                lambda d: 1.0 if 60 <= d <= 200 else (0.6 if d < 60 else 0.3))
            cat_match["score"] = cat_match["price_score"] * 0.6 + cat_match["urgency"] * 0.4

            best = cat_match.nlargest(1, "score").iloc[0]
            rows.append({
                "ItemCode":           item.get("ItemCode", ""),
                "Category":           cat,
                "Product":            item.get("Product", ""),
                "IS_STUDDED":         is_stud,
                "Value (Rs L)":       round(amt_l, 2),
                "Wt (g)":             round(item["WT"], 2),
                "THEME":              item.get("THEME", ""),
                "IMG":                item.get("IMG", ""),
                "Best Customer":      best["CUSTOMERNAME"],
                "Customer Mobile":    str(int(best["mobile"])) if pd.notna(best["mobile"]) else "—",
                "Last Visit (days)":  int(best["recency_days"]),
                "Segment":            str(best["segment"]),
                "RSO":                best["rso"].title(),
                "Match Score":        round(best["score"], 2),
            })
        return rows

    stud_rows  = _match_items(stock[stock["IS_STUDDED"]])
    plain_rows = _match_items(stock[~stock["IS_STUDDED"]])

    stud_df  = (pd.DataFrame(stud_rows).sort_values("Match Score", ascending=False).head(top_n)
                if stud_rows else pd.DataFrame())
    plain_df = (pd.DataFrame(plain_rows).sort_values("Match Score", ascending=False).head(top_n)
                if plain_rows else pd.DataFrame())

    return pd.concat([stud_df, plain_df], ignore_index=True)


def october_forecast(hist: pd.DataFrame) -> dict:
    """Forecast October demand based on 5-year history."""
    if hist.empty:
        return {}
    oct_data = hist[hist["MONTH_NUM"] == 10]
    yoy = oct_data.groupby("YEAR")["CMTOTAL"].sum()
    avg = yoy.mean()
    growth = yoy.pct_change().mean()
    forecast_2026 = avg * (1 + growth)
    oct_stud = oct_data.groupby("YEAR").apply(
        lambda x: x.loc[x["IS_STUDDED"],"CMTOTAL"].sum() / x["CMTOTAL"].sum() * 100
    ).mean()
    return {
        "avg_oct_value_L": round(avg, 0),
        "forecast_2026_L": round(forecast_2026, 0),
        "avg_yoy_growth_pct": round(growth * 100, 1),
        "avg_stud_share_oct": round(oct_stud, 1),
        "days_to_oct": (dt.date(2026, 10, 1) - dt.date.today()).days,
    }


def studded_decline_alert(hist: pd.DataFrame) -> dict:
    """Surface the declining studded share trend."""
    if hist.empty:
        return {}
    yoy = yoy_summary(hist)
    if yoy.empty:
        return {}
    peak = yoy["Studded_Share_Pct"].max()
    current = yoy.sort_values("YEAR")["Studded_Share_Pct"].iloc[-1]
    peak_yr = yoy.loc[yoy["Studded_Share_Pct"].idxmax(), "YEAR"]
    return {
        "peak_pct": peak,
        "peak_year": peak_yr,
        "current_pct": current,
        "decline_pts": round(peak - current, 1),
        "target_pct": 35,
        "gap_pts": round(35 - current, 1),
    }
