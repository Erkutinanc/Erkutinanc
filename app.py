import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite: Final", layout="wide")

# --- VERİ ÇEKME MOTORU (GÜNCELLENDİ) ---
def get_bist_data(ticker):
    try:
        # Engeli aşmak için 'auto_adjust' ve 'actions' kapatıldı, veriyi ham istiyoruz
        data = yf.download(
            tickers=ticker,
            period="1y",
            interval="1d",
            group_by='ticker',
            auto_adjust=False,
            prepost=False,
            threads=False, # Threading bazen ban sebebidir, kapattık
            proxy=None
        )
        
        if data.empty:
            return None
        
        # Çoklu indeks yapısını temizle
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        return data
    except:
        return None

# --- ANALİZ MOTORU ---
def analyze(df):
    try:
        c = df['Close']
        fiyat = float(c.iloc[-1])
        # Basit RSI
        delta = c.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 1e-6)))).iloc[-1]
        
        # Fibonacci Hedefi (Son 1 yılın zirvesine göre)
        zirve = float(df['High'].max())
        dip = float(df['Low'].min())
        hedef = zirve + ((zirve - dip) * 0.618)
        
        return round(rsi, 2), round(hedef, 2)
    except:
        return 0, 0

# --- ARAYÜZ ---
st.title("🚀 BIST Shadow Elite: Kesin Çözüm")

BIST_LISTE = {
    "Banka": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS"],
    "Enerji": ["SASA.IS", "ASTOR.IS", "ENJSA.IS"],
    "Sanayi": ["EREGL.IS", "KCHOL.IS", "SISE.IS"]
}

secilen_sektor = st.selectbox("Sektör Seçin", list(BIST_LISTE.keys()))

if st.button("Analizi Başlat"):
    sonuclar = []
    progress_bar = st.progress(0)
    hisseler = BIST_LISTE[secilen_sektor]
    
    for idx, t in enumerate(hisseler):
        with st.spinner(f"{t} Sorgulanıyor..."):
            df = get_bist_data(t)
            if df is not None:
                rsi, fibo = analyze(df)
                sonuclar.append({
                    "Hisse": t,
                    "Fiyat": round(float(df['Close'].iloc[-1]), 2),
                    "RSI": rsi,
                    "Fibo Hedef": fibo
                })
            else:
                st.warning(f"{t} verisi şu an alınamıyor.")
            
            # Yahoo'yu kızdırmamak için her hisse arasında 1 saniye tam mola
            time.sleep(1)
            progress_bar.progress((idx + 1) / len(hisseler))
            
    if sonuclar:
        st.table(pd.DataFrame(sonuclar))
