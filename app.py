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
# Creiamo l'oggetto di connessione globale
conn = st.connection("gsheets", type=GSheetsConnection)

# URL del tuo foglio (sostituisci questo URL con quello del tuo Google Sheet)
# Esempio: "https://docs.google.com/spreadsheets/d/1abcxyz..."
SPREADSHEET_URL = "INSERISCI_QUI_URL_DEL_TUO_FOGLIO_GOOGLE"

def carica_dati():
    # Legge i dati dal foglio. 'ttl=0' disattiva la cache per forzare l'aggiornamento
    try:
        df = conn.read(spreadsheet=SPREADSHEET_URL, ttl=0)
        # Convertiamo la colonna isbn in stringa per evitare problemi di formattazione
        df['isbn'] = df['isbn'].astype(str)
        return df
    except Exception as e:
        st.error(f"Errore di connessione a Google Sheets: {e}")
        # Ritorna un dataframe vuoto con le colonne corrette in caso di errore
        return pd.DataFrame(columns=["isbn", "titolo", "nome_autore", "cognome_autore", "data_acquisto", "data_edizione", "tipologia", "argomento", "posizione", "luogo_acquisto"])

def aggiungi_libro(isbn, titolo, nome, cognome, d_acq, d_ed, tipo, arg, pos, luogo):
    df_corrente = carica_dati()
    
    # Controlla l'unicità dell'ISBN
    if str(isbn) in df_corrente['isbn'].values:
        return False, "Errore: ISBN già censito a sistema. Operazione annullata."
    
    nuovo_libro = pd.DataFrame([{
        "isbn": str(isbn), "titolo": titolo, "nome_autore": nome, "cognome_autore": cognome,
        "data_acquisto": d_acq, "data_edizione": d_ed, "tipologia": tipo, 
        "argomento": arg, "posizione": pos, "luogo_acquisto": luogo
    }])
    
    # Unisce il nuovo libro ai dati esistenti
    df_aggiornato = pd.concat([df_corrente, nuovo_libro], ignore_index=True)
    
    # Scrive i dati aggiornati sul foglio di calcolo
    try:
        conn.update(worksheet="Foglio1", data=df_aggiornato, spreadsheet=SPREADSHEET_URL)
        return True, "Libro inserito correttamente a sistema."
    except Exception as e:
        return False, f"Errore durante il salvataggio: {e}"

# --- HEADER DELL'APPLICAZIONE ---
st.title("📘 Sistema di Gestione Libreria (Cloud Edition)")
st.markdown("Pannello di controllo collegato a Google Sheets per il salvataggio permanente.")
st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Ricerca", "📝 Inserimento Manuale", "📂 Importazione Massiva (PDF)"])

# --- TAB 1: RICERCA E DASHBOARD ---
with tab1:
    df_libri = carica_dati()
    
    if not df_libri.empty:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1: st.metric(label="Totale Volumi", value=len(df_libri))
        with col_m2: st.metric(label="Autori in Catalogo", value=df_libri['cognome_autore'].nunique())
        with col_m3: st.metric(label="Totale Saggi", value=len(df_libri[df_libri['tipologia'] == 'Saggio']))
        with col_m4: st.metric(label="Ultimo acquisto", value=df_libri['data_acquisto'].max() if not df_libri['data_acquisto'].empty else "N/A")
    
    st.markdown("### 🔍 Esplora Catalogo")
    col_search, col_filter = st.columns([3, 1])
    with col_search: search_query = st.text_input("Ricerca...", placeholder="Filtra...").lower()
    with col_filter: filtro_tipo = st.selectbox("Filtra Tipologia", ["Tutte", "Manuale", "Saggio", "Romanzo", "Fumetto", "Altro"])
    
    if not df_libri.empty:
        df_filtrato = df_libri.copy()
        if filtro_tipo != "Tutte": df_filtrato = df_filtrato[df_filtrato['tipologia'] == filtro_tipo]
        if search_query:
            # Ricerca su tutte le colonne convertite in stringa
            mask = df_filtrato.astype(str).apply(lambda x: x.str.lower().str.contains(search_query)).any(axis=1)
            df_filtrato = df_filtrato[mask]
        st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
    else:
        st.info("💡 Database vuoto.")

# --- TAB 2: AGGIUNGI LIBRO (FORM) ---
with tab2:
    with st.form("form_aggiunta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: isbn = st.text_input("Codice ISBN *"); titolo = st.text_input("Titolo *")
        with col2: nome_autore = st.text_input("Nome"); cognome_autore = st.text_input("Cognome")
        
        st.divider()
        col3, col4, col5 = st.columns(3)
        with col3: tipo = st.selectbox("Categoria", ["Manuale", "Saggio", "Romanzo", "Fumetto", "Altro"]); arg = st.text_input("Argomento")
        with col4: d_ed = st.date_input("Edizione", datetime.date.today()); d_acq = st.date_input("Acquisto", datetime.date.today())
        with col5: luogo = st.selectbox("Luogo", ["MI", "ME", "ST"]); pos = st.text_input("Posizione")
        
        submit = st.form_submit_button("➕ Salva nel Cloud", use_container_width=True)
        
        if submit:
            if not isbn or not titolo:
                st.error("⚠️ ISBN e Titolo obbligatori.")
            else:
                successo, msg = aggiungi_libro(isbn, titolo, nome_autore, cognome_autore, str(d_acq), str(d_ed), tipo, arg, pos, luogo)
                if successo: st.success(f"✅ {msg}")
                else: st.error(f"❌ {msg}")

# --- TAB 3: CARICA DA PDF (Testo) ---
with tab3:
    st.info("Funzionalità temporanea: il PDF viene letto ma i dati non vengono inseriti in Google Sheets.")
    uploaded_file = st.file_uploader("Seleziona PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        st.text("\n".join(page.extract_text() for page in reader.pages))
