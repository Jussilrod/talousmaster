import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime

# --- ASETUKSET ---
st.set_page_config(
    page_title="TalousMaster AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- TYYLIT (CSS) ---
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    
    /* OTSIKOT */
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        color: #000000;
        margin-bottom: 0px;
        line-height: 1.1;
    }
    .highlight-blue {
        color: #2563eb;
    }
    .slogan {
        font-size: 1.8rem;
        font-weight: 500;
        color: #4b5563;
        margin-top: 10px;
        margin-bottom: 40px;
    }
    
    /* Videon otsikko */
    .video-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 15px;
    }

    /* Piilota header */
    header {visibility: hidden;}
    
    /* Painikkeet */
    .stButton>button {
        border-radius: 8px;
        height: 45px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API-KEY SETUP
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ API-avain puuttuu.")
except Exception as e:
    st.error(f"Järjestelmävirhe: {e}")

LOG_FILE = "talousdata_logi.csv"
EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx" 

# --- FUNKTIOT ---
@st.cache_data
def lue_kaksiosainen_excel(file):
    try:
        df = pd.read_excel(file, header=None)
        data_rows = []
        try:
            tulot_rivi = df[df.iloc[:, 1].astype(str).str.contains("Tulot", na=False)].index[0]
            menot_rivi = df[df.iloc[:, 1].astype(str).str.contains("Menot", na=False)].index[0]
        except IndexError:
            return pd.DataFrame() 
        
        tulot_df = df.iloc[tulot_rivi + 2 : menot_rivi].copy()
        for _, row in tulot_df.iterrows():
            nimi = str(row[1])
            kk_summa = pd.to_numeric(row[2], errors='coerce') 
            if pd.isna(kk_summa): continue
            if "Yhteensä" in nimi or nimi == "nan": continue
            if kk_summa > 0.5: 
                data_rows.append({"Kategoria": "Tulo", "Selite": nimi, "Euroa_KK": round(kk_summa, 2)})

        menot_df = df.iloc[menot_rivi + 2 : ].copy()
        for _, row in menot_df.iterrows():
            nimi = str(row[1])
            kk_summa = pd.to_numeric(row[2], errors='coerce')
            if pd.isna(kk_summa): continue
            if "Yhteensä" in nimi or nimi == "nan": continue
            if kk_summa > 0.5:
                data_rows.append({"Kategoria": "Meno", "Selite": nimi, "Euroa_KK": round(kk_summa, 2)})
        return pd.DataFrame(data_rows)
    except Exception as e:
        return pd.DataFrame()

def analysoi_talous(df, profiili, data_tyyppi):
    model = genai.GenerativeModel('gemini-2.5-flash') 
    data_txt = df.to_string(index=False)
    tulot = df[df['Kategoria']=='Tulo']['Euroa_KK'].sum()
    menot = df[df['Kategoria']=='Meno']['Euroa_KK'].sum()
    jaama = tulot - menot
    
    tilanne_ohje = ""
    if jaama > 500: tilanne_ohje = "Talous on vahva."
    elif jaama >= 0: tilanne_ohje = "Talous on tasapainossa."
    else: tilanne_ohje = "Talous on alijäämäinen."

    financial_framework = """
    VIITEKEHYS (50/30/20):
    - 50% Välttämättömät
    - 30% Haluat
    - 20% Säästöt
    """
    prompt = f"""
    Toimit kokeneena varainhoitajana. Analysoi data.
    ASIAKAS: Ikä: {profiili['ika']} | Status: {profiili['suhde']} | Lapset: {profiili['lapset']}
    Tilanne: {tilanne_ohje} ({data_tyyppi})
    DATA: {data_txt}
    {financial_framework}
    TEHTÄVÄ: Markdown raportti. 1. Tilannekuva. 2. Huomiot. 3. Action Points.
    """
    response = model.generate_content(prompt)
    return response.text, jaama

def tallenna_lokiiin(profiili, jaama, tyyppi):
    uusi_tieto = pd.DataFrame([{
        "Pvm": datetime.now().strftime("%Y-%m-%d"),
        "Tyyppi": tyyppi,
        "Ikä": profiili['ika'],
        "Status": profiili['suhde'],
        "Lapset": profiili['lapset'],
        "Jäämä": round(jaama, 2)
    }])
    header = not os.path.exists(LOG_FILE)
    uusi_tieto.to_csv(LOG_FILE, mode='a', header=header, index=False)

# --- KÄYTTÖLIITTYMÄ ---

# 1. OTSIKKO
st.markdown("""
<div>
    <h1 class="main-title">TalousMaster <span class="highlight-blue">AI</span></h1>
    <p class="slogan">Ota taloutesi hallintaan datalla.</p>
</div>
""", unsafe_allow_html=True)

# 2. PÄÄOSIO (SPLIT)
# Tässä määritellään sarakkeiden suhde. [1, 1] tarkoittaa yhtä suuria.
col_left, col_right = st.columns([1, 1], gap="large")

# --- VASEN PUOLI (TOIMINNOT) ---
with col_left:
    # Toissijainen toiminto: Pohjan lataus (Suoraan näkyvillä)
        st.subheader("1. Puuttuuko pohja?")
        st.write("Lataa valmis pohja, täytä se ja palauta alla olevaan laatikkoon.")
    
    # Käytetään Streamlitin aitoa reunusta -> Ei haamu-ongelmia
    with st.container(border=True):
        st.subheader("2. Lataa tiedosto")
        
        # Päätoiminto: Lataus
        uploaded_file = st.file_uploader("Pudota täytetty Excel tähän", type=['xlsx'])
        
        st.write("") 
        st.markdown("---") # Erotinviiva
        st.write("") 
        
        try:
            with open(EXCEL_TEMPLATE_NAME, "rb") as file:
                st.download_button(
                    label="📥 Lataa Excel-työkalu",
                    data=file,
                    file_name="talous_tyokalu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except:
            st.warning("Pohjatiedostoa ei löytynyt.")

        st.write("")
        st.write("")
        
        # Tietoturva
        st.info("🔒 **Tietoturva:** Älä syötä Exceliin nimeäsi tai tilinumeroita. Data käsitellään anonyymisti.")

# --- OIKEA PUOLI (VIDEO) ---
with col_right:
    # Otsikko videon päällä
    st.markdown('<p class="video-title">📽️ Näin TalousMaster toimii</p>', unsafe_allow_html=True)
    
    # Video
    st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4")
    
    st.caption("Lataa Excel, määritä profiili ja anna tekoälyn etsiä säästökohteet.")

st.write("---")

# 3. TULOS-OSIO
if uploaded_file:
    df_laskettu = lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot
        
        st.header("📊 Analyysin tulokset")
        
        # PROFIILI
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            with c1: ika = st.number_input("Ikä", 15, 100, 30)
            with c2: suhde = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perheellinen", "YH"])
            with c3: lapset = st.number_input("Lapset", 0, 10, 0)
            with c4: data_tyyppi = st.radio("Datan tyyppi", ["Suunnitelma", "Toteuma"])

        st.write("")
        
        # KPI KORTIT
        m1, m2, m3 = st.columns(3)
        m1.metric("Tulot", f"{tulot:,.0f} €")
        m2.metric("Menot", f"{menot:,.0f} €")
        m3.metric("Jäämä", f"{jaama_preview:,.0f} €", delta_color="normal", delta=f"{jaama_preview:,.0f} €")

        st.write("")
        analyze_btn = st.button("✨ LUO ANALYYSI", type="primary", use_container_width=True)

        if analyze_btn:
            with st.spinner('Tekoäly varainhoitaja työskentelee...'):
                profiili = {"ika": ika, "suhde": suhde, "lapset": lapset, "sukupuoli": "Muu"}
                vastaus, lopullinen_jaama = analysoi_talous(df_laskettu, profiili, data_tyyppi)
                tallenna_lokiiin(profiili, lopullinen_jaama, data_tyyppi)
                
                st.markdown("### 📝 Toimenpidesuositukset")
                st.markdown(f"""
                <div style="background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    {vastaus}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("Virhe: Excelistä ei löytynyt dataa.")
