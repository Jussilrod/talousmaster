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
        # --- 1. PYTHON-LASKENTA (Matemaattinen totuus) ---
        # Lasketaan faktat, jotta AI ei voi hallusinoida summia.
        tulot_yht = df[df['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot_yht = df[df['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama = tulot_yht - menot_yht
        saastoprosentti = (jaama / tulot_yht * 100) if tulot_yht > 0 else 0

        # Etsitään Top 3 kulut valmiiksi tekstiksi
        top_menot = df[df['Kategoria']=='Meno'].nlargest(3, 'Euroa_KK')
        top_menot_txt = ""
        for _, row in top_menot.iterrows():
            osuus = (row['Euroa_KK'] / tulot_yht * 100) if tulot_yht > 0 else 0
            top_menot_txt += f"* **{row['Selite']}**: {row['Euroa_KK']:.2f}€ ({osuus:.1f}% tuloista)\n"

        # Luodaan "Fakta-laatikko" promptiin
        kpi_stats = f"""
        - TULOT: {tulot_yht:.2f} €
        - MENOT: {menot_yht:.2f} €
        - JÄÄMÄ: {jaama:.2f} €
        - SÄÄSTÖASTE: {saastoprosentti:.1f} %
        """

        # Logiikka tilanneohjeelle
        if jaama > 500:
            tilanne_ohje = "Vahva ylijäämä. Keskity sijoittamiseen."
        elif jaama >= 0:
            tilanne_ohje = "Tasapainossa, mutta herkkä yllätyksille."
        else:
            tilanne_ohje = "Alijäämäinen! Vaatii nopeita leikkauksia."

        # Viitekehys
        financial_framework = """
        VIITEKEHYS (70/20/10):
        - 70% Välttämättömät (Asuminen, ruoka, laskut)
        - 20% Elämäntyyli (Huvit, ostokset, ravintolat)
        - 10% Säästöt (Sijoitukset, puskuri, lainanlyhennys)
        """

        # --- 2. PROMPT ENGINEERING (Analyytikko) ---
        model = genai.GenerativeModel('gemini-2.5-flash')
        data_txt = df.to_string(index=False)

        prompt = f"""
        ### ROLE
        Toimit empaattisena mutta tiukkana Senior Financial Plannerina. Autat asiakasta näkemään numeroiden taakse.

        ### CONTEXT & DATA
        - **Profiili:** {profiili['ika']}v, {profiili['suhde']}, {profiili['lapset']} lasta.
        - **Status:** {tilanne_ohje} ({data_tyyppi})

        ### ABSOLUUTTISET FAKTAT (Käytä näitä lukuja, ne on laskettu valmiiksi)
        {kpi_stats}

        ### SUURIMMAT KULUT (Top 3 valmiiksi laskettuna)
        {top_menot_txt}

        ### RIVIDATA (Lähdeaineisto analyysiin)
        {data_txt}

        ### INSTRUCTIONS (Tee tämä)
        1. **70/20/10 Arvio:** Rividatassa ei lue mikä on "hupia" ja mikä "pakollista". Sinun täytyy päätellä se rivien nimistä (esim. Vuokra=Pakollinen, Netflix=Hupi). Tee arvio, miten asiakkaan kulutus jakautuu näihin koreihin suhteessa faktoihin.
        2. **Kuluanalyysi:** Kommentoi yllä mainittuja TOP 3 kuluja. Ovatko ne järkeviä tälle profiilille?
        3. **Simulaatio:** - Jos jäämä > 0: Laske korkoa korolle (7% tuotto) summalle {jaama:.0f}€ per kk, aika 10 vuotta.
           - Jos jäämä < 0: Laske paljonko velkaa kertyy vuodessa ({jaama:.0f}€ * 12).
        4. **Toimenpide:** Anna vain yksi, kaikkein tärkein neuvo.

        ### OUTPUT FORMAT (Markdown)

        ## 📊 Talouden "Health Check"
        [Tiivis sanallinen yhteenveto tilanteesta].
        * **Välttämättömät:** ~X% (Tavoite 70%)
        * **Elämäntyyli:** ~X% (Tavoite 20%)
        * **Säästöt:** {saastoprosentti:.1f}% (Tavoite 10%)

        ## 📉 Kulupaljastus (Top 3 Syöppöä)
        [Kopioi täsmälleen yllä oleva "Suurimmat kulut" -lista tähän ja lisää lyhyt, terävä kommentti jokaisen perään. Esim. "Liikaa yhdelle hengelle!"]

        ## 🔮 Tulevaisuus-simulaatio (10v)
        [Motivoiva tai varoittava laskelma perustuen lukuun {jaama:.0f}€/kk]
        👉 **Lopputulos:** [Esim: "Sijoittamalla tämän summan, salkkusi on 10v päästä **XX XXX €**."]

        ## ✅ Tärkein toimenpide (Tee tämä heti)
        [Yksi konkreettinen käsky imperatiivissa. Esim. "Lopeta X ja siirrä raha Y..."]
        
        **Arvosana taloudelle (4-10):** [X]/10
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




