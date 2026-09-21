import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Quantamental Master Dashboard V5.1", layout="wide")

# --- 1. STRATEJİ SÖZLÜĞÜ (PARAMETRELER) ---
STRATEJILER = {
    "🛡️ KALKAN": {"fk": 12.0, "pddd": 3.0, "rsi_min": 40, "rsi_max": 60, "ema": 11, "vol": 20, "iz": 5.0, "atr": 1.2},
    "🚀 AVCI":   {"fk": 30.0, "pddd": 8.0, "rsi_min": 50, "rsi_max": 75, "ema": 21, "vol": 50, "iz": 8.0, "atr": 1.5},
    "🐆 PANTER": {"fk": 15.0, "pddd": 5.0, "rsi_min": 45, "rsi_max": 70, "ema": 21, "vol": 40, "iz": 12.0, "atr": 2.5},
    "🦅 ANKA":   {"fk": 8.0,  "pddd": 1.5, "rsi_min": 30, "rsi_max": 45, "ema": 21, "vol": 50, "iz": 10.0, "atr": 2.0}
}

# --- 2. MAKRO REJİM MOTORU ---
@st.cache_data(ttl=600)
def makro_rejimi_belirle():
    try:
        xu100 = yf.Ticker("XU100.IS").history(period="1y", interval="1d")
        if xu100.empty: return "Nötr", 0
        close = xu100['Close']
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
        son_fiyat = close.iloc[-1]
        if (son_fiyat > ema200 * 1.02) and (ema50 > ema200): return "YÜKSELİŞ 🟢", son_fiyat
        elif son_fiyat < ema200 * 0.98: return "DÜŞÜŞ 🔴", son_fiyat
        else: return "NÖTR 🟡", son_fiyat
    except: return "BİLİNMİYOR", 0

rejim, xu100_fiyat = makro_rejimi_belirle()

# --- 3. SOL MENÜ ---
st.sidebar.markdown(f"### 🌐 Makro Rejim: **{rejim}**")
st.sidebar.caption(f"BİST 100 Güncel: {xu100_fiyat:.2f}")
st.sidebar.markdown("---")

st.sidebar.header("📉 Makro Ekonomi")
# Son 5 yılın tahmini kümülatif enflasyonu (Değiştirilebilir)
enflasyon_orani = st.sidebar.number_input("5 Yıllık Kümülatif Enflasyon (%)", min_value=0, max_value=5000, value=1450, step=50)

st.sidebar.markdown("---")
st.sidebar.header("📋 Varlık Yönetimi")
portfoy_girdisi = st.sidebar.text_area("💼 Portföy Hisseleri", "KCHOL.IS, TCELL.IS, DESA.IS, CLEBI.IS, KONTR.IS, BRSAN.IS, OTKAR.IS, AKSEN.IS, GLRMK.IS")
izleme_girdisi = st.sidebar.text_area("👁️ İzleme Listesi", "ASTOR.IS, MPARK.IS, TURSG.IS, ISCTR.IS, AKBNK.IS, ALARK.IS, ARDYZ.IS, CVKMD.IS, MIATK.IS, ORGE.IS, YEOTK.IS")

st.sidebar.markdown("---")
st.sidebar.header("🎯 BİST Tarama Stratejisi")
secilen_tarama_stratejisi = st.sidebar.selectbox("Tarama Profilini Seçin:", list(STRATEJILER.keys()))

# --- 4. BACKTEST & ÇOKLU SİNYAL MOTORU ---
def strateji_simulasyonu(df, p_ema, p_atr, p_iz_suren):
    sermaye = 100000.0
    pozisyonda_mi, lot = False, 0
    df_sim = df.copy()
    df_sim['EMA_Trend'] = df_sim['Close'].ewm(span=p_ema, adjust=False).mean()
    df_sim['EMA_21'] = df_sim['Close'].ewm(span=21, adjust=False).mean() 
    tr = pd.concat([df_sim['High'] - df_sim['Low'], (df_sim['High'] - df_sim['Close'].shift()).abs(), (df_sim['Low'] - df_sim['Close'].shift()).abs()], axis=1).max(axis=1)
    df_sim['ATR_14'] = tr.rolling(14).mean()
    df_sim['ATR_Stop'] = df_sim['EMA_21'] - (p_atr * df_sim['ATR_14'])
    df_sim['Trailing_Stop'] = df_sim['High'].rolling(20).max() * (1 - (p_iz_suren / 100))
    
    for i in range(50, len(df_sim)):
        fiyat = df_sim['Close'].iloc[i]
        if not pozisyonda_mi and fiyat > df_sim['EMA_Trend'].iloc[i]:
            pozisyonda_mi = True
            lot = sermaye / fiyat
        elif pozisyonda_mi and (fiyat < df_sim['Trailing_Stop'].iloc[i] or fiyat < df_sim['ATR_Stop'].iloc[i]):
            pozisyonda_mi = False
            sermaye = lot * fiyat
            lot = 0
    if pozisyonda_mi: sermaye = lot * df_sim['Close'].iloc[-1]
    return ((sermaye - 100000) / 100000) * 100

@st.cache_data(ttl=300)
def coklu_analiz_ve_backtest(ticker):
    try:
        hisse = yf.Ticker(ticker)
        # Period 5y olarak güncellendi
        df = hisse.history(period="5y", interval="1d") 
        if len(df) < 50: return None
        
        info = hisse.info
        fk = info.get('trailingPE', 0) or 0
        pddd = info.get('priceToBook', 0) or 0
        fiyat = df['Close'].iloc[-1]
        
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        delta = df['Close'].diff()
        rs = delta.where(delta > 0, 0.0).rolling(14).mean() / -delta.where(delta < 0, 0.0).rolling(14).mean().replace(0, np.nan)
        df['RSI_14'] = 100 - (100 / (1 + rs))
        tr = pd.concat([df['High'] - df['Low'], (df['High'] - df['Close'].shift()).abs(), (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(14).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        son = df.iloc[-1]
        
        sonuc_satiri = {"Hisse": ticker, "Fiyat": round(fiyat, 2), "F/K": round(fk, 1)}
        
        # Canlı Sinyaller
        for ad, p in STRATEJILER.items():
            ema_t = df['Close'].ewm(span=p['ema'], adjust=False).mean().iloc[-1]
            atr_s = df['EMA_21'].iloc[-1] - (p['atr'] * df['ATR_14'].iloc[-1])
            trail = df['High'].rolling(20).max().iloc[-1] * (1 - (p['iz'] / 100))
            
            if fiyat < trail or fiyat < atr_s: sinyal = "🔴 SAT"
            else:
                tek_ok = (fiyat > ema_t) and (p['rsi_min'] <= son['RSI_14'] <= p['rsi_max']) and (son['Volume'] >= son['Vol_SMA20'] * (1 + p['vol']/100))
                tem_ok = (0 < fk <= p['fk']) and (0 < pddd <= p['pddd'])
                
                if tek_ok and tem_ok: sinyal = "🚫 YASAK" if "DÜŞÜŞ" in rejim else "🟢 AL"
                elif tek_ok and not tem_ok: sinyal = "⚠️ ŞİŞKİN"
                else: sinyal = "⏳ BEKLE"
            
            sonuc_satiri[f"{ad[:2]} Sinyal"] = sinyal # Tabloya sığması için başlıklar kısaltıldı

        # 5 Yıllık Backtest
        al_tut_getiri = ((fiyat - df['Close'].iloc[50]) / df['Close'].iloc[50]) * 100
        getiriler = {"AL-TUT": al_tut_getiri}
        
        getiriler["🛡️ KALKAN"] = strateji_simulasyonu(df, STRATEJILER["🛡️ KALKAN"]['ema'], STRATEJILER["🛡️ KALKAN"]['atr'], STRATEJILER["🛡️ KALKAN"]['iz'])
        getiriler["🚀 AVCI"] = strateji_simulasyonu(df, STRATEJILER["🚀 AVCI"]['ema'], STRATEJILER["🚀 AVCI"]['atr'], STRATEJILER["🚀 AVCI"]['iz'])
        getiriler["🐆 PANTER"] = strateji_simulasyonu(df, STRATEJILER["🐆 PANTER"]['ema'], STRATEJILER["🐆 PANTER"]['atr'], STRATEJILER["🐆 PANTER"]['iz'])
        
        lider = max(getiriler, key=getiriler.get)
        max_nominal = getiriler[lider]
        
        # Fisher Denklemi ile Enflasyondan Arındırılmış Reel Getiri
        reel_getiri = (((1 + (max_nominal / 100)) / (1 + (enflasyon_orani / 100))) - 1) * 100
        
        sonuc_satiri["🏆 5Y Lider"] = lider
        sonuc_satiri["Nominal (%)"] = round(max_nominal, 1)
        sonuc_satiri["Reel Getiri (%)"] = round(reel_getiri, 1)
        
        return sonuc_satiri
    except: return None

def portfoy_goster(girdi_metni):
    hisseler = [x.strip().upper() for x in girdi_metni.split(",") if x.strip()]
    if not hisseler: return None
    sonuclar = []
    with st.spinner('5 Yıllık Backtest & Enflasyon Analizi Çalışıyor...'):
        for h in hisseler:
            if not h.endswith(".IS"): h += ".IS"
            res = coklu_analiz_ve_backtest(h)
            if res: sonuclar.append(res)
    return pd.DataFrame(sonuclar) if sonuclar else None

# --- 5. TEKİL TARAMA MOTORU (Değişmedi) ---
@st.cache_data(ttl=300)
def radar_analizi(ticker, strat_name):
    try:
        hisse = yf.Ticker(ticker)
        df = hisse.history(period="6mo", interval="1d")
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
        fk, pddd, temel_ok = 0, 0, False
        if not stop_oldu and teknik_ok:
            info = hisse.info
            fk = info.get('trailingPE', 0) or 0
            pddd = info.get('priceToBook', 0) or 0
            temel_ok = (0 < fk <= p['fk']) and (0 < pddd <= p['pddd'])
        if stop_oldu: durum = "🔴 SAT"
        elif teknik_ok and temel_ok: durum = "🚫 YASAK (Rejim)" if "DÜŞÜŞ" in rejim else "🟢 ONAY"
        elif teknik_ok and not temel_ok: durum = "⚠️ ŞİŞKİN"
        else: durum = "⏳ BEKLE"
        return {"Hisse": ticker, "Fiyat": round(fiyat,2), "F/K": round(fk,1), "Sinyal": durum}
    except: return None

# --- 6. ARAYÜZ (TABS) ---
st.title("🛡️ Master Quant Dashboard V5.1 (Enflasyon Kalkanı)")
tab_portfoy, tab_izleme, tab_tarama, tab_sorgu = st.tabs(["💼 Portföyüm", "👁️ İzleme Listem", "📡 BİST Tarayıcı", "🔍 Serbest Sorgu"])

with tab_portfoy:
    st.subheader("Aktif Yatırımlar (5 Yıllık Reel Getiri Analizi)")
    df_port = portfoy_goster(portfoy_girdisi)
    if df_port is not None: st.dataframe(df_port, use_container_width=True)

with tab_izleme:
    st.subheader("Pusudaki Hedefler (5 Yıllık Reel Getiri Analizi)")
    df_iz = portfoy_goster(izleme_girdisi)
    if df_iz is not None: st.dataframe(df_iz, use_container_width=True)

with tab_tarama:
    st.subheader(f"Tüm Borsayı Tara ({secilen_tarama_stratejisi})")
    ticker_dosyasi = st.file_uploader("tickers.csv dosyasını yükleyin", type=["csv"])
    if ticker_dosyasi is not None:
        tum_hisseler = pd.read_csv(ticker_dosyasi)['Tickers'].dropna().tolist()
        if st.button("🚀 Taramayı Başlat"):
            metin, cubuk = st.empty(), st.progress(0)
            firsatlar, toplam = [], len(tum_hisseler)
            for i, h in enumerate(tum_hisseler):
                metin.text(f"Taranıyor: {h} ({i+1}/{toplam})")
                sonuc = radar_analizi(h, secilen_tarama_stratejisi)
                if sonuc and ("ONAY" in sonuc['Sinyal'] or "YASAK" in sonuc['Sinyal']): firsatlar.append(sonuc)
                cubuk.progress((i + 1) / toplam)
            metin.text("Tarama Tamamlandı!")
            if firsatlar: st.dataframe(pd.DataFrame(firsatlar), use_container_width=True)
            else: st.warning("Bu profilin şartlarını sağlayan hisse bulunamadı.")

with tab_sorgu:
    st.subheader("Hızlı Hisse Röntgeni")
    aranan = st.text_input("Hisse Kodu (Örn: ARDYZ):").upper()
    if aranan:
        if not aranan.endswith(".IS"): aranan += ".IS"
        with st.spinner("Röntgen çekiliyor..."):
            sonuc = coklu_analiz_ve_backtest(aranan)
            if sonuc: st.dataframe(pd.DataFrame([sonuc]), use_container_width=True)
