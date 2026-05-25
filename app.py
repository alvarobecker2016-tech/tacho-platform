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

# 3. Tworzenie zakładek dokładnie według Twojego interfejsu graficznego
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Audytor AI", 
    "📸 Skaner (Tacho/CMR)", 
    "📊 ADR 1.1.3.6", 
    "🛑 Art. 12 (Nocny)", 
    "🗺️ GPS Granice", 
    "✍️ Wpisy Manualne", 
    "⛓️ Pasy (EN 12195)"
])

# --- ZAKŁADKA 1: AUDYTOR AI ---
with tab1:
    st.header("Swobodny Audyt Prawny (W tym Pora Nocna i IMI)")
    
    # Nowa, zaktualizowana podpowiedź pasująca do rygorystycznego systemu RAG
    st.info("💡 Spróbuj zapytać o konkretny przypadek, np.: 'Co ile tygodni kierowca musi wrócić do bazy firmy według Pakietu Mobilności?' lub 'Jakie są ogólne wyłączenia z przepisów ADR?'")
    
    # Historia chatu w sesji
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Reakcja na pytanie użytkownika
    if user_query := st.chat_input("Zadaj pytanie prawne..."):
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        with st.chat_message("assistant"):
            if rag_system:
                with st.spinner("Ekspert AI analizuje wgrane akty prawne..."):
                    response = rag_system.ask(user_query)
            else:
                response = "❌ Błąd: Nie znaleziono lokalnej bazy danych ChromaDB. Uruchom najpierw skrypty dodające dokumenty."
            
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- ZAKŁADKA 3: DETERMINISTYCZNY KALKULATOR ADR 1.1.3.6 ---
with tab3:
    st.header("📊 Kalkulator Wyłączenia ADR na punkty (Tabela A)")
    st.write("Wprowadź towary niebezpieczne z listu przewozowego (CMR), aby sprawdzić, czy transport przekracza limit 1000 punktów.")
    
    # Inicjalizacja listy ładunków w pamięci podręcznej sesji
    if "adr_loads" not in st.session_state:
        st.session_state.adr_loads = []
        
    # Formularz dodawania towaru
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        wybrany_un = st.selectbox(
            "Wybierz towar niebezpieczny (Numer UN)", 
            options=list(TABELA_A.keys()), 
            format_func=lambda x: f"UN {x} - {TABELA_A[x]['nazwa']} (Kategoria transportowa: {TABELA_A[x]['kategoria']})"
        )
    with col2:
        ilosc = st.number_input("Ilość (Litrów lub Kilogramów)", min_value=1, value=100, step=10)
    with col3:
        st.write("##")  # Mały trik wyrównujący przycisk w dół
        if st.button("➕ Dodaj do zestawienia", use_container_width=True):
            st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
            st.toast(f"Dodano UN {wybrany_un} do kalkulatora!")

    # Wyświetlanie aktywnego zestawienia i wyników
    if st.session_state.adr_loads:
        st.write("### 📋 Bieżący ładunek na pojeździe:")
        
        # Obliczenia za pomocą naszego bezpiecznego modułu matematycznego
        wynik = oblicz_1136(st.session_state.adr_loads)
        
        if "error" in wynik:
            st.error(wynik["error"])
        else:
            # Przygotowanie czytelnej tabeli dla użytkownika
            tabela_wyswietl = []
            for item in wynik["szczegoly"]:
                tabela_wyswietl.append({
                    "Numer UN": f"UN {item['un']}",
                    "Nazwa towaru": item["nazwa"],
                    "Kat. Transportowa": item["kategoria"],
                    "Zadeklarowana ilość": f"{item['ilosc']} L/kg",
                    "Mnożnik ADR": f"x {item['mnoznik']}",
                    "Punkty obliczone": int(item["punkty"])
                })
            
            st.table(tabela_wyswietl)
            
            # Sekcja podsumowania punktowego
            st.write("---")
            suma_pkt = wynik["suma_punktow"]
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric(label="SUMA PUNKTÓW ADR", value=f"{int(suma_pkt)} / 1000")
            with c2:
                if wynik["zwolniony"]:
                    st.success("✅ TRANSPORT ZWOLNIONY! Ładunek kwalifikuje się do wyłączenia zgodnie z 1.1.3.6 ADR. Brak wymogu pomarańczowych tablic i pełnych uprawnień kierowcy.")
                else:
                    st.error("🚨 PEŁNY ADR! Limit 1000 punktów został przekroczony. Wymagane pomarańczowe tablice, kierowca z zaświadczeniem ADR oraz pełne wyposażenie pojazdu.")
            
            # Wizualny pasek postępu limitu
            procent_paska = min(float(suma_pkt / 1000), 1.0)
            st.progress(procent_paska)
            
        # Przycisk czyszczenia pamięci podręcznej
        if st.button("🗑️ Wyczyść całe zestawienie ładunków", type="secondary"):
            st.session_state.adr_loads = []
            st.rerun()
    else:
        st.info("Kalkulator jest pusty. Wybierz towar z listy i kliknij przycisk, aby rozpocząć kalkulację punktów.")

# --- POZOSTAŁE ZAKŁADKI (Makiety przygotowane pod dalszy rozwój projektu) ---
for tab, nazwa_modulu in zip([tab2, tab4, tab5, tab6, tab7], [
    "📸 Zaawansowany Skaner dokumentów przewozowych OCR", 
    "🛑 Moduł weryfikacji Pracy w Porze Nocnej", 
    "🗺️ Kontrola GPS i Przekroczenia Granic", 
    "✍️ Weryfikacja Wpisów Manualnych w Tachografie", 
    "⛓️ Kalkulator Siły Mocowania Ładunków (Norma EN 12195)"
]):
    with tab:
        st.subheader(nazwa_modulu)
        st.write("Moduł rdzeniowy platformy. Oczekuje na aktywację i podpięcie dedykowanych baz danych.")