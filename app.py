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
        border-left: 5px solid #00FF00; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px;
    }
    .sentiment-box {
        background: #1e212b; border: 1px solid #444; padding: 10px; border-radius: 8px; margin-bottom: 20px;
    }
    .firsat-box {
        background: #1a1c24; border: 1px solid #00FF00; border-radius: 8px; padding: 5px 10px; text-align: center;
    }
    .firsat-hisse { color: #00FF00; font-size: 1rem !important; font-weight: bold; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------
# GLOBAL GÜNDEM & SEKTÖR EĞİLİMİ
# ------------------------------------
GLOBAL_SENTIMENT = {
    "🔥 Banka": {"Rüzgar": "🚩 Negatif/Nötr", "Neden": "Faiz indirim beklentileri marjları baskılayabilir.", "Skor": 45},
    "🔥 Ulaştırma": {"Rüzgar": "✅ Pozitif", "Neden": "Petrol fiyatlarındaki düşüş ve artan turizm talebi.", "Skor": 85},
    "🔥 Holding": {"Rüzgar": "🔄 Nötr", "Neden": "İskontolu çarpanlar devam ediyor, seçici hareket.", "Skor": 60},
    "⚡ Enerji": {"Rüzgar": "🔥 Çok Pozitif", "Neden": "Yenilenebilir yatırımlar ve global enerji arz güvenliği.", "Skor": 90},
    "🏭 Sanayi": {"Rüzgar": "🚩 Negatif", "Neden": "Avrupa'daki resesyon korkusu ihracatı zorluyor.", "Skor": 40},
    "🛒 Perakende": {"Rüzgar": "✅ Pozitif", "Neden": "Enflasyonist ortamda güçlü nakit akışı ve defansif yapı.", "Skor": 80},
    "🏗️ İnşaat": {"Rüzgar": "🔄 Nötr", "Neden": "Yüksek faizler konut satışlarını baskılıyor.", "Skor": 55},
    "🚗 Otomotiv": {"Rüzgar": "🔄 Nötr", "Neden": "İç piyasada daralma beklentisi, ihracat odaklı seyir.", "Skor": 50},
    "💻 Teknoloji": {"Rüzgar": "🚀 Patlama", "Neden": "AI (Yapay Zeka) rallisi ve dijital dönüşüm talebi.", "Skor": 95}
}

# ------------------------------------
# SEKTÖRLER
# ------------------------------------
BIST_SEKTORLER = {
    "🏦 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "DSTKF.IS", "TSKB.IS"],
    "🏢 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "BRSAN.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "PETKM.IS"],
    "✈️ Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS", "PASEU.IS"],
    "🛒 Perakende": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "AEFES.IS", "SOKM.IS", "ULKER.IS", "MAVI.IS"],
    "🏗️ İnşaat ve Çimento": ["BTCIM.IS", "CIMSA.IS", "OYAKC.IS", "EKGYO.IS", "ENKAI.IS", "KUYAS.IS"],
    "🚗 Otomotiv": ["FROTO.IS", "DOAS.IS", "TOASO.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS"],
    "📱 İletişim": ["TCELL.IS", "TTKOM.IS"],
    "⛏️ Maden": ["TRALT.IS", "KCAER.IS"],
    "🌱 Tarım": ["GUBRF.IS", "HEKTS.IS"],
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
        gunluk_degisim = ((fiyat - float(close.iloc[-2])) / float(close.iloc[-2])) * 100
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
        stop_loss = min(ema13, float(df["Low"].iloc[-5:].min()) * 0.98)
        vol = close.pct_change().std()
        est_days = int(abs((hedef_fibo - fiyat) / (fiyat + 1e-6)) / (vol + 1e-6))
        puan = 0
        if fiyat > ema13: puan += 50
        if 45 < rsi_val < 65: puan += 30
        if is_squeeze: puan += 20
        karar = "🚀 GÜÇLÜ AL" if puan >= 80 else "🔄 İZLE" if puan >= 50 else "🛑 BEKLE"
        return {"rsi": round(rsi_val, 2), "hedef": round(hedef_fibo, 2), "vade": f"{max(5, est_days)}-{est_days+12} G", "olasılık": f"%{min(95, 40 + puan)}", "karar": karar, "durum": "🎯 SIKIŞMA" if is_squeeze else "💎 NORMAL", "puan": puan, "stop": round(stop_loss, 2), "degisim": gunluk_degisim}
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
        
        gs = GLOBAL_SENTIMENT[sec]
        st.markdown(f"""
            <div class='sentiment-box'>
                <table style='width:100%'>
                    <tr>
                        <td style='width:30%'><b>Global Rüzgar:</b> {gs['Rüzgar']}</td>
                        <td style='width:50%'><b>Haber Analizi:</b> <i>{gs['Neden']}</i></td>
                        <td style='width:20%; text-align:right;'><b>Eğilim Skoru:</b> {gs['Skor']}</td>
                    </tr>
                </table>
            </div>
        """, unsafe_allow_html=True)
        st.progress(gs['Skor'] / 100)

        if st.button(f"{sec} Analizini Başlat", key=f"btn_{i}"):
            time_display.markdown(f"<p class='update-text'>⏱️ {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
            results = []
            with st.spinner(f"{sec} taranıyor..."):
                pddd_vals = []
                for ticker in BIST_SEKTORLER[sec]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    a = analyze_stock(df)
                    if a:
                        # PD/DD İyileştirilmiş Çekme Mantığı
                        try:
                            t_info = yf.Ticker(ticker).info
                            pddd = t_info.get("priceToBook")
                            if pddd is None: # Yedek yöntem
                                pddd = t_info.get("forwardPE", 0) / t_info.get("forwardEps", 1) # Çok kaba bir tahmin veya 0
                                pddd = round(pddd, 2) if pddd else 0
                        except: 
                            pddd = 0
                            
                        if pddd and pddd > 0: pddd_vals.append(pddd)
                        
                        results.append({"Hisse": ticker.replace(".IS", ""), "Fiyat": round(float(df["Close"].iloc[-1]), 2), "Karar": a["karar"], "Durum": a["durum"], "Fibo Hedef": a["hedef"], "Stop-Loss": a["stop"], "Tahmini Vade": a["vade"], "Olasılık": a["olasılık"], "PD/DD": round(pddd, 2) if pddd else 0.0, "RSI": a["rsi"], "Puan": a["puan"], "D": a["degisim"]})
                        time.sleep(0.05)

            if results:
                res_df = pd.DataFrame(results)
                sec_avg_pddd = round(np.mean(pddd_vals), 2) if pddd_vals else 0
                sec_avg_degisim = res_df["D"].mean()
                
                def calculate_strength(row):
                    symbol = " ⬆️" if row['D'] > sec_avg_degisim else " ⬇️"
                    leader = " ⚡" if row['D'] > sec_avg_degisim and row['Puan'] >= 80 else ""
                    return f"{row['Hisse']}{symbol}{leader}"
                res_df["Hisse"] = res_df.apply(calculate_strength, axis=1)

                radar_hisse = res_df[res_df["Puan"] == res_df["Puan"].max()].iloc[0]
                st.markdown(f"<div class='radar-box'><span style='color:#00FF00; font-weight:bold;'>📡 RADAR:</span> <b>{radar_hisse['Hisse']}</b> (%{radar_hisse['Puan']} Güven). Hedef: {radar_hisse['Fibo Hedef']}</div>", unsafe_allow_html=True)
                
                st.markdown("##### 🌟 Sektör Fırsatları")
                firsatlar = res_df[(res_df["PD/DD"] > 0) & (res_df["PD/DD"] < sec_avg_pddd) & (res_df["Karar"] == "🚀 GÜÇLÜ AL")].sort_values("Puan", ascending=False)
                if not firsatlar.empty:
                    f_cols = st.columns(min(len(firsatlar), 4))
                    for idx, (_, row) in enumerate(firsatlar[:4].iterrows()):
                        f_cols[idx].markdown(f"<div class='firsat-box'><p class='firsat-hisse'>{row['Hisse']}</p><p class='firsat-detay'>{row['Fibo Hedef']}</p></div>", unsafe_allow_html=True)
                
                st.divider()
                def style_rows(row):
                    styles = [''] * len(row)
                    if row['Karar'] == "🚀 GÜÇLÜ AL": styles[row.index.get_loc('Karar')] = 'color: #00FF00; font-weight: bold'
                    if row['Stop-Loss'] > 0: styles[row.index.get_loc('Stop-Loss')] = 'color: #FF4B4B;'
                    if 0 < row['PD/DD'] < sec_avg_pddd: styles[row.index.get_loc('PD/DD')] = 'color: #00FF00'
                    return styles

                st.dataframe(res_df.sort_values("Puan", ascending=False).drop(columns=["Puan", "D"]).style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
                st.info(f"📊 {sec} PD/DD Ortalaması: {sec_avg_pddd} | Sektör Ort. Değişim: %{sec_avg_degisim:.2f}")
