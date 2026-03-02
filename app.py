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
    .update-text { color: #888888; font-size: 0.8rem !important; text-align: right; margin-bottom: 10px; }
    .radar-box {
        background: linear-gradient(90deg, #1a1c24 0%, #0e4b2a 100%);
        border-left: 5px solid #00FF00; padding: 12px; border-radius: 8px; margin-bottom: 15px;
    }
    .sentiment-box {
        background: #1e212b; border: 1px solid #444; padding: 12px; border-radius: 8px; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 🌍 JEOPOLİTİK GÜNDEM SÖZLÜĞÜ (GÜNCEL SAVAŞ RİSKİ ENTEGRELİ)
GLOBAL_SENTIMENT = {
    "🔥 Banka": {"Rüzgar": "🔄 Nötr", "Neden": "Belirsizlik nedeniyle risk primi artışı ve kredi iştahında azalma.", "Skor": 45},
    "🔥 Ulaştırma": {"Rüzgar": "🚩 Çok Negatif", "Neden": "Irak-İsrail-ABD gerilimi: Artan petrol maliyetleri ve hava sahası riskleri.", "Skor": 15},
    "🔥 Holding": {"Rüzgar": "🔄 Nötr", "Neden": "Defansif portföy yapıları sayesinde piyasaya göre dirençli seyir.", "Skor": 55},
    "⚡ Enerji": {"Rüzgar": "🚀 Patlama", "Neden": "Bölgesel çatışmaların petrol ve doğalgaz arz güvenliğini tehdit etmesi.", "Skor": 95},
    "🏭 Sanayi": {"Rüzgar": "🚩 Negatif", "Neden": "Artan enerji maliyetleri ve küresel tedarik zinciri aksama riski.", "Skor": 30},
    "🛒 Perakende": {"Rüzgar": "✅ Pozitif", "Neden": "Kriz dönemlerinde gıda ve temel ihtiyaç talebinin defansif gücü.", "Skor": 80},
    "🏗️ İnşaat ve Çimento": {"Rüzgar": "🚩 Negatif", "Neden": "Artan emtia maliyetleri ve yüksek faiz ortamının baskısı.", "Skor": 35},
    "🚗 Otomotiv": {"Rüzgar": "🚩 Negatif", "Neden": "Lojistik aksamalar ve azalan tüketici güven endeksi.", "Skor": 25},
    "💻 Teknoloji": {"Rüzgar": "✅ Pozitif", "Neden": "Siber savunma ve yerli askeri teknoloji projelerindeki ivme.", "Skor": 75},
    "📱 İletişim": {"Rüzgar": "✅ Pozitif", "Neden": "Enflasyona karşı korunaklı gelir yapısı ve güçlü nakit akışı.", "Skor": 85},
    "⛏️ Maden": {"Rüzgar": "🚀 Patlama", "Neden": "Savaş riskine karşı Altın ve değerli emtia fiyatlarındaki küresel ralli.", "Skor": 90},
    "🌱 Tarım": {"Rüzgar": "✅ Pozitif", "Neden": "Gıda arz güvenliğinin stratejik önem kazanması.", "Skor": 75}
}

BIST_SEKTORLER = {
    "🔥 Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "TSKB.IS"],
    "🔥 Ulaştırma": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "🔥 Holding": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS"],
    "⚡ Enerji": ["TUPRS.IS", "ENJSA.IS", "ASTOR.IS", "SASA.IS", "KONTR.IS", "PETKM.IS"],
    "🏭 Sanayi": ["EREGL.IS", "KARDM.IS", "SISE.IS", "ARCLK.IS", "BRSAN.IS"],
    "🛒 Perakende": ["BIMAS.IS", "MGROS.IS", "CCOLA.IS", "SOKM.IS", "ULKER.IS"],
    "🏗️ İnşaat ve Çimento": ["BTCIM.IS", "CIMSA.IS", "OYAKC.IS", "EKGYO.IS"],
    "🚗 Otomotiv": ["FROTO.IS", "DOAS.IS", "TOASO.IS"],
    "💻 Teknoloji": ["ASELS.IS", "MIATK.IS"],
    "📱 İletişim": ["TCELL.IS", "TTKOM.IS"],
    "⛏️ Maden": ["TRALT.IS", "KCAER.IS"],
    "🌱 Tarım": ["GUBRF.IS", "HEKTS.IS"]
}

def fetch_data(ticker, is_usd=False, usd_rate=1.0):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
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
        sma20, std20 = close.rolling(20).mean(), close.rolling(20).std()
        is_squeeze = ((sma20 + 2*std20 - (sma20 - 2*std20)) / (sma20 + 1e-6)).iloc[-1] < 0.12
        high_1y, low_1y = float(df["High"].max()), float(df["Low"].min())
        hedef_fibo = high_1y + ((high_1y - low_1y) * 0.618)
        ema13 = float(close.ewm(span=13).mean().iloc[-1])
        stop_loss = min(ema13, float(df["Low"].iloc[-5:].min()) * 0.98)
        puan = (50 if fiyat > ema13 else 0) + (30 if 45 < rsi_val < 65 else 0) + (20 if is_squeeze else 0)
        return {"rsi": round(rsi_val, 2), "hedef": round(hedef_fibo, 2), "karar": "🚀 GÜÇLÜ AL" if puan >= 80 else "🔄 İZLE" if puan >= 50 else "🛑 BEKLE", "durum": "🎯 SIKIŞMA" if is_squeeze else "💎 NORMAL", "puan": puan, "stop": round(stop_loss, 2), "degisim": gunluk_degisim}
    except: return None

# ARAYÜZ
st.sidebar.title("⚙️ Ayarlar")
para_birimi = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = para_birimi == "USD $"
usd_rate = 1.0
if is_usd:
    try: usd_rate = float(yf.download("USDTRY=X", period="1d", progress=False)['Close'].iloc[-1])
    except: usd_rate = 34.50

st.subheader("📊 BIST Shadow Elite Pro")
time_info = st.empty()
tabs = st.tabs(list(BIST_SEKTORLER.keys()))

for i, tab in enumerate(tabs):
    with tab:
        sec = list(BIST_SEKTORLER.keys())[i]
        gs = GLOBAL_SENTIMENT[sec]
        st.markdown(f"<div class='sentiment-box'><table style='width:100%'><tr><td style='width:25%'><b>Rüzgar:</b> {gs['Rüzgar']}</td><td style='width:55%'><b>Analiz:</b> <i>{gs['Neden']}</i></td><td style='width:20%; text-align:right;'><b>Skor: {gs['Skor']}</b></td></tr></table></div>", unsafe_allow_html=True)
        st.progress(gs['Skor'] / 100)

        if st.button(f"{sec} Analizini Başlat", key=f"btn_{i}"):
            time_info.markdown(f"<p class='update-text'>⏱️ Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)
            results = []
            with st.spinner("Veriler çekiliyor..."):
                pddd_vals = []
                for ticker in BIST_SEKTORLER[sec]:
                    df = fetch_data(ticker, is_usd, usd_rate)
                    a = analyze_stock(df)
                    if a:
                        # PD/DD GARANTİLEME SİSTEMİ
                        pddd = 0.0
                        try:
                            t_obj = yf.Ticker(ticker)
                            pddd = t_obj.fast_info.get('price_to_book', 0.0)
                            if not pddd or pddd == 0:
                                pddd = t_obj.info.get("priceToBook", 0.0)
                            if not pddd or pddd == 0: # 3. Seviye Yedek: Defter Değerine Böl
                                bv = t_obj.info.get("bookValue", 0)
                                if bv > 0: pddd = float(df["Close"].iloc[-1]) / bv
                        except: pddd = 0.0
                        
                        if pddd > 0: pddd_vals.append(pddd)
                        results.append({"Hisse": ticker.replace(".IS", ""), "Fiyat": round(float(df["Close"].iloc[-1]), 2), "Karar": a["karar"], "Durum": a["durum"], "Fibo Hedef": a["hedef"], "Stop-Loss": a["stop"], "PD/DD": round(pddd, 2) if pddd else 0.0, "RSI": a["rsi"], "Puan": a["puan"], "D": a["degisim"]})
                        time.sleep(0.1)

            if results:
                res_df = pd.DataFrame(results)
                sec_avg_pddd = round(np.mean(pddd_vals), 2) if pddd_vals else 1.0
                sec_avg_degisim = res_df["D"].mean()
                def set_strength(row):
                    sym = " ⬆️" if row['D'] > sec_avg_degisim else " ⬇️"
                    ldr = " ⚡" if row['D'] > sec_avg_degisim and row['Puan'] >= 80 else ""
                    return f"{row['Hisse']}{sym}{ldr}"
                res_df["Hisse"] = res_df.apply(set_strength, axis=1)
                radar = res_df[res_df["Puan"] == res_df["Puan"].max()].iloc[0]
                st.markdown(f"<div class='radar-box'><span style='color:#00FF00; font-weight:bold;'>📡 RADAR:</span> <b>{radar['Hisse']}</b> (%{radar['Puan']} Güven). Hedef: {radar['Fibo Hedef']} | Stop: {radar['Stop-Loss']}</div>", unsafe_allow_html=True)
                st.dataframe(res_df.sort_values("Puan", ascending=False).drop(columns=["Puan", "D"]).style.apply(lambda r: ['color:#00FF00;font-weight:bold' if r.Karar=="🚀 GÜÇLÜ AL" else '' for _ in r], axis=1), use_container_width=True, hide_index=True)
                st.info(f"📊 Sektör PD/DD Ortalaması: {sec_avg_pddd} | Sektör Ort. Değişim: %{sec_avg_degisim:.2f}")
