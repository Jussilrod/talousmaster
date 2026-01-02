import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

# --- ASETUKSET ---
st.set_page_config(page_title="TaskuEkonomisti 2.0", page_icon="💎", layout="wide")

# Alustetaan Session State tavoitteille ja chatille
if "messages" not in st.session_state: st.session_state.messages = []
if "varallisuus_tavoite" not in st.session_state: st.session_state.varallisuus_tavoite = 50000.0

# --- CSS ---
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

logiikka.konfiguroi_ai()

# --- SIVUPALKKI ---
with st.sidebar:
    st.title("💎 Valikko")
    if os.path.exists("talous_pohja.xlsx"):
        with open("talous_pohja.xlsx", "rb") as file:
            st.download_button(label="📥 Lataa tyhjä Excel-pohja", data=file, file_name="talous_tyokalu.xlsx", use_container_width=True)
    uploaded_file = st.file_uploader("📂 Lataa täytetty Excel", type=['xlsx'])
    st.markdown("---")
    with st.expander("🔒 Tietoturva"):
        st.caption("Data käsitellään vain väliaikaisessa muistissa.")

# --- OTSIKKO ---
st.markdown('<div style="text-align: center;"><h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1><p class="slogan">Ota taloutesi hallintaan datalla ja tekoälyllä</p></div>', unsafe_allow_html=True)

if not uploaded_file:
    # Laskeutumissivu pysyy ennallaan
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div style="text-align: center; background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;"><h3>👋 Tervetuloa!</h3><p>Lataa pohja, täytä tiedot ja palauta se tähän.</p></div><br>', unsafe_allow_html=True)
        st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4")
else:
    df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
    if not df_raw.empty:
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] /= kk_lkm
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        # --- KPI KORTIT (Glassmorphism) ---
        c1, c2, c3, c4 = st.columns(4)
        metrics = [("Analysoitu", f"{kk_lkm} kk"), ("Tulot (kk)", f"{tulot_avg:,.0f}€"), ("Menot (kk)", f"{menot_avg:,.0f}€"), ("Jäämä (kk)", f"{jaama_avg:,.0f}€")]
        for i, col in enumerate([c1, c2, c3, c4]):
            col.markdown(f'<div class="kpi-card"><div class="kpi-label">{metrics[i][0]}</div><div class="kpi-value">{metrics[i][1]}</div></div>', unsafe_allow_html=True)

        st.write("")

       # --- VÄLILEHDET ---
        # Poistettu "Virtaus"-välilehti, pidetään alkuperäiset 5
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Yleiskuva", 
            "📈 Trendit", 
            "🔮 Simulaattori", 
            "💬 Chat", 
            "📝 Analyysi"
        ])

        with tab1:
            st.subheader("Talouden kokonaiskuva")
            # TÄSSÄ: Sankey korvaa Sunburstin
            st.plotly_chart(logiikka.luo_sankey(tulot_avg, df_avg[df_avg['Kategoria']=='Meno'], jaama_avg), use_container_width=True)
            
            st.divider()
            
            # Pidetään Top 5 kulut rinnakkain, jos haluat
            st.subheader("Suurimmat menoerät")
            top5 = df_avg[df_avg['Kategoria']=='Meno'].sort_values('Summa', ascending=False).head(5)
            fig_bar = px.bar(top5, x='Summa', y='Selite', orientation='h', text_auto='.0f')
            fig_bar.update_traces(marker_color='#ef4444')
            st.plotly_chart(fig_bar, use_container_width=True)

        with tab2: # Trendit pysyvät ennallaan
            if kk_lkm > 1:
                df_trend = df_raw.groupby(['Kuukausi', 'Kategoria'])['Summa'].sum().reset_index()
                st.plotly_chart(px.line(df_trend, x='Kuukausi', y='Summa', color='Kategoria', markers=True), use_container_width=True)
            else:
                st.warning("Trendit vaativat dataa useammalta kuukaudelta.")

        with tab3:
            st.subheader("🔮 Miljonääri-simulaattori")
            cs1, cs2 = st.columns([1,2])
            with cs1:
                kk_saasto = st.slider("Kuukausisäästö (€)", 0.0, 3000.0, float(max(jaama_avg, 0)))
                vuodet = st.slider("Aika (v)", 1, 40, 20)
                korko = st.slider("Tuotto %", 1.0, 15.0, 7.0)
            with cs2:
                df_sim = logiikka.laske_tulevaisuus(0, kk_saasto, korko, vuodet)
                st.plotly_chart(px.area(df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"], color_discrete_map={"Oma pääoma": "#94a3b8", "Tuotto": "#22c55e"}), use_container_width=True)

        with tab4:
            st.subheader("💬 Kysy taloudestasi")
            # Pikavalinnat
            st.write("Pikatoiminnot:")
            p1, p2, p3 = st.columns(3)
            p_input = None
            if p1.button("Mihin rahani menivät?", use_container_width=True): p_input = "Analysoi suurimmat kulueryhmäni."
            if p2.button("Simuloi +50€ säästö", use_container_width=True): p_input = "Miten 50€ lisäsäästö vaikuttaa 20 vuodessa?"
            if p3.button("Luo säästösuunnitelma", use_container_width=True): p_input = "Luo minulle säästösuunnitelma."

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            chat_in = st.chat_input("Kirjoita kysymys...")
            actual_input = chat_in or p_input
            if actual_input:
                st.session_state.messages.append({"role": "user", "content": actual_input})
                with st.chat_message("user"): st.markdown(actual_input)
                with st.chat_message("assistant"):
                    resp = logiikka.chat_with_data(df_raw, actual_input, st.session_state.messages)
                    st.markdown(resp)
                    st.session_state.messages.append({"role": "assistant", "content": resp})

        with tab5:
            with st.form("analyysi_form"):
                c_a1, c_a2 = st.columns(2)
                ika = c_a1.number_input("Ikä", 18, 99, 30)
                lapset = c_a1.number_input("Lapset", 0, 10, 0)
                status = c_a2.selectbox("Tilanne", ["Sinkku", "Perhe", "Yhteistalous"])
                varallisuus = c_a2.number_input("Nykyinen varallisuus (€)", value=10000.0)
                tavoite_nimi = st.selectbox("Tavoite", ["Asunnon osto", "FIRE", "Puskuri"])
                st.session_state.varallisuus_tavoite = st.number_input("Tavoitesumma (€)", value=50000.0)
                submit = st.form_submit_button("✨ Aja AI-Analyysi", type="primary", use_container_width=True)
            
            # Tavoitemittari aina näkyvissä analyysivälilehdellä
            st.divider()
            prog = min(varallisuus / st.session_state.varallisuus_tavoite, 1.0)
            st.write(f"**Edistyminen kohti tavoitetta ({tavoite_nimi}):**")
            st.progress(prog)
            st.caption(f"{varallisuus:,.0f}€ / {st.session_state.varallisuus_tavoite:,.0f}€ ({prog*100:.1f}%)")

            if submit:
                prof = {"ika": ika, "suhde": status, "lapset": lapset, "tavoite": tavoite_nimi, "varallisuus": varallisuus}
                res = logiikka.analysoi_talous(df_avg, prof, "Toteuma")
                st.markdown(f'<div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0;">{res}</div>', unsafe_allow_html=True)

