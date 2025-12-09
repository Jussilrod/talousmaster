import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
from datetime import datetime

# --- ASETUKSET ---
# ❗ Laita API-avain tähän
GOOGLE_API_KEY = "AIzaSyAntKErnXvsS8WMvqFHGkmn9RZTWPfrSgM"

# Sivun konfiguraatio
st.set_page_config(
    page_title="TalousMaster AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error("Järjestelmävirhe: API-avain puuttuu.")

LOG_FILE = "talousdata_logi.csv"
EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx" 

# --- TEKNISET FUNKTIOT ---

def lue_kaksiosainen_excel(file):
    """
    Lukee Excelin YKSINKERTAISTETULLA logiikalla.
    Lukee vain sarakkeen C (Kuukausisumma). Ei enää vuosijakoja.
    """
    try:
        df = pd.read_excel(file, header=None)
        data_rows = []
        
        # Etsitään "Tulot" ja "Menot" otsikot
        try:
            tulot_rivi = df[df.iloc[:, 1].astype(str).str.contains("Tulot", na=False)].index[0]
            menot_rivi = df[df.iloc[:, 1].astype(str).str.contains("Menot", na=False)].index[0]
        except IndexError:
            return pd.DataFrame() 
        
        # --- 1. TULOT ---
        tulot_df = df.iloc[tulot_rivi + 2 : menot_rivi].copy()
        for _, row in tulot_df.iterrows():
            nimi = str(row[1])
            # Luetaan vain sarake 2 (C-sarake, eli Kuukausi)
            kk_summa = pd.to_numeric(row[2], errors='coerce') 
            
            if pd.isna(kk_summa): continue
            if "Yhteensä" in nimi or nimi == "nan": continue

            # Nyt ei jaeta mitään, vaan otetaan luku sellaisenaan
            if kk_summa > 0.5: 
                data_rows.append({"Kategoria": "Tulo", "Selite": nimi, "Euroa_KK": round(kk_summa, 2)})

        # --- 2. MENOT ---
        menot_df = df.iloc[menot_rivi + 2 : ].copy()
        for _, row in menot_df.iterrows():
            nimi = str(row[1])
            # Luetaan vain sarake 2 (C-sarake, eli Kuukausi)
            kk_summa = pd.to_numeric(row[2], errors='coerce')
            
            if pd.isna(kk_summa): continue
            if "Yhteensä" in nimi or nimi == "nan": continue

            if kk_summa > 0.5:
                data_rows.append({"Kategoria": "Meno", "Selite": nimi, "Euroa_KK": round(kk_summa, 2)})
                
        return pd.DataFrame(data_rows)
        
    except Exception as e:
        return pd.DataFrame()

def analysoi_talous(df, profiili):
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

    # 2. Datan tyyppi -ohje (UUSI)
    tyyppi_ohje = ""
    if "Toteuma" in data_tyyppi:
        tyyppi_ohje = "HUOM: Data on TOTEUMA (oikeasti tapahtuneet kulut). Etsi menneisyyden virheet, ylitykset ja vuodot."
    else:
        tyyppi_ohje = "HUOM: Data on BUDJETTI (suunnitelma). Arvioi onko suunnitelma realistinen ja onko jotain unohtunut."    

    financial_framework = """
    VIITEKEHYS ANALYYSIIN (70/20/10 -sääntö):
    - Välttämättömät (70%): Asuminen, ruoka, sähkö, vakuutukset, lainat.
    - Haluat/Elämäntyyli (20%): Harrastukset, ulkona syöminen, viihde.
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
        "Sukupuoli": profiili['sukupuoli'],
        "Status": profiili['suhde'],
        "Lapset": profiili['lapset'],
        "Jäämä": round(jaama, 2)
    }])
    if not os.path.exists(LOG_FILE):
        uusi_tieto.to_csv(LOG_FILE, index=False)
    else:
        uusi_tieto.to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- KÄYTTÖLIITTYMÄ (UI) ---

st.title("💎 TalousMaster AI")
st.markdown("""
<style>
    .big-font { font-size:18px !important; color: #555; }
</style>
<p class="big-font">Henkilökohtainen varainhoitajasi. Lataa luvut, tekoäly hoitaa loput.</p>
""", unsafe_allow_html=True)

st.divider()

# VAIHE 1: OHJEET JA LATAUS
col_info, col_download = st.columns([1.5, 1])

with col_info:
    st.subheader("1. Aloita tästä")
    st.info("""
    **🛡️ Tietoturvaohje:** Älä koskaan kirjoita Exceliin nimeäsi, henkilötunnustasi tai pankkitilinumeroitasi. 
    Tekoäly tarvitsee vain luvut ja kategorioiden nimet.
    """)
    # KORJATTU KOHTA: Nuoli on nyt tavallinen '->'
    st.markdown("""
    * **Lisää rivejä vapaasti:** Voit lisätä uusia rivejä Exceliin.
    * **Nimeä kulut:** Muuta "Laina 1" -> "Opintolaina".
    """)

with col_download:
    st.subheader("Pohja")
    try:
        with open(EXCEL_TEMPLATE_NAME, "rb") as file:
            st.download_button(
                label="📥 Lataa Excel-työkalu",
                data=file,
                file_name="talous_tyokalu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
    except:
        st.error("Pohjatiedosto puuttuu palvelimelta.")

st.divider()

# VAIHE 2: UPLOAD
st.subheader("2. Analyysi")
uploaded_file = st.file_uploader("Palauta täytetty Excel tähän", type=['xlsx'], label_visibility="collapsed")

if uploaded_file:
    df_laskettu = lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        # Lasketaan avainluvut
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot
        
        st.write("### 👤 Taustatiedot & Nykytila")
        
        with st.container():
            col_prof1, col_prof2, col_prof3, col_prof4,col_prof5  = st.columns(5)
            with col_prof1: ika = st.number_input("Ikä", 15, 100, 30)
            with col_prof2: sukupuoli = st.selectbox("Sukupuoli", ["Mies", "Nainen", "Muu"])
            with col_prof3: suhde = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perheellinen", "Yksinhuoltaja"])
            with col_prof4: lapset = st.number_input("Lapset", 0, 10, 0)
            with col_prof5: data_tyyppi = st.radio("Tiedot ovat:", ["Suunnitelma (Budjetti)", "Toteuma (Oikeat kulut)"])
        
        st.markdown("---")
        
        # DASHBOARD-TYYLISET LUVUT
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Tulot (kk)", f"{tulot:,.0f} €")
        col_m2.metric("Menot (kk)", f"{menot:,.0f} €") # Ei deltaa menoissa, pelkkä luku
        
        # KORJATTU KOHTA: Jäämä ja sen väri
        # 'normal' tarkoittaa: Positiivinen = Vihreä, Negatiivinen = Punainen.
        # Näytetään delta-arvona itse summa, jolloin väri aktivoituu.
        col_m3.metric(
            "Jäämä (kk)", 
            f"{jaama_preview:,.0f} €", 
            delta=f"{jaama_preview:,.0f} €", 
            delta_color="normal"
        )

        with st.expander("🔍 Katso tarkka erittely (Data)"):
            st.dataframe(df_laskettu, use_container_width=True)

        st.write(" ")
        analyze_btn = st.button("🚀 Analysoi", type="primary", use_container_width=True)

        if analyze_btn:
            with st.spinner('Varainhoitaja analysoi kulurakennetta...'):
                profiili = {"ika": ika, "sukupuoli": sukupuoli, "suhde": suhde, "lapset": lapset}
                
                vastaus, lopullinen_jaama = analysoi_talous(df_laskettu, profiili)
                
                st.success("Analyysi valmistunut.")
                st.markdown("### 📝 Toimenpidesuositus")
                st.markdown(vastaus)
                
                tallenna_lokiiin(profiili, lopullinen_jaama, data_tyyppi)
    else:
        st.warning("⚠️ Excel näyttää tyhjältä.")

else:
    st.info("👆 Lataa Excel yläpuolelta nähdäksesi analyysin.")