import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite Pro", layout="wide", page_icon="💎")

# CSS ile Sekmeleri ve Arayüzü Özelleştirme (Yeşil Vurgu Eklendi)
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
    /* Aktif ve Önemli Sekmeleri Vurgula */
    button[data-baseweb="tab"]:contains("🔥") {
        color: #00FF00 !important;
        font-weight: bold !important;
        border-bottom-color: #00FF00 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------
# BIST SEKTÖRLER (Ağırlığı Olanlar 🔥 ile İşaretlendi)
# ------------------------------------
BIST_SEKTORLER = {
    "🔥 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "TSKB.IS"],
    "🔥 Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "🔥 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "BRSAN.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "PETKM.IS"],
    "🛒 Perakende": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "SOKM.IS", "ULKER.IS"],
    "🏗️ İnşaat": ["BTCIM.IS", "CIMSA.IS", "OYAKC.IS", "EKGYO.IS"],
    "🚗 Otomotiv": ["FROTO.IS", "DOAS.IS", "TOASO.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS"],
    "📱 İletişim": ["TCELL.IS", "TTKOM.IS"],
    "⛏️ Maden": ["TRALT.IS", "KCAER.IS"],
    "🌱 Tarım": ["GUBRF.IS", "HEKTS.IS"]
}

# ------------------------------------
# VERİ ÇEKME VE ANALİZ
# ------------------------------------
def fetch_data(ticker, is_usd=False, usd_rate=1.0):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df is None or df.empty or len(df) < 30: return None
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']: df[col] = df[col] / usd_rate
        return df
    except: return None

def analyze_stock(df):
    try:
        close = df["Close"]
        fiyat = float(close.iloc[-1])
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_val = float((100 - (100 / (1 + (gain / (loss + 1e-6))))).iloc[-1])
        
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        width = (sma20 + 2*std20 - (sma20 - 2*std20)) / sma20
        squeeze = "🎯 SIKIŞMA" if width.iloc[-1] < 0.12 else "💎 NORMAL"
        
        high_1y = float(df["High"].max())
        low_1y = float(df["Low"].min())
        hedef_fibo = high_1y + ((high_1y - low_1y) * 0.618)
        
        daily_vol = close.pct_change().std()
        dist_pct = (hedef_fibo - fiyat) / fiyat
        est_days = int(abs(dist_pct) / (daily_vol + 1e-6))
        
        ema13 = float(close.ewm(span=13).mean().iloc[-1])
        puan = 0
        if fiyat > ema13: puan += 50
        if 45 < rsi_val < 70: puan += 30
        if width.iloc[-1] < 0.12: puan += 20
        
        if puan >= 80: karar = "🚀 GÜÇLÜ AL"
        elif puan >= 50: karar = "🔄 İZLE"
        else: karar = "🛑 BEKLE"
        
        return {"rsi": round(rsi_val, 2), "hedef": round(hedef_fibo, 2), "vade": f"{max(5, est_days)}-{est_days+15} G", "olasılık": f"%{min(95, 40 + puan)}", "karar": karar, "durum": squeeze, "puan": puan}
    except: return None

# ------------------------------------
# ARAYÜZ
# ------------------------------------
st.sidebar.title("⚙️ Ayarlar")
currency = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = True if currency == "USD $" else False

st.title("📊 BIST Shadow Elite Pro")
st.caption("🔥 simgeli sekmeler piyasa ağırlığı yüksek, lokomotif sektörlerdir.")

tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sec = list(BIST_SEKTORLER.keys())[i]
        if st.button(f"{sec} Analizini Başlat", key=f"btn_{i}"):
            results = []
            with st.spinner(f"{sec} verileri çekiliyor..."):
                pddd_vals = []
                for ticker in BIST_SEKTORLER[sec]:
                    df = fetch_data(ticker, is_usd)
                    a = analyze_stock(df)
                    if a:
                        try:
                            info = yf.Ticker(ticker).info
                            pddd = info.get("priceToBook", 0)
                            if pddd and pddd > 0: pddd_vals.append(pddd)
                        except: pddd = 0
                        
                        results.append({
                            "Hisse": ticker.replace(".IS", ""),
                            "Fiyat": round(float(df["Close"].iloc[-1]), 2),
                            "Karar": a["karar"],
                            "Durum": a["durum"],
                            "Fibo Hedef": a["hedef"],
                            "Tahmini Vade": a["vade"],
                            "Olasılık": a["olasılık"],
                            "PD/DD": round(pddd, 2),
                            "RSI": a["rsi"],
                            "Güven_G": a["puan"]
                        })
                        time.sleep(0.2)

            if results:
                res_df = pd.DataFrame(results)
                sec_avg = round(np.mean(pddd_vals), 2) if pddd_vals else 0
                st.success(f"📊 {sec} Sektörü PD/DD Ortalaması: {sec_avg}")
                
                def style_rows(row):
                    styles = [''] * len(row)
                    if row['Karar'] == "🚀 GÜÇLÜ AL": styles[row.index.get_loc('Karar')] = 'color: #00FF00; font-weight: bold'
                    elif row['Karar'] == "🛑 BEKLE": styles[row.index.get_loc('Karar')] = 'color: #FF4B4B; font-weight: bold'
                    elif row['Karar'] == "🔄 İZLE": styles[row.index.get_loc('Karar')] = 'color: #FFFF00; font-weight: bold'
                    if row['PD/DD'] < sec_avg: styles[row.index.get_loc('PD/DD')] = 'color: #00FF00'
                    return styles

                final_df = res_df.sort_values("Güven_G", ascending=False).drop(columns=["Güven_G"])
                st.dataframe(final_df.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
