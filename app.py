import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="Master Quant V6.3 | Tüm Fonksiyonlar", layout="wide")

# --- 0. YAHOO ANTI-BLOKAJ (CRUMB) ÇÖZÜMÜ ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# --- 1. SABİTLER VE STRATEJİLER ---
MADEN_EVRENİ = ["GLDTR.IS", "GMSTR.IS"]
VEKİL_ENDEKS = ["KCHOL.IS", "TCELL.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS", "AKBNK.IS", "ISCTR.IS"]

STRATEJILER = {
    "🛡️ KALKAN": {"fk": 12.0, "pddd": 3.0, "rsi_min": 40, "rsi_max": 60, "ema": 11, "vol": 20, "iz": 5.0, "atr": 1.2},
    "🚀 AVCI":   {"fk": 30.0, "pddd": 8.0, "rsi_min": 50, "rsi_max": 75, "ema": 21, "vol": 50, "iz": 8.0, "atr": 1.5},
    "🐆 PANTER": {"fk": 15.0, "pddd": 5.0, "rsi_min": 45, "rsi_max": 70, "ema": 21, "vol": 40, "iz": 12.0, "atr": 2.5},
    "🦅 ANKA":   {"fk": 8.0,  "pddd": 1.5, "rsi_min": 30, "rsi_max": 45, "ema": 21, "vol": 50, "iz": 10.0, "atr": 2.0}
}

# --- 2. MAKRO REJİM MOTORU ---
@st.cache_data(ttl=600)
def rejim_motorunu_calistir():
    try:
        veri = yf.download(VEKİL_ENDEKS + ["XU100.IS"], period="2y", interval="1d", progress=False, session=session)['Close']
        if veri.empty: return "NÖTR", {}, "", {}
        
        xu100 = veri['XU100.IS'].dropna()
        ema50 = xu100.ewm(span=50, adjust=False).mean()
        ema200 = xu100.ewm(span=200, adjust=False).mean()
        
        returns = xu100.pct_change().dropna()
        volatilite_20g = returns.rolling(20).std() * np.sqrt(252)
        vol_yuzdelik = (volatilite_20g.tail(252).rank(pct=True).iloc[-1]) * 100
        
        son_20g_zirve = xu100.tail(20).max()
        drawdown_20g = ((xu100.iloc[-1] - son_20g_zirve) / son_20g_zirve) * 100
        
        vekil_fiyatlar = veri[VEKİL_ENDEKS].dropna()
        vekil_ema200 = vekil_fiyatlar.ewm(span=200, adjust=False).mean()
        genislik_orani = (vekil_fiyatlar.iloc[-1] > vekil_ema200.iloc[-1]).sum() / len(VEKİL_ENDEKS) * 100
        
        son_fiyat = xu100.iloc[-1]
        e200_deger = ema200.iloc[-1]
        e50_deger = ema50.iloc[-1]
        
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
            
        return rejim, tahsis, risk, {"Fiyat": round(son_fiyat, 2), "Piyasa Genişliği": round(genislik_orani, 1), "Volatilite (Yüzdelik)": round(vol_yuzdelik, 1)}
    except:
        return "BİLİNMİYOR", {}, "", {}

rejim_adi, tahsis_plani, risk_butcesi, makro_metrikler = rejim_motorunu_calistir()

# --- 3. SOL MENÜ (AYARLAR) ---
st.sidebar.markdown(f"### 🌐 Makro Rejim: **{rejim_adi}**")
st.sidebar.caption(f"İşlem Riski: {risk_butcesi}")
st.sidebar.markdown("---")

st.sidebar.header("📋 Varlık Yönetimi")
portfoy_girdisi = st.sidebar.text_area("💼 Portföy Hisseleri", "KCHOL.IS, TCELL.IS, DESA.IS, CLEBI.IS, KONTR.IS, BRSAN.IS, OTKAR.IS, AKSEN.IS, GLRMK.IS")
izleme_girdisi = st.sidebar.text_area("👁️ İzleme Listesi", "MPARK.IS, TURSG.IS, ISCTR.IS, AKBNK.IS, ALARK.IS, ARDYZ.IS, CVKMD.IS, MIATK.IS, ORGE.IS, YEOTK.IS")

st.sidebar.markdown("---")
st.sidebar.header("🎯 BİST Tarama Stratejisi")
secilen_tarama_stratejisi = st.sidebar.selectbox("Tüm Borsayı Tarama Profili:", list(STRATEJILER.keys()))

# --- 4. PORTFÖY/İZLEME İÇİN ÇOKLU SİNYAL MOTORU ---
@st.cache_data(ttl=300)
def varlik_analizi(ticker, varlik_tipi="Hisse"):
    try:
        data = yf.Ticker(ticker, session=session)
        df = data.history(period="1y", interval="1d")
        if len(df) < 50: return None
        
        son_fiyat = df['Close'].iloc[-1]
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        delta = df['Close'].diff()
        rs = delta.where(delta > 0, 0.0).rolling(14).mean() / -delta.where(delta < 0, 0.0).rolling(14).mean().replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        tr = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift()).abs(), (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        atr = df['ATR_14'].iloc[-1]
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        
        ilk_stop_atr = df['EMA21'].iloc[-1] - (2.0 * atr)
        iz_suren_atr = df['High'].rolling(20).max().iloc[-1] - (3.0 * atr)
        getiri_6a = ((son_fiyat - df['Close'].iloc[-126]) / df['Close'].iloc[-126]) * 100 if len(df) >= 126 else 0
        
        fk_val, pddd_val = 0.0, 0.0
        fk_str, pddd_str = "-", "-"
        if varlik_tipi == "Hisse":
            try:
                info = data.info
                if info:
                    fk_val = float(info.get('trailingPE') or 0)
                    pddd_val = float(info.get('priceToBook') or 0)
                    fk_str, pddd_str = round(fk_val, 1), round(pddd_val, 1)
            except: pass 

        sonuc = {
            "Varlık": ticker,
            "Fiyat": round(son_fiyat, 2),
            "F/K": fk_str,
            "PD/DD": pddd_str,
            "RSI": round(rsi, 1),
            "6A Momentum (%)": round(getiri_6a, 1),
            "İlk Stop (2 ATR)": round(ilk_stop_atr, 2),
            "İz Süren (3 ATR)": round(iz_suren_atr, 2)
        }

        for ad, p in STRATEJILER.items():
            ema_t = df['Close'].ewm(span=p['ema'], adjust=False).mean().iloc[-1]
            atr_s = df['EMA21'].iloc[-1] - (p['atr'] * df['ATR_14'].iloc[-1])
            trail = df['High'].rolling(20).max().iloc[-1] * (1 - (p['iz'] / 100))
            
            if son_fiyat < trail or son_fiyat < atr_s: 
                sinyal = "🔴 SAT"
            else:
                tek_ok = (son_fiyat > ema_t) and (p['rsi_min'] <= rsi <= p['rsi_max']) and (df['Volume'].iloc[-1] >= df['Vol_SMA20'].iloc[-1] * (1 + p['vol']/100))
                tem_ok = True if varlik_tipi == "Emtia" else ((0 < fk_val <= p['fk']) and (0 < pddd_val <= p['pddd']))
                
                if tek_ok and tem_ok: 
                    sinyal = "🚫 YASAK (Rejim)" if "DÜŞÜŞ" in rejim_adi or "KRİZ" in rejim_adi else "🟢 AL"
                elif tek_ok and not tem_ok: 
                    sinyal = "⚠️ PAHALI"
                else: 
                    sinyal = "⏳ BEKLE"
            
            sonuc[ad.split(" ")[0]] = sinyal

        return sonuc
    except: return None

def listeyi_islet(girdi_metni):
    hisseler = [x.strip().upper() for x in girdi_metni.split(",") if x.strip()]
    if not hisseler: return None
    sonuclar = []
    with st.spinner("Matris hesaplanıyor..."):
        for h in hisseler:
            if not h.endswith(".IS"): h += ".IS"
            res = varlik_analizi(h, "Hisse")
            if res: sonuclar.append(res)
    return pd.DataFrame(sonuclar) if sonuclar else None

# --- 5. HIZLI TARAMA MOTORU (RADAR İÇİN LAZY EVALUATION) ---
@st.cache_data(ttl=300)
def radar_analizi(ticker, strat_name):
    try:
        data = yf.Ticker(ticker, session=session)
        df = data.history(period="6mo", interval="1d")
        if len(df) < 50: return None
        
        p = STRATEJILER[strat_name]
        df['EMA_Trend'] = df['Close'].ewm(span=p['ema'], adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        delta = df['Close'].diff()
        rs = delta.where(delta > 0, 0.0).rolling(14).mean() / -delta.where(delta < 0, 0.0).rolling(14).mean().replace(0, np.nan)
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        tr = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift()).abs(), (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        
        df['ATR_Stop'] = df['EMA_21'] - (p['atr'] * df['ATR_14'])
        df['Trailing_Stop'] = df['High'].rolling(20).max() * (1 - (p['iz'] / 100))
        
        son = df.iloc[-1]
        fiyat = son['Close']
        
        teknik_ok = (fiyat > son['EMA_Trend']) and (p['rsi_min'] <= son['RSI_14'] <= p['rsi_max']) and (son['Volume'] >= son['Vol_SMA20'] * (1 + p['vol'] / 100))
        stop_oldu = (fiyat < son['Trailing_Stop']) or (fiyat < son['ATR_Stop'])
        
        fk, pddd, temel_ok = 0.0, 0.0, False
        if not stop_oldu and teknik_ok:
            try:
                info = data.info
                if info:
                    fk = float(info.get('trailingPE') or 0)
                    pddd = float(info.get('priceToBook') or 0)
                    temel_ok = (0 < fk <= p['fk']) and (0 < pddd <= p['pddd'])
            except: pass 
        
        if stop_oldu: durum = "🔴 SAT"
        elif teknik_ok and temel_ok: durum = "🚫 YASAK (Rejim)" if "DÜŞÜŞ" in rejim_adi or "KRİZ" in rejim_adi else "🟢 KUSURSUZ ONAY"
        elif teknik_ok and not temel_ok: durum = "⚠️ ŞİŞKİN TEMEL"
        else: durum = "⏳ BEKLE"
        
        return {"Hisse": ticker, "Fiyat": round(fiyat,2), "F/K": round(fk,1) if fk else "-", "Sinyal": durum}
    except: return None

# --- 6. ARAYÜZ (KOKPİT) ---
st.title("🏛️ Master Quant Fon Yönetim Sistemi V6.3")

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
tab_portfoy, tab_izleme, tab_maden, tab_tarama, tab_sorgu = st.tabs([
    "💼 Portföyüm", 
    "👁️ İzleme Listem", 
    "🪙 Maden (Hedge)", 
    "📡 BİST Tarayıcı", 
    "🔍 Serbest Sorgu"
])

with tab_portfoy:
    st.subheader("Aktif Yatırımlar (Çoklu Sinyal Matrisi)")
    df_port = listeyi_islet(portfoy_girdisi)
    if df_port is not None: st.dataframe(df_port.sort_values(by="6A Momentum (%)", ascending=False), use_container_width=True)

with tab_izleme:
    st.subheader("Pusudaki Hedefler (Çoklu Sinyal Matrisi)")
    df_iz = listeyi_islet(izleme_girdisi)
    if df_iz is not None: st.dataframe(df_iz.sort_values(by="6A Momentum (%)", ascending=False), use_container_width=True)

with tab_maden:
    st.subheader("Kriz Kalkanları (Temel Analizden Muaf)")
    if st.button("Madenleri Analiz Et"):
        with st.spinner("Emtia verileri çekiliyor..."):
            maden_sonuclar = [varlik_analizi(m, "Emtia") for m in MADEN_EVRENİ]
            df_maden = pd.DataFrame([s for s in maden_sonuclar if s])
            if not df_maden.empty:
                df_maden = df_maden.drop(columns=["F/K", "PD/DD"])
                st.dataframe(df_maden, use_container_width=True)

with tab_tarama:
    st.subheader(f"Tüm Borsayı Tara: {secilen_tarama_stratejisi}")
    ticker_dosyasi = st.file_uploader("tickers.csv dosyasını yükleyin", type=["csv"])
    if ticker_dosyasi is not None:
        tum_hisseler = pd.read_csv(ticker_dosyasi)['Tickers'].dropna().tolist()
        if st.button("🚀 Dev Taramayı Başlat"):
            metin = st.empty()
            cubuk = st.progress(0)
            firsatlar = []
            toplam = len(tum_hisseler)
            for i, h in enumerate(tum_hisseler):
                metin.text(f"Taranıyor: {h} ({i+1}/{toplam})")
                sonuc = radar_analizi(h, secilen_tarama_stratejisi)
                if sonuc and ("ONAY" in sonuc['Sinyal'] or "YASAK" in sonuc['Sinyal']):
                    firsatlar.append(sonuc)
                cubuk.progress((i + 1) / toplam)
            metin.text("Tarama Tamamlandı!")
            if firsatlar:
                st.success(f"{secilen_tarama_stratejisi} profiline uyan {len(firsatlar)} hisse bulundu.")
                st.dataframe(pd.DataFrame(firsatlar), use_container_width=True)
            else:
                st.warning("Bu profilin katı şartlarını sağlayan hisse bulunamadı.")

with tab_sorgu:
    st.subheader("Hızlı Hisse Röntgeni (Tüm Stratejiler)")
    aranan = st.text_input("Hisse Kodu (Örn: ARDYZ):").upper()
    if aranan:
        if not aranan.endswith(".IS"): aranan += ".IS"
        with st.spinner("Röntgen çekiliyor..."):
            sonuc = varlik_analizi(aranan, "Hisse")
            if sonuc:
                st.dataframe(pd.DataFrame([sonuc]), use_container_width=True)
