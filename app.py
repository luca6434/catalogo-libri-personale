import streamlit as st
import sqlite3
import pandas as pd
from PyPDF2 import PdfReader
import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Gestione Catalogo Libri", page_icon="📘", layout="wide")

# --- CSS PERSONALIZZATO PER LOOK PROFESSIONALE ---
st.markdown("""
<style>
    /* Sfondo generale più morbido (stile dashboard) */
    .stApp {
        background-color: #f4f6f9;
    }
    /* Stile dei riquadri delle Metriche */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        border-left: 5px solid #0068c9;
    }
    /* Pulsanti primary */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
    }
    /* Personalizzazione delle Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
        font-size: 1.1rem;
    }
    /* Formattazione Box Form */
    div[data-testid="stForm"] {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        border: 1px solid #e1e4e8;
    }
</style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE DATABASE ---
def init_db():
    conn = sqlite3.connect('catalogo_libri.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS libri (
            isbn TEXT UNIQUE,
            titolo TEXT,
            nome_autore TEXT,
            cognome_autore TEXT,
            data_acquisto DATE,
            data_edizione DATE,
            tipologia TEXT,
            argomento TEXT,
            posizione TEXT,
            luogo_acquisto TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- FUNZIONI DATABASE ---
def aggiungi_libro(isbn, titolo, nome, cognome, d_acq, d_ed, tipo, arg, pos, luogo):
    conn = sqlite3.connect('catalogo_libri.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO libri VALUES (?,?,?,?,?,?,?,?,?,?)", 
                  (isbn, titolo, nome, cognome, d_acq, d_ed, tipo, arg, pos, luogo))
        conn.commit()
        success = True
        msg = "Libro inserito correttamente a sistema."
    except sqlite3.IntegrityError:
        success = False
        msg = "Errore: ISBN già censito a sistema. Operazione annullata."
    conn.close()
    return success, msg

def carica_dati():
    conn = sqlite3.connect('catalogo_libri.db')
    df = pd.read_sql_query("SELECT * FROM libri", conn)
    conn.close()
    return df

# --- HEADER DELL'APPLICAZIONE ---
st.title("📘 Sistema di Gestione Libreria")
st.markdown("Pannello di controllo per l'amministrazione e la catalogazione dei testi.")
st.divider()

# Creazione delle tab per la navigazione
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & Ricerca", "📝 Inserimento Manuale", "📂 Importazione Massiva (PDF)"])

# --- TAB 1: RICERCA E DASHBOARD ---
with tab1:
    df_libri = carica_dati()
    
    # Sezione Metriche (KPI)
    if not df_libri.empty:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric(label="Totale Volumi", value=len(df_libri))
        with col_m2:
            autori_unici = df_libri['cognome_autore'].nunique()
            st.metric(label="Autori in Catalogo", value=autori_unici)
        with col_m3:
            saggi_count = len(df_libri[df_libri['tipologia'] == 'Saggio'])
            st.metric(label="Totale Saggi", value=saggi_count)
        with col_m4:
            ultimo_inserimento = df_libri['data_acquisto'].max()
            st.metric(label="Ultimo acquisto", value=ultimo_inserimento)
    
    st.markdown("### 🔍 Esplora Catalogo")
    
    # Layout barra di ricerca e filtri
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("Ricerca testo libero (Titolo, Autore, ISBN, Zona...)", placeholder="Inizia a digitare per filtrare...").lower()
    with col_filter:
        filtro_tipo = st.selectbox("Filtra per Tipologia", ["Tutte le tipologie", "Manuale", "Saggio", "Romanzo", "Fumetto", "Altro"])
    
    if not df_libri.empty:
        # Applica filtri
        df_filtrato = df_libri.copy()
        
        if filtro_tipo != "Tutte le tipologie":
            df_filtrato = df_filtrato[df_filtrato['tipologia'] == filtro_tipo]
            
        if search_query:
            mask = (
                df_filtrato['titolo'].str.lower().str.contains(search_query) |
                df_filtrato['nome_autore'].str.lower().str.contains(search_query) |
                df_filtrato['cognome_autore'].str.lower().str.contains(search_query) |
                df_filtrato['isbn'].str.lower().str.contains(search_query) |
                df_filtrato['luogo_acquisto'].str.lower().str.contains(search_query)
            )
            df_filtrato = df_filtrato[mask]
            
        # Dataframe Avanzato e formattato
        st.dataframe(
            df_filtrato, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "isbn": st.column_config.TextColumn("ISBN", width="medium"),
                "titolo": st.column_config.TextColumn("Titolo", width="large"),
                "nome_autore": "Nome",
                "cognome_autore": "Cognome",
                "data_acquisto": st.column_config.DateColumn("Acquisto", format="DD/MM/YYYY"),
                "data_edizione": st.column_config.DateColumn("Edizione", format="DD/MM/YYYY"),
                "tipologia": "Tipologia",
                "argomento": "Argomento",
                "posizione": "Posizione",
                "luogo_acquisto": "Zona"
            }
        )
    else:
        st.info("💡 Il database è attualmente vuoto. Recati nella sezione 'Inserimento Manuale' per iniziare.")

# --- TAB 2: AGGIUNGI LIBRO (FORM) ---
with tab2:
    st.markdown("### 📝 Registrazione Nuovo Volume")
    st.markdown("Compila la scheda sottostante per aggiungere un nuovo libro all'archivio. I campi contrassegnati con l'asterisco (*) sono obbligatori.")
    
    with st.form("form_aggiunta", clear_on_submit=True):
        st.subheader("Dati Principali")
        col1, col2 = st.columns(2)
        with col1:
            isbn = st.text_input("Codice ISBN *")
            titolo = st.text_input("Titolo dell'opera *")
        with col2:
            nome_autore = st.text_input("Nome Autore")
            cognome_autore = st.text_input("Cognome Autore")
            
        st.divider()
        st.subheader("Dettagli Editoriali e Logistici")
        col3, col4, col5 = st.columns(3)
        with col3:
            tipologia = st.selectbox("Categoria", ["Manuale", "Saggio", "Romanzo", "Fumetto", "Altro"])
            argomento = st.text_input("Argomento / Materia")
        with col4:
            data_edizione = st.date_input("Data di Pubblicazione", datetime.date.today())
            data_acquisto = st.date_input("Data di Acquisizione", datetime.date.today())
        with col5:
            luogo_acquisto = st.selectbox("Circoscrizione di Acquisto", ["MI", "ME", "ST"])
            posizione = st.text_input("Posizione in Libreria (es. Scaffale 3)")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("➕ Salva nel Database", use_container_width=True)
        
        if submit:
            if not isbn or not titolo:
                st.error("⚠️ Attenzione: ISBN e Titolo sono campi obbligatori.")
            else:
                successo, messaggio = aggiungi_libro(
                    isbn, titolo, nome_autore, cognome_autore, 
                    str(data_acquisto), str(data_edizione), 
                    tipologia, argomento, posizione, luogo_acquisto
                )
                if successo:
                    st.success(f"✅ {messaggio}")
                else:
                    st.error(f"❌ {messaggio}")

# --- TAB 3: CARICA DA PDF ---
with tab3:
    st.markdown("### 📂 Importazione Documenti PDF")
    st.markdown("Strumento di parsing per caricare elenchi massivi o fatture d'acquisto in formato PDF.")
    
    col_pdf1, col_pdf2 = st.columns([1, 2])
    with col_pdf1:
        st.info("Istruzioni: Trascina il file nell'area designata. Il sistema analizzerà il contenuto testuale del documento.")
        uploaded_file = st.file_uploader("Seleziona File (.pdf)", type="pdf")
        
    with col_pdf2:
        if uploaded_file is not None:
            with st.spinner("Elaborazione del documento in corso..."):
                try:
                    reader = PdfReader(uploaded_file)
                    testo_estratto = ""
                    for page in reader.pages:
                        testo_estratto += page.extract_text() + "\n"
                        
                    st.success("Analisi completata con successo.")
                    with st.expander("Anteprima Testo Estratto (Raw Data)", expanded=True):
                        st.text(testo_estratto)
                except Exception as e:
                    st.error(f"Errore critico durante la lettura: {e}")
        else:
            st.markdown("*(L'anteprima del testo apparirà qui)*")