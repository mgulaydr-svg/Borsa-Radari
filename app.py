import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="Quantamental Portföy Kokpiti",
    page_icon="📈",
    layout="wide"
)

# --- Yan Menü: Parametre Kontrolü ---
st.sidebar.header("🎛️ Algoritma Parametreleri")

atr_carpani = st.sidebar.slider("ATR Dalgalanma Tamponu (α)", min_value=0.5, max_value=3.0, value=1.5, step=0.1)
trailing_stop_pct = st.sidebar.slider("İz Süren Stop Oranı (%)", min_value=3.0, max_value=15.0, value=7.0, step=0.5)
rsi_ust_limit = st.sidebar.slider("RSI Aşırı Alım Filtresi", min_value=60, max_value=80, value=65, step=1)
hacim_esigi = st.sidebar.slider("Hacim Artış Şartı (%)", min_value=0, max_value=100, value=20, step=5)

# --- Veri Çekme ve Hesaplama Fonksiyonu ---
@st.cache_data(ttl=300)
def hisse_verisi_hazirla(ticker):
    df = yf.Ticker(ticker).history(period="6mo", interval="1d")
    if df.empty:
        return None
    
    # EMA 21
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # RSI 14
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # ATR 14
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = true_range.rolling(14).mean()
    
    # Dinamik Stop Seviyesi (EMA - alpha * ATR)
    df['ATR_Stop'] = df['EMA_21'] - (atr_carpani * df['ATR_14'])
    
    # İz Süren Stop Seviyesi (Son 20 günün zirvesinden trailing_stop_pct kadar aşağıda)
    df['Rolling_Peak'] = df['High'].rolling(20).max()
    df['Trailing_Stop'] = df['Rolling_Peak'] * (1 - (trailing_stop_pct / 100))
    
    # 20 Günlük Ortalama Hacim
    df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
    
    return df.dropna()

# --- Başlık ve Özet Kartları ---
st.title("🛡️ Quantamental Portföy & Karar Destek Paneli")
st.caption(f"Veri Güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

tab_anchor, tab_radar = st.tabs(["⚓ Anchor Varlıklar (MPARK / KCHOL)", "📡 Taktik Radar & İzleme"])

with tab_anchor:
    st.subheader("Anchor Varlık Analizi: MPARK.IS")
    
    veri = hisse_verisi_hazirla("MPARK.IS")
    
    if veri is not None:
        son_bar = veri.iloc[-1]
        onceki_bar = veri.iloc[-2]
        
        # Temel Metrik Kartları
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Son Fiyat", f"{son_bar['Close']:.2f} TL", f"{(son_bar['Close'] - onceki_bar['Close']):.2f} TL")
        col2.metric("EMA-21", f"{son_bar['EMA_21']:.2f} TL", f"Fark: {(son_bar['Close'] - son_bar['EMA_21']):.2f} TL")
        col3.metric("ATR Kalkan Stop", f"{son_bar['ATR_Stop']:.2f} TL")
        col4.metric("İz Süren Stop", f"{son_bar['Trailing_Stop']:.2f} TL")
        
        # Karar Sinyali Üretimi
        sinyal = "BEKLE"
        renk = "warning"
        
        fiyat_guvenli = son_bar['Close'] > son_bar['ATR_Stop']
        rsi_uygun = son_bar['RSI_14'] < rsi_ust_limit
        hacim_onay = son_bar['Volume'] > (son_bar['Vol_SMA20'] * (1 + hacim_esigi / 100))
        
        if son_bar['Close'] < son_bar['Trailing_Stop']:
            sinyal = "🔴 İZ SÜREN STOP TETİKLENDİ (KÂR KİLİTLE / ÇIK)"
            st.error(sinyal)
        elif son_bar['Close'] < son_bar['ATR_Stop']:
            sinyal = "🔴 ATR KALKAN STOP TETİKLENDİ (ZARAR KES)"
            st.error(sinyal)
        elif son_bar['Close'] > son_bar['EMA_21'] and rsi_uygun:
            sinyal = "🟢 GÜVENLİ BÖLGE (POZİSYONU KORU / EKLE)"
            st.success(sinyal)
        else:
            st.warning("⏳ İZLEMEDE KAL (NÖTR BÖLGE)")
            
        # Görsel Plotly Grafiği
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=veri.index,
            open=veri['Open'], high=veri['High'],
            low=veri['Low'], close=veri['Close'],
            name="MPARK Fiyat"
        ))
        
        fig.add_trace(go.Scatter(
            x=veri.index, y=veri['EMA_21'],
            line=dict(color='orange', width=2),
            name="EMA 21"
        ))
        
        fig.add_trace(go.Scatter(
            x=veri.index, y=veri['ATR_Stop'],
            line=dict(color='red', width=1.5, dash='dot'),
            name="ATR Dinamik Stop"
        ))
        
        fig.add_trace(go.Scatter(
            x=veri.index, y=veri['Trailing_Stop'],
            line=dict(color='purple', width=1.5, dash='dash'),
            name=f"İz Süren Stop (%{trailing_stop_pct})"
        ))
        
        fig.update_layout(
            height=500,
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=30, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.error("MPARK.IS verisi çekilemedi. Bağlantıyı kontrol edin.")

with tab_radar:
    st.subheader("İzleme ve Radar Tablosu")
    radar_listesi = ["KCHOL.IS", "TCELL.IS", "ASELS.IS", "BIMAS.IS", "THYAO.IS"]
    
    radar_ozet = []
    for sembol in radar_listesi:
        d = hisse_verisi_hazirla(sembol)
        if d is not None:
            sb = d.iloc[-1]
            durum = "GÜVENLİ" if sb['Close'] > sb['ATR_Stop'] else "RİSKLİ"
            radar_ozet.append({
                "Hisse": sembol,
                "Fiyat": round(sb['Close'], 2),
                "EMA-21": round(sb['EMA_21'], 2),
                "RSI (14)": round(sb['RSI_14'], 1),
                "ATR Stop": round(sb['ATR_Stop'], 2),
                "Durum": durum
            })
            
    st.dataframe(pd.DataFrame(radar_ozet), use_container_width=True)
