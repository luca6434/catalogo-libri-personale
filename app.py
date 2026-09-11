import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import datetime
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
SPREADSHEET_URL = "INSERISCI_QUI_URL_DEL_TUO_FOGLIO_GOOGLE" # Ricordati di rimettere il tuo URL!

COLONNE = ['isbn', 'cognome1', 'cognome2', 'cognome3', 'nome1', 'nome2', 'nome3', 
           'titolo1', 'titolo2', 'editore', 'edi.', 'acq.', 'lingua', 
           'argomento1', 'argomento2', 'argomento3', 'luogo', 'stanza', 
           'libreria', 'riga', 'colonna', 'note']

def carica_dati():
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
        if not df.empty and 'isbn' in df.columns:
            df['isbn'] = df['isbn'].astype(str)
        return df
    except Exception as e:
        st.error(f"Errore di connessione a Google Sheets: {e}")
        return pd.DataFrame(columns=COLONNE)

def aggiungi_libro(dati_libro):
    df_corrente = carica_dati()
    
    if str(dati_libro['isbn']) in df_corrente['isbn'].values:
        return False, "Errore: ISBN già censito a sistema."
    
    nuovo_libro = pd.DataFrame([dati_libro])
    df_aggiornato = pd.concat([df_corrente, nuovo_libro], ignore_index=True)
    
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
        st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
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
        with col_d1: edi = st.date_input("Data Edizione (edi.)", datetime.date.today())
        with col_d2: acq = st.date_input("Data Acquisto (acq.)", datetime.date.today())

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
            
        note = st.text_area("Note aggiuntive")
        
        submit = st.form_submit_button("➕ Salva nel Cloud", use_container_width=True)
        
        if submit:
            if not isbn or not titolo1:
                st.error("⚠️ ISBN e Titolo 1 sono obbligatori.")
            else:
                dati_libro = {
                    'isbn': str(isbn), 'cognome1': cognome1, 'cognome2': cognome2, 'cognome3': cognome3,
                    'nome1': nome1, 'nome2': nome2, 'nome3': nome3, 'titolo1': titolo1, 'titolo2': titolo2,
                    'editore': editore, 'edi.': str(edi), 'acq.': str(acq), 'lingua': lingua,
                    'argomento1': argomento1, 'argomento2': argomento2, 'argomento3': argomento3,
                    'luogo': luogo, 'stanza': stanza, 'libreria': libreria, 'riga': riga, 'colonna': colonna, 'note': note
                }
                successo, msg = aggiungi_libro(dati_libro)
                if successo: st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")

# --- TAB 3: CARICA DA PDF (Testo) ---
with tab3:
    st.info("Funzionalità in attesa di implementazione logica estrazione ISBN.")
    uploaded_file = st.file_uploader("Seleziona PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        st.text("\n".join(page.extract_text() for page in reader.pages))
