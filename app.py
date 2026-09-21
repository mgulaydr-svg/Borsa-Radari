import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Quantamental Fon Yönetimi", layout="wide")

# --- YAN MENÜ: PARAMETRELER ---
st.sidebar.header("🎛️ Algoritma Parametreleri")
atr_carpani = st.sidebar.slider("ATR Dalgalanma Tamponu (α)", 0.5, 3.0, 1.5, 0.1)
trailing_stop_pct = st.sidebar.slider("İz Süren Stop (%)", 3.0, 15.0, 7.0, 0.5)
rsi_limit = st.sidebar.slider("RSI Aşırı Alım Sınırı", 50, 85, 65, 1)

# --- MATEMATİK MOTORU ---
@st.cache_data(ttl=300) # Veriyi 5 dakika hafızada tutar (Hız kazandırır)
def hisse_analiz_et(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo", interval="1d")
        if df.empty: return None
        
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # RSI Hesaplama
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0.0).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # ATR Hesaplama
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        
        # Stop Kalkanları
        df['ATR_Stop'] = df['EMA_21'] - (atr_carpani * df['ATR_14'])
        df['Trailing_Stop'] = df['High'].rolling(20).max() * (1 - (trailing_stop_pct / 100))
        
        son_bar = df.iloc[-1]
        
        # Sinyal Üretimi
        fiyat = son_bar['Close']
        if fiyat < son_bar['Trailing_Stop']:
            durum = "🔴 İZ SÜREN PATLADI (SAT)"
        elif fiyat < son_bar['ATR_Stop']:
            durum = "🔴 ATR STOP (ZARAR KES)"
        elif fiyat > son_bar['EMA_21'] and son_bar['RSI_14'] < rsi_limit:
            durum = "🟢 GÜÇLÜ TREND (AL/TUT)"
        else:
            durum = "⏳ BEKLE (ZAYIF/ŞİŞKİN)"
            
        return {
            "Hisse": ticker,
            "Fiyat": round(fiyat, 2),
            "EMA-21": round(son_bar['EMA_21'], 2),
            "RSI-14": round(son_bar['RSI_14'], 1),
            "ATR Stop": round(son_bar['ATR_Stop'], 2),
            "İz Süren": round(son_bar['Trailing_Stop'], 2),
            "Sinyal": durum
        }
    except:
        return None

# --- ANA EKRAN VE VERİTABANI YÜKLEME ---
st.title("🛡️ Dinamik Quantamental Portföy Radarı")

yuklenen_dosya = st.file_uploader("Portföy Veritabanını (CSV) Yükle", type=["csv"])

if yuklenen_dosya is not None:
    # Veritabanını Oku
    vd = pd.read_csv(yuklenen_dosya)
    st.success(f"{len(vd)} hisselik veritabanı başarıyla yüklendi!")
    
    tab_portfoy, tab_izleme, tab_radar = st.tabs(["💼 Portföyüm", "👁️ İzleme Listem", "📡 BİST Tarayıcı (Radar)"])
    
    with tab_portfoy:
        st.subheader("Aktif Yatırımlar ve Kâr Kalkanları")
        portfoy_hisseleri = vd[vd['Kategori'] == 'Portföy']['Hisse'].tolist()
        if portfoy_hisseleri:
            sonuclar = [hisse_analiz_et(h) for h in portfoy_hisseleri]
            sonuclar = [s for s in sonuclar if s is not None] # Hatalıları temizle
            st.dataframe(pd.DataFrame(sonuclar), use_container_width=True)
        else:
            st.info("Portföy kategorisinde hisse bulunamadı.")
            
    with tab_izleme:
        st.subheader("Pusudaki Hedefler")
        izleme_hisseleri = vd[vd['Kategori'] == 'İzleme']['Hisse'].tolist()
        if izleme_hisseleri:
            sonuclar = [hisse_analiz_et(h) for h in izleme_hisseleri]
            sonuclar = [s for s in sonuclar if s is not None]
            st.dataframe(pd.DataFrame(sonuclar), use_container_width=True)
            
    with tab_radar:
        st.subheader("BİST Fırsat Taraması")
        radar_hisseleri = vd[vd['Kategori'] == 'Radar']['Hisse'].tolist()
        if st.button("🚀 Taramyı Başlat"):
            with st.spinner('Piyasa taranıyor, algoritmalar devrede...'):
                sonuclar = [hisse_analiz_et(h) for h in radar_hisseleri]
                sonuclar = [s for s in sonuclar if s is not None]
                df_radar = pd.DataFrame(sonuclar)
                
                # Sadece "GÜÇLÜ TREND" veren kusursuz kopuşları filtrele
                firsatlar = df_radar[df_radar['Sinyal'].str.contains("GÜÇLÜ")]
                
                if not firsatlar.empty:
                    st.success(f"{len(firsatlar)} adet onaylı kırılım bulundu!")
                    st.dataframe(firsatlar, use_container_width=True)
                else:
                    st.warning("Mevcut parametrelerle güvenli bir alım fırsatı bulunamadı.")
else:
    st.info("Sistemi başlatmak için sol menüden CSV dosyanızı yükleyin. Sütunlar: 'Hisse' ve 'Kategori' olmalıdır.")
