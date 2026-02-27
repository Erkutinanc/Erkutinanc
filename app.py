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
        # Veriyi çekerken hata riskini azaltmak için 1 yıllık güncellik
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df is None or df.empty or len(df) < 25: 
            return None
        df.dropna(inplace=True)
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col] / usd_rate
        return df
    except:
        return None

# ------------------------------------
# TEKNİK ANALİZ MOTORU (Hata Düzeltilmiş Sürüm)
# ------------------------------------
def analyze_stock(df):
    try:
        close = df["Close"]
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_series = 100 - (100 / (1 + (gain / (loss + 1e-6))))
        rsi_val = float(rsi_series.iloc[-1])
        
        # Bollinger & Sıkışma (Hata burada düzeltildi)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + (2 * std20)
        lower = sma20 - (2 * std20)
        
        # Width değerini skaler bir sayıya zorluyoruz (.item() veya float())
        width_series = (upper - lower) / sma20
        last_width = float(width_series.iloc[-1])
        
        # Sıkışma kontrolü
        squeeze = "🎯 SIKIŞMA" if last_width < 0.12 else "💎 NORMAL"

        # EMA 13 (Selçuk Gönençer)
        ema13_series = close.ewm(span=13).mean()
        ema13_val = float(ema13_series.iloc[-1])
        fiyat = float(close.iloc[-1])
        
        # Karar Mekanizması
        puan = 0
        if fiyat > ema13_val: puan += 50
        if 40 < rsi_val < 70: puan += 30
        if last_width < 0.12: puan += 20
        
        karar = "🚀 GÜÇLÜ AL" if puan >= 80 else "🔄 İZLE" if puan >= 50 else "🛑 BEKLE"
        return round(rsi_val, 2), squeeze, karar, puan
    except:
        return 0.0, "⚠️ VERİ HATASI", "BELİRSİZ", 0

# ---------------------------------------------------
# STREAMLIT ARAYÜZÜ
# ---------------------------------------------------
st.sidebar.title("⚙️ Ayarlar")
currency = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = True if currency == "USD $" else False

# USD Kuru
usd_rate = 1.0
if is_usd:
    try:
        usd_data = yf.download("USDTRY=X", period="1d", progress=False)
        usd_rate = float(usd_data['Close'].iloc[-1])
    except:
        usd_rate = 34.50

st.title("📊 BIST Shadow Elite Pro")

tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sector_name = list(BIST_SEKTORLER.keys())[i]
        results = []
        if st.button(f"{sector_name} Sektörünü Tara", key=f"btn_{i}"):
            with st.spinner(f"{sector_name} taranıyor..."):
                for ticker in BIST_SEKTORLER[sector_name]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    if df is not None:
                        rsi, squeeze, karar, puan = analyze_stock(df)
                        # Temel Veriler
                        try:
                            info = yf.Ticker(ticker).info
                            pddd = info.get("priceToBook", 0)
                            roe = info.get("returnOnEquity", 0) * 100
                        except:
                            pddd, roe = 0, 0
                        
                        results.append({
                            "Hisse": ticker.replace(".IS", ""),
                            "Fiyat": round(float(df["Close"].iloc[-1]), 2),
                            "Karar": karar,
                            "Durum": squeeze,
                            "ROE %": f"%{round(roe, 1)}",
                            "PD/DD": round(pddd, 2),
                            "RSI": rsi,
                            "Güven": puan
                        })
                        time.sleep(0.1) 

            if results:
                res_df = pd.DataFrame(results)
                st.dataframe(res_df.sort_values("Güven", ascending=False), use_container_width=True, hide_index=True)
            else:
                st.warning("Veri çekilemedi. Lütfen internet bağlantısını kontrol edin veya biraz bekleyin.")
