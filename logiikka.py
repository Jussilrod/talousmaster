import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime

# --- KONFIGURAATIO ---
def konfiguroi_ai():
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key and "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
        
        if api_key:
            genai.configure(api_key=api_key)
            return True
        return False
    except:
        return False

# --- EXCELIN LUKU (AIKASARJATUKI) ---
@st.cache_data
def lue_kaksiosainen_excel(file):
    try:
        df = pd.read_excel(file, header=None)
        
        # Etsitään Tulot ja Menot rivit
        col_b = df.iloc[:, 1].astype(str)
        try:
            tulot_idx = df[col_b.str.contains("Tulot", na=False, case=False)].index[0]
            menot_idx = df[col_b.str.contains("Menot", na=False, case=False)].index[0]
        except IndexError:
            return pd.DataFrame()

        # Oletetaan, että rivillä (tulot_idx - 1) on otsikot: "Selite", "Tammikuu", "Helmikuu"...
        header_row_idx = tulot_idx - 1 if tulot_idx > 0 else 0
        headers = df.iloc[header_row_idx]
        
        data_rows = []

        def process_section(start_idx, end_idx, kategoria):
            section = df.iloc[start_idx:end_idx].copy()
            for _, row in section.iterrows():
                selite = str(row[1])
                if "Yhteensä" in selite or selite == "nan": continue
                
                # Käydään läpi sarakkeet C (indeksi 2) eteenpäin
                for col_idx in range(2, df.shape[1]):
                    val = pd.to_numeric(row[col_idx], errors='coerce')
                    col_name = str(headers[col_idx]) if pd.notna(headers[col_idx]) else f"KK_{col_idx-1}"
                    
                    if col_name == "nan": continue

                    if pd.notna(val) and val > 0:
                        data_rows.append({
                            "Kategoria": kategoria,
                            "Selite": selite,
                            "Kuukausi": col_name,
                            "Summa": round(val, 2)
                        })

        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        
        return pd.DataFrame(data_rows)

    except Exception as e:
        st.error(f"Virhe tiedoston luvussa: {e}")
        return pd.DataFrame()

# --- SIMULOINTI ---
def laske_tulevaisuus(aloitussumma, kk_saasto, korko_pros, vuodet):
    data = []
    saldo = aloitussumma
    kk_korko = (korko_pros / 100) / 12
    for kk in range(vuodet * 12):
        saldo += kk_saasto
        saldo *= (1 + kk_korko)
        if kk % 12 == 0: 
            data.append({
                "Vuosi": int(kk / 12),
                "Yhteensä": round(saldo, 0)
            })
    return pd.DataFrame(data)
    
    
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
        Yksinkertainen "hei riittää. Ei jaaritteluja, ystävällinen voi olla.

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

# --- CHAT ---
def chat_with_data(df, user_question, history):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        data_summary = df.head(50).to_string(index=False) # Rajoitetaan datamäärää promptissa
        
        prompt = f"""
        Olet TaskuEkonomisti-assistentti. Vastaa lyhyesti suomeksi käyttäjän kysymykseen datan perusteella.
        DATA (Ote):
        {data_summary}
        
        HISTORIA: {history}
        KYSYMYS: {user_question}
        """
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Tekoälyyn ei saada yhteyttä."













