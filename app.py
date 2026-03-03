import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- SAYFA AYARI ---
st.set_page_config(page_title="BIST 50 PRO Sinyal Sistemi", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    .signal-strong-buy { color: #00FF00; font-weight: bold; font-size: 1.2em; }
    .signal-buy { color: #32CD32; font-weight: bold; }
    .signal-sell { color: #FF4500; font-weight: bold; }
    .signal-strong-sell { color: #FF0000; font-weight: bold; font-size: 1.2em; }
    .signal-wait { color: #FFFF00; font-weight: bold; }
    .indicator-box { background: #1e212b; padding: 10px; border-radius: 8px; margin: 5px 0; }
    .target-box { background: linear-gradient(90deg, #1a1c24 0%, #0e4b2a 100%); padding: 12px; border-radius: 8px; border-left: 4px solid #00FF00; }
    .stop-box { background: linear-gradient(90deg, #1a1c24 0%, #4b0e0e 100%); padding: 12px; border-radius: 8px; border-left: 4px solid #FF0000; }
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

# --- TEKNİK İNDİKATÖR HESAPLAMALARI ---

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def calculate_fibonacci_levels(high, low):
    diff = high - low
    levels = {
        "0%": low,
        "23.6%": low + 0.236 * diff,
        "38.2%": low + 0.382 * diff,
        "50%": low + 0.5 * diff,
        "61.8%": low + 0.618 * diff,
        "78.6%": low + 0.786 * diff,
        "100%": high
    }
    return levels

def calculate_volume_analysis(volume_df, close_df):
    avg_volume = volume_df.rolling(20).mean()
    current_volume = volume_df.iloc[-1]
    avg_vol = avg_volume.iloc[-1]
    volume_ratio = current_volume / avg_vol if avg_vol > 0 else 1
    return volume_ratio

# --- KAPSAMLI ANALİZ FONKSİYONU ---

@st.cache_data(ttl=300)  # 5 dakika cache
def analyze_stock(ticker):
    try:
        # Farklı zaman periyotları için veri çek
        data_1d = yf.Ticker(ticker).history(period="1mo", interval="1d")
        data_1h = yf.Ticker(ticker).history(period="5d", interval="1h")
        data_wk = yf.Ticker(ticker).history(period="6mo", interval="1wk")
        
        if len(data_1d) < 30:
            return None
        
        close = data_1d['Close']
        high = data_1d['High']
        low = data_1d['Low']
        volume = data_1d['Volume']
        current_price = close.iloc[-1]
        
        # EMA Hesaplamaları
        ema_9 = calculate_ema(close, 9).iloc[-1]
        ema_21 = calculate_ema(close, 21).iloc[-1]
        ema_50 = calculate_ema(close, 50).iloc[-1]
        ema_200 = calculate_ema(close, 200).iloc[-1] if len(close) >= 200 else close.mean()
        
        # RSI
        rsi_14 = calculate_rsi(close, 14).iloc[-1]
        
        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = calculate_bollinger(close, 20, 2)
        bb_upper = bb_upper.iloc[-1]
        bb_mid = bb_mid.iloc[-1]
        bb_lower = bb_lower.iloc[-1]
        
        # Fibonacci (Son 52 hafta)
        high_52w = high.rolling(252).max().iloc[-1] if len(high) >= 252 else high.max()
        low_52w = low.rolling(252).min().iloc[-1] if len(low) >= 252 else low.min()
        fib_levels = calculate_fibonacci_levels(high_52w, low_52w)
        
        # Hacim Analizi
        volume_ratio = calculate_volume_analysis(volume, close)
        
        # --- SİNYAL SKORLAMA SİSTEMİ ---
        score = 0
        signals = []
        
        # EMA Sinyalleri
        if current_price > ema_9 > ema_21 > ema_50:
            score += 3
            signals.append("✅ EMA Trend: GÜÇLÜ YÜKSELİŞ")
        elif current_price > ema_21 > ema_50:
            score += 2
            signals.append("✅ EMA Trend: YÜKSELİŞ")
        elif current_price < ema_9 < ema_21 < ema_50:
            score -= 3
            signals.append("❌ EMA Trend: GÜÇLÜ DÜŞÜŞ")
        elif current_price < ema_21 < ema_50:
            score -= 2
            signals.append("❌ EMA Trend: DÜŞÜŞ")
        
        # RSI Sinyalleri
        if rsi_14 < 30:
            score += 2
            signals.append("✅ RSI: AŞIRI SATIM (AL)")
        elif rsi_14 > 70:
            score -= 2
            signals.append("❌ RSI: AŞIRI ALIM (SAT)")
        elif 40 <= rsi_14 <= 60:
            signals.append("⚪ RSI: NÖTR")
        
        # Bollinger Sinyalleri
        if current_price < bb_lower:
            score += 2
            signals.append("✅ Bollinger: ALT BANT (AL)")
        elif current_price > bb_upper:
            score -= 2
            signals.append("❌ Bollinger: ÜST BANT (SAT)")
        elif bb_lower < current_price < bb_mid:
            signals.append("⚪ Bollinger: ORTA-ALT")
        elif bb_mid < current_price < bb_upper:
            signals.append("⚪ Bollinger: ORTA-ÜST")
        
        # Hacim Sinyalleri
        if volume_ratio > 1.5:
            signals.append(f"📊 Hacim: {volume_ratio:.2f}x (YÜKSEK)")
            if current_price > ema_21:
                score += 1
        elif volume_ratio < 0.5:
            signals.append(f"📊 Hacim: {volume_ratio:.2f}x (DÜŞÜK)")
        
        # --- HEDEF VE STOP SEVİYELERİ ---
        
        # Kısa Vade (1-2 hafta)
        short_target = current_price * 1.05
        short_stop = current_price * 0.97
        
        # Orta Vade (1 ay)
        medium_target = current_price * 1.10
        medium_stop = current_price * 0.92
        
        # Uzun Vade (6 ay - 1 yıl)
        long_target_6m = fib_levels["61.8%"]
        long_target_1y = fib_levels["100%"]
        long_stop = fib_levels["38.2%"]
        
        # --- NİHAİ SİNYAL ---
        if score >= 5:
            final_signal = "🟢 GÜÇLÜ AL"
            signal_class = "signal-strong-buy"
        elif score >= 2:
            final_signal = "🟡 AL"
            signal_class = "signal-buy"
        elif score <= -5:
            final_signal = "🔴 GÜÇLÜ SAT"
            signal_class = "signal-strong-sell"
        elif score <= -2:
            final_signal = "🟠 SAT"
            signal_class = "signal-sell"
        else:
            final_signal = "⚪ BEKLE"
            signal_class = "signal-wait"
        
        # Vade Bazlı Öneriler
        timeframe_signals = {}
        
        # Gün İçi (1 saatlik veri)
        if len(data_1h) > 10:
            close_1h = data_1h['Close']
            rsi_1h = calculate_rsi(close_1h, 14).iloc[-1]
            if rsi_1h < 35:
                timeframe_signals["Gün İçi"] = "AL"
            elif rsi_1h > 65:
                timeframe_signals["Gün İçi"] = "SAT"
            else:
                timeframe_signals["Gün İçi"] = "BEKLE"
        
        # Kısa Vade (1-2 hafta)
        if score >= 3:
            timeframe_signals["Kısa Vade"] = "AL"
        elif score <= -3:
            timeframe_signals["Kısa Vade"] = "SAT"
        else:
            timeframe_signals["Kısa Vade"] = "BEKLE"
        
        # Orta Vade (1 ay)
        if current_price > ema_50:
            timeframe_signals["Orta Vade"] = "AL"
        elif current_price < ema_50:
            timeframe_signals["Orta Vade"] = "SAT"
        else:
            timeframe_signals["Orta Vade"] = "BEKLE"
        
        # Uzun Vade (6 ay - 1 yıl)
        if current_price > ema_200:
            timeframe_signals["Uzun Vade"] = "AL"
        elif current_price < ema_200:
            timeframe_signals["Uzun Vade"] = "SAT"
        else:
            timeframe_signals["Uzun Vade"] = "BEKLE"
        
        return {
            "ticker": ticker,
            "price": current_price,
            "score": score,
            "signal": final_signal,
            "signal_class": signal_class,
            "signals": signals,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "rsi": rsi_14,
            "bb_upper": bb_upper,
            "bb_mid": bb_mid,
            "bb_lower": bb_lower,
            "fib_levels": fib_levels,
            "volume_ratio": volume_ratio,
            "short_target": short_target,
            "short_stop": short_stop,
            "medium_target": medium_target,
            "medium_stop": medium_stop,
            "long_target_6m": long_target_6m,
            "long_target_1y": long_target_1y,
            "long_stop": long_stop,
            "timeframe_signals": timeframe_signals
        }
        
    except Exception as e:
        return None

# --- BAŞLIK ---
st.title("🎯 BIST 50 PRO SİNYAL SİSTEMİ")
st.markdown(f"<div style='color:#888; text-align:right'>Son Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}</div>", unsafe_allow_html=True)

# --- FİLTRELER ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    filter_signal = st.selectbox("Sinyal Filtresi", ["Tümü", "GÜÇLÜ AL", "AL", "BEKLE", "SAT", "GÜÇLÜ SAT"])
with col2:
    filter_vade = st.selectbox("Vade Filtresi", ["Tümü", "Gün İçi", "Kısa Vade", "Orta Vade", "Uzun Vade"])
with col3:
    min_score = st.slider("Min Skor", -10, 10, -10)
with col4:
    search_ticker = st.text_input("Hisse Ara", "")

# --- ANALİZ BUTONU ---
if st.button("🔍 TÜM HİSSELERİ ANALİZ ET", use_container_width=True, type="primary"):
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(BIST_50):
        status_text.text(f"Analiz ediliyor: {ticker} ({i+1}/{len(BIST_50)})")
        result = analyze_stock(ticker)
        if result:
            results.append(result)
        progress_bar.progress((i + 1) / len(BIST_50))
    
    progress_bar.empty()
    status_text.empty()
    
    # Filtreleme
    if filter_signal != "Tümü":
        results = [r for r in results if filter_signal in r["signal"]]
    
    if search_ticker:
        results = [r for r in results if search_ticker.upper() in r["ticker"]]
    
    results = [r for r in results if r["score"] >= min_score]
    
    # --- ÖZET KARTLARI ---
    st.subheader("📊 Piyasa Özeti")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    strong_buy = len([r for r in results if "GÜÇLÜ AL" in r["signal"]])
    buy = len([r for r in results if r["signal"] == "🟡 AL"])
    wait = len([r for r in results if "BEKLE" in r["signal"]])
    sell = len([r for r in results if r["signal"] == "🟠 SAT"])
    strong_sell = len([r for r in results if "GÜÇLÜ SAT" in r["signal"]])
    
    with col1:
        st.markdown(f"<div class='target-box'><h3 style='margin:0;color:#00FF00'>GÜÇLÜ AL</h3><h1 style='margin:5px 0'>{strong_buy}</h1></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='target-box'><h3 style='margin:0;color:#32CD32'>AL</h3><h1 style='margin:5px 0'>{buy}</h1></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='indicator-box'><h3 style='margin:0;color:#FFFF00'>BEKLE</h3><h1 style='margin:5px 0'>{wait}</h1></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='stop-box'><h3 style='margin:0;color:#FF4500'>SAT</h3><h1 style='margin:5px 0'>{sell}</h1></div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='stop-box'><h3 style='margin:0;color:#FF0000'>GÜÇLÜ SAT</h3><h1 style='margin:5px 0'>{strong_sell}</h1></div>", unsafe_allow_html=True)
    
    # --- DETAYLI TABLO ---
    st.subheader("📋 Tüm Sinyaller")
    
    table_data = []
    for r in results:
        table_data.append({
            "Hisse": r["ticker"].replace(".IS", ""),
            "Fiyat": f"{r['price']:.2f}",
            "Skor": r["score"],
            "Sinyal": r["signal"],
            "RSI": f"{r['rsi']:.1f}",
            "Hacim": f"{r['volume_ratio']:.2f}x",
            "Kısa Vade": r["timeframe_signals"].get("Kısa Vade", "-"),
            "Orta Vade": r["timeframe_signals"].get("Orta Vade", "-"),
            "Uzun Vade": r["timeframe_signals"].get("Uzun Vade", "-")
        })
    
    df = pd.DataFrame(table_data)
    
    def color_signal(val):
        if "GÜÇLÜ AL" in val: return "color: #00FF00; font-weight: bold;"
        if "AL" in val: return "color: #32CD32; font-weight: bold;"
        if "GÜÇLÜ SAT" in val: return "color: #FF0000; font-weight: bold;"
        if "SAT" in val: return "color: #FF4500; font-weight: bold;"
        return "color: #FFFF00;"
    
    def color_score(val):
        if val >= 5: return "color: #00FF00;"
        if val >= 2: return "color: #32CD32;"
        if val <= -5: return "color: #FF0000;"
        if val <= -2: return "color: #FF4500;"
        return "color: #FFFF00;"
    
    st.dataframe(
        df.style.applymap(color_signal, subset=["Sinyal"])
        .applymap(color_score, subset=["Skor"]),
        use_container_width=True,
        hide_index=True
    )
    
    # --- DETAYLI HİSSE ANALİZİ ---
    st.subheader("🔬 Detaylı Hisse Analizi")
    
    selected_ticker = st.selectbox("Hisse Seçin", [r["ticker"] for r in results])
    
    if selected_ticker:
        selected_data = next((r for r in results if r["ticker"] == selected_ticker), None)
        
        if selected_data:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                    <div class='indicator-box'>
                        <h2>{selected_data['ticker'].replace('.IS', '')} - {selected_data['signal']}</h2>
                        <p><b>Mevcut Fiyat:</b> {selected_data['price']:.2f} ₺</p>
                        <p><b>Analiz Skoru:</b> {selected_data['score']}</p>
                        <p><b>RSI (14):</b> {selected_data['rsi']:.2f}</p>
                        <p><b>Hacim Oranı:</b> {selected_data['volume_ratio']:.2f}x</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 📈 Teknik İndikatörler")
                indicator_col1, indicator_col2 = st.columns(2)
                
                with indicator_col1:
                    st.markdown(f"""
                        <div class='indicator-box'>
                            <h4>EMA Değerleri</h4>
                            <p>EMA 9: {selected_data['ema_9']:.2f}</p>
                            <p>EMA 21: {selected_data['ema_21']:.2f}</p>
                            <p>EMA 50: {selected_data['ema_50']:.2f}</p>
                            <p>EMA 200: {selected_data['ema_200']:.2f}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with indicator_col2:
                    st.markdown(f"""
                        <div class='indicator-box'>
                            <h4>Bollinger Bantları</h4>
                            <p>Üst: {selected_data['bb_upper']:.2f}</p>
                            <p>Orta: {selected_data['bb_mid']:.2f}</p>
                            <p>Alt: {selected_data['bb_lower']:.2f}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("### 📊 Sinyal Detayları")
                for signal in selected_data["signals"]:
                    st.markdown(f"- {signal}")
            
            with col2:
                st.markdown("### 🎯 Hedef Seviyeler")
                st.markdown(f"""
                    <div class='target-box'>
                        <h4>Kısa Vade (1-2 Hafta)</h4>
                        <p>🎯 Hedef: {selected_data['short_target']:.2f} ₺</p>
                        <p>🛑 Stop: {selected_data['short_stop']:.2f} ₺</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class='target-box'>
                        <h4>Orta Vade (1 Ay)</h4>
                        <p>🎯 Hedef: {selected_data['medium_target']:.2f} ₺</p>
                        <p>🛑 Stop: {selected_data['medium_stop']:.2f} ₺</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class='target-box'>
                        <h4>Uzun Vade (6 Ay - 1 Yıl)</h4>
                        <p>🎯 6 Ay Hedef: {selected_data['long_target_6m']:.2f} ₺</p>
                        <p>🎯 1 Yıl Hedef: {selected_data['long_target_1y']:.2f} ₺</p>
                        <p>🛑 Stop: {selected_data['long_stop']:.2f} ₺</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### ⏱️ Vade Bazlı Sinyaller")
                for vade, sinyal in selected_data["timeframe_signals"].items():
                    if sinyal == "AL":
                        st.success(f"{vade}: {sinyal}")
                    elif sinyal == "SAT":
                        st.error(f"{vade}: {sinyal}")
                    else:
                        st.warning(f"{vade}: {sinyal}")
                
                st.markdown("### 📐 Fibonacci Seviyeleri")
                fib_df = pd.DataFrame([
                    {"Seviye": k, "Fiyat": f"{v:.2f}"} 
                    for k, v in selected_data["fib_levels"].items()
                ])
                st.dataframe(fib_df, hide_index=True, use_container_width=True)

else:
    st.info("👆 Analizi başlatmak için butona tıklayın. İlk yükleme 1-2 dakika sürebilir.")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<center>
    <small>⚠️ <b>YASAL UYARI:</b> Bu sistem sadece teknik analiz amaçlıdır. Yatırım tavsiyesi değildir.</small><br>
    <small>Veriler Yahoo Finance üzerinden alınmaktadır. Gecikmeler olabilir.</small><br>
    <small>© 2024 BIST 50 PRO Sinyal Sistemi</small>
</center>
""", unsafe_allow_html=True)
