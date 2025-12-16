import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

# --- ASETUKSET ---
st.set_page_config(
    page_title="TaskuEkonomisti",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx"

# --- TYYLIT ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# Alustetaan tekoäly
logiikka.konfiguroi_ai()

# --- SIVUPALKKI (NAVIGAATIO & ASETUKSET) ---
with st.sidebar:
    st.markdown("### ⚙️ Hallintapaneeli")
    
    # 1. Lataa pohja
    with open(EXCEL_TEMPLATE_NAME, "rb") as file:
        st.download_button(
            label="📥 Lataa Excel-pohja",
            data=file,
            file_name="talous_tyokalu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # 2. Lataa oma data (Tämä on nyt sivupalkissa, jotta se on aina saatavilla)
    uploaded_file = st.file_uploader("📂 Lataa oma Excelisi", type=['xlsx'])
    
    st.markdown("---")
    st.info("💡 **Vinkki:** Voit piilottaa tämän sivupalkin nuolesta, kun haluat lisää tilaa graafeille.")

# --- PÄÄNÄKYMÄ ---

# OTSIKKO
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1>
    <p class="slogan">Ota taloutesi hallintaan datalla ja tekoälyllä</p>
</div>
""", unsafe_allow_html=True)

# LOGIIKKA: NÄYTETÄÄN ERI SISÄLTÖÄ RIIPPUEN ONKO TIEDOSTO LADATTU
if not uploaded_file:
    # --- TILANNE A: EI TIEDOSTOA (Laskeutumissivu) ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div style="text-align: center; font-size: 1.2rem; margin-bottom: 20px;">👇 Aloita lataamalla Excel-tiedosto sivupalkista tai katso video</div>', unsafe_allow_html=True)
        
        # Video keskitetysti
        video_path = "esittely.mp4"
        if os.path.exists(video_path):
            st.video(video_path, autoplay=True, muted=True)
        else:
            st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4", autoplay=True, muted=True)

else:
    # --- TILANNE B: DATA LADATTU (Dashboard) ---
    df_laskettu = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        # Lasketaan KPI-luvut heti kärkeen
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot

        # 1. YLÄOSAN KPI-MITTARIT
        with st.container(border=True):
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Tulot", f"{tulot:,.0f} €")
            kpi2.metric("Menot", f"{menot:,.0f} €", delta="-menot", delta_color="inverse")
            kpi3.metric("Jäämä", f"{jaama_preview:,.0f} €", delta=f"{jaama_preview:,.0f} €")

        st.write("") # Tyhjää tilaa

        # 2. VÄLILEHDET (TABS) - TÄMÄ ON SE "HELPPO SIIRTYMÄ"
        tab_visual, tab_sim, tab_ai = st.tabs([
            "📊 Visualisointi & Kassavirta", 
            "🔮 Miljonääri-simulaattori", 
            "🤖 AI-Analyysi & Suositukset"
        ])

        # --- TAB 1: VISUALISOINTI ---
        with tab_visual:
            st.subheader("Miten rahasi liikkuvat?")
            
            # Vesiputouskaavio
            menot_df = df_laskettu[df_laskettu['Kategoria']=='Meno'].copy().sort_values(by='Euroa_KK', ascending=False)
            
            TOP_N = 6
            if len(menot_df) > TOP_N:
                top_menot = menot_df.iloc[:TOP_N]
                muut_summa = menot_df.iloc[TOP_N:]['Euroa_KK'].sum()
                labels = ["Tulot"] + top_menot['Selite'].tolist() + ["Muut menot", "JÄÄMÄ"]
                values = [tulot] + [x * -1 for x in top_menot['Euroa_KK'].tolist()] + [muut_summa * -1, 0]
                measure = ["absolute"] + ["relative"] * (len(top_menot) + 1) + ["total"]
            else:
                labels = ["Tulot"] + menot_df['Selite'].tolist() + ["JÄÄMÄ"]
                values = [tulot] + [x * -1 for x in menot_df['Euroa_KK'].tolist()] + [0]
                measure = ["absolute"] + ["relative"] * len(menot_df) + ["total"]

            fig_waterfall = go.Figure(go.Waterfall(
                name = "Kassavirta", orientation = "v", measure = measure, x = labels, y = values,
                text = [f"{val:,.0f}€" for val in values[:-1]] + [f"{jaama_preview:,.0f}€"],
                textposition = "outside",
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
                decreasing = {"marker":{"color":"#ef4444"}},
                increasing = {"marker":{"color":"#22c55e"}},
                totals = {"marker":{"color":"#3b82f6"}}
            ))
            fig_waterfall.update_layout(title="Kassavirran vesiputous", height=500, waterfallgap=0.1)
            st.plotly_chart(fig_waterfall, use_container_width=True)
            
            with st.expander("Näytä tarkka kululista"):
                st.dataframe(menot_df[['Selite', 'Euroa_KK']].style.format({"Euroa_KK": "{:.2f} €"}), use_container_width=True)

        # --- TAB 2: SIMULAATTORI ---
        with tab_sim:
            st.subheader("Korkoa korolle -laskuri")
            st.caption("Pienikin kuukausisäästö kasvaa suureksi ajallaan.")
            
            sc1, sc2 = st.columns([1, 2])
            with sc1:
                start_val = float(jaama_preview) if jaama_preview > 0 else 50.0
                kk_saasto_sim = st.slider("Säästösumma (€/kk)", 0.0, 3000.0, start_val, step=10.0)
                vuodet_sim = st.slider("Aika (vuotta)", 1, 50, 20)
                tuotto_sim = st.slider("Tuotto-odotus (%)", 1.0, 15.0, 7.0)
                alkupotti = st.number_input("Nykyinen salkku (€)", 0, 1000000, 0)
            
            with sc2:
                df_sim = logiikka.laske_tulevaisuus(alkupotti, kk_saasto_sim, tuotto_sim, vuodet_sim)
                loppusumma = df_sim.iloc[-1]['Yhteensä']
                profitti = df_sim.iloc[-1]['Tuotto']
                
                st.metric("Salkun arvo lopussa", f"{loppusumma:,.0f} €", delta=f"+{profitti:,.0f} € korkotuottoa")
                
                fig_area = px.area(df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"], 
                                  color_discrete_map={"Oma pääoma": "#cbd5e1", "Tuotto": "#22c55e"})
                fig_area.update_layout(hovermode="x unified")
                st.plotly_chart(fig_area, use_container_width=True)

        # --- TAB 3: AI ANALYYSI ---
        with tab_ai:
            st.subheader("Tekoälyn varainhoitaja")
            st.caption("Syötä taustatiedot, niin AI etsii säästökohteet puolestasi.")
            
            with st.form("ai_form"):
                ac1, ac2, ac3 = st.columns(3)
                with ac1: ika = st.number_input("Ikä", 15, 100, 30)
                with ac2: suhde = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perheellinen", "YH"])
                with ac3: lapset = st.number_input("Lapset", 0, 10, 0)
                
                data_tyyppi = st.radio("Datan tyyppi", ["Suunnitelma (Budjetti)", "Toteuma (Tiliote)"], horizontal=True)
                
                submit_ai = st.form_submit_button("✨ Analysoi talouteni", type="primary", use_container_width=True)

            if submit_ai:
                with st.spinner('Tekoäly käy läpi tilitietojasi...'):
                    profiili = {"ika": ika, "suhde": suhde, "lapset": lapset}
                    vastaus, _ = logiikka.analysoi_talous(df_laskettu, profiili, data_tyyppi)
                    
                    st.markdown("### 📝 Analyysin tulos")
                    st.markdown(vastaus)

    else:
        st.error("Tiedoston luku epäonnistui. Tarkista, että Excelissä on sarakkeet oikein.")
