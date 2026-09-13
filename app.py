import streamlit as st
import pandas as pd
import datetime
import re
import pdfplumber
import tempfile
import os
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Catalogo Libreria", page_icon="📘", layout="wide")

# --- DESIGN MODERNO (CSS) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f1f3f5 100%);
        border-left: 5px solid #1c7ed6;
        padding: 20px 25px; 
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        border-left: 5px solid #1c7ed6;
    }
    div[data-testid="metric-container"] label {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #6c757d !important;
    }
    div[data-testid="metric-container"] div {
        font-size: 2.2rem !important;
        color: #1c7ed6 !important;
        font-weight: 800 !important;
    }

    .stButton>button { 
        border-radius: 8px; 
        font-weight: 600; 
        padding: 0.6rem 1.2rem; 
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; font-weight: 600; }
    div[data-testid="stForm"] { 
        background-color: #ffffff; 
        border-radius: 12px; 
        padding: 25px; 
        border: 1px solid #e9ecef; 
        box-shadow: 0 2px 10px rgba(0,0,0,0.02); 
    }
</style>
""", unsafe_allow_html=True)

# --- CONNESSIONE E VARIABILI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SPREADSHEET_URL = "INSERISCI_QUI_URL_DEL_TUO_FOGLIO_GOOGLE"

COLONNE = ['isbn', 'cognome1', 'cognome2', 'cognome3', 'nome1', 'nome2', 'nome3', 
           'titolo1', 'titolo2', 'editore', 'edi', 'acq', 'lingua', 
           'argomento1', 'argomento2', 'argomento3', 'luogo', 'stanza', 
           'libreria', 'riga', 'colonna', 'note1', 'note2']

def carica_dati():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
        df.columns = df.columns.str.strip()
        colonne_valide = [c for c in COLONNE if c in df.columns]
        if not df.empty:
            df = df[colonne_valide]
            if 'isbn' in df.columns:
                df['isbn'] = df['isbn'].astype(str)
        else:
            df = pd.DataFrame(columns=COLONNE)
        return df
    except:
        return pd.DataFrame(columns=COLONNE)

# --- INTERFACCIA PRINCIPALE ---
st.title("📘 Gestione Catalogo")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Ricerca", "➕ Inserimento Manuale", "📂 Estrazione PDF"])

# --- TAB 1: DASHBOARD ---
with tab1:
    df_libri = carica_dati()
    
    if not df_libri.empty:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.metric("Totale Volumi", len(df_libri))
        with col_m2: st.metric("Autori", df_libri['cognome1'].nunique())
        with col_m3: st.metric("Sedi", df_libri['luogo'].nunique())
        
        st.write("")
        
        search_query = st.text_input("Ricerca testuale", placeholder="Es. eco roma 2024...", label_visibility="collapsed").lower()
        
        df_filtrato = df_libri.copy()
        
        with st.expander("🛠️ Filtri Avanzati"):
            def ottieni_unici(nome_colonna):
                valori = [str(x).strip() for x in df_libri[nome_colonna].dropna().unique()]
                return sorted(list(set(v for v in valori if v not in ["", "None", "nan"])))
            
            col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
            with col_f1: filtro_lingua = st.multiselect("Lingua", ottieni_unici('lingua'))
            with col_f2: filtro_stanza = st.multiselect("Stanza", ottieni_unici('stanza'))
            with col_f3: filtro_libreria = st.multiselect("Libreria", ottieni_unici('libreria'))
            with col_f4: filtro_riga = st.multiselect("Riga", ottieni_unici('riga'))
            with col_f5: filtro_colonna = st.multiselect("Colonna", ottieni_unici('colonna'))
                
        if search_query:
            for termine in search_query.split():
                mask = df_filtrato.astype(str).apply(lambda x: x.str.lower().str.contains(termine)).any(axis=1)
                df_filtrato = df_filtrato[mask]
        
        if filtro_lingua: df_filtrato = df_filtrato[df_filtrato['lingua'].astype(str).str.strip().isin(filtro_lingua)]
        if filtro_stanza: df_filtrato = df_filtrato[df_filtrato['stanza'].astype(str).str.strip().isin(filtro_stanza)]
        if filtro_libreria: df_filtrato = df_filtrato[df_filtrato['libreria'].astype(str).str.strip().isin(filtro_libreria)]
        if filtro_riga: df_filtrato = df_filtrato[df_filtrato['riga'].astype(str).str.strip().isin(filtro_riga)]
        if filtro_colonna: df_filtrato = df_filtrato[df_filtrato['colonna'].astype(str).str.strip().isin(filtro_colonna)]

        def comprimi_su_righe(row, cols):
            valori = [str(row[c]).strip() for c in cols if pd.notna(row[c]) and str(row[c]).strip() not in ["", "None", "nan"]]
            if len(valori) == 0: return ""
            elif len(valori) == 1: return valori[0]
            else: return "\n".join([f"• {v}" for v in valori])
            
        df_display = pd.DataFrame()
        df_display['isbn'] = df_filtrato.get('isbn', '')
        df_display['cognome'] = df_filtrato.apply(lambda r: comprimi_su_righe(r, ['cognome1', 'cognome2', 'cognome3']), axis=1)
        df_display['nome'] = df_filtrato.apply(lambda r: comprimi_su_righe(r, ['nome1', 'nome2', 'nome3']), axis=1)
        df_display['titolo1'] = df_filtrato.get('titolo1', '')
        df_display['titolo2'] = df_filtrato.get('titolo2', '')
        df_display['editore'] = df_filtrato.get('editore', '')
        df_display['edi'] = df_filtrato.get('edi', '')
        df_display['acq'] = df_filtrato.get('acq', '')
        df_display['lingua'] = df_filtrato.get('lingua', '')
        df_display['argomento1'] = df_filtrato.get('argomento1', '')
        df_display['argomento2'] = df_filtrato.get('argomento2', '')
        df_display['argomento3'] = df_filtrato.get('argomento3', '')
        df_display['luogo'] = df_filtrato.get('luogo', '')
        df_display['stanza'] = df_filtrato.get('stanza', '')
        df_display['libreria'] = df_filtrato.get('libreria', '')
        df_display['riga'] = df_filtrato.get('riga', '')
        df_display['colonna'] = df_filtrato.get('colonna', '')
        df_display['note'] = df_filtrato.apply(lambda r: comprimi_su_righe(r, ['note1', 'note2']), axis=1)

        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={"isbn": "Isbn", "cognome": "cognome", "nome": "nome", "titolo1": "titolo(1)", "titolo2": "titolo(2)", "editore": "editore", "edi": "edi.", "acq": "Acq.", "lingua": "Lingua", "argomento1": "argomento", "argomento2": "argomento", "argomento3": "argomento", "luogo": "luogo", "stanza": "stanza", "libreria": "libreria", "riga": "riga", "colonna": "colonna", "note": "note"}
        )
        
        st.write("")
        opzioni = df_filtrato['isbn'].astype(str) + " - " + df_filtrato['titolo1'].astype(str)
        selezione = st.selectbox("Gestione Rapida Volume", options=[""] + list(opzioni), label_visibility="collapsed")
        
        if selezione:
            isbn_selezionato = selezione.split(" - ")[0]
            df_riga = df_libri[df_libri['isbn'].astype(str) == isbn_selezionato].copy()
            df_modificato = st.data_editor(df_riga, hide_index=True, use_container_width=True, disabled=["isbn"])
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("💾 Applica Modifiche", type="primary", use_container_width=True):
                    indice = df_libri.index[df_libri['isbn'].astype(str) == isbn_selezionato].tolist()[0]
                    df_libri.iloc[indice] = df_modificato.iloc[0]
                    
                    # Ordinamento alfabetico pre-salvataggio
                    df_libri.sort_values(by=['cognome1', 'nome1', 'titolo1'], key=lambda col: col.astype(str).str.lower().str.strip(), inplace=True, ignore_index=True)
                    
                    conn.update(worksheet="Foglio1", data=df_libri, spreadsheet=SPREADSHEET_URL)
                    st.rerun()
            with col_b2:
                if st.button("🗑️ Elimina", use_container_width=True):
                    df_libri = df_libri[df_libri['isbn'].astype(str) != isbn_selezionato]
                    conn.update(worksheet="Foglio1", data=df_libri, spreadsheet=SPREADSHEET_URL)
                    st.rerun()

# --- TAB 2: INSERIMENTO ---
with tab2:
    with st.form("form_aggiunta", clear_on_submit=True):
        isbn = st.text_input("Codice ISBN")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1: titolo1 = st.text_input("Titolo 1")
        with col_t2: titolo2 = st.text_input("Titolo 2")
        
        col_e1, col_e2 = st.columns(2)
        with col_e1: editore = st.text_input("Editore")
        with col_e2: lingua = st.text_input("Lingua")

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            nome1 = st.text_input("Nome 1")
            nome2 = st.text_input("Nome 2")
            nome3 = st.text_input("Nome 3")
        with col_a2:
            cognome1 = st.text_input("Cognome 1")
            cognome2 = st.text_input("Cognome 2")
            cognome3 = st.text_input("Cognome 3")

        col_arg1, col_arg2, col_arg3 = st.columns(3)
        with col_arg1: argomento1 = st.text_input("Argomento 1")
        with col_arg2: argomento2 = st.text_input("Argomento 2")
        with col_arg3: argomento3 = st.text_input("Argomento 3")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1: edi = st.text_input("Data Edizione")
        with col_d2: acq = st.text_input("Data Acquisto")

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: 
            luogo = st.selectbox("Luogo", ["", "MI", "ME", "ST"])
            stanza = st.text_input("Stanza")
        with col_p2: 
            libreria = st.text_input("Libreria")
            riga = st.text_input("Riga")
        with col_p3: 
            colonna = st.text_input("Colonna")
            
        note1 = st.text_area("Note 1")
        note2 = st.text_area("Note 2")
        
        if st.form_submit_button("➕ Aggiungi al Catalogo", type="primary", use_container_width=True):
            if isbn and titolo1:
                df_corrente = carica_dati()
                if not df_corrente.empty and str(isbn) in df_corrente['isbn'].values:
                    st.error("ISBN già esistente nel sistema.")
                else:
                    dati_libro = {
                        'isbn': str(isbn), 'cognome1': cognome1, 'cognome2': cognome2, 'cognome3': cognome3,
                        'nome1': nome1, 'nome2': nome2, 'nome3': nome3, 'titolo1': titolo1, 'titolo2': titolo2,
                        'editore': editore, 'edi': edi, 'acq': acq, 'lingua': lingua,
                        'argomento1': argomento1, 'argomento2': argomento2, 'argomento3': argomento3,
                        'luogo': luogo, 'stanza': stanza, 'libreria': libreria, 'riga': riga, 'colonna': colonna, 
                        'note1': note1, 'note2': note2
                    }
                    nuovo_libro = pd.DataFrame([dati_libro])
                    df_aggiornato = pd.concat([df_corrente, nuovo_libro], ignore_index=True)
                    
                    for col in COLONNE:
                        if col not in df_aggiornato.columns:
                            df_aggiornato[col] = ""
                            
                    df_aggiornato = df_aggiornato[COLONNE]
                    
                    # Ordinamento alfabetico pre-salvataggio
                    df_aggiornato.sort_values(by=['cognome1', 'nome1', 'titolo1'], key=lambda col: col.astype(str).str.lower().str.strip(), inplace=True, ignore_index=True)
                    
                    conn.update(worksheet="Foglio1", data=df_aggiornato, spreadsheet=SPREADSHEET_URL)
                    st.success("Volume salvato correttamente in ordine alfabetico!")
            else:
                st.error("ISBN e Titolo 1 sono campi obbligatori.")

# --- TAB 3: PDF ---
with tab3:
    ha_intestazione = st.checkbox("Ignora la prima riga delle tabelle", value=True)
    uploaded_file = st.file_uploader("Carica File PDF", type="pdf", label_visibility="collapsed")
    
    if uploaded_file is not None:
        with st.spinner("Scansione in corso..."):
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    temp_path = tmp_file.name
                
                libri_trovati = []
                
                with pdfplumber.open(temp_path) as pdf:
                    totale_pagine = len(pdf.pages)
                    progress_bar = st.progress(0)
                    
                    for num_pagina, pagina in enumerate(pdf.pages):
                        progress_bar.progress((num_pagina + 1) / totale_pagine)
                        
                        tabelle = pagina.extract_tables()
                        for tabella in tabelle:
                            dati = tabella[1:] if ha_intestazione and num_pagina == 0 else tabella
                            for riga in dati:
                                if not riga or all(cella is None or str(cella).strip() == "" for cella in riga):
                                    continue
                                
                                riga_pulita = [str(cella).replace('\n', ' ').strip() if cella else "" for cella in riga]
                                
                                isbn_trovato = ""
                                for cella in riga_pulita:
                                    match = re.search(r'(?:97[89])?\d{9}[\dX]', cella.replace("-", "").replace(" ", ""), re.IGNORECASE)
                                    if match:
                                        isbn_trovato = match.group(0)
                                        break
                                
                                if isbn_trovato:
                                    libro = {col: "" for col in COLONNE}
                                    for indice_col, nome_col in enumerate(COLONNE):
                                        if indice_col < len(riga_pulita):
                                            if nome_col == 'isbn':
                                                libro[nome_col] = str(isbn_trovato)
                                            else:
                                                libro[nome_col] = riga_pulita[indice_col]
                                        elif nome_col == 'isbn':
                                            libro[nome_col] = str(isbn_trovato)
                                            
                                    libri_trovati.append(libro)
                                    
                progress_bar.empty()
                
                if libri_trovati:
                    df_trovati = pd.DataFrame(libri_trovati)
                    st.dataframe(df_trovati, use_container_width=True, hide_index=True)
                    
                    if st.button("💾 Salva in blocco nel Database", type="primary", use_container_width=True):
                        with st.spinner("Sincronizzazione..."):
                            df_corrente = carica_dati()
                            isbn_esistenti = df_corrente['isbn'].astype(str).tolist() if not df_corrente.empty else []
                            nuovi_inserimenti = [l for l in libri_trovati if str(l['isbn']) not in isbn_esistenti]
                            
                            if nuovi_inserimenti:
                                df_nuovi = pd.DataFrame(nuovi_inserimenti)
                                df_aggiornato = pd.concat([df_corrente, df_nuovi], ignore_index=True)
                                
                                for col in COLONNE:
                                    if col not in df_aggiornato.columns:
                                        df_aggiornato[col] = ""
                                df_aggiornato = df_aggiornato[COLONNE]
                                
                                # Ordinamento alfabetico pre-salvataggio massivo
                                df_aggiornato.sort_values(by=['cognome1', 'nome1', 'titolo1'], key=lambda col: col.astype(str).str.lower().str.strip(), inplace=True, ignore_index=True)
                                
                                conn.update(worksheet="Foglio1", data=df_aggiornato, spreadsheet=SPREADSHEET_URL)
                                st.success(f"{len(nuovi_inserimenti)} volumi aggiunti e riordinati!")
                            else:
                                st.warning("Tutti i volumi elaborati sono già nel sistema.")
                                
            except Exception as e:
                st.error(f"Errore: {e}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
