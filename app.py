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
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------
# GÜNCEL JEOPOLİTİK EĞİLİMLER (Yeni Sektörler Eklendi)
# ------------------------------------
GLOBAL_SENTIMENT = {
    "🔥 Banka": {"Rüzgar": "🔄 Nötr", "Neden": "Global belirsizlik risk iştahını düşürüyor, güvenli liman arayışı.", "Skor": 50},
    "🔥 Ulaştırma": {"Rüzgar": "🚩 Çok Negatif", "Neden": "Ortadoğu çatışma riski: Artan petrol maliyetleri ve hava sahası kısıtları.", "Skor": 20},
    "🔥 Holding": {"Rüzgar": "🔄 Nötr", "Neden": "Savaş riskine karşı savunmacı portföyler ön planda.", "Skor": 55},
    "⚡ Enerji": {"Rüzgar": "🚀 Patlama", "Neden": "Bölgesel çatışmaların arz güvenliğini tehdit etmesi, petrol/gaz rallisi.", "Skor": 95},
    "🏭 Sanayi": {"Rüzgar": "🚩 Negatif", "Neden": "Enerji maliyetlerinde artış baskısı ve tedarik zinciri endişeleri.", "Skor": 35},
    "🛒 Perakende": {"Rüzgar": "✅ Pozitif", "Neden": "Savaş/kriz dönemlerinde defansif talep ve gıda arzı önceliği.", "Skor": 75},
    "🏗️ İnşaat": {"Rüzgar": "🚩 Negatif", "Neden": "Yükselen emtia fiyatları ve inşaat maliyetlerinde artış riski.", "Skor": 40},
    "🚗 Otomotiv": {"Rüzgar": "🚩 Negatif", "Neden": "Lojistik aksamalar ve düşen tüketici güven endeksi.", "Skor": 30},
    "💻 Teknoloji": {"Rüzgar": "✅ Pozitif", "Neden": "Askeri teknoloji (ASELS vb.) ve siber güvenlik talebinde artış.", "Skor": 80},
    "📱 İletişim": {"Rüzgar": "✅ Pozitif", "Neden": "Defansif yapı, enflasyonist ortamda ARPU artışı ve güçlü nakit akışı.", "Skor": 85},
    "⛏️ Maden": {"Rüzgar": "🚀 Patlama", "Neden": "Global krizlerde Altın/Değerli maden rallisi ve emtia fiyat artışları.", "Skor": 90},
    "🌱 Tarım": {"Rüzgar": "✅ Pozitif", "Neden": "Gıda güvenliği endişeleri ve gübre/tarım ürünlerine olan stratejik talep.", "Skor": 70}
}

# ------------------------------------
# SEKTÖRLER (Tam Liste)
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
        st.markdown(f"""<div class='sentiment-box'><table style='width:100%'><tr><td style='width:30%'><b>Global Rüzgar:</b> {gs['Rüzgar']}</td><td style='width:50%'><b>Haber Analizi:</b> <i>{gs['Neden']}</i></td><td style='width:20%; text-align:right;'><b>Eğilim Skoru:</b> {gs['Skor']}</td></tr></table></div>""", unsafe_allow_html=True)
        st.progress(gs['Skor'] / 100)

        if st.button(f"{sec} Analizini Başlat", key=f"btn_{i}"):
            time_display.markdown
