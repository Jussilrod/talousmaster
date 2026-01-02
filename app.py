import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

st.set_page_config(page_title="TaskuEkonomisti 2.0", page_icon="💎", layout="wide")

# --- ALUSTUS ---
if "messages" not in st.session_state: st.session_state.messages = []
if "tavoite_nimi" not in st.session_state: st.session_state.tavoite_nimi = "Säästötavoite"
if "varallisuus" not in st.session_state: st.session_state.varallisuus = 10000
if "tavoite_summa" not in st.session_state: st.session_state.tavoite_summa = 50000

# CSS Lataus
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

logiikka.konfiguroi_ai()

# --- SIVUPALKKI ---
with st.sidebar:
    st.title("💎 Valikko")
    if os.path.exists("talous_pohja.xlsx"):
        with open("talous_pohja.xlsx", "rb") as f:
            st.download_button("📥 Lataa tyhjä Excel", f, file_name="pohja.xlsx", use_container_width=True)
    uploaded_file = st.file_uploader("📂 Lataa täytetty Excel", type=['xlsx'])

# --- OTSIKKO ---
st.markdown('<div style="text-align:center;"><h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1><p class="slogan">Datalla kohti vaurautta</p></div>', unsafe_allow_html=True)

if not uploaded_file:
    st.info("Lataa Excel-tiedosto sivupalkista aloittaaksesi.")
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
        cards = [
            ("Data", f"{kk_lkm} kk", "📈"),
            ("Tulot", f"{tulot_avg:,.0f} €", "💰"),
            ("Menot", f"{menot_avg:,.0f} €", "📉"),
            ("Jäämä", f"{jaama_avg:,.0f} €", "💎")
        ]
        for i, (label, val, icon) in enumerate(cards):
            with [c1, c2, c3, c4][i]:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">{icon} {label}</div><div class="kpi-value">{val}</div></div>', unsafe_allow_html=True)

        # --- TAVOITTEEN SEURANTA ---
        progress = min(st.session_state.varallisuus / st.session_state.tavoite_summa, 1.0)
        with st.container(border=True):
            st.markdown(f"### 🎯 Tavoite: {st.session_state.tavoite_nimi}")
            cp1, cp2 = st.columns([4, 1])
            cp1.progress(progress)
            cp2.markdown(f"**{progress*100:.1f}%**")
            st.caption(f"Nykyinen varallisuus {st.session_state.varallisuus:,.0f}€ / Tavoite {st.session_state.tavoite_summa:,.0f}€")

        # --- VÄLILEHDET ---
        tabs = st.tabs(["📊 Yleiskuva", "🌊 Virtaus", "🔮 Simulaattori", "💬 Chat", "📝 Suunnitelma"])
        
        with tabs[0]: # Yleiskuva
            col1, col2 = st.columns(2)
            col1.plotly_chart(px.sunburst(df_avg[df_avg['Kategoria']=='Meno'], path=['Selite'], values='Summa', title="Menot"), use_container_width=True)
            col2.plotly_chart(px.bar(df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa'), x='Summa', y='Selite', orientation='h', title="Top 5 Kulut"), use_container_width=True)

        with tabs[1]: # Sankey
            st.plotly_chart(logiikka.luo_sankey_kaavio(tulot_avg, df_avg[df_avg['Kategoria']=='Meno'], jaama_avg), use_container_width=True)

        with tabs[2]: # Simulaattori
            c_s1, c_s2 = st.columns([1, 2])
            with c_s1:
                kk_s = st.slider("KK-säästö (€)", 0, 2000, int(max(0, jaama_avg)))
                vuo = st.slider("Vuodet", 1, 40, 15)
            with c_s2:
                df_sim = logiikka.laske_tulevaisuus(st.session_state.varallisuus, kk_s, 7.0, vuo)
                st.plotly_chart(px.area(df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"], title="Varallisuuden kasvu"), use_container_width=True)

        with tabs[3]: # Chat
            st.write("💡 **Pikavalinnat:**")
            p_c1, p_c2, p_c3 = st.columns(3)
            q = None
            if p_c1.button("Mihin rahani menevät?", use_container_width=True): q = "Mihin rahani menevät?"
            if p_c2.button("Säästövinkkejä", use_container_width=True): q = "Anna 3 säästövinkkiä."
            if p_c3.button("Simuloi +100€", use_container_width=True): q = "Miten 100€ lisäsäästö vaikuttaa?"
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if user_input := (st.chat_input("Kysy taloudestasi...") or q):
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.rerun() # Päivittää chatin heti

        with tabs[4]: # Suunnitelma
            with st.form("set_goals"):
                st.session_state.tavoite_nimi = st.selectbox("Tavoite", ["Asunnon osto", "FIRE", "Puskuri", "Sijoitukset"])
                st.session_state.tavoite_summa = st.number_input("Tavoitesumma (€)", value=st.session_state.tavoite_summa)
                st.session_state.varallisuus = st.number_input("Nykyinen varallisuus (€)", value=st.session_state.varallisuus)
                if st.form_submit_button("Päivitä tiedot ja pyydä analyysi"):
                    with st.spinner("AI analysoi..."):
                        prof = {"ika": 30, "suhde": "Sinkku", "tavoite": st.session_state.tavoite_nimi, "varallisuus": st.session_state.varallisuus}
                        st.markdown(logiikka.analysoi_talous(df_avg, prof, "Toteuma"))
                    st.rerun()
