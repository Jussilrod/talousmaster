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

# --- WOW-EFFEKTI CSS ---
st.markdown("""
<style>
    /* 1. TAUSTA JA YLEISILME */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* 2. OTSIKKO JA HERO-TEKSTI */
    .main-header {
        text-align: center;
        padding: 40px 0;
    }
    .main-header h1 {
        font-size: 3.5rem;
        font-weight: 800;
        color: #1e3a8a; /* Tummansininen */
        margin-bottom: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .main-header h2 {
        font-size: 1.5rem;
        font-weight: 400;
        color: #475569;
        margin-top: 10px;
    }
    
    /* 3. UPLOAD-LAATIKKO (OIKEA PUOLI) */
    .upload-card {
        background-color: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    
    /* 4. KPI KORTIT */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 6px solid #3b82f6;
    }
    
    /* 5. POISTA TURHIA ELEMENTTEJÄ */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    
    /* Painikkeet */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 50px;
        font-size: 18px;
        font-weight: bold;
        box-shadow: 0 4px 14px 0 rgba(0,118,255,0.39);
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

# --- FUNKTIOT (LOGIIKKA SAMA KUIN ENNEN) ---
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

# --- UI LOGIIKKA ---

# 1. HERO SECTION (KESKITETTY ISO OTSIKKO)
st.markdown("""
<div class="main-header">
    <h1>💎 TalousMaster AI</h1>
    <h2>Henkilökohtainen varainhoitajasi.<br>Lataa Excel, saat ammattilaisen analyysin sekunneissa.</h2>
</div>
""", unsafe_allow_html=True)

st.write("") 

# 2. SPLIT LAYOUT (VASEN: KUVA & FIILIS / OIKEA: TOIMINTA)
col_left, col_right = st.columns([1.2, 1])

with col_left:
    # Käytetään Unsplash-kuvaa tuomaan "Fintech"-fiilistä
    st.image("https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?q=80&w=2000&auto=format&fit=crop", 
             use_container_width=True, caption="Ota taloutesi hallintaan datalla.")
    st.markdown("### 📈 Miksi käyttää tekoälyä?")
    st.markdown("""
    * **Puolueeton:** AI ei tuomitse, se laskee.
    * **Nopea:** Unohda tuntien Excel-pyörittely.
    * **Turvallinen:** Emme tallenna pankkitietojasi.
    """)

with col_right:
    # "Upload Card" - Rakennetaan visuaalinen laatikko
    st.markdown('<div class="upload-card"><h3>🚀 Aloita tästä</h3>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("1. Pudota Excel-tiedostosi", type=['xlsx'], label_visibility="collapsed")
    
    st.markdown("---")
    st.write("Tai lataa pohja:")
    try:
        with open(EXCEL_TEMPLATE_NAME, "rb") as file:
            st.download_button(
                label="📥 Lataa tyhjä Excel-pohja",
                data=file,
                file_name="talous_tyokalu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    except:
        st.warning("Pohjaa ei löytynyt.")
        
    st.markdown('</div>', unsafe_allow_html=True)

st.write("---")

# 3. ANALYYSI-OSIO (Näkyy vain jos tiedosto on)
if uploaded_file:
    df_laskettu = lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot
        
        st.header("📊 Analyysin asetukset & Tulokset")
        
        # PROFIILI
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            with c1: ika = st.number_input("Ikä", 15, 100, 30)
            with c2: suhde = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perheellinen", "YH"])
            with c3: lapset = st.number_input("Lapset", 0, 10, 0)
            with c4: data_tyyppi = st.radio("Tyyppi", ["Suunnitelma", "Toteuma"])

        st.write("")
        
        # KPI KORTIT
        m1, m2, m3 = st.columns(3)
        m1.metric("Tulot", f"{tulot:,.0f} €")
        m2.metric("Menot", f"{menot:,.0f} €")
        m3.metric("Jäämä", f"{jaama_preview:,.0f} €", delta_color="normal", delta=f"{jaama_preview:,.0f} €")

        # ANALYYSI BUTTON
        st.write("")
        analyze_btn = st.button("✨ LUO TEKOÄLY-ANALYYSI", type="primary")

        if analyze_btn:
            with st.spinner('Varainhoitaja miettii...'):
                profiili = {"ika": ika, "suhde": suhde, "lapset": lapset, "sukupuoli": "Muu"}
                vastaus, lopullinen_jaama = analysoi_talous(df_laskettu, profiili, data_tyyppi)
                tallenna_lokiiin(profiili, lopullinen_jaama, data_tyyppi)
                
                st.markdown("### 📝 Sinulle luotu suunnitelma")
                # Laitetaan vastaus valkoiseen laatikkoon
                st.markdown(f"""
                <div style="background-color: white; padding: 30px; border-radius: 15px; border-left: 5px solid #3b82f6; box-shadow: 0 5px 15px rgba(0,0,0,0.05);">
                    {vastaus}
                </div>
                """, unsafe_allow_html=True)

    else:
        st.error("Excelin luku epäonnistui.")
