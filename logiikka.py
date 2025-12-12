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
    try:
        # --- 1. PYTHON-LASKENTA (Faktat) ---
        tulot_yht = df[df['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot_yht = df[df['Kategoria']=='Meno']['Euroa_KK'].sum()
        
        # Lasketaan sijoitukset erikseen, jotta ymmärretään "oikea" tilanne
        # Oletetaan, että sijoitukset löytyvät menosta hakusanalla "sijoitus", "rahasto", "osake", "nordnet" tms.
        # Tässä yksinkertaistus: Etsitään rivejä, joissa 'Selite' viittaa sijoituksiin (voit tarkentaa logiikkaa)
        sijoitukset_summa = 0
        sijoitus_keywords = ['sijoitus', 'rahasto', 'osake', 'säästö', 'nordnet', 'op-tuotto', 'ostot']
        for _, row in df[df['Kategoria']=='Meno'].iterrows():
             if any(x in str(row['Selite']).lower() for x in sijoitus_keywords):
                 sijoitukset_summa += row['Euroa_KK']

        jaama = tulot_yht - menot_yht
        
        # TODELLINEN SÄÄSTÖKYKY = Jäämä + Sijoitukset
        # Jos tämä on plussalla, talous on oikeasti ylijäämäinen, mutta kassavirta on tiukka.
        todellinen_saasto = jaama + sijoitukset_summa
        
        # KPI-laskenta
        saastoprosentti = (todellinen_saasto / tulot_yht * 100) if tulot_yht > 0 else 0

        # Etsitään Top 3 kulut
        top_menot = df[df['Kategoria']=='Meno'].nlargest(3, 'Euroa_KK')
        top_menot_txt = ""
        for _, row in top_menot.iterrows():
            osuus = (row['Euroa_KK'] / tulot_yht * 100) if tulot_yht > 0 else 0
            top_menot_txt += f"* **{row['Selite']}**: {row['Euroa_KK']:.2f}€ ({osuus:.1f}%)\n"

        # --- 2. ÄLYKÄS TILANNEOHJEISTUS ---
        # Tämä estää AI:ta ylireagoimasta
        if jaama < 0 and todellinen_saasto > 0:
            strategia = "KASSAVIRTA-OPTIMOINTI. Asiakas sijoittaa enemmän kuin hänellä on varaa käteistä. ÄLÄ KÄSE LOPETTAMAAN SIJOITUKSIA KOKONAAN. Neuvo pienentämään sijoituksia tai kuluja vain sen verran (n. 20-50€), että tili ei mene miinukselle."
            tilanne_teksti = "Investointivetoinen alijäämä (Sijoittaa aggressiivisesti)"
        elif jaama < 0:
            strategia = "HÄTÄJARRUTUS. Talous vuotaa oikeasti. Etsi säästökohteita."
            tilanne_teksti = "Aito alijäämä"
        else:
            strategia = "VARALLISUUDEN KASVATUS. Ylijäämä on vahva."
            tilanne_teksti = "Ylijäämäinen"

        kpi_stats = f"""
        - TULOT: {tulot_yht:.2f} €
        - MENOT (sis. sijoitukset): {menot_yht:.2f} €
        - KASSAVIRTA (Tilin saldo kk lopussa): {jaama:.2f} €
        - NYKYISET SIJOITUKSET: {sijoitukset_summa:.2f} €
        - TODELLINEN SÄÄSTÖKYKY: {todellinen_saasto:.2f} €
        """
        financial_framework = """
        VIITEKEHYS ANALYYSIIN (70/20/10 -sääntö):
        - Välttämättömät (70%): Asuminen, ruoka, sähkö, vakuutukset, lainat.
        - Elämäntyyli (20%): Harrastukset, ulkona syöminen, viihde.
        - Säästöt (10%): Sijoitukset, puskuri.
        """
        # Data tyyppi -ohje
        tyyppi_ohje = ""
        if "Toteuma" in data_tyyppi:
        tyyppi_ohje = "HUOM: Data on TOTEUMA (oikeasti tapahtuneet kulut). Etsi menneisyyden virheet, ylitykset ja vuodot."
        else:
        tyyppi_ohje = "HUOM: Data on BUDJETTI (suunnitelma). Arvioi onko suunnitelma realistinen ja onko jotain unohtunut."  

        # --- 3. PROMPT ENGINEERING ---
        model = genai.GenerativeModel('gemini-2.5-flash')
        data_txt = df.to_string(index=False)

        prompt = f"""
        ### ROLE
        Toimit kokeneena varainhoitajana (Certified Financial Planner). Tehtäväsi on analysoida asiakkaan talousdata ja antaa konkreettisia, matemaattisesti perusteltuja suosituksia.
        Yksinkertainen hei. Mene suoraan asiaan, mutta voi olla ystävällinen.
        

        ### CONTEXT
        - Profiili: {profiili['ika']}v, {profiili['suhde']}, {profiili['lapset']} lasta.
        - Tilanne: {tilanne_teksti}
        
        ### STRATEGIA (Noudata tätä!)
        {strategia}

        ### FAKTAT (Käytä näitä lukuja):
        {kpi_stats}

        ### SUURIMMAT KULUT:
        {top_menot_txt}

        ### DATA:
        {data_txt}

        ### INSTRUCTIONS
        1. **70/20/10 Analyysi:** Arvioi menot (Välttämätön / Hupi / Säästö). Huom: Laske nykyiset sijoitukset osaksi Säästö-kategoriaa, vaikka ne ovat teknisesti menoja Excelissä.
        2. Tunnista vuodot: Etsi kulueriä, jotka poikkeavat merkittävästi profiilin mukaisesta normaalitasosta.
        3. **Action Plan:** - Jos kyseessä on "Kassavirta-optimointi" (pieni miinus, mutta sijoittaa): Ehdota vain pientä viilausta. Älä ehdota satojen eurojen leikkauksia turhaan!
           - Tavoite on saada kassavirta ({jaama}€) juuri ja juuri plussalle ilman suuria uhrauksia.

        VASTAUKSEN RAKENNE (Käytä Markdownia):

        ## 📊 Talouden tilannekuva
        [Lyhyt, ammattimainen yhteenveto siitä, miltä tilanne näyttää suhteessa 70/20/10-sääntöön. Esim: "Välttämättömät menot vievät 80% tuloista, mikä luo riskiä..."]

        ## 💡 Huomiot kulurakenteesta
        * **Positiivista:** [Mikä on hyvin?]
        * **Kehitettävää:** [Missä on suurin vuoto?]

        ## 🔮 Ennuste
        [Jos kassavirta korjataan nollaan ja sijoitukset ({sijoitukset_summa}€/kk) jatkuvat, paljonko salkku on 10v päästä (7% tuotto)?]
        👉 **Potentiaali:** [Summa]

        ## ✅ Tärkein toimenpide
        [Yksi kirurgisen tarkka toimenpide. Jos puuttuu 16€, etsi se 16€, älä 700€.]

        Lopuksi anna talousrating (1-10) perustellen.

        HUOM: Ole suora, kannustava ja ratkaisukeskeinen. Älä käytä jargonia ilman selitystä.
        """

        response = model.generate_content(prompt)
        return response.text, jaama

    except Exception as e:
        return f"Virhe analyysissa: {str(e)}", 0

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








