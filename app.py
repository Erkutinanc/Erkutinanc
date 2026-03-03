import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import re

# --- SAYFA AYARI ---
st.set_page_config(page_title="BIST 50 HABER + SENTIMENT", layout="wide", page_icon="📰")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    
    /* KARTLAR - SİYAH/GRİ */
    .day-trade { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
    .week-trade { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
    .month-trade { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
    
    /* ELITE KARTLAR (EN İYİ) */
    .elite-trade { background: linear-gradient(135deg, #1a1c24 0%, #2d3a2d 100%); padding: 15px; border-radius: 8px; margin: 10px 0; border: 2px solid #FFD700; box-shadow: 0 0 15px rgba(255, 215, 0, 0.3); }
    
    /* HABER KUTULARI */
    .news-positive { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #00FF00; }
    .news-negative { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #FF0000; }
    .news-neutral { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #888888; }
    
    /* HEDEF FİYAT RENKLERİ */
    .target-up { color: #00FF00; font-weight: bold; font-size: 1.2em; }
    .target-down { color: #FF0000; font-weight: bold; font-size: 1.2em; }
    
    /* ELITE BADGE */
    .elite-badge { 
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); 
        color: #000; 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-weight: bold; 
        font-size: 0.85em;
        display: inline-block;
        margin-left: 10px;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
    }
    
    /* TOP PICK BADGE */
    .top-badge { 
        background: linear-gradient(135deg, #FF6B6B 0%, #C44569 100%); 
        color: #fff; 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-weight: bold; 
        font-size: 0.85em;
        display: inline-block;
        margin-left: 10px;
        box-shadow: 0 0 10px rgba(255, 107, 107, 0.5);
    }
    
    /* TABLO RENKLERİ */
    div[data-testid="stDataFrame"] { background: #1a1c24; }
    div[data-testid="stDataFrame"] tr { background-color: #1a1c24; color: #ffffff; }
    div[data-testid="stDataFrame"] th { background-color: #0e1117; color: #ffffff; border: 1px solid #333; }
    
    /* BUTONLAR */
    .stButton > button {
        background: #1a1c24;
        color: #ffffff;
        border: 1px solid #333;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background: #2a2d35;
        border: 1px solid #555;
    }
    
    /* METRİKLER */
    [data-testid="stMetricValue"] { color: #ffffff !important; }
    [data-testid="stMetricLabel"] { color: #888888 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- BIST 50 ---
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

# --- SENTIMENT KELİMELERİ ---
POSITIVE_WORDS = [
    'kar', 'kâr', 'büyüme', 'artış', 'yükseliş', 'rekor', 'başarı', 'kazandı',
    'temettü', 'kazanç', 'fırsat', 'iyi', 'olumlu', 'güçlü', 'yatırım', 'anlaşma',
    'ortaklık', 'genişleme', 'yeni', 'proje', 'teşvik', 'destek', 'ödül',
    'hedef', 'beklenti', 'pozitif', 'umut', 'potansiyel', 'değer', 'prim',
    'talep', 'satış', 'ciro', 'pay', 'lider', 'öncü', 'inovasyon', 'teknoloji',
    'ihale', 'sözleşme', 'lisans', 'ruhsat', 'onay', 'izin',
    'dividend', 'profit', 'growth', 'record', 'success', 'gain', 'opportunity',
    'strong', 'positive', 'increase', 'rise', 'win', 'deal', 'partnership',
    'expansion', 'investment', 'target', 'potential', 'value', 'demand'
]

NEGATIVE_WORDS = [
    'zarar', 'düşüş', 'azalış', 'kayıp', 'başarısız', 'kötü', 'olumsuz',
    'zayıf', 'risk', 'tehlike', 'sorun', 'kriz', 'çöküş', 'iflas', 'tasfiye',
    'satış', 'küçülme', 'gerileme', 'negatif', 'korku', 'endişe', 'belirsizlik',
    'dava', 'mahkeme', 'ceza', 'yasak', 'kısıtlama', 'engelleme', 'iptal',
    'red', 'ret', 'erteleme', 'askıya', 'durdurma', 'duraksama',
    'volatilite', 'oynaklık', 'spekülasyon', 'balon', 'çökme', 'erime',
    'loss', 'decline', 'fall', 'drop', 'crisis', 'problem', 'risk', 'weak',
    'negative', 'decrease', 'failure', 'bankruptcy', 'lawsuit', 'penalty',
    'uncertainty', 'fear', 'concern', 'volatile', 'bubble'
]

MARKET_IMPACT_WORDS = {
    'temettü': 3, 'rekor': 3, 'iflas': 3, 'kriz': 3,
    'anlaşma': 2, 'ihale': 2, 'dava': 2, 'ceza': 2,
    'büyüme': 2, 'zarar': 2, 'yatırım': 1, 'risk': 1
}

# --- HABER ÇEKME ---

@st.cache_data(ttl=300)
def get_stock_news(ticker, limit=10):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            return []
        
        news_list = []
        for item in news[:limit]:
            news_item = {
                'title': item.get('title', ''),
                'publisher': item.get('publisher', ''),
                'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)),
                'link': item.get('link', ''),
                'type': item.get('type', 'STORY')
            }
            news_list.append(news_item)
        
        return news_list
    except Exception as e:
        print(f"Haber hatası ({ticker}): {e}")
        return []

def analyze_sentiment(text):
    if not text:
        return 0, 'NÖTR'
    
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    positive_count = 0
    negative_count = 0
    impact_score = 0
    
    for word in words:
        if word in POSITIVE_WORDS:
            positive_count += 1
            if word in MARKET_IMPACT_WORDS:
                impact_score += MARKET_IMPACT_WORDS[word]
            else:
                impact_score += 1
        elif word in NEGATIVE_WORDS:
            negative_count += 1
            if word in MARKET_IMPACT_WORDS:
                impact_score -= MARKET_IMPACT_WORDS[word]
            else:
                impact_score -= 1
    
    total_words = positive_count + negative_count
    if total_words == 0:
        return 0, 'NÖTR'
    
    sentiment_score = (impact_score / total_words) * 50
    sentiment_score = max(-100, min(100, sentiment_score))
    
    if sentiment_score >= 20:
        sentiment_label = 'POZİTİF'
    elif sentiment_score <= -20:
        sentiment_label = 'NEGATİF'
    else:
        sentiment_label = 'NÖTR'
    
    return sentiment_score, sentiment_label

def get_market_sentiment():
    try:
        bist = yf.Ticker("^XU100")
        news = bist.news[:5] if bist.news else []
        
        total_sentiment = 0
        news_count = 0
        
        for item in news:
            title = item.get('title', '')
            score, _ = analyze_sentiment(title)
            total_sentiment += score
            news_count += 1
        
        avg_sentiment = total_sentiment / news_count if news_count > 0 else 0
        
        if avg_sentiment >= 15:
            return "POZİTİF", "#00FF00", "Piyasa iyimser, alım fırsatları var"
        elif avg_sentiment <= -15:
            return "NEGATİF", "#FF0000", "Piyasa kötümser, temkinli ol"
        else:
            return "NÖTR", "#FFFF00", "Piyasa dengeli, normal koşullar"
            
    except:
        return "NÖTR", "#FFFF00", "Veri alınamadı"

# --- TEMEL ANALİZ ---

@st.cache_data(ttl=600)
def get_fundamental_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        book_value = info.get('bookValue', 0)
        price_to_book = info.get('priceToBook', 0)
        roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
        revenue = info.get('totalRevenue', 0)
        profit_margin = info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
        
        return {
            'book_value': book_value,
            'price_to_book': price_to_book,
            'roe': roe,
            'revenue': revenue,
            'profit_margin': profit_margin
        }
    except:
        return {'book_value': 0, 'price_to_book': 0, 'roe': 0, 'revenue': 0, 'profit_margin': 0}

def calculate_indicators(data):
    close = data['Close']
    high = data['High']
    low = data['Low']
    volume = data['Volume']
    
    ema_9 = close.ewm(span=9).mean().iloc[-1]
    ema_21 = close.ewm(span=21).mean().iloc[-1]
    ema_50 = close.ewm(span=50).mean().iloc[-1]
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1]
    
    ema_12 = close.ewm(span=12).mean()
    ema_26 = close.ewm(span=26).mean()
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9).mean()
    macd_val = macd.iloc[-1]
    signal_val = signal.iloc[-1]
    
    sma = close.rolling(20).mean()
    std = close.rolling(20).std()
    bb_upper = (sma + 2*std).iloc[-1]
    bb_lower = (sma - 2*std).iloc[-1]
    
    avg_volume = volume.rolling(20).mean().iloc[-1]
    current_volume = volume.iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
    
    tr = pd.DataFrame()
    tr['h-l'] = high - low
    tr['h-pc'] = abs(high - close.shift(1))
    tr['l-pc'] = abs(low - close.shift(1))
    tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr['tr'].rolling(14).mean().iloc[-1]
    
    return {
        'ema_9': ema_9,
        'ema_21': ema_21,
        'ema_50': ema_50,
        'rsi': rsi_val,
        'macd': macd_val,
        'signal': signal_val,
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'volume_ratio': volume_ratio,
        'atr': atr,
        'current_price': close.iloc[-1]
    }

# --- KALİTE SKORU HESAPLAMA (EN İYİ HİSSE BELİRLEME) ---

def calculate_quality_score(result, category_type):
    """
    Hisse kalite skoru hesapla (0-100)
    En iyi hisseleri belirlemek için
    """
    score = 0
    
    # 1. Güven seviyesi (Max 30 puan)
    if category_type == 'GÜN İÇİ':
        day_score = result.get('day_score', 0)
        if day_score >= 8:
            score += 30
        elif day_score >= 6:
            score += 25
        elif day_score >= 4:
            score += 20
    elif category_type == '1 HAFTALIK':
        week_score = result.get('week_score', 0)
        if week_score >= 8:
            score += 30
        elif week_score >= 6:
            score += 25
        elif week_score >= 5:
            score += 20
    elif category_type == '1 AYLIK':
        month_score = result.get('month_score', 0)
        if month_score >= 10:
            score += 30
        elif month_score >= 8:
            score += 25
        elif month_score >= 6:
            score += 20
    
    # 2. Haber Sentiment (Max 25 puan)
    if result['news_sentiment'] == 'POZİTİF':
        score += 25
    elif result['news_sentiment'] == 'NÖTR':
        score += 10
    
    # 3. Pozitif Haber Sayısı (Max 15 puan)
    if result['positive_news'] >= 3:
        score += 15
    elif result['positive_news'] >= 1:
        score += 10
    
    # 4. Teknik İndikatörler (Max 20 puan)
    tech = result.get('technical', {})
    if tech.get('rsi', 50) < 40:
        score += 10  # Aşırı satım bölgesi
    if tech.get('volume_ratio', 1) > 1.5:
        score += 10  # Yüksek hacim
    
    # 5. Temel Analiz (Max 10 puan)
    fund = result.get('fundamental', {})
    if fund.get('roe', 0) > 20:
        score += 5
    if fund.get('price_to_book', 99) < 2:
        score += 5
    
    return score

# --- ANA ANALİZ FONKSİYONU ---

def analyze_with_news(ticker):
    try:
        data = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if len(data) < 30:
            return None
        
        fundamental = get_fundamental_data(ticker)
        technical = calculate_indicators(data)
        
        # HABER ANALİZİ
        news_list = get_stock_news(ticker, limit=10)
        
        news_sentiment_score = 0
        news_sentiment_label = 'NÖTR'
        positive_news_count = 0
        negative_news_count = 0
        recent_news = []
        
        for news_item in news_list:
            title = news_item['title']
            score, label = analyze_sentiment(title)
            
            news_item['sentiment_score'] = score
            news_item['sentiment_label'] = label
            recent_news.append(news_item)
            
            hours_ago = (datetime.now() - news_item['published']).total_seconds() / 3600
            if hours_ago < 72:
                weight = 2 if hours_ago < 24 else 1
                news_sentiment_score += score * weight
                
                if label == 'POZİTİF':
                    positive_news_count += 1
                elif label == 'NEGATİF':
                    negative_news_count += 1
        
        if news_list:
            news_sentiment_score = news_sentiment_score / len(news_list)
        
        if news_sentiment_score >= 15:
            news_sentiment_label = 'POZİTİF'
        elif news_sentiment_score <= -15:
            news_sentiment_label = 'NEGATİF'
        else:
            news_sentiment_label = 'NÖTR'
        
        current_price = technical['current_price']
        atr = technical['atr']
        
        # --- SKORLAMA ---
        day_score = 0
        week_score = 0
        month_score = 0
        
        if technical['rsi'] < 35:
            day_score += 3
        elif technical['rsi'] > 65:
            day_score -= 3
        
        if technical['macd'] > technical['signal']:
            day_score += 2
        else:
            day_score -= 2
        
        if technical['volume_ratio'] > 1.5:
            day_score += 2
        
        if current_price > technical['ema_9'] > technical['ema_21']:
            week_score += 3
        elif current_price < technical['ema_9'] < technical['ema_21']:
            week_score -= 3
        
        if current_price > technical['ema_50']:
            week_score += 2
        
        if fundamental['price_to_book'] < 2 and fundamental['price_to_book'] > 0:
            month_score += 3
        
        if fundamental['roe'] > 15:
            month_score += 3
        
        if fundamental['profit_margin'] > 10:
            month_score += 2
        
        # HABER SKORU
        news_impact = news_sentiment_score / 10
        
        day_score += news_impact * 0.5
        week_score += news_impact * 0.7
        month_score += news_impact
        
        # --- HEDEF FİYATLAR ---
        day_target_up = current_price + (atr * 1.5)
        day_target_down = current_price - (atr * 1.2)
        
        week_target_up = current_price * 1.05
        week_target_down = current_price * 0.97
        
        month_target_up = current_price * 1.10
        month_target_down = current_price * 0.92
        
        # --- KATEGORİZE ETME ---
        categories = []
        
        if day_score >= 4 and technical['rsi'] < 45:
            categories.append({
                'type': 'GÜN İÇİ',
                'action': 'AL',
                'day_target': day_target_up,
                'day_change': ((day_target_up - current_price) / current_price * 100),
                'confidence': 'YÜKSEK' if day_score >= 6 else 'ORTA',
                'score': day_score
            })
        elif day_score <= -4 and technical['rsi'] > 55:
            categories.append({
                'type': 'GÜN İÇİ',
                'action': 'SAT',
                'day_target': day_target_down,
                'day_change': ((day_target_down - current_price) / current_price * 100),
                'confidence': 'YÜKSEK' if day_score <= -6 else 'ORTA',
                'score': day_score
            })
        
        if week_score >= 5:
            categories.append({
                'type': '1 HAFTALIK',
                'action': 'AL',
                'week_target': week_target_up,
                'week_change': ((week_target_up - current_price) / current_price * 100),
                'confidence': 'YÜKSEK' if week_score >= 7 else 'ORTA',
                'score': week_score
            })
        elif week_score <= -5:
            categories.append({
                'type': '1 HAFTALIK',
                'action': 'SAT',
                'week_target': week_target_down,
                'week_change': ((week_target_down - current_price) / current_price * 100),
                'confidence': 'YÜKSEK' if week_score <= -7 else 'ORTA',
                'score': week_score
            })
        
        if month_score >= 6:
            categories.append({
                'type': '1 AYLIK',
                'action': 'AL',
                'month_target': month_target_up,
                'month_change': ((month_target_up - current_price) / current_price * 100),
                'confidence': 'YÜKSEK' if month_score >= 9 else 'ORTA',
                'score': month_score
            })
        elif month_score <= -6:
            categories.append({
                'type': '1 AYLIK',
                'action': 'SAT',
                'month_target': month_target_down,
                'month_change': ((month_target_down - current_price) / current_price * 100),
                'confidence': 'YÜKSEK' if month_score <= -9 else 'ORTA',
                'score': month_score
            })
        
        return {
            'ticker': ticker,
            'price': current_price,
            'categories': categories,
            'news_sentiment': news_sentiment_label,
            'news_score': news_sentiment_score,
            'positive_news': positive_news_count,
            'negative_news': negative_news_count,
            'recent_news': recent_news[:5],
            'fundamental': fundamental,
            'technical': technical,
            'day_score': day_score,
            'week_score': week_score,
            'month_score': month_score
        }
        
    except Exception as e:
        print(f"Hata ({ticker}): {e}")
        return None

# --- BAŞLIK ---
st.title("📰 BIST 50 HABER + SENTIMENT")
st.markdown(f"<div style='color:#888; text-align:right'>Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}</div>", unsafe_allow_html=True)

# --- PİYASA SENTIMENT ---
st.subheader("🌍 GENEL PİYASA DUYGUSU")
market_sentiment, sentiment_color, market_advice = get_market_sentiment()

st.markdown(f"""
    <div class='market-box' style='background:#1a1c24; padding:15px; border-radius:8px; border:1px solid #333;'>
        <h3 style='margin:0;color:{sentiment_color}'>Piyasa Sentiment: {market_sentiment}</h3>
        <p style='margin:5px 0;color:#888'>{market_advice}</p>
    </div>
""", unsafe_allow_html=True)

st.info("📊 Arka planda: Haber + Sentiment + Defter Değeri + ROE + Teknik")

# --- ANALİZ BUTONU ---
if st.button("🎯 HABERLERİ ANALİZ ET", use_container_width=True, type="primary"):
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(BIST_50):
        status_text.text(f"Analiz: {ticker} ({i+1}/{len(BIST_50)})")
        result = analyze_with_news(ticker)
        if result and result['categories']:
            results.append(result)
        progress_bar.progress((i + 1) / len(BIST_50))
    
    progress_bar.empty()
    status_text.empty()
    
    if not results:
        st.error("❌ Sonuç bulunamadı.")
        st.stop()
    
    # KATEGORİLER
    day_trades = []
    week_trades = []
    month_trades = []
    
    for r in results:
        for cat in r['categories']:
            item = {
                'ticker': r['ticker'],
                'price': r['price'],
                'news_sentiment': r['news_sentiment'],
                'news_score': r['news_score'],
                'positive_news': r['positive_news'],
                'negative_news': r['negative_news'],
                'recent_news': r['recent_news'],
                'day_score': r['day_score'],
                'week_score': r['week_score'],
                'month_score': r['month_score'],
                'fundamental': r['fundamental'],
                'technical': r['technical'],
                **cat
            }
            
            # KALİTE SKORU HESAPLA
            item['quality_score'] = calculate_quality_score(r, cat['type'])
            
            if cat['type'] == 'GÜN İÇİ':
                day_trades.append(item)
            elif cat['type'] == '1 HAFTALIK':
                week_trades.append(item)
            elif cat['type'] == '1 AYLIK':
                month_trades.append(item)
    
    # EN İYİ HİSSELERİ BELİRLE (Kalite skoruna göre sırala)
    day_trades_sorted = sorted(day_trades, key=lambda x: x['quality_score'], reverse=True)
    week_trades_sorted = sorted(week_trades, key=lambda x: x['quality_score'], reverse=True)
    month_trades_sorted = sorted(month_trades, key=lambda x: x['quality_score'], reverse=True)
    
    # En iyi 2 hisseyi işaretle
    for i, trade in enumerate(day_trades_sorted):
        trade['is_elite'] = (i < 2 and trade['quality_score'] >= 70)
        trade['is_top'] = (i == 0 and trade['quality_score'] >= 80)
    
    for i, trade in enumerate(week_trades_sorted):
        trade['is_elite'] = (i < 2 and trade['quality_score'] >= 70)
        trade['is_top'] = (i == 0 and trade['quality_score'] >= 80)
    
    # --- 1. GÜN İÇİ ---
    st.subheader("🌅 1. GÜN İÇİ AL-SAT")
    if day_trades_sorted:
        for trade in day_trades_sorted[:6]:  # İlk 6 hisse göster
            sentiment_emoji = "🟢" if trade['news_sentiment'] == 'POZİTİF' else ("🔴" if trade['news_sentiment'] == 'NEGATİF' else "⚪")
            border_color = "#00FF00" if trade['news_sentiment'] == 'POZİTİF' else ("#FF0000" if trade['news_sentiment'] == 'NEGATİF' else "#888")
            
            change_color = "target-up" if trade['day_change'] > 0 else "target-down"
            
            # Elite/Top badge ekle
            badge = ""
            card_class = "day-trade"
            if trade.get('is_top', False):
                badge = '<span class="top-badge">🏆 TOP PICK</span>'
                card_class = "elite-trade"
                border_color = "#FFD700"
            elif trade.get('is_elite', False):
                badge = '<span class="elite-badge">⭐ ELITE</span>'
                card_class = "elite-trade"
                border_color = "#FFD700"
            
            st.markdown(f"""
                <div class='{card_class}' style='border-left: 4px solid {border_color};'>
                    <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap'>
                        <div>
                            <h3 style='margin:0;display:inline'>{trade['ticker'].replace(".IS", "")}</h3>
                            {badge}
                        </div>
                        <span style='font-size:1.5em'>{sentiment_emoji}</span>
                    </div>
                    <p style='margin:5px 0'>Fiyat: {trade['price']:.2f} ₺</p>
                    <p style='margin:5px 0'>Hedef: <span class='{change_color}'>{trade['day_target']:.2f} ₺ ({trade['day_change']:+.2f}%)</span></p>
                    <p style='margin:5px 0;color:#888'>Haber: {trade['positive_news']} pozitif, {trade['negative_news']} negatif</p>
                    <p style='margin:5px 0;color:#888'>Güven: {trade['confidence']} | Kalite Skoru: {trade['quality_score']}/100</p>
                    <p style='margin:5px 0;font-size:0.9em'>{trade['action']}</p>
                </div>
            """, unsafe_allow_html=True)
        
        # Tüm gün içi tablosu
        st.markdown("### Tüm Gün İçi Sinyaller")
        day_df = pd.DataFrame([{
            "Hisse": t['ticker'].replace(".IS", ""),
            "Fiyat": f"{t['price']:.2f}",
            "Hedef": f"{t['day_target']:.2f}",
            "Beklenti": f"{t['day_change']:+.2f}%",
            "Kalite": f"{t['quality_score']}/100",
            "Haber": f"+{t['positive_news']}/-{t['negative_news']}",
            "Sentiment": t['news_sentiment'],
            "Güven": t['confidence'],
            "Özel": "🏆 TOP" if t.get('is_top') else ("⭐ ELITE" if t.get('is_elite') else "-")
        } for t in day_trades_sorted])
        st.dataframe(day_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Bugün için uygun gün içi işlem bulunamadı.")
    
    st.markdown("---")
    
    # --- 2. HAFTALIK ---
    st.subheader("📅 2. 1 HAFTALIK")
    if week_trades_sorted:
        for trade in week_trades_sorted[:6]:
            sentiment_emoji = "🟢" if trade['news_sentiment'] == 'POZİTİF' else ("🔴" if trade['news_sentiment'] == 'NEGATİF' else "⚪")
            border_color = "#00FF00" if trade['news_sentiment'] == 'POZİTİF' else ("#FF0000" if trade['news_sentiment'] == 'NEGATİF' else "#888")
            
            change_color = "target-up" if trade['week_change'] > 0 else "target-down"
            
            badge = ""
            card_class = "week-trade"
            if trade.get('is_top', False):
                badge = '<span class="top-badge">🏆 TOP PICK</span>'
                card_class = "elite-trade"
                border_color = "#FFD700"
            elif trade.get('is_elite', False):
                badge = '<span class="elite-badge">⭐ ELITE</span>'
                card_class = "elite-trade"
                border_color = "#FFD700"
            
            st.markdown(f"""
                <div class='{card_class}' style='border-left: 4px solid {border_color};'>
                    <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap'>
                        <div>
                            <h3 style='margin:0;display:inline'>{trade['ticker'].replace(".IS", "")}</h3>
                            {badge}
                        </div>
                        <span style='font-size:1.5em'>{sentiment_emoji}</span>
                    </div>
                    <p style='margin:5px 0'>Fiyat: {trade['price']:.2f} ₺</p>
                    <p style='margin:5px 0'>Hedef: <span class='{change_color}'>{trade['week_target']:.2f} ₺ ({trade['week_change']:+.2f}%)</span></p>
                    <p style='margin:5px 0;color:#888'>Haber: {trade['positive_news']} pozitif, {trade['negative_news']} negatif</p>
                    <p style='margin:5px 0;color:#888'>Güven: {trade['confidence']} | Kalite Skoru: {trade['quality_score']}/100</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Tüm Haftalık Sinyaller")
        week_df = pd.DataFrame([{
            "Hisse": t['ticker'].replace(".IS", ""),
            "Fiyat": f"{t['price']:.2f}",
            "Hedef": f"{t['week_target']:.2f}",
            "Beklenti": f"{t['week_change']:+.2f}%",
            "Kalite": f"{t['quality_score']}/100",
            "Haber": f"+{t['positive_news']}/-{t['negative_news']}",
            "Sentiment": t['news_sentiment'],
            "Güven": t['confidence'],
            "Özel": "🏆 TOP" if t.get('is_top') else ("⭐ ELITE" if t.get('is_elite') else "-")
        } for t in week_trades_sorted])
        st.dataframe(week_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Bu hafta için uygun işlem bulunamadı.")
    
    st.markdown("---")
    
    # --- 3. AYLIK ---
    st.subheader("📆 3. 1 AYLIK")
    if month_trades_sorted:
        for trade in month_trades_sorted[:6]:
            sentiment_emoji = "🟢" if trade['news_sentiment'] == 'POZİTİF' else ("🔴" if trade['news_sentiment'] == 'NEGATİF' else "⚪")
            border_color = "#00FF00" if trade['news_sentiment'] == 'POZİTİF' else ("#FF0000" if trade['news_sentiment'] == 'NEGATİF' else "#888")
            
            change_color = "target-up" if trade['month_change'] > 0 else "target-down"
            
            st.markdown(f"""
                <div class='month-trade' style='border-left: 4px solid {border_color};'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <h3 style='margin:0'>{trade['ticker'].replace(".IS", "")}</h3>
                        <span style='font-size:1.5em'>{sentiment_emoji}</span>
                    </div>
                    <p style='margin:5px 0'>Fiyat: {trade['price']:.2f} ₺</p>
                    <p style='margin:5px 0'>Hedef: <span class='{change_color}'>{trade['month_target']:.2f} ₺ ({trade['month_change']:+.2f}%)</span></p>
                    <p style='margin:5px 0;color:#888'>Haber: {trade['positive_news']} pozitif, {trade['negative_news']} negatif</p>
                    <p style='margin:5px 0;color:#888'>Güven: {trade['confidence']} | Kalite: {trade['quality_score']}/100</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### Tüm Aylık Sinyaller")
        month_df = pd.DataFrame([{
            "Hisse": t['ticker'].replace(".IS", ""),
            "Fiyat": f"{t['price']:.2f}",
            "Hedef": f"{t['month_target']:.2f}",
            "Beklenti": f"{t['month_change']:+.2f}%",
            "Kalite": f"{t['quality_score']}/100",
            "Haber": f"+{t['positive_news']}/-{t['negative_news']}",
            "Sentiment": t['news_sentiment'],
            "Güven": t['confidence']
        } for t in month_trades_sorted])
        st.dataframe(month_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Bu ay için uygun işlem bulunamadı.")
    
    # --- HABER DETAYLARI ---
    st.markdown("---")
    st.subheader("📰 SON HABERLER")
    
    selected_ticker = st.selectbox("Haberleri Gör", [r['ticker'].replace('.IS', '') for r in results])
    
    if selected_ticker:
        selected = next((r for r in results if r['ticker'] == selected_ticker+'.IS'), None)
        if selected and selected['recent_news']:
            st.markdown(f"### {selected_ticker} Son Haberleri")
            for news in selected['recent_news']:
                sentiment_emoji = "🟢" if news['sentiment_label'] == 'POZİTİF' else ("🔴" if news['sentiment_label'] == 'NEGATİF' else "⚪")
                border = "#00FF00" if news["sentiment_label"]=="POZİTİF" else ("#FF0000" if news["sentiment_label"]=="NEGATİF" else "#888")
                st.markdown(f"""
                    <div style='background:#1a1c24;padding:10px;border-radius:8px;margin:8px 0;border-left:3px solid {border}'>
                        <p style='margin:0'><b>{sentiment_emoji} {news['title']}</b></p>
                        <p style='margin:5px 0 0 0;font-size:0.85em;color:#888'>{news['publisher']} | {news['published'].strftime("%d.%m.%Y %H:%M")}</p>
                    </div>
                """, unsafe_allow_html=True)
    
    # --- ÖZET ---
    st.markdown("---")
    st.subheader("📊 ÖZET")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Gün İçi Sinyal", len(day_trades))
    with col2:
        st.metric("Haftalık Sinyal", len(week_trades))
    with col3:
        st.metric("Aylık Sinyal", len(month_trades))
    with col4:
        elite_count = len([t for t in day_trades_sorted + week_trades_sorted if t.get('is_elite', False)])
        st.metric("Elite/Top", elite_count)

else:
    st.info("👆 Butona tıklayarak haber analizi başlatın. 3-4 dakika sürer.")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<center>
    <small style='color:#888'>⚠️ Yatırım tavsiyesi değildir.</small><br>
    <small style='color:#888'>🏆 TOP PICK = En iyi sinyal (Kalite ≥80) | ⭐ ELITE = Çok iyi sinyal (Kalite ≥70)</small><br>
    <small style='color:#888'>Yahoo Finance haberleri + Türkçe sentiment + Temel/Teknik analiz</small><br>
    <small style='color:#888'>© 2024 BIST 50 HABER + SENTIMENT</small>
</center>
""", unsafe_allow_html=True)
