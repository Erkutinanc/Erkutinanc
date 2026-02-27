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
    button[data-baseweb="tab"]:contains("🔥") {
        color: #00FF00 !important;
        font-weight: bold !important;
        border-bottom-color: #00FF00 !important;
    }
    .update-text { color: #888888; font-size: 0.9rem; text-align: right; }
    .firsat-box {
        background: #1a1c24;
        border: 1px solid #00FF00;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------
# BIST SEKTÖRLER
# ------------------------------------
BIST_SEKTORLER = {
    "🔥 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "DSTKF.IS", "TSKB.IS"],
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
# ANALİZ MOTORU
# ------------------------------------
def fetch_data(ticker, is_usd=False, usd_rate=1.0):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
        if df is None or df.empty or len(df) < 35: return None
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # USD Dönüşümü
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col] / usd_rate
        return df
    except: return None

def analyze_stock(df):
    try:
        close = df["Close"]
        fiyat = float(close.iloc[-1])
        
        # RSI & Squeeze
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_val = float((100 - (100 / (1 + (gain / (loss + 1e-6))))).iloc[-1])
        
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        width = (sma20 + 2*std20 - (sma20 - 2*std20)) / sma20
        is_squeeze = width.iloc[-1] < 0.12
        
        # Fibonacci 1.618
        high_1y, low_1y = float(df["High"].max()), float(df["Low"].min())
        hedef_fibo = high_1y + ((high_1y - low_1y) * 0.618)
        
        # Volatilite & Vade
        vol = close.pct_change().std()
        est_days = int(abs((hedef_fibo - fiyat) / fiyat) / (vol + 1e-6))
        
        ema13 = float(close.ewm(span=13).mean().iloc[-1])
        puan = 0
        if fiyat > ema13: puan += 50
        if 45 < rsi_val < 65: puan += 30
        if is_squeeze: puan += 20
        
        karar = "🚀 GÜÇLÜ AL" if puan >= 80 else "🔄 İZLE" if puan >= 50 else "🛑 BEKLE"
        return {"rsi": round(rsi_val, 2), "hedef": round(hedef_fibo, 2), "vade": f"{max(5, est_days)}-{est_days+12} G", "olasılık": f"%{min(95, 40 + puan)}", "karar": karar, "durum": "🎯 SIKIŞMA" if is_squeeze else "💎 NORMAL", "puan": puan}
    except: return None

# ------------------------------------
# ARAYÜZ VE AYARLAR
# ------------------------------------
st.sidebar.title("⚙️ Terminal Ayarları")
para_birimi = st.sidebar.radio("Para Birimi Seçin", ["TL ₺", "USD $"])
is_usd = para_birimi == "USD $"

# Canlı USD Kuru Çekimi
usd_rate = 1.0
if is_usd:
    try:
        usd_data = yf.download("USDTRY=X", period="1d", progress=False)
        usd_rate = float(usd_data['Close'].iloc[-1])
    except:
        usd_rate = 34.50 # Hata durumunda fallback

col1, col2 = st.columns([3, 1])
with col1:
    st.title("📊 BIST Shadow Elite Pro")
    st.caption(f"Fırsat Skoru: Sıkışma + Düşük PD/DD + RSI Uyumu | Birim: {para_birimi}")
with col2:
    time_placeholder = st.empty()

tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sec = list(BIST_SEKTORLER.keys())[i]
        if st.button(f"{sec} Analizini Başlat", key=f"btn_{i}"):
            time_placeholder.markdown(f"<p class='update-text'>⏱️ {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
            results = []
            with st.spinner(f"{sec} verileri {para_birimi} bazında analiz ediliyor..."):
                pddd_vals = []
                for ticker in BIST_SEKTORLER[sec]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    a = analyze_stock(df)
                    if a:
                        try:
                            # PD/DD her zaman aynıdır (oran olduğu için para birimi etkilemez)
                            pddd = yf.Ticker(ticker).info.get("priceToBook", 0)
                            if pddd > 0: pddd_vals.append(pddd)
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
                        time.sleep(0.1)

            if results:
                res_df = pd.DataFrame(results)
                sec_avg = round(np.mean(pddd_vals), 2) if pddd_vals else 0
                
                # 1. Piyasa İştahı Barı
                al_orani = len(res_df[res_df["Karar"] == "🚀 GÜÇLÜ AL"]) / len(res_df)
                st.write(f"📈 **Sektör Alım İştahı:**")
                st.progress(al_orani)
                
                # 2. Günün Yıldızları
                st.subheader("🌟 Sektörün En İyi Fırsatları")
                firsatlar = res_df[(res_df["PD/DD"] < sec_avg) & (res_df["Karar"] == "🚀 GÜÇLÜ AL")]
                if not firsatlar.empty:
                    f_cols = st.columns(len(firsatlar[:3]))
                    for idx, row in firsatlar[:3].iterrows():
                        birim = "$" if is_usd else "₺"
                        f_cols[idx % 3].markdown(f"""
                            <div class='firsat-box'>
                                <h3 style='color:#00FF00;margin:0;'>{row['Hisse']}</h3>
                                <p style='margin:0;'>Hedef: {row['Fibo Hedef']} {birim}</p>
                                <small>{row['Durum']}</small>
                            </div>""", unsafe_allow_html=True)
                else:
                    st.write("Şu an kriterlere uyan yıldız hisse bulunamadı.")
                
                # 3. Ana Tablo
                st.divider()
                def style_rows(row):
                    styles = [''] * len(row)
                    if row['Karar'] == "🚀 GÜÇLÜ AL": styles[row.index.get_loc('Karar')] = 'color: #00FF00; font-weight: bold'
                    elif row['Karar'] == "🛑 BEKLE": styles[row.index.get_loc('Karar')] = 'color: #FF4B4B; font-weight: bold'
                    if row['PD/DD'] < sec_avg: styles[row.index.get_loc('PD/DD')] = 'color: #00FF00'
                    return styles

                st.dataframe(res_df.sort_values("Güven_G", ascending=False).drop(columns=["Güven_G"]).style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
                st.info(f"📊 {sec} PD/DD Ortalaması: {sec_avg} | Döviz Kuru: 1 USD = {usd_rate:.2f} TL")
