import streamlit as st
import os
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
import auth_db
from pdf_generator import create_defense_pdf

# 1. Konfiguracja strony musi być pierwsza!
st.set_page_config(page_title="Pocket DGSA & Tacho Ultimate", layout="wide")

# Inicjalizacja bazy użytkowników
auth_db.init_db()

# --- SYSTEM LOGOWANIA I REJESTRACJI ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if not st.session_state.logged_in:
    st.title("🔐 Platforma Enterprise dla Transportu")
    st.write("Witaj w systemie. Zaloguj się, aby uzyskać dostęp do panelu audytu i zarządzania.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_log, tab_reg = st.tabs(["Logowanie", "Nowe Konto"])
        
        # LOGOWANIE
        with tab_log:
            log_user = st.text_input("Nazwa użytkownika")
            log_pass = st.text_input("Hasło", type="password")
            if st.button("Zaloguj się", type="primary", use_container_width=True):
                user_info = auth_db.verify_login(log_user, log_pass)
                if user_info:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_info
                    st.rerun()
                else:
                    st.error("❌ Błędny login lub hasło!")
                    
        # REJESTRACJA B2B & B2C
        with tab_reg:
            st.info("Konto dla firm transportowych oraz niezależnych kierowców zawodowych.")
            
            typ_konta = st.radio("Wybierz typ konta:", ["Kierowca Indywidualny", "Firma Transportowa (Przewoźnik)"])
            
            reg_user = st.text_input("Wybierz login")
            reg_pass = st.text_input("Wybierz hasło", type="password")
            reg_name = st.text_input("Imię i Nazwisko (do dokumentów PDF)")
            
            # Jeśli wybrano firmę, pokazujemy pole. Jeśli nie, automatycznie w tle przypisujemy status.
            if typ_konta == "Firma Transportowa (Przewoźnik)":
                reg_comp = st.text_input("Nazwa Firmy Przewozowej")
            else:
                reg_comp = "Kierowca Indywidualny"
                
            if st.button("Zarejestruj się", type="secondary", use_container_width=True):
                if reg_user and reg_pass and reg_name:
                    if typ_konta == "Firma Transportowa (Przewoźnik)" and not reg_comp:
                        st.warning("Podaj nazwę firmy przewozowej.")
                    else:
                        if auth_db.register_user(reg_user, reg_pass, reg_name, reg_comp):
                            st.success("✅ Konto utworzone pomyślnie! Przejdź do zakładki 'Logowanie'.")
                        else:
                            st.error("⚠️ Użytkownik o takiej nazwie już istnieje! Wybierz inny login.")
                else:
                    st.warning("Wypełnij przynajmniej Login, Hasło oraz Imię i Nazwisko.")
    
    st.stop() # Ta linijka zatrzymuje resztę kodu dla niezalogowanych!

# --- PANEL BOCZNY (PO ZALOGOWANIU) ---
user_info = st.session_state.user_data
with st.sidebar:
    st.success(f"👤 Zalogowano jako: **{user_info['full_name']}**")
    
    # Inteligentne wyświetlanie profilu B2B / B2C
    if user_info['company_name'] == "Kierowca Indywidualny":
        st.info("🚛 Profil: Kierowca Indywidualny")
    else:
        st.info(f"🏢 Firma: {user_info['company_name']}")
        
    st.divider()
    if st.button("🚪 Wyloguj się", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

# --- GŁÓWNA APLIKACJA ---
st.title("🚚 Pocket DGSA & Tacho Ultimate")
st.caption("Platforma Poziomu Enterprise | Zalogowany użytkownik posiada dostęp Premium")

@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    if rag.load_existing_database():
        return rag
    return None

rag_system = get_rag_system()

# Zakładki
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "💬 Audytor AI", "🛡️ Linia Obrony (PDF)", "💰 Kalkulator Kar", "📊 ADR 1.1.3.6", 
    "📸 Skaner (OCR)", "🗺️ GPS Granice", "✍️ Wpisy Manualne", "⛓️ Pasy (EN 12195)"
])

# --- ZAKŁADKA 1: AUDYTOR AI ---
with tab1:
    st.header("Swobodny Audyt Prawny")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if user_query := st.chat_input("Zadaj pytanie prawne...", key="audytor_input"):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("assistant"):
            if rag_system:
                with st.spinner("Ekspert AI analizuje akty prawne..."):
                    response = rag_system.ask(user_query)
            else:
                response = "❌ Błąd bazy danych."
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- ZAKŁADKA 2: LINIA OBRONY Z EKSPORTEM PDF ---
with tab2:
    st.header("🛡️ Generator Oświadczeń (Art. 12)")
    
    # Indywidualny komunikat o generowaniu
    naglowek = f"**{user_info['full_name']}**"
    if user_info['company_name'] != "Kierowca Indywidualny":
        naglowek += f" ({user_info['company_name']})"
    else:
        naglowek += " (Kierowca Niezależny)"
        
    st.info(f"Oświadczenie zostanie wygenerowane oficjalnie na dane: {naglowek}")
    
    opis_incydentu = st.text_area("Opisz sytuację awaryjną do Adwokata (np. brak parkingu na A2):", height=100)
    
    if "pdf_ready" not in st.session_state:
        st.session_state.pdf_ready = False
        st.session_state.pdf_bytes = None
        st.session_state.pdf_text = ""

    if st.button("⚖️ Wygeneruj Oświadczenie", type="primary", use_container_width=True):
        if not opis_incydentu:
            st.warning("Uzupełnij opis incydentu przed wygenerowaniem pisma.")
        else:
            with st.spinner("Adwokat AI konstruuje linię obrony..."):
                odpowiedz = rag_system.generate_defense_statement(opis_incydentu)
                pdf_data = create_defense_pdf(odpowiedz, user_info['full_name'], user_info['company_name'])
                
                st.session_state.pdf_text = odpowiedz
                st.session_state.pdf_bytes = pdf_data
                st.session_state.pdf_ready = True
                st.success("Dokument wygenerowany z sukcesem!")

    if st.session_state.pdf_ready:
        st.markdown(st.session_state.pdf_text)
        st.divider()
        st.download_button(
            label="📄 POBIERZ DOKUMENT PDF (GOTOWY DO DRUKU)",
            data=st.session_state.pdf_bytes,
            file_name=f"Oswiadczenie_{user_info['full_name'].replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

# --- ZAKŁADKA 3: KALKULATOR KAR ---
with tab3:
    st.header("💰 Wycena Ryzyka i Taryfikator ITD/BAG")
    opis_naruszenia = st.text_area("Opisz naruszenie (np. brak wpisu manualnego):", height=100)
    if st.button("🚨 Rozpocznij Audyt Finansowy", type="primary", use_container_width=True):
        with st.spinner("Inspektor AI ocenia kary..."):
            odpowiedz = rag_system.calculate_penalty(opis_naruszenia)
            st.error("Raport z wyceną wygenerowany!")
            st.markdown(odpowiedz)

# --- ZAKŁADKA 4: KALKULATOR ADR ---
with tab4:
    st.header("📊 Kalkulator Wyłączenia ADR (1.1.3.6)")
    if "adr_loads" not in st.session_state:
        st.session_state.adr_loads = []
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        wybrany_un = st.selectbox("Towar (UN)", options=list(TABELA_A.keys()), format_func=lambda x: f"UN {x} - {TABELA_A[x]['nazwa']}")
    with c2:
        ilosc = st.number_input("Ilość (L/kg)", min_value=1, value=100)
    with c3:
        st.write("##")
        if st.button("➕ Dodaj"):
            st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
            st.toast("Dodano do ładunku!")
    if st.session_state.adr_loads:
        wynik = oblicz_1136(st.session_state.adr_loads)
        if "error" not in wynik:
            st.table([{"UN": i['un'], "Ilość": i['ilosc'], "Punkty": int(i['punkty'])} for i in wynik["szczegoly"]])
            suma_pkt = wynik["suma_punktow"]
            st.metric("SUMA PUNKTÓW", f"{int(suma_pkt)} / 1000")
            if wynik["zwolniony"]:
                st.success("✅ TRANSPORT ZWOLNIONY (Brak pełnego ADR)")
            else:
                st.error("🚨 PEŁNY ADR WYMAGANY")
        if st.button("🗑️ Wyczyść"):
            st.session_state.adr_loads = []
            st.rerun()

# --- ZAKŁADKA 5: SKANER OCR ---
with tab5:
    st.header("📸 Skaner Dowodów (Wydruki Tacho / CMR)")
    uploaded_file = st.file_uploader("Wybierz zdjęcie", type=["jpg", "png"])
    if uploaded_file and st.button("🔍 Skanuj i Analizuj", type="primary"):
        with st.spinner("Ekstrakcja OCR i audyt prawny..."):
            tekst = rag_system.read_image(uploaded_file.read())
            st.expander("Surowe dane (Raw)").text(tekst)
            analiza = rag_system.ask(f"Przeanalizuj pod kątem zgodności z prawem:\n{tekst}")
            st.markdown(f"### ⚖️ Wynik:\n{analiza}")

# --- ZAKŁADKA 6: GRANICE GPS ---
with tab6:
    st.header("🗺️ Granice i Promy (Pakiet Mobilności)")
    scenariusz = st.selectbox("Sytuacja kierowcy:", ["Przekroczenie granicy wewnętrznej UE", "Wjazd na prom lub do pociągu", "Granica z krajem spoza UE"])
    if st.button("Wygeneruj instrukcję z ustawy"):
        with st.spinner("Szukam dyrektyw..."):
            st.markdown(rag_system.ask(f"Jakie są obowiązki w tachografie: {scenariusz}?"))

# --- ZAKŁADKA 7: WPISY MANUALNE ---
with tab7:
    st.header("✍️ Asystent Wpisów Manualnych")
    c1, c2 = st.columns(2)
    with c1:
        co_robil = st.selectbox("Co kierowca robił?", ["Odpoczynek", "Inna praca", "Dojazd"])
    with c2:
        kraj_rozpoczecia = st.text_input("Kraj rozpoczęcia:", value="PL")
    if st.button("Zapytaj o procedurę"):
        with st.spinner("Opracowuję instrukcję wpisu..."):
            st.markdown(rag_system.ask(f"Kierowca robił: {co_robil}. Kraj startu to {kraj_rozpoczecia}. Jak zrobić wpis manualny?"))

# --- ZAKŁADKA 8: PASY EN 12195 ---
with tab8:
    st.header("⛓️ Kalkulator Siły Mocowania (Pasy Dociskowe)")
    col_a, col_b = st.columns(2)
    with col_a:
        waga = st.number_input("Waga (kg)", min_value=100, value=2500, step=100)
        stf = st.number_input("STF pasa (daN)", min_value=100, value=500, step=50)
    with col_b:
        tarcie_nazwa = st.selectbox("Tarcie", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
        kat = st.slider("Kąt (alfa)", min_value=10, max_value=90, value=60)
    if st.button("🧮 Oblicz pasy", type="primary"):
        wynik = oblicz_pasy_docisk(waga, WSPOLCZYNNIKI_TARCIA[tarcie_nazwa], stf, kat)
        if "error" in wynik:
            st.error(wynik["error"])
        else:
            st.metric(label="MINIMALNA LICZBA PASÓW", value=wynik["pasy"])
            st.write(wynik['wiadomosc'])