import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite Pro", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    button[data-baseweb="tab"]:contains("🔥") { color: #00FF00 !important; font-weight: bold !important; }
    .update-text { color: #888888; font-size: 0.8rem !important; text-align: right; }
    .radar-box {
        background: linear-gradient(90deg, #1a1c24 0%, #0e4b2a 100%);
        border-left: 5px solid #00FF00;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .firsat-box {
        background: #1a1c24;
        border: 1px solid #00FF00;
        border-radius: 8px;
        padding: 5px 10px;
        text-align: center;
    }
    .firsat-hisse { color: #00FF00; font-size: 1rem !important; font-weight: bold; margin: 0; }
    .firsat-detay { font-size: 0.8rem !important; margin: 0; color: #cccccc; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------
# SEKTÖRLER
# ------------------------------------
BIST_SEKTORLER = {
    "🔥 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "TSKB.IS"],
    "🔥 Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "🔥 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "PETKM.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "BRSAN.IS"],
    "🛒 Perakende": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "SOKM.IS", "ULKER.IS"],
    "🏗️ İnşaat": ["BTCIM.IS", "CIMSA.IS", "OYAKC.IS", "EKGYO.IS"],
    "🚗 Otomotiv": ["FROTO.IS", "DOAS.IS", "TOASO.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS"]
}

# ------------------------------------
# ANALİZ MOTORU
# ------------------------------------
def fetch_data(ticker, is_usd=False, usd_rate=1.0):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df is None or df.empty or len(df) < 35: return None
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']: df[col] = df[col] / usd_rate
        return df
    except: return None

def analyze_stock(df):
    try:
        close = df["Close"]
        fiyat = float(close.iloc[-1])
        # Teknik İndikatörler
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_val = float((100 - (100 / (1 + (gain / (loss + 1e-6))))).iloc[-1])
        
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        width = (sma20 + 2*std20 - (sma20 - 2*std20)) / (sma20 + 1e-6)
        is_squeeze = width.iloc[-1] < 0.12
        
        high_1y, low_1y = float(df["High"].max()), float(df["Low"].min())
        hedef_fibo = high_1y + ((high_1y - low_1y) * 0.618)
        
        ema13 = float(close.ewm(span=13).mean().iloc[-1])
        # STOP-LOSS HESABI: EMA13 altı veya son 5 günün en düşüğünün %2 altı
        stop_loss = min(ema13, float(df["Low"].iloc[-5:].min()) * 0.98)
        
        vol = close.pct_change().std()
        est_days = int(abs((hedef_fibo - fiyat) / (fiyat + 1e-6)) / (vol + 1e-6))
        
        puan = 0
        if fiyat > ema13: puan += 50
        if 45 < rsi_val < 65: puan += 30
        if is_squeeze: puan += 20
        
        karar = "🚀 GÜÇLÜ AL" if puan >= 80 else "🔄 İZLE" if puan >= 50 else "🛑 BEKLE"
        return {
            "rsi": round(rsi_val, 2), "hedef": round(hedef_fibo, 2), 
            "vade": f"{max(5, est_days)}-{est_days+12} G", "olasılık": f"%{min(95, 40 + puan)}", 
            "karar": karar, "durum": "🎯 SIKIŞMA" if is_squeeze else "💎 NORMAL", 
            "puan": puan, "stop": round(stop_loss, 2)
        }
    except: return None

# ------------------------------------
# ARAYÜZ
# ------------------------------------
st.sidebar.title("⚙️ Ayarlar")
para_birimi = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = para_birimi == "USD $"

usd_rate = 1.0
if is_usd:
    try: usd_rate = float(yf.download("USDTRY=X", period="1d", progress=False)['Close'].iloc[-1])
    except: usd_rate = 34.50

col_t1, col_t2 = st.columns([3, 1])
with col_t1: st.subheader("📊 BIST Shadow Elite Pro")
with col_t2: time_display = st.empty()

tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sec = list(BIST_SEKTORLER.keys())[i]
        if st.button(f"{sec} Analizini Başlat", key=f"btn_{i}"):
            time_display.markdown(f"<p class='update-text'>⏱️ {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
            results = []
            with st.spinner(f"{sec} taranıyor..."):
                pddd_vals = []
                for ticker in BIST_SEKTORLER[sec]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    a = analyze_stock(df)
                    if a:
                        try: pddd = yf.Ticker(ticker).info.get("priceToBook", 0)
                        except: pddd = 0
                        if pddd and pddd > 0: pddd_vals.append(pddd)
                        results.append({
                            "Hisse": ticker.replace(".IS", ""), "Fiyat": round(float(df["Close"].iloc[-1]), 2),
                            "Karar": a["karar"], "Durum": a["durum"], "Fibo Hedef": a["hedef"],
                            "Stop-Loss": a["stop"], "Tahmini Vade": a["vade"], "Olasılık": a["olasılık"], 
                            "PD/DD": round(pddd, 2), "RSI": a["rsi"], "Puan": a["puan"]
                        })
                        time.sleep(0.05)

            if results:
                res_df = pd.DataFrame(results)
                sec_avg = round(np.mean(pddd_vals), 2) if pddd_vals else 0
                
                # --- 1. RADAR BİLDİRİMİ ---
                radar_hisse = res_df[res_df["Puan"] == res_df["Puan"].max()].iloc[0]
                st.markdown(f"""
                    <div class='radar-box'>
                        <span style='color:#00FF00; font-weight:bold;'>📡 RADAR:</span> 
                        <b>{radar_hisse['Hisse']}</b> şu an sektörün en yüksek potansiyeline sahip (%{radar_hisse['Puan']} Güven). 
                        Hedef: {radar_hisse['Fibo Hedef']} | Stop: {radar_hisse['Stop-Loss']}
                    </div>
                """, unsafe_allow_html=True)

                st.progress(len(res_df[res_df["Karar"] == "🚀 GÜÇLÜ AL"]) / len(res_df))
                
                # --- FIRSATLAR ---
                st.markdown("##### 🌟 Sektör Fırsatları")
                firsatlar = res_df[(res_df["PD/DD"] < sec_avg) & (res_df["Karar"] == "🚀 GÜÇLÜ AL")].sort_values("Puan", ascending=False)
                if not firsatlar.empty:
                    f_cols = st.columns(min(len(firsatlar), 4))
                    for idx, (_, row) in enumerate(firsatlar[:4].iterrows()):
                        birim = "$" if is_usd else "₺"
                        f_cols[idx].markdown(f"""<div class='firsat-box'><p class='firsat-hisse'>{row['Hisse']}</p><p class='firsat-detay'>{row['Fibo Hedef']} {birim}</p></div>""", unsafe_allow_html=True)
                
                # --- ANA TABLO (RENKLİ) ---
                st.divider()
                def style_rows(row):
                    styles = [''] * len(row)
                    if row['Karar'] == "🚀 GÜÇLÜ AL": styles[row.index.get_loc('Karar')] = 'color: #00FF00; font-weight: bold'
                    if row['Stop-Loss'] > 0: styles[row.index.get_loc('Stop-Loss')] = 'color: #FF4B4B;'
                    if row['PD/DD'] < sec_avg: styles[row.index.get_loc('PD/DD')] = 'color: #00FF00'
                    return styles

                st.dataframe(res_df.sort_values("Puan", ascending=False).drop(columns=["Puan"]).style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
                st.info(f"📊 {sec} PD/DD Ortalaması: {sec_avg}")
