# Mum grafiği
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'],
    low=df['Low'], close=df['Close'], name="Fiyat"
), row=1, col=1)

# Bollinger
sma, upper, lower = calc_bollinger(df["Close"])
fig.add_trace(go.Scatter(x=df.index, y=upper, line=dict(color="gray"), name="BB Üst"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=lower, line=dict(color="gray"), name="BB Alt"), row=1, col=1)

# RSI
rsi = calc_rsi(df["Close"])
fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="orange"), name="RSI"), row=2, col=1)

# MACD
macd, signal, hist = calc_macd(df["Close"])
fig.add_trace(go.Scatter(x=df.index, y=macd, line=dict(color="cyan"), name="MACD"), row=3, col=1)
fig.add_trace(go.Scatter(x=df.index, y=signal, line=dict(color="white"), name="Signal"), row=3, col=1)
fig.add_trace(go.Bar(x=df.index, y=hist, name="Hist"), row=3, col=1)

# Stoch RSI
stoch = calc_stoch_rsi(df["Close"])
fig.add_trace(go.Scatter(x=df.index, y=stoch, line=dict(color="yellow"), name="StochRSI"), row=4, col=1)

fig.update_layout(height=900, title=f"{ticker} — Gelişmiş Grafik", template="plotly_dark")
return fig
def __init__(self):
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

def add_position(self, ticker, qty, buy_price):
    st.session_state.portfolio.append({
        "ticker": ticker,
        "qty": qty,
        "buy": buy_price,
        "added": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

def remove_position(self, index):
    if 0 <= index < len(st.session_state.portfolio):
        st.session_state.portfolio.pop(index)

def get_positions(self):
    return st.session_state.portfolio

def calculate_metrics(self):
    df_list = []
    total_value = 0
    total_cost = 0

    for pos in st.session_state.portfolio:
        ticker = pos["ticker"]
        qty = pos["qty"]
        buy = pos["buy"]

        df = fetch_yahoo(ticker, period="1mo")
        if df is None or df.empty:
            continue

        current_price = df["Close"].iloc[-1]

        value = qty * current_price
        cost = qty * buy
        pnl = value - cost
        pnl_pct = pnl / cost * 100 if cost != 0 else 0

        df_list.append({
            "Hisse": ticker,
            "Adet": qty,
            "Alış": buy,
            "Güncel": round(current_price, 2),
            "Değer": round(value, 2),
            "Maliyet": round(cost, 2),
            "Kar": round(pnl, 2),
            "Kar %": round(pnl_pct, 2)
        })

        total_value += value
        total_cost += cost

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return df_list, total_value, total_pnl, total_pnl_pct
def __init__(self):
    if "alerts" not in st.session_state:
        st.session_state.alerts = []

def add_price_alert(self, ticker, condition, target):
    st.session_state.alerts.append({
        "type": "price",
        "ticker": ticker,
        "condition": condition,
        "target": target,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

def add_rsi_alert(self, ticker, condition, level):
    st.session_state.alerts.append({
        "type": "rsi",
        "ticker": ticker,
        "condition": condition,
        "level": level,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

def add_macd_alert(self, ticker, signal_type):
    st.session_state.alerts.append({
        "type": "macd",
        "ticker": ticker,
        "signal": signal_type,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

def list_alerts(self):
    return st.session_state.alerts

def check_alerts(self):
    results = []

    for alert in st.session_state.alerts:
        ticker = alert["ticker"]
        df = fetch_yahoo(ticker, period="1mo")

        if df is None or df.empty:
            continue

        close = df["Close"].iloc[-1]
        rsi = calc_rsi(df["Close"]).iloc[-1]
        macd, signal, hist = calc_macd(df["Close"])

        # Fiyat alarmı
        if alert["type"] == "price":
            if alert["condition"] == "Üstünde" and close > alert["target"]:
                results.append(f"{ticker}: Fiyat {alert['target']} üstüne çıktı → {close}")
            if alert["condition"] == "Altında" and close < alert["target"]:
                results.append(f"{ticker}: Fiyat {alert['target']} altına düştü → {close}")

        # RSI alarmı
        if alert["type"] == "rsi":
            if alert["condition"] == "Üstünde" and rsi > alert["level"]:
                results.append(f"{ticker}: RSI {alert['level']} üstünde → {round(rsi,2)}")
            if alert["condition"] == "Altında" and rsi < alert["level"]:
                results.append(f"{ticker}: RSI {alert['level']} altında → {round(rsi,2)}")

        # MACD alarmı
        if alert["type"] == "macd":
            if alert["signal"] == "Crossover" and hist.iloc[-1] > 0 and hist.iloc[-2] < 0:
                results.append(f"{ticker}: MACD pozitif kesişim!")
            if alert["signal"] == "Crossunder" and hist.iloc[-1] < 0 and hist.iloc[-2] > 0:
                results.append(f"{ticker}: MACD negatif kesişim!")

    return results
for art in articles:
    title = clean_text(art.get("title", ""))
    desc = clean_text(art.get("description", ""))
    full = title + " " + desc

    if len(full) < 5:
        continue

    score = analyzer.polarity_scores(full)
    sentiments.append(score["compound"])

if len(sentiments) == 0:
    return 0, "🔘 Veri Yok"

avg = np.mean(sentiments)

if avg > 0.5:
    label = "🟢 Güçlü Pozitif"
elif avg > 0.1:
    label = "🟩 Pozitif"
elif avg >= -0.1:
    label = "⚪ Nötr"
elif avg >= -0.5:
    label = "🟥 Negatif"
else:
    label = "🔴 Güçlü Negatif"

return avg, label
momentum = close.pct_change().rolling(20).mean().iloc[-1]
vol = close.pct_change().rolling(20).std().iloc[-1]
rsi = calc_rsi(close).iloc[-1]

macd, signal, hist = calc_macd(close)
macd_slope = macd.diff().iloc[-5:].mean()

score = 0

if momentum > 0:
    score += 30
if macd_slope > 0:
    score += 30
if 40 < rsi < 70:
    score += 20
if vol < 0.02:
    score += 20

if score >= 80:
    trend = "🚀 Güçlü Yukarı"
elif score >= 55:
    trend = "📈 Yukarı"
elif score >= 40:
    trend = "〽️ Kararsız"
else:
    trend = "📉 Aşağı"

return trend, score
for ticker in BIST100_LISTESI:
    df = fetch_yahoo(ticker, period="6mo")
    if df is None or df.empty:
        continue

    rsi = calc_rsi(df["Close"]).iloc[-1]
    volume = df["Volume"].iloc[-1]
    price = df["Close"].iloc[-1]

    # PD/DD ve ROE — Yahoo Finance info
    try:
        info = yf.Ticker(ticker).info
        roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0
        pddd = info.get("priceToBook", 0)
    except:
        roe = 0
        pddd = 0

    # Filtre uygulanıyor
    if not (min_rsi <= rsi <= max_rsi):
        continue
    if roe < min_roe:
        continue
    if pddd > max_pddd:
        continue
    if volume < min_volume:
        continue

    results.append({
        "Hisse": ticker,
        "RSI": round(rsi, 2),
        "ROE %": round(roe, 2),
        "PD/DD": round(pddd, 2),
        "Hacim": int(volume),
        "Fiyat": round(price, 2)
    })

return pd.DataFrame(results)
    close = df["Close"].iloc[-1]

    # --- RSI ---
    rsi = calc_rsi(df["Close"]).iloc[-1]

    # --- MACD ---
    macd, signal, hist = calc_macd(df["Close"])
    macd_val = macd.iloc[-1]
    signal_val = signal.iloc[-1]

    # --- Stoch RSI ---
    stoch = calc_stoch_rsi(df["Close"]).iloc[-1]

    # --- Ichimoku ---
    tenkan, kijun, senkou_a, senkou_b, chikou = calc_ichimoku(df)
    ichi_trend = "N/A"
    try:
        if close > max(senkou_a.iloc[-1], senkou_b.iloc[-1]):
            ichi_trend = "🟢 Yukarı Trend"
        elif close < min(senkou_a.iloc[-1], senkou_b.iloc[-1]):
            ichi_trend = "🔴 Aşağı Trend"
        else:
            ichi_trend = "⚪ Yan Bölge"
    except:
        pass

    # --- Bollinger Sıkışma ---
    sma, upper, lower = calc_bollinger(df["Close"])
    bb_width = ((upper - lower) / sma).iloc[-1]
    squeeze = "🎯 Sıkışma" if bb_width < 0.12 else "💎 Normal"

    # --- PD / DD & ROE ---
    try:
        info = yf.Ticker(ticker).info
        roe = info.get("returnOnEquity", 0)
        pddd = info.get("priceToBook", 0)
        roe = roe * 100 if roe else 0
    except:
        roe = 0
        pddd = 0

    # --- Trend Skoru ---
    trend, trend_score = simple_trend_predictor(df)

    return {
        "ticker": ticker,
        "price": round(close, 2),
        "rsi": round(rsi, 2),
        "macd": round(macd_val, 4),
        "signal": round(signal_val, 4),
        "stoch": round(stoch, 3),
        "ichi": ichi_trend,
        "bb": squeeze,
        "roe": round(roe, 2),
        "pddd": round(pddd, 2),
        "trend": trend,
        "trend_score": trend_score
    }

except Exception as e:
    return None
for t in BIST100_LISTESI:
    d = full_analysis(t)
    if d:
        results.append(d)
    time.sleep(0.1)

df = pd.DataFrame(results)
return df
c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 0.8, 1.2, 1.5])

with c1:
    st.metric("Piyasa Durumu", "Nötr-Pozitif", "+0.4%")

with c2:
    st.markdown(f"""
    <div style="background: #1a1c24; border: 1px solid #2d2f39; padding: 10px; 
                border-radius: 10px; text-align:center;">
        <span style="font-size:0.8rem; color:#94a3b8;">VIX Endeksi</span><br>
        <span style="font-size:1.3rem; font-weight:700; color:white;">{vix_val}</span><br>
        <span style="font-size:0.8rem; color:{vix_color}; font-weight:600;">{vix_text}</span>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.write(f"⏱️ **{datetime.now().strftime('%H:%M')}**")

with c4:
    currency = st.radio("Birim", ["TL ₺", "USD $"], horizontal=True, label_visibility="collapsed")
    st.session_state.currency = currency

with c5:
    vade = st.select_slider(
        "Vade",
        options=["1 Saatlik", "4 Saatlik", "Günlük", "Haftalık"],
        label_visibility="collapsed"
    )
    st.session_state.vade = vade

# USD Kuru
if "usd_rate" not in st.session_state:
    try:
        st.session_state.usd_rate = yf.Ticker("USDTRY=X").history(period="1d")["Close"].iloc[-1]
    except:
        st.session_state.usd_rate = 34.5

st.divider()
    if df is None or df.empty or len(df) < 30:
        return None

    price_tl = df["Close"].iloc[-1]
    usd_rate = st.session_state.usd_rate
    display_price = convert_price(price_tl, is_usd, usd_rate)

    # BB
    sma, upper, lower = calc_bollinger(df["Close"])
    bb_width = ((upper - lower) / sma).iloc[-1]
    squeeze = "🎯 Sıkışma" if bb_width < 0.12 else "💎 Normal"

    # RSI
    rsi = calc_rsi(df["Close"]).iloc[-1]

    # MACD
    macd, signal, hist = calc_macd(df["Close"])

    # Stoch RSI
    stoch = calc_stoch_rsi(df["Close"]).iloc[-1]

    # ROE, PD/DD
    try:
        info = yf.Ticker(ticker).info
        roe = info.get("returnOnEquity", 0)
        pddd = info.get("priceToBook", 0)
        roe = roe * 100 if roe else 0
    except:
        roe = 0
        pddd = 0

    # Trend Skoru
    trend, score = simple_trend_predictor(df)

    return {
        "Hisse": ticker.replace(".IS", ""),
        "Fiyat": display_price,
        "RSI": round(rsi, 2),
        "MACD": round(macd.iloc[-1], 4),
        "Signal": round(signal.iloc[-1], 4),
        "Stoch": round(stoch, 3),
        "BB": squeeze,
        "PD/DD": round(pddd, 2),
        "ROE": round(roe, 2),
        "Trend": trend,
        "Skor": score,
        "df": df
    }

except Exception as e:
    return None
results = []
for t in tickers:
    data = fetch_stock_data(t, vade, is_usd)
    if data:
        results.append(data)
    time.sleep(0.10)  # Rate limit koruması

if len(results) == 0:
    st.warning("Veri alınamadı. Yahoo limitine takılmış olabilir.")
    return

df = pd.DataFrame(results).sort_values("Skor", ascending=False)

def highlight_row(row):
    if row["Skor"] >= 80 and row["PD/DD"] < df["PD/DD"].mean():
        return ['background-color:#00ff41; color:black; font-weight:bold'] * len(row)
    if row["Skor"] < 40:
        return ['color:#ef4444; font-weight:bold'] * len(row)
    return [''] * len(row)

st.dataframe(
    df.style.apply(highlight_row, axis=1),
    use_container_width=True,
    hide_index=True
)
st.markdown(f"## 📌 {ticker} – Gelişmiş Detay")

# --- Veri çek ---
df = fetch_yahoo(ticker, period="1y", interval="1d")
if df is None or df.empty:
    st.error("Veri alınamadı.")
    return

# --- ÖZET ANALİZ ---
analysis = full_analysis(ticker)

c1, c2 = st.columns([1.4, 1])

# Sol: Grafik
with c1:
    chart = plot_advanced(df, ticker)
    st.plotly_chart(chart, use_container_width=True)

# Sağ: Analiz Kartı
with c2:
    st.subheader("📊 Teknik Durum")
    st.write(f"**Fiyat:** {analysis['price']}")
    st.write(f"**RSI:** {analysis['rsi']}")
    st.write(f"**MACD:** {analysis['macd']} / {analysis['signal']}")
    st.write(f"**StochRSI:** {analysis['stoch']}")
    st.write(f"**Bollinger:** {analysis['bb']}")
    st.write(f"**Ichimoku:** {analysis['ichi']}")
    st.write(f"**PD/DD:** {analysis['pddd']}")
    st.write(f"**ROE:** {analysis['roe']}%")
    st.write(f"**Trend:** {analysis['trend']} ({analysis['trend_score']})")

st.divider()

# --- Haber Analizi ---
st.subheader("📰 Haber Duygu Analizi")
avg, label = analyze_news_sentiment(ticker.replace(".IS", ""))
st.metric("Duygu Skoru", round(avg, 3), label)
pm = PortfolioManager()

st.subheader("📦 Portföy Yönetimi")

with st.expander("➕ Yeni Pozisyon Ekle"):
    t = st.text_input("Hisse:", placeholder="Ör: THYAO.IS")
    qty = st.number_input("Adet:", min_value=1, step=1)
    price = st.number_input("Alış Fiyatı:", min_value=0.01)
    if st.button("Ekle"):
        if ".IS" not in t:
            st.error("Hisse formatı HISE.IS şeklinde olmalı!")
        else:
            pm.add_position(t, qty, price)
            st.success("Eklendi.")

st.divider()

positions, total_value, total_pnl, total_pnl_pct = pm.calculate_metrics()

if len(positions) == 0:
    st.info("Portföyde pozisyon yok.")
    return

st.write(f"💰 **Toplam Değer:** {round(total_value,2)}")
st.write(f"📈 **Toplam Kar:** {round(total_pnl,2)}  (%{round(total_pnl_pct,2)})")

st.dataframe(pd.DataFrame(positions), use_container_width=True)
am = AlertManager()

st.subheader("🔔 Alarm Sistemi")

tab1, tab2 = st.tabs(["Alarm Ekle", "Alarm Listesi"])

# ------------------ Alarm Ekle ------------------
with tab1:
    st.markdown("### ➕ Yeni Alarm Oluştur")

    alarm_type = st.selectbox(
        "Alarm Türü", 
        ["Fiyat Alarmı", "RSI Alarmı", "MACD Alarmı"]
    )

    ticker = st.text_input("Hisse (örn: THYAO.IS):")

    if alarm_type == "Fiyat Alarmı":
        condition = st.selectbox("Koşul", ["Üstünde", "Altında"])
        target = st.number_input("Hedef Fiyat", min_value=0.01)

        if st.button("Fiyat Alarmı Ekle"):
            am.add_price_alert(ticker, condition, target)
            st.success("Alarm eklendi!")

    elif alarm_type == "RSI Alarmı":
        condition = st.selectbox("Koşul", ["Üstünde", "Altında"])
        level = st.slider("RSI Seviye", 0, 100, 70)

        if st.button("RSI Alarmı Ekle"):
            am.add_rsi_alert(ticker, condition, level)
            st.success("Alarm eklendi!")

    elif alarm_type == "MACD Alarmı":
        signal = st.selectbox("MACD Sinyal Türü", ["Crossover", "Crossunder"])
        if st.button("MACD Alarmı Ekle"):
            am.add_macd_alert(ticker, signal)
            st.success("Alarm eklendi!")

# ------------------ Alarm Listesi ------------------
with tab2:
    st.markdown("### 📋 Alarm Listesi")

    alerts = am.list_alerts()
    if len(alerts) == 0:
        st.info("Hiç alarm eklenmemiş.")
        return

    st.dataframe(pd.DataFrame(alerts), use_container_width=True)

    st.markdown("### 🔍 Alarm Kontrolü")

    if st.button("Kontrol Et"):
        triggered = am.check_alerts()
        if len(triggered) == 0:
            st.info("Şu anda tetiklenen alarm yok.")
        else:
            for t in triggered:
                st.success(t)
st.subheader("🔍 Gelişmiş Hisse Tarayıcı")

with st.expander("⚙️ Filtreleri Aç / Kapat"):

    rsi_range = st.slider("RSI Aralığı", 0, 100, (30, 70))
    min_roe = st.slider("Minimum ROE %", 0, 60, 10)
    max_pddd = st.slider("Maksimum PD/DD", 0.0, 10.0, 3.0)
    min_volume = st.number_input("Minimum Günlük Hacim", min_value=0, value=1_000_000)

    filters = {
        "rsi": rsi_range,
        "roe": min_roe,
        "pddd": max_pddd,
        "volume": min_volume
    }

    if st.button("Taramayı Başlat"):
        df = run_screener(filters)
        if df.empty:
            st.warning("Filtrelere uyan hisse bulunamadı.")
        else:
            st.success(f"{len(df)} hisse bulundu")
            st.dataframe(df, use_container_width=True)
st.subheader("📘 BIST100 Genel Bakış")

if st.button("Verileri Yenile ➰"):
    st.cache_data.clear()

df = analyze_all_bist100()

if df.empty:
    st.error("Veri alınamadı.")
    return

st.dataframe(df.sort_values("trend_score", ascending=False), use_container_width=True)
menu = st.sidebar.radio(
    "",
    [
        "📊 Tek Hisse Analizi",
        "📈 Sektörel Analiz",
        "📘 BIST100 Genel Bakış",
        "🔍 Gelişmiş Tarayıcı",
        "📦 Portföy Yönetimi",
        "🔔 Alarm Sistemi",
        "⚙️ Ayarlar"
    ]
)

return menu
st.subheader("⚙️ Ayarlar")

if st.button("📁 Cache Temizle"):
    st.cache_data.clear()
    st.success("Cache temizlendi.")

st.write("🔧 Uygulama ayarları ileride buraya eklenecek.")
if menu_choice == "📊 Tek Hisse Analizi":
    ticker = st.text_input("Hisse seçin (örn: THYAO.IS):")
    if ticker:
        render_single_stock_view(ticker)

elif menu_choice == "📈 Sektörel Analiz":
    tab_list = list(BIST_SEKTORLER.keys())
    tabs = st.tabs(tab_list)

    for idx, tab in enumerate(tabs):
        with tab:
            sector_name = tab_list[idx]
            tickers = BIST_SEKTORLER[sector_name]
            render_sector_table(sector_name, tickers, st.session_state.vade, st.session_state.currency == "USD $")

elif menu_choice == "📘 BIST100 Genel Bakış":
    render_bist100_overview()

elif menu_choice == "🔍 Gelişmiş Tarayıcı":
    render_screener_page()

elif menu_choice == "📦 Portföy Yönetimi":
    render_portfolio_page()

elif menu_choice == "🔔 Alarm Sistemi":
    render_alert_page()

elif menu_choice == "⚙️ Ayarlar":
    render_settings_page()

else:
    st.write("Bilinmeyen sayfa.")
# Üst Panel
render_home_header()
render_top_panel()

# Menü
menu = render_main_menu()

# Sayfayı yönlendir
render_page(menu)
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)

    return {
        "PP": round(pp, 2),
        "R1": round(r1, 2),
        "S1": round(s1, 2),
        "R2": round(r2, 2),
        "S2": round(s2, 2)
    }
except:
    return None
    levels = {
        "0.236": round(high - diff * 0.236, 2),
        "0.382": round(high - diff * 0.382, 2),
        "0.5": round(high - diff * 0.5, 2),
        "0.618": round(high - diff * 0.618, 2),
        "0.786": round(high - diff * 0.786, 2),
    }
    return levels
except:
    return None
    if ema20.iloc[-1] > ema50.iloc[-1]:
        return "🟢 Yukarı"
    elif ema20.iloc[-1] < ema50.iloc[-1]:
        return "🔴 Aşağı"
    else:
        return "⚪ Yatay"
except:
    return "⚪ Belirsiz"
for i in range(window, len(df) - window):
    high = df["High"].iloc[i]
    low = df["Low"].iloc[i]

    if high == max(df["High"].iloc[i-window:i+window+1]):
        resistances.append(high)

    if low == min(df["Low"].iloc[i-window:i+window+1]):
        supports.append(low)

return supports[-10:], resistances[-10:]
    coeffs = np.polyfit(x, y, deg=1)
    trendline = coeffs[0] * x + coeffs[1]

    return trendline
except:
    return None
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    return atr
except:
    return None
    if atr / price < 0.01:
        return "🟢 Düşük Volatilite"
    elif atr / price < 0.025:
        return "🟡 Orta Volatilite"
    else:
        return "🔴 Yüksek Volatilite"
except:
    return "⚪ Belirsiz"
    result = {}
    last = df["Close"].iloc[-1]

    for p in periods:
        if len(df) > p:
            ret = (last / df["Close"].iloc[-p] - 1) * 100
        else:
            ret = None
        result[p] = round(ret, 2) if ret else None

    return {
        "1m": result[20],
        "3m": result[60],
        "6m": result[120],
        "12m": result[240]
    }
except:
    return None
o = df["Open"].iloc[-1]
h = df["High"].iloc[-1]
l = df["Low"].iloc[-1]
c = df["Close"].iloc[-1]

# Hammer
if (h - l) > 3 * (o - c) and abs(o - c) <= (h - l) * 0.25:
    patterns.append("🔨 Hammer")

# Doji
if abs(o - c) < (h - l) * 0.1:
    patterns.append("➕ Doji")

# Engulfing
if len(df) > 2:
    prev_o = df["Open"].iloc[-2]
    prev_c = df["Close"].iloc[-2]
    if c > o and prev_o > prev_c and c > prev_o and o < prev_c:
        patterns.append("🟢 Bullish Engulfing")
    if c < o and prev_o < prev_c and c < prev_o and o > prev_c:
        patterns.append("🔴 Bearish Engulfing")

return patterns if patterns else ["— Formasyon Yok —"]
st.subheader("📐 Ek Teknik Göstergeler")

# --- VOLATİLİTE ----
vol = classify_volatility(df)
st.write(f"**Volatilite:** {vol}")

# --- OBV ---
obv = calc_obv(df)
if obv is not None:
    st.line_chart(obv, height=140, use_container_width=True)

# --- Pivot Noktaları ---
pivots = calc_pivots(df)
if pivots:
    st.write("### 🎯 Pivot Noktaları")
    st.json(pivots)

# --- Fibonacci ---
fib = calc_fibonacci(df)
if fib:
    st.write("### 📏 Fibonacci Seviyeleri")
    st.json(fib)

# --- Performans ---
perf = performance_periods(df)
if perf:
    st.write("### 📊 Getiri Performansı")
    st.json(perf)

# --- Formasyonlar ---
patt = detect_patterns(df)
st.write("### 🔎 Mum Formasyonu")
st.write(", ".join(patt))
# Veri çek
df = fetch_yahoo(ticker, period="1y", interval="1d")
if df is None or df.empty:
    st.error("Veri alınamadı.")
    return

# Temizle
df = sanitize_df(df)

# ÖZET TEKNİK ANALİZ
analysis = full_analysis(ticker)

# Grafik ve analiz yan yana
c1, c2 = st.columns([1.6, 1])

with c1:
    chart = plot_advanced(df, ticker)
    st.plotly_chart(chart, use_container_width=True)

with c2:
    st.subheader("📊 Teknik Durum")
    st.write(f"**Fiyat:** {analysis['price']}")
    st.write(f"**Trend:** {analysis['trend']} ({analysis['trend_score']})")
    st.write(f"**RSI:** {analysis['rsi']}")
    st.write(f"**MACD:** {analysis['macd']} / {analysis['signal']}")
    st.write(f"**Bollinger:** {analysis['bb']}")
    st.write(f"**Ichimoku:** {analysis['ichi']}")
    st.write(f"**PD/DD:** {analysis['pddd']}")
    st.write(f"**ROE:** {analysis['roe']}%")

st.divider()

# EK GÖSTERGELER
render_additional_indicators(df)

st.divider()

# HABER ANALİZİ
st.subheader("📰 Haber Duygu Analizi")
avg, label = analyze_news_sentiment(ticker.replace(".IS", ""))
st.metric("Duygu Skoru", round(avg, 3), label)
def __init__(self):
    if "data_cache" not in st.session_state:
        st.session_state.data_cache = {}

def get(self, key):
    return st.session_state.data_cache.get(key, None)

def set(self, key, value):
    st.session_state.data_cache[key] = {
        "value": value,
        "timestamp": time.time()
    }

def is_valid(self, key, ttl=300):
    entry = st.session_state.data_cache.get(key, None)
    if not entry:
        return False
    return (time.time() - entry["timestamp"]) < ttl
for t in tickers:
    key = f"{t}-{period}-{interval}"

    if cache.is_valid(key):
        results[t] = cache.get(key)["value"]
        continue

    df = fetch_yahoo(t, period=period, interval=interval)
    df = sanitize_df(df)

    cache.set(key, df)
    results[t] = df

    time.sleep(0.1)  # YF limit koruması

return results
def worker(t):
    results[t] = fetch_yahoo(t, period=period, interval=interval)

for t in tickers:
    th = threading.Thread(target=worker, args=(t,))
    threads.append(th)
    th.start()
    time.sleep(0.05)

for th in threads:
    th.join()

return results
