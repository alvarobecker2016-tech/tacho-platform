import streamlit as st
import os
from openai import OpenAI
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
import auth_db
from pdf_generator import create_defense_pdf

# 1. Konfiguracja strony
st.set_page_config(page_title="Pocket DGSA", page_icon="🛣️", layout="centered", initial_sidebar_state="collapsed")

# --- CSS: CZERŃ, BIEL I CZERWIEŃ ---
st.markdown("""
<style>
header {visibility: hidden;}
footer {visibility: hidden;}
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 5rem !important;
}
.stButton>button {
    border-radius: 8px;
    font-weight: bold;
    border: none;
    transition: all 0.2s;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(211, 47, 47, 0.4);
}
.welcome-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin-top: 5vh;
    margin-bottom: 3vh;
    text-align: center;
}

/* ZMIANA: Puste Czerwone Kółko (Usunięto zdjęcie) */
.highway-logo-container {
    width: 140px;
    height: 140px;
    border-radius: 50%;
    border: 3px solid #D32F2F; /* Czerwony pierścień */
    box-shadow: 0 0 25px rgba(211, 47, 47, 0.3);
    margin-bottom: 1.5rem;
    background-color: transparent; /* Puste w środku */
}

.welcome-text {
    font-size: 2.2rem;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: 1px;
}

/* Pasek boczny (Sidebar) - kolory tekstu */
[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)

auth_db.init_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if not st.session_state.logged_in:
    # Ekran powitalny przy logowaniu
    st.markdown("""
    <div class='welcome-container'>
        <div class='highway-logo-container'></div> <div class='welcome-text'>POCKET DGSA & TACHO</div>
        <p style='color: #A0A0A0; font-size: 1.1rem; margin-top: 5px;'>Profesjonalny System Prawny B2B</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab_log, tab_reg = st.tabs(["LOGOWANIE", "REJESTRACJA"])
    with tab_log:
        log_user = st.text_input("Adres Email / Identyfikator")
        log_pass = st.text_input("Hasło", type="password")
        if st.button("WEJDŹ DO SYSTEMU", type="primary", use_container_width=True):
            user_info = auth_db.verify_login(log_user, log_pass)
            if user_info:
                st.session_state.logged_in = True
                st.session_state.user_data = user_info
                st.rerun()
            else:
                st.error("Błędny identyfikator lub hasło.")
                
    with tab_reg:
        typ_konta = st.radio("Rodzaj subskrypcji:", ["Kierowca Indywidualny", "Firma Transportowa"])
        reg_user = st.text_input("Nowy Email / Identyfikator")
        reg_pass = st.text_input("Nowe hasło", type="password")
        reg_name = st.text_input("Imię i Nazwisko (do pism)")
        reg_comp = st.text_input("Nazwa Firmy (Opcjonalnie)") if typ_konta == "Firma Transportowa" else "Kierowca Indywidualny"
        
        if st.button("UTWÓRZ KONTO TESTOWE", use_container_width=True):
            if reg_user and reg_pass and reg_name:
                if auth_db.register_user(reg_user, reg_pass, reg_name, reg_comp):
                    st.success("Konto utworzone. Przejdź do logowania.")
                else:
                    st.error("Użytkownik już istnieje.")
            else:
                st.warning("Wypełnij wymagane pola.")
    st.stop()

@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    if rag.load_existing_database():
        return rag
    return None

rag_system = get_rag_system()

def classify_intent(text):
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Jesteś routerem AI. Zwróć jedno słowo: OBRONA, KARY, ADR, PASY lub OGOLNE."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip().upper()
    except:
        return "OGOLNE"

user_info = st.session_state.user_data
imie_uzytkownika = user_info['full_name'].split()[0]

with st.sidebar:
    st.markdown(f"### {user_info['full_name']}")
    st.caption(f"Status: {user_info['company_name']}")
    st.divider()
    
    st.markdown("**KONFIGURACJA PISM**")
    jezyk_pism = st.selectbox("Wybór organu kontrolnego:", ["Niemiecki (BAG)", "Polski (ITD)", "Angielski (DVSA)", "Francuski (DREAL)"])
    
    st.divider()
    if st.button("WYLOGUJ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

if "messages" not in st.session_state: st.session_state.messages = []
if "show_adr" not in st.session_state: st.session_state.show_adr = False
if "show_pasy" not in st.session_state: st.session_state.show_pasy = False

# MAGICZNY EKRAN POWITALNY (Tylko gdy czat jest pusty i nie włączono kalkulatorów)
if not st.session_state.messages and not st.session_state.show_adr and not st.session_state.show_pasy:
    st.markdown(f"""
    <div class='welcome-container'>
        <div class='highway-logo-container'></div> <div class='welcome-text'>GOTOWY DO TRASY, {imie_uzytkownika.upper()}?</div>
        <p style='color: #707070;'>Wpisz naruszenie, poproś o pismo lub użyj przycisku '📎' poniżej, aby wrzucić dokument.</p>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.show_adr:
    st.markdown("### 🛑 KALKULATOR ADR")
    if "adr_loads" not in st.session_state: st.session_state.adr_loads = []
    c1, c2, c3 = st.columns([2, 1, 1])
    wybrany_un = c1.selectbox("Kod UN", options=list(TABELA_A.keys()))
    ilosc = c2.number_input("Ilość", min_value=1, value=100)
    if c3.button("DODAJ"):
        st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
    if st.session_state.adr_loads:
        wynik = oblicz_1136(st.session_state.adr_loads)
        if "error" not in wynik:
            st.table([{"UN": i['un'], "Ilość": i['ilosc'], "Punkty": int(i['punkty'])} for i in wynik["szczegoly"]])
            st.info(f"SUMA PUNKTÓW: {int(wynik['suma_punktow'])} / 1000")
        if st.button("ZAMKNIJ MODUŁ"):
            st.session_state.show_adr = False
            st.session_state.adr_loads = []
            st.rerun()

if st.session_state.show_pasy:
    st.markdown("### ⛓️ FIZYKA DOCISKU (EN-12195)")
    c1, c2 = st.columns(2)
    waga = c1.number_input("Waga ładunku (kg)", value=2500, step=100)
    stf = c1.number_input("Naciąg pasa STF (daN)", value=500, step=50)
    tarcie = c2.selectbox("Powierzchnia styku", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
    kat = c2.slider("Kąt mocowania (stopnie)", 10, 90, 60)
    if st.button("OBLICZ MINIMUM PASÓW", type="primary"):
        wynik = oblicz_pasy_docisk(waga, WSPOLCZYNNIKI_TARCIA[tarcie], stf, kat)
        if "error" not in wynik:
            st.success(f"Wymagana ilość pasów: {wynik['pasy']}")
    if st.button("ZAMKNIJ MODUŁ"):
        st.session_state.show_pasy = False
        st.rerun()

# Wyświetlanie czatu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("pdf_bytes"):
            st.download_button("⬇️ POBIERZ DOKUMENT PDF", data=message["pdf_bytes"], file_name="Oswiadczenie.pdf", mime="application/pdf", key=str(hash(message["content"])))

# --- NOWOŚĆ: POPUP ZAŁĄCZNIKÓW TUŻ PRZY PASKU CZATU ---
with st.popover("📎 Mikrofon / Aparat / Pliki"):
    st.markdown("**Dodaj dowód lub naruszenie:**")
    
    uploaded_file = st.file_uploader("Wrzuć zdjęcie (Tacho, CMR, Mandat)", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if uploaded_file and st.button("PRZEKAŻ DO ANALIZY AI", type="primary", use_container_width=True):
        with st.spinner("Ekstrakcja danych ze zdjęcia..."):
            odczyt_ocr = rag_system.read_image(uploaded_file.read())
            st.session_state.messages.append({"role": "user", "content": f"[SKAN DOKUMENTU]\n{odczyt_ocr}\n\nWykonaj pełny audyt prawny tego dokumentu."})
            st.rerun()
    
    st.warning("Obsługa mikrofonu/głosu wymaga dodatkowych modułów.")

# Główny pasek tekstowy (Czat)
if user_query := st.chat_input("Zgłoś problem lub poproś o pismo..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
        
    with st.chat_message("assistant"):
        if not rag_system:
            st.error("Brak połączenia z systemem prawnym.")
        else:
            with st.spinner("Przetwarzanie danych..."):
                intencja = classify_intent(user_query)
                pdf_bytes_to_save = None
                
                if "OBRONA" in intencja:
                    response = rag_system.generate_defense_statement(user_query, jezyk_pism)
                    pdf_bytes_to_save = create_defense_pdf(response, user_info['full_name'], user_info['company_name'])
                    st.markdown(response)
                    st.download_button("⬇️ POBIERZ WYGENEROWANY DOKUMENT PDF", data=pdf_bytes_to_save, file_name="Oswiadczenie.pdf", mime="application/pdf")
                    
                elif "KARY" in intencja:
                    response = rag_system.calculate_penalty(user_query)
                    st.markdown(response)
                    
                elif "ADR" in intencja:
                    st.session_state.show_adr = True
                    st.session_state.show_pasy = False
                    response = "Uruchomiono moduł ADR powyżej."
                    st.markdown(response)
                    st.rerun()
                    
                elif "PASY" in intencja:
                    st.session_state.show_pasy = True
                    st.session_state.show_adr = False
                    response = "Uruchomiono kalkulator mocowania ładunków powyżej."
                    st.markdown(response)
                    st.rerun()
                    
                else:
                    response = rag_system.ask(user_query)
                    st.markdown(response)
                    
            st.session_state.messages.append({"role": "assistant", "content": response, "pdf_bytes": pdf_bytes_to_save})