import streamlit as st
import pandas as pd
import datetime
import re 
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestione Catalogo Libri", page_icon="📘", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
<style>
    .stApp { background-color: #f4f6f9; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e1e4e8;
        padding: 15px 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04); border-left: 5px solid #0068c9;
    }
    .stButton>button { border-radius: 6px; font-weight: 600; padding: 0.5rem 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; border-radius: 4px 4px 0px 0px; font-weight: 600; }
    div[data-testid="stForm"] { background-color: #ffffff; border-radius: 10px; padding: 25px; border: 1px solid #e1e4e8; }
</style>
""", unsafe_allow_html=True)

# --- CONNESSIONE A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Zn9mqWmS1KAlttSTr55lwA5eS_vjuHIPAh5qF3lMO_E/edit?usp=sharing"

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
    except Exception as e:
        st.error(f"Errore di connessione a Google Sheets: {e}")
        return pd.DataFrame(columns=COLONNE)

def aggiungi_libro(dati_libro):
    df_corrente = carica_dati()
    
    if not df_corrente.empty and str(dati_libro['isbn']) in df_corrente['isbn'].values:
        return False, "Errore: ISBN già censito a sistema."
    
    nuovo_libro = pd.DataFrame([dati_libro])
    df_aggiornato = pd.concat([df_corrente, nuovo_libro], ignore_index=True)
    
    for col in COLONNE:
        if col not in df_aggiornato.columns:
            df_aggiornato[col] =  None
            
    df_aggiornato = df_aggiornato[COLONNE]
    
    # Ordinamento alfabetico prima di salvare
    df_aggiornato.sort_values(by=['cognome1', 'nome1', 'titolo1'], key=lambda col: col.astype(str).str.lower().str.strip(), inplace=True, ignore_index=True)
    
    try:
        conn.update(worksheet="Foglio1", data=df_aggiornato, spreadsheet=SPREADSHEET_URL)
        return True, "Libro inserito e riordinato correttamente a sistema."
    except Exception as e:
        return False, f"Errore durante il salvataggio: {e}"

# --- HEADER DELL'APPLICAZIONE ---
st.title("📘 Sistema di Gestione Libreria (Cloud Edition)")
st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Ricerca", "📝 Inserimento Manuale", "📂 Importazione Massiva (PDF)"])

# --- TAB 1: RICERCA, DASHBOARD E GESTIONE ---
with tab1:
    df_libri = carica_dati()
    
    if not df_libri.empty:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.metric(label="Totale Volumi", value=len(df_libri))
        with col_m2: st.metric(label="Autori Principali", value=df_libri['cognome1'].nunique())
        with col_m3: st.metric(label="Sedi Utilizzate", value=df_libri['luogo'].nunique())
    
    st.markdown("### 🔍 Esplora e Modifica Catalogo")
    
    search_query = st.text_input("Ricerca testuale (Titolo, Autore, ISBN...)", placeholder="Digita qui per cercare...").lower()
    
    df_filtrato = df_libri.copy() if not df_libri.empty else pd.DataFrame()
    
    if not df_libri.empty:
        with st.expander("🛠️ Apri Filtri Avanzati (Lingua, Posizione...)"):
            def ottieni_unici(nome_colonna):
                valori = [str(x).strip() for x in df_libri[nome_colonna].dropna().unique()]
                return sorted(list(set(v for v in valori if v not in ["", "None", "nan"])))
            
            col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
            with col_f1: filtro_lingua = st.multiselect("Lingua", options=ottieni_unici('lingua'))
            with col_f2: filtro_stanza = st.multiselect("Stanza", options=ottieni_unici('stanza'))
            with col_f3: filtro_libreria = st.multiselect("Libreria", options=ottieni_unici('libreria'))
            with col_f4: filtro_riga = st.multiselect("Riga", options=ottieni_unici('riga'))
            with col_f5: filtro_colonna = st.multiselect("Colonna", options=ottieni_unici('colonna'))
                
        # 1. Filtro testuale
        if search_query:
            termini = search_query.split()
            for termine in termini:
                mask = df_filtrato.astype(str).apply(lambda x: x.str.lower().str.contains(termine)).any(axis=1)
                df_filtrato = df_filtrato[mask]
        
        # 2. Filtri avanzati
        if filtro_lingua: df_filtrato = df_filtrato[df_filtrato['lingua'].astype(str).str.strip().isin(filtro_lingua)]
        if filtro_stanza: df_filtrato = df_filtrato[df_filtrato['stanza'].astype(str).str.strip().isin(filtro_stanza)]
        if filtro_libreria: df_filtrato = df_filtrato[df_filtrato['libreria'].astype(str).str.strip().isin(filtro_libreria)]
        if filtro_riga: df_filtrato = df_filtrato[df_filtrato['riga'].astype(str).str.strip().isin(filtro_riga)]
        if filtro_colonna: df_filtrato = df_filtrato[df_filtrato['colonna'].astype(str).str.strip().isin(filtro_colonna)]

        # --- PREPARAZIONE DATI SENZA DECIMALI ---
        df_filtrato = df_filtrato.fillna("").astype(str).replace(["nan", "None", "<NA>", "NaT"], "")
        for col in df_filtrato.columns:
            # Rimuove ".0" alla fine dei numeri ma lascia intatto il testo
            df_filtrato[col] = df_filtrato[col].str.replace(r'\.0$', '', regex=True)
            
        configurazione_testo = {col: st.column_config.TextColumn(col) for col in df_filtrato.columns}

       # --- TABELLA INTERATTIVA (AUTOSALVATAGGIO) ---
        st.info("💡 **Doppio clic sulle celle per modificarle.** Il salvataggio avverrà in automatico in background e la tabella non tornerà più all'inizio.")
        
        ordine_visivo = ['isbn', 'cognome1', 'nome1', 'cognome2', 'nome2', 'cognome3', 'nome3', 
                         'titolo1', 'titolo2', 'editore', 'edi', 'acq', 'lingua', 
                         'argomento1', 'argomento2', 'argomento3', 'luogo', 'stanza', 
                         'libreria', 'riga', 'colonna', 'note1', 'note2']
                         
        df_modificato = st.data_editor(
            df_filtrato, 
            hide_index=True, 
            use_container_width=True, 
            disabled=["isbn"],
            column_config=configurazione_testo,
            column_order=ordine_visivo,
            height=600,
            key="tabella_principale"  # Blocca in memoria l'interfaccia e la posizione di scorrimento
        )
        
        # CONTROLLO SALVATAGGIO AUTOMATICO
        if not df_filtrato.equals(df_modificato):
            # 1. Identifica gli ISBN dei libri visualizzati e modificati
            isbns_modificati = df_modificato['isbn'].astype(str).tolist()
            
            # 2. Rimuovi le vecchie versioni di questi libri dal dataset principale
            df_libri = df_libri[~df_libri['isbn'].astype(str).isin(isbns_modificati)]
            
            # 3. Aggiungi i record appena modificati
            df_libri = pd.concat([df_libri, df_modificato], ignore_index=True)
            
            # 4. Riordina colonne e ordine alfabetico
            for col in COLONNE:
                if col not in df_libri.columns:
                    df_libri[col] = ""
            df_libri = df_libri[COLONNE]
            
            df_libri.sort_values(by=['cognome1', 'nome1', 'titolo1'], key=lambda col: col.astype(str).str.lower().str.strip(), inplace=True, ignore_index=True)
            
            conn.update(worksheet="Foglio1", data=df_libri, spreadsheet=SPREADSHEET_URL)
            
            # Sostituiamo st.rerun() con una notifica visiva non invasiva
            st.toast("Modifica salvata in background!", icon="✅")
                
        # --- SEZIONE MODIFICA ISBN E RIMOZIONE ---
        st.divider()
        st.markdown("**⚙️ Gestione Avanzata (Modifica ISBN o Elimina)**")
        opzioni = df_filtrato['isbn'].astype(str) + " - " + df_filtrato['titolo1'].astype(str)
        selezione = st.selectbox("Seleziona un volume per correggere l'ISBN o rimuoverlo:", options=[""] + list(opzioni))
        
        if selezione:
            isbn_selezionato = selezione.split(" - ")[0]
            st.caption("In questa riga puoi modificare liberamente anche il codice ISBN.")
            
            df_riga = df_libri[df_libri['isbn'].astype(str) == isbn_selezionato].copy()
            df_riga = df_riga.fillna("").astype(str).replace(["nan", "None", "<NA>", "NaT"], "")
            for col in df_riga.columns:
                df_riga[col] = df_riga[col].str.replace(r'\.0$', '', regex=True)
                
            # QUI L'ISBN E' SBLOCCATO
            df_modificato_singolo = st.data_editor(
                df_riga, 
                hide_index=True, 
                use_container_width=True, 
                column_config=configurazione_testo,
                column_order=ordine_visivo
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Applica Modifica Avanzata", type="primary", use_container_width=True):
                    with st.spinner("Salvataggio..."):
                        nuovo_isbn = str(df_modificato_singolo.iloc[0]['isbn']).strip()
                        indice = df_libri.index[df_libri['isbn'].astype(str) == isbn_selezionato].tolist()[0]
                        
                        # Controllo anti-doppioni sul nuovo ISBN
                        if nuovo_isbn != isbn_selezionato and nuovo_isbn in df_libri['isbn'].astype(str).values:
                            st.error(f"⚠️ Impossibile salvare: l'ISBN {nuovo_isbn} è già associato a un altro volume!")
                        else:
                            df_libri.iloc[indice] = df_modificato_singolo.iloc[0]
                            df_libri.sort_values(by=['cognome1', 'nome1', 'titolo1'], key=lambda col: col.astype(str).str.lower().str.strip(), inplace=True, ignore_index=True)
                            
                            conn.update(worksheet="Foglio1", data=df_libri, spreadsheet=SPREADSHEET_URL)
                            st.success("✅ Modifica avanzata salvata con successo!")
                            st.rerun()
                            
            with col_btn2:
                if st.button("🗑️ Elimina Definitivamente", type="secondary", use_container_width=True):
                    with st.spinner("Eliminazione in corso..."):
                        df_libri = df_libri[df_libri['isbn'].astype(str) != isbn_selezionato]
                        conn.update(worksheet="Foglio1", data=df_libri, spreadsheet=SPREADSHEET_URL)
                        st.success("✅ Volume rimosso dal database!")
                        st.rerun()
    else:
        st.info("💡 Database vuoto.")
# --- TAB 2: AGGIUNGI LIBRO (FORM) ---
with tab2:
    with st.form("form_aggiunta", clear_on_submit=True):
        st.subheader("Dati Principali")
        isbn = st.text_input("Codice ISBN *")
        col_t1, col_t2 = st.columns(2)
        with col_t1: titolo1 = st.text_input("Titolo 1 *")
        with col_t2: titolo2 = st.text_input("Titolo 2")
        
        col_e1, col_e2 = st.columns(2)
        with col_e1: editore = st.text_input("Editore")
        with col_e2: lingua = st.text_input("Lingua")

        st.subheader("Autori")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            nome1 = st.text_input("Nome 1")
            nome2 = st.text_input("Nome 2")
            nome3 = st.text_input("Nome 3")
        with col_a2:
            cognome1 = st.text_input("Cognome 1")
            cognome2 = st.text_input("Cognome 2")
            cognome3 = st.text_input("Cognome 3")

        st.subheader("Classificazione & Date")
        col_arg1, col_arg2, col_arg3 = st.columns(3)
        with col_arg1: argomento1 = st.text_input("Argomento 1")
        with col_arg2: argomento2 = st.text_input("Argomento 2")
        with col_arg3: argomento3 = st.text_input("Argomento 3")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1: edi = st.date_input("Data Edizione (edi)", datetime.date.today())
        with col_d2: acq = st.date_input("Data Acquisto (acq)", datetime.date.today())

        st.subheader("Posizione Logistica")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: 
            luogo = st.selectbox("Luogo", ["MI", "ME", "ST"])
            stanza = st.text_input("Stanza")
        with col_p2: 
            libreria = st.text_input("Libreria")
            riga = st.text_input("Riga")
        with col_p3: 
            colonna = st.text_input("Colonna")
            
        st.subheader("Note Aggiuntive")
        note1 = st.text_area("Note 1 (Opzionale)")
        note2 = st.text_area("Note 2 (Opzionale)")
        
        submit = st.form_submit_button("➕ Salva nel Cloud", use_container_width=True)
        
        if submit:
            if not isbn or not titolo1:
                st.error("⚠️ ISBN e Titolo 1 sono obbligatori.")
            else:
                dati_libro = {
                    'isbn': str(isbn), 'cognome1': cognome1, 'cognome2': cognome2, 'cognome3': cognome3,
                    'nome1': nome1, 'nome2': nome2, 'nome3': nome3, 'titolo1': titolo1, 'titolo2': titolo2,
                    'editore': editore, 'edi': str(edi), 'acq': str(acq), 'lingua': lingua,
                    'argomento1': argomento1, 'argomento2': argomento2, 'argomento3': argomento3,
                    'luogo': luogo, 'stanza': stanza, 'libreria': libreria, 'riga': riga, 'colonna': colonna, 
                    'note1': note1, 'note2': note2
                }
                successo, msg = aggiungi_libro(dati_libro)
                if successo: st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")

# --- TAB 3: CARICA DA PDF (Motore Ultra-Leggero PyMuPDF) ---
with tab3:
    st.markdown("### ⚠️LAVORI IN CORSO⚠️ ")
    
