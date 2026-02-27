import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from datetime import datetime, timedelta
import time
from plotly.subplots import make_subplots

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Shadow Elite Pro", layout="wide", page_icon="💎")

# CSS: Karanlık tema ve metrik düzenlemeleri
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

# -----------------------------
# FinBERT Haber Analizi Yükleme
# -----------------------------
@st.cache_resource
def load_finbert():
    tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
    model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
    return tokenizer, model

tokenizer, finbert = load_finbert()

def analyze_sentiment_finbert(text):
    if not text or len(text.strip()) < 3:
        return 0
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = finbert(**inputs)
    scores = torch.softmax(outputs.logits, dim=1).numpy()[0]
    sentiment = scores[2] - scores[0]  
    return float(sentiment)

# ------------------------------------
# BIST SEKTÖRLER VE LİSTE
# ------------------------------------
BIST_SEKTORLER = {
    "Bankacılık": ["AKBNK.IS","GARAN.IS","HALKB.IS","ISCTR.IS","VAKBN.IS","YKBNK.IS"],
    "Havacılık": ["THYAO.IS","PGSUS.IS","TAVHL.IS"],
    "Petrokimya": ["PETKM.IS","TUPRS.IS"],
    "Telekom": ["TCELL.IS","TTKOM.IS"],
    "Enerji": ["AKSEN.IS","ENJSA.IS","AYDEM.IS","SASA.IS"],
    "Demir Çelik": ["EREGL.IS","ISDMR.IS","KARDM.IS"],
    "Perakende": ["BIMAS.IS","MAVI.IS","SOKM.IS","MGROS.IS"],
    "Gıda": ["ULKER.IS","PNSUT.IS"]
}

# Tüm hisselerin tek bir listede toplanması
BIST100_LISTESI = [ticker for sublist in BIST_SEKTORLER.values() for ticker in sublist]

# ------------------------------------
# VERİ ÇEKME VE USD DÖNÜŞÜMÜ
# ------------------------------------
def fetch_data(ticker, period="1y", interval="1d", is_usd=False, usd_rate=1.0):
    try:
        # Rate limit koruması için küçük es
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df.dropna(inplace=True)
        
        # USD Switch Uygulaması
        if is_usd:
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = df[col] / usd_rate
        return df
    except:
        return None

# ------------------------------------
# TEKNİK GÖSTERGELER (RSI, MACD, BB, STOCH)
# ------------------------------------
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rsi = 100 - (100 / (1 + (gain / (loss + 1e-6))))
    return rsi

def calc_stoch_rsi(series, period=14):
    rsi = calc_rsi(series, period)
    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()
    return (rsi - min_rsi) / (max_rsi - min_rsi + 1e-6)

def calc_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist

def calc_bollinger(series, period=20, mult=2):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + mult * std
    lower = sma - mult * std
    return sma, upper, lower

# ------------------------------------------------
# KARAR MOTORU (Shadow Elite Disiplini)
# ------------------------------------------------
def decision_engine(df, news_score):
    close = df["Close"]
    rsi = calc_rsi(close).iloc[-1]
    stoch = calc_stoch_rsi(close).iloc[-1]
    macd, signal, hist = calc_macd(close)
    sma, upper, lower = calc_bollinger(close)
    
    # Bollinger Sıkışması Hesabı (Squeeze)
    width = ((upper - lower) / sma).iloc[-1]
    squeeze_status = "🎯 SIKIŞMA" if width < 0.12 else "💎 NORMAL"

    total = 0
    # Haber Etkisi
    if news_score > 0.2: total += 20
    elif news_score < -0.2: total -= 20

    # RSI ve MACD
    if rsi < 30: total += 15
    elif rsi > 70: total -= 15
    if macd.iloc[-1] > signal.iloc[-1]: total += 20
    
    # Selçuk Gönençer 13 EMA Disiplini
    ema13 = close.ewm(span=13).mean().iloc[-1]
    if close.iloc[-1] > ema13: total += 20

    if total >= 50: decision = "AL"
    elif total <= -40: decision = "SAT"
    else: decision = "BEKLE"

    return decision, total, squeeze_status

# ------------------------------------------------------
# FİNANSAL VERİLER VE SEKTÖR ANALİZİ
# ------------------------------------------------------
def fetch_financials(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        pddd = info.get("priceToBook", 0)
        roe = info.get("returnOnEquity", 0) * 100
        div_yield = info.get("dividendYield", 0) * 100
        return pddd, roe, div_yield
    except:
        return 0, 0, 0

# ---------------------------------------------------
# GRAFİK MODÜLÜ
# ---------------------------------------------------
def plot_advanced(df, ticker):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.45, 0.18, 0.18, 0.19])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
    
    sma, upper, lower = calc_bollinger(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=upper, line=dict(color="gray", dash='dash'), name="BB Üst"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=lower, line=dict(color="gray", dash='dash'), name="BB Alt"), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=calc_rsi(df["Close"]), line=dict(color="yellow"), name="RSI"), row=2, col=1)
    
    macd, signal, hist = calc_macd(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=macd, line=dict(color="cyan"), name="MACD"), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=hist, name="Hist"), row=3, col=1)
    
    fig.update_layout(height=800, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)
    return fig

# ---------------------------------------------------
# STREAMLIT ARAYÜZÜ
# ---------------------------------------------------
st.title("📊 BIST Shadow Elite Pro")

# Sidebar Ayarları
st.sidebar.header("⚙️ Kontrol Paneli")
currency = st.sidebar.radio("Para Birimi", ["TL ₺", "USD $"])
is_usd = True if currency == "USD $" else False

# USD Kuru Çekimi
@st.cache_data(ttl=3600)
def get_usd_rate():
    return yf.download("USDTRY=X", period="1d", progress=False)['Close'].iloc[-1]

usd_rate = get_usd_rate() if is_usd else 1.0

menu = st.sidebar.radio("Menü", ["📈 BIST Tarayıcı", "🔍 Tek Hisse Analizi", "📊 Sektörel Görünüm"])

# --- 1) BIST TARAYICI ---
if menu == "📈 BIST Tarayıcı":
    st.subheader(f"🚀 BIST Sektörel Fırsat Radarı ({currency})")
    
    if st.button("Taramayı Başlat"):
        results = []
        progress = st.progress(0)
        
        # Tüm hisseleri tara (Sektör bazlı döngü)
        all_tickers = [t for tlist in BIST_SEKTORLER.values() for t in tlist]
        
        for i, ticker in enumerate(all_tickers):
            progress.progress((i + 1) / len(all_tickers))
            df = fetch_data(ticker, is_usd=is_usd, usd_rate=usd_rate)
            
            if df is not None and len(df) > 30:
                # Haber Analizi (Simüle/Hizli mod)
                news_score = 0.1 # News API limitleri için sabitlendi, istenirse fetch_news açılabilir
                decision, score, squeeze = decision_engine(df, news_score)
                pddd, roe, tmt = fetch_financials(ticker)
                
                results.append({
                    "Hisse": ticker.replace(".IS", ""),
                    "Fiyat": round(df["Close"].iloc[-1], 2),
                    "Sinyal": decision,
                    "Durum": squeeze,
                    "ROE %": round(roe, 1),
                    "Temettü %": round(tmt, 1),
                    "PD/DD": round(pddd, 2),
                    "Puan": score
                })
                time.sleep(0.1) # Rate limit engelleyici
        
        final_df = pd.DataFrame(results)
        st.dataframe(final_df.sort_values("Puan", ascending=False), use_container_width=True, hide_index=True)

# --- 2) TEK HİSSE ANALİZİ ---
if menu == "🔍 Tek Hisse Analizi":
    ticker = st.text_input("Hisse Kodu Giriniz (Örn: THYAO.IS)", "THYAO.IS")
    if ticker:
        df = fetch_data(ticker, is_usd=is_usd, usd_rate=usd_rate)
        if df is not None:
            col1, col2, col3, col4 = st.columns(4)
            pddd, roe, tmt = fetch_financials(ticker)
            decision, score, squeeze = decision_engine(df, 0.1)
            
            col1.metric("Fiyat", f"{round(df['Close'].iloc[-1], 2)} {currency.split()[1]}")
            col2.metric("Sinyal", decision)
            col3.metric("Durum", squeeze)
            col4.metric("ROE %", f"%{round(roe,1)}")
            
            st.plotly_chart(plot_advanced(df, ticker), use_container_width=True)

# --- 3) SEKTÖREL GÖRÜNÜM ---
if menu == "📊 Sektörel Görünüm":
    for sec, tlist in BIST_SEKTORLER.items():
        with st.expander(f"🏭 {sec} Sektörü Analizi"):
            sec_data = []
            for t in tlist:
                pddd, roe, tmt = fetch_financials(t)
                sec_data.append({"Hisse": t, "PD/DD": pddd, "ROE %": roe, "Temettü %": tmt})
            st.table(pd.DataFrame(sec_data))
