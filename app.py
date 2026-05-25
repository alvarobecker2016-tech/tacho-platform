import streamlit as st
import os
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA

# 1. Konfiguracja strony
st.set_page_config(page_title="Pocket DGSA & Tacho Ultimate", layout="wide")
st.title("🚚 Pocket DGSA & Tacho Ultimate")
st.caption("Wersja 3.0 Enterprise | ADR, Tacho, Pakiet Mobilności, CMR, Mocowanie Ładunków")

# 2. Inicjalizacja bazy RAG
@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    success = rag.load_existing_database()
    if success:
        return rag
    return None

rag_system = get_rag_system()

# 3. Zakładki
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "💬 Audytor AI", 
    "🛡️ Linia Obrony",
    "💰 Kalkulator Kar",
    "📊 ADR 1.1.3.6", 
    "📸 Skaner (OCR)", 
    "🗺️ GPS Granice", 
    "✍️ Wpisy Manualne", 
    "⛓️ Pasy (EN 12195)"
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

# --- ZAKŁADKA 2: LINIA OBRONY ---
with tab2:
    st.header("🛡️ Generator Oświadczeń (Art. 12)")
    opis_incydentu = st.text_area("Opisz sytuację awaryjną (np. brak parkingu, wypadek):", height=100)
    if st.button("⚖️ Wygeneruj Oświadczenie", type="primary", use_container_width=True):
        with st.spinner("Adwokat AI konstruuje linię obrony..."):
            odpowiedz = rag_system.generate_defense_statement(opis_incydentu)
            st.success("Dokument gotowy!")
            st.markdown(odpowiedz)

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
    st.write("Wybierz scenariusz, aby uzyskać instrukcje wpisu do tachografu z bazy wiedzy UE.")
    scenariusz = st.selectbox("Sytuacja kierowcy:", [
        "Przekroczenie granicy wewnętrznej UE", 
        "Wjazd na prom lub do pociągu (Tryb Promowy)", 
        "Przekroczenie granicy z krajem spoza UE (np. Szwajcaria)"
    ])
    if st.button("Wygeneruj instrukcję z ustawy", key="btn_granice"):
        with st.spinner("Szukam odpowiednich dyrektyw..."):
            odpowiedz = rag_system.ask(f"Jakie są dokładne obowiązki kierowcy dotyczące wpisu w tachografie w sytuacji: {scenariusz}? Kiedy dokładnie ma to zrobić?")
            st.info("Zalecenie z aktów prawnych:")
            st.markdown(odpowiedz)

# --- ZAKŁADKA 7: WPISY MANUALNE ---
with tab7:
    st.header("✍️ Asystent Wpisów Manualnych")
    st.write("Zbuduj scenariusz przerwy kierowcy, a asystent podpowie, jak uzupełnić lukę na karcie.")
    c1, c2 = st.columns(2)
    with c1:
        co_robil = st.selectbox("Co kierowca robił podczas braku karty w tacho?", ["Odpoczynek (Urlop/Weekend)", "Inna praca (w bazie/magazynie)", "Dojazd do ciężarówki pociągiem/autem"])
    with c2:
        kraj_rozpoczecia = st.text_input("Kraj rozpoczęcia po przerwie (np. PL, DE):", value="PL")
    
    if st.button("Zapytaj eksperta o procedurę", key="btn_manual"):
        with st.spinner("Opracowuję instrukcję wpisu..."):
            odpowiedz = rag_system.ask(f"Kierowca wyciągnął kartę, a podczas przerwy robił: {co_robil}. Kraj rozpoczęcia to {kraj_rozpoczecia}. Jak krok po kroku zrobić wpis manualny w tachografie cyfrowym zgodnie z Rozporządzeniem 165/2014?")
            st.success("Procedura:")
            st.markdown(odpowiedz)

# --- ZAKŁADKA 8: PASY EN 12195 ---
with tab8:
    st.header("⛓️ Kalkulator Siły Mocowania (Pasy Dociskowe)")
    st.info("Kalkulacja oparta o wzory fizyczne z normy EN 12195-1 (Mocowanie przez docisk).")
    
    col_a, col_b = st.columns(2)
    with col_a:
        waga = st.number_input("Waga ładunku (kg)", min_value=100, value=2500, step=100)
        stf = st.number_input("Siła naciągu pasa (STF w daN) - sprawdź na niebieskiej metce!", min_value=100, value=500, step=50)
    with col_b:
        tarcie_nazwa = st.selectbox("Powierzchnia styku (Współczynnik tarcia)", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
        tarcie = WSPOLCZYNNIKI_TARCIA[tarcie_nazwa]
        kat = st.slider("Kąt nachylenia pasa (alfa w stopniach)", min_value=10, max_value=90, value=60)
        
    if st.button("🧮 Oblicz wymaganą ilość pasów", type="primary"):
        wynik = oblicz_pasy_docisk(waga, tarcie, stf, kat)
        if "error" in wynik:
            st.error(wynik["error"])
        else:
            st.metric(label="MINIMALNA LICZBA PASÓW", value=wynik["pasy"])
            st.write(f"📝 **Szczegóły:** {wynik['wiadomosc']}")