import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Quantamental Fon Radarı", layout="wide")

# --- SOL MENÜ: PARAMETRELER ---
st.sidebar.header("🎛️ Teknik Filtreler")
atr_carpani = st.sidebar.slider("ATR Tamponu (α)", 0.5, 3.0, 1.5, 0.1)
trailing_stop_pct = st.sidebar.slider("İz Süren Stop (%)", 3.0, 15.0, 7.0, 0.5)
rsi_limit = st.sidebar.slider("Maksimum RSI", 50, 85, 65, 1)

st.sidebar.markdown("---")
st.sidebar.header("🏛️ Temel Filtreler")
max_fk = st.sidebar.slider("Maksimum F/K", 0.0, 50.0, 15.0, 1.0)
max_pddd = st.sidebar.slider("Maksimum PD/DD", 0.0, 15.0, 5.0, 0.5)

# --- MATEMATİK VE VERİ MOTORU ---
@st.cache_data(ttl=300)
def hisse_analiz_et(ticker):
    try:
        hisse = yf.Ticker(ticker)
        df = hisse.history(period="3mo", interval="1d")
        if df.empty: return None
        
        # Temel Verileri Çek
        info = hisse.info
        fk_orani = info.get('trailingPE', 0)
        pddd_orani = info.get('priceToBook', 0)
        
        if fk_orani is None: fk_orani = 0
        if pddd_orani is None: pddd_orani = 0

        # Teknik Hesaplamalar
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
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
        
        df['ATR_Stop'] = df['EMA_21'] - (atr_carpani * df['ATR_14'])
        df['Trailing_Stop'] = df['High'].rolling(20).max() * (1 - (trailing_stop_pct / 100))
        
        son_bar = df.iloc[-1]
        fiyat = son_bar['Close']
        
        # Sinyal Mantığı
        teknik_onay = (fiyat > df['EMA_21'].iloc[-1]) and (fiyat > son_bar['ATR_Stop']) and (son_bar['RSI_14'] < rsi_limit)
        temel_onay = (0 < fk_orani <= max_fk) and (0 < pddd_orani <= max_pddd)
        
        if teknik_onay and temel_onay:
            durum = "🟢 KUSURSUZ QUANTAMENTAL KOPUŞ"
        elif teknik_onay and not temel_onay:
            durum = "⚠️ TEKNİK İYİ AMA TEMEL PAHALI"
        elif fiyat < son_bar['Trailing_Stop'] or fiyat < son_bar['ATR_Stop']:
            durum = "🔴 STOP BÖLGESİ (SAT)"
        else:
            durum = "⏳ BEKLE"
            
        return {
            "Hisse": ticker,
            "Fiyat": round(fiyat, 2),
            "F/K": round(fk_orani, 2),
            "PD/DD": round(pddd_orani, 2),
            "EMA-21": round(son_bar['EMA_21'], 2),
            "RSI": round(son_bar['RSI_14'], 1),
            "Sinyal": durum
        }
    except:
        return None

# --- ANA EKRAN ---
st.title("🛡️ BİST Quantamental Tarayıcı")

tab_tarama, tab_sorgu = st.tabs(["📡 BİST Tüm Piyasa Taraması", "🔍 Tekil Hisse Sorgusu"])

with tab_tarama:
    st.subheader("tickers.csv ile Tüm Borsayı Tara")
    ticker_dosyasi = st.file_uploader("tickers.csv dosyasını yükleyin", type=["csv"])
    
    if ticker_dosyasi is not None:
        df_tickers = pd.read_csv(ticker_dosyasi)
        
        if 'Tickers' in df_tickers.columns:
            tum_hisseler = df_tickers['Tickers'].dropna().tolist()
            st.info(f"Sistemde toplam {len(tum_hisseler)} hisse senedi algılandı.")
            
            if st.button("🚀 Dev Taramayı Başlat"):
                ilerleme_metni = st.empty()
                ilerleme_cubugu = st.progress(0)
                
                firsatlar = []
                toplam_sayi = len(tum_hisseler)
                
                for i, hisse in enumerate(tum_hisseler):
                    ilerleme_metni.text(f"Taranıyor: {hisse} ({i+1}/{toplam_sayi})")
                    sonuc = hisse_analiz_et(hisse)
                    
                    # Sadece tekniği ve temeli mükemmel olanları listeye al
                    if sonuc is not None and "KUSURSUZ" in sonuc['Sinyal']:
                        firsatlar.append(sonuc)
                        
                    ilerleme_cubugu.progress((i + 1) / toplam_sayi)
                
                ilerleme_metni.text("Tarama Tamamlandı!")
                
                if firsatlar:
                    st.success(f"Bütün BİST içinde teknik ve temel şartlarınızı sağlayan {len(firsatlar)} adet elit hisse bulundu!")
                    st.dataframe(pd.DataFrame(firsatlar).sort_values(by="F/K", ascending=True), use_container_width=True)
                else:
                    st.warning("Mevcut şartlarınızı sağlayan hiçbir hisse bulunamadı. Sol menüden filtreleri (Örn: Maksimum F/K) gevşetmeyi deneyin.")
        else:
            st.error("Yüklenen dosyada 'Tickers' adlı bir sütun bulunamadı! Lütfen doğru dosyayı yükleyin.")

with tab_sorgu:
    st.subheader("Anlık Hızlı Hisse Taraması")
    aranan_hisse = st.text_input("Hisse Kodunu Girin (Örn: MPARK.IS veya KCHOL):").upper()
    
    if aranan_hisse:
        if not aranan_hisse.endswith(".IS"):
            aranan_hisse += ".IS" # Uzantıyı unutsan bile sistem otomatik ekler
            
        with st.spinner('Analiz ediliyor...'):
            sonuc = hisse_analiz_et(aranan_hisse)
            if sonuc is not None:
                st.success("Analiz Tamamlandı!")
                st.dataframe(pd.DataFrame([sonuc]), use_container_width=True)
            else:
                st.error("Hisse bulunamadı veya Yahoo Finance'den veri çekilemedi.")
