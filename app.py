import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Pro", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; opacity: 0.8; }
    div[data-testid="stMetric"] { 
        padding: 5px 10px !important; 
        background: #1a1c24 !important;
        border: 1px solid #2d2f39 !important;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. VERİ ÇEKME FONKSİYONU (Gelişmiş Hata Yakalayıcı) ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker, interval_key, is_usd=False, usd_rate=1.0):
    try:
        # Veriyi çek
        stock = yf.Ticker(ticker)
        params = {"4 Saatlik": "90m", "Günlük": "1d", "Haftalık": "1wk"}
        df = stock.history(period="1y", interval=params[interval_key])
        
        if df.empty or len(df) < 30:
            return None
        
        # Fiyat ve Selçuk Gönençer 13 EMA Disiplini
        last_price = df['Close'].iloc[-1]
        ema13 = df['Close'].ewm(span=13).mean().iloc[-1]
        
        # Bollinger Sıkışması (Squeeze)
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        upper = sma20 + (2 * std20)
        lower = sma20 - (2 * std20)
        bw = ((upper - lower) / sma20).iloc[-1]
        squeeze_status = "🎯 SIKIŞMA" if bw < 0.12 else "💎 NORMAL"

        # Temel Veriler (ROE ve Temettü)
        info = stock.info
        roe = info.get('returnOnEquity', 0) * 100
        yield_val = info.get('dividendYield', 0) * 100
        pddd = info.get('priceToBook', 0)

        # RSI ve Güven Skoru
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-6))))

        skor = 0
        if last_price > ema13: skor += 50 # 13 EMA üstü TEYİTLİ
        if 40 < rsi < 70: skor += 30
        if df['Volume'].iloc[-1] > df['Volume'].tail(10).mean(): skor += 20

        karar = "🚀 GÜÇLÜ AL" if skor >= 80 else "🔄 TUT" if skor >= 50 else "🛑 SAT"

        return {
            "Hisse": ticker.replace(".IS", ""),
            "Fiyat": round(last_price / usd_rate, 2),
            "ROE(Kar)": f"%{round(roe, 1)}" if roe else "---",
            "Tmtü": f"%{round(yield_val, 1)}" if yield_val else "---",
            "Durum": squeeze_status,
            "PD/DD": round(pddd, 2) if pddd else 0,
            "Karar": karar,
            "Güven": skor
        }
    except:
        return None

# --- 3. ÜST PANEL ---
c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1.5])

with c1:
    st.markdown("### 💎 BIST Shadow Pro")
with c2:
    currency = st.radio("Birim", ["TL ₺", "USD $"], horizontal=True, label_visibility="collapsed")
    is_usd = True if currency == "USD $" else False
with c3:
    vade = st.select_slider("", options=["4 Saatlik", "Günlük", "Haftalık"], label_visibility="collapsed")
with c4:
    st.write(f"⏱️ **Son Güncelleme:** {datetime.now().strftime('%H:%M')}")

# USD Kuru Çek
usd_rate = 1.0
if is_usd:
    try:
        usd_rate = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
    except:
        usd_rate = 34.5

st.divider()

# --- 4. SEKTÖRLER ---
sektorler = {
    "🏦 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
    "🏢 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS"],
    "🏭 Sanayi": ["EREGL.IS", "SISE.IS", "KARDM.IS", "TOASO.IS", "FROTO.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "KONTR.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS", "REEDR.IS", "LOGO.IS"]
}

tabs = st.tabs(list(sektorler.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sk_adi = list(sektorler.keys())[i]
        with st.spinner('Analiz ediliyor...'):
            hisseler = sektorler[sk_adi]
            final_list = []
            for h in hisseler:
                data = fetch_pro_data(h, vade, is_usd, usd_rate)
                if data: final_list.append(data)
                time.sleep(0.2) # Banlanmayı önlemek için her hisse arası küçük bekleme
            
            df = pd.DataFrame(final_list)

        if not df.empty:
            avg_pddd = df['PD/DD'].mean()
            st.caption(f"📍 {sk_adi} PD/DD Ortalaması: {round(avg_pddd, 2)}")

            def style_df(row):
                if row['Güven'] >= 80 and row['PD/DD'] < avg_pddd:
                    return ['background-color: #00ff41; color: black; font-weight: bold'] * len(row)
                return [''] * len(row)

            st.dataframe(df.sort_values("Güven", ascending=False).style.apply(style_df, axis=1), use_container_width=True, hide_index=True)
        else:
            st.error("Veri bağlantısı kurulamadı. Lütfen 10 saniye sonra sayfayı yenileyin.")
