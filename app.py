import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Master Quant V6.1 | Rejim & Skor Motoru", layout="wide")

# --- 1. VARLIK EVRENİ & PARAMETRELER ---
HİSSE_EVRENİ = ["KCHOL.IS", "ASTOR.IS", "TCELL.IS", "DESA.IS", "CLEBI.IS", "KONTR.IS", "BRSAN.IS", "OTKAR.IS", "AKSEN.IS", "GLRMK.IS", "MPARK.IS", "TURSG.IS", "ISCTR.IS", "AKBNK.IS", "ALARK.IS", "ARDYZ.IS", "CVKMD.IS", "MIATK.IS", "ORGE.IS", "YEOTK.IS"]
MADEN_EVRENİ = ["GLDTR.IS", "GMSTR.IS"]

# Piyasa Genişliği (Breadth) için Hızlı Vekil Endeks (BİST'in lokomotifleri + Kendi Evrenimiz)
VEKİL_ENDEKS = list(set(HİSSE_EVRENİ + ["BIMAS.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"]))

# --- 2. GELİŞMİŞ MAKRO REJİM MOTORU (Piyasa Genişliği Dahil) ---
@st.cache_data(ttl=600)
def rejim_motorunu_calistir():
    try:
        # XU100 ve Vekil Hisseleri Tek Seferde Hızlıca Çek
        veri = yf.download(VEKİL_ENDEKS + ["XU100.IS"], period="2y", interval="1d", progress=False)['Close']
        if veri.empty: return "NÖTR", {}, "", {}
        
        xu100 = veri['XU100.IS'].dropna()
        
        # 1. Trend Bileşeni
        ema50 = xu100.ewm(span=50, adjust=False).mean()
        ema200 = xu100.ewm(span=200, adjust=False).mean()
        
        # 2. Volatilite Bileşeni
        returns = xu100.pct_change().dropna()
        volatilite_20g = returns.rolling(20).std() * np.sqrt(252)
        vol_yuzdelik = (volatilite_20g.tail(252).rank(pct=True).iloc[-1]) * 100
        
        # 3. Kriz Şartı (Drawdown)
        son_20g_zirve = xu100.tail(20).max()
        drawdown_20g = ((xu100.iloc[-1] - son_20g_zirve) / son_20g_zirve) * 100
        
        # 4. Piyasa Genişliği (Market Breadth - EMA200 Üzerindeki Hisselerin Oranı)
        vekil_fiyatlar = veri[VEKİL_ENDEKS].dropna()
        vekil_ema200 = vekil_fiyatlar.ewm(span=200, adjust=False).mean()
        genislik_orani = (vekil_fiyatlar.iloc[-1] > vekil_ema200.iloc[-1]).sum() / len(VEKİL_ENDEKS) * 100
        
        son_fiyat = xu100.iloc[-1]
        e200_deger = ema200.iloc[-1]
        e50_deger = ema50.iloc[-1]
        
        # Karar Ağacı
        if drawdown_20g <= -10.0 or vol_yuzdelik >= 90.0:
            rejim = "🚨 KRİZ MODU"
            tahsis = {"Hisse": "%0", "Nakit/PPF": "%70", "Altın/Gümüş": "%30"}
            risk = "%0 (Yeni Alım Yok)"
        elif son_fiyat < (e200_deger * 0.98) or e50_deger < e200_deger or genislik_orani < 40.0:
            rejim = "🔴 DÜŞÜŞ (Ayı Piyasası)"
            tahsis = {"Hisse": "%0 - %15", "Nakit/PPF": "%50", "Altın/Gümüş": "%35"}
            risk = "İşlem Başına %0.25"
        elif (son_fiyat > e200_deger * 1.02) and (e50_deger > e200_deger) and (genislik_orani > 55.0):
            rejim = "🟢 YÜKSELİŞ (Boğa Piyasası)"
            tahsis = {"Hisse": "%70 - %100", "Nakit/PPF": "%0", "Altın/Gümüş": "%0 - %10"}
            risk = "İşlem Başına %0.75"
        else:
            rejim = "🟡 NÖTR (Testere)"
            tahsis = {"Hisse": "%30 - %50", "Nakit/PPF": "%30", "Altın/Gümüş": "%20"}
            risk = "İşlem Başına %0.50"
            
        metrikler = {
            "Fiyat": round(son_fiyat, 2),
            "Piyasa Genişliği": round(genislik_orani, 1),
            "Volatilite (Yüzdelik)": round(vol_yuzdelik, 1),
            "20G Drawdown": round(drawdown_20g, 2)
        }
        return rejim, tahsis, risk, metrikler
    except Exception as e:
        return f"HATA: {e}", {}, "", {}

rejim_adi, tahsis_plani, risk_butcesi, makro_metrikler = rejim_motorunu_calistir()

# --- 3. DİNAMİK SKORLAMA VE STOP MOTORU ---
@st.cache_data(ttl=300)
def varlik_analizi(ticker, varlik_tipi="Hisse"):
    try:
        data = yf.Ticker(ticker)
        df = data.history(period="1y", interval="1d")
        if len(df) < 200: return None
        
        son_fiyat = df['Close'].iloc[-1]
        
        # Temel Teknikler
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        delta = df['Close'].diff()
        rs = delta.where(delta > 0, 0.0).rolling(14).mean() / -delta.where(delta < 0, 0.0).rolling(14).mean().replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        tr = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift()).abs(), (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        atr = df['ATR_14'].iloc[-1]
        
        # Volatilite Tabanlı Dinamik Stoplar (Dokümana Göre)
        ilk_stop_atr = df['EMA21'].iloc[-1] - (2.0 * atr)
        iz_suren_atr = df['High'].rolling(20).max().iloc[-1] - (3.0 * atr)
        
        # Getiri Momentum (6 Aylık)
        getiri_6a = ((son_fiyat - df['Close'].iloc[-126]) / df['Close'].iloc[-126]) * 100 if len(df) >= 126 else 0
        
        sonuc = {
            "Varlık": ticker,
            "Fiyat": round(son_fiyat, 2),
            "RSI": round(rsi, 1),
            "Trend (EMA50)": "🟢 Üzerinde" if son_fiyat > df['EMA50'].iloc[-1] else "🔴 Altında",
            "6A Momentum (%)": round(getiri_6a, 1),
            "ATR": round(atr, 2),
            "İlk Stop (2 ATR)": round(ilk_stop_atr, 2),
            "İz Süren Stop (3 ATR)": round(iz_suren_atr, 2)
        }
        
        # Hisse ise Temel Verileri Ekle
        if varlik_tipi == "Hisse":
            info = data.info
            sonuc["F/K"] = round(info.get('trailingPE', 0) or 0, 1)
            sonuc["PD/DD"] = round(info.get('priceToBook', 0) or 0, 1)
            
        return sonuc
    except:
        return None

# --- 4. ARAYÜZ (KOKPİT) ---
st.title("🏛️ Master Quant Fon Yönetim Sistemi V6.1")

# Makro Rejim Paneli
st.markdown("### 🌐 Dinamik Rejim ve Varlık Tahsisi")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Mevcut Rejim", rejim_adi)
col2.metric("İşlem Risk Bütçesi", risk_butcesi)
col3.metric("Piyasa Genişliği", f"%{makro_metrikler.get('Piyasa Genişliği', 0)} (EMA200 Üstü)")
col4.metric("BİST100 Volatilite", f"%{makro_metrikler.get('Volatilite (Yüzdelik)', 0)} Yüzdelik")

st.markdown("#### 🎯 Rejime Uygun İdeal Varlık Dağılımı")
c_hisse, c_altin, c_nakit = st.columns(3)
c_hisse.info(f"📈 **Hisse Senedi:** {tahsis_plani.get('Hisse', '%0')}")
c_altin.warning(f"🪙 **Altın/Gümüş:** {tahsis_plani.get('Altın/Gümüş', '%0')}")
c_nakit.success(f"💵 **Nakit/PPF:** {tahsis_plani.get('Nakit/PPF', '%0')}")

st.markdown("---")

tab_hisse, tab_maden = st.tabs(["📊 Hisse Senedi Skor ve Stop Tablosu", "🪙 Kıymetli Madenler (Hedge)"])

with tab_hisse:
    st.subheader("Hisse Portföyü Göreli Momentum ve ATR Stoplar")
    if st.button("Hisseleri Analiz Et"):
        with st.spinner("Hisseler taranıyor..."):
            hisse_sonuclar = [varlik_analizi(h, "Hisse") for h in HİSSE_EVRENİ]
            df_hisse = pd.DataFrame([s for s in hisse_sonuclar if s])
            if not df_hisse.empty:
                # 6 Aylık momentuma göre sırala
                df_hisse = df_hisse.sort_values(by="6A Momentum (%)", ascending=False)
                # Tablodaki sütun sırasını düzenle
                df_hisse = df_hisse[["Varlık", "Fiyat", "F/K", "PD/DD", "RSI", "Trend (EMA50)", "6A Momentum (%)", "ATR", "İlk Stop (2 ATR)", "İz Süren Stop (3 ATR)"]]
                st.dataframe(df_hisse, use_container_width=True)

with tab_maden:
    st.subheader("Kriz Kalkanları: Altın ve Gümüş BYF'leri")
    if st.button("Madenleri Analiz Et"):
        with st.spinner("Emtia verileri çekiliyor..."):
            maden_sonuclar = [varlik_analizi(m, "Emtia") for m in MADEN_EVRENİ]
            df_maden = pd.DataFrame([s for s in maden_sonuclar if s])
            if not df_maden.empty:
                df_maden = df_maden[["Varlık", "Fiyat", "RSI", "Trend (EMA50)", "6A Momentum (%)", "ATR", "İlk Stop (2 ATR)", "İz Süren Stop (3 ATR)"]]
                st.dataframe(df_maden, use_container_width=True)
