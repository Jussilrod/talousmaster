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

# Chat-historia
if "messages" not in st.session_state:
    st.session_state.messages = []

# CSS
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
    st.caption("Täytä Exceliin kuukausisarakkeet (esim. Tammikuu, Helmikuu), niin näet trendit.")

# --- PÄÄNÄKYMÄ ---
if not uploaded_file:
    st.markdown("# Tervetuloa TaskuEkonomistiin 👋")
    st.info("Aloita lataamalla Excel-tiedosto vasemmalta.")
else:
    # 1. DATAN LATAUS
    df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_raw.empty:
        # Lasketaan keskiarvot per kuukausi (Summary data)
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] = df_avg['Summa'] / kk_lkm 
        
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        # 2. KPI MITTARIT
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Data", f"{kk_lkm} kk keskiarvo")
            c2.metric("Tulot", f"{tulot_avg:,.0f} €")
            c3.metric("Menot", f"{menot_avg:,.0f} €", delta="-")
            c4.metric("Jäämä", f"{jaama_avg:,.0f} €", delta=f"{jaama_avg:,.0f} €")

        st.write("") 

        # 3. VÄLILEHDET
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Yleiskuva", "📈 Trendit", "🔮 Simulaattori", "🤖 AI & Chat"])

        # --- TAB 1: YLEISKUVA ---
        with tab1:
            # Ylärivi: Rakenne (Sunburst) ja Top kulut (Bar)
            row1_col1, row1_col2 = st.columns(2)
            
            with row1_col1:
                st.subheader("Menojen rakenne")
                menot_df = df_avg[df_avg['Kategoria']=='Meno']
                fig_sun = px.sunburst(menot_df, path=['Kategoria', 'Selite'], values='Summa', color='Summa', color_continuous_scale='RdBu_r')
                st.plotly_chart(fig_sun, use_container_width=True)
            
            with row1_col2:
                st.subheader("Top 5 Kulut")
                top5 = menot_df.sort_values('Summa', ascending=False).head(5)
                fig_bar = px.bar(top5, x='Summa', y='Selite', orientation='h', text_auto='.2s')
                fig_bar.update_traces(marker_color='#ef4444')
                st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # Alarivi: Vesiputouskaavio (Kassavirta)
            st.subheader("💧 Kassavirran vesiputous")
            
            # Valmistellaan data vesiputousta varten keskiarvoista
            menot_sorted = menot_df.sort_values(by='Summa', ascending=False)
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
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                decreasing={"marker":{"color":"#ef4444"}},
                increasing={"marker":{"color":"#22c55e"}},
                totals={"marker":{"color":"#3b82f6"}}
            ))
            fig_water.update_layout(height=500, title="Kuinka tulot muuttuvat jäämäksi")
            st.plotly_chart(fig_water, use_container_width=True)

        # --- TAB 2: TRENDIT ---
        with tab2:
            st.subheader("Kehitys kuukausittain")
            if kk_lkm > 1:
                df_trend = df_raw.groupby(['Kuukausi', 'Kategoria'])['Summa'].sum().reset_index()
                fig_line = px.line(df_trend, x='Kuukausi', y='Summa', color='Kategoria', markers=True)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.warning("Trendit vaativat dataa useammalta kuukaudelta.")

        # --- TAB 3: SIMULAATTORI ---
        with tab3:
            st.subheader("Korkoa korolle -laskuri")
            c_sim1, c_sim2 = st.columns([1,2])
            with c_sim1:
                kk_saasto = st.slider("Säästö (€/kk)", 0.0, 2000.0, float(max(jaama_avg, 50.0)), step=10.0)
                vuodet = st.slider("Aika (v)", 1, 40, 20)
                korko = st.slider("Tuotto %", 1.0, 15.0, 7.0)
            with c_sim2:
                df_sim = logiikka.laske_tulevaisuus(0, kk_saasto, korko, vuodet)
                fig_area = px.area(df_sim, x="Vuosi", y="Yhteensä")
                st.plotly_chart(fig_area, use_container_width=True)

        # --- TAB 4: ANALYYSI & CHAT ---
        with tab4:
            col_chat, col_analysis = st.columns([1, 1])
            
            # VASEN: CHAT
            with col_chat:
                st.subheader("💬 Kysy datalta")
                # Chat historia
                for msg in st.session_state.messages:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                # Input
                if prompt := st.chat_input("Esim: Mihin meni eniten rahaa?"):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    with st.chat_message("assistant"):
                        with st.spinner("AI tutkii..."):
                            resp = logiikka.chat_with_data(df_raw, prompt, st.session_state.messages)
                            st.markdown(resp)
                            st.session_state.messages.append({"role": "assistant", "content": resp})

            # OIKEA: ANALYYSI (SELAIMESSA)
            with col_analysis:
                st.subheader("📊 Syväluotaava Analyysi")
                st.caption("AI analysoi koko taloutesi tilanteen ja antaa suositukset.")
                
                with st.form("analyysi_form"):
                    ika = st.number_input("Ikä", 18, 99, 30)
                    status = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perhe"])
                    submit_btn = st.form_submit_button("✨ Analysoi Nyt", type="primary")
                
                if submit_btn:
                    with st.spinner("Luodaan analyysiä..."):
                        profiili = {"ika": ika, "suhde": status}
                        analyysi_teksti = logiikka.analysoi_talous(df_avg, profiili, "Keskiarvot")
                        
                        # Tulostetaan tulos tyylikkääseen laatikkoon
                        st.markdown("---")
                        st.markdown(f"""
                        <div style="background-color:#f8fafc; padding:20px; border-radius:10px; border:1px solid #e2e8f0;">
                            {analyysi_teksti}
                        </div>
                        """, unsafe_allow_html=True)

    else:
        st.error("Virhe datan luvussa.")
