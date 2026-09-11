import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import datetime
from streamlit_gsheets import GSheetsConnection
import re

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
            df_aggiornato[col] = None 
            
    df_aggiornato = df_aggiornato[COLONNE]
    
    try:
        conn.update(worksheet="Foglio1", data=df_aggiornato, spreadsheet=SPREADSHEET_URL)
        return True, "Libro inserito correttamente a sistema."
    except Exception as e:
        return False, f"Errore durante il salvataggio: {e}"

# --- HEADER DELL'APPLICAZIONE ---
st.title("📘 Sistema di Gestione Libreria (Cloud Edition)")
st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Ricerca", "📝 Inserimento Manuale", "📂 Importazione Massiva (PDF)"])

# --- TAB 1: RICERCA E DASHBOARD ---
# --- TAB 1: RICERCA E DASHBOARD ---
with tab1:
    df_libri = carica_dati()
    
    if not df_libri.empty:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.metric(label="Totale Volumi", value=len(df_libri))
        with col_m2: st.metric(label="Autori Principali", value=df_libri['cognome1'].nunique())
        with col_m3: st.metric(label="Sedi Utilizzate", value=df_libri['luogo'].nunique())
    
    st.markdown("### 🔍 Esplora Catalogo")
    search_query = st.text_input("Ricerca libera (Titolo, Autore, ISBN, Luogo...)", placeholder="Inizia a digitare...").lower()
    
    if not df_libri.empty:
        df_filtrato = df_libri.copy()
        if search_query:
            mask = df_filtrato.astype(str).apply(lambda x: x.str.lower().str.contains(search_query)).any(axis=1)
            df_filtrato = df_filtrato[mask]
            
        # Funzione per formattare testi multipli su più righe
        def comprimi_su_righe(row, cols):
            valori = [str(row[c]).strip() for c in cols if pd.notna(row[c]) and str(row[c]).strip() not in ["", "None", "nan"]]
            if len(valori) == 0:
                return ""
            elif len(valori) == 1:
                return valori[0]
            else:
                # Aggiunge un punto elenco e un a capo per separare visivamente ogni voce
                return "\n".join([f"• {v}" for v in valori])
            
        # Costruzione del Dataframe "Visivo"
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

        # Rendering della tabella con i titoli colonne richiesti
        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "isbn": "Isbn",
                "cognome": "cognome",
                "nome": "nome",
                "titolo1": "titolo(1)",
                "titolo2": "titolo(2)",
                "editore": "editore",
                "edi": "edi.",
                "acq": "Acq.",
                "lingua": "Lingua",
                "argomento1": "argomento",
                "argomento2": "argomento",
                "argomento3": "argomento",
                "luogo": "luogo",
                "stanza": "stanza",
                "libreria": "libreria",
                "riga": "riga",
                "colonna": "colonna",
                "note": "note"
            }
        )
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

# --- TAB 3: CARICA DA PDF ---
with tab3:
    st.markdown("### 📂 Importazione Automatica ISBN")
    st.markdown("Carica un PDF. Il sistema analizzerà il testo grezzo usando espressioni regolari per isolare i codici ISBN all'interno del documento.")
    
    uploaded_file = st.file_uploader("Seleziona File (.pdf)", type="pdf")
    
    if uploaded_file is not None:
        with st.spinner("Analisi del documento in corso..."):
            try:
                reader = PdfReader(uploaded_file)
                testo_estratto = ""
                for page in reader.pages:
                    testo_estratto += page.extract_text() + "\n"
                
                # 1. Pulizia: rimuoviamo trattini e spazi per uniformare la ricerca
                testo_pulito = testo_estratto.replace("-", "").replace(" ", "")
                
                # 2. Regex: Cerca sequenze di 13 cifre (inizio 978/979) o 10 cifre
                pattern_isbn = r'(?:97[89])?\d{9}[\dX]'
                isbn_trovati = re.findall(pattern_isbn, testo_pulito, re.IGNORECASE)
                
                # 3. Elimina i doppioni generati leggendo più pagine
                isbn_unici = list(set(isbn_trovati))
                
                if isbn_unici:
                    st.success(f"✅ Analisi completata: trovati {len(isbn_unici)} codici ISBN unici!")
                    
                    # Creiamo una tabella temporanea per mostrarli
                    df_trovati = pd.DataFrame(isbn_unici, columns=["ISBN Rilevati"])
                    st.dataframe(df_trovati, use_container_width=True)
                    
                    st.info("💡 Questi codici sono pronti per essere elaborati.")
                    
                    with st.expander("Visualizza il testo grezzo (Debug)"):
                        st.text(testo_estratto)
                        
                else:
                    st.warning("⚠️ Nessun codice ISBN valido rilevato all'interno del testo.")
                    
            except Exception as e:
                st.error(f"Errore critico durante la lettura del PDF: {e}")
