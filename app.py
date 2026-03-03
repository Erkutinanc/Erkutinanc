import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import datetime

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BIST 50 Shadow Elite Pro", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: #0e1117; color: #ffffff; }
    .stDataFrame { color: #ffffff; }
    .update-text { color: #888888; font-size: 0.8rem !important; text-align: right; margin-bottom: 10px; }
    .radar-box {
        background: linear-gradient(90deg, #1a1c24 0%, #0e4b2a 100%);
        border-left: 5px solid #00FF00; padding: 12px; border-radius: 8px; margin-bottom: 15px;
    }
    .sentiment-box {
        background: #1e212b; border: 1px solid #444; padding: 12px; border-radius: 8px; margin-bottom: 20px;
    }
    /* Tablo renkleri */
    div[data-testid="stDataFrame"] tr { background-color: #1a1c24; color: #ffffff; }
    div[data-testid="stDataFrame"] th { background-color: #0e1117; color: #00FF00; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. VERİ YAPILARI (BIST 50) ---

# Güncel BIST 50 Temsilci Hisseler (.IS uzantısı ile)
BIST_50_TICKERS = [
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

# Genişletilmiş Sektör Haritası
SECTORS = {
    "Bankacılık": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "HALKB.IS", "YKBNK.IS", "VAKBN.IS", "TSKB.IS"],
    "Havacılık & Ulaşım": ["THYAO.IS", "PGSUS.IS", "SAHOL.IS", "TTRAK.IS"],
    "Otomotiv": ["FROTO.IS", "TOASO.IS", "ARCLK.IS", "BURCE.IS"],
    "Enerji & Petrol": ["EREGL.IS", "TUPRS.IS", "ASTOR.IS", "ENKAI.IS", "AKSEN.IS"],
    "Perakende & Gıda": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "ULKER.IS", "KARTN.IS"],
    "Holding": ["KCHOL.IS", "SAHOL.IS", "DOHOL.IS", "ZOREN.IS"],
    "Teknoloji & İletişim": ["ASELS.IS", "TCELL.IS", "LOGO.IS", "KONTR.IS", "LINK.IS"],
    "Gayrimenkul": ["EKGYO.IS", "ISGYO.IS", "ALARK.IS"],
    "Sanayi & Kimya": ["SISE.IS", "PETKM.IS", "HEKTS.IS", "NUHCM.IS", "POLHO.IS"]
}

# --- 3. YARDIMCI FONKSİYONLAR ---

@st.cache_data(ttl=600)  # 10 dakika cache (BIST 50 için veri yükünü azaltır)
def get_stock_data(tickers, period="1mo", interval="1d"):
    # Yahoo Finance bazen tek seferde çok isteği reddedebilir, gruplayabiliriz ama şimdilik tek çekim deniyoruz.
    try:
        data = yf.download(tickers, period=period, interval=interval, progress=False, threads=True)
        return data
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_info(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.info
    except:
        return {}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_shadow_signal(close_prices):
    if len(close_prices) < 14:
        return "Nötr", "#888888"
    
    rsi = calculate_rsi(close_prices).iloc[-1]
    sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
    current_price = close_prices.iloc[-1]
    
    if rsi < 30 and current_price < sma_20:
        return "GÜÇLÜ AL", "#00FF00"
    elif rsi > 70 and current_price > sma_20:
        return "GÜÇLÜ SAT", "#FF0000"
    elif current_price > sma_20:
        return "AL", "#32CD32"
    elif current_price < sma_20:
        return "SAT", "#FF4500"
    else:
        return "BEKLE", "#FFFF00"

# --- 4. ANA UYGULAMA AKIŞI ---

now = datetime.now().strftime("%d.%m.%Y %H:%M")
st.markdown(f"<div class='update-text'>Son Güncelleme: {now} | Veri Kaynağı: Yahoo Finance (BIST 50)</div>", unsafe_allow_html=True)

st.title("💎 BIST 50 Shadow Elite Pro")
st.markdown("---")

# Sekmeler
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Piyasa Özeti", "📡 Shadow Radar", "🏭 Sektörler", "📰 Gündem & Sentiment"])

# --- TAB 1: PİYASA ÖZETİ (BIST 50 TABLOSU) ---
with tab1:
    st.subheader("BIST 50 Canlı Akış & Teknik Özet")
    
    if st.button("Verileri Yenile 🔄"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner('50 Hisse Analiz Ediliyor...'):
        try:
            # Verileri Çek
            df = get_stock_data(BIST_50_TICKERS, period="1mo", interval="1d")
            
            # MultiIndex kontrolü
            if isinstance(df.columns, pd.MultiIndex):
                close_df = df['Close']
                open_df = df['Open']
            else:
                close_df = df
                open_df = df # Basitleştirilmiş

            # Özet Tablo Oluşturma
            summary_data = []
            
            for ticker in BIST_50_TICKERS:
                try:
                    if ticker in close_df.columns:
                        current_price = close_df[ticker].iloc[-1]
                        prev_price = close_df[ticker].iloc[-2] if len(close_df) > 1 else current_price
                        change = ((current_price - prev_price) / prev_price) * 100
                        
                        # Sinyal Hesaplama
                        signal, color = generate_shadow_signal(close_df[ticker])
                        
                        summary_data.append({
                            "Hisse": ticker.replace(".IS", ""),
                            "Fiyat": f"{current_price:.2f}",
                            "Değişim %": f"{change:.2f}",
                            "Sinyal": signal,
                            "Renk": color
                        })
                except Exception:
                    continue
            
            summary_df = pd.DataFrame(summary_data)
            
            # Tabloyu Renklendirme (Streamlit native styling)
            def color_change(val):
                try:
                    num = float(val.replace('%', ''))
                    color = '#00FF00' if num >= 0 else '#FF0000'
                    return f'color: {color}'
                except:
                    return ''

            def color_signal(val):
                if val == "GÜÇLÜ AL": return 'color: #00FF00; font-weight: bold;'
                if val == "GÜÇLÜ SAT": return 'color: #FF0000; font-weight: bold;'
                if val == "AL": return 'color: #32CD32;'
                if val == "SAT": return 'color: #FF4500;'
                return 'color: #FFFF00;'

            st.dataframe(
                summary_df.style.applymap(color_change, subset=["Değişim %"])
                .applymap(color_signal, subset=["Sinyal"]),
                use_container_width=True,
                hide_index=True
            )
            
        except Exception as e:
            st.error(f"Veri işleme hatası: {e}")
            st.info("Yahoo Finance yoğunluğu nedeniyle veri çekilemedi. Lütfen tekrar deneyin.")

# --- TAB 2: SHADOW RADAR ---
with tab2:
    st.subheader("📡 Derinlemesine Teknik Analiz")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_stock = st.selectbox("Hisse Seçiniz", BIST_50_TICKERS, index=0)
        analyze_btn = st.button("Radarı Tara 🔍", use_container_width=True)
    
    with col2:
        if analyze_btn:
            with st.spinner('Algoritmalar çalışıyor...'):
                time.sleep(0.5)
                hist = yf.Ticker(selected_stock).history(period="6mo")
                
                if not hist.empty:
                    signal, color = generate_shadow_signal(hist['Close'])
                    rsi_val = calculate_rsi(hist["Close"]).iloc[-1]
                    sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
                    current_price = hist["Close"].iloc[-1]
                    
                    st.markdown(f"""
                        <div class='radar-box'>
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <h3 style='margin:0; color:#fff;'>{selected_stock} Analizi</h3>
                                <h2 style='color:{color}; margin:0;'>{signal}</h2>
                            </div>
                            <hr style='border-color:#444;'>
                            <div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px;'>
                                <div>
                                    <span style='color:#aaa;'>RSI (14):</span> <b style='color:#fff;'>{rsi_val:.2f}</b>
                                </div>
                                <div>
                                    <span style='color:#aaa;'>Fiyat:</span> <b style='color:#fff;'>{current_price:.2f}</b>
                                </div>
                                <div>
                                    <span style='color:#aaa;'>Ort. (50):</span> <b style='color:#fff;'>{sma_50:.2f}</b>
                                </div>
                                <div>
                                    <span style='color:#aaa;'>Trend:</span> <b style='color:{"#00FF00" if current_price > sma_50 else "#FF0000"};'>{"Yükseliş" if current_price > sma_50 else "Düşüş"}</b>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.line_chart(hist['Close'])
                else:
                    st.warning("Veri alınamadı.")
        else:
            st.info("Analiz etmek için soldan hisse seçip 'Radarı Tara' butonuna basın.")

# --- TAB 3: SEKTÖRLER ---
with tab3:
    st.subheader("🏭 Sektör Bazlı Performans")
    
    # Sektörleri dinamik olarak buton veya selectbox ile seçilebilir yapalım
    selected_sector = st.selectbox("Sektör Seçiniz", list(SECTORS.keys()))
    
    if selected_sector:
        stocks_in_sector = SECTORS[selected_sector]
        st.write(f"**{selected_sector}** sektöründeki hisseler:")
        
        sector_data = get_stock_data(stocks_in_sector, period="3mo")
        
        if isinstance(sector_data.columns, pd.MultiIndex):
            close_sector = sector_data['Close']
        else:
            close_sector = sector_data
            
        if not close_sector.empty:
            # Normalizasyon (Başlangıç noktasını 100 kabul et)
            normalized = (close_sector / close_sector.iloc[0]) * 100
            st.line_chart(normalized)
            
            # Son durum özeti
            cols = st.columns(len(stocks_in_sector))
            for i, stock in enumerate(stocks_in_sector):
                if stock in normalized.columns:
                    perf = normalized[stock].iloc[-1] - 100
                    with cols[i % len(cols)]:
                        if perf >= 0:
                            st.success(f"{stock.replace('.IS','')} %{perf:.1f}")
                        else:
                            st.error(f"{stock.replace('.IS','')} %{perf:.1f}")

# --- TAB 4: GÜNDEM & SENTIMENT ---
with tab4:
    st.subheader("📰 Piyasa Sentiment & Gündem")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🔥 Öne Çıkan Başlıklar (Simülasyon)")
        news_data = [
            {"title": "BIST 50 Endeksi Hacim Rekoru Kırdı", "sentiment": "Pozitif", "time": "15dk önce"},
            {"title": "Yabancı Takas Oranları Yükselişte", "sentiment": "Pozitif", "time": "1saat önce"},
            {"title": "Sanayi Üretim Verileri Açıklandı", "sentiment": "Nötr", "time": "2saat önce"},
            {"title": "Teknoloji Hisselerinde Kar Satışları", "sentiment": "Negatif", "time": "3saat önce"},
            {"title": "Bankacılık Kredi Büyümesi Hedeflendi", "sentiment": "Pozitif", "time": "4saat önce"},
        ]
        
        for news in news_data:
            sentiment_color = "#00FF00" if news['sentiment'] == "Pozitif" else ("#FF0000" if news['sentiment'] == "Negatif" else "#FFFF00")
            st.markdown(f"""
                <div style='background:#1e212b; padding:10px; border-radius:5px; margin-bottom:10px; border-left: 3px solid {sentiment_color};'>
                    <b>{news['title']}</b> <span style='font-size:0.8em; color:#888;'>({news['time']})</span><br>
                    <span style='color:{sentiment_color}; font-size:0.9em;'>Sentiment: {news['sentiment']}</span>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 🧠 Genel Piyasa Duygusu")
        st.markdown("""
            <div class='sentiment-box'>
                <h4 style='color:#fff;'>Korku & Açgöz Endeksi</h4>
                <h2 style='color:#00FF00;'>Açgöz (72)</h2>
                <div style='background:#333; height:10px; border-radius:5px; margin-top:5px;'>
                    <div style='background:#00FF00; width:72%; height:100%; border-radius:5px;'></div>
                </div>
                <p style='font-size:0.8rem; color:#aaa; margin-top:10px;'>BIST 50 genelinde alım iştahı yüksek.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.warning("⚠️ Yasal Uyarı: Buradaki veriler yatırım tavsiyesi değildir.")

# --- 5. FOOTER ---
st.markdown("---")
st.markdown("<center><small>© 2023 BIST 50 Shadow Elite Pro | Veriler 15 dk gecikmeli olabilir.</small></center>", unsafe_allow_html=True)
