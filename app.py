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

# Määritellään pohjatiedoston nimi
EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx"

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
    
    # 1. POHJAN LATAUS (UUSI)
    # Tarkistetaan onko pohjatiedosto olemassa palvelimella
    if os.path.exists(EXCEL_TEMPLATE_NAME):
        with open(EXCEL_TEMPLATE_NAME, "rb") as file:
            st.download_button(
                label="📥 Lataa tyhjä Excel-pohja",
                data=file,
                file_name="talous_tyokalu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        st.markdown("---")
    
    # 2. OMAN TIEDOSTON LATAUS
    uploaded_file = st.file_uploader("📂 Lataa täytetty Excel", type=['xlsx'])
    
    st.markdown("---")
    
    # 3. TIETOTURVA (PÄIVITETTY)
    with st.expander("🔒 Tietoturva & Yksityisyys", expanded=False):
        st.markdown("""
        <small style="color: #ef4444;">
        ⚠️ **Suositus:** Älä syötä Exceliin henkilötietojasi tai tilinumeroita. Data käsitellään anonyymisti.
        </small>
        
        ---
        
        **1. SSL-salaus:**
        Yhteys tähän sovellukseen on suojattu (HTTPS/SSL), mikä tarkoittaa, että verkkoliikenne sinun ja palvelimen välillä on salattua.
        
        **2. Ei tallennusta:**
        Lataamasi Excel käsitellään vain väliaikaisessa muistissa (RAM) istunnon ajan. Tiedostoa ei tallenneta tietokantaan.
        
        **3. Tietojen minimointi:**
        Sovellus ei lisää tai kerää henkilötietoja. Tekoäly näkee vain Excelissä olevat luvut ja tekstit.
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
            <p><strong>1. Lataa tyhjä pohja sivupalkista.</strong><br>
            <strong>2. Täytä tietosi.</strong><br>
            <strong>3. Lataa täytetty tiedosto takaisin.</strong></p>
        </div>
        <br>
        """, unsafe_allow_html=True)

        video_path = "esittely.mp4"
        if os.path.exists(video_path):
            st.video(video_path, autoplay=True, muted=True)
        else:
            st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4", autoplay=True, muted=True)

# 2. TILANNE: TIEDOSTO LADATTU (DASHBOARD)
else:
    df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_raw.empty:
        # Lasketaan keskiarvot per kuukausi
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] = df_avg['Summa'] / kk_lkm 
        
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        # KPI MITTARIT
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Analysoitu", f"{kk_lkm} kk data")
            c2.metric("Tulot (kk)", f"{tulot_avg:,.0f} €")
            c3.metric("Menot (kk)", f"{menot_avg:,.0f} €", delta="-")
            c4.metric("Jäämä (kk)", f"{jaama_avg:,.0f} €", delta=f"{jaama_avg:,.0f} €")

        st.write("") 

        # VÄLILEHDET
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Yleiskuva", 
            "📈 Trendit", 
            "🔮 Miljonääri-simulaattori", 
            "💬 Chat", 
            "📝 Analyysi"
        ])

        # TAB 1: YLEISKUVA
        with tab1:
            r1, r2 = st.columns(2)
            with r1:
                st.subheader("Menojen rakenne")
                fig_sun = px.sunburst(df_avg[df_avg['Kategoria']=='Meno'], path=['Kategoria', 'Selite'], values='Summa', color='Summa', color_continuous_scale='RdBu_r')
                st.plotly_chart(fig_sun, use_container_width=True)
            with r2:
                st.subheader("Top 5 Kulut")
                top5 = df_avg[df_avg['Kategoria']=='Meno'].sort_values('Summa', ascending=False).head(5)
                fig_bar = px.bar(top5, x='Summa', y='Selite', orientation='h', text_auto='.0f')
                fig_bar.update_traces(marker_color='#ef4444')
                st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()
            st.subheader("💧 Kassavirta")
            
            menot_sorted = df_avg[df_avg['Kategoria']=='Meno'].sort_values(by='Summa', ascending=False)
            TOP_N = 6
            if len(menot_sorted) > TOP_N:
                top_m = menot_sorted.iloc[:TOP_N]
                muut_m = menot_sorted.iloc[TOP_N:]['Summa'].sum()
                labels = ["Tulot"] + top_m['Selite'].tolist() + ["Muut menot", "JÄÄMÄ"]
                values = [tulot_avg] + [x * -1 for x in top_m['Summa'].tolist()] + [muut_m * -1, 0]
                measure = ["absolute"] + ["relative"] * (len(top_m) + 1) + ["total"]
            else:
                labels = ["Tulot"] + menot_sorted['Selite'].tolist() + ["JÄÄMÄ"]
                values = [tulot_avg] + [x * -1 for x in menot_sorted['Summa'].tolist()] + [0]
                measure = ["absolute"] + ["relative"] * len(menot_sorted) + ["total"]

            fig_water = go.Figure(go.Waterfall(
                name="Kassavirta", orientation="v", measure=measure, x=labels, y=values,
                text=[f"{v:,.0f}" for v in values[:-1]] + [f"{jaama_avg:,.0f}"],
                textposition="outside",
                connector={"line":{"color":"#333"}}, decreasing={"marker":{"color":"#ef4444"}},
                increasing={"marker":{"color":"#22c55e"}}, totals={"marker":{"color":"#3b82f6"}}
            ))
            st.plotly_chart(fig_water, use_container_width=True)

        # TAB 2: TRENDIT
        with tab2:
            st.subheader("Kehitys kuukausittain")
            if kk_lkm > 1:
                df_trend = df_raw.groupby(['Kuukausi', 'Kategoria'])['Summa'].sum().reset_index()
                st.plotly_chart(px.line(df_trend, x='Kuukausi', y='Summa', color='Kategoria', markers=True), use_container_width=True)
            else:
                st.warning("Trendit vaativat dataa useammalta kuukaudelta. Täytä Exceliin sarakkeet esim: Tammikuu, Helmikuu...")

        # TAB 3: SIMULAATTORI
        with tab3:
            st.subheader("🔮 Miljonääri-simulaattori")
            st.caption("Visualisoi korkoa korolle -ilmiön voima. Vihreä alue kuvaa sijoitusten tuottoa.")
            
            c_sim1, c_sim2 = st.columns([1,2])
            with c_sim1:
                oletus_saasto = float(max(jaama_avg, 50.0))
                kk_saasto = st.slider("Kuukausisäästö (€)", 0.0, 3000.0, oletus_saasto, step=10.0)
                vuodet = st.slider("Sijoitusaika (v)", 1, 40, 20)
                korko = st.slider("Tuotto %", 1.0, 15.0, 7.0)
                alkupotti = st.number_input("Alkupääoma (€)", 0, 1000000, 0, step=1000)
            
            with c_sim2:
                df_sim = logiikka.laske_tulevaisuus(alkupotti, kk_saasto, korko, vuodet)
                
                loppusumma = df_sim.iloc[-1]['Yhteensä']
                loppu_tuotto = df_sim.iloc[-1]['Tuotto']
                st.metric(f"Salkun arvo {vuodet}v päästä", f"{loppusumma:,.0f} €", delta=f"Tuottoa: {loppu_tuotto:,.0f} €")
                
                # Pinottu aluekaavio
                fig_area = px.area(
                    df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"],
                    color_discrete_map={"Oma pääoma": "#94a3b8", "Tuotto": "#22c55e"}
                )
                fig_area.update_layout(hovermode="x unified", yaxis_title="Euroa (€)")
                st.plotly_chart(fig_area, use_container_width=True)

        # TAB 4: CHAT
        with tab4:
            st.subheader("💬 Kysy datalta")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            if prompt := st.chat_input("Kysy taloudestasi..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Hetki..."):
                        resp = logiikka.chat_with_data(df_raw, prompt, st.session_state.messages)
                        st.markdown(resp)
                        st.session_state.messages.append({"role": "assistant", "content": resp})

        # TAB 5: ANALYYSI
        with tab5:
            st.subheader("📝 Henkilökohtainen varainhoitosuunnitelma")
            
            with st.container(border=True):
                with st.form("analyysi_form"):
                    st.markdown("**1. Perustiedot**")
                    c_a1, c_a2 = st.columns(2)
                    with c_a1:
                        ika = st.number_input("Oma ikäsi", 18, 99, 30)
                        lapset = st.number_input("Lasten määrä taloudessa", 0, 10, 0)
                    with c_a2:
                        status = st.selectbox("Elämäntilanne", ["Sinkku", "Parisuhteessa (yhteistalous)", "Parisuhteessa (erilliset)", "Lapsiperhe", "Yksinhuoltaja"], index=0)
                        data_tyyppi = st.radio("Datan lähde", ["Toteuma (Tiliote)", "Suunnitelma (Budjetti)"])
                    
                    st.markdown("---")
                    st.markdown("**2. Tavoitteet**")
                    tavoite = st.selectbox("Mikä on tärkein tavoitteesi?", ["Puskurin kerryttäminen", "Asunnon osto", "Velattomuus", "FIRE (Riippumattomuus)", "Elintason nosto", "Sijoitusten kasvatus"])
                    varallisuus = st.number_input("Nettovarallisuus (€)", value=10000, step=1000, help="Omaisuus - Velat")
                    
                    st.write("")
                    submit_btn = st.form_submit_button("✨ Pyydä Varainhoitajan Analyysi", type="primary", use_container_width=True)
            
            if submit_btn:
                with st.spinner("Tekoäly laatii strategiaa..."):
                    profiili = {"ika": ika, "suhde": status, "lapset": lapset, "tavoite": tavoite, "varallisuus": varallisuus}
                    analyysi_teksti = logiikka.analysoi_talous(df_avg, profiili, data_tyyppi)
                    
                    st.markdown("---")
                    st.markdown(f"""<div style="background-color:#f8fafc; padding:30px; border-radius:12px; border:1px solid #e2e8f0;">{analyysi_teksti}</div>""", unsafe_allow_html=True)
    else:
        st.error("Virhe datan luvussa.")

