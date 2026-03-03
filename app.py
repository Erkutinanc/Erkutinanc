import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# --- SAYFA AYARI ---
st.set_page_config(page_title="BIST 50 ELITE AI SİNYAL", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    .elite-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; border-radius: 12px; margin: 10px 0; }
    .signal-strong-buy { color: #00FF00; font-weight: bold; font-size: 1.3em; text-shadow: 0 0 10px #00FF00; }
    .signal-buy { color: #32CD32; font-weight: bold; font-size: 1.1em; }
    .signal-sell { color: #FF4500; font-weight: bold; font-size: 1.1em; }
    .signal-strong-sell { color: #FF0000; font-weight: bold; font-size: 1.3em; text-shadow: 0 0 10px #FF0000; }
    .signal-wait { color: #FFFF00; font-weight: bold; }
    .psychology-box { background: linear-gradient(90deg, #1a1c24 0%, #2d1b69 100%); padding: 12px; border-radius: 8px; border-left: 4px solid #9b59b6; }
    .global-box { background: linear-gradient(90deg, #1a1c24 0%, #1e3c72 100%); padding: 12px; border-radius: 8px; border-left: 4px solid #3498db; }
    .target-box { background: linear-gradient(90deg, #1a1c24 0%, #0e4b2a 100%); padding: 12px; border-radius: 8px; border-left: 4px solid #00FF00; }
    .stop-box { background: linear-gradient(90deg, #1a1c24 0%, #4b0e0e 100%); padding: 12px; border-radius: 8px; border-left: 4px solid #FF0000; }
    .indicator-box { background: #1e212b; padding: 10px; border-radius: 8px; margin: 5px 0; }
    .confidence-high { color: #00FF00; font-weight: bold; }
    .confidence-medium { color: #FFFF00; font-weight: bold; }
    .confidence-low { color: #FF0000; font-weight: bold; }
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

# --- GELİŞMİŞ İNDİKATÖRLER ---

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series):
    ema_12 = series.ewm(span=12, adjust=False).mean()
    ema_26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    return k, d

def calculate_adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = pd.DataFrame()
    tr['h-l'] = high - low
    tr['h-pc'] = abs(high - close.shift(1))
    tr['l-pc'] = abs(low - close.shift(1))
    tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    
    atr = tr['tr'].rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx, plus_di, minus_di

def calculate_bollinger(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, sma, lower

def calculate_atr(high, low, close, period=14):
    tr = pd.DataFrame()
    tr['h-l'] = high - low
    tr['h-pc'] = abs(high - close.shift(1))
    tr['l-pc'] = abs(low - close.shift(1))
    tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    return tr['tr'].rolling(window=period).mean()

def calculate_pivot_points(high, low, close):
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    return pivot, r1, s1, r2, s2

def calculate_obv(close, volume):
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=close.index)

def calculate_mfi(high, low, close, volume, period=14):
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = []
    negative_flow = []
    
    for i in range(1, len(typical_price)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            positive_flow.append(money_flow.iloc[i])
            negative_flow.append(0)
        elif typical_price.iloc[i] < typical_price.iloc[i-1]:
            negative_flow.append(money_flow.iloc[i])
            positive_flow.append(0)
        else:
            positive_flow.append(0)
            negative_flow.append(0)
    
    positive_mf = pd.Series(positive_flow, index=close.index[1:]).rolling(window=period).sum()
    negative_mf = pd.Series(negative_flow, index=close.index[1:]).rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi

# --- KÜRESEL PİYASA VERİLERİ ---

@st.cache_data(ttl=600)
def get_global_markets():
    """Küresel piyasa verilerini çek"""
    try:
        # VIX (Korku endeksi)
        vix = yf.Ticker("^VIX").history(period="5d")
        vix_value = vix['Close'].iloc[-1] if not vix.empty else 20
        
        # Petrol (WTI)
        oil = yf.Ticker("CL=F").history(period="1mo")
        oil_change = ((oil['Close'].iloc[-1] - oil['Close'].iloc[-5]) / oil['Close'].iloc[-5] * 100) if len(oil) > 5 else 0
        
        # Altın
        gold = yf.Ticker("GC=F").history(period="1mo")
        gold_change = ((gold['Close'].iloc[-1] - gold['Close'].iloc[-5]) / gold['Close'].iloc[-5] * 100) if len(gold) > 5 else 0
        
        # Dolar Endeksi
        dxy = yf.Ticker("DX-Y.NYB").history(period="1mo")
        dxy_change = ((dxy['Close'].iloc[-1] - dxy['Close'].iloc[-5]) / dxy['Close'].iloc[-5] * 100) if len(dxy) > 5 else 0
        
        # BIST 100
        bist100 = yf.Ticker("^XU100").history(period="1mo")
        bist100_change = ((bist100['Close'].iloc[-1] - bist100['Close'].iloc[-5]) / bist100['Close'].iloc[-5] * 100) if len(bist100) > 5 else 0
        
        return {
            "vix": vix_value,
            "oil_change": oil_change,
            "gold_change": gold_change,
            "dxy_change": dxy_change,
            "bist100_change": bist100_change
        }
    except:
        return {
            "vix": 20,
            "oil_change": 0,
            "gold_change": 0,
            "dxy_change": 0,
            "bist100_change": 0
        }

# --- YATIRIMCI PSİKOLOJİSİ ANALİZİ ---

def analyze_market_psychology(global_data):
    """Piyasa psikolojisini analiz et"""
    vix = global_data["vix"]
    bist_trend = global_data["bist100_change"]
    oil_trend = global_data["oil_change"]
    gold_trend = global_data["gold_change"]
    
    # Korku & Açgöz Endeksi (0-100)
    fear_greed = 50
    
    # VIX etkisi
    if vix < 15:
        fear_greed += 20  # Açgöz
    elif vix < 20:
        fear_greed += 10
    elif vix > 30:
        fear_greed -= 20  # Korku
    elif vix > 25:
        fear_greed -= 10
    
    # BIST trendi
    if bist_trend > 5:
        fear_greed += 15
    elif bist_trend > 2:
        fear_greed += 8
    elif bist_trend < -5:
        fear_greed -= 15
    elif bist_trend < -2:
        fear_greed -= 8
    
    # Altın (Güvenli liman)
    if gold_trend > 3:
        fear_greed -= 10  # Altın yükseliyorsa korku var
    elif gold_trend < -3:
        fear_greed += 10
    
    # Petrol (Ekonomik aktivite)
    if oil_trend > 5:
        fear_greed += 5
    elif oil_trend < -5:
        fear_greed -= 5
    
    fear_greed = max(0, min(100, fear_greed))
    
    # Psikoloji yorumu
    if fear_greed >= 75:
        sentiment = "AŞIRI AÇGÖZ"
        sentiment_color = "#FF0000"
        advice = "Dikkat! Düzeltme riski yüksek"
    elif fear_greed >= 60:
        sentiment = "AÇGÖZ"
        sentiment_color = "#FF8C00"
        advice = "Pozitif ama temkinli ol"
    elif fear_greed >= 40:
        sentiment = "NÖTR"
        sentiment_color = "#FFFF00"
        advice = "Normal piyasa koşulları"
    elif fear_greed >= 25:
        sentiment = "KORKU"
        sentiment_color = "#32CD32"
        advice = "Alım fırsatları çıkabilir"
    else:
        sentiment = "AŞIRI KORKU"
        sentiment_color = "#00FF00"
        advice = "Güçlü alım fırsatı!"
    
    return {
        "fear_greed": fear_greed,
        "sentiment": sentiment,
        "sentiment_color": sentiment_color,
        "advice": advice
    }

# --- ELITE ANALİZ FONKSİYONU ---

@st.cache_data(ttl=300)
def elite_analyze_stock(ticker, global_data, psychology):
    try:
        # Veri çek
        data = yf.Ticker(ticker).history(period="6mo", interval="1d")
        
        if len(data) < 50:
            return None
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        current_price = close.iloc[-1]
        
        # Temel indikatörler
        ema_9 = calculate_ema(close, 9).iloc[-1]
        ema_21 = calculate_ema(close, 21).iloc[-1]
        ema_50 = calculate_ema(close, 50).iloc[-1]
        ema_200 = calculate_ema(close, 200).iloc[-1] if len(close) >= 200 else close.mean()
        
        rsi = calculate_rsi(close, 14).iloc[-1]
        
        # MACD
        macd_line, signal_line, histogram = calculate_macd(close)
        macd = macd_line.iloc[-1]
        macd_signal = signal_line.iloc[-1]
        macd_hist = histogram.iloc[-1]
        
        # Stochastic
        k, d = calculate_stochastic(high, low, close)
        stoch_k = k.iloc[-1]
        stoch_d = d.iloc[-1]
        
        # ADX (Trend gücü)
        adx, plus_di, minus_di = calculate_adx(high, low, close)
        adx_value = adx.iloc[-1]
        plus_di_value = plus_di.iloc[-1]
        minus_di_value = minus_di.iloc[-1]
        
        # Bollinger
        bb_upper, bb_mid, bb_lower = calculate_bollinger(close)
        bb_upper = bb_upper.iloc[-1]
        bb_mid = bb_mid.iloc[-1]
        bb_lower = bb_lower.iloc[-1]
        
        # ATR (Volatilite)
        atr = calculate_atr(high, low, close)
        atr_value = atr.iloc[-1]
        
        # OBV (Hacim trendi)
        obv = calculate_obv(close, volume)
        obv_trend = "Yükseliş" if obv.iloc[-1] > obv.iloc[-10] else "Düşüş"
        
        # MFI (Para akışı)
        mfi = calculate_mfi(high, low, close, volume)
        mfi_value = mfi.iloc[-1] if not mfi.empty else 50
        
        # Pivot noktaları
        pivot, r1, s1, r2, s2 = calculate_pivot_points(high.iloc[-1], low.iloc[-1], close.iloc[-1])
        
        # Hacim analizi
        avg_volume = volume.rolling(20).mean()
        volume_ratio = volume.iloc[-1] / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1
        
        # --- ELITE SKORLAMA SİSTEMİ (Min Skor: 5) ---
        score = 0
        signals = []
        
        # 1. EMA Trend (Max +3/-3)
        if current_price > ema_9 > ema_21 > ema_50 > ema_200:
            score += 3
            signals.append("✅ EMA: MÜKEMMEL YÜKSELİŞ")
        elif current_price > ema_21 > ema_50:
            score += 2
            signals.append("✅ EMA: GÜÇLÜ YÜKSELİŞ")
        elif current_price > ema_50:
            score += 1
            signals.append("✅ EMA: YÜKSELİŞ")
        elif current_price < ema_9 < ema_21 < ema_50 < ema_200:
            score -= 3
            signals.append("❌ EMA: MÜKEMMEL DÜŞÜŞ")
        elif current_price < ema_21 < ema_50:
            score -= 2
            signals.append("❌ EMA: GÜÇLÜ DÜŞÜŞ")
        elif current_price < ema_50:
            score -= 1
            signals.append("❌ EMA: DÜŞÜŞ")
        
        # 2. MACD (Max +2/-2)
        if macd > macd_signal and macd_hist > 0:
            score += 2
            signals.append("✅ MACD: AL Sinyali")
        elif macd < macd_signal and macd_hist < 0:
            score -= 2
            signals.append("❌ MACD: SAT Sinyali")
        
        # 3. RSI (Max +2/-2)
        if rsi < 30:
            score += 2
            signals.append("✅ RSI: AŞIRI SATIM")
        elif rsi < 40:
            score += 1
            signals.append("✅ RSI: SATIM BÖLGESİ")
        elif rsi > 70:
            score -= 2
            signals.append("❌ RSI: AŞIRI ALIM")
        elif rsi > 60:
            score -= 1
            signals.append("❌ RSI: ALIM BÖLGESİ")
        
        # 4. Stochastic (Max +2/-2)
        if stoch_k < 20 and stoch_k > stoch_d:
            score += 2
            signals.append("✅ Stochastic: AL")
        elif stoch_k > 80 and stoch_k < stoch_d:
            score -= 2
            signals.append("❌ Stochastic: SAT")
        
        # 5. ADX Trend Gücü (Max +2/-2)
        if adx_value > 25 and plus_di_value > minus_di_value:
            score += 2
            signals.append(f"✅ ADX: GÜÇLÜ YÜKSELİŞ ({adx_value:.1f})")
        elif adx_value > 25 and minus_di_value > plus_di_value:
            score -= 2
            signals.append(f"❌ ADX: GÜÇLÜ DÜŞÜŞ ({adx_value:.1f})")
        elif adx_value < 20:
            signals.append(f"⚪ ADX: ZAYIF TREND ({adx_value:.1f})")
        
        # 6. Bollinger (Max +2/-2)
        if current_price < bb_lower:
            score += 2
            signals.append("✅ Bollinger: ALT BANT (AL)")
        elif current_price > bb_upper:
            score -= 2
            signals.append("❌ Bollinger: ÜST BANT (SAT)")
        
        # 7. Hacim (Max +2/-1)
        if volume_ratio > 2 and current_price > ema_21:
            score += 2
            signals.append(f"✅ Hacim: ÇOK YÜKSEK ({volume_ratio:.1f}x)")
        elif volume_ratio > 1.5 and current_price > ema_21:
            score += 1
            signals.append(f"✅ Hacim: YÜKSEK ({volume_ratio:.1f}x)")
        elif volume_ratio < 0.5:
            score -= 1
            signals.append(f"❌ Hacim: ÇOK DÜŞÜK ({volume_ratio:.1f}x)")
        
        # 8. OBV (Max +1/-1)
        if obv_trend == "Yükseliş" and current_price > ema_21:
            score += 1
            signals.append("✅ OBV: Hacim trendi POZİTİF")
        elif obv_trend == "Düşüş":
            score -= 1
            signals.append("❌ OBV: Hacim trendi NEGATİF")
        
        # 9. MFI (Max +1/-1)
        if mfi_value < 20:
            score += 1
            signals.append("✅ MFI: Para çıkışı azaldı")
        elif mfi_value > 80:
            score -= 1
            signals.append("❌ MFI: Para girişi azaldı")
        
        # 10. Küresel Piyasa Etkisi (Max +2/-2)
        if psychology["fear_greed"] >= 60 and global_data["bist100_change"] > 0:
            score += 2
            signals.append("✅ Küresel: Piyasa POZİTİF")
        elif psychology["fear_greed"] <= 40 or global_data["bist100_change"] < -2:
            score -= 2
            signals.append("❌ Küresel: Piyasa NEGATİF")
        
        # --- GÜVEN SEVİYESİ ---
        if score >= 8 and adx_value > 25:
            confidence = "ÇOK YÜKSEK"
            confidence_class = "confidence-high"
        elif score >= 5:
            confidence = "YÜKSEK"
            confidence_class = "confidence-high"
        elif score >= 2:
            confidence = "ORTA"
            confidence_class = "confidence-medium"
        else:
            confidence = "DÜŞÜK"
            confidence_class = "confidence-low"
        
        # --- NİHAİ SİNYAL ---
        if score >= 8:
            final_signal = "🟢 GÜÇLÜ AL"
            signal_class = "signal-strong-buy"
        elif score >= 5:
            final_signal = "🟡 AL"
            signal_class = "signal-buy"
        elif score <= -8:
            final_signal = "🔴 GÜÇLÜ SAT"
            signal_class = "signal-strong-sell"
        elif score <= -5:
            final_signal = "🟠 SAT"
            signal_class = "signal-sell"
        else:
            final_signal = "⚪ BEKLE"
            signal_class = "signal-wait"
        
        # --- HEDEF VE STOP SEVİYELERİ ---
        # ATR bazlı dinamik stop
        short_target = current_price + (atr_value * 2)
        short_stop = current_price - (atr_value * 1.5)
        
        medium_target = current_price * 1.08
        medium_stop = current_price * 0.94
        
        # Pivot bazlı hedefler
        long_target = r2 if current_price > pivot else s2
        long_stop = s1 if current_price > pivot else r1
        
        # Vade bazlı sinyaller
        timeframe_signals = {
            "Gün İçi": "AL" if (rsi < 40 and stoch_k < 30) else ("SAT" if (rsi > 60 and stoch_k > 70) else "BEKLE"),
            "Kısa Vade": "AL" if score >= 5 else ("SAT" if score <= -5 else "BEKLE"),
            "Orta Vade": "AL" if current_price > ema_50 and macd > macd_signal else ("SAT" if current_price < ema_50 else "BEKLE"),
            "Uzun Vade": "AL" if current_price > ema_200 and adx_value > 25 else ("SAT" if current_price < ema_200 else "BEKLE")
        }
        
        return {
            "ticker": ticker,
            "price": current_price,
            "score": score,
            "signal": final_signal,
            "signal_class": signal_class,
            "confidence": confidence,
            "confidence_class": confidence_class,
            "signals": signals,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "adx": adx_value,
            "atr": atr_value,
            "obv_trend": obv_trend,
            "mfi": mfi_value,
            "volume_ratio": volume_ratio,
            "pivot": pivot,
            "r1": r1, "s1": s1, "r2": r2, "s2": s2,
            "bb_upper": bb_upper,
            "bb_mid": bb_mid,
            "bb_lower": bb_lower,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "short_target": short_target,
            "short_stop": short_stop,
            "medium_target": medium_target,
            "medium_stop": medium_stop,
            "long_target": long_target,
            "long_stop": long_stop,
            "timeframe_signals": timeframe_signals
        }
        
    except Exception as e:
        print(f"Hata ({ticker}): {e}")
        return None

# --- BAŞLIK ---
st.title("🚀 BIST 50 ELITE AI SİNYAL SİSTEMİ")
st.markdown(f"<div style='color:#888; text-align:right'>Son Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}</div>", unsafe_allow_html=True)

# --- KÜRESEL PİYASALAR ---
st.subheader("🌍 KÜRESEL PİYASA DURUMU")
global_data = get_global_markets()
psychology = analyze_market_psychology(global_data)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    vix_color = "#00FF00" if global_data["vix"] < 20 else ("#FFFF00" if global_data["vix"] < 30 else "#FF0000")
    st.markdown(f"""
        <div class='global-box'>
            <h4 style='margin:0;color:#3498db'>VIX (Korku)</h4>
            <h2 style='margin:5px 0;color:{vix_color}'>{global_data['vix']:.1f}</h2>
        </div>
    """, unsafe_allow_html=True)

with col2:
    oil_color = "#00FF00" if global_data["oil_change"] >= 0 else "#FF0000"
    st.markdown(f"""
        <div class='global-box'>
            <h4 style='margin:0;color:#3498db'>Petrol</h4>
            <h2 style='margin:5px 0;color:{oil_color}'>{global_data['oil_change']:+.2f}%</h2>
        </div>
    """, unsafe_allow_html=True)

with col3:
    gold_color = "#00FF00" if global_data["gold_change"] >= 0 else "#FF0000"
    st.markdown(f"""
        <div class='global-box'>
            <h4 style='margin:0;color:#3498db'>Altın</h4>
            <h2 style='margin:5px 0;color:{gold_color}'>{global_data['gold_change']:+.2f}%</h2>
        </div>
    """, unsafe_allow_html=True)

with col4:
    bist_color = "#00FF00" if global_data["bist100_change"] >= 0 else "#FF0000"
    st.markdown(f"""
        <div class='global-box'>
            <h4 style='margin:0;color:#3498db'>BIST 100</h4>
            <h2 style='margin:5px 0;color:{bist_color}'>{global_data['bist100_change']:+.2f}%</h2>
        </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
        <div class='psychology-box'>
            <h4 style='margin:0;color:#9b59b6'>Korku/Açgöz</h4>
            <h2 style='margin:5px 0;color:{psychology["sentiment_color"]}'>{psychology["fear_greed"]:.0f}</h2>
            <small>{psychology["sentiment"]}</small>
        </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
    <div class='elite-box'>
        <h3 style='margin:0'>🧠 Piyasa Psikolojisi: {psychology["sentiment"]}</h3>
        <p style='margin:5px 0'>{psychology["advice"]}</p>
    </div>
""", unsafe_allow_html=True)

# --- FİLTRELER ---
col1, col2, col3 = st.columns(3)
with col1:
    filter_signal = st.selectbox("Sinyal Filtresi", ["Tümü", "GÜÇLÜ AL", "AL", "BEKLE", "SAT", "GÜÇLÜ SAT"])
with col2:
    filter_confidence = st.selectbox("Güven Seviyesi", ["Tümü", "ÇOK YÜKSEK", "YÜKSEK", "ORTA"])
with col3:
    search_ticker = st.text_input("Hisse Ara", "")

# --- ANALİZ BUTONU ---
if st.button("🎯 ELITE ANALİZ BAŞLAT", use_container_width=True, type="primary"):
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(BIST_50):
        status_text.text(f"Elite analiz: {ticker} ({i+1}/{len(BIST_50)})")
        result = elite_analyze_stock(ticker, global_data, psychology)
        if result:
            results.append(result)
        progress_bar.progress((i + 1) / len(BIST_50))
    
    progress_bar.empty()
    status_text.empty()
    
    if not results:
        st.error("❌ Analiz sonucu alınamadı.")
        st.stop()
    
    # Filtreleme
    if filter_signal != "Tümü":
        results = [r for r in results if filter_signal in r["signal"]]
    
    if search_ticker:
        results = [r for r in results if search_ticker.upper() in r["ticker"]]
    
    if filter_confidence != "Tümü":
        results = [r for r in results if r["confidence"] == filter_confidence]
    
    # ARKA PLAN FİLTRESİ: Min Skor 5 (Kullanıcıya gösterilmez)
    results = [r for r in results if r["score"] >= 5 or "SAT" in r["signal"]]
    
    if not results:
        st.warning("⚠️ Filtrelere uygun sonuç bulunamadı.")
        st.stop()
    
    # --- ÖZET ---
    st.subheader("📊 ELITE ÖZET")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    strong_buy = len([r for r in results if "GÜÇLÜ AL" in r["signal"]])
    buy = len([r for r in results if r["signal"] == "🟡 AL"])
    wait = len([r for r in results if "BEKLE" in r["signal"]])
    sell = len([r for r in results if r["signal"] == "🟠 SAT"])
    strong_sell = len([r for r in results if "GÜÇLÜ SAT" in r["signal"]])
    
    high_conf = len([r for r in results if r["confidence"] in ["ÇOK YÜKSEK", "YÜKSEK"]])
    
    with col1:
        st.markdown(f"<div class='target-box'><h3 style='margin:0;color:#00FF00'>GÜÇLÜ AL</h3><h1 style='margin:5px 0'>{strong_buy}</h1></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='target-box'><h3 style='margin:0;color:#32CD32'>AL</h3><h1 style='margin:5px 0'>{buy}</h1></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='indicator-box'><h3 style='margin:0;color:#FFFF00'>BEKLE</h3><h1 style='margin:5px 0'>{wait}</h1></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='stop-box'><h3 style='margin:0;color:#FF4500'>SAT</h3><h1 style='margin:5px 0'>{sell}</h1></div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='elite-box'><h3 style='margin:0;color:#fff'>YÜKSEK GÜVEN</h3><h1 style='margin:5px 0'>{high_conf}</h1></div>", unsafe_allow_html=True)
    
    # --- TABLO ---
    st.subheader("📋 ELITE SİNYALLER")
    
    table_data = []
    for r in results:
        table_data.append({
            "Hisse": r["ticker"].replace(".IS", ""),
            "Fiyat": f"{r['price']:.2f}",
            "Skor": r["score"],
            "Sinyal": r["signal"],
            "Güven": r["confidence"],
            "RSI": f"{r['rsi']:.1f}",
            "ADX": f"{r['adx']:.1f}",
            "Hacim": f"{r['volume_ratio']:.2f}x"
        })
    
    df = pd.DataFrame(table_data)
    
    def color_signal(val):
        if pd.isna(val): return ""
        if "GÜÇLÜ AL" in val: return "color: #00FF00; font-weight: bold; text-shadow: 0 0 5px #00FF00;"
        if "AL" in val: return "color: #32CD32; font-weight: bold;"
        if "GÜÇLÜ SAT" in val: return "color: #FF0000; font-weight: bold; text-shadow: 0 0 5px #FF0000;"
        if "SAT" in val: return "color: #FF4500; font-weight: bold;"
        return "color: #FFFF00;"
    
    def color_confidence(val):
        if pd.isna(val): return ""
        if val == "ÇOK YÜKSEK": return "color: #00FF00; font-weight: bold;"
        if val == "YÜKSEK": return "color: #32CD32; font-weight: bold;"
        if val == "ORTA": return "color: #FFFF00;"
        return "color: #FF0000;"
    
    st.dataframe(
        df.style.applymap(color_signal, subset=["Sinyal"])
        .applymap(color_confidence, subset=["Güven"]),
        use_container_width=True,
        hide_index=True
    )
    
    # --- DETAYLI ANALİZ ---
    st.subheader("🔬 DETAYLI ELITE ANALİZ")
    
    selected_ticker = st.selectbox("Hisse Seçin", [r["ticker"] for r in results])
    
    if selected_ticker:
        selected = next((r for r in results if r["ticker"] == selected_ticker), None)
        
        if selected:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                    <div class='elite-box'>
                        <h2 style='margin:0'>{selected['ticker'].replace('.IS', '')}</h2>
                        <h1 style='margin:10px 0' class='{selected["signal_class"]}'>{selected["signal"]}</h1>
                        <p><b>Fiyat:</b> {selected['price']:.2f} ₺ | <b>Skor:</b> {selected['score']} | <b>Güven:</b> <span class='{selected["confidence_class"]}'>{selected["confidence"]}</span></p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 📊 Teknik İndikatörler")
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown(f"""
                        <div class='indicator-box'>
                            <h4>RSI & Stochastic</h4>
                            <p>RSI (14): {selected['rsi']:.2f}</p>
                            <p>Stoch K: {selected['stoch_k']:.2f}</p>
                            <p>Stoch D: {selected['stoch_d']:.2f}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with c2:
                    st.markdown(f"""
                        <div class='indicator-box'>
                            <h4>MACD</h4>
                            <p>MACD: {selected['macd']:.4f}</p>
                            <p>Signal: {selected['macd_signal']:.4f}</p>
                            <p>Histogram: {selected['macd'] - selected['macd_signal']:.4f}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with c3:
                    st.markdown(f"""
                        <div class='indicator-box'>
                            <h4>Trend & Hacim</h4>
                            <p>ADX: {selected['adx']:.2f}</p>
                            <p>ATR: {selected['atr']:.2f}</p>
                            <p>MFI: {selected['mfi']:.2f}</p>
                            <p>Hacim: {selected['volume_ratio']:.2f}x</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("### 📈 Sinyal Detayları")
                for sig in selected["signals"]:
                    st.markdown(f"- {sig}")
            
            with col2:
                st.markdown("### 🎯 HEDEF & STOP")
                
                st.markdown(f"""
                    <div class='target-box'>
                        <h4>Kısa Vade (Günlük)</h4>
                        <p>🎯 Hedef: {selected['short_target']:.2f} ₺</p>
                        <p>🛑 Stop: {selected['short_stop']:.2f} ₺</p>
                        <p><small>ATR Bazlı</small></p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class='target-box'>
                        <h4>Orta Vade (Haftalık)</h4>
                        <p>🎯 Hedef: {selected['medium_target']:.2f} ₺</p>
                        <p>🛑 Stop: {selected['medium_stop']:.2f} ₺</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class='target-box'>
                        <h4>Uzun Vade (Pivot)</h4>
                        <p>🎯 Hedef: {selected['long_target']:.2f} ₺</p>
                        <p>🛑 Stop: {selected['long_stop']:.2f} ₺</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### ⏱️ VADE BAZLI")
                for vade, sinyal in selected["timeframe_signals"].items():
                    if sinyal == "AL":
                        st.success(f"{vade}: {sinyal}")
                    elif sinyal == "SAT":
                        st.error(f"{vade}: {sinyal}")
                    else:
                        st.warning(f"{vade}: {sinyal}")
                
                st.markdown("### 📐 PIVOT NOKTALARI")
                st.markdown(f"""
                    <div class='indicator-box'>
                        <p><b>R2:</b> {selected['r2']:.2f}</p>
                        <p><b>R1:</b> {selected['r1']:.2f}</p>
                        <p><b>Pivot:</b> {selected['pivot']:.2f}</p>
                        <p><b>S1:</b> {selected['s1']:.2f}</p>
                        <p><b>S2:</b> {selected['s2']:.2f}</p>
                    </div>
                """, unsafe_allow_html=True)

else:
    st.info("👆 Elite analiz için butona tıklayın. 2-3 dakika sürebilir.")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<center>
    <small>⚠️ <b>YASAL UYARI:</b> Yatırım tavsiyesi değildir. Sadece teknik analiz.</small><br>
    <small> Küresel veriler + Yatırımcı psikolojisi + 15+ indikatör</small><br>
    <small>© 2024 BIST 50 ELITE AI SİNYAL</small>
</center>
""", unsafe_allow_html=True)
