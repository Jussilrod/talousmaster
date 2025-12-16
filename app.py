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

# Alustetaan chat-historia muistiin, jos ei ole vielä
if "messages" not in st.session_state:
    st.session_state.messages = []

local_css_path = "style.css"
if os.path.exists(local_css_path):
    with open(local_css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

logiikka.konfiguroi_ai()

# --- SIVUPALKKI ---
with st.sidebar:
    st.title("💎 TaskuEko")
    uploaded_file = st.file_uploader("📂 Lataa Excel", type=['xlsx'])
    st.markdown("---")
    st.info("Tukee nyt useita kuukausia! Täytä Exceliin sarakkeet C, D, E... eri kuukausille.")

# --- PÄÄNÄKYMÄ ---
if not uploaded_file:
    st.markdown("# Tervetuloa TaskuEkonomistiin 👋")
    st.write("Lataa Excel vasemmalta aloittaaksesi.")
else:
    # Ladataan data
    df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_raw.empty:
        # Lasketaan KPI:t (Summataan kaikki kuukaudet ja jaetaan kuukausien määrällä = keskiarvo/kk)
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] = df_avg['Summa'] / kk_lkm # Keskiarvo per kk
        
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        # KPI Metrics
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Analysoitu", f"{kk_lkm} kk")
            c2.metric("Tulot (keskim.)", f"{tulot_avg:,.0f} €")
            c3.metric("Menot (keskim.)", f"{menot_avg:,.0f} €", delta="-")
            c4.metric("Jäämä (keskim.)", f"{jaama_avg:,.0f} €", delta=f"{jaama_avg:,.0f} €")

        # --- NAVIGAATIO ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Yleiskuva", "📈 Trendit", "🔮 Simulaattori", "💬 Chat & Raportti"])

        # TAB 1: YLEISKUVA (Keskiarvot)
        with tab1:
            st.subheader("Keskimääräinen kulurakenne")
            col_1, col_2 = st.columns(2)
            
            with col_1:
                # Sunburst
                menot_df = df_avg[df_avg['Kategoria']=='Meno']
                fig_sun = px.sunburst(menot_df, path=['Kategoria', 'Selite'], values='Summa', color='Summa')
                st.plotly_chart(fig_sun, use_container_width=True)
            
            with col_2:
                # Top Kulut Bar Chart
                top5 = menot_df.sort_values('Summa', ascending=False).head(5)
                fig_bar = px.bar(top5, x='Summa', y='Selite', orientation='h', title="Top 5 Menot (avg/kk)")
                st.plotly_chart(fig_bar, use_container_width=True)

        # TAB 2: TRENDIT (AIKASARJA) - UUSI!
        with tab2:
            st.subheader("Talouden kehitys kuukausittain")
            
            if kk_lkm > 1:
                # 1. Viivagraafi: Tulot vs Menot
                df_trend = df_raw.groupby(['Kuukausi', 'Kategoria'])['Summa'].sum().reset_index()
                
                # Järjestetään kuukaudet (tämä vaatisi oikeasti datetime-logiikkaa, mutta oletetaan excel järjestys)
                # Yksinkertainen visualisointi:
                fig_line = px.line(df_trend, x='Kuukausi', y='Summa', color='Kategoria', markers=True,
                                  title="Tulot ja Menot ajan yli")
                st.plotly_chart(fig_line, use_container_width=True)
                
                st.divider()
                
                # 2. Stacked Bar: Mihin raha meni eri kuukausina?
                valittu_kategoria = st.selectbox("Tarkastele kategoriaa:", ["Meno", "Tulo"])
                df_cat_trend = df_raw[df_raw['Kategoria'] == valittu_kategoria]
                
                fig_stack = px.bar(df_cat_trend, x='Kuukausi', y='Summa', color='Selite', 
                                  title=f"{valittu_kategoria}erien jakautuminen")
                st.plotly_chart(fig_stack, use_container_width=True)
            else:
                st.info("💡 Lataa Excel, jossa on sarakkeita useammalle kuukaudelle (esim. Tammi, Helmi), niin näet trendikäyrät tässä.")

        # TAB 3: SIMULAATTORI (Vanha tuttu)
        with tab3:
            st.subheader("Miljonääri-simulaattori")
            s_col1, s_col2 = st.columns([1,2])
            with s_col1:
                kk_saasto = st.slider("Säästö (€/kk)", 0.0, 2000.0, float(max(jaama_avg, 50.0)), step=10.0)
                vuodet = st.slider("Vuodet", 1, 40, 20)
                korko = st.slider("Tuotto %", 1.0, 15.0, 7.0)
            with s_col2:
                df_sim = logiikka.laske_tulevaisuus(0, kk_saasto, korko, vuodet)
                fig_area = px.area(df_sim, x="Vuosi", y="Yhteensä", title=f"Potti: {df_sim.iloc[-1]['Yhteensä']:,.0f} €")
                st.plotly_chart(fig_area, use_container_width=True)

        # TAB 4: CHAT & RAPORTTI - UUSI!
        with tab4:
            c_left, c_right = st.columns([2, 1])
            
            # CHAT
            with c_left:
                st.subheader("💬 Kysy dataltasi")
                
                # Näytä historia
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                # Input
                if prompt := st.chat_input("Esim: 'Mihin käytin eniten rahaa tammikuussa?'"):
                    # 1. Käyttäjän viesti
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    # 2. AI vastaus
                    with st.chat_message("assistant"):
                        with st.spinner("Tutkin Exceliä..."):
                            response_text = logiikka.chat_with_data(df_raw, prompt, st.session_state.messages)
                            st.markdown(response_text)
                            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # RAPORTTI
            with c_right:
                st.subheader("📄 Lataa raportti")
                with st.container(border=True):
                    st.write("Luo virallinen yhteenveto pankkia tai arkistointia varten.")
                    
                    # Pienet inputit raporttia varten
                    r_ika = st.number_input("Ikä", 18, 100, 30, key="r_ika")
                    r_status = st.selectbox("Status", ["Yksin", "Perhe"], key="r_stat")
                    
                    if st.button("Luo PDF-analyysi"):
                        profiili = {"ika": r_ika, "suhde": r_status}
                        analyysi_txt, _ = logiikka.analysoi_talous(df_raw, profiili, "Raportti")
                        
                        pdf_data = logiikka.luo_pdf_raportti(df_avg, analyysi_txt, profiili)
                        
                        st.download_button(
                            label="⬇️ Lataa PDF",
                            data=pdf_data,
                            file_name="taskuekonomisti_raportti.pdf",
                            mime="application/pdf",
                            type="primary"
                        )

    else:
        st.error("Datan luku epäonnistui. Tarkista Excel.")
