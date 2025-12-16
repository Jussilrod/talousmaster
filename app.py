import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime
from fpdf import FPDF

# --- KONFIGURAATIO ---
LOG_FILE = "talousdata_logi.csv"

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

# --- UUSI: EXCELIN LUKU AIKASARJANA ---
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

        # Tunnistetaan sarakkeet (C, D, E... eli indeksit 2, 3, 4...)
        # Oletetaan, että rivillä (tulot_idx - 1) on otsikot: "Selite", "Tammikuu", "Helmikuu"...
        header_row_idx = tulot_idx - 1 if tulot_idx > 0 else 0
        headers = df.iloc[header_row_idx]
        
        # Kerätään aikasarjadata
        data_rows = []

        def process_section(start_idx, end_idx, kategoria):
            section = df.iloc[start_idx:end_idx].copy()
            for _, row in section.iterrows():
                selite = str(row[1])
                if "Yhteensä" in selite or selite == "nan": continue
                
                # Käydään läpi kaikki sarakkeet indeksistä 2 eteenpäin
                for col_idx in range(2, df.shape[1]):
                    val = pd.to_numeric(row[col_idx], errors='coerce')
                    col_name = str(headers[col_idx]) if pd.notna(headers[col_idx]) else f"KK_{col_idx-1}"
                    
                    # Jos sarakeotsikko on tyhjä/nan, ei oteta
                    if col_name == "nan": continue

                    if pd.notna(val) and val > 0:
                        data_rows.append({
                            "Kategoria": kategoria,
                            "Selite": selite,
                            "Kuukausi": col_name, # Esim. "Tammikuu"
                            "Summa": round(val, 2)
                        })

        # Käsitellään osiot
        process_section(tulot_idx + 2, menot_idx, "Tulo")
        process_section(menot_idx + 2, len(df), "Meno")
        
        return pd.DataFrame(data_rows)

    except Exception as e:
        st.error(f"Virhe: {e}")
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
                "Oma pääoma": round(aloitussumma + (kk_saasto * kk), 0),
                "Tuotto": round(saldo - (aloitussumma + (kk_saasto * kk)), 0),
                "Yhteensä": round(saldo, 0)
            })
    return pd.DataFrame(data)

# --- ANALYYSI ---
def analysoi_talous(df, profiili, data_tyyppi):
    try:
        # Lasketaan keskiarvot jos on useita kuukausia
        df_aggr = df.groupby(['Kategoria', 'Selite'])['Summa'].mean().reset_index()
        tulot_yht = df_aggr[df_aggr['Kategoria']=='Tulo']['Summa'].sum()
        menot_yht = df_aggr[df_aggr['Kategoria']=='Meno']['Summa'].sum()
        jaama = tulot_yht - menot_yht
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Toimi varainhoitajana. Profiili: {profiili}. Data ({data_tyyppi}):
        Tulot avg: {tulot_yht}€, Menot avg: {menot_yht}€.
        Data: {df_aggr.to_string()}
        
        Analysoi lyhyesti:
        1. Tilannekuva
        2. Top kulut
        3. Yksi säästövinkki
        """
        response = model.generate_content(prompt)
        return response.text, jaama
    except Exception as e:
        return "Virhe analyysissa.", 0

# --- UUSI: CHAT-TOIMINTO ---
def chat_with_data(df, user_question, history):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Tiivistetään data promptiin
        data_summary = df.to_string(index=False)
        
        prompt = f"""
        Olet avulias talousassistentti TaskuEkonomisti-sovelluksessa.
        Käytössäsi on käyttäjän talousdata alla. Vastaa käyttäjän kysymykseen ytimekkäästi suomeksi.
        Jos kysymys ei liity talouteen, ohjaa kohteliaasti takaisin aiheeseen.
        
        DATA:
        {data_summary}
        
        KESKUSTELUHISTORIA:
        {history}
        
        KÄYTTÄJÄN KYSYMYS: {user_question}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "En pystynyt yhdistämään tekoälyyn juuri nyt."

# --- UUSI: PDF RAPORTTI ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'TaskuEkonomisti - Raportti', 0, 1, 'C')
        self.ln(10)

def luo_pdf_raportti(df, ai_analyysi, profiili):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Profiili
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Analyysi: {profiili['ika']}v, {profiili['suhde']}", 0, 1)
    pdf.set_font("Arial", size=12)
    
    # 2. Luvut
    tulot = df[df['Kategoria']=='Tulo']['Summa'].sum()
    menot = df[df['Kategoria']=='Meno']['Summa'].sum()
    pdf.cell(0, 10, f"Tulot yhteensa: {tulot:.2f} EUR", 0, 1)
    pdf.cell(0, 10, f"Menot yhteensa: {menot:.2f} EUR", 0, 1)
    pdf.cell(0, 10, f"Jaama: {tulot-menot:.2f} EUR", 0, 1)
    pdf.ln(10)
    
    # 3. AI Teksti (Huom: FPDF ei tue kaikkia unicode-merkkejä täydellisesti ilman fonttiasetuksia,
    # mutta tämä on yksinkertaistettu versio. Korvataan ääkköset varmuuden vuoksi tai hyväksytään perusfontti)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Tekoalyn huomiot:", 0, 1)
    pdf.set_font("Arial", size=10)
    
    # Pilkotaan pitkä teksti riveiksi
    clean_text = ai_analyysi.encode('latin-1', 'replace').decode('latin-1') # Quick fix encodingiin
    pdf.multi_cell(0, 8, clean_text)
    
    return pdf.output(dest='S').encode('latin-1')
