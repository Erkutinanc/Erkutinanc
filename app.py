import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite Pro", layout="wide", page_icon="💎")

# --- 2. GÜÇLENDİRİLMİŞ VERİ ÇEKME MOTORU ---
def fetch_data_robust(ticker, is_usd=False, usd_rate=1.0):
    try:
        # Ticker objesi üzerinden çekmek, toplu indirmeden (download) daha stabildir
        t = yf.Ticker(ticker)
        df = t.history(period="1y", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
            
        df.dropna(inplace=True)
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col] / usd_rate
        return df
    except Exception as e:
        return None

# --- 3. ANALİZ MOTORU ---
def analyze_stock(df):
    try:
        close = df["Close"]
        high_max = float(df["High"].max())
        low_min = float(df["Low"].min())
        fiyat = float(close.iloc[-1])
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_val = float((100 - (100 / (1 + (gain / (loss + 1e-6))))).iloc[-1])
        
        # Fibonacci (1.618 Hedefleme)
        diff = high_max - low_min
        hedef_fibo = high_max + (diff * 0.618) if fiyat > low_min + (diff * 0.5) else high_max
        
        # Zaman ve Olasılık Tahmini
        volatilite = close.pct_change().std()
        dist_pct = abs(hedef_fibo - fiyat) / fiyat
        est_days = int(dist_pct / (volatilite + 1e-6))
        
        ema13 = float(close.ewm(span=13).mean().iloc[-1])
        prob = 40
        if 45 < rsi_val < 70: prob += 30
        if fiyat > ema13: prob += 20
        
        # Sıkışma
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        width = float(((sma20 + 2*std20) - (sma20 - 2*std20)) / sma20).iloc[-1]
        
        return {
            "rsi": round(rsi_val, 2),
            "squeeze": "🎯 SIKIŞMA" if width < 0.12 else "💎 NORMAL",
            "karar": "🚀 GÜÇLÜ AL" if (fiyat > ema13 and prob >= 70) else "🔄 İZLE",
            "hedef": round(hedef_fibo, 2),
            "vade": f"{max(5, est_days)}-{est_days+12} G",
            "olasılık": f"%{min(95, prob)}"
        }
    except: return None

# --- 4. ARAYÜZ ---
st.sidebar.title("💎 Shadow Elite Pro")
currency = st.sidebar.radio("Birim", ["TL ₺", "USD $"])
is_usd = True if currency == "USD $" else False

# Kur Verisi
@st.cache_data(ttl=3600)
def get_rate():
    try: return yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
    except: return 34.50

usd_rate = get_rate() if is_usd else 1.0

BIST_SEKTORLER = {
    "Bankacılık": ["AKBNK.IS","GARAN.IS","ISCTR.IS","YKBNK.IS","HALKB.IS"],
    "Enerji": ["AKSEN.IS","ENJSA.IS","SASA.IS","ASTOR.IS","KONTR.IS"],
    "Havacılık": ["THYAO.IS","PGSUS.IS","TAVHL.IS"],
    "Sanayi": ["EREGL.IS","KCHOL.IS","SAHOL.IS","SISE.IS","FROTO.IS"],
    "Perakende": ["BIMAS.IS","MGROS.IS","SOKM.IS"]
}

st.title("📊 BIST Hedef & Zaman Terminali")
tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sec = list(BIST_SEKTORLER.keys())[i]
        if st.button(f"{sec} Analizini Başlat", key=f"btn_{sec}"):
            results = []
            with st.spinner("Veri hatları temizleniyor..."):
                for ticker in BIST_SEKTORLER[sec]:
                    df = fetch_data_robust(ticker, is_usd, usd_rate)
                    if df is not None:
                        a = analyze_stock(df)
                        if a:
                            results.append({
                                "Hisse": ticker.replace(".IS", ""),
                                "Fiyat": round(df["Close"].iloc[-1], 2),
                                "Fibo Hedef": a["hedef"],
                                "Tahmini Vade": a["vade"],
                                "Olasılık": a["olasılık"],
                                "Durum": a["squeeze"],
                                "RSI": a["rsi"],
                                "Sinyal": a["karar"]
                            })
                    # Her hisse arasında 0.3 saniye mola (Burası kritik!)
                    time.sleep(0.3)
                
            if results:
                st.dataframe(pd.DataFrame(results).sort_values("Olasılık", ascending=False), use_container_width=True, hide_index=True)
            else:
                st.error("Yahoo Finance şu an isteği reddediyor. Lütfen 1 dakika sonra tekrar butona bas.")
