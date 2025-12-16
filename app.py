import streamlit as st
import pandas as pd
import plotly.express as px  # UUSI KIRJASTO
import logiikka
import os

# --- ASETUKSET ---
st.set_page_config(
    page_title="TaskuEkonomisti",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
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

# --- UI RAKENNE ---

# 1. OTSIKKO
st.markdown("""
<div>
    <h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1>
    <p class="slogan">Varmista, että rahasi pysyvät taskussa eivätkä lennä muille 💸</p>
</div>
""", unsafe_allow_html=True)

# 2. PÄÄOSIO (Lataus ja Video)
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    with st.container(border=True):
        st.subheader("1. Lataa ja analysoi")
        st.write("Lataa täytetty Excel-pohja tähän.")
        
        # Excel latausnappi (Template)
        try:
            with open(EXCEL_TEMPLATE_NAME, "rb") as file:
                st.download_button(
                    label="📥 Lataa tyhjä Excel-pohja",
                    data=file,
                    file_name="talous_tyokalu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except:
            st.warning("⚠️ Pohjatiedostoa ei löytynyt.")

        st.markdown("---")
        
        uploaded_file = st.file_uploader("Pudota täytetty Excel tähän", type=['xlsx'], label_visibility="collapsed")
        
        if uploaded_file:
            st.success("Tiedosto ladattu onnistuneesti! Analysoidaan...")

with col_right:
    # Piilotetaan video jos tiedosto on ladattu, jotta tilaa jää datalle
    if not uploaded_file:
        st.markdown('<p class="video-title">Ota taloutesi hallintaan datalla</p>', unsafe_allow_html=True)
        video_path = "esittely.mp4"
        if os.path.exists(video_path):
            st.video(video_path, autoplay=True, muted=True)
        else:
            st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4", autoplay=True, muted=True)

# 3. ANALYYSI JA GRAAFIT
if uploaded_file:
    # Haetaan data
    df_laskettu = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        # Lasketaan perustiedot
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot

        st.divider()

        # --- A. KPI MITTARIT ---
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Tulot", f"{tulot:,.0f} €", delta_color="normal")
        kpi2.metric("Menot", f"{menot:,.0f} €", delta="-menot", delta_color="inverse") # Punainen jos iso
        kpi3.metric("Jäämä / KK", f"{jaama_preview:,.0f} €", delta=f"{jaama_preview:,.0f} €")

        # --- B. VISUALISOINTI (UUSI) ---
        st.subheader("📊 Mihin rahasi menevät?")
        
        g1, g2 = st.columns([1, 1])
        
        with g1:
            # 1. Donut chart: Tulot vs Menot (Yksinkertainen yleiskuva)
            balanssi_df = pd.DataFrame({
                "Tyyppi": ["Menot", "Jäämä" if jaama_preview > 0 else "Alijäämä"],
                "Summa": [menot, abs(jaama_preview)]
            })
            fig_pie = px.pie(balanssi_df, values='Summa', names='Tyyppi', hole=0.4, 
                             color_discrete_sequence=['#ef4444', '#22c55e']) # Punainen / Vihreä
            fig_pie.update_layout(showlegend=False, title_text="Kassavirran rakenne")
            st.plotly_chart(fig_pie, use_container_width=True)

        with g2:
            # 2. Bar chart: Top 5 Kulut
            menot_df = df_laskettu[df_laskettu['Kategoria']=='Meno'].sort_values(by='Euroa_KK', ascending=True).tail(5)
            fig_bar = px.bar(menot_df, x='Euroa_KK', y='Selite', orientation='h', 
                             title="Top 5 Suurimmat kuluerät", text='Euroa_KK')
            fig_bar.update_traces(marker_color='#3b82f6', texttemplate='%{text:.0f}€', textposition='outside')
            fig_bar.update_layout(xaxis_title="Euroa / kk", yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # --- C. SIMULOINTI (UUSI) ---
        st.markdown("### 🔮 Tulevaisuus-simulaattori")
        st.info("Leiki luvuilla: Mitä jos sijoittaisit jäämäsi viisaasti?")
        
        with st.container(border=True):
            sim_c1, sim_c2 = st.columns([1, 2])
            
            with sim_c1:
                # Oletuksena käytetään laskettua jäämää, mutta ei negatiivista
                start_saasto = float(jaama_preview) if jaama_preview > 0 else 50.0
                
                kk_saasto_sim = st.slider("Kuukausisäästö (€)", 0.0, 2000.0, start_saasto, step=10.0)
                vuodet_sim = st.slider("Sijoitusaika (vuotta)", 1, 40, 15)
                tuotto_sim = st.slider("Oletettu vuosituotto (%)", 1.0, 15.0, 7.0)
                alkupotti = st.number_input("Nykyiset sijoitukset (€)", 0, 1000000, 0)
            
            with sim_c2:
                # Lasketaan simulaatio logiikka.py:n funktiolla
                df_sim = logiikka.laske_tulevaisuus(alkupotti, kk_saasto_sim, tuotto_sim, vuodet_sim)
                
                # Piirretään aluegraafi (Area chart)
                fig_sim = px.area(df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"], 
                                  title=f"Salkun arvo {vuodet_sim}v päästä: {df_sim.iloc[-1]['Yhteensä']:,.0f} €",
                                  color_discrete_map={"Oma pääoma": "#94a3b8", "Tuotto": "#22c55e"})
                st.plotly_chart(fig_sim, use_container_width=True)

        st.divider()

        # --- D. TEKOÄLY ANALYYSI ---
        st.header("🤖 Tekoälyn tuomio")
        
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            with c1: ika = st.number_input("Ikä", 15, 100, 30)
            with c2: suhde = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perheellinen", "YH"])
            with c3: lapset = st.number_input("Lapset", 0, 10, 0)
            with c4: data_tyyppi = st.radio("Datan tyyppi", ["Suunnitelma", "Toteuma"])

        analyze_btn = st.button("✨ LUO SYVÄLUOTAAVA ANALYYSI", type="primary", use_container_width=True)

        if analyze_btn:
            with st.spinner('Taskuekonomisti miettii ratkaisuja...'):
                profiili = {"ika": ika, "suhde": suhde, "lapset": lapset}
                
                vastaus, lopullinen_jaama = logiikka.analysoi_talous(df_laskettu, profiili, data_tyyppi)
                logiikka.tallenna_lokiiin(profiili, lopullinen_jaama, data_tyyppi)
                
                st.markdown("### 📝 Toimenpidesuositukset")
                st.markdown(f"""
                <div style="background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    {vastaus}
                </div>
                """, unsafe_allow_html=True)

    else:
        st.error("Virhe: Excelistä ei löytynyt dataa tai rakenne on väärä.")
