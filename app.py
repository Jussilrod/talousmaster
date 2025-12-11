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

# --- MODERN UI CSS ---
# Tämä osio muuttaa vain ulkoasua, ei logiikkaa.
st.markdown("""
<style>
    /* Päätausta ja fontit */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Otsikon tyyli */
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        text-align: center;
        padding-bottom: 20px;
    }
    
    /* Metriikka-kortit (KPI) */
    div[data-testid="metric-container"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #3b82f6;
        text-align: center;
    }
    
    /* Latauslaatikon tyyli */
    .upload-box {
        border: 2px dashed #cbd5e1;
        border-radius: 10px;
        padding: 20px;
        background-color: white;
    }
    
    /* Painikkeet */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
    }
    
    /* Piilota turha yläpalkki */
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# Turvallinen API-avaimen haku
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("⚠️ API-avain puuttuu secrets.toml -tiedostosta.")
except Exception as e:
    st.error(f"Järjestelmävirhe: {e}")

LOG_FILE = "talousdata_logi.csv"
EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx" 

# --- TEKNISET FUNKTIOT (LOGIIKKA KOSKEMATON) ---

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
        
        # --- 1. TULOT ---
        tulot_df = df.iloc[tulot_rivi + 2 : menot_rivi].copy()
        for _, row in tulot_df.iterrows():
            nimi = str(row[1])
            kk_summa = pd.to_numeric(row[2], errors='coerce') 
            
            if pd.isna(kk_summa): continue
            if "Yhteensä" in nimi or nimi == "nan": continue

            if kk_summa > 0.5: 
                data_rows.append({"Kategoria": "Tulo", "Selite": nimi, "Euroa_KK": round(kk_summa, 2)})

        # --- 2. MENOT ---
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
    # ALKUPERÄINEN MALLI JA PROMPT - EI MUUTOKSIA
    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    data_txt = df.to_string(index=False)
    tulot = df[df['Kategoria']=='Tulo']['Euroa_KK'].sum()
    menot = df[df['Kategoria']=='Meno']['Euroa_KK'].sum()
    jaama = tulot - menot
    
    tilanne_ohje = ""
    if jaama > 500:
        tilanne_ohje = "Talous on vahva. Keskity varallisuuden kasvattamiseen."
    elif jaama >= 0:
        tilanne_ohje = "Talous on tasapainossa, mutta herkkä."
    else:
        tilanne_ohje = "Talous on alijäämäinen. Etsi säästökohteita."

    tyyppi_ohje = ""
    if "Toteuma" in data_tyyppi:
        tyyppi_ohje = "HUOM: Data on TOTEUMA (oikeasti tapahtuneet kulut). Etsi menneisyyden virheet, ylitykset ja vuodot."
    else:
        tyyppi_ohje = "HUOM: Data on BUDJETTI (suunnitelma). Arvioi onko suunnitelma realistinen ja onko jotain unohtunut."    

    financial_framework = """
    VIITEKEHYS ANALYYSIIN (70/20/10 -sääntö):
    - Välttämättömät (70%): Asuminen, ruoka, sähkö, vakuutukset, lainat.
    - Elämäntyyli (20%): Harrastukset, ulkona syöminen, viihde.
    - Säästöt (10%): Sijoitukset, puskuri.
    """

    prompt = f"""
    Toimit kokeneena varainhoitajana (Certified Financial Planner). Tehtäväsi on analysoida asiakkaan talousdata ja antaa konkreettisia, matemaattisesti perusteltuja suosituksia.

    ASIAKASPROFIILI:
    - Ikä: {profiili['ika']} | Status: {profiili['suhde']} | Lapset: {profiili['lapset']}
    - Nykyinen kassavirtatilanne: {tilanne_ohje}

    DATA (Kuukausitaso):
    {data_txt}

    {financial_framework}

    ANALYYSIOHJEET:
    1. Laske ja kategorisoi: Jaa asiakkaan kulut yllä mainittuihin 50/30/20 kategorioihin ja vertaa niitä ihannetasoon.
    2. Tunnista vuodot: Etsi kulueriä, jotka poikkeavat merkittävästi profiilin mukaisesta normaalitasosta.
    3. Priorisoi: Jos talous on alijäämäinen, etsi nopeimmat säästöt "Haluat"-kategoriasta. Jos ylijäämäinen, suosittele allokaatiota (puskuri vs. sijoittaminen).

    VASTAUKSEN RAKENNE (Käytä Markdownia):

    ## 📊 Talouden tilannekuva
    [Lyhyt, ammattimainen yhteenveto siitä, miltä tilanne näyttää suhteessa 50/30/20-sääntöön. Esim: "Välttämättömät menot vievät 70% tuloista, mikä luo riskiä..."]

    ## 💡 Huomiot kulurakenteesta
    * **Positiivista:** [Mikä on hyvin?]
    * **Kehitettävää:** [Missä on suurin vuoto?]

    ## 🚀 3 Toimenpidettä (Action Points)
    1.  **[Toimenpide 1 - Nopea vaikutus]:** [Mitä tehdään, paljonko säästetään/tuotetaan euroissa?]
    2.  **[Toimenpide 2 - Rakenteellinen muutos]:** [Esim. kilpailutus tai budjettikatto]
    3.  **[Toimenpide 3 - Tulevaisuus/Turva]:** [Puskurin kerrytys tai sijoittaminen]

    HUOM: Ole suora, kannustava ja ratkaisukeskeinen. Älä käytä jargonia ilman selitystä.
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
    if not os.path.exists(LOG_FILE):
        uusi_tieto.to_csv(LOG_FILE, index=False)
    else:
        uusi_tieto.to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- KÄYTTÖLIITTYMÄ (UI) ---

# Header Section
st.markdown("<h1>💎 TalousMaster <span style='color:#3b82f6'>AI</span></h1>", unsafe_allow_html=True)
st.caption("Henkilökohtainen varainhoitajasi. Lataa Excel, saat ammattilaisen analyysin sekunneissa.")

st.write("") # Spacer

# VAIHE 1: LAYOUT & LATAUS
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📂 1. Lataa aineisto")
        st.info("💡 **Vinkki:** Voit lisätä Exceliin rivejä vapaasti. AI ymmärtää kategorioiden nimet automaattisesti.")
        uploaded_file = st.file_uploader("Pudota Excel-tiedosto tähän", type=['xlsx'], label_visibility="collapsed")
    
    with col2:
        st.subheader("📥 Pohjatiedosto")
        st.write("Ei vielä tiedostoa?")
        try:
            with open(EXCEL_TEMPLATE_NAME, "rb") as file:
                st.download_button(
                    label="Lataa Excel-työkalu",
                    data=file,
                    file_name="talous_tyokalu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="secondary"
                )
        except:
            st.warning("Pohjatiedostoa ei löytynyt.")

st.write("---")

# VAIHE 2: ANALYYSI (Näkyy vain jos tiedosto ladattu)
if uploaded_file:
    df_laskettu = lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot
        
        # --- DASHBOARD SECTION ---
        st.subheader("👤 2. Taustatiedot & Nykytila")
        
        # Profiili-asetukset tyylikkäässä rivissä
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            with c1: ika = st.number_input("Ikä", 15, 100, 30)
            with c2: suhde = st.selectbox("Elämäntilanne", ["Yksin", "Parisuhteessa", "Perheellinen", "YH"])
            with c3: lapset = st.number_input("Lapset", 0, 10, 0)
            with c4: data_tyyppi = st.radio("Analyysin tyyppi", ["Suunnitelma", "Toteuma"])

        st.write("") # Spacer

        # KPI KORTIT
        m1, m2, m3 = st.columns(3)
        m1.metric("Tulot / kk", f"{tulot:,.0f} €")
        m2.metric("Menot / kk", f"{menot:,.0f} €")
        m3.metric("Jäämä / kk", f"{jaama_preview:,.0f} €", 
                 delta=f"{jaama_preview:,.0f} €", delta_color="normal")

        # DATA EXPANDER
        with st.expander("🔍 Tarkastele luettuja lukuja (Data)"):
            st.dataframe(df_laskettu, use_container_width=True)

        st.write("")
        st.write("")

        # ANALYSOI -PAINIKE
        col_btn_l, col_btn_c, col_btn_r = st.columns([1, 2, 1])
        with col_btn_c:
            analyze_btn = st.button("🚀 KÄYNNISTÄ TEKOÄLY-ANALYYSI", type="primary", use_container_width=True)

        if analyze_btn:
            # Placeholder analyysin ajaksi
            progress_text = "Analysoidaan kulurakennetta... Etsitään säästökohteita... Lasketaan suosituksia..."
            with st.status(progress_text, expanded=True) as status:
                st.write("Yhdistetään AI-varainhoitajaan...")
                profiili = {"ika": ika, "sukupuoli": "Muu", "suhde": suhde, "lapset": lapset} # Sukupuoli oletuksena
                
                vastaus, lopullinen_jaama = analysoi_talous(df_laskettu, profiili, data_tyyppi)
                
                tallenna_lokiiin(profiili, lopullinen_jaama, data_tyyppi)
                status.update(label="Analyysi valmis!", state="complete", expanded=False)
            
            # TULOS
            st.markdown("---")
            st.markdown("### 📝 Varainhoitajan Raportti")
            
            # Tulostetaan vastaus containeriin, jossa on vaalea tausta
            with st.container():
                st.markdown(vastaus)
                
    else:
        st.error("⚠️ Tiedoston luku epäonnistui. Tarkista, että Excelissä on sarakkeet 'Tulot' ja 'Menot'.")

else:
    # Tyhjä tila alhaalla, jos tiedostoa ei ole
    st.markdown("<div style='text-align: center; color: #aaa; margin-top: 50px;'><i>Odottamassa aineistoa...</i></div>", unsafe_allow_html=True)