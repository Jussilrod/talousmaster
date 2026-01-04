import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logiikka
import os

# --- ASETUKSET ---
st.set_page_config(page_title="TaskuEkonomisti 2.0", page_icon="💎", layout="wide")

if "messages" not in st.session_state: st.session_state.messages = []
if "varallisuus_tavoite" not in st.session_state: st.session_state.varallisuus_tavoite = 10000.0
if "analyysi_kaynnissa" not in st.session_state: st.session_state.analyysi_kaynnissa = False

# Alustetaan manuaalinen data session_stateen
if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(
        columns=["Kategoria", "Selite", "Summa", "Kuukausi"],
        data=[["Tulo", "Palkka", 3000.0, "Tammi"], ["Meno", "Vuokra", 800.0, "Tammi"]]
    )

EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx"

# --- CSS ---
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

logiikka.konfiguroi_ai()

# --- SIVUPALKKI ---
with st.sidebar:
    st.title("💎 Valikko")
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
    uploaded_file = st.file_uploader("📂 Lataa täytetty Excel", type=['xlsx'])
    
    if uploaded_file:
        st.session_state.analyysi_kaynnissa = True # Tiedoston lataus aktivoi analyysin
        if st.button("🗑️ Tyhjennä tiedosto"):
            st.session_state.analyysi_kaynnissa = False
            st.rerun()

    st.markdown("---")
    with st.expander("🔒 Tietoturva & Yksityisyys", expanded=False):
        st.markdown("""
        <small style="color: #ef4444;">
        ⚠️ **Suositus:** Älä syötä Exceliin henkilötietojasi tai tilinumeroita. Data käsitellään anonyymisti.
        </small>
        ---
        **1. SSL-salaus:** Yhteys on suojattu (HTTPS/SSL).
        **2. Ei tallennusta:** Käsitellään vain RAM-muistissa istunnon ajan.
        **3. Tietojen minimointi:** AI näkee vain luvut ja selitteet.
        """, unsafe_allow_html=True)

# --- OTSIKKO ---
st.markdown("""
<div style="text-align: center; margin-top: 10px; margin-bottom: 30px;">
    <h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💎</h1>
    <p class="slogan">Ota taloutesi hallintaan datalla ja tekoälyllä</p>
</div>
""", unsafe_allow_html=True)

# --- DATAN HALLINTA ---
df_raw = pd.DataFrame()

if uploaded_file:
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if "df_raw" not in st.session_state or st.session_state.get("last_file") != file_id:
        st.session_state.df_raw = logiikka.lue_kaksiosainen_excel(uploaded_file)
        st.session_state.last_file = file_id
    df_raw = st.session_state.df_raw
else:
    # MANUAALINEN SYÖTTÖ ETUSIVULLA
    if not st.session_state.analyysi_kaynnissa:
        col_a, col_b, col_c = st.columns([1, 4, 1])
        with col_b:
            st.markdown("""
            <div style="text-align: center; background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
                <h3>👋 Tervetuloa!</h3>
                <p>Syötä tiedot alle tai lataa Excel sivupalkista.</p>
            </div>
            """, unsafe_allow_html=True)
            
            edited_df = st.data_editor(
                st.session_state.manual_df,
                num_rows="dynamic",
                use_container_width=True,
                key="editor"
            )
            
            if st.button("🚀 Analysoi syötetyt tiedot", type="primary", use_container_width=True):
                st.session_state.manual_df = edited_df
                st.session_state.analyysi_kaynnissa = True
                st.rerun()
    else:
        # Jos analyysi on päällä, käytetään tallennettua manuaalista dataa
        df_raw = st.session_state.manual_df
        if st.button("⬅️ Muokkaa tietoja"):
            st.session_state.analyysi_kaynnissa = False
            st.rerun()

# --- VISUALISOINTI ---
if st.session_state.analyysi_kaynnissa and not df_raw.empty:
    # Varmistetaan kk-nimet
    kk_nimet_map = {'kk_1': 'Tammi', 'kk_2': 'Helmi', 'kk_3': 'Maalis', 'kk_4': 'Huhti', 'kk_5': 'Touko', 'kk_6': 'Kesä', 'kk_7': 'Heinä', 'kk_8': 'Elo', 'kk_9': 'Syys', 'kk_10': 'Loka', 'kk_11': 'Marras', 'kk_12': 'Joulu'}
    df_raw['Kuukausi'] = df_raw['Kuukausi'].replace(kk_nimet_map)
    oikea_jarjestys = ['Tammi', 'Helmi', 'Maalis', 'Huhti', 'Touko', 'Kesä', 'Heinä', 'Elo', 'Syys', 'Loka', 'Marras', 'Joulu']
    
    kk_lkm = df_raw['Kuukausi'].nunique()
    df_avg = df_raw.groupby(['Kategoria', 'Selite'])['Summa'].sum().reset_index()
    df_avg['Summa'] /= kk_lkm
    tulot_avg = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
    menot_avg = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
    jaama_avg = tulot_avg - menot_avg

    # KPI KORTIT
    c1, c2, c3, c4 = st.columns(4)
    m = [("Analysoitu", f"{kk_lkm} kk"), ("Tulot (kk)", logiikka.muotoile_suomi(tulot_avg)), ("Menot (kk)", logiikka.muotoile_suomi(menot_avg)), ("Jäämä (kk)", logiikka.muotoile_suomi(jaama_avg))]
    for i, col in enumerate([c1, c2, c3, c4]):
        col.markdown(f'<div class="kpi-card"><div class="kpi-label">{m[i][0]}</div><div class="kpi-value">{m[i][1]}</div></div>', unsafe_allow_html=True)

    # Vakaa navigointi
    tabs_list = ["📊 Yleiskuva", "📈 Trendit", "🔮 Simulaattori", "💬 Chat", "📝 Analyysi"]
    active_tab = st.radio("Nav", tabs_list, horizontal=True, label_visibility="collapsed", key="nav")
    st.markdown("<br>", unsafe_allow_html=True)

    if active_tab == "📊 Yleiskuva":
        r1, r2 = st.columns(2)
        with r1:
            st.subheader("Menojen rakenne")
            fig_sun = px.sunburst(df_avg[df_avg['Kategoria']=='Meno'], path=['Kategoria', 'Selite'], values='Summa', color_discrete_sequence=logiikka.PASTEL_COLORS)
            st.plotly_chart(fig_sun, use_container_width=True)
        with r2:
            st.subheader("Top 5 Kulut")
            top5 = df_avg[df_avg['Kategoria']=='Meno'].sort_values('Summa', ascending=False).head(5)
            fig_bar = px.bar(top5, x='Summa', y='Selite', orientation='h', text_auto='.0f')
            fig_bar.update_traces(marker_color=logiikka.PASTEL_COLORS[2])
            st.plotly_chart(fig_bar, use_container_width=True)
        st.divider()
        st.subheader("💰 Kassavirta")
        menot_sorted = df_avg[df_avg['Kategoria']=='Meno'].sort_values(by='Summa', ascending=False)
        labels = ["Tulot"] + menot_sorted['Selite'].tolist() + ["JÄÄMÄ"]
        values = [tulot_avg] + [x * -1 for x in menot_sorted['Summa'].tolist()] + [0]
        measure = ["absolute"] + ["relative"] * len(menot_sorted) + ["total"]
        fig_water = go.Figure(go.Waterfall(orientation="v", measure=measure, x=labels, y=values, connector={"line":{"color":"#cbd5e1"}}, decreasing={"marker":{"color": "#fca5a5"}}, increasing={"marker":{"color": "#86efac"}}, totals={"marker":{"color": logiikka.PASTEL_COLORS[0]}}))
        st.plotly_chart(fig_water, use_container_width=True)

    elif active_tab == "📈 Trendit":
        st.subheader("Rahan virtausanalyysi")
        st.plotly_chart(logiikka.luo_sankey(tulot_avg, df_avg[df_avg['Kategoria']=='Meno'], jaama_avg), use_container_width=True)           
        st.divider()
        st.subheader("Kehitys kuukausittain")
        if kk_lkm > 1:
            df_trend = df_raw.groupby(['Kuukausi', 'Kategoria'])['Summa'].sum().reset_index()
            kk_idx_map = {nimi: i for i, nimi in enumerate(oikea_jarjestys)}
            df_trend['kk_nro'] = df_trend['Kuukausi'].map(kk_idx_map)
            df_trend = df_trend.sort_values(by='kk_nro')
            fig_trend = px.line(df_trend, x='Kuukausi', y='Summa', color='Kategoria', markers=True, color_discrete_sequence=[logiikka.PASTEL_COLORS[2], logiikka.PASTEL_COLORS[4]])
            fig_trend.update_xaxes(categoryorder='array', categoryarray=oikea_jarjestys)
            st.plotly_chart(fig_trend, use_container_width=True)
        else: st.warning("Trendit vaativat dataa useammalta kuukaudelta.")

    elif active_tab == "🔮 Simulaattori":
        st.subheader("🔮 Miljonääri-simulaattori")
        c_sim1, c_sim2 = st.columns([1,2])
        with c_sim1:
            kk_saasto = st.slider("Kuukausisäästö (€)", 0.0, 1000.0, float(max(jaama_avg, 50.0)), step=10.0)
            vuodet = st.slider("Sijoitusaika (v)", 1, 40, 20)
            korko = st.slider("Tuotto %", 1.0, 15.0, 7.0)
            alkupotti = st.number_input("Alkupääoma (€)", 0, 1000000, 0, step=1000)
        with c_sim2:
            df_sim = logiikka.laske_tulevaisuus(alkupotti, kk_saasto, korko, vuodet)
            loppusumma = df_sim.iloc[-1]['Yhteensä']
            st.metric(f"Salkun arvo {vuodet} vuoden päästä", logiikka.muotoile_suomi(loppusumma))
            fig_area = px.area(df_sim, x="Vuosi", y=["Oma pääoma", "Tuotto"], color_discrete_sequence=[logiikka.PASTEL_COLORS[5], logiikka.PASTEL_COLORS[4]])
            st.plotly_chart(fig_area, use_container_width=True)

    elif active_tab == "💬 Chat":
        st.subheader("💬 Kysy taloudestasi")
        chat_cont = st.container()
        for msg in st.session_state.messages:
            with chat_cont:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        chat_in = st.chat_input("Kirjoita kysymys...")
        if chat_in:
            st.session_state.messages.append({"role": "user", "content": chat_in})
            with chat_cont:
                with st.chat_message("user"): st.markdown(chat_in)
                with st.chat_message("assistant"):
                    resp = logiikka.chat_with_data(df_raw, chat_in, st.session_state.messages)
                    st.markdown(resp)
                    st.session_state.messages.append({"role": "assistant", "content": resp})

    elif active_tab == "📝 Analyysi":
        with st.form("analyysi_form"):
            st.markdown("### 📝 Varainhoitajan analyysi")
            data_tyyppi = st.radio("Datan tyyppi", ["Toteuma", "Budjetti"], horizontal=True)
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                ika, lapset = st.number_input("Ikä", 18, 99, 30), st.number_input("Lapset", 0, 10, 0)
            with c_a2:
                status = st.selectbox("Tilanne", ["Sinkku", "Parisuhteessa (yhteistalous)", "Parisuhteessa (erilliset)", "Lapsiperhe", "Yksinhuoltaja"])
                varallisuus = st.number_input("Nykyinen varallisuus (€)", value=1000.0)
            tavoite_nimi = st.selectbox("Tavoite", ["Puskurin kerryttäminen", "Asunnon osto", "Velattomuus", "FIRE (Riippumattomuus)", "Elintason nosto", "Sijoitusten kasvatus"])
            tavoite_summa = st.number_input("Tavoitesumma (€)", value=10000.0)
            submit = st.form_submit_button("✨ Aja AI-Analyysi", type="primary")
        if submit:
            with st.spinner("AI analysoi..."):
                prof = {"ika": ika, "suhde": status, "lapset": lapset, "tavoite": tavoite_nimi, "varallisuus": varallisuus, "tavoite_summa": tavoite_summa}
                res = logiikka.analysoi_talous(df_avg, prof, data_tyyppi, df_raw)
                st.divider()
                st.markdown(f'<div style="background-color: white; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0; color: black;">{res}</div>', unsafe_allow_html=True)
