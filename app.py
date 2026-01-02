import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

# --- ASETUKSET ---
st.set_page_config(page_title="TaskuEkonomisti 2.0", page_icon="💎", layout="wide")

# Alustetaan Session State (muisti) hyppimisen estämiseksi
if "messages" not in st.session_state: st.session_state.messages = []
if "varallisuus_tavoite" not in st.session_state: st.session_state.varallisuus_tavoite = 50000.0

# Määritellään pohjatiedoston nimi
EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx"

# Alustetaan chat-historia
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- CSS ---
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

logiikka.konfiguroi_ai()

# --- SIVUPALKKI ---
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
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] /= kk_lkm
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        # KPI KORTIT
        c1, c2, c3, c4 = st.columns(4)
        m = [("Analysoitu", f"{kk_lkm} kk"), ("Tulot (kk)", f"{tulot_avg:,.0f}€"), ("Menot (kk)", f"{menot_avg:,.0f}€"), ("Jäämä (kk)", f"{jaama_avg:,.0f}€")]
        for i, col in enumerate([c1, c2, c3, c4]):
            col.markdown(f'<div class="kpi-card"><div class="kpi-label">{m[i][0]}</div><div class="kpi-value">{m[i][1]}</div></div>', unsafe_allow_html=True)

        st.write("")

        # --- VÄLILEHDET ---
        # ... (alkuosa ennallaan KPI-kortteihin asti) ...

        # --- VÄLILEHDET ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Yleiskuva", 
            "📈 Trendit", 
            "🔮 Simulaattori", 
            "💬 Chat", 
            "📝 Analyysi"
        ])

        with tab1:
            r1, r2 = st.columns(2)
            with r1:
                st.subheader("Menojen rakenne")
                fig_sun = px.sunburst(df_avg[df_avg['Kategoria']=='Meno'], path=['Kategoria', 'Selite'], values='Summa', color='Summa', color_continuous_scale='RdBu_r')
                st.plotly_chart(fig_sun, width='stretch')
            with r2:
                st.subheader("Top 5 Kulut")
                top5 = df_avg[df_avg['Kategoria']=='Meno'].sort_values('Summa', ascending=False).head(5)
                fig_bar = px.bar(top5, x='Summa', y='Selite', orientation='h', text_auto='.0f')
                fig_bar.update_traces(marker_color='#ef4444')
                st.plotly_chart(fig_bar, width='stretch')

            st.divider()
            st.subheader("💧 Kassavirta")
            menot_sorted = df_avg[df_avg['Kategoria']=='Meno'].sort_values(by='Summa', ascending=False)
            labels = ["Tulot"] + menot_sorted['Selite'].tolist() + ["JÄÄMÄ"]
            values = [tulot_avg] + [x * -1 for x in menot_sorted['Summa'].tolist()] + [0]
            measure = ["absolute"] + ["relative"] * len(menot_sorted) + ["total"]

            fig_water = go.Figure(go.Waterfall(
                orientation="v", measure=measure, x=labels, y=values,
                text=[f"{v:,.0f}" for v in values[:-1]] + [f"{jaama_avg:,.0f}"],
                textposition="outside",
                connector={"line":{"color":"#333"}}, decreasing={"marker":{"color":"#ef4444"}},
                increasing={"marker":{"color":"#22c55e"}}, totals={"marker":{"color":"#3b82f6"}}
            ))
            st.plotly_chart(fig_water, width='stretch')

        with tab2:
            
          
            st.subheader("Rahan virtausanalyysi")
            st.plotly_chart(logiikka.luo_sankey(tulot_avg, df_avg[df_avg['Kategoria']=='Meno'], jaama_avg), width='stretch')           
            
            st.divider()
           
            st.subheader("Kehitys kuukausittain")
            if kk_lkm > 1:
                # 1. Määritellään kalenterijärjestys tiedostosi perusteella
                kuukaudet_oikein = [
                    'Tammi', 'Helmi', 'Maalis', 'Huhti', 'Touko', 'Kesä', 
                    'Heinä', 'Elo', 'Syys', 'Loka', 'Marras', 'Joulu'
                ]
                
                # 2. Ryhmitellään data
                df_trend = df_raw.groupby(['Kuukausi', 'Kategoria'])['Summa'].sum().reset_index()
                
                # 3. Piirretään kuvaaja ja pakotetaan X-akselin järjestys
                fig_trend = px.line(
                    df_trend, 
                    x='Kuukausi', 
                    y='Summa', 
                    color='Kategoria', 
                    markers=True,
                    category_orders={"Kuukausi": kuukaudet_oikein} # TÄMÄ pakottaa oikean järjestyksen
                )
                
                # 4. Päivitetään ulkoasu ja näytetään
                fig_trend.update_layout(xaxis_title="Kuukausi", yaxis_title="Summa (€)")
                st.plotly_chart(fig_trend, width='stretch')
            else:
                st.warning("Trendit vaativat dataa useammalta kuukaudelta (esim. Tammi, Helmi...).")

        

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


        with tab4:
            st.subheader("💬 Kysy taloudestasi")
            chat_cont = st.container()
            st.caption("Pikatoiminnot:")
            p1, p2, p3 = st.columns(3)
            p_input = None
            if p1.button("📊 Kuluanalyysi", width='stretch', key="q_kulu"): p_input = "Analysoi kulujani."
            if p2.button("🔮 Simuloi +50€", width='stretch', key="q_sim"): p_input = "Miten 50€ lisäsäästö vaikuttaa?"
            if p3.button("📝 Säästösuunnitelma", width='stretch', key="q_plan"): p_input = "Luo säästösuunnitelma."

            with chat_cont:
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            chat_in = st.chat_input("Kirjoita kysymys...")
            actual_input = chat_in or p_input
            if actual_input:
                st.session_state.messages.append({"role": "user", "content": actual_input})
                with chat_cont:
                    with st.chat_message("user"): st.markdown(actual_input)
                    with st.chat_message("assistant"):
                        resp = logiikka.chat_with_data(df_raw, actual_input, st.session_state.messages)
                        st.markdown(resp)
                        st.session_state.messages.append({"role": "assistant", "content": resp})

        with tab5:
            with st.form("analyysi_form"):
                st.markdown("### 📝 Varainhoitajan analyysi")
                c_a1, c_a2 = st.columns(2)
                with c_a1:
                    ika = st.number_input("Ikä", 18, 99, 30, key="f_ika")
                    lapset = st.number_input("Lapset", 0, 10, 0, key="f_lapset")
                with c_a2:
                    status = st.selectbox("Tilanne", ["Sinkku", "Perhe", "Yhteistalous"], key="f_status")
                    varallisuus = st.number_input("Nykyinen varallisuus (€)", value=10000.0, key="f_varat")
                tavoite_nimi = st.selectbox("Tavoite", ["Asunnon osto", "FIRE", "Puskuri"], key="f_tavoite")
                tavoite_summa = st.number_input("Tavoitesumma (€)", value=50000.0, key="f_summa")
                submit = st.form_submit_button("✨ Aja AI-Analyysi", type="primary")

            if submit:
                with st.spinner("AI analysoi..."):
                    prof = {"ika": ika, "suhde": status, "lapset": lapset, "tavoite": tavoite_nimi, "varallisuus": varallisuus}
                    res = logiikka.analysoi_talous(df_avg, prof, "Toteuma")
                    st.divider()
                    st.markdown(f'<div style="background-color: white; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0; color: black;">{res}</div>', unsafe_allow_html=True)
    else:
        st.error("Datan luku epäonnistui.")













