import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

st.set_page_config(page_title="TaskuEkonomisti", page_icon="💎", layout="wide")

# --- 1. ALUSTA MUISTI (Session State) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "tavoite_nimi" not in st.session_state: st.session_state.tavoite_nimi = "Asunnon osto"
if "varallisuus" not in st.session_state: st.session_state.varallisuus = 10000
if "tavoite_summa" not in st.session_state: st.session_state.tavoite_summa = 50000

# CSS Lataus
if os.path.exists("style.css"):
    with open("style.css") as f: st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

logiikka.konfiguroi_ai()

# --- 2. SIVUPALKKI ---
with st.sidebar:
    st.title("💎 Valikko")
    if os.path.exists("talous_pohja.xlsx"):
        with open("talous_pohja.xlsx", "rb") as f:
            st.download_button("📥 Lataa tyhjä Excel-pohja", f, file_name="talous_tyokalu.xlsx", use_container_width=True)
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 Lataa täytetty Excel", type=['xlsx'])
    st.markdown("---")
    with st.expander("🔒 Tietoturva"):
        st.write("Dataasi ei tallenneta palvelimelle.")

# --- 3. OTSIKKO ---
st.markdown('<div style="text-align:center;"><h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1><p class="slogan">Ota taloutesi hallintaan datalla ja tekoälyllä</p></div>', unsafe_allow_html=True)

# --- 4. LASKEUTUMISSIVU (PALAUTETTU ALKUPERÄINEN) ---
if not uploaded_file:
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0;">
            <h3>👋 Tervetuloa!</h3>
            <p>Tämä työkalu auttaa sinua ymmärtämään rahavirtojasi, ennustamaan vaurastumista ja löytämään säästökohteita tekoälyn avulla.</p>
            <p><strong>1. Lataa tyhjä pohja sivupalkista.</strong><br>
            <strong>2. Täytä tietosi.</strong><br>
            <strong>3. Lataa täytetty tiedosto takaisin.</strong></p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        if os.path.exists("esittely.mp4"):
            st.video("esittely.mp4")
        else:
            st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4")

# --- 5. DASHBOARD ---
else:
    df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
    if not df_raw.empty:
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] /= kk_lkm
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        # KPI KORTIT
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Analysoitu</div><div class="kpi-value">{kk_lkm} kk</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Tulot (kk)</div><div class="kpi-value">{tulot_avg:,.0f} €</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Menot (kk)</div><div class="kpi-value">{menot_avg:,.0f} €</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Jäämä (kk)</div><div class="kpi-value">{jaama_avg:,.0f} €</div></div>', unsafe_allow_html=True)

        st.write("")

        # TAVOITTEEN SEURANTA
        prog = min(st.session_state.varallisuus / st.session_state.tavoite_summa, 1.0)
        with st.container(border=True):
            st.markdown(f"### 🎯 Tavoite: {st.session_state.tavoite_nimi}")
            cp1, cp2 = st.columns([4, 1])
            cp1.progress(prog)
            cp2.write(f"**{prog*100:.1f}%**")

        # VÄLILEHDET
        tabs = st.tabs(["📊 Yleiskuva", "🌊 Virtaus", "🔮 Simulaattori", "💬 Chat", "📝 Suunnitelma"])
        
        with tabs[0]: # Yleiskuva
            r1, r2 = st.columns(2)
            r1.plotly_chart(px.sunburst(df_avg[df_avg['Kategoria']=='Meno'], path=['Selite'], values='Summa', title="Menoerät"), use_container_width=True)
            r2.plotly_chart(px.bar(df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa'), x='Summa', y='Selite', orientation='h', title="Top 5 Kulut"), use_container_width=True)

        with tabs[1]: # Virtaus (Sankey)
            st.plotly_chart(logiikka.luo_sankey_kaavio(tulot_avg, df_avg[df_avg['Kategoria']=='Meno'], jaama_avg), use_container_width=True)

        with tabs[2]: # Simulaattori
            c_s1, c_s2 = st.columns([1, 2])
            with c_s1:
                kk_s = st.slider("KK-säästö (€)", 0, 3000, int(max(0, jaama_avg)))
                vuo = st.slider("Vuodet", 1, 40, 20)
            with c_s2:
                df_sim = logiikka.laske_tulevaisuus(st.session_state.varallisuus, kk_s, 7.0, vuo)
                st.plotly_chart(px.area(df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"], title="Varallisuuden kasvu"), use_container_width=True)

        with tabs[3]: # Chat
            st.write("💡 **Pikavalinnat:**")
            p1, p2, p3 = st.columns(3)
            chat_p = None
            if p1.button("Mihin rahani menivät?", use_container_width=True): chat_p = "Mihin rahani menivät?"
            if p2.button("Säästövinkkejä", use_container_width=True): chat_p = "Anna säästövinkkejä."
            if p3.button("Simuloi +100€", use_container_width=True): chat_p = "Miten 100€ lisäsäästö vaikuttaa?"
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if prompt := (st.chat_input("Kysy...") or chat_p):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant"):
                    r = logiikka.chat_with_data(df_raw, prompt, st.session_state.messages)
                    st.markdown(r)
                    st.session_state.messages.append({"role": "assistant", "content": r})

        with tabs[4]: # Suunnitelma
            with st.form("goal_form"):
                st.session_state.tavoite_nimi = st.selectbox("Tavoite", ["Asunnon osto", "Puskuri", "FIRE"], index=0)
                st.session_state.tavoite_summa = st.number_input("Tavoitesumma (€)", value=st.session_state.tavoite_summa)
                st.session_state.varallisuus = st.number_input("Nettovarallisuus (€)", value=st.session_state.varallisuus)
                if st.form_submit_button("Luo AI-Analyysi"):
                    prof = {"ika": 30, "tavoite": st.session_state.tavoite_nimi, "varallisuus": st.session_state.varallisuus}
                    st.markdown(logiikka.analysoi_talous(df_avg, prof, "Toteuma"))
    else:
        st.error("Datan lukeminen epäonnistui.")
