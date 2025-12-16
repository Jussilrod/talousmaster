import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

st.set_page_config(page_title="TaskuEkonomisti 2.0", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

if "messages" not in st.session_state:
    st.session_state.messages = []

local_css_path = "style.css"
if os.path.exists(local_css_path):
    with open(local_css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

logiikka.konfiguroi_ai()

with st.sidebar:
    st.title("💎 TaskuEko")
    uploaded_file = st.file_uploader("📂 Lataa Excel", type=['xlsx'])
    st.markdown("---")
    st.caption("Excelissä oltava sarakkeet kuukausille (esim. Tammi, Helmi) trendejä varten.")

if not uploaded_file:
    st.markdown("# Tervetuloa TaskuEkonomistiin 👋")
    st.info("Aloita lataamalla Excel-tiedosto vasemmalta.")
else:
    df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_raw.empty:
        kk_lkm = df_raw['Kuukausi'].nunique()
        df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
        df_avg['Summa'] = df_avg['Summa'] / kk_lkm 
        
        tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama_avg = tulot_avg - menot_avg

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Data", f"{kk_lkm} kk keskiarvo")
            c2.metric("Tulot", f"{tulot_avg:,.0f} €")
            c3.metric("Menot", f"{menot_avg:,.0f} €", delta="-")
            c4.metric("Jäämä", f"{jaama_avg:,.0f} €", delta=f"{jaama_avg:,.0f} €")

        st.write("") 

        # --- JAETUT VÄLILEHDET: CHAT JA ANALYYSI ERIKSEEN ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Yleiskuva", "📈 Trendit", "🔮 Simulaattori", "💬 Chat", "📝 Analyysi"])

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
                st.warning("Trendit vaativat dataa useammalta kuukaudelta.")

        # TAB 3: SIMULAATTORI
        with tab3:
            st.subheader("Korkoa korolle -laskuri")
            c_sim1, c_sim2 = st.columns([1,2])
            with c_sim1:
                kk_saasto = st.slider("Säästö (€/kk)", 0.0, 2000.0, float(max(jaama_avg, 50.0)), step=10.0)
                vuodet = st.slider("Aika (v)", 1, 40, 20)
                korko = st.slider("Tuotto %", 1.0, 15.0, 7.0)
            with c_sim2:
                df_sim = logiikka.laske_tulevaisuus(0, kk_saasto, korko, vuodet)
                st.plotly_chart(px.area(df_sim, x="Vuosi", y="Yhteensä"), use_container_width=True)

        # TAB 4: CHAT (NYT OMA SIVU)
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

        # TAB 5: ANALYYSI (NYT OMA SIVU)
        with tab5:
            st.subheader("📝 Syväluotaava Analyysi")
            st.info("Täytä tiedot, niin tekoäly luo henkilökohtaisen raportin.")
            
            with st.form("analyysi_form"):
                c_a1, c_a2 = st.columns(2)
                with c_a1:
                    ika = st.number_input("Ikä", 18, 99, 30)
                    lapset = st.number_input("Lasten määrä", 0, 10, 0)
                with c_a2:
                    status = st.selectbox("Parisuhdestatus", ["Yksin", "Parisuhteessa", "Perhe", "Yksinhuoltaja"])
                    data_tyyppi = st.radio("Datan tyyppi", ["Toteuma (Tiliote)", "Suunnitelma (Budjetti)"])
                
                submit_btn = st.form_submit_button("✨ Analysoi Nyt", type="primary")
            
            if submit_btn:
                with st.spinner("Analysoidaan..."):
                    profiili = {"ika": ika, "suhde": status, "lapset": lapset}
                    analyysi_teksti = logiikka.analysoi_talous(df_avg, profiili, data_tyyppi)
                    
                    st.markdown("---")
                    st.markdown(f"""<div style="background-color:#f8fafc; padding:25px; border-radius:10px; border:1px solid #e2e8f0;">{analyysi_teksti}</div>""", unsafe_allow_html=True)
    else:
        st.error("Virhe datan luvussa.")
