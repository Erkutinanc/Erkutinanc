import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite", layout="wide", page_icon="💎")

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
    if vix < 20: 
        return "⚖️ DENGELİ / GÜVENLİ", "#10b981"
    elif vix < 30: 
        return "⚠️ HAFİF GERGİN", "#f59e0b"
    else: 
        return "🚨 YÜKSEK KORKU", "#ef4444"

@st.cache_data(ttl=600)
def fetch_stock_data(ticker, interval_key):
    try:
        t = yf.Ticker(ticker)
        params = {"4 Saatlik": "90m", "Günlük": "1d", "Haftalık": "1wk"}
        df = t.history(period="1mo" if interval_key == "4 Saatlik" else "1y", interval=params[interval_key])
        
        if df.empty or len(df) < 5: return None
        
        fiyat = df['Close'].iloc[-1]
        high_max = df['High'].max()
        low_min = df['Low'].min()
        
        # Fibonacci Hedefleme
        diff = high_max - low_min
        hedef = high_max + (0.618 * diff) if fiyat > (high_max * 0.95) else high_max
        
        # RSI Gücü
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-6))))
        
        # --- TEKNİK DİSİPLİN (5-8-13 ARALIKLI) ---
        skor = 0
        ema13 = df['Close'].ewm(span=13).mean().iloc[-1] # Son kale disiplini
        
        if fiyat > ema13: skor += 50
        if 45 < rsi < 70: skor += 30
        if df['Volume'].iloc[-1] > df['Volume'].tail(10).mean(): skor += 20
        
        # Karar Mekanizması
        if skor >= 80: karar = "🚀 GÜÇLÜ AL"
        elif skor >= 50: karar = "🔄 TUT / İZLE"
        elif skor >= 30: karar = "⚠️ BEKLE"
        else: karar = "🛑 SAT / KAÇ"
            
        return {
            "Hisse": ticker.replace(".IS", ""),
            "Fiyat": round(fiyat, 2),
            "Hedef": round(hedef, 2),
            "Potansiyel": f"%{round(((hedef/fiyat)-1)*100, 1)}",
            "PD/DD": t.info.get('priceToBook', 0),
            "Karar": karar,
            "Güven": skor
        }
    except: return None

# --- 3. ÜST PANEL ---
vix_val = 17.2
vix_text, vix_color = analyze_vix(vix_val)

c1, c2, c3, c4 = st.columns([1.5, 1.5, 0.8, 2])

with c1: 
    st.metric("Piyasa Durumu", "NÖTR-POZİTİF", "0.4%")
with c2: 
    st.markdown(f"""
        <div style="background: #1a1c24; border: 1px solid #2d2f39; padding: 7px 12px; border-radius: 8px; height: 68px;">
            <span style="font-size: 0.8rem; color: #94a3b8; display: block;">Korku Endeksi (VIX)</span>
            <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 2px;">
                <span style="font-size: 1.1rem; font-weight: 700; color: white;">{vix_val}</span>
                <span style="font-size: 0.75rem; color: {vix_color}; font-weight: 600;">{vix_text}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c3: 
    st.write(f"⏱️ **{datetime.now().strftime('%H:%M')}**")
with c4: 
    vade = st.select_slider("", options=["4 Saatlik", "Günlük", "Haftalık"], label_visibility="collapsed")

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
        with st.spinner('Fırsat Radarı Çalışıyor...'):
            sonuclar = []
            for h in BIST50[sk_adi]:
                res = fetch_stock_data(h, vade)
                if res: sonuclar.append(res)
                time.sleep(0.1)
            df = pd.DataFrame(sonuclar)
        
        if not df.empty:
            avg_pddd = df['PD/DD'].mean()
            st.caption(f"📍 {sk_adi} Sektörü PD/DD Ortalaması: **{round(avg_pddd, 2)}**")

            def highlight_stars(row):
                if row['Güven'] >= 80 and row['PD/DD'] < avg_pddd:
                    return ['background-color: #00ff41; color: black; font-weight: bold'] * len(row)
                elif "SAT" in str(row['Karar']):
                    return ['color: #ef4444; font-weight: bold'] * len(row)
                return [''] * len(row)

            st.dataframe(
                df.sort_values("Güven", ascending=False).style.apply(highlight_stars, axis=1), 
                use_container_width=True, 
                hide_index=True
            )
