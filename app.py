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
    .day-trade { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
    .week-trade { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
    .month-trade { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #333; }
    .elite-trade { background: linear-gradient(135deg, #1a1c24 0%, #2d3a2d 100%); padding: 15px; border-radius: 8px; margin: 10px 0; border: 2px solid #FFD700; box-shadow: 0 0 15px rgba(255, 215, 0, 0.3); }
    .news-positive { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #00FF00; }
    .news-negative { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #FF0000; }
    .news-neutral { background: #1a1c24; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #888888; }
    .target-up { color: #00FF00; font-weight: bold; font-size: 1.2em; }
    .target-down { color: #FF0000; font-weight: bold; font-size: 1.2em; }
    .elite-badge { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); color: #000; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 0.85em; display: inline-block; margin-left: 10px; box-shadow: 0 0 10px rgba(255, 215, 0, 0.5); }
    .top-badge { background: linear-gradient(135deg, #FF6B6B 0%, #C44569 100%); color: #fff; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 0.85em; display: inline-block; margin-left: 10px; box-shadow: 0 0 10px rgba(255, 107, 107, 0.5); }
    div[data-testid="stDataFrame"] { background: #1a1c24; }
    div[data-testid="stDataFrame"] tr { background-color: #1a1c24; color: #ffffff; }
    div[data-testid="stDataFrame"] th { background-color: #0e1117; color: #ffffff; border: 1px solid #333; }
    .stButton > button { background: #1a1c24; color: #ffffff; border: 1px solid #333; border-radius: 8px; }
    .stButton > button:hover { background: #2a2d35; border: 1px solid #555; }
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
POSITIVE_WORDS = ['kar', 'büyüme', 'artış', 'yükseliş', 'rekor', 'başarı', 'temettü', 'kazanç', 'fırsat', 'güçlü', 'yatırım', 'profit', 'growth', 'success', 'positive', 'gain']
NEGATIVE_WORDS = ['zarar', 'düşüş', 'kayıp', 'risk', 'kriz', 'sorun', 'negatif', 'zayıf', 'dava', 'loss', 'decline', 'risk', 'negative', 'crisis']

MARKET_IMPACT_WORDS = {'temettü': 3, 'rekor': 3, 'kriz': 3, 'büyüme': 2, 'zarar': 2, 'yatırım': 1}

# --- FONKSİYONLAR ---

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
                'link': item.get('link', '')
            }
            news_list.append(news_item)
        return news_list
    except:
        return []

def analyze_sentiment(text):
    if not text:
        return 0, 'NÖTR'
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    positive_count = sum(1 for word in words if word in POSITIVE_WORDS)
    negative_count = sum(1 for word in words if word in NEGATIVE_WORDS)
    impact_score = 0
    for word in words:
        if word in POSITIVE_WORDS:
            impact_score += MARKET_IMPACT_WORDS.get(word, 1)
        elif word in NEGATIVE_WORDS:
            impact_score -= MARKET_IMPACT_WORDS.get(word, 1)
    total = positive_count + negative_count
    if total == 0:
        return 0, 'NÖTR'
    score = (impact_score / total) * 50
    score = max(-100, min(100, score))
    if score >= 20:
        return score, 'POZİTİF'
    elif score <= -20:
        return score, 'NEGATİF'
    return score, 'NÖTR'

def get_market_sentiment():
    try:
        bist = yf.Ticker("^XU100")
        news = bist.news[:5] if bist.news else []
        total = sum(analyze_sentiment(item.get('title', ''))[0] for item in news)
        avg = total / len(news) if news else 0
        if avg >= 15:
            return "POZİTİF", "#00FF00", "Piyasa iyimser"
        elif avg <= -15:
            return "NEGATİF", "#FF0000", "Piyasa kötümser"
        return "NÖTR", "#FFFF00", "Piyasa dengeli"
    except:
        return "NÖTR", "#FFFF00", "Veri yok"

@st.cache_data(ttl=600)
def get_fundamental_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'book_value': info.get('bookValue', 0),
            'price_to_book': info.get('priceToBook', 0),
            'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
            'profit_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0
        }
    except:
        return {'book_value': 0, 'price_to_book': 0, 'roe': 0, 'profit_margin': 0}

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
    rsi = (100 - (100 / (1 + rs))).iloc[-1]
    
    ema_12 = close.ewm(span=12).mean()
    ema_26 = close.ewm(span=26).mean()
    macd = (ema_12 - ema_26).iloc[-1]
    signal = (ema_12 - ema_26).ewm(span=9).mean().iloc[-1]
    
    sma = close.rolling(20).mean()
    std = close.rolling(20).std()
    bb_upper = (sma + 2*std).iloc[-1]
    bb_lower = (sma - 2*std).iloc[-1]
    
    avg_vol = volume.rolling(20).mean().iloc[-1]
    vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 1
    
    tr = pd.DataFrame()
    tr['h-l'] = high - low
    tr['h-pc'] = abs(high - close.shift(1))
    tr['l-pc'] = abs(low - close.shift(1))
    tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    atr = tr['tr'].rolling(14).mean().iloc[-1]
    
    return {
        'ema_9': ema_9, 'ema_21': ema_21, 'ema_50': ema_50,
        'rsi': rsi, 'macd': macd, 'signal': signal,
        'bb_upper': bb_upper, 'bb_lower': bb_lower,
        'volume_ratio': vol_ratio, 'atr': atr,
        'current_price': close.iloc[-1]
    }

def calculate_quality_score(result, cat_type):
    score = 0
    if cat_type == 'GÜN İÇİ':
        s = result.get('day_score', 0)
        if s >= 8: score += 30
        elif s >= 6: score += 25
        elif s >= 4: score += 20
    elif cat_type == '1 HAFTALIK':
        s = result.get('week_score', 0)
        if s >= 8: score += 30
        elif s >= 6: score += 25
        elif s >= 5: score += 20
    elif cat_type == '1 AYLIK':
        s = result.get('month_score', 0)
        if s >= 10: score += 30
        elif s >= 8: score += 25
        elif s >= 6: score += 20
    
    if result['news_sentiment'] == 'POZİTİF': score += 25
    elif result['news_sentiment'] == 'NÖTR': score += 10
    
    if result['positive_news'] >= 3: score += 15
    elif result['positive_news'] >= 1: score += 10
    
    tech = result.get('technical', {})
    if tech.get('rsi', 50) < 40: score += 10
    if tech.get('volume_ratio', 1) > 1.5: score += 10
    
    fund = result.get('fundamental', {})
    if fund.get('roe', 0) > 20: score += 5
    if fund.get('price_to_book', 99) < 2: score += 5
    
    return score

def analyze_with_news(ticker):
    try:
        data = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if len(data) < 30:
            return None
        
        fundamental = get_fundamental_data(ticker)
        technical = calculate_indicators(data)
        news_list = get_stock_news(ticker, limit=10)
        
        news_score = 0
        news_label = 'NÖTR'
        pos_count = 0
        neg_count = 0
        recent_news = []
        
        for item in news_list:
            score, label = analyze_sentiment(item['title'])
            item['sentiment_score'] = score
            item['sentiment_label'] = label
            recent_news.append(item)
            
            hours = (datetime.now() - item['published']).total_seconds() / 3600
            if hours < 72:
                weight = 2 if hours < 24 else 1
                news_score += score * weight
                if label == 'POZİTİF': pos_count += 1
                elif label == 'NEGATIF': neg_count += 1
        
        if news_list:
            news_score = news_score / len(news_list)
        
        if news_score >= 15: news_label = 'POZİTİF'
        elif news_score <= -15: news_label = 'NEGATİF'
        
        price = technical['current_price']
        atr = technical['atr']
        
        # Skorlar
        day_score = 0
        week_score = 0
        month_score = 0
        
        if technical['rsi'] < 35: day_score += 3
        elif technical['rsi'] > 65: day_score -= 3
        
        if technical['macd'] > technical['signal']: day_score += 2
        else: day_score -= 2
        
        if technical['volume_ratio'] > 1.5: day_score += 2
        
        if price > technical['ema_9'] > technical['ema_21']: week_score += 3
        elif price < technical['ema_9'] < technical['ema_21']: week_score -= 3
        
        if price > technical['ema_50']: week_score += 2
        
        if 0 < fundamental['price_to_book'] < 2: month_score += 3
        if fundamental['roe'] > 15: month_score += 3
        if fundamental['profit_margin'] > 10: month_score += 2
        
        news_impact = news_score / 10
        day_score += news_impact * 0.5
        week_score += news_impact * 0.7
        month_score += news_impact
        
        # Hedefler
        day_target = price + (atr * 1.5)
        week_target = price * 1.05
        month_target = price * 1.10
        
        categories = []
        
        if day_score >= 4 and technical['rsi'] < 45:
            categories.append({
                'type': 'GÜN İÇİ', 'action': 'AL',
                'target': day_target, 'change': ((day_target - price) / price * 100),
                'confidence': 'YÜKSEK' if day_score >= 6 else 'ORTA', 'score': day_score
            })
        elif day_score <= -4 and technical['rsi'] > 55:
            categories.append({
                'type': 'GÜN İÇİ', 'action': 'SAT',
                'target': price - (atr * 1.2), 'change': ((price - (atr * 1.2) - price) / price * 100),
                'confidence': 'YÜKSEK' if day_score <= -6 else 'ORTA', 'score': day_score
            })
        
        if week_score >= 5:
            categories.append({
                'type': '1 HAFTALIK', 'action': 'AL',
                'target': week_target, 'change': ((week_target - price) / price * 100),
                'confidence': 'YÜKSEK' if week_score >= 7 else 'ORTA', 'score': week_score
            })
        elif week_score <= -5:
            categories.append({
                'type': '1 HAFTALIK', 'action': 'SAT',
                'target': price * 0.97, 'change': ((price * 0.97 - price) / price * 100),
                'confidence': 'YÜKSEK' if week_score <= -7 else 'ORTA', 'score': week_score
            })
        
        if month_score >= 6:
            categories.append({
                'type': '1 AYLIK', 'action': 'AL',
                'target': month_target, 'change': ((month_target - price) / price * 100),
                'confidence': 'YÜKSEK' if month_score >= 9 else 'ORTA', 'score': month_score
            })
        elif month_score <= -6:
            categories.append({
                'type': '1 AYLIK', 'action': 'SAT',
                'target': price * 0.92, 'change': ((price * 0.92 - price) / price * 100),
                'confidence': 'YÜKSEK' if month_score <= -9 else 'ORTA', 'score': month_score
            })
        
        return {
            'ticker': ticker, 'price': price, 'categories': categories,
            'news_sentiment': news_label, 'news_score': news_score,
            'positive_news': pos_count, 'negative_news': neg_count,
            'recent_news': recent_news[:5], 'fundamental': fundamental,
            'technical': technical, 'day_score': day_score,
            'week_score': week_score, 'month_score': month_score
        }
    except Exception as e:
        print(f"Hata ({ticker}): {e}")
        return None

# --- ANA PROGRAM ---
st.title("📰 BIST 50 HABER + SENTIMENT")
st.markdown(f"<div style='color:#888; text-align:right'>Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}</div>", unsafe_allow_html=True)

st.subheader("🌍 GENEL PİYASA DUYGUSU")
mkt_sent, mkt_color, mkt_advice = get_market_sentiment()
st.markdown(f"""
    <div style='background:#1a1c24; padding:15px; border-radius:8px; border:1px solid #333;'>
        <h3 style='margin:0;color:{mkt_color}'>Piyasa: {mkt_sent}</h3>
        <p style='margin:5px 0;color:#888'>{mkt_advice}</p>
    </div>
    """, unsafe_allow_html=True)

st.info("📊 Arka planda: Haber + Sentiment + Temel + Teknik analiz")

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
    
    # Kategorilere ayır
    day_trades = []
    week_trades = []
    month_trades = []
    
    for r in results:
        for cat in r['categories']:
            item = {
                'ticker': r['ticker'], 'price': r['price'],
                'news_sentiment': r['news_sentiment'],
                'positive_news': r['positive_news'],
                'negative_news': r['negative_news'],
                'day_score': r['day_score'], 'week_score': r['week_score'],
                'month_score': r['month_score'],
                'fundamental': r['fundamental'], 'technical': r['technical'],
                **cat
            }
            item['quality_score'] = calculate_quality_score(r, cat['type'])
            
            if cat['type'] == 'GÜN İÇİ':
                day_trades.append(item)
            elif cat['type'] == '1 HAFTALIK':
                week_trades.append(item)
            elif cat['type'] == '1 AYLIK':
                month_trades.append(item)
    
    # Sırala ve işaretle
    day_trades = sorted(day_trades, key=lambda x: x['quality_score'], reverse=True)
    week_trades = sorted(week_trades, key=lambda x: x['quality_score'], reverse=True)
    
    for i, t in enumerate(day_trades):
        t['is_top'] = (i == 0 and t['quality_score'] >= 80)
        t['is_elite'] = (i < 2 and t['quality_score'] >= 70)
    
    for i, t in enumerate(week_trades):
        t['is_top'] = (i == 0 and t['quality_score'] >= 80)
        t['is_elite'] = (i < 2 and t['quality_score'] >= 70)
    
    # GÜN İÇİ
    st.subheader("🌅 GÜN İÇİ AL-SAT")
    if day_trades:
        for trade in day_trades[:6]:
            emoji = "🟢" if trade['news_sentiment'] == 'POZİTİF' else ("🔴" if trade['news_sentiment'] == 'NEGATİF' else "⚪")
            border = "#00FF00" if trade['news_sentiment'] == 'POZİTİF' else ("#FF0000" if trade['news_sentiment'] == 'NEGATİF' else "#888")
            color = "target-up" if trade['change'] > 0 else "target-down"
            
            badge = ""
            card_class = "day-trade"
            if trade.get('is_top'):
                badge = "🏆 TOP PICK"
                card_class = "elite-trade"
                border = "#FFD700"
            elif trade.get('is_elite'):
                badge = "⭐ ELITE"
                card_class = "elite-trade"
                border = "#FFD700"
            
            html = f"""
                <div class='{card_class}' style='border-left: 4px solid {border};'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <div>
                            <h3 style='margin:0;display:inline'>{trade['ticker'].replace(".IS", "")}</h3>
                            {f'<span class="top-badge">{badge}</span>' if badge else ''}
                        </div>
                        <span style='font-size:1.5em'>{emoji}</span>
                    </div>
                    <p style='margin:5px 0'><b>Fiyat:</b> {trade['price']:.2f} ₺</p>
                    <p style='margin:5px 0'><b>Hedef:</b> <span class='{color}'>{trade['target']:.2f} ₺ ({trade['change']:+.2f}%)</span></p>
                    <p style='margin:5px 0;color:#888'><b>Haber:</b> {trade['positive_news']} pozitif, {trade['negative_news']} negatif</p>
                    <p style='margin:5px 0;color:#888'><b>Güven:</b> {trade['confidence']} | <b>Kalite:</b> {trade['quality_score']}/100</p>
                    <p style='margin:5px 0;font-size:0.9em'>{trade['action']}</p>
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)
        
        # Tablo
        st.markdown("### Tüm Gün İçi Sinyaller")
        day_df = pd.DataFrame([{
            "Hisse": t['ticker'].replace(".IS", ""),
            "Fiyat": f"{t['price']:.2f}",
            "Hedef": f"{t['target']:.2f}",
            "Beklenti": f"{t['change']:+.2f}%",
            "Kalite": f"{t['quality_score']}/100",
            "Haber": f"+{t['positive_news']}/-{t['negative_news']}",
            "Sentiment": t['news_sentiment'],
            "Güven": t['confidence'],
            "Özel": "🏆 TOP" if t.get('is_top') else ("⭐ ELITE" if t.get('is_elite') else "-")
        } for t in day_trades])
        st.dataframe(day_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Bugün için uygun işlem bulunamadı.")
    
    st.markdown("---")
    
    # HAFTALIK
    st.subheader("📅 HAFTALIK")
    if week_trades:
        for trade in week_trades[:6]:
            emoji = "🟢" if trade['news_sentiment'] == 'POZİTİF' else ("🔴" if trade['news_sentiment'] == 'NEGATİF' else "⚪")
            border = "#00FF00" if trade['news_sentiment'] == 'POZİTİF' else ("#FF0000" if trade['news_sentiment'] == 'NEGATİF' else "#888")
            color = "target-up" if trade['change'] > 0 else "target-down"
            
            badge = ""
            card_class = "week-trade"
            if trade.get('is_top'):
                badge = "🏆 TOP PICK"
                card_class = "elite-trade"
                border = "#FFD700"
            elif trade.get('is_elite'):
                badge = "⭐ ELITE"
                card_class = "elite-trade"
                border = "#FFD700"
            
            html = f"""
                <div class='{card_class}' style='border-left: 4px solid {border};'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <div>
                            <h3 style='margin:0;display:inline'>{trade['ticker'].replace(".IS", "")}</h3>
                            {f'<span class="top-badge">{badge}</span>' if badge else ''}
                        </div>
                        <span style='font-size:1.5em'>{emoji}</span>
                    </div>
                    <p style='margin:5px 0'><b>Fiyat:</b> {trade['price']:.2f} ₺</p>
                    <p style='margin:5px 0'><b>Hedef:</b> <span class='{color}'>{trade['target']:.2f} ₺ ({trade['change']:+.2f}%)</span></p>
                    <p style='margin:5px 0;color:#888'><b>Haber:</b> {trade['positive_news']} pozitif, {trade['negative_news']} negatif</p>
                    <p style='margin:5px 0;color:#888'><b>Güven:</b> {trade['confidence']} | <b>Kalite:</b> {trade['quality_score']}/100</p>
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)
        
        st.markdown("### Tüm Haftalık Sinyaller")
        week_df = pd.DataFrame([{
            "Hisse": t['ticker'].replace(".IS", ""),
            "Fiyat": f"{t['price']:.2f}",
            "Hedef": f"{t['target']:.2f}",
            "Beklenti": f"{t['change']:+.2f}%",
            "Kalite": f"{t['quality_score']}/100",
            "Haber": f"+{t['positive_news']}/-{t['negative_news']}",
            "Sentiment": t['news_sentiment'],
            "Güven": t['confidence'],
            "Özel": "🏆 TOP" if t.get('is_top') else ("⭐ ELITE" if t.get('is_elite') else "-")
        } for t in week_trades])
        st.dataframe(week_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Bu hafta için uygun işlem bulunamadı.")
    
    st.markdown("---")
    
    # AYLIK
    st.subheader("📆 AYLIK")
    if month_trades:
        for trade in month_trades[:6]:
            emoji = "🟢" if trade['news_sentiment'] == 'POZİTİF' else ("🔴" if trade['news_sentiment'] == 'NEGATİF' else "⚪")
            border = "#00FF00" if trade['news_sentiment'] == 'POZİTİF' else ("#FF0000" if trade['news_sentiment'] == 'NEGATİF' else "#888")
            color = "target-up" if trade['change'] > 0 else "target-down"
            
            html = f"""
                <div class='month-trade' style='border-left: 4px solid {border};'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                        <h3 style='margin:0'>{trade['ticker'].replace(".IS", "")}</h3>
                        <span style='font-size:1.5em'>{emoji}</span>
                    </div>
                    <p style='margin:5px 0'><b>Fiyat:</b> {trade['price']:.2f} ₺</p>
                    <p style='margin:5px 0'><b>Hedef:</b> <span class='{color}'>{trade['target']:.2f} ₺ ({trade['change']:+.2f}%)</span></p>
                    <p style='margin:5px 0;color:#888'><b>Haber:</b> {trade['positive_news']} pozitif, {trade['negative_news']} negatif</p>
                    <p style='margin:5px 0;color:#888'><b>Güven:</b> {trade['confidence']} | <b>Kalite:</b> {trade['quality_score']}/100</p>
                </div>
            """
            st.markdown(html, unsafe_allow_html=True)
        
        st.markdown("### Tüm Aylık Sinyaller")
        month_df = pd.DataFrame([{
            "Hisse": t['ticker'].replace(".IS", ""),
            "Fiyat": f"{t['price']:.2f}",
            "Hedef": f"{t['target']:.2f}",
            "Beklenti": f"{t['change']:+.2f}%",
            "Kalite": f"{t['quality_score']}/100",
            "Haber": f"+{t['positive_news']}/-{t['negative_news']}",
            "Sentiment": t['news_sentiment'],
            "Güven": t['confidence']
        } for t in month_trades])
        st.dataframe(month_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Bu ay için uygun işlem bulunamadı.")
    
    # ÖZET
    st.markdown("---")
    st.subheader("📊 ÖZET")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Gün İçi", len(day_trades))
    with c2:
        st.metric("Haftalık", len(week_trades))
    with c3:
        st.metric("Aylık", len(month_trades))

else:
    st.info("👆 Butona tıklayarak analiz başlatın. 3-4 dakika sürer.")

st.markdown("---")
st.markdown("<center><small style='color:#888'>⚠️ Yatırım tavsiyesi değildir.</small></center>", unsafe_allow_html=True)
