import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
import os

def konfiguroi_ai():
    try:
        api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            return True
        return False
    except:
        return False

@st.cache_data
def lue_kaksiosainen_excel(file):
    try:
        df = pd.read_excel(file, header=None)
        col_b = df.iloc[:, 1].astype(str)
        tulot_idx = df[col_b.str.contains("Tulot", na=False, case=False)].index[0]
        menot_idx = df[col_b.str.contains("Menot", na=False, case=False)].index[0]
        
        headers = df.iloc[tulot_idx - 1]
        data_rows = []

        def process_section(start_idx, end_idx, kategoria):
            section = df.iloc[start_idx:end_idx].copy()
            for _, row in section.iterrows():
                selite = str(row[1])
                if "Yhteensä" in selite or selite == "nan": continue
                for col_idx in range(2, df.shape[1]):
                    val = pd.to_numeric(row[col_idx], errors='coerce')
                    col_name = str(headers[col_idx])
                    if col_name != "nan" and pd.notna(val) and val > 0:
                        data_rows.append({"Kategoria": kategoria, "Selite": selite, "Kuukausi": col_name, "Summa": round(val, 2)})

        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        return pd.DataFrame(data_rows)
    except:
        return pd.DataFrame()

def luo_sankey_kaavio(tulot_summa, df_menot_avg, jaama):
    labels = ["Tulot"] + df_menot_avg['Selite'].tolist() + ["Säästö/Jäämä"]
    sources = [0] * (len(df_menot_avg) + 1)
    targets = list(range(1, len(df_menot_avg) + 2))
    values = df_menot_avg['Summa'].tolist() + [max(0, jaama)]
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels, color="#3b82f6"),
        link=dict(source=sources, target=targets, value=values, color="rgba(37, 99, 235, 0.2)")
    )])
    fig.update_layout(title_text="Rahan virtaus: Tulot -> Menot & Säästöt", font_size=12)
    return fig

def laske_tulevaisuus(aloitussumma, kk_saasto, korko_pros, vuodet):
    data = []
    saldo = aloitussumma
    oma_paaoma = aloitussumma
    kk_korko = (korko_pros / 100) / 12
    data.append({"Vuosi": 0, "Oma pääoma": aloitussumma, "Tuotto": 0, "Yhteensä": aloitussumma})

    for kk in range(1, vuodet * 12 + 1):
        saldo = (saldo + kk_saasto) * (1 + kk_korko)
        oma_paaoma += kk_saasto
        if kk % 12 == 0:
            data.append({"Vuosi": int(kk/12), "Oma pääoma": round(oma_paaoma,0), "Tuotto": round(saldo-oma_paaoma,0), "Yhteensä": round(saldo,0)})
    return pd.DataFrame(data)

def analysoi_talous(df_avg, profiili, data_tyyppi):
    try:
        tulot = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama = tulot - menot
        top_menot = df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa').to_string(index=False)

        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        ROOLI: Yksityispankkiiri. ASIAKAS: {profiili['ika']}v, {profiili['suhde']}, tavoite: {profiili['tavoite']}.
        DATA: Tulot {tulot}€, Menot {menot}€, Jäämä {jaama}€. TOP KULUT: {top_menot}.
        
        TEHTÄVÄ:
        1. Tilannekuva: Onko tavoite realistinen?
        2. Kahvikuppi-indeksi: Kerro säästöpotentiaali {jaama}€ konkreettisina asioina (esim. noutokahveina tai suoratoistotilauksina).
        3. Toimintasuunnitelma: Luo 3 kohdan Checklist [ ] Markdownina.
        4. Käytä kaavaa $$A = P(1 + r/n)^{{nt}}$$ jos selität korkoa korolle.
        """
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Virhe analyysissa: {str(e)}"

def chat_with_data(df, user_question, history):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        summary = df.groupby(['Kategoria', 'Selite'])['Summa'].mean().to_string()
        prompt = f"Vastaa lyhyesti datan perusteella. Yhteenveto: {summary}\nKysymys: {user_question}"
        return model.generate_content(prompt).text
    except:
        return "Virhe yhteydessä."
