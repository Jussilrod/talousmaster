import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
import plotly.express as px
import os

# --- VÄRIT ---
# Määritellään globaali paletti
PASTEL_COLORS = px.colors.qualitative.Pastel

def muotoile_suomi(luku):
    """Muotoilee luvun suomalaiseen tyyliin: 1 234,56 €"""
    if pd.isna(luku): return "0 €"
    # Muutetaan piste pilkuksi ja lisätään tuhansien erottimeksi välilyönti
    formatted = f"{luku:,.0f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"

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
    labels = ["Tulot"] + df_menot_avg['Selite'].tolist() + ["Säästöt/Jäämä"]
    node_colors = [PASTEL_COLORS[i % len(PASTEL_COLORS)] for i in range(len(labels))]
    
    sources = [0] * (len(df_menot_avg) + 1)
    targets = list(range(1, len(df_menot_avg) + 2))
    values = df_menot_avg['Summa'].tolist() + [max(0, jaama)]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20, 
            thickness=20,
            line=dict(color="gray", width=0.5),
            label=labels,
            color=node_colors 
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=[node_colors[t].replace('rgb', 'rgba').replace(')', ', 0.3)') for t in targets]
        )
    )])
    
    fig.update_layout(height=600, font_size=12, margin=dict(t=20, b=20))
    fig.update_traces(textfont_color="black", selector=dict(type='sankey'))
    return fig

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
                    col_name = str(headers[col_idx]) if pd.notna(headers[col_idx]) else f"kk_{col_idx-1}"
                    if col_name == "nan": continue
                    if pd.notna(val) and val > 0:
                        data_rows.append({"Kategoria": kategoria, "Selite": selite, "Kuukausi": col_name, "Summa": round(val, 2)})

        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        return pd.DataFrame(data_rows)
    except Exception as e:
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
            tuotto = saldo - oma_paaoma
            data.append({
                "Vuosi": int(kk / 12),
                "Oma pääoma": round(oma_paaoma, 0),
                "Tuotto": round(tuotto, 0),
                "Yhteensä": round(saldo, 0)
            })
    return pd.DataFrame(data)

def analysoi_talous(df_avg, profiili, data_tyyppi):
    try:
        tulot = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama = tulot - menot
        
        sijoitukset_summa = 0
        sijoitus_keywords = ['sijoitus', 'rahasto', 'osake', 'säästö', 'nordnet', 'op-tuotto', 'ostot', 'etf']
        for _, row in df_avg[df_avg['Kategoria']=='Meno'].iterrows():
             if any(x in str(row['Selite']).lower() for x in sijoitus_keywords):
                 sijoitukset_summa += row['Summa']
        
        todellinen_saasto = jaama + sijoitukset_summa
        top_menot = df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa')
        kulut_txt = top_menot.to_string(index=False)

        if jaama < 0: status_txt = "Kriittinen (Alijäämäinen)"
        elif todellinen_saasto > 500: status_txt = "Vahva (Ylijäämäinen)"
        else: status_txt = "Tasapainoilija (Nollatulos)"

        model = genai.GenerativeModel('gemini-2.5-flash') # Päivitetty vakaampaan versioon
        
        prompt = f"""
       ### ROLE
Toimit kokeneena yksityispankkiirina (Senior Private Banker). Tyylisi on analyyttinen, tarkka ja asiantunteva, mutta samalla empaattinen ja kannustava. Puhetyylisi on ammattimainen suomi.

### CONTEXT
Analysoit asiakkaan taloutta pohjautuen Excel-dataan. 
Asiakasprofiili:
- Ikä: [ika] vuotta
- Kotitalous: [suhde], lapsia [lapset]
- Päätavoite: [tavoite]
- Nettovarallisuus: [varallisuus] €

Talousdata ([data_tyyppi]):
- Aikajakso: [kk] kuukauden toteuma
- Tulot: [tulot] €/kk
- Menot: [menot] €/kk
- Jäämä: [jaama] €/kk
- Todellinen säästöaste (sis. sijoitukset): [todellinen_saasto] €/kk
- Talouden tila: [status_txt]

Suurimmat kuluerät:
[kulut_txt]

### TASK
Luo kattava talousanalyysi seuraavalla rakenteella:

1. **Tilannekuva**: Arvioi nykyhetkeä suhteessa asiakkaan tavoitteeseen ([tavoite]). Onko tavoite realistinen nykyisellä säästöasteella?
2. **Kulujen rakenne**: Analysoi TOP 5 kuluja. Tee huomioita mahdollisista säästökohteista tai poikkeamista.
3. **Toimenpidesuositukset**:
    - Anna 3 konkreettista parannusehdotusta.
    - **Kahvikuppi-indeksi**: Laske, kuinka paljon pieni, toistuva menoerä (esim. 5 €/pvä) kasvaisi 10 vuodessa 7 % korolla. Käytä tätä havainnollistamaan säästämisen voimaa.
4. **Tehtävälista [ ]**: Luo 3-5 kohdan checklist, jonka asiakas voi toteuttaa heti.
5. **Ennuste**: Arvioi varallisuuden kehitystä 5-10 vuoden säteellä perustuen nykyiseen säästöön ja nettovarallisuuteen.
6. **Arvosana**: Anna talouden hoidolle arvosana (4-10) ja lyhyt perustelu.

### CONSTRAINTS
- Käytä Markdown-otsikoita (##).
- Ole rehellinen: jos talous on alijäämäinen, sano se suoraan mutta ratkaisukeskeisesti.
- Muotoile luvut selkeästi (esim. 1 250 €).
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




