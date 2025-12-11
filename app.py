import streamlit as st
import logiikka  # Tuodaan meidän oma logiikka-moduuli
import os

# --- ASETUKSET ---
st.set_page_config(
    page_title="TalousMaster AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

EXCEL_TEMPLATE_NAME = "talous_pohja.xlsx"

# --- LADATAAN CSS TYYLIT ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Ladataan style.css, jos se on olemassa
if os.path.exists("style.css"):
    local_css("style.css")

# Alustetaan tekoäly
logiikka.konfiguroi_ai()

# --- KÄYTTÖLIITTYMÄ (UI) ---

# 1. OTSIKKO
st.markdown("""
<div>
    <h1 class="main-title">TalousMaster <span class="highlight-blue">AI</span></h1>
    <p class="slogan">Ota taloutesi hallintaan datalla.</p>
</div>
""", unsafe_allow_html=True)

# 2. PÄÄOSIO
col_left, col_right = st.columns([1, 1], gap="large")

# --- VASEN PUOLI (TOIMINNOT) ---
with col_left:
    with st.container(border=True):
        st.subheader("1. Lataa tiedosto")
        uploaded_file = st.file_uploader("Pudota täytetty Excel tähän", type=['xlsx'])
        
        st.write("") 
        st.markdown("---")
        st.write("") 

        st.subheader("2. Puuttuuko pohja?")
        st.write("Lataa valmis pohja, täytä se ja palauta yllä olevaan laatikkoon.")
        
        try:
            with open(EXCEL_TEMPLATE_NAME, "rb") as file:
                st.download_button(
                    label="📥 Lataa Excel-työkalu",
                    data=file,
                    file_name="talous_tyokalu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except:
            st.warning("Pohjatiedostoa ei löytynyt.")

        st.write("")
        st.info("🔒 **Tietoturva:** Älä syötä Exceliin nimeäsi tai tilinumeroita. Data käsitellään anonyymisti.")

# --- OIKEA PUOLI (VIDEO) ---
with col_right:
    st.markdown('<p class="video-title">📽️ Näin TalousMaster toimii</p>', unsafe_allow_html=True)
    st.video("https://videos.pexels.com/video-files/3129671/3129671-hd_1920_1080_30fps.mp4")
    st.caption("Lataa Excel, määritä profiili ja anna tekoälyn etsiä säästökohteet.")

st.write("---")

# 3. TULOS-OSIO
if uploaded_file:
    # Kutsutaan funktiota logiikka-tiedostosta
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
            with st.spinner('Tekoäly varainhoitaja työskentelee...'):
                profiili = {"ika": ika, "suhde": suhde, "lapset": lapset}
                
                # Kutsutaan funktiota logiikka-tiedostosta
                vastaus, lopullinen_jaama = logiikka.analysoi_talous(df_laskettu, profiili, data_tyyppi)
                logiikka.tallenna_lokiiin(profiili, lopullinen_jaama, data_tyyppi)
                
                st.markdown("### 📝 Toimenpidesuositukset")
                st.markdown(f"""
                <div style="background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    {vastaus}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("Virhe: Excelistä ei löytynyt dataa.")