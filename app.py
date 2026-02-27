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
     "🏦 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
    "🏢 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "TOASO.IS", "FROTO.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "AKSEN.IS"],
    "✈️ Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "🛒 Perakende/Gıda": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "AEFES.IS", "ULKER.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS", "REEDR.IS", "LOGO.IS"]
}

# ------------------------------------
# VERİ ÇEKME VE USD DÖNÜŞÜMÜ
# ------------------------------------
def fetch_data(ticker, is_usd=False, usd_rate=1.0):
    try:
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
# TEKNİK ANALİZ MOTORU
# ------------------------------------
def analyze_stock(df):
    try:
        close = df["Close"]
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_series = 100 - (100 / (1 + (gain / (loss + 1e-6))))
        rsi_val = float(rsi_series.iloc[-1])
        
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + (2 * std20)
        lower = sma20 - (2 * std20)
        width_series = (upper - lower) / sma20
        last_width = float(width_series.iloc[-1])
        
        squeeze = "🎯 SIKIŞMA" if last_width < 0.12 else "💎 NORMAL"

        ema13_series = close.ewm(span=13).mean()
        ema13_val = float(ema13_series.iloc[-1])
        fiyat = float(close.iloc[-1])
        
        puan = 0
        if fiyat > ema13_val: puan += 50
        if 40 < rsi_val < 70: puan += 30
        if last_width < 0.12: puan += 20
        
        if puan >= 80:
            karar = "🚀 GÜÇLÜ AL"
        elif puan >= 50:
            karar = "🔄 İZLE"
        else:
            karar = "🛑 BEKLE"
            
        return round(rsi_val, 2), squeeze, karar, puan
    except:
        return 0.0, "⚠️ VERİ HATASI", "BELİRSİZ", 0

# ---------------------------------------------------
# STREAMLIT ARAYÜZÜ VE RENKLENDİRME FONKSİYONU
# ---------------------------------------------------
def highlight_signal(val):
    color = '#ffffff' # Varsayılan beyaz
    if val == "🚀 GÜÇLÜ AL":
        color = '#00FF00' # Yeşil
    elif val == "🛑 BEKLE" or val == "SAT":
        color = '#FF0000' # Kırmızı
    elif val == "🔄 İZLE" or val == "BEKLE":
        color = '#FFFF00' # Sarı
    return f'color: {color}; font-weight: bold'

st.sidebar.title("⚙️ Ayarlar")
currency = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = True if currency == "USD $" else False

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
                sector_pddd_list = []
                
                # Önce sektör verilerini topla
                for ticker in BIST_SEKTORLER[sector_name]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    if df is not None:
                        rsi, squeeze, karar, puan = analyze_stock(df)
                        try:
                            info = yf.Ticker(ticker).info
                            pddd = info.get("priceToBook", 0)
                            roe = info.get("returnOnEquity", 0) * 100
                            if pddd > 0: sector_pddd_list.append(pddd)
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
                
                # Sektör PD/DD Ortalamasını hesapla
                sec_pddd_avg = round(np.mean(sector_pddd_list), 2) if sector_pddd_list else 0
                
                st.info(f"📊 {sector_name} Sektörü PD/DD Ortalaması: **{sec_pddd_avg}**")
                
                # Renklendirme ve Sıralama Uygula
                styled_df = res_df.sort_values("Güven", ascending=False).style.applymap(highlight_signal, subset=['Karar'])
                
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Veri çekilemedi. Lütfen internet bağlantısını kontrol edin veya biraz bekleyin.")
