import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
import plotly.express as px
import os

# --- KONFIGURAATIO ---
@st.cache_resource
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
        
def luo_sankey(tulot_summa, df_menot_avg, jaama):
    # Luodaan värit kategorioille käyttäen Plotlyn valmista palettia
    color_palette = px.colors.qualitative.Pastel
    
    labels = ["Tulot"] + df_menot_avg['Selite'].tolist() + ["Säästöt/Jäämä"]
    
    # Määritellään värit solmuille
    node_colors = [color_palette[i % len(color_palette)] for i in range(len(labels))]
    
    sources = [0] * (len(df_menot_avg) + 1)
    targets = list(range(1, len(df_menot_avg) + 2))
    values = df_menot_avg['Summa'].tolist() + [max(0, jaama)]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20, # Lisää väliä solmujen välille tarkkuuden parantamiseksi
            thickness=20,
            line=dict(color="gray", width=0.5),
            label=labels,
            color=node_colors # Käytetään uusia värejä
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            # Tehdään linkeistä solmun värisiä mutta läpinäkyviä
            color=[node_colors[t].replace('rgb', 'rgba').replace(')', ', 0.3)') for t in targets]
        )
    )])
    
    # Säädetään korkeutta, jotta se ei ole niin "epätarkka"
    fig.update_layout(height=600, font_size=12)

    # Pakotetaan tekstin renderöinti ilman varjoja (halo: 0)
    fig.update_traces(textfont_color="black", selector=dict(type='sankey'))
    
    return fig

# --- EXCELIN LUKU ---
@st.cache_data
def lue_kaksiosainen_excel(file):
    try:
        # Luetaan koko tiedosto kerralla
        df = pd.read_excel(file, header=None)
        
        # Etsitään "Tulot" ja "Menot" tekstien sijainnit B-sarakkeesta (index 1)
        col_b = df.iloc[:, 1].astype(str)
        try:
            tulot_idx = df[col_b.str.contains("Tulot", na=False, case=False)].index[0]
            menot_idx = df[col_b.str.contains("Menot", na=False, case=False)].index[0]
        except IndexError:
            return pd.DataFrame()

        # Otsikot (kuukaudet) ovat yleensä riviä ennen "Tulot"-otsikkoa
        header_row_idx = tulot_idx - 1
        headers = df.iloc[header_row_idx]
        
        data_rows = []

        def process_section(start_idx, end_idx, kategoria):
            # Käydään läpi rivit (Selitteet)
            section = df.iloc[start_idx:end_idx].copy()
            for _, row in section.iterrows():
                selite = str(row[1]).strip()
                # Ohitetaan tyhjät tai "Yhteensä"-rivit
                if not selite or selite == "nan" or "yhteensä" in selite.lower():
                    continue
                
                # Käydään läpi sarakkeet alkaen indeksistä 2 (C-sarake eteenpäin)
                for col_idx in range(2, df.shape[1]):
                    # Napataan sarakkeen nimi (kuukausi)
                    col_name = str(headers[col_idx]).strip()
                    if col_name == "nan" or not col_name:
                        continue
                    
                    # Muutetaan summa numeroksi (käsittelee tyhjät solut nollina)
                    val = pd.to_numeric(row[col_idx], errors='coerce')
                    
                    if pd.notna(val) and val != 0:
                        data_rows.append({
                            "Kategoria": kategoria, 
                            "Selite": selite, 
                            "Kuukausi": col_name, 
                            "Summa": float(val)
                        })

        # Prosessoidaan tulot ja menot
        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        
        return pd.DataFrame(data_rows)
    except Exception as e:
        print(f"Lukuivirhe: {e}")
        return pd.DataFrame()

# --- SIMULOINTI (PÄIVITETTY: EROTTELEE PÄÄOMAN JA TUOTON) ---
def laske_tulevaisuus(aloitussumma, kk_saasto, korko_pros, vuodet):
    data = []
    saldo = aloitussumma
    oma_paaoma = aloitussumma # Seurataan paljonko on talletettu itse taskusta
    
    kk_korko = (korko_pros / 100) / 12
    
    # Lisätään alkupiste (Vuosi 0)
    data.append({
        "Vuosi": 0,
        "Oma pääoma": aloitussumma,
        "Tuotto": 0,
        "Yhteensä": aloitussumma
    })

    for kk in range(1, vuodet * 12 + 1):
        saldo += kk_saasto
        oma_paaoma += kk_saasto
        saldo *= (1 + kk_korko)
        
        # Tallennetaan data kerran vuodessa
        if kk % 12 == 0: 
            tuotto = saldo - oma_paaoma
            data.append({
                "Vuosi": int(kk / 12),
                "Oma pääoma": round(oma_paaoma, 0),
                "Tuotto": round(tuotto, 0),
                "Yhteensä": round(saldo, 0)
            })
            
    return pd.DataFrame(data)

# --- ANALYYSI (PARANNETTU KONTEKSTI) ---
def analysoi_talous(df_avg, profiili, data_tyyppi):
    try:
        # 1. Laskenta (pysyy samana)
        tulot = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama = tulot - menot
        
        sijoitukset_summa = 0
        sijoitus_keywords = ['sijoitus', 'rahasto', 'osake', 'säästö', 'nordnet', 'op-tuotto', 'ostot', 'etf']
        for _, row in df_avg[df_avg['Kategoria']=='Meno'].iterrows():
             if any(x in str(row['Selite']).lower() for x in sijoitus_keywords):
                 sijoitukset_summa += row['Summa']
        
        todellinen_saasto = jaama + sijoitukset_summa

        # Top kulut
        top_menot = df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa')
        kulut_txt = top_menot.to_string(index=False)

        # 2. Älykäs tilannetulkinta
        if jaama < 0:
            status_txt = "Kriittinen (Alijäämäinen)"
        elif todellinen_saasto > 500:
            status_txt = "Vahva (Ylijäämäinen)"
        else:
            status_txt = "Tasapainoilija (Nollatulos)"

        # 3. PROMPT ENGINEERING (KORJATTU HENKILÖKUVAUS)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        prompt = f"""
        ### ROLE
        Toimit yksityispankkiirina (Private Banker). Tyylisi on analyyttinen mutta empaattinen.
        
        ### ASIAKASPROFIILI (Tärkeä: Erota henkilö ja kotitalous)
        - **Henkilö:** {profiili['ika']}-vuotias aikuinen.
        - **Kotitalous:** {profiili['suhde']}. Lapsia: {profiili['lapset']}.
        - **Päätavoite:** {profiili['tavoite']}
        - **Nettovarallisuus:** {profiili['varallisuus']} € (Asunnot + sijoitukset - velat)
        
        ### TALOUDEN DATA ({data_tyyppi})
        - Tulot: {tulot:.0f} €/kk
        - Menot: {menot:.0f} €/kk
        - Jäämä: {jaama:.0f} €/kk
        - Säästöön menee nyt (sis. sijoitukset): {todellinen_saasto:.0f} €/kk
        - Talouden tila: {status_txt}

        ### TOP 5 KULUERÄT
        {kulut_txt}

        ### TEHTÄVÄ
        Luo Markdown-muotoinen analyysi (älä käytä otsikoissa risuaitaa # vaan ##):

        ## 1. Tilannekuva
        Kuvaile tilannetta luonnollisesti. Esim. "Olet 37-vuotias ja elät lapsiperhearkea..." eikä "Olet 37-vuotias perhe".
        Peilaa nykytilannetta ilmoitettuun tavoitteeseen ("{profiili['tavoite']}"). Onko se realistinen näillä luvuilla?

        ## 2. Kulujen rakenne
        Analysoi TOP-kuluja. Ovatko ne linjassa perhekoon ({profiili['lapset']} lasta) kanssa? 
        Jos lapsia on, huomioi se (esim. ruokakulut ovat luonnostaan korkeammat).

        ## 3. Toimenpidesuositus
        Anna YKSI konkreettinen neuvo. Muuta säästöpotentiaali "Kahvikuppi-indeksiksi" 
        (esim. "Tämä säästö vastaa 12 noutokahvia kuukaudessa").

        ## 4. Tehtävälista (Checklist)
        Luo 3 kohdan interaktiivinen tehtävälista Markdown-muodossa [ ], jolla käyttäjä pääsee alkuun.
        
        ## 5. Ennuste
        Jos nykyinen säästötahti ({todellinen_saasto:.0f}€/kk) jatkuu, onko tavoite saavutettavissa?

        ## Arvosana (4-10)
        Perustele lyhyesti.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Virhe analyysissa: {str(e)}"
        

# --- CHAT ---
def chat_with_data(df, user_question, history):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
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













