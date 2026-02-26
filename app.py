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

# --- 2. YARDIMCI FONKSİYONLAR ---
def analyze_vix(vix):
    if vix < 20: return "⚖️ DENGELİ", "#10b981"
    elif vix < 30: return "⚠️ GERGİN", "#f59e0b"
    else: return "🚨 PANİK", "#ef4444"

@st.cache_data(ttl=600)
def fetch_stock_data(ticker, interval_key, is_usd=False, usd_rate=1.0):
    try:
        t = yf.Ticker(ticker)
        params = {"4 Saatlik": "90m", "Günlük": "1d", "Haftalık": "1wk"}
        df = t.history(period="1y", interval=params[interval_key])
        
        if df.empty or len(df) < 20: return None
        
        # Fiyatı USD/TL seçimine göre ayarla
        fiyat = df['Close'].iloc[-1] / usd_rate
        ema13 = df['Close'].ewm(span=13).mean().iloc[-1] / usd_rate
        
        # --- BOLLINGER SIKIŞMASI (SQUEEZE) ---
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        upper_band = sma20 + (2 * std20)
        lower_band = sma20 - (2 * std20)
        # Bant genişliği % (Düşük değer = Sıkışma/Patlama Yakın)
        bw = ((upper_band - lower_band) / sma20).iloc[-1]
        squeeze = "🎯 SIKIŞMA" if bw < 0.10 else "💎 NORMAL"

        # --- TEMEL VERİLER ---
        info = t.info
        pddd = info.get('priceToBook', 0)
        roe = info.get('returnOnEquity', 0) * 100 # Özsermaye Karlılığı
        div_yield = info.get('dividendYield', 0) * 100 # Temettü Verimi

        # --- SKORLAMA (5-8-13 + RSI) ---
        skor = 0
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-6))))

        if (df['Close'].iloc[-1] / usd_rate) > ema13: skor += 50
        if 40 < rsi < 70: skor += 30
        if df['Volume'].iloc[-1] > df['Volume'].tail(10).mean(): skor += 20
        
        karar = "🚀 GÜÇLÜ AL" if skor >= 80 else "🔄 TUT" if skor >= 50 else "🛑 SAT"
            
        return {
            "Hisse": ticker.replace(".IS", ""),
            "Fiyat": round(fiyat, 2),
            "Kar": f"%{round(roe, 1)}" if roe else "---",
            "Tmtü": f"%{round(div_yield, 1)}" if div_yield else "---",
            "Durum": squeeze,
            "PD/DD": round(pddd, 2) if pddd else 0.0,
            "Karar": karar,
            "Güven": skor
        }
    except: return None

# --- 3. ÜST PANEL & USD SWITCH ---
vix_val = 17.2
vix_text, vix_color = analyze_vix(vix_val)

c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 0.8, 1.2, 1.5])

with c1: st.metric("Piyasa", "NÖTR-POZİTİF", "0.4%")
with c2: 
    st.markdown(f"""<div style="background:#1a1c24; border:1px solid #2d2f39; padding:7px 12px; border-radius:8px; height:68px;">
    <span style="font-size:0.8rem; color:#94a3b8;">VIX</span><br>
    <span style="font-size:1.1rem; font-weight:700;">{vix_val}</span> <span style="font-size:0.7rem; color:{vix_color};">{vix_text}</span></div>""", unsafe_allow_html=True)
with c3: st.write(f"⏱️ **{datetime.now().strftime('%H:%M')}**")
with c4:
    currency = st.radio("Birim", ["TL ₺", "USD $"], horizontal=True, label_visibility="collapsed")
    is_usd = True if currency == "USD $" else False
with c5: vade = st.select_slider("", options=["4 Saatlik", "Günlük", "Haftalık"], label_visibility="collapsed")

# USD Kuru Çek (Sadece USD seçiliyse)
usd_rate = 1.0
if is_usd:
    try: usd_rate = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
    except: usd_rate = 31.0 # Hata durumunda fallback

st.divider()

# --- 4. SEKTÖREL TABLOLAR ---
BIST50 = {
    "🏦 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
    "🏢 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "TOASO.IS", "FROTO.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "AKSEN.IS"],
    "✈️ Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "🛒 Perakende/Gıda": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "AEFES.IS", "ULKER.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS", "REEDR.IS", "LOGO.IS"]
}

tabs = st.tabs(list(BIST50.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sk_adi = list(BIST50.keys())[i]
        with st.spinner('Pro Analiz Yapılıyor...'):
            sonuclar = [fetch_stock_data(h, vade, is_usd, usd_rate if is_usd else 1.0) for h in BIST50[sk_adi]]
            df = pd.DataFrame([r for r in sonuclar if r is not None])
        
        if not df.empty:
            avg_pddd = df['PD/DD'].mean()
            st.caption(f"📍 {sk_adi} Ort. PD/DD: {round(avg_pddd, 2)} | Birim: {'USD' if is_usd else 'TL'}")

            def highlight_pro(row):
                styles = [''] * len(row)
                # KURAL 1: Gölge Fırsat (Yeşil)
                if row['Güven'] >= 80 and row['PD/DD'] < avg_pddd:
                    styles = ['background-color: #00ff41; color: black; font-weight: bold'] * len(row)
                # KURAL 2: Sat (Kırmızı metin)
                elif "SAT" in str(row['Karar']):
                    styles = ['color: #ef4444; font-weight: bold'] * len(row)
                return styles

            st.dataframe(
                df.sort_values("Güven", ascending=False).style.apply(highlight_pro, axis=1), 
                use_container_width=True, hide_index=True
            )
        else: st.error("Bağlantı hatası.")
