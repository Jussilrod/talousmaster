import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime

# --- KONFIGURAATIO ---
LOG_FILE = "talousdata_logi.csv"

def konfiguroi_ai():
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            return True
        else:
            st.error("⚠️ API-avain puuttuu secrets.toml -tiedostosta.")
            return False
    except Exception as e:
        st.error(f"Järjestelmävirhe API-yhteydessä: {e}")
        return False

# --- EXCELIN LUKU ---
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
        
        # Tulot
        tulot_df = df.iloc[tulot_rivi + 2 : menot_rivi].copy()
        for _, row in tulot_df.iterrows():
            nimi = str(row[1])
            kk_summa = pd.to_numeric(row[2], errors='coerce') 
            if pd.isna(kk_summa): continue
            if "Yhteensä" in nimi or nimi == "nan": continue
            if kk_summa > 0.5: 
                data_rows.append({"Kategoria": "Tulo", "Selite": nimi, "Euroa_KK": round(kk_summa, 2)})

        # Menot
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

# --- TEKOÄLY ANALYYSI ---
def analysoi_talous(df, profiili, data_tyyppi):
    # Pidetty alkuperäinen malli
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

    # Data tyyppi -ohje
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

    # ALKUPERÄINEN PROMPT PIDETTY KOSKEMATTOMANA
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
    [Lyhyt, ammattimainen yhteenveto siitä, miltä tilanne näyttää suhteessa 70/20/10-sääntöön. Esim: "Välttämättömät menot vievät 80% tuloista, mikä luo riskiä..."]

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

# --- LOKITUS ---
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
