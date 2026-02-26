import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite Pro", layout="wide", page_icon="💎")

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
    if vix < 20: return "⚖️ DENGELİ / GÜVENLİ", "#10b981"
    elif vix < 30: return "⚠️ HAFİF GERGİN", "#f59e0b"
    else: return "🚨 YÜKSEK KORKU", "#ef4444"

@st.cache_data(ttl=600)
def fetch_stock_data(ticker, interval_key, is_usd=False, usd_rate=1.0):
    try:
        t = yf.Ticker(ticker)
        params = {"4 Saatlik": "90m", "Günlük": "1d", "Haftalık": "1wk"}
        # Veri çekme periyodunu biraz daha genişletelim ki Bollinger doğru hesaplansın
        df = t.history(period="1y", interval=params[interval_key])
        
        if df.empty or len(df) < 20: return None
        
        # Temel Fiyat ve Ortalamalar (TL bazlı)
        fiyat_tl = df['Close'].iloc[-1]
        ema13 = df['Close'].ewm(span=13).mean().iloc[-1]
        
        # Birim Çevrimi
        display_fiyat = fiyat_tl / usd_rate
        
        # Fibonacci Hedefleme (TL bazlı hesaplanır, birime çevrilir)
        high_max = df['High'].max()
        low_min = df['Low'].min()
        diff = high_max - low_min
        hedef_tl = high_max + (0.618 * diff) if fiyat_tl > (high_max * 0.95) else high_max
        display_hedef = hedef_tl / usd_rate
        
        # --- BOLLINGER SIKIŞMASI (SQUEEZE) ---
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        upper_band = sma20 + (2 * std20)
        lower_band = sma20 - (2 * std20)
        bw = ((upper_band - lower_band) / sma20).iloc[-1]
        # %12 ve altı daralma sıkışma sinyalidir
        squeeze = "🎯 SIKIŞMA" if bw < 0.12 else "💎 NORMAL"

        # --- TEMEL VERİLER (ROE & TEMETTÜ) ---
        # .info bazen yavaşlatabilir, hata kontrolü ekliyoruz
        info = t.info
        roe = info.get('returnOnEquity', 0) * 100 
        div_yield = info.get('dividendYield', 0) * 100 
        pddd = info.get('priceToBook', 0)

        # RSI Gücü
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-6))))
        
        # --- SKORLAMA (Selçuk Gönençer Disiplini) ---
        skor = 0
        if fiyat_tl > ema13: skor += 50
        if 40 < rsi < 70: skor += 30
        if df['Volume'].iloc[-1] > df['Volume'].tail(10).mean(): skor += 20
        
        if skor >= 80: karar = "🚀 GÜÇLÜ AL"
        elif skor >= 50: karar = "🔄 TUT / İZLE"
        elif skor >= 30: karar = "⚠️ BEKLE"
        else: karar = "🛑 SAT / KAÇ"
            
        return {
            "Hisse": ticker.replace(".IS", ""),
            "Fiyat": round(display_fiyat, 2),
            "ROE": f"%{round(roe, 1)}" if roe else "---",
            "Tmtü": f"%{round(div_yield, 1)}" if div_yield else "---",
            "Durum": squeeze,
            "PD/DD": round(pddd, 2) if pddd else 0,
            "Karar": karar,
            "Güven": skor
        }
    except: return None

# --- 3. ÜST PANEL ---
vix_val = 17.2
vix_text, vix_color = analyze_vix(vix_val)

c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 0.8, 1.2, 1.5])

with c1: 
    st.metric("Piyasa Durumu", "NÖTR-POZİTİF", "0.4%")
with c2: 
    st.markdown(f"""
        <div style="background: #1a1c24; border: 1px solid #2d2f39; padding: 7px 12px; border-radius: 8px; height: 68px;">
            <span style="font-size: 0.8rem; color: #94a3b8; display: block;">VIX Endeksi</span>
            <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 2px;">
                <span style="font-size: 1.1rem; font-weight: 700; color: white;">{vix_val}</span>
                <span style="font-size: 0.7rem; color: {vix_color}; font-weight: 600;">{vix_text}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c3: st.write(f"⏱️ **{datetime.now().strftime('%H:%M')}**")
with c4:
    currency = st.radio("Birim", ["TL ₺", "USD $"], horizontal=True, label_visibility="collapsed")
    is_usd = True if currency == "USD $" else False
with c5: 
    vade = st.select_slider("", options=["4 Saatlik", "Günlük", "Haftalık"], label_visibility="collapsed")

# USD Kuru Çekimi
usd_rate = 1.0
if is_usd:
    try:
        usd_rate = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
    except:
        usd_rate = 34.5 # Fallback

st.divider()

# --- 4. SEKTÖREL TABLOLAR ---
BIST50 = {
    "🏦 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
    "🏢 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "TOASO.IS", "FROTO.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "AKSEN.IS"],
    "✈️ Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "🛒 Perakende": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "ULKER.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS", "REEDR.IS", "LOGO.IS"]
}

tabs = st.tabs(list(BIST50.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sk_adi = list(BIST50.keys())[i]
        with st.spinner(f'{sk_adi} Verileri Alınıyor...'):
            sonuclar = []
            for h in BIST50[sk_adi]:
                res = fetch_stock_data(h, vade, is_usd, usd_rate)
                if res: sonuclar.append(res)
                # ÖNEMLİ: Rate limit yememek için her hisse arasında kısa bir mola
                time.sleep(0.15) 
            df = pd.DataFrame(sonuclar)
        
        if not df.empty:
            avg_pddd = df['PD/DD'].mean()
            st.caption(f"📍 {sk_adi} Ort. PD/DD: **{round(avg_pddd, 2)}** | Para Birimi: {'USD' if is_usd else 'TL'}")

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
            st.error("Şu an veri çekilemiyor. Yahoo limitlerine takılmış olabiliriz, lütfen 30 sn sonra yenileyin.")
