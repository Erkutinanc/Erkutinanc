import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import feedparser
import requests
from datetime import datetime, timedelta
import time

# ── SAYFA AYARLARI ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BIST100 Öneri Motoru",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background-color: #08090c; color: #dde1f0; }
.block-container { padding: 1.5rem 2rem; max-width: 1400px; }

/* Metrik kartlar */
div[data-testid="metric-container"] {
    background: #0e1016;
    border: 1px solid #1e2130;
    padding: 14px 18px;
    border-radius: 0px;
}
div[data-testid="metric-container"] label { color: #4a5070 !important; font-size: 11px !important; letter-spacing: 2px !important; text-transform: uppercase; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 22px !important; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #0e1016; border-right: 1px solid #1e2130; }
section[data-testid="stSidebar"] .stSelectbox label, 
section[data-testid="stSidebar"] .stMultiSelect label { color: #6a7090; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }

/* Butonlar */
.stButton button { background: #13151d; border: 1px solid #1e2130; color: #dde1f0; border-radius: 0; font-family: 'IBM Plex Mono', monospace; letter-spacing: 1px; }
.stButton button:hover { border-color: #00e676; color: #00e676; }

/* Sinyal kutucukları */
.sig-al  { display:inline-block; background:rgba(0,230,118,0.1); color:#00e676; border:1px solid rgba(0,230,118,0.3); font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:700; padding:3px 10px; letter-spacing:2px; }
.sig-sat { display:inline-block; background:rgba(255,68,68,0.1);  color:#ff4444; border:1px solid rgba(255,68,68,0.3);  font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:700; padding:3px 10px; letter-spacing:2px; }
.sig-bkl { display:inline-block; background:rgba(255,179,0,0.1); color:#ffb300; border:1px solid rgba(255,179,0,0.3); font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:700; padding:3px 10px; letter-spacing:2px; }

.sektor-card { background:#0e1016; border:1px solid #1e2130; padding:16px; margin-bottom:8px; }
.hisse-row   { background:#13151d; border:1px solid #1e2130; padding:12px; margin-bottom:4px; }
.top-badge   { background:#00e676; color:#000; font-size:9px; font-weight:700; padding:2px 7px; letter-spacing:1px; margin-left:8px; }

div[data-testid="stDataFrame"] { border: 1px solid #1e2130; }
div[data-testid="stDataFrame"] th { background: #0e1016 !important; color: #4a5070 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important; letter-spacing: 1px !important; text-transform: uppercase !important; }
</style>
""", unsafe_allow_html=True)

# ── SABİT VERİLER ─────────────────────────────────────────────────────────────
HISSELER = {
    "Bankacılık":  ["GARAN.IS", "AKBNK.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS"],
    "Havacılık":   ["THYAO.IS", "PGSUS.IS"],
    "Enerji":      ["TUPRS.IS", "ENKAI.IS", "AKSEN.IS"],
    "Teknoloji":   ["ASELS.IS", "TOASO.IS", "FROTO.IS", "LOGO.IS"],
    "Perakende":   ["BIMAS.IS", "MGROS.IS", "KCHOL.IS", "SAHOL.IS"],
    "Demir-Çelik": ["EREGL.IS", "KRDMD.IS", "SISE.IS"],
}

HABER_KAYNAKLARI = [
    "https://www.bloomberght.com/rss",
    "https://www.haberturk.com/rss/borsa.xml",
    "https://www.ntv.com.tr/ekonomi.rss",
]

# ── FONKSİYONLAR ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # 5 dakikada bir güncelle
def get_fiyat_verisi(ticker, period="5d"):
    """yfinance ile hisse verisi çek"""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None

@st.cache_data(ttl=300)
def get_hisse_ozeti(ticker):
    """Güncel fiyat, değişim, hacim"""
    df = get_fiyat_verisi(ticker, "2d")
    if df is None or len(df) < 1:
        return {"fiyat": None, "degisim": None, "hacim": None}
    son = df.iloc[-1]
    onceki = df.iloc[-2] if len(df) >= 2 else son
    degisim = ((son["Close"] - onceki["Close"]) / onceki["Close"]) * 100
    return {
        "fiyat": round(son["Close"], 2),
        "degisim": round(degisim, 2),
        "hacim": int(son["Volume"]),
    }

@st.cache_data(ttl=300)
def hesapla_momentum(ticker):
    """3 günlük fiyat momentumu (0-100 skoru)"""
    df = get_fiyat_verisi(ticker, "5d")
    if df is None or len(df) < 3:
        return 50
    son3 = df.tail(3)
    momentum_pct = ((son3["Close"].iloc[-1] - son3["Close"].iloc[0]) / son3["Close"].iloc[0]) * 100
    # Hacim artışı kontrolü
    hacim_artis = son3["Volume"].iloc[-1] / (son3["Volume"].mean() + 1)
    # Normalize: -10% ile +10% arası -> 0-100
    skor = min(100, max(0, 50 + momentum_pct * 3 + (hacim_artis - 1) * 5))
    return round(skor)

@st.cache_data(ttl=600)  # 10 dakika cache
def get_haberler():
    """RSS kaynaklarından haber çek"""
    haberler = []
    for url in HABER_KAYNAKLARI:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                haberler.append({
                    "baslik": entry.get("title", ""),
                    "ozet": entry.get("summary", "")[:200],
                    "kaynak": feed.feed.get("title", url),
                    "tarih": entry.get("published", ""),
                })
        except Exception:
            pass
    return haberler[:30]

def analiz_haber_sentiment(baslik, ozet, hisse_kodu):
    """
    Basit kural tabanlı haber sentiment analizi.
    Gerçek uygulamada BERTurk modeli kullanılır.
    """
    metin = (baslik + " " + ozet).lower()
    hisse_lower = hisse_kodu.replace(".IS", "").lower()
    
    # Hisse ile ilgili mi?
    ilgili = hisse_lower in metin or hisse_kodu.lower() in metin
    
    # Pozitif kelimeler
    pozitif = ["yüksel", "arttı", "rekor", "büyüme", "kar", "kazanç", "güçlü", 
               "olumlu", "yatırım", "ihracat", "başarı", "al", "hedef"]
    # Negatif kelimeler  
    negatif = ["düştü", "azaldı", "zarar", "risk", "endişe", "düşüş", "satış",
               "kötü", "olumsuz", "baskı", "geriledi", "iflas", "dava"]
    
    poz_skor = sum(1 for k in pozitif if k in metin)
    neg_skor = sum(1 for k in negatif if k in metin)
    
    if not ilgili:
        # Genel piyasa haberi — yarı etkili
        etki = 0.5
    else:
        etki = 1.0
    
    toplam = (poz_skor - neg_skor) * etki
    # 0-100 normalize
    return min(100, max(0, 50 + toplam * 8))

def hesapla_psikoloji_skoru(haberler, hisse_kodu):
    """
    Psikoloji katmanı: haber yoğunluğu + ton analizi.
    Gerçek uygulamada Twitter/Ekşi verileri de eklenir.
    """
    hisse_lower = hisse_kodu.replace(".IS", "").lower()
    ilgili_haberler = [h for h in haberler if hisse_lower in (h["baslik"] + h["ozet"]).lower()]
    
    if len(ilgili_haberler) == 0:
        return 50, "NORMAL"
    
    sentimentler = [analiz_haber_sentiment(h["baslik"], h["ozet"], hisse_kodu) for h in ilgili_haberler]
    ort_sentiment = sum(sentimentler) / len(sentimentler)
    
    # Psikoloji etiketi
    if len(ilgili_haberler) >= 3 and ort_sentiment > 70:
        etiket = "FOMO"
    elif len(ilgili_haberler) >= 2 and ort_sentiment < 35:
        etiket = "PANİK"
    elif len(ilgili_haberler) >= 4:
        etiket = "SÜRÜ"
    else:
        etiket = "NORMAL"
    
    return round(ort_sentiment), etiket

def hesapla_kompozit(haber_skor, psikoloji_skor, momentum_skor):
    """Ana kompozit skor: %40 haber + %35 psikoloji + %25 momentum"""
    return round(haber_skor * 0.40 + psikoloji_skor * 0.35 + momentum_skor * 0.25)

def sinyal_uret(kompozit):
    """AL / BEKLE / SAT"""
    if kompozit >= 65:
        return "AL"
    elif kompozit <= 42:
        return "SAT"
    else:
        return "BEKLE"

def renk(deger):
    if deger >= 65: return "#00e676"
    if deger >= 50: return "#ffb300"
    return "#ff4444"

def sinyal_html(sinyal):
    if sinyal == "AL":  return '<span class="sig-al">AL</span>'
    if sinyal == "SAT": return '<span class="sig-sat">SAT</span>'
    return '<span class="sig-bkl">BEKLE</span>'

# ── ANA HESAPLAMA ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def hesapla_tum_hisseler():
    haberler = get_haberler()
    sonuclar = []
    
    for sektor, tickers in HISSELER.items():
        for ticker in tickers:
            ozet = get_hisse_ozeti(ticker)
            if ozet["fiyat"] is None:
                continue
            
            momentum = hesapla_momentum(ticker)
            psiko_skor, psiko_etiket = hesapla_psikoloji_skoru(haberler, ticker)
            haber_skor = analiz_haber_sentiment("", " ".join([h["baslik"] for h in haberler[:10]]), ticker)
            kompozit = hesapla_kompozit(haber_skor, psiko_skor, momentum)
            sinyal = sinyal_uret(kompozit)
            
            sonuclar.append({
                "Hisse": ticker.replace(".IS", ""),
                "Sektör": sektor,
                "Fiyat": ozet["fiyat"],
                "Değişim%": ozet["degisim"],
                "Haber": haber_skor,
                "Psikoloji": psiko_skor,
                "Psiko Etiket": psiko_etiket,
                "Momentum": momentum,
                "Kompozit": kompozit,
                "Sinyal": sinyal,
            })
    
    return sorted(sonuclar, key=lambda x: x["Kompozit"], reverse=True)

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📈 BIST100 PANO")
    st.markdown(f"*{datetime.now().strftime('%d %B %Y, %H:%M')}*")
    st.divider()
    
    gorunum = st.radio(
        "Görünüm",
        ["Tüm Sinyaller", "🟢 AL", "🔴 SAT", "🟡 BEKLE"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.markdown("**SEKTÖR FİLTRESİ**")
    secili_sektorler = st.multiselect(
        "Sektör",
        list(HISSELER.keys()),
        default=list(HISSELER.keys()),
        label_visibility="collapsed"
    )
    
    st.divider()
    st.markdown("**PSİKOLOJİ FİLTRESİ**")
    secili_psiko = st.multiselect(
        "Psikoloji",
        ["FOMO", "PANİK", "SÜRÜ", "NORMAL"],
        default=["FOMO", "PANİK", "SÜRÜ", "NORMAL"],
        label_visibility="collapsed"
    )
    
    st.divider()
    if st.button("🔄 Verileri Güncelle", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.caption("Her 5 dakikada otomatik güncellenir.")

# ── BAŞLIK ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-bottom:1px solid #1e2130;padding-bottom:16px;margin-bottom:24px">
  <span style="font-family:IBM Plex Mono,monospace;font-size:24px;font-weight:700;letter-spacing:3px">
    BIST<span style="color:#00e676">100</span> ÖNERİ MOTORU
  </span>
  <span style="font-size:11px;color:#4a5070;margin-left:16px;letter-spacing:2px">
    HABER · PSİKOLOJİ · MOMENTUM
  </span>
</div>
""", unsafe_allow_html=True)

# ── VERİ YÜKLEME ───────────────────────────────────────────────────────────────
with st.spinner("Veriler yükleniyor... BIST hisseleri ve haberler çekiliyor."):
    sonuclar = hesapla_tum_hisseler()

if not sonuclar:
    st.error("Veri çekilemedi. İnternet bağlantınızı kontrol edin.")
    st.stop()

df = pd.DataFrame(sonuclar)

# ── ÖZET METRİKLER ─────────────────────────────────────────────────────────────
al_say  = len(df[df["Sinyal"] == "AL"])
sat_say = len(df[df["Sinyal"] == "SAT"])
bkl_say = len(df[df["Sinyal"] == "BEKLE"])

sektor_ozet = df.groupby("Sektör")["Kompozit"].mean().sort_values(ascending=False)
top_sektor  = sektor_ozet.index[0]
top_skor    = round(sektor_ozet.iloc[0])

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("🟢 AL Sinyali", f"{al_say} hisse")
with c2: st.metric("🔴 SAT Sinyali", f"{sat_say} hisse")
with c3: st.metric("🟡 BEKLE", f"{bkl_say} hisse")
with c4: st.metric("⭐ En Güçlü Sektör", top_sektor, f"Skor: {top_skor}")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ── SEKTÖR ANALİZİ ─────────────────────────────────────────────────────────────
st.markdown("""<div style="font-family:IBM Plex Mono,monospace;font-size:11px;letter-spacing:2px;color:#6a7090;text-transform:uppercase;margin-bottom:12px">⬡ Sektör Analizi</div>""", unsafe_allow_html=True)

sektor_df = df.groupby("Sektör").agg(
    Haber=("Haber", "mean"),
    Psikoloji=("Psikoloji", "mean"),
    Momentum=("Momentum", "mean"),
    Kompozit=("Kompozit", "mean"),
    AL=("Sinyal", lambda x: (x == "AL").sum()),
    SAT=("Sinyal", lambda x: (x == "SAT").sum()),
).round(0).astype(int).reset_index().sort_values("Kompozit", ascending=False)

cols = st.columns(len(sektor_df))
for i, (_, row) in enumerate(sektor_df.iterrows()):
    with cols[i]:
        is_top = row["Sektör"] == top_sektor
        border_color = "#00e676" if is_top else "#1e2130"
        st.markdown(f"""
        <div style="background:#0e1016;border:1px solid {border_color};padding:14px;height:100%">
          {"<div style='background:#00e676;color:#000;font-size:8px;font-weight:700;padding:2px 6px;letter-spacing:1px;display:inline-block;margin-bottom:6px'>EN GÜÇLÜ</div>" if is_top else ""}
          <div style="font-size:12px;font-weight:600;margin-bottom:8px">{row["Sektör"]}</div>
          <div style="display:flex;justify-content:space-between;margin-bottom:3px">
            <span style="font-size:10px;color:#4a5070">Haber</span>
            <span style="font-family:IBM Plex Mono,monospace;font-size:10px;color:{renk(row["Haber"])}">{row["Haber"]}</span>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:3px">
            <span style="font-size:10px;color:#4a5070">Psikoloji</span>
            <span style="font-family:IBM Plex Mono,monospace;font-size:10px;color:{renk(row["Psikoloji"])}">{row["Psikoloji"]}</span>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="font-size:10px;color:#4a5070">Momentum</span>
            <span style="font-family:IBM Plex Mono,monospace;font-size:10px;color:{renk(row["Momentum"])}">{row["Momentum"]}</span>
          </div>
          <div style="height:3px;background:#1e2130">
            <div style="height:3px;width:{row["Kompozit"]}%;background:{renk(row["Kompozit"])}"></div>
          </div>
          <div style="margin-top:8px">
            <span style="font-family:IBM Plex Mono,monospace;font-size:10px;font-weight:700;color:{renk(row["Kompozit"])}">{row["Kompozit"]}</span>
            <span style="font-size:10px;color:#4a5070;margin-left:6px">AL:{row["AL"]} SAT:{row["SAT"]}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ── HİSSE TABLOLARI ────────────────────────────────────────────────────────────
st.markdown("""<div style="font-family:IBM Plex Mono,monospace;font-size:11px;letter-spacing:2px;color:#6a7090;text-transform:uppercase;margin-bottom:12px">◈ Hisse Sinyalleri</div>""", unsafe_allow_html=True)

# Filtrele
filtered = df[df["Sektör"].isin(secili_sektorler) & df["Psiko Etiket"].isin(secili_psiko)].copy()
if gorunum == "🟢 AL":     filtered = filtered[filtered["Sinyal"] == "AL"]
elif gorunum == "🔴 SAT":  filtered = filtered[filtered["Sinyal"] == "SAT"]
elif gorunum == "🟡 BEKLE": filtered = filtered[filtered["Sinyal"] == "BEKLE"]

st.caption(f"{len(filtered)} hisse gösteriliyor")

# Tablo görünümü
tab1, tab2 = st.tabs(["📋 Tablo", "📊 Grafik"])

with tab1:
    display_df = filtered[["Hisse","Sektör","Fiyat","Değişim%","Haber","Psikoloji","Psiko Etiket","Momentum","Kompozit","Sinyal"]].copy()
    
    def style_sinyal(val):
        if val == "AL":    return "background-color:#00e67622;color:#00e676;font-weight:bold"
        if val == "SAT":   return "background-color:#ff444422;color:#ff4444;font-weight:bold"
        return "background-color:#ffb30022;color:#ffb300;font-weight:bold"
    
    def style_degisim(val):
        if val is None: return ""
        return f"color:{'#00e676' if val >= 0 else '#ff4444'}"
    
    def style_skor(val):
        if isinstance(val, (int, float)):
            c = renk(val).replace("var(--", "").replace(")", "")
            return f"color:{renk(val)};font-family:IBM Plex Mono,monospace"
        return ""
    
    styled = display_df.style        .applymap(style_sinyal, subset=["Sinyal"])        .applymap(style_degisim, subset=["Değişim%"])        .applymap(style_skor, subset=["Haber","Psikoloji","Momentum","Kompozit"])        .format({"Fiyat": "{:.2f} ₺", "Değişim%": "{:+.2f}%", "Haber": "{:.0f}", "Psikoloji": "{:.0f}", "Momentum": "{:.0f}", "Kompozit": "{:.0f}"})
    
    st.dataframe(styled, use_container_width=True, hide_index=True, height=450)

with tab2:
    if not filtered.empty:
        fig = px.scatter(
            filtered,
            x="Momentum", y="Haber",
            size="Kompozit", color="Sinyal",
            hover_name="Hisse",
            hover_data=["Sektör", "Psikoloji", "Kompozit"],
            color_discrete_map={"AL": "#00e676", "SAT": "#ff4444", "BEKLE": "#ffb300"},
            text="Hisse",
            title="Haber Skoru vs Momentum (boyut = Kompozit Skor)"
        )
        fig.update_layout(
            plot_bgcolor="#08090c", paper_bgcolor="#08090c",
            font_color="#dde1f0", font_family="IBM Plex Mono",
            xaxis=dict(gridcolor="#1e2130", title="Momentum Skoru"),
            yaxis=dict(gridcolor="#1e2130", title="Haber Sentiment Skoru"),
            legend=dict(bgcolor="#0e1016", bordercolor="#1e2130"),
        )
        fig.update_traces(textposition="top center", textfont_size=10)
        st.plotly_chart(fig, use_container_width=True)

# ── HABERLER ───────────────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
with st.expander("📰 Canlı Haber Akışı"):
    haberler = get_haberler()
    if haberler:
        for h in haberler[:15]:
            st.markdown(f"""
            <div style="border-left:2px solid #1e2130;padding:8px 12px;margin-bottom:8px">
              <div style="font-size:13px;font-weight:600">{h["baslik"]}</div>
              <div style="font-size:11px;color:#4a5070;margin-top:3px">{h["kaynak"]} · {h["tarih"][:20] if h["tarih"] else ""}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Haber kaynakları yüklenemedi. İnternet bağlantısını kontrol edin.")

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="display:flex;justify-content:space-between;font-size:11px;color:#4a5070">
  <span>BIST100 Öneri Motoru • Kişisel Kullanım</span>
  <span style="color:#ff4444">⚠ Bu sistem yatırım tavsiyesi değildir. Kararlarınızı kendiniz verin.</span>
</div>
""", unsafe_allow_html=True)
