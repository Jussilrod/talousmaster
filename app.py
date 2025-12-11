import streamlit as st
import logiikka  # Varmista, että logiikka.py on samassa kansiossa
import os

# --- ASETUKSET ---
st.set_page_config(
    page_title="TaskuEkonomisti",
    page_icon="💸",
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

# 1. OTSIKKO (UUSI NIMI JA EMOJI)
st.markdown("""
<div>
    <h1 class="main-title">Tasku<span class="highlight-blue">Ekonomisti</span> 💸</h1>
    <p class="slogan">Varmista, että rahasi pysyvät taskussa eivätkä lennä muille 💸</p>
</div>
""", unsafe_allow_html=True)

# 2. PÄÄOSIO
col_left, col_right = st.columns([1, 1], gap="large")

st.markdown("""
    <div style="
        font-size: 1.2rem; 
        font-weight: 600; 
        color: #334155; 
        margin-top: 15px; 
        line-height: 1.4;">
        🚀 Lataa Excel, määritä profiili ja anna tekoälyn etsiä säästökohteet.
    </div>
    """, unsafe_allow_html=True)

# --- VASEN PUOLI (TOIMINNOT) ---
with col_left:
    with st.container(border=True):
        
        # --- OSA 1: PUUTTUUKO POHJA? ---
        st.subheader("1. Puuttuuko pohja?")
        st.write("Lataa valmis pohja tästä, täytä se tiedoillasi ja tallenna.")
        
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
            st.warning("⚠️ Pohjatiedostoa (talous_pohja.xlsx) ei löytynyt kansiosta.")

        st.markdown("---") # Erotinviiva
        
        # --- OSA 2: LATAA TIEDOSTO ---
        st.subheader("2. Lataa tiedosto")
        st.write("Kun Excel on täytetty, pudota se tähän.")
        
        uploaded_file = st.file_uploader("Pudota täytetty Excel tähän", type=['xlsx'], label_visibility="collapsed")

        st.write("")
        st.info("🔒 **Tietoturva:** Älä syötä Exceliin henkilötietojasi tai tilinumeroita. Data käsitellään anonyymisti.")

# --- OIKEA PUOLI ---
with col_right:
    st.markdown('<p class="video-title">Ota taloutesi hallintaan datalla</p>', unsafe_allow_html=True)
    
    # Tarkistetaan, löytyykö video assets-kansiosta
    video_path = "esittely.mp4"
    
    if os.path.exists(video_path):
        # autoplay=True vaatii yleensä muted=True toimiakseen selaimissa
        st.video(video_path, autoplay=True, muted=True)
    else:
        # Fallback: Jos omaa videota ei löydy, näytetään verkkovideo
        st.warning(f"Videota ei löytynyt polusta: {video_path}")
        st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4", autoplay=True, muted=True)
    
    

# 3. TULOS-OSIO
if uploaded_file:
    # Logiikka haetaan toisesta tiedostosta
    df_laskettu = logiikka.lue_kaksiosainen_excel(uploaded_file)
    
    if not df_laskettu.empty:
        tulot = df_laskettu[df_laskettu['Kategoria']=='Tulo']['Euroa_KK'].sum()
        menot = df_laskettu[df_laskettu['Kategoria']=='Meno']['Euroa_KK'].sum()
        jaama_preview = tulot - menot
        
        st.header("📊 Analyysin tulokset")
        
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            with c1: ika = st.number_input("Ikä", 15, 100, 30)
            with c2: suhde = st.selectbox("Status", ["Yksin", "Parisuhteessa", "Perheellinen", "YH"])
            with c3: lapset = st.number_input("Lapset", 0, 10, 0)
            with c4: data_tyyppi = st.radio("Datan tyyppi", ["Suunnitelma", "Toteuma"])

        st.write("")
        m1, m2, m3 = st.columns(3)
        m1.metric("Tulot", f"{tulot:,.0f} €")
        m2.metric("Menot", f"{menot:,.0f} €")
        m3.metric("Jäämä", f"{jaama_preview:,.0f} €", delta_color="normal", delta=f"{jaama_preview:,.0f} €")

        st.write("")
        analyze_btn = st.button("✨ LUO ANALYYSI", type="primary", use_container_width=True)

        if analyze_btn:
            with st.spinner('Taskuekonomisti laskee suosituksia...'):
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














