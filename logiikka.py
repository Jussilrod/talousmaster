# --- ANALYYSI (PARANNETTU KONTEKSTI) ---
def analysoi_talous(df_avg, profiili, data_tyyppi):
    try:
        # 1. Laskenta (pysyy samana)
        tulot = df_avg[df_avg['Kategoria']=='Tulo']['Summa'].sum()
        menot = df_avg[df_avg['Kategoria']=='Meno']['Summa'].sum()
        jaama = tulot - menot
        
        sijoitukset_summa = 0
        sijoitus_keywords = ['sijoitus', 'rahasto', 'osake', 'säästö', 'nordnet', 'op-tuotto', 'ostot', 'etf']
        for _, row in df_avg[df_avg['Kategoria']=='Meno'].iterrows():
             if any(x in str(row['Selite']).lower() for x in sijoitus_keywords):
                 sijoitukset_summa += row['Summa']
        
        todellinen_saasto = jaama + sijoitukset_summa

        # Top kulut
        top_menot = df_avg[df_avg['Kategoria']=='Meno'].nlargest(5, 'Summa')
        kulut_txt = top_menot.to_string(index=False)

        # 2. Älykäs tilannetulkinta
        if jaama < 0:
            status_txt = "Kriittinen (Alijäämäinen)"
        elif todellinen_saasto > 500:
            status_txt = "Vahva (Ylijäämäinen)"
        else:
            status_txt = "Tasapainoilija (Nollatulos)"

        # 3. PROMPT ENGINEERING (KORJATTU HENKILÖKUVAUS)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        ### ROLE
        Toimit yksityispankkiirina (Private Banker). Tyylisi on analyyttinen mutta empaattinen.
        
        ### ASIAKASPROFIILI (Tärkeä: Erota henkilö ja kotitalous)
        - **Henkilö:** {profiili['ika']}-vuotias aikuinen.
        - **Kotitalous:** {profiili['suhde']}. Lapsia: {profiili['lapset']}.
        - **Päätavoite:** {profiili['tavoite']}
        - **Nettovarallisuus:** {profiili['varallisuus']} € (Asunnot + sijoitukset - velat)
        
        ### TALOUDEN DATA ({data_tyyppi})
        - Tulot: {tulot:.0f} €/kk
        - Menot: {menot:.0f} €/kk
        - Jäämä: {jaama:.0f} €/kk
        - Säästöön menee nyt (sis. sijoitukset): {todellinen_saasto:.0f} €/kk
        - Talouden tila: {status_txt}

        ### TOP 5 KULUERÄT
        {kulut_txt}

        ### TEHTÄVÄ
        Luo Markdown-muotoinen analyysi (älä käytä otsikoissa risuaitaa # vaan ##):

        ## 1. Tilannekuva
        Kuvaile tilannetta luonnollisesti. Esim. "Olet 37-vuotias ja elät lapsiperhearkea..." eikä "Olet 37-vuotias perhe".
        Peilaa nykytilannetta ilmoitettuun tavoitteeseen ("{profiili['tavoite']}"). Onko se realistinen näillä luvuilla?

        ## 2. Kulujen rakenne
        Analysoi TOP-kuluja. Ovatko ne linjassa perhekoon ({profiili['lapset']} lasta) kanssa? 
        Jos lapsia on, huomioi se (esim. ruokakulut ovat luonnostaan korkeammat).

        ## 3. Toimenpidesuositus
        Anna YKSI konkreettinen neuvo, joka auttaa saavuttamaan tavoitteen ({profiili['tavoite']}).
        
        ## 4. Ennuste
        Jos nykyinen säästötahti ({todellinen_saasto:.0f}€/kk) jatkuu, onko tavoite saavutettavissa?

        ## Arvosana (4-10)
        Perustele lyhyesti.
        """

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"Virhe analyysissa: {str(e)}"
