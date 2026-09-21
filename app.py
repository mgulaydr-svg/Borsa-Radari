import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Quantamental Fon Radarı V4.1", layout="wide")

# --- 1. MAKRO REJİM MOTORU ---
@st.cache_data(ttl=600)
def makro_rejimi_belirle():
    try:
        xu100 = yf.Ticker("XU100.IS").history(period="1y", interval="1d")
        if xu100.empty: return "Nötr", 0
        
        close = xu100['Close']
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
        son_fiyat = close.iloc[-1]
        
        if (son_fiyat > ema200 * 1.02) and (ema50 > ema200):
            return "YÜKSELİŞ 🟢", son_fiyat
        elif son_fiyat < ema200 * 0.98:
            return "DÜŞÜŞ 🔴", son_fiyat
        else:
            return "NÖTR 🟡", son_fiyat
    except:
        return "BİLİNMİYOR", 0

rejim, xu100_fiyat = makro_rejimi_belirle()

# --- 2. SOL MENÜ: STRATEJİ VE PARAMETRELER ---
st.sidebar.markdown(f"### 🌐 Makro Rejim: **{rejim}**")
st.sidebar.caption(f"BİST 100 Güncel: {xu100_fiyat:.2f}")
st.sidebar.markdown("---")

st.sidebar.header("📋 Varlık Yönetimi")
portfoy_girdisi = st.sidebar.text_area("💼 Portföy Hisseleri", "MPARK.IS")
izleme_girdisi = st.sidebar.text_area("👁️ İzleme Listesi", "TKFEN.IS, HALKB.IS, ISDMR.IS, CEOEM.IS")

st.sidebar.markdown("---")
st.sidebar.header("🎯 Tarama Stratejisi")

strateji = st.sidebar.selectbox(
    "Aktif Profili Seçin:",
    ["Manuel Ayarlar", "🛡️ Kalkan (Defansif)", "🚀 Avcı (Agresif Büyüme)", "🦅 Anka (Dipten Dönüş)", "🏢 Nakit İneği (Temettü)"]
)

# Strateji Parametrelerinin Dinamik Atanması
if strateji == "🛡️ Kalkan (Defansif)":
    p_max_fk, p_max_pddd = 12.0, 3.0
    p_rsi_min, p_rsi_max = 45, 60
    p_ema_periyot = 21
    p_hacim_artis = 20
    p_iz_suren = 5.0
    p_atr = 1.5
elif strateji == "🚀 Avcı (Agresif Büyüme)":
    p_max_fk, p_max_pddd = 30.0, 8.0
    p_rsi_min, p_rsi_max = 60, 80
    p_ema_periyot = 9
    p_hacim_artis = 80
    p_iz_suren = 10.0
    p_atr = 2.0
elif strateji == "🦅 Anka (Dipten Dönüş)":
    p_max_fk, p_max_pddd = 8.0, 1.5
    p_rsi_min, p_rsi_max = 30, 45
    p_ema_periyot = 21
    p_hacim_artis = 50
    p_iz_suren = 7.0
    p_atr = 1.0
elif strateji == "🏢 Nakit İneği (Temettü)":
    p_max_fk, p_max_pddd = 10.0, 2.0
    p_rsi_min, p_rsi_max = 40, 65
    p_ema_periyot = 50
    p_hacim_artis = 0
    p_iz_suren = 7.0
    p_atr = 1.5
else: # Manuel Ayarlar
    st.sidebar.caption("Manuel parametreleri aşağıdan belirleyin:")
    p_max_fk = st.sidebar.slider("Maks F/K", 0.0, 50.0, 15.0)
    p_max_pddd = st.sidebar.slider("Maks PD/DD", 0.0, 15.0, 5.0)
    p_rsi_min = st.sidebar.slider("Min RSI", 20, 70, 40)
    p_rsi_max = st.sidebar.slider("Maks RSI", 40, 90, 65)
    p_ema_periyot = st.sidebar.selectbox("Trend EMA", [9, 21, 50, 200], index=1)
    p_hacim_artis = st.sidebar.slider("Min Hacim Artışı (%)", 0, 200, 20)
    p_iz_suren = st.sidebar.slider("İz Süren Stop (%)", 3.0, 15.0, 7.0)
    p_atr = st.sidebar.slider("ATR Tamponu", 0.5, 3.0, 1.5)

# --- 3. MATEMATİK VE SİNYAL MOTORU ---
@st.cache_data(ttl=300)
def hisse_analiz_et(ticker, strat_name):
    try:
        hisse = yf.Ticker(ticker)
        df = hisse.history(period="6mo", interval="1d")
        if len(df) < 50: return None
        
        info = hisse.info
        fk_orani = info.get('trailingPE', 0) or 0
        pddd_orani = info.get('priceToBook', 0) or 0

        # Teknik İndikatörler
        df['EMA_Trend'] = df['Close'].ewm(span=p_ema_periyot, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean() # Standart koruma
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0.0).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        
        # Stopların Hesaplanması
        df['ATR_Stop'] = df['EMA_21'] - (p_atr * df['ATR_14'])
        df['Trailing_Stop'] = df['High'].rolling(20).max() * (1 - (p_iz_suren / 100))
        
        son_bar = df.iloc[-1]
        fiyat = son_bar['Close']
        
        # Şartların Kontrolü
        trend_sarti = fiyat > son_bar['EMA_Trend']
        rsi_sarti = p_rsi_min <= son_bar['RSI_14'] <= p_rsi_max
        hacim_sarti = son_bar['Volume'] >= son_bar['Vol_SMA20'] * (1 + (p_hacim_artis / 100))
        temel_sarti = (0 < fk_orani <= p_max_fk) and (0 < pddd_orani <= p_max_pddd)
        
        teknik_ok = trend_sarti and rsi_sarti and hacim_sarti
        
        # Detaylı Sinyal ve Karar Mekanizması
        if fiyat < son_bar['Trailing_Stop']:
            durum = f"🔴 SAT (İz Süren Kırıldı: {fiyat:.2f} < {son_bar['Trailing_Stop']:.2f})"
        elif fiyat < son_bar['ATR_Stop']:
            durum = f"🔴 SAT (ATR Stop Kırıldı: {fiyat:.2f} < {son_bar['ATR_Stop']:.2f})"
        elif teknik_ok and temel_sarti:
            if "DÜŞÜŞ" in rejim:
                durum = "🚫 ALIM YASAK (Makro Rejim Düşüşte)"
            else:
                durum = "🟢 KUSURSUZ ONAY (Teknik + Temel Uygun)"
        elif teknik_ok and not temel_sarti:
            durum = f"⚠️ ŞİŞKİN (Teknik İyi Ama F/K: {fk_orani:.1f} Yüksek)"
        else:
            eksikler = []
            if not trend_sarti: eksikler.append(f"Trend Altı (EMA{p_ema_periyot})")
            if not rsi_sarti: eksikler.append(f"RSI Uyumsuz ({son_bar['RSI_14']:.1f})")
            if not hacim_sarti: eksikler.append("Hacim Yetersiz")
            durum = f"⏳ BEKLE ({' | '.join(eksikler)})"
            
        return {
            "Hisse": ticker,
            "Fiyat": round(fiyat, 2),
            "F/K": round(fk_orani, 2),
            "PD/DD": round(pddd_orani, 2),
            f"EMA-{p_ema_periyot}": round(son_bar['EMA_Trend'], 2),
            "RSI": round(son_bar['RSI_14'], 1),
            "İz Süren Stop": round(son_bar['Trailing_Stop'], 2),
            "ATR Stop": round(son_bar['ATR_Stop'], 2),
            "Sinyal": durum
        }
    except:
        return None

def listeyi_analiz_et(girdi_metni):
    hisseler = [x.strip().upper() for x in girdi_metni.split(",") if x.strip()]
    if not hisseler: return None
    sonuclar = []
    with st.spinner(f'{strateji} ayarlarına göre taranıyor...'):
        for h in hisseler:
            if not h.endswith(".IS"): h += ".IS"
            sonuc = hisse_analiz_et(h, strateji)
            if sonuc: sonuclar.append(sonuc)
    return pd.DataFrame(sonuclar) if sonuclar else None

# --- 4. ANA EKRAN SEKMELERİ ---
st.title("🛡️ Quantamental Portföy & Tarama Kokpiti V4.1")
st.caption(f"Geçerli Strateji Seti: **{strateji}** | Rejim: **{rejim}**")

tab_portfoy, tab_izleme, tab_tarama, tab_sorgu = st.tabs([
    "💼 Portföyüm", 
    "👁️ İzleme Listem", 
    "📡 BİST Tüm Piyasa Taraması", 
    "🔍 Tekil Hisse Sorgusu"
])

with tab_portfoy:
    st.subheader("Aktif Yatırımlar ve Kâr Kalkanları")
    df_portfoy = listeyi_analiz_et(portfoy_girdisi)
    if df_portfoy is not None:
        st.dataframe(df_portfoy, use_container_width=True)

with tab_izleme:
    st.subheader("Pusudaki Hedefler (Zamanlama Bekleyenler)")
    df_izleme = listeyi_analiz_et(izleme_girdisi)
    if df_izleme is not None:
        st.dataframe(df_izleme, use_container_width=True)

with tab_tarama:
    st.subheader(f"Tüm Borsayı {strateji} Modunda Tara")
    ticker_dosyasi = st.file_uploader("tickers.csv dosyasını yükleyin", type=["csv"])
    
    if ticker_dosyasi is not None:
        df_tickers = pd.read_csv(ticker_dosyasi)
        if 'Tickers' in df_tickers.columns:
            tum_hisseler = df_tickers['Tickers'].dropna().tolist()
            
            if st.button("🚀 Dev Taramayı Başlat"):
                ilerleme_metni = st.empty()
                ilerleme_cubugu = st.progress(0)
                firsatlar = []
                toplam_sayi = len(tum_hisseler)
                
                for i, hisse in enumerate(tum_hisseler):
                    ilerleme_metni.text(f"Taranıyor: {hisse} ({i+1}/{toplam_sayi})")
                    sonuc = hisse_analiz_et(hisse, strateji)
                    
                    if sonuc is not None and ("KUSURSUZ" in sonuc['Sinyal'] or "YASAK" in sonuc['Sinyal']):
                        firsatlar.append(sonuc)
                        
                    ilerleme_cubugu.progress((i + 1) / toplam_sayi)
                
                ilerleme_metni.text("Tarama Tamamlandı!")
                if firsatlar:
                    st.success(f"{strateji} profiline uyan {len(firsatlar)} hisse bulundu.")
                    st.dataframe(pd.DataFrame(firsatlar).sort_values(by="F/K", ascending=True), use_container_width=True)
                else:
                    st.warning("Bu profilin katı şartlarını sağlayan hisse bulunamadı.")
        else:
            st.error("Yüklenen dosyada 'Tickers' sütunu yok!")

with tab_sorgu:
    st.subheader("Anlık Hızlı Hisse Taraması")
    aranan_hisse = st.text_input("Hisse Kodunu Girin (Örn: MPARK.IS):").upper()
    if aranan_hisse:
        if not aranan_hisse.endswith(".IS"): aranan_hisse += ".IS"
        with st.spinner('Analiz ediliyor...'):
            sonuc = hisse_analiz_et(aranan_hisse, strateji)
            if sonuc is not None:
                st.dataframe(pd.DataFrame([sonuc]), use_container_width=True)
