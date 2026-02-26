import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from datetime import datetime, timedelta

st.set_page_config(page_title="BIST100 Tarayıcı", layout="wide")

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

    # 0 = negative, 1 = neutral, 2 = positive
    sentiment = scores[2] - scores[0]  
    return float(sentiment)
# ------------------------------------
# BIST100 LİSTESİ
# ------------------------------------
BIST100_LISTESI = [
    "AKBNK.IS","GARAN.IS","HALKB.IS","ISCTR.IS","VAKBN.IS","YKBNK.IS","THYAO.IS","PGSUS.IS",
    "TAVHL.IS","PETKM.IS","TUPRS.IS","TCELL.IS","TTKOM.IS","BIMAS.IS","MAVI.IS","SOKM.IS",
    "AKSEN.IS","ENJSA.IS","AYDEM.IS","EREGL.IS","ISDMR.IS","ULKER.IS","PNSUT.IS"
]

# ------------------------------------
# VERİ ÇEKME (YF üzerinden)
# ------------------------------------
def fetch_data(ticker, period="1y", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df.dropna(inplace=True)
        return df
    except:
        return None

# ------------------------------------
# HABER ÇEKME (Google News API)
# Not: Kullanıcı kendi API anahtarını girmelidir.
# ------------------------------------
NEWS_API_KEY = "BURAYA_KENDİ_API_KEYİNİ_YAZ"

def fetch_news(query, days=3):
    url = (
        f"https://newsapi.org/v2/everything?q={query}"
        f"&from={(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')}"
        f"&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    )

    try:
        r = requests.get(url).json()
        return r.get("articles", [])
    except:
        return []

# ------------------------------------
# HABERLERİN FİNBERT İLE TARANMASI
# ------------------------------------
def analyze_news_effect(ticker):
    articles = fetch_news(ticker.replace(".IS", ""))

    sentiments = []
    for art in articles:
        title = art.get("title", "")
        desc = art.get("description", "")
        text = (title or "") + " " + (desc or "")
        score = analyze_sentiment_finbert(text)
        sentiments.append(score)

    if len(sentiments) == 0:
        return 0, "No News"

    avg = np.mean(sentiments)

    if avg > 0.25:
        label = "Strong Positive"
    elif avg > 0.05:
        label = "Positive"
    elif avg < -0.25:
        label = "Strong Negative"
    elif avg < -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    return round(float(avg), 4), label
# ------------------------------------
# RSI
# ------------------------------------
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ------------------------------------
# Stoch RSI
# ------------------------------------
def calc_stoch_rsi(series, period=14):
    rsi = calc_rsi(series, period)
    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()
    return (rsi - min_rsi) / (max_rsi - min_rsi)


# ------------------------------------
# MACD
# ------------------------------------
def calc_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


# ------------------------------------
# Bollinger Bands
# ------------------------------------
def calc_bollinger(series, period=20, mult=2):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + mult * std
    lower = sma - mult * std
    return sma, upper, lower


# ------------------------------------
# Ichimoku
# ------------------------------------
def calc_ichimoku(df):
    high = df["High"]
    low = df["Low"]

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    chikou = df["Close"].shift(-26)

    return tenkan, kijun, senkou_a, senkou_b, chikou
# ------------------------------------------------
# Fiyat Davranışı Analizi (Momentum + Volatilite)
# ------------------------------------------------
def price_behavior(df):
    close = df["Close"]

    momentum = close.pct_change().rolling(5).mean().iloc[-1]     # kısa vadeli alım baskısı
    volatility = close.pct_change().rolling(20).std().iloc[-1]   # oynaklık
    trend = close.iloc[-1] - close.iloc[-20]                     # 20 günlük trend

    return momentum, volatility, trend


# ------------------------------------------------
# Psikolojik Analiz Skoru
# ------------------------------------------------
def psychological_score(df):
    mom, vol, trend = price_behavior(df)

    score = 0

    # momentum güçlü ise
    if mom > 0:
        score += 25
    elif mom < 0:
        score -= 25

    # trend yönü
    if trend > 0:
        score += 25
    else:
        score -= 25

    # volatilite düşükse güven artar
    if vol < 0.02:
        score += 15
    elif vol > 0.05:
        score -= 15

    return score


# ------------------------------------------------
# Sert AL–SAT Karar Motoru
# Tüm göstergeleri birlikte değerlendirir
# ------------------------------------------------
def decision_engine(df, news_score):
    close = df["Close"]

    rsi = calc_rsi(close).iloc[-1]
    stoch = calc_stoch_rsi(close).iloc[-1]
    macd, signal, hist = calc_macd(close)
    macd = macd.iloc[-1]
    signal = signal.iloc[-1]
    hist = hist.iloc[-1]
    sma, upper, lower = calc_bollinger(close)

    price = close.iloc[-1]

    psych = psychological_score(df)

    total = 0

    # Haber etkisi
    if news_score > 0.2:
        total += 20
    elif news_score < -0.2:
        total -= 20

    # RSI
    if rsi < 30:
        total += 15
    elif rsi > 70:
        total -= 15

    # MACD
    if macd > signal and hist > 0:
        total += 20
    elif macd < signal and hist < 0:
        total -= 20

    # Stoch RSI
    if stoch < 0.2:
        total += 10
    elif stoch > 0.8:
        total -= 10

    # Bollinger sıkışması → trend başlangıcı
    width = ((upper - lower) / sma).iloc[-1]
    if width < 0.12:
        total += 10

    # Psikolojik baskı
    total += psych

    # --------------------------------------------
    # Sert karar
    # --------------------------------------------
    if total >= 50:
        return "AL", total
    elif total <= -40:
        return "SAT", total
    else:
        return "BEKLE", total
# -----------------------------------------
# Sektör sözlüğü (güncellenebilir)
# -----------------------------------------
BIST_SEKTORLER = {
    "Bankacılık": ["AKBNK.IS","GARAN.IS","HALKB.IS","ISCTR.IS","VAKBN.IS","YKBNK.IS"],
    "Havacılık": ["THYAO.IS","PGSUS.IS","TAVHL.IS"],
    "Petrokimya": ["PETKM.IS","TUPRS.IS"],
    "Telekom": ["TCELL.IS","TTKOM.IS"],
    "Enerji": ["AKSEN.IS","ENJSA.IS","AYDEM.IS"],
    "Demir Çelik": ["EREGL.IS","ISDMR.IS"],
    "Perakende": ["BIMAS.IS","MAVI.IS","SOKM.IS"],
    "Gıda": ["ULKER.IS","PNSUT.IS"]
}

# ------------------------------------------------------
# Şirket finansal verilerini çekme (Yahoo Finance)
# ------------------------------------------------------
def fetch_financials(ticker):
    try:
        info = yf.Ticker(ticker).info
        pddd = info.get("priceToBook", None)
        roe = info.get("returnOnEquity", None)
        if roe:
            roe *= 100
        return pddd, roe
    except:
        return None, None


# ------------------------------------------------------
# Sektör ortalamalarını hesaplama
# ------------------------------------------------------
def sector_averages():
    results = {}

    for sector, tickers in BIST_SEKTORLER.items():
        pddd_vals = []
        roe_vals = []

        for t in tickers:
            pddd, roe = fetch_financials(t)
            if pddd: pddd_vals.append(pddd)
            if roe: roe_vals.append(roe)

        if len(pddd_vals) > 0:
            results[sector] = {
                "sector_pddd": np.mean(pddd_vals),
                "sector_roe": np.mean(roe_vals) if len(roe_vals) else None
            }

    return results


SEKTOR_ORt = sector_averages()


# ------------------------------------------------------
# Hissenin sektörüne göre ucuz/pahalı değerlendirilmesi
# ------------------------------------------------------
def valuation_status(ticker):
    sector_name = None
    for sec, tlist in BIST_SEKTORLER.items():
        if ticker in tlist:
            sector_name = sec
            break

    if not sector_name:
        return None, None, "Sector Unknown"

    sector = SEKTOR_ORt.get(sector_name, None)
    if not sector:
        return None, None, "No Data"

    pddd, roe = fetch_financials(ticker)
    if pddd is None:
        return None, None, "No Financial Data"

    sector_pddd = sector["sector_pddd"]
    sector_roe = sector["sector_roe"]

    # Ucuz mu pahalı mı?
    if pddd < sector_pddd * 0.8:
        status = "Ucuz"
    elif pddd > sector_pddd * 1.2:
        status = "Pahalı"
    else:
        status = "Nötr"

    return pddd, roe, status
# ---------------------------------------------------------
# GELİŞMİŞ GRAFİK OLUŞTURUCU
# ---------------------------------------------------------
def plot_advanced(df, ticker):
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.45, 0.18, 0.18, 0.19]
    )

    # -------------------------------
    # 1 — Mum grafiği
    # -------------------------------
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price"
        ),
        row=1, col=1
    )

    # -------------------------------
    # Bollinger Bands
    # -------------------------------
    sma, upper, lower = calc_bollinger(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=upper, line=dict(color="gray"), name="BB Üst"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=lower, line=dict(color="gray"), name="BB Alt"), row=1, col=1)

    # -------------------------------
    # 2 — RSI
    # -------------------------------
    rsi = calc_rsi(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="yellow"), name="RSI"), row=2, col=1)

    # -------------------------------
    # 3 — MACD
    # -------------------------------
    macd, signal, hist = calc_macd(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=macd, line=dict(color="cyan"), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=signal, line=dict(color="white"), name="Signal"), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=hist, name="Hist"), row=3, col=1)

    # -------------------------------
    # 4 — Stoch RSI
    # -------------------------------
    stoch = calc_stoch_rsi(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=stoch, line=dict(color="orange"), name="StochRSI"), row=4, col=1)

    fig.update_layout(
        title=f"{ticker} — Gelişmiş Teknik Grafik",
        height=900,
        template="plotly_dark",
        showlegend=False
    )
    return fig
# ---------------------------------------------------
# Hisse için tam analiz
# ---------------------------------------------------
def full_stock_analysis(ticker):
    df = fetch_data(ticker, period="1y", interval="1d")
    if df is None or len(df) < 60:
        return None

    # HABER ANALİZİ
    news_score, news_label = analyze_news_effect(ticker)

    # KARAR MOTORU
    decision, total_score = decision_engine(df, news_score)

    # PD/DD - ROE - Sektör değerlendirmesi
    pddd, roe, val_status = valuation_status(ticker)

    # Kapanış fiyatı
    price = df["Close"].iloc[-1]

    # Sonuç sözlüğü
    return {
        "Hisse": ticker,
        "Fiyat": round(price, 2),
        "PD/DD": round(pddd, 2) if pddd else None,
        "ROE %": round(roe, 2) if roe else None,
        "Değerleme": val_status,
        "Haber Skoru": news_score,
        "Haber Durumu": news_label,
        "Sinyal": decision,
        "Puan": total_score,
    }


# ---------------------------------------------------
# BIST100 tarayıcısı
# ---------------------------------------------------
def bist100_scanner():
    results = []
    progress = st.progress(0)

    for i, ticker in enumerate(BIST100_LISTESI):
        progress.progress((i + 1) / len(BIST100_LISTESI))

        data = full_stock_analysis(ticker)
        if data:
            results.append(data)

        time.sleep(0.3)  # Rate limit koruması

    if len(results) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df.sort_values("Puan", ascending=False, inplace=True)
    return df
# ---------------------------------------------------
# STREAMLIT ARAYÜZÜ
# ---------------------------------------------------
import streamlit as st
from plotly.subplots import make_subplots

st.title("📊 BIST100 Gelişmiş Al–Sat Tarayıcı")
st.write("Uluslararası haber etkisi • Teknik analiz • Psikolojik davranış • PD/DD sektör karşılaştırması")

menu = st.sidebar.radio(
    "Menü",
    ["📈 BIST100 Tarayıcı", "🔍 Tek Hisse Analizi", "📊 Sektörel Görünüm"]
)

# ---------------------------------------------------
# 1) BIST100 TARAMA EKRANI
# ---------------------------------------------------
if menu == "📈 BIST100 Tarayıcı":
    st.subheader("📈 BIST100 Tarama Sonuçları")
    st.write("FinBERT haber analizi + teknik göstergeler + sektör karşılaştırması + psikolojik analiz")

    if st.button("Tarama Başlat"):
        df = bist100_scanner()
        if df.empty:
            st.error("Veri alınamadı.")
        else:
            st.success(f"{len(df)} hisse bulundu.")
            st.dataframe(df, use_container_width=True)


# ---------------------------------------------------
# 2) TEK HİSSE ANALİZİ
# ---------------------------------------------------
if menu == "🔍 Tek Hisse Analizi":
    st.subheader("🔍 Tek Hisse Gelişmiş Analiz")

    ticker = st.text_input("Hisse kodu (Örn: THYAO.IS)")

    if ticker:
        df = fetch_data(ticker, "1y", "1d")

        if df is None or len(df) < 50:
            st.error("Yeterli veri yok.")
        else:
            # Grafik
            st.subheader("📈 Teknik Grafik")
            fig = plot_advanced(df, ticker)
            st.plotly_chart(fig, use_container_width=True)

            # Analiz
            st.subheader("📊 Temel ve Haber Analizi")

            pddd, roe, val = valuation_status(ticker)
            news_score, news_label = analyze_news_effect(ticker)
            decision, score = decision_engine(df, news_score)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("PD/DD", pddd)
                st.metric("ROE %", roe)

            with col2:
                st.metric("Değerleme", val)
                st.metric("Haber Durumu", news_label)

            with col3:
                st.metric("Sinyal", decision)
                st.metric("Puan", score)


# ---------------------------------------------------
# 3) SEKTÖREL GÖRÜNÜM
# ---------------------------------------------------
if menu == "📊 Sektörel Görünüm":
    st.subheader("📊 BIST Sektör Analizi")

    for sec, tlist in BIST_SEKTORLER.items():
        st.markdown(f"### 🏭 {sec}")

        sector_rows = []
        for t in tlist:
            pddd, roe, val = valuation_status(t)
            sector_rows.append({
                "Hisse": t,
                "PD/DD": pddd,
                "ROE %": roe,
                "Durum": val
            })
            time.sleep(0.2)

        df = pd.DataFrame(sector_rows)
        st.dataframe(df, use_container_width=True)
