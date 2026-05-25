import streamlit as st
import os
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
import auth_db
from pdf_generator import create_defense_pdf

# 1. Konfiguracja strony musi być pierwsza!
st.set_page_config(page_title="Pocket DGSA & Tacho Ultimate", page_icon="🚚", layout="wide")

# --- WSTRZYKNIĘCIE ZAAWANSOWANEGO KODU CSS (DESIGN ENTERPRISE) ---
st.markdown("""
<style>
/* Ukrycie domyślnego, niepotrzebnego paska na samej górze */
header {visibility: hidden;}

/* Stylizacja głównego kontenera, by nie dotykał krawędzi ekranu */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
}

/* Eleganckie cienie i animacje dla przycisków głównych */
.stButton>button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    border: none;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
}

/* Przebudowa Zakładek (Tabs) - Nowoczesny wygląd */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    border-radius: 8px 8px 0px 0px;
    padding: 10px 20px;
    background-color: #E2E8F0;
    color: #475569;
    font-weight: 600;
    border: none;
}
.stTabs [aria-selected="true"] {
    background-color: #004B87 !important;
    color: white !important;
    box-shadow: 0 -3px 6px rgba(0,0,0,0.1);
}

/* Zaokrąglone pola tekstowe z eleganckim obramowaniem */
.stTextArea textarea, .stTextInput input {
    border-radius: 8px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #004B87;
    box-shadow: 0 0 0 2px rgba(0, 75, 135, 0.2);
}

/* Kolor tekstu dla jasnego paska bocznego (dzięki config.toml tło będzie ciemne, więc tekst musi być biały) */
[data-testid="stSidebar"] {
    border-right: none;
    box-shadow: 2px 0 10px rgba(0,0,0,0.1);
}
[data-testid="stSidebar"] * {
    color: #F8FAFC !important;
}
</style>
""", unsafe_allow_html=True)

# Inicjalizacja bazy użytkowników
auth_db.init_db()

# --- SYSTEM LOGOWANIA I REJESTRACJI ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if not st.session_state.logged_in:
    # Ekran powitalny w nowym designie
    st.markdown("<h1 style='text-align: center; color: #004B87; padding-bottom: 20px;'>🚚 Pocket DGSA & Tacho Ultimate</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #475569; padding-bottom: 40px;'>Centralna Platforma Compliance dla Transportu Drogowego</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_log, tab_reg = st.tabs(["🔐 Logowanie do systemu", "📝 Utwórz nowe konto"])
        
        with tab_log:
            st.markdown("### Wprowadź dane uwierzytelniające")
            log_user = st.text_input("Identyfikator użytkownika (Login)")
            log_pass = st.text_input("Hasło dostępu", type="password")
            st.write("---")
            if st.button("Autoryzuj dostęp", type="primary", use_container_width=True):
                user_info = auth_db.verify_login(log_user, log_pass)
                if user_info:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_info
                    st.rerun()
                else:
                    st.error("❌ Błędny identyfikator lub hasło.")
                    
        with tab_reg:
            st.info("Konto dla firm transportowych oraz niezależnych kierowców zawodowych.")
            typ_konta = st.radio("Wybierz typ profilu operacyjnego:", ["Kierowca Indywidualny", "Firma Transportowa (Przewoźnik)"])
            reg_user = st.text_input("Wybierz identyfikator (Login)")
            reg_pass = st.text_input("Wybierz hasło", type="password")
            reg_name = st.text_input("Imię i Nazwisko (do oficjalnych dokumentów PDF)")
            
            if typ_konta == "Firma Transportowa (Przewoźnik)":
                reg_comp = st.text_input("Pełna Nazwa Firmy Przewozowej")
            else:
                reg_comp = "Kierowca Indywidualny"
                
            st.write("---")
            if st.button("Zarejestruj profil", type="secondary", use_container_width=True):
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
    st.stop()

# --- PANEL BOCZNY ---
user_info = st.session_state.user_data
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white;'>Panel Operacyjny</h2>", unsafe_allow_html=True)
    st.write("---")
    st.success(f"👤 Zalogowano: \n**{user_info['full_name']}**")
    if user_info['company_name'] == "Kierowca Indywidualny":
        st.info("🚛 Profil: Niezależny")
    else:
        st.info(f"🏢 Firma: \n{user_info['company_name']}")
    st.write("---")
    if st.button("🚪 Wyloguj bezpiecznie", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

st.title("🚚 Pocket DGSA & Tacho Ultimate")
st.caption("Platforma Poziomu Enterprise | Połączenie szyfrowane | Aktywny silnik AI Multilanguage")

@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    if rag.load_existing_database():
        return rag
    return None

rag_system = get_rag_system()

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "💬 Audytor AI", "🛡️ Linia Obrony (PDF)", "💰 Kalkulator Kar", "📊 ADR 1.1.3.6", 
    "📸 Skaner (OCR)", "🗺️ GPS Granice", "✍️ Wpisy Manualne", "⛓️ Pasy (EN 12195)"
])

# --- ZAKŁADKA 1: AUDYTOR AI ---
with tab1:
    st.header("Swobodny Audyt Prawny")
    st.success("🌍 AI Multilanguage Engine aktywny! Możesz pisać i pytać w dowolnym języku (np. 🇬🇧, 🇩🇪, 🇺🇦, 🇪🇸).")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if user_query := st.chat_input("Zadaj pytanie (Ask question / Ставити питання)...", key="audytor_input"):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("assistant"):
            if rag_system:
                with st.spinner("Przeszukiwanie wektorowej bazy ustaw..."):
                    response = rag_system.ask(user_query)
            else:
                response = "❌ Błąd silnika wektorowego."
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- ZAKŁADKA 2: LINIA OBRONY ---
with tab2:
    st.header("🛡️ Generator Oświadczeń (Art. 12)")
    
    naglowek = f"**{user_info['full_name']}**"
    if user_info['company_name'] != "Kierowca Indywidualny":
        naglowek += f" ({user_info['company_name']})"
    else:
        naglowek += " (Kierowca Niezależny)"
    st.info(f"Oświadczenie zostanie wygenerowane oficjalnie na dane: {naglowek}")
    
    opis_incydentu = st.text_area("Opisz sytuację awaryjną (możesz opisać ją we własnym języku):", height=100)
    
    jezyk_docelowy = st.selectbox(
        "Dla jakiego organu kontrolnego generujesz dokument?",
        ["Polski (ITD)", "Niemiecki (BAG / BALM)", "Angielski (Uniwersalny / DVSA)", "Francuski (DREAL)", "Hiszpański (Guardia Civil)"]
    )
    
    if "pdf_ready" not in st.session_state:
        st.session_state.pdf_ready = False
        st.session_state.pdf_bytes = None
        st.session_state.pdf_text = ""

    if st.button("⚖️ Generuj Dokument Prawny", type="primary", use_container_width=True):
        if not opis_incydentu:
            st.warning("Uzupełnij opis incydentu przed wygenerowaniem pisma.")
        else:
            with st.spinner(f"Adwokat AI konstruuje linię obrony w języku: {jezyk_docelowy}..."):
                odpowiedz = rag_system.generate_defense_statement(opis_incydentu, jezyk_docelowy)
                pdf_data = create_defense_pdf(odpowiedz, user_info['full_name'], user_info['company_name'])
                
                st.session_state.pdf_text = odpowiedz
                st.session_state.pdf_bytes = pdf_data
                st.session_state.pdf_ready = True
                st.success("Dokument prawny wygenerowany z sukcesem!")

    if st.session_state.pdf_ready:
        st.markdown(st.session_state.pdf_text)
        st.divider()
        st.download_button(
            label="📄 POBIERZ OFICJALNY DOKUMENT PDF DO KONTROLI",
            data=st.session_state.pdf_bytes,
            file_name=f"Oswiadczenie_{user_info['full_name'].replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

# --- ZAKŁADKA 3: KALKULATOR KAR ---
with tab3:
    st.header("💰 Wycena Ryzyka i Taryfikator ITD/BAG")
    st.info("System obsługuje dowolny język. Wpisz naruszenie, a system przeszuka oficjalne taryfikatory UE.")
    opis_naruszenia = st.text_area("Opisz naruszenie (np. skrócenie odpoczynku):", height=100)
    if st.button("🚨 Rozpocznij Audyt Finansowy", type="primary", use_container_width=True):
        with st.spinner("Inspektor AI ocenia potencjalne ryzyko finansowe..."):
            odpowiedz = rag_system.calculate_penalty(opis_naruszenia)
            st.error("Raport wyceny ryzyka został przygotowany.")
            st.markdown(odpowiedz)

# --- ZAKŁADKA 4: KALKULATOR ADR ---
with tab4:
    st.header("📊 Kalkulator Wyłączenia ADR (1.1.3.6)")
    if "adr_loads" not in st.session_state:
        st.session_state.adr_loads = []
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        wybrany_un = st.selectbox("Towar (Kod UN)", options=list(TABELA_A.keys()), format_func=lambda x: f"UN {x} - {TABELA_A[x]['nazwa']}")
    with c2:
        ilosc = st.number_input("Ilość (L/kg)", min_value=1, value=100)
    with c3:
        st.write("##")
        if st.button("➕ Dodaj Ładunek", use_container_width=True):
            st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
            st.toast("Dodano ładunek do zestawienia.")
    if st.session_state.adr_loads:
        wynik = oblicz_1136(st.session_state.adr_loads)
        if "error" not in wynik:
            st.table([{"Numer UN": i['un'], "Ilość deklarowana": i['ilosc'], "Obliczone Punkty": int(i['punkty'])} for i in wynik["szczegoly"]])
            suma_pkt = wynik["suma_punktow"]
            st.metric("SUMA PUNKTÓW ADR", f"{int(suma_pkt)} / 1000")
            if wynik["zwolniony"]:
                st.success("✅ TRANSPORT ZWOLNIONY (Kwalifikuje się do wyłączenia)")
            else:
                st.error("🚨 PEŁNY ADR WYMAGANY (Przekroczono limit)")
        if st.button("🗑️ Resetuj zestawienie", type="secondary"):
            st.session_state.adr_loads = []
            st.rerun()

# --- ZAKŁADKA 5: SKANER OCR ---
with tab5:
    st.header("📸 Skaner Dowodów (Wydruki Tacho / CMR)")
    st.write("Wgraj zdjęcie dokumentu przewozowego do analizy silnika Vision AI.")
    uploaded_file = st.file_uploader("Wybierz plik graficzny", type=["jpg", "png"])
    if uploaded_file and st.button("🔍 Skanuj i Przeprowadź Audyt", type="primary", use_container_width=True):
        with st.spinner("Ekstrakcja OCR i audyt prawny dowodu..."):
            tekst = rag_system.read_image(uploaded_file.read())
            st.expander("Zobacz wyciągnięte surowe dane (Raw OCR Text)").text(tekst)
            analiza = rag_system.ask(f"Przeanalizuj pod kątem zgodności z prawem transportowym te dane odczytane z dokumentu:\n{tekst}")
            st.markdown(f"### ⚖️ Wynik Audytu:\n{analiza}")

# --- ZAKŁADKA 6: GRANICE GPS ---
with tab6:
    st.header("🗺️ Granice i Promy (Pakiet Mobilności)")
    scenariusz = st.selectbox("Zidentyfikuj sytuację na trasie:", ["Przekroczenie granicy wewnętrznej UE", "Wjazd na prom lub do pociągu", "Granica z krajem spoza UE"])
    if st.button("Pobierz procedurę z bazy wiedzy UE"):
        with st.spinner("Szukam odpowiednich dyrektyw prawnych..."):
            st.markdown(rag_system.ask(f"Jakie są obowiązki kierowcy w tachografie w sytuacji: {scenariusz}?"))

# --- ZAKŁADKA 7: WPISY MANUALNE ---
with tab7:
    st.header("✍️ Asystent Wpisów Manualnych")
    c1, c2 = st.columns(2)
    with c1:
        co_robil = st.selectbox("Status kierowcy bez karty:", ["Odpoczynek (Urlop/Weekend)", "Inna praca (Magazyn)", "Dojazd (Pociąg/Auto)"])
    with c2:
        kraj_rozpoczecia = st.text_input("Kraj powrotu (np. DE, PL):", value="PL")
    if st.button("Wygeneruj krok po kroku"):
        with st.spinner("Opracowuję oficjalną procedurę wpisu..."):
            st.markdown(rag_system.ask(f"Kierowca wyciągnął kartę, robił: {co_robil}. Kraj startu to {kraj_rozpoczecia}. Podaj instrukcję wpisu manualnego wg. Rozporządzenia 165/2014."))

# --- ZAKŁADKA 8: PASY EN 12195 ---
with tab8:
    st.header("⛓️ Moduł Inżynieryjny: Siła Mocowania (EN 12195)")
    col_a, col_b = st.columns(2)
    with col_a:
        waga = st.number_input("Waga ładunku (kg)", min_value=100, value=2500, step=100)
        stf = st.number_input("Wartość STF na metce pasa (daN)", min_value=100, value=500, step=50)
    with col_b:
        tarcie_nazwa = st.selectbox("Rodzaj powierzchni styku", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
        kat = st.slider("Kąt nachylenia pasa (alfa)", min_value=10, max_value=90, value=60)
    if st.button("🧮 Wykonaj obliczenia naciągu", type="primary", use_container_width=True):
        wynik = oblicz_pasy_docisk(waga, WSPOLCZYNNIKI_TARCIA[tarcie_nazwa], stf, kat)
        if "error" in wynik:
            st.error(wynik["error"])
        else:
            st.metric(label="MINIMALNA WYMAGANA LICZBA PASÓW", value=wynik["pasy"])
            st.write(f"📝 Uzasadnienie inżynieryjne: {wynik['wiadomosc']}")