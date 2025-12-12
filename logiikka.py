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

    # 1. Python-laskenta (Force Calculation)
    tulot_yht = df[df['Kategoria']=='Tulo']['Euroa_KK'].sum()
    menot_yht = df[df['Kategoria']=='Meno']['Euroa_KK'].sum()
    jaama = tulot_yht - menot_yht
    saastoprosentti = (jaama / tulot_yht * 100) if tulot_yht > 0 else 0
    
    # Lasketaan "Runway" (Kuinka monta kk pärjää ilman tuloja, jos säästöt 0€ oletuksena kassassa)
    # Tämä on vain kassavirtapohjainen arvio
    runway_text = "Kriittinen (kulut ylittävät tulot)" if jaama < 0 else "Vakaa"

    # Muotoillaan data promptia varten tiiviiksi
    kpi_stats = f"""
    - TULOT: {tulot_yht} €
    - MENOT: {menot_yht} €
    - JÄÄMÄ: {jaama} € ({saastoprosentti:.1f}%)
    """
    
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

   prompt = f"""
    ### ROLE
    Toimit empaattisena mutta tiukkana Senior Financial Plannerina. Tavoitteesi on auttaa asiakasta ymmärtämään rahavirtansa ja rakentamaan varallisuutta. Et vain listaa lukuja, vaan etsit niiden takaa käyttäytymismalleja.

    ### CONTEXT & DATA
    - Asiakasprofiili: Ikä {profiili['ika']}, Status: {profiili['suhde']}, Lapset: {profiili['lapset']}
    - Kassavirtatilanne: {tilanne_ohje}
    - Datan tyyppi: {tyyppi_ohje}
    
    Talousdata (Kuukausitaso):
    {data_txt}

    Viitekehys (Benchmark):
    {financial_framework}

    ### INSTRUCTIONS (Step-by-Step)
    1. **Categorize & Calculate:** Käy läpi annettu data. Summaa yhteen kategoriat (Välttämättömät, Elämäntyyli, Säästöt) viitekehyksen mukaisesti.
    2. **Analyze Deviation:** Vertaa asiakkaan toteumaa viitekehyksen tavoiteprosentteihin. Missä on suurin poikkeama?
    3. **Identify Leakage:** Etsi yksittäisiä rivejä, jotka ovat epätavallisen suuria suhteessa profiiliin (esim. suuret ruokakulut yhdelle hengelle tai kalliit vakuutukset).
    4. **Formulate Action Plan:** Luo 3 konkreettista toimenpidettä.
       - Jos alijäämäinen: Etsi välittömiä säästöjä.
       - Jos ylijäämäinen: Optimoi sijoitus/puskuri-suhde.

    ### OUTPUT FORMAT (Markdown)
    
    ## 📊 Talouden "Health Check"
    [Tiivis yhteenveto: Miten hyvin asiakas noudattaa 70/20/10 -sääntöä? Käytä prosentteja.]
    * **Välttämättömät:** X% (Tavoite 70%)
    * **Elämäntyyli:** X% (Tavoite 20%)
    * **Säästöt:** X% (Tavoite 10%)

    ## 🔍 Syväanalyysi & Vuodot
    * **Positiivista:** [Yksi selkeä onnistuminen]
    * **Huomio:** [Suurin yksittäinen kuluerä tai huolestuttava trendi]
    * **Profilointi:** [Miten ikä/perhesuhde vaikuttaa tähän? Esim. "Lapsiperheellisenä ruokakulusi ovat..."]

    ## 📉 Kulupaljastus (Top 2)
        * **[Kategoria/Rivi]: [Summa]€** - [Lyhyt, terävä kommentti, esim. "Vastaa 15% tuloistasi!"]
        * **[Kategoria/Rivi]: [Summa]€** - [Kommentti]

    ## 🚀 3 Askeleen Toimintasuunnitelma
    1. **[Quick Win - Säästä heti]:** [Konkreettinen toimi, arvioitu säästö €/kk]
    2. **[Rakenteellinen muutos]:** [Sopimukset, kilpailutus tai budjettikatto]
    3. **[Varallisuuden kasvu]:** [Mihin ylijäämä tulisi ohjata juuri nyt?]


    **Arvosana taloudelle (4-10):** [X]/10

        ## 🔮 Tulevaisuus-simulaatio (10v)
        [Motivoiva tai varoittava laskelma]
        👉 **Lopputulos:** [Esim: "Nykyisellä ylijäämällä salkkusi arvo olisi 10v päästä n. **XX XXX €**."]

        ## ✅ Tärkein toimenpide (Tee tämä heti)
        [Yksi konkreettinen käsky/neuvo imperatiivissa. Esim. "Avaa automaattinen tilisiirto..."]
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


