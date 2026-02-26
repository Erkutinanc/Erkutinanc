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
        # Veri çekme denemesi (Hata toleransı için)
        t = yf.Ticker(ticker)
        params = {"4 Saatlik": "90m", "Günlük": "1d", "Haftalık": "1wk"}
        df = t.history(period="1y", interval=params[interval_key])
        
        if df.empty or len(df) < 20:
            return None
        
        # Fiyat ve Ortalamalar
        fiyat_last = df['Close'].iloc[-1]
        ema13 = df['Close'].ewm(span=13).mean().iloc[-1]
        
        fiyat_display = fiyat_last / usd_rate
        
        # --- BOLLINGER SIKIŞMASI (SQUEEZE) ---
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        upper_band = sma20 + (2 * std20)
        lower_band = sma20 - (2 * std20)
        bw = ((upper_band - lower_band) / sma20).iloc[-1]
        squeeze = "🎯 SIKIŞMA" if bw < 0.12 else "💎 NORMAL"

        # --- TEMEL VERİLER ---
        info = t.info
        pddd = info.get('priceToBook', 0)
        roe = info.get('returnOnEquity', 0) * 100 
        div_yield = info.get('dividendYield', 0) * 100 

        # --- SKORLAMA (Selçuk Gönençer 5-8-13 + RSI) ---
        skor = 0
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-6))))

        # 5-8-13 Disiplini: Fiyat 13 EMA üstündeyse puan ver
        if fiyat_last > ema13: skor += 50
        if 40 < rsi < 70: skor += 30
        if df['Volume'].iloc[-1] > df['Volume'].tail(10).mean(): skor += 20
        
        if skor >= 80: karar = "🚀 GÜÇLÜ AL"
        elif skor >= 50: karar = "🔄 TUT"
        elif skor >= 30: karar = "⚠️ BEKLE"
        else: karar = "🛑 SAT"
            
        return {
            "Hisse": ticker.replace(".IS", ""),
            "Fiyat": round(fiyat_display, 2),
            "ROE": f"%{round(roe, 1)}" if roe else "---",
            "Tmt": f"%{round(div_yield, 1)}" if div_yield else "---",
            "Durum": squeeze,
            "PD/DD": round(pddd, 2) if pddd else 0.0,
            "Karar": karar,
            "Güven": skor
        }
    except Exception as e:
        return None

# --- 3. ÜST PANEL ---
vix_val = 17.2
vix_text, vix_color = analyze_vix(vix_val)

c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 0.8, 1.2, 1.5])

with c1: st.metric("Piyasa", "NÖTR-POZİTİF", "0.4%")
with c2: 
    st.markdown(f"""<div style="background:#1a1c24; border:1px solid #2d2f39; padding:7px 12px; border-radius:8px; height:68px;">
    <span style="font-size:0.8rem; color:#94a3b8;">VIX</span><br>
    <span style="font-size:1.1rem; font-weight:700;">{vix_val}</span> <span style="font-size:0.7rem; color:{vix_color}; font-weight:bold;">{vix_text}</span></div>""", unsafe_allow_html=True)
with c3: st.write(f"⏱️ **{datetime.now().strftime('%H:%M')}**")
with c4:
    currency = st.radio("Birim", ["TL ₺", "USD $"], horizontal=True, label_visibility="collapsed")
    is_usd = True if currency == "USD $" else False
with c5: vade = st.select_slider("", options=["4 Saatlik", "Günlük", "Haftalık"], label_visibility="collapsed")

# USD Kuru Çek
usd_rate = 1.0
if is_usd:
    try:
        u_data = yf.Ticker("USDTRY=X").history(period="1d")
        usd_rate = u_data['Close'].iloc[-1]
    except:
        usd_rate = 34.5

st.divider()

# --- 4. SEKTÖREL TABLOLAR ---
BIST50 = {
    "🏦 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
    "🏢 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"],
    "Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "TOASO.IS", "FROTO.IS"],
    "Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS"],
    "Teknoloji": ["ASELS.IS", "MIATK.IS", "REEDR.IS", "LOGO.IS"]
}

tabs = st.tabs(list(BIST50.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sk_adi = list(BIST50.keys())[i]
        with st.spinner(f'{sk_adi} Analiz Ediliyor...'):
            hisseler = BIST50[sk_adi]
            sonuclar = []
            for h in hisseler:
                res = fetch_stock_data(h, vade, is_usd, usd_rate)
                if res: sonuclar.append(res)
                time.sleep(0.1) # Yahoo banlanmasını önlemek için gecikme
            
            df = pd.DataFrame(sonuclar)
        
        if not df.empty:
            avg_pddd = df['PD/DD'].mean()
            st.caption(f"📍 {sk_adi} Ort. PD/DD: {round(avg_pddd, 2)}")

            def highlight_pro(row):
                if row['Güven'] >= 80 and row['PD/DD'] < avg_pddd:
                    return ['background-color: #00ff41; color: black; font-weight: bold'] * len(row)
                elif "SAT" in str(row['Karar']):
                    return ['color: #ef4444; font-weight: bold'] * len(row)
                return [''] * len(row)

            st.dataframe(
                df.sort_values("Güven", ascending=False).style.apply(highlight_pro, axis=1), 
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Veri çekilemedi. Lütfen sayfayı yenileyin veya internetinizi kontrol edin.")
