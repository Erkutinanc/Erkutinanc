import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time
from plotly.subplots import make_subplots

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite Pro", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700 !important; }
    div[data-testid="stMetric"] { 
        padding: 5px 10px !important; 
        background: #1a1c24 !important;
        border: 1px solid #2d2f39 !important;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------
# BIST SEKTÖRLER VE LİSTE
# ------------------------------------
BIST_SEKTORLER = {
    "Bankacılık": ["AKBNK.IS","GARAN.IS","HALKB.IS","ISCTR.IS","VAKBN.IS","YKBNK.IS"],
    "Havacılık": ["THYAO.IS","PGSUS.IS","TAVHL.IS"],
    "Petrokimya": ["PETKM.IS","TUPRS.IS"],
    "Enerji": ["AKSEN.IS","ENJSA.IS","SASA.IS","ASTOR.IS"],
    "Sanayi": ["EREGL.IS","KCHOL.IS","SAHOL.IS","SISE.IS"],
    "Perakende": ["BIMAS.IS","MGROS.IS","SOKM.IS"]
}

# ------------------------------------
# VERİ ÇEKME VE USD DÖNÜŞÜMÜ
# ------------------------------------
def fetch_data(ticker, is_usd=False, usd_rate=1.0):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df is None or df.empty or len(df) < 50: 
            return None
        df.dropna(inplace=True)
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col] / usd_rate
        return df
    except:
        return None

# ------------------------------------
# TEKNİK ANALİZ MOTORU + FIBONACCI PROJEKSİYONU
# ------------------------------------
def analyze_stock(df):
    try:
        close = df["Close"]
        high_max = df["High"].max()
        low_min = df["Low"].min()
        fiyat = float(close.iloc[-1])
        
        # RSI Hesaplama
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_val = float((100 - (100 / (1 + (gain / (loss + 1e-6))))).iloc[-1])
        
        # Fibonacci Hedefleri (Trend Uzatma 1.618)
        diff = high_max - low_min
        hedef_fibo = high_max + (diff * 0.618) if fiyat > low_min + (diff * 0.5) else high_max
        
        # Zaman ve Olasılık Tahmini
        # Volatilite üzerinden hedefe uzaklık analizi
        daily_ret = close.pct_change().std() 
        dist_to_target = abs(hedef_fibo - fiyat) / fiyat
        est_days = int(dist_to_target / (daily_ret + 1e-6))
        
        # Olasılık Skoru (RSI ve EMA uyumuna göre)
        ema13 = float(close.ewm(span=13).mean().iloc[-1])
        prob_score = 0
        if 45 < rsi_val < 70: prob_score += 40
        if fiyat > ema13: prob_score += 40
        if rsi_val > 70: prob_score -= 20 # Aşırı alım risk düşürür
        
        # Bollinger Sıkışma
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        width = float(((sma20 + 2*std20) - (sma20 - 2*std20)) / sma20).iloc[-1]
        squeeze = "🎯 SIKIŞMA" if width < 0.12 else "💎 NORMAL"
        
        karar = "🚀 GÜÇLÜ AL" if (fiyat > ema13 and prob_score >= 60) else "🔄 İZLE"
        
        return {
            "rsi": round(rsi_val, 2),
            "squeeze": squeeze,
            "karar": karar,
            "hedef": round(hedef_fibo, 2),
            "vade": f"{max(5, est_days)}-{est_days+10} Gün",
            "olasılık": f"%{min(95, 40 + prob_score)}"
        }
    except:
        return None

# ---------------------------------------------------
# STREAMLIT ARAYÜZÜ
# ---------------------------------------------------
st.sidebar.title("⚙️ Ayarlar")
currency = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = True if currency == "USD $" else False

usd_rate = 1.0
if is_usd:
    try:
        usd_data = yf.download("USDTRY=X", period="1d", progress=False)
        usd_rate = float(usd_data['Close'].iloc[-1])
    except: usd_rate = 34.50

st.title("📊 BIST Shadow Elite: Hedef Tahmin Terminali")

tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sector_name = list(BIST_SEKTORLER.keys())[i]
        results = []
        if st.button(f"{sector_name} Sektörünü Analiz Et", key=f"btn_{i}"):
            with st.spinner(f"Fibonacci ve Zaman Projeksiyonu hesaplanıyor..."):
                for ticker in BIST_SEKTORLER[sector_name]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    analysis = analyze_stock(df) if df is not None else None
                    
                    if analysis:
                        try:
                            info = yf.Ticker(ticker).info
                            pddd = info.get("priceToBook", 0)
                        except: pddd = 0
                        
                        results.append({
                            "Hisse": ticker.replace(".IS", ""),
                            "Fiyat": round(float(df["Close"].iloc[-1]), 2),
                            "Hedef (Fibo)": analysis["hedef"],
                            "Tahmini Vade": analysis["vade"],
                            "Olasılık": analysis["olasılık"],
                            "Sinyal": analysis["karar"],
                            "Durum": analysis["squeeze"],
                            "RSI": analysis["rsi"],
                            "PD/DD": round(pddd, 2)
                        })
                        time.sleep(0.1) 

            if results:
                res_df = pd.DataFrame(results)
                st.dataframe(res_df.sort_values("Olasılık", ascending=False), use_container_width=True, hide_index=True)
            else:
                st.warning("Veri çekilemedi, lütfen tekrar deneyin.")
