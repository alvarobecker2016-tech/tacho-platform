import streamlit as st
import os
from openai import OpenAI
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
import auth_db
from pdf_generator import create_defense_pdf

# 1. Konfiguracja strony - Ukryty pasek boczny na start (jak w aplikacji mobilnej)
st.set_page_config(page_title="Pocket AI", page_icon="✨", layout="centered", initial_sidebar_state="collapsed")

# --- CSS: MAGICZNY MINIMALIZM ---
st.markdown("""
<style>
/* Ukrycie domyślnych pasków Streamlit */
header {visibility: hidden;}
footer {visibility: hidden;}

/* Zrobienie miejsca na dole, by czat nie zasłaniał treści */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 5rem !important;
}

/* Wygładzenie przycisków */
.stButton>button {
    border-radius: 20px;
    font-weight: 600;
    border: none;
    transition: all 0.2s;
}
.stButton>button:hover {
    transform: scale(1.02);
}

/* Centralne powitanie - stylizacja */
.welcome-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 40vh;
    text-align: center;
}
.welcome-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    background: -webkit-linear-gradient(45deg, #3B82F6, #8B5CF6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.welcome-text {
    font-size: 2.2rem;
    font-weight: 500;
    color: #FFFFFF;
}
</style>
""", unsafe_allow_html=True)

# Inicjalizacja bazy użytkowników
auth_db.init_db()

# --- SYSTEM LOGOWANIA ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if not st.session_state.logged_in:
    st.markdown("<div class='welcome-container'><div class='welcome-icon'>✨</div><div class='welcome-text'>Pocket DGSA & Tacho</div><p style='color: #9CA3AF; margin-top: 10px;'>Twój inteligentny asystent transportowy</p></div>", unsafe_allow_html=True)
    
    tab_log, tab_reg = st.tabs(["Logowanie", "Rejestracja"])
    with tab_log:
        log_user = st.text_input("Identyfikator")
        log_pass = st.text_input("Hasło", type="password")
        if st.button("Wejdź", type="primary", use_container_width=True):
            user_info = auth_db.verify_login(log_user, log_pass)
            if user_info:
                st.session_state.logged_in = True
                st.session_state.user_data = user_info
                st.rerun()
            else:
                st.error("Błędny identyfikator lub hasło.")
                
    with tab_reg:
        typ_konta = st.radio("Typ profilu:", ["Kierowca Indywidualny", "Firma Transportowa"])
        reg_user = st.text_input("Nowy identyfikator")
        reg_pass = st.text_input("Nowe hasło", type="password")
        reg_name = st.text_input("Twoje Imię (np. Rafał)")
        reg_comp = st.text_input("Nazwa Firmy") if typ_konta == "Firma Transportowa" else "Kierowca Indywidualny"
        
        if st.button("Utwórz profil", use_container_width=True):
            if reg_user and reg_pass and reg_name:
                if auth_db.register_user(reg_user, reg_pass, reg_name, reg_comp):
                    st.success("Konto gotowe. Możesz się zalogować.")
                else:
                    st.error("Użytkownik już istnieje.")
            else:
                st.warning("Wypełnij wymagane pola.")
    st.stop()

# --- ŁADOWANIE SILNIKA ---
@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    if rag.load_existing_database():
        return rag
    return None

rag_system = get_rag_system()

# --- INTENT ROUTER ---
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

# --- PANEL BOCZNY (Ukryty pod ikoną w lewym górnym rogu) ---
user_info = st.session_state.user_data
imie_uzytkownika = user_info['full_name'].split()[0] # Wyciągamy samo imię

with st.sidebar:
    st.markdown(f"### 👤 {user_info['full_name']}")
    st.caption(f"Profil: {user_info['company_name']}")
    st.divider()
    
    st.markdown("**Ustawienia Asystenta**")
    jezyk_pism = st.selectbox("Język pism urzędowych:", ["Niemiecki (BAG)", "Polski (ITD)", "Angielski (DVSA)", "Francuski (DREAL)"])
    
    st.divider()
    st.markdown("**Skaner Dowodów (Zdjęcie)**")
    uploaded_file = st.file_uploader("Wgraj zdjęcie", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if uploaded_file and st.button("Wyślij do AI", type="primary"):
        with st.spinner("Analizuję obraz..."):
            odczyt_ocr = rag_system.read_image(uploaded_file.read())
            st.session_state.messages.append({"role": "user", "content": f"[ZESKANOWANY DOKUMENT]\n{odczyt_ocr}\n\nCo to za dokument i czy są błędy?"})
            st.rerun()

    st.divider()
    if st.button("Wyloguj", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

# --- GŁÓWNY INTERFEJS ---

# Inicjalizacja historii i widoków
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_adr" not in st.session_state: st.session_state.show_adr = False
if "show_pasy" not in st.session_state: st.session_state.show_pasy = False

# MAGICZNY EKRAN POWITALNY (Tylko gdy czat jest pusty i nie włączono kalkulatorów)
if not st.session_state.messages and not st.session_state.show_adr and not st.session_state.show_pasy:
    st.markdown(f"""
    <div class='welcome-container'>
        <div class='welcome-icon'>✨</div>
        <div class='welcome-text'>W czym mogę pomóc, {imie_uzytkownika}?</div>
    </div>
    """, unsafe_allow_html=True)

# Kalkulatory (pojawiają się tylko, gdy AI je wywoła)
if st.session_state.show_adr:
    st.markdown("### 📊 Kalkulator ADR (Wywołany przez asystenta)")
    if "adr_loads" not in st.session_state: st.session_state.adr_loads = []
    c1, c2, c3 = st.columns([2, 1, 1])
    wybrany_un = c1.selectbox("Kod UN", options=list(TABELA_A.keys()))
    ilosc = c2.number_input("Ilość", min_value=1, value=100)
    if c3.button("Dodaj"):
        st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
    if st.session_state.adr_loads:
        wynik = oblicz_1136(st.session_state.adr_loads)
        if "error" not in wynik:
            st.table([{"UN": i['un'], "Ilość": i['ilosc'], "Punkty": int(i['punkty'])} for i in wynik["szczegoly"]])
            st.info(f"Suma: {int(wynik['suma_punktow'])} / 1000")
        if st.button("Zamknij kalkulator"):
            st.session_state.show_adr = False
            st.session_state.adr_loads = []
            st.rerun()

if st.session_state.show_pasy:
    st.markdown("### ⛓️ Fizyka Docisku (Wywołana przez asystenta)")
    c1, c2 = st.columns(2)
    waga = c1.number_input("Waga (kg)", value=2500, step=100)
    stf = c1.number_input("STF pasa (daN)", value=500, step=50)
    tarcie = c2.selectbox("Tarcie", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
    kat = c2.slider("Kąt (alfa)", 10, 90, 60)
    if st.button("Oblicz", type="primary"):
        wynik = oblicz_pasy_docisk(waga, WSPOLCZYNNIKI_TARCIA[tarcie], stf, kat)
        if "error" not in wynik:
            st.success(f"Minimalna liczba pasów: {wynik['pasy']}")
    if st.button("Zamknij kalkulator"):
        st.session_state.show_pasy = False
        st.rerun()

# Wyświetlanie historii czatu
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("pdf_bytes"):
            st.download_button("📄 POBIERZ DOKUMENT PDF", data=message["pdf_bytes"], file_name="Oswiadczenie.pdf", mime="application/pdf", key=str(hash(message["content"])))

# Główne pole na dole (Zawsze przyklejone do dołu przez Streamlit)
if user_query := st.chat_input("Pytaj, zlecaj analizy i generuj dokumenty..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)
        
    with st.chat_message("assistant"):
        if not rag_system:
            st.error("Brak połączenia z bazą prawną.")
        else:
            with st.spinner("Myślę..."):
                intencja = classify_intent(user_query)
                pdf_bytes_to_save = None
                
                if "OBRONA" in intencja:
                    response = rag_system.generate_defense_statement(user_query, jezyk_pism)
                    pdf_bytes_to_save = create_defense_pdf(response, user_info['full_name'], user_info['company_name'])
                    st.markdown(response)
                    st.download_button("📄 POBIERZ DOKUMENT PDF", data=pdf_bytes_to_save, file_name="Oswiadczenie.pdf", mime="application/pdf")
                    
                elif "KARY" in intencja:
                    response = rag_system.calculate_penalty(user_query)
                    st.markdown(response)
                    
                elif "ADR" in intencja:
                    st.session_state.show_adr = True
                    st.session_state.show_pasy = False
                    response = "Uruchomiłem kalkulator ADR powyżej. Wprowadź ładunek."
                    st.markdown(response)
                    st.rerun()
                    
                elif "PASY" in intencja:
                    st.session_state.show_pasy = True
                    st.session_state.show_adr = False
                    response = "Uruchomiłem moduł inżynieryjny EN-12195 powyżej. Sprawdź pasy."
                    st.markdown(response)
                    st.rerun()
                    
                else:
                    response = rag_system.ask(user_query)
                    st.markdown(response)
                    
            st.session_state.messages.append({"role": "assistant", "content": response, "pdf_bytes": pdf_bytes_to_save})