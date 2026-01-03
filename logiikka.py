import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
import plotly.express as px
import os

# --- VÄRIT ---
PASTEL_COLORS = px.colors.qualitative.Pastel

def muotoile_suomi(luku):
    """Muotoilee luvun suomalaiseen tyyliin: 1 234,56 €"""
    if pd.isna(luku): return "0 €"
    formatted = f"{luku:,.0f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"

@st.cache_resource
def konfiguroi_ai():
    try:
        api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            return True
        return False
    except:
        return False
        
def luo_sankey(tulot_summa, df_menot_avg, jaama):
    labels = ["Tulot"] + df_menot_avg['Selite'].tolist() + ["Säästöt/Jäämä"]
    node_colors = [PASTEL_COLORS[i % len(PASTEL_COLORS)] for i in range(len(labels))]
    
    sources = [0] * (len(df_menot_avg) + 1)
    targets = list(range(1, len(df_menot_avg) + 2))
    values = df_menot_avg['Summa'].tolist() + [max(0, jaama)]

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=20, thickness=20, line=dict(color="gray", width=0.5), label=labels, color=node_colors),
        link=dict(source=sources, target=targets, value=values,
                  color=[node_colors[t].replace('rgb', 'rgba').replace(')', ', 0.3)') for t in targets])
    )])
    fig.update_layout(height=600, font_size=12, margin=dict(t=20, b=20))
    return fig

@st.cache_data
def lue_kaksiosainen_excel(file):
    try:
        df = pd.read_excel(file, header=None)
        col_b = df.iloc[:, 1].astype(str)
        tulot_idx = df[col_b.str.contains("Tulot", na=False, case=False)].index[0]
        menot_idx = df[col_b.str.contains("Menot", na=False, case=False)].index[0]
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
                    col_name = str(headers[col_idx])
                    if pd.notna(val) and val > 0:
                        data_rows.append({"Kategoria": kategoria, "Selite": selite, "Kuukausi": col_name, "Summa": round(val, 2)})

        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        return pd.DataFrame(data_rows)
    except:
        return pd.DataFrame()

def laske_tulevaisuus(aloitussumma, kk_saasto, korko_pros, vuodet):
    data = []
    saldo = aloitussumma
    oma_paaoma = aloitussumma 
    kk_korko = (korko_pros / 100) / 12
    data.append({"Vuosi": 0, "Oma pääoma": aloitussumma, "Tuotto": 0, "Yhteensä": aloitussumma})
    for kk in range(1, vuodet * 12 + 1):
        saldo += kk_saasto
        oma_paaoma += kk_saasto
        saldo *= (1 + kk_korko)
        if kk % 12 == 0: 
            data.append({"Vuosi": int(kk / 12), "Oma pääoma": round(oma_paaoma, 0), "Tuotto": round(saldo - oma_paaoma, 0), "Yhteensä": round(saldo, 0)})
    return pd.DataFrame(data)

def analysoi_talous(df_avg, profiili, data_tyyppi, df_raw):
    try:
        kk_lkm = df_raw['Kuukausi'].nunique()
        tulot = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama = tulot - menot
        
        sijoitus_keywords = ['sijoitus', 'rahasto', 'osake', 'säästö', 'nordnet', 'etf']
        sijoitukset_summa = df_avg[(df_avg['Kategoria']=='Meno') & (df_avg['Selite'].str.lower().str.contains('|'.join(sijoitus_keywords), na=False))]['Summa'].sum()
        todellinen_saasto = jaama + sijoitukset_summa
        top_menot = df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa').to_string(index=False)

        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        ### ROLE
        Toimit Senior Private Banker -roolissa. Analysoit asiakkaan talousdataa, tyyppi: **{data_tyyppi.upper()}**.

        ### OHJEET
        - JOS tyyppi on 'Budjetti': Arvioi suunnitelman realistisuutta.
        - JOS tyyppi on 'Toteuma': Arvioi kurinalaisuutta.

        ### DATA
        - Aikaväli: {kk_lkm} kuukautta.
        - Asiakas: {profiili['ika']}v, {profiili['suhde']}, {profiili['lapset']} lasta.
        - Tavoite: {profiili['tavoite']} (Tavoitesumma: {profiili['tavoite_summa']} €).
        - Tulot: {tulot:.0f} €/kk | Menot: {menot:.0f} €/kk | Jäämä: {jaama:.0f} €/kk.
        - Todellinen säästö (sis. sijoitukset): {todellinen_saasto:.0f} €/kk.
        - TOP 5 MENOT: {top_menot}

        ### TEHTÄVÄ
        Luo analyysi:
        ## 1. Tilannekuva ({data_tyyppi})
        Analysoi {kk_lkm} kk datan kattavuus ja realistisuus suhteessa tavoitteeseen.
        
        ## 2. Kulurakenne & Vuositason ennuste
        Analysoi suurimpia eriä ja skaalaa ne 12 kk tasolle.
        
        ## 3. Strategiset suositukset
        Anna 2-3 konkreettista parannusta.
        **Kahvikuppi-indeksi**: Laske 150 €/kk lisäsäästön vaikutus 10 vuodessa (7% korko).
        
        ## 4. Checklist askeleille [ ]
        ## 5. Matemaattinen ennuste (Varallisuuden kehitys)
        ## Arvosana (4-10)
        Perustele lyhyesti.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Virhe analyysissa: {str(e)}"

def chat_with_data(df, user_question, history):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        data_summary = df.head(50).to_string(index=False)
        prompt = f"Vastaa lyhyesti kysymykseen datan perusteella.\nDATA: {data_summary}\nHISTORIA: {history}\nKYSYMYS: {user_question}"
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Virhe yhteydessä."

