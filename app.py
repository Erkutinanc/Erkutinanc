import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- SAYFA AYARI ---
st.set_page_config(page_title="BIST 50 Hızlı Sinyal", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    .signal-buy { color: #00FF00; font-weight: bold; }
    .signal-sell { color: #FF0000; font-weight: bold; }
    .signal-wait { color: #FFFF00; font-weight: bold; }
    .result-box { background: #1e212b; padding: 15px; border-radius: 8px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- BIST 50 LİSTESİ ---
BIST_50 = [
    "THYAO.IS", "ASELS.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", 
    "KCHOL.IS", "SAHOL.IS", "SISE.IS", "TUPRS.IS", "BIMAS.IS",
    "HALKB.IS", "ISCTR.IS", "KOZAL.IS", "PGSUS.IS", "TCELL.IS",
    "HEKTS.IS", "FROTO.IS", "TOASO.IS", "ARCLK.IS", "VESBE.IS",
    "YKBNK.IS", "VAKBN.IS", "TSKB.IS", "EKGYO.IS", "ENKAI.IS",
    "PETKM.IS", "MGROS.IS", "SOKM.IS", "ALARK.IS", "DOHOL.IS",
    "ANACI.IS", "AFYON.IS", "LOGO.IS", "KONTR.IS", "LINK.IS",
    "ZOREN.IS", "TTRAK.IS", "BURCE.IS", "KARTN.IS", "ODAS.IS",
    "MAVI.IS", "DESA.IS", "POLHO.IS", "ULKER.IS", "CADDE.IS",
    "ISGYO.IS", "AKSEN.IS", "NUHCM.IS", "CELHA.IS", "TRKCM.IS"
]

# --- SİNYAL FONKSİYONU ---
def get_signal(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1mo", interval="1d")
        if len(df) < 20:
            return "VERİ YOK", 0, 0
        close = df['Close']
        price = close.iloc[-1]
        prev = close.iloc[-2]
        change = ((price - prev) / prev) * 100
        
        # Basit strateji: Fiyat > 20 günlük ortalama ve RSI < 70 ise AL
        sma20 = close.rolling(20).mean().iloc[-1]
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        
        if rsi_val < 35 and price > sma20:
            signal = "🟢 AL"
        elif rsi_val > 65 and price < sma20:
            signal = "🔴 SAT"
        elif price > sma20:
            signal = "🟡 TAKİP"
        else:
            signal = "⚪ BEKLE"
        return signal, price, change
    except:
        return "HATA", 0, 0

# --- BAŞLIK ---
st.title("⚡ BIST 50 HIZLI SİNYAL")
st.markdown(f"<div style='color:#888; text-align:right'>Güncelleme: {datetime.now().strftime('%H:%M')}</div>", unsafe_allow_html=True)

# --- FİLTRE ---
filter_option = st.radio("Filtre:", ["Tümü", "Sadece AL", "Sadece SAT", "Sadece TAKİP"], horizontal=True)

# --- VERİ ÇEKME VE GÖSTERİM ---
if st.button("🔄 Sinyalleri Getir", use_container_width=True):
    results = []
    with st.spinner('Hisseler taranıyor...'):
        for ticker in BIST_50:
            signal, price, change = get_signal(ticker)
            if signal != "VERİ YOK" and signal != "HATA":
                results.append({
                    "Hisse": ticker.replace(".IS", ""),
                    "Fiyat": f"{price:.2f}",
                    "Değişim": f"{change:+.2f}%",
                    "Sinyal": signal
                })
    
    df = pd.DataFrame(results)
    
    # Filtreleme
    if filter_option == "Sadece AL":
        df = df[df["Sinyal"].str.contains("AL")]
    elif filter_option == "Sadece SAT":
        df = df[df["Sinyal"].str.contains("SAT")]
    elif filter_option == "Sadece TAKİP":
        df = df[df["Sinyal"].str.contains("TAKİP")]
    
    # Renklendirme
    def color_signal(val):
        if "AL" in val: return "color: #00FF00; font-weight: bold;"
        if "SAT" in val: return "color: #FF0000; font-weight: bold;"
        if "TAKİP" in val: return "color: #FFFF00; font-weight: bold;"
        return "color: #888;"
    
    def color_change(val):
        try:
            num = float(val.replace('%', ''))
            return f"color: {'#00FF00' if num >= 0 else '#FF0000'}"
        except:
            return ''
    
    # Tabloyu göster
    st.dataframe(
        df.style.applymap(color_signal, subset=["Sinyal"])
        .applymap(color_change, subset=["Değişim"]),
        use_container_width=True,
        hide_index=True
    )
    
    # Özet kutuları
    col1, col2, col3 = st.columns(3)
    with col1:
        al_count = len(df[df["Sinyal"].str.contains("AL")])
        st.markdown(f"<div class='result-box'><h3 style='color:#00FF00; margin:0'>AL Sinyali</h3><h1 style='margin:5px 0'>{al_count}</h1></div>", unsafe_allow_html=True)
    with col2:
        sat_count = len(df[df["Sinyal"].str.contains("SAT")])
        st.markdown(f"<div class='result-box'><h3 style='color:#FF0000; margin:0'>SAT Sinyali</h3><h1 style='margin:5px 0'>{sat_count}</h1></div>", unsafe_allow_html=True)
    with col3:
        takip_count = len(df[df["Sinyal"].str.contains("TAKİP")])
        st.markdown(f"<div class='result-box'><h3 style='color:#FFFF00; margin:0'>TAKİP</h3><h1 style='margin:5px 0'>{takip_count}</h1></div>", unsafe_allow_html=True)

else:
    st.info("👆 Sinyalleri görmek için butona basın.")

# --- FOOTER ---
st.markdown("---")
st.markdown("<center><small>⚠️ Yatırım tavsiyesi değildir. Sadece teknik sinyal özetidir.</small></center>", unsafe_allow_html=True)
