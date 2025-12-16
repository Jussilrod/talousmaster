import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

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

# --- EXCELIN LUKU ---
@st.cache_data
def lue_kaksiosainen_excel(file):
    try:
        df = pd.read_excel(file, header=None)
        col_b = df.iloc[:, 1].astype(str)
        try:
            tulot_idx = df[col_b.str.contains("Tulot", na=False, case=False)].index[0]
            menot_idx = df[col_b.str.contains("Menot", na=False, case=False)].index[0]
        except IndexError:
            return pd.DataFrame()

        header_row_idx = tulot_idx - 1 if tulot_idx > 0 else 0
        headers = df.iloc[header_row_idx]
        data_rows = []

        def process_section(start_idx, end_idx, kategoria):
            section = df.iloc[start_idx:end_idx].copy()
            for _, row in section.iterrows():
                selite = str(row[1])
                if "Yhteensä" in selite or selite == "nan": continue
                for col_idx in range(2, df.shape[1]):
                    val = pd.to_numeric(row[col_idx], errors='coerce')
                    col_name = str(headers[col_idx]) if pd.notna(headers[col_idx]) else f"KK_{col_idx-1}"
                    if col_name == "nan": continue
                    if pd.notna(val) and val > 0:
                        data_rows.append({"Kategoria": kategoria, "Selite": selite, "Kuukausi": col_name, "Summa": round(val, 2)})

        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        return pd.DataFrame(data_rows)
    except Exception as e:
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
            data.append({"Vuosi": int(kk / 12), "Yhteensä": round(saldo, 0)})
    return pd.DataFrame(data)

# --- ANALYYSI (KORJATTU MALLI & TIEDOT) ---
def analysoi_talous(df, profiili, data_tyyppi):
    try:
        tulot_yht = df[df['Kategoria']=='Tulo']['Summa'].sum()
        menot_yht = df[df['Kategoria']=='Meno']['Summa'].sum()
        
        sijoitukset_summa = 0
        sijoitus_keywords = ['sijoitus', 'rahasto', 'osake', 'säästö', 'nordnet', 'op-tuotto', 'ostot', 'etf']
        for _, row in df[df['Kategoria']=='Meno'].iterrows():
             if any(x in str(row['Selite']).lower() for x in sijoitus_keywords):
                 sijoitukset_summa += row['Summa']

        jaama = tulot_yht - menot_yht
        todellinen_saasto = jaama + sijoitukset_summa
        
        top_menot = df[df['Kategoria']=='Meno'].nlargest(3, 'Summa')
        top_menot_txt = ""
        for _, row in top_menot.iterrows():
            osuus = (row['Summa'] / tulot_yht * 100) if tulot_yht > 0 else 0
            top_menot_txt += f"* **{row['Selite']}**: {row['Summa']:.2f}€ ({osuus:.1f}%)\n"

        if jaama < 0 and todellinen_saasto > 0:
            strategia = "KASSAVIRTA-OPTIMOINTI. Asiakas sijoittaa enemmän kuin on varaa käteistä."
            tilanne_teksti = "Investointivetoinen alijäämä"
        elif jaama < 0:
            strategia = "HÄTÄJARRUTUS. Talous vuotaa."
            tilanne_teksti = "Aito alijäämä"
        else:
            strategia = "VARALLISUUDEN KASVATUS."
            tilanne_teksti = "Ylijäämäinen"

        kpi_stats = f"""
        - TULOT: {tulot_yht:.2f} €
        - MENOT: {menot_yht:.2f} €
        - KASSAVIRTA: {jaama:.2f} €
        - SIJOITUKSET: {sijoitukset_summa:.2f} €
        """
        
        # Datatyypin ohjeistus
        tyyppi_ohje = "HUOM: Data on TOTEUMA (oikeasti tapahtunut)." if "Toteuma" in str(data_tyyppi) else "HUOM: Data on BUDJETTI (suunnitelma)."

        # KÄYTETÄÄN TOIMIVAKSI TODETTUA MALLIA
        model = genai.GenerativeModel('gemini-2.5-flash')
        data_txt = df.to_string(index=False)

        prompt = f"""
        ### ROLE
        Toimit varainhoitajana.

        ### CONTEXT
        - Profiili: {profiili['ika']}v, {profiili['suhde']}.
        - Lapset: {profiili.get('lapset', 0)} kpl.
        - Tilanne: {tilanne_teksti}
        - Datan tyyppi: {tyyppi_ohje}
        
        ### STRATEGIA
        {strategia}

        ### FAKTAT:
        {kpi_stats}

        ### TOP KULUT:
        {top_menot_txt}

        ### DATA:
        {data_txt}

        ### TEHTÄVÄ
        Kirjoita Markdown-analyysi:
        1. **Tilannekuva**: Ota kantaa elämäntilanteeseen (lapset, ikä) ja lukuihin.
        2. **Huomiot kuluista**: Mikä on hyvin/huonosti?
        3. **Ennuste**: Jos nykyinen säästö ({todellinen_saasto:.0f}€) jatkuu 10v (7%), mikä on potti?
        4. **Toimenpide**: Yksi konkreettinen neuvo.
        5. **Rating**: Arvosana 1-10.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Virhe analyysissa: {str(e)}"

# --- CHAT ---
def chat_with_data(df, user_question, history):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        data_summary = df.head(50).to_string(index=False)
        prompt = f"""
        Vastaa lyhyesti kysymykseen datan perusteella.
        DATA: {data_summary}
        HISTORIA: {history}
        KYSYMYS: {user_question}
        """
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Virhe yhteydessä."
