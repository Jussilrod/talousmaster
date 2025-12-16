import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

# --- ASETUKSET ---
st.set_page_config(
    page_title="TaskuEkonomisti 2.0",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Alustetaan chat-historia
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- CSS TYYLIT ---
local_css_path = "style.css"
if os.path.exists(local_css_path):
    with open(local_css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .main-title { font-size: 3rem; font-weight: 800; color: #0f172a; margin: 0; }
        .highlight-blue { 
            color: #2563eb; 
            background: -webkit-linear-gradient(45deg, #2563eb, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .slogan { font-size: 1.2rem; color: #64748b; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# Alustetaan AI
logiikka.konfiguroi_ai()

# --- SIVUPALKKI (VALIKKO & TIETOTURVA) ---
with st.sidebar:
    st.title("💎 Valikko")
    
    # 1. Lataus
    uploaded_file = st.file_uploader("📂 Lataa Excel", type=['xlsx'])
    
    st.markdown("---")
    
    # 2. Tietoturva (UUSI)
    with st.expander("🔒 Tietoturva & Yksityisyys", expanded=False):
        st.markdown("""
        <small>
        **Tietosi ovat turvassa.**
        
        1. **Ei tallennusta:** Lataamasi Excel käsitellään vain väliaikaisessa muistissa (RAM). Sitä ei tallenneta palvelimelle.
        2. **Anonyymi:** Tekoäly (Google Gemini) analysoi lukuja tilastollisesti. Henkilötietoja ei yhdistetä dataan.
        3. **Salaus:** Yhteys on SSL-suojattu.
        </small>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Vinkki: Täytä Exceliin kuukausisarakkeet (esim. Tammikuu, Helmikuu), niin näet trendit.")

# --- OTSIKKO (AINA NÄKYVISSÄ) ---
st.markdown("""
<div style="text-align: center; margin-top: 10px; margin-bottom: 30px;">
    <h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1>
    <p class="slogan">Ota taloutesi hallintaan datalla ja tekoälyllä</p>
</div>
""", unsafe_allow_html=True)

# --- PÄÄNÄKYMÄ ---

# 1. TILANNE: EI TIEDOSTOA (LASKEUTUMISSIVU)
if not uploaded_file:
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
            <h3>👋 Tervetuloa!</h3>
            <p>Tämä työkalu auttaa sinua ymmärtämään rahavirtojasi, ennustamaan vaurastumista ja löytämään säästökohteita tekoälyn avulla.</p>
            <p><strong>Aloita lataamalla Excel-tiedosto vasemmalta valikosta.</strong></p>
        </div>
        <br>
        """, unsafe_allow_html=True)

        video_path = "esittely.mp4"
        if os.path.exists(video_path):
            st.video(video_path, autoplay=True, muted=True)
        else:
            st.video("
