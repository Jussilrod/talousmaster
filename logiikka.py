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