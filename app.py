import streamlit as st
import os
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A

# 1. Konfiguracja strony głównej Streamlit
st.set_page_config(page_title="Pocket DGSA & Tacho Ultimate", layout="wide")

st.title("🚚 Pocket DGSA & Tacho Ultimate")
st.caption("Wersja 2.0 | Zawiera: ADR, Tacho, Pakiet Mobilności, CMR i Mocowanie Ładunków")

# 2. Bezpieczna inicjalizacja bazy RAG (z cache, aby nie ładować bazy przy każdym kliknięciu)
@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    success = rag.load_existing_database()
    if success:
        return rag
    return None

rag_system = get_rag_system()

# 3. Zaktualizowane Zakładki - Poziom Enterprise (8 modułów)
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "💬 Audytor AI", 
    "🛡️ Linia Obrony (Adwokat)",
    "💰 Kalkulator Kar (Inspektor)",
    "📊 ADR 1.1.3.6", 
    "📸 Skaner (Tacho/CMR)", 
    "🗺️ GPS Granice", 
    "✍️ Wpisy Manualne", 
    "⛓️ Pasy (EN 12195)"
])

# --- ZAKŁADKA 1: AUDYTOR AI ---
with tab1:
    st.header("Swobodny Audyt Prawny")
    st.info("💡 Zapytaj o konkretny przypadek prawny (np. 'Kiedy kierowca musi zgłosić się w systemie IMI?'). Zgodnie z wytycznymi, sztuczna inteligencja będzie odpowiadać wyłącznie na podstawie dostarczonych aktów prawnych.")
    
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
                with st.spinner("Ekspert AI analizuje wgrane akty prawne..."):
                    response = rag_system.ask(user_query)
            else:
                response = "❌ Błąd: Nie znaleziono lokalnej bazy danych ChromaDB."
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- ZAKŁADKA 2: LINIA OBRONY (NOWY MODUŁ) ---
with tab2:
    st.header("🛡️ Generator Oświadczeń i Linii Obrony (np. Art. 12)")
    st.info("Opisz dokładnie sytuację awaryjną. Adwokat AI wygeneruje formalne, prawnicze oświadczenie gotowe do podpisania podczas kontroli BAG/ITD.")
    
    opis_incydentu = st.text_area("Opisz sytuację (np. 'Zabrakło mi czasu na dojazd do bazy przez wypadek na A2, przekroczyłem czas jazdy o 40 minut'):", height=100)
    
    if st.button("⚖️ Wygeneruj Oświadczenie", type="primary", use_container_width=True):
        if not rag_system:
            st.error("Błąd bazy danych.")
        elif not opis_incydentu:
            st.warning("Proszę najpierw opisać sytuację.")
        else:
            with st.spinner("Adwokat AI konstruuje linię obrony i dobiera paragrafy..."):
                odpowiedz_prawnika = rag_system.generate_defense_statement(opis_incydentu)
                st.success("Dokument wygenerowany pomyślnie!")
                st.markdown(odpowiedz_prawnika)

# --- ZAKŁADKA 3: KALKULATOR KAR (NOWY MODUŁ) ---
with tab3:
    st.header("💰 Wycena Ryzyka i Taryfikator ITD/BAG")
    st.info("Podaj naruszenie, które chcesz zweryfikować. Inspektor AI przeszuka taryfikatory i oceni potencjalną karę oraz ryzyko utraty licencji (BPN/PPN).")
    
    opis_naruszenia = st.text_area("Opisz naruszenie (np. 'Skrócenie odpoczynku tygodniowego regularnego o 4 godziny bez rekompensaty'):", height=100)
    
    if st.button("🚨 Rozpocznij Audyt Finansowy", type="primary", use_container_width=True):
        if not rag_system:
            st.error("Błąd bazy danych.")
        elif not opis_naruszenia:
            st.warning("Proszę wpisać opis naruszenia.")
        else:
            with st.spinner("Inspektor AI przeszukuje taryfikatory i klasyfikację UE..."):
                odpowiedz_inspektora = rag_system.calculate_penalty(opis_naruszenia)
                st.error("Raport z wyceną ryzyka wygenerowany!")
                st.markdown(odpowiedz_inspektora)

# --- ZAKŁADKA 4: KALKULATOR ADR 1.1.3.6 ---
with tab4:
    st.header("📊 Kalkulator Wyłączenia ADR na punkty (Tabela A)")
    st.write("Wprowadź towary niebezpieczne z listu przewozowego (CMR), aby sprawdzić, czy transport przekracza limit 1000 punktów.")
    
    if "adr_loads" not in st.session_state:
        st.session_state.adr_loads = []
        
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        wybrany_un = st.selectbox(
            "Wybierz towar niebezpieczny (Numer UN)", 
            options=list(TABELA_A.keys()), 
            format_func=lambda x: f"UN {x} - {TABELA_A[x]['nazwa']} (Kat: {TABELA_A[x]['kategoria']})"
        )
    with col2:
        ilosc = st.number_input("Ilość (Litrów lub Kilogramów)", min_value=1, value=100, step=10)
    with col3:
        st.write("##")
        if st.button("➕ Dodaj do zestawienia", use_container_width=True):
            st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
            st.toast(f"Dodano UN {wybrany_un} do kalkulatora!")

    if st.session_state.adr_loads:
        st.write("### 📋 Bieżący ładunek na pojeździe:")
        wynik = oblicz_1136(st.session_state.adr_loads)
        
        if "error" in wynik:
            st.error(wynik["error"])
        else:
            tabela_wyswietl = []
            for item in wynik["szczegoly"]:
                tabela_wyswietl.append({
                    "Numer UN": f"UN {item['un']}",
                    "Nazwa towaru": item["nazwa"],
                    "Kat. Transportowa": item["kategoria"],
                    "Ilość": f"{item['ilosc']} L/kg",
                    "Punkty": int(item["punkty"])
                })
            
            st.table(tabela_wyswietl)
            st.write("---")
            suma_pkt = wynik["suma_punktow"]
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric(label="SUMA PUNKTÓW ADR", value=f"{int(suma_pkt)} / 1000")
            with c2:
                if wynik["zwolniony"]:
                    st.success("✅ TRANSPORT ZWOLNIONY! Brak wymogu pełnych uprawnień.")
                else:
                    st.error("🚨 PEŁNY ADR! Wymagane tablice i zaświadczenie.")
            
            st.progress(min(float(suma_pkt / 1000), 1.0))
            
        if st.button("🗑️ Wyczyść zestawienie", type="secondary"):
            st.session_state.adr_loads = []
            st.rerun()
    else:
        st.info("Kalkulator jest pusty.")

# --- ZAKŁADKA 5: ZAAWANSOWANY SKANER OCR (WIZJA AI) ---
with tab5:
    st.header("📸 Skaner Dowodów (Wydruki Tacho / CMR)")
    st.info("Wgraj zdjęcie dokumentu przewozowego lub wydruku z tachografu. Oczy AI (Vision) odczytają surowe dane, a następnie zlecą Audytorowi ich analizę prawną.")
    
    uploaded_file = st.file_uploader("Wybierz zdjęcie dowodu (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Wgrany dokument dowodowy", use_container_width=True)
        
        if st.button("🔍 Skanuj i Analizuj Dokument", type="primary", use_container_width=True):
            if not rag_system:
                st.error("Błąd bazy danych.")
            else:
                # KROK 1: Odczyt danych z obrazka
                with st.spinner("Oczy AI skanują dokument (Ekstrakcja OCR)..."):
                    image_bytes = uploaded_file.read()
                    extracted_text = rag_system.read_image(image_bytes)
                
                st.success("Dokument zdekodowany pomyślnie!")
                
                with st.expander("Kliknij, aby zobaczyć surowe dane z odczytu (Raw Text)"):
                    st.text(extracted_text)
                
                # KROK 2: Automatyczna analiza wyciągniętego tekstu przez silnik prawny
                with st.spinner("Silnik LegalTech analizuje odczytane dane pod kątem naruszeń..."):
                    prompt_dla_audytora = f"Przeanalizuj pod kątem zgodności z prawem transportowym następujące dane odczytane ze zdjęcia dokumentu:\n\n{extracted_text}"
                    analiza = rag_system.ask(prompt_dla_audytora)
                
                st.write("### ⚖️ Audyt Prawny Dokumentu:")
                st.markdown(analiza)

# --- POZOSTAŁE ZAKŁADKI (Makiety) ---
for tab, nazwa_modulu in zip([tab6, tab7, tab8], [
    "🗺️ Kontrola GPS i Przekroczenia Granic", 
    "✍️ Weryfikacja Wpisów Manualnych w Tachografie", 
    "⛓️ Kalkulator Siły Mocowania Ładunków (Norma EN 12195)"
]):
    with tab:
        st.subheader(nazwa_modulu)
        st.write("Moduł oczekuje na wdrożenie silnika przestrzennego (Geospatial) i nowych algorytmów.")