import streamlit as st
from rag_engine import TachografRAG
from openai import OpenAI
import datetime
import sqlite3
import json

# ==========================================
# SYSTEM BAZY DANYCH (TWARDA PAMIĘĆ)
# ==========================================
def init_db():
    conn = sqlite3.connect('profil_kierowcy.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS stan_aplikacji (id INTEGER PRIMARY KEY, kabotaz INTEGER, adr_json TEXT)')
    c.execute('SELECT kabotaz, adr_json FROM stan_aplikacji WHERE id=1')
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO stan_aplikacji (id, kabotaz, adr_json) VALUES (1, 0, '[]')")
        conn.commit()
        return 0, []
    return row[0], json.loads(row[1])

def update_kabotaz_db(val):
    conn = sqlite3.connect('profil_kierowcy.db')
    conn.cursor().execute('UPDATE stan_aplikacji SET kabotaz=? WHERE id=1', (val,))
    conn.commit()

def update_adr_db(adr_list):
    conn = sqlite3.connect('profil_kierowcy.db')
    conn.cursor().execute('UPDATE stan_aplikacji SET adr_json=? WHERE id=1', (json.dumps(adr_list),))
    conn.commit()

if "db_loaded" not in st.session_state:
    start_kabotaz, start_adr = init_db()
    st.session_state.kabotaz_count = start_kabotaz
    st.session_state.adr_cargo = start_adr
    st.session_state.messages = []
    st.session_state.db_loaded = True

# ==========================================
# INICJALIZACJA AI
# ==========================================
client = OpenAI() 

@st.cache_resource
def load_rag():
    rag = TachografRAG(persist_directory="./chroma_db_prawdziwa")
    rag.load_existing_database()
    return rag

rag_system = load_rag()

def speech_to_text(audio_bytes):
    return client.audio.transcriptions.create(model="whisper-1", file=("nagranie.wav", audio_bytes, "audio/wav")).text

def text_to_speech(text):
    return client.audio.speech.create(model="tts-1", voice="onyx", input=text).content

# ==========================================
# GŁÓWNY INTERFEJS APLIKACJI
# ==========================================
st.set_page_config(page_title="Pocket DGSA & Tacho Ultimate", page_icon="🚚", layout="wide")
st.title("🚚 Pocket DGSA & Tacho Ultimate")
st.caption("Wersja 2.0 | Zawiera: ADR, Tacho, Pakiet Mobilności, CMR i Mocowanie Ładunków")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Audytor AI", 
    "📸 Skaner (Tacho/CMR)", 
    "🧮 ADR 1.1.3.6",
    "🆘 Art. 12 (Nocny)",
    "🗺️ GPS Granice",
    "🕒 Wpisy Manualne",
    "🔗 Pasy (EN 12195)"
])

# ZAKŁADKA 1: AUDYTOR AI
with tab1:
    st.header("💬 Swobodny Audyt Prawny (W tym Pora Nocna i IMI)")
    st.info("💡 Spróbuj zapytać: 'Ile mogę pracować, jeśli zacząłem o 2:00 w nocy?' lub 'Kiedy muszę zgłosić kierowcę do IMI?'")
    czytaj_na_glos = st.toggle("🗣️ Odpowiadaj głosem", value=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])

    prompt_tekst = st.chat_input("Zadaj pytanie prawne...")
    prompt_glos = st.audio_input("🎙️ Nagraj pytanie głosowe")
    prompt = None
    
    if prompt_glos and prompt_glos.getvalue() != st.session_state.get("ostatnie_audio"):
        st.session_state["ostatnie_audio"] = prompt_glos.getvalue()
        with st.spinner("🎧 Dekoduję głos..."): prompt = speech_to_text(prompt_glos.getvalue())
    elif prompt_tekst: prompt = prompt_tekst

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analizuję unijne przepisy..."):
                response = rag_system.ask(prompt)
                st.markdown(response)
                if czytaj_na_glos: st.audio(text_to_speech(response), format="audio/mp3", autoplay=True)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ZAKŁADKA 2: APARAT I SKANER (NOWOŚĆ: Tryb CMR)
with tab2:
    st.header("📸 Inteligentny Skaner Dokumentów")
    opcja_zdjecia = st.radio("Źródło obrazu:", ["Wgraj plik", "Aparat"], horizontal=True)
    dokument = st.file_uploader("Wybierz plik", type=["jpg", "png"]) if opcja_zdjecia == "Wgraj plik" else st.camera_input("Zrób zdjęcie")
        
    if dokument:
        col_img, col_actions = st.columns([1, 2])
        with col_img: st.image(dokument, use_container_width=True)
        with col_actions:
            typ_audytu = st.selectbox("Czym jest ten dokument?", ["Wydruk z tachografu / Certyfikat", "List Przewozowy CMR (Szukaj haczyków)"])
            
            if st.button("Uruchom Skaner AI", type="primary"):
                with st.spinner("OCR przetwarza obraz..."):
                    tekst = rag_system.read_image(dokument.getvalue())
                st.info("📝 Odczytano:")
                st.code(tekst)
                
                with st.spinner("Audytuję..."):
                    if "CMR" in typ_audytu:
                        zapytanie = f"Jesteś surowym prawnikiem. Przeanalizuj ten list CMR: \n{tekst}\nSzukaj klauzul obciążających kierowcę, uwag magazyniera w polu 18 (np. uszkodzony towar, brak możliwości przeliczenia) oraz błędów w nazwach. Ostrzeż kierowcę!"
                    else:
                        zapytanie = f"Przeanalizuj zgodność tych danych z prawem: \n{tekst}"
                    st.success(f"⚖️ Werdykt:\n\n{rag_system.ask(zapytanie)}")

# ZAKŁADKA 3: KALKULATOR ADR
with tab3:
    st.header("🧮 Kalkulator ADR 1.1.3.6")
    with st.form("form_dodaj_towar"):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: nazwa_un = st.text_input("UN i nazwa", value="UN 1203")
        with c2: kat_trans = st.selectbox("Kategoria", [0, 1, 2, 3, 4], index=2)
        with c3: ilosc = st.number_input("Ilość (L/Kg)", min_value=1, value=100)
        if st.form_submit_button("Dodaj"):
            mnozniki = {0: "Brak", 1: 50, 2: 3, 3: 1, 4: 0}
            punkty = 999999 if kat_trans == 0 else ilosc * mnozniki[kat_trans]
            st.session_state.adr_cargo.append({"un": nazwa_un, "kat": kat_trans, "qty": ilosc, "pts": punkty})
            update_adr_db(st.session_state.adr_cargo)
            st.rerun()

    if st.session_state.adr_cargo:
        suma_punktow = sum(item['pts'] for item in st.session_state.adr_cargo if item['kat'] != 0)
        if any(item['kat'] == 0 for item in st.session_state.adr_cargo): st.error("🚨 ZABRONIONY POD 1.1.3.6")
        elif suma_punktow > 1000: st.error(f"🚨 LIMIT PRZEKROCZONY ({suma_punktow}/1000) - Pełny ADR!")
        else: st.success(f"✅ WYŁĄCZENIE ({suma_punktow}/1000) - Brak pomarańczowych tablic.")
        if st.button("Wyczyść naczepę"): 
            st.session_state.adr_cargo = []
            update_adr_db([])
            st.rerun()

# ZAKŁADKA 4: AWARYJNY ART. 12
with tab4:
    st.header("🆘 Awaryjne Przedłużenie Jazdy (Art. 12)")
    wydluzenie = st.slider("Minuty przekroczenia:", 0, 120, 15, step=15)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_mop = st.button("🅿️ BRAK MIEJSCA", use_container_width=True)
        btn_pogoda = st.button("❄️ ZŁA POGODA", use_container_width=True)
    with col_btn2:
        btn_wypadek = st.button("💥 WYPADEK", use_container_width=True)
        btn_ladunek = st.button("📦 OPÓŹNIENIE", use_container_width=True)
        
    powod = "BRAK MIEJSC NA MOP" if btn_mop else "ZŁA POGODA" if btn_pogoda else "WYPADEK/KOREK" if btn_wypadek else "OPÓŹNIENIE ZAŁADUNKU" if btn_ladunek else None
    if powod:
        st.success("Przepisz na tył wydruku:")
        st.code(f"ART. 12 ROZP. 561/2006.\nW DNIU {datetime.datetime.now().strftime('%d.%m.%Y')} WYDŁUŻONO CZAS O {wydluzenie} MIN.\nPOWÓD: {powod}.", language="text")

# ZAKŁADKA 5: ASYSTENT GRANIC
with tab5:
    st.header("🗺️ Geolokalizacja & Kabotaż")
    st.subheader("🇪🇺 Licznik Kabotażu")
    st.metric(label="Operacje w tym tygodniu", value=f"{st.session_state.kabotaz_count} / 3")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Zarejestruj Kabotaż", use_container_width=True) and st.session_state.kabotaz_count < 3:
            st.session_state.kabotaz_count += 1
            update_kabotaz_db(st.session_state.kabotaz_count)
            st.rerun()
    with c2:
        if st.button("🔄 Resetuj", use_container_width=True): 
            st.session_state.kabotaz_count = 0
            update_kabotaz_db(0)
            st.rerun()
    if st.session_state.kabotaz_count == 3: st.error("🚫 LIMIT KABOTAŻU WYCZERPANY! Opuść kraj.")

# ZAKŁADKA 6: WPISY MANUALNE
with tab6:
    st.header("🕒 Asystent Wpisu po Weekendzie")
    marka_tacho = st.radio("🖲️ Jaki masz tachograf w kabinie?", ["VDO Continental", "Stoneridge SE5000"], horizontal=True)
    scenariusz = st.radio("Co robiłeś po wyjęciu karty?", ["🛏️ Wyłącznie odpoczywałem", "🔨 Wykonywałem też inną pracę", "❓ Nie wiem / Pominąłem wpis"])
    if marka_tacho == "VDO Continental":
        if "odpoczywałem" in scenariusz: st.success("✅ [VDO] Wykonuj kroki:\n1. Wpis z ręki? -> OK\n2. Czas wyjęcia -> OK\n3. Ustaw symbol 🛏️ -> OK\n4. Zatwierdź godzinę -> OK\n5. Kraj rozpoczęcia -> OK\n6. Potwierdź wpis -> OK")
        elif "pracę" in scenariusz: st.warning("⚠️ [VDO] Wykonuj kroki:\n1. Wpis z ręki? -> OK\n2. Ustaw symbol 🔨 -> OK\n3. Czas zakończenia innej pracy -> OK\n4. Ustaw symbol 🛏️ -> OK\n5. Zatwierdź godzinę i Kraj -> OK")
    elif marka_tacho == "Stoneridge SE5000":
        if "odpoczywałem" in scenariusz: st.success("✅ [STONERIDGE]\n1. Odpoczynek do teraz? -> Kliknij OK.\n2. Wybierz kraj i zatwierdź.")
        elif "pracę" in scenariusz: st.warning("⚠️ [STONERIDGE]\n1. Odpoczynek do teraz? -> Kliknij KRZYŻYK (Anuluj)\n2. Dodaj wpis manualny? -> OK\n3. Zmień na 🔨 do godziny X -> OK\n4. Zmień na 🛏️ do końca -> OK")
    if "Nie wiem" in scenariusz: st.error("🚨 Zrobiłeś lukę na karcie! (UNKNOWN). Wyjmij kartę i zrób wpis od nowa lub wypisz zaświadczenie o urlopie.")

# ZAKŁADKA 7: MOCOWANIE ŁADUNKÓW (NOWOŚĆ)
with tab7:
    st.header("🔗 Kalkulator Mocowania Ładunków (EN 12195-1)")
    st.write("Oblicz ile pasów (dociskowych 500 daN) musisz wrzucić na ładunek, aby uniknąć mandatu.")
    
    waga = st.number_input("Waga ładunku (w Tonach)", min_value=0.5, value=10.0, step=0.5)
    maty = st.toggle("Czy używasz gumowych mat antypoślizgowych pod palety?", value=True)
    
    # Uproszczony algorytm fizyczny: n = (W - mu*W) / (2 * mu * STF) * wsp. bezp.
    # Używamy współczynników tarcia: drewno-drewno (0.3), maty gumowe (0.6)
    wsp_tarcia = 0.6 if maty else 0.3
    
    if st.button("Oblicz wymaganą ilość pasów", type="primary"):
        # Symulacja obliczeń zgodnych z EN 12195-1 dla standardowych pasów 500 daN (STF)
        # Przy mocowaniu dociskiem z góry
        sila_w_kg = waga * 1000
        wymagany_docisk = (sila_w_kg * (0.8 - wsp_tarcia)) / wsp_tarcia  # 0.8 to przeciążenie przy hamowaniu
        
        if wymagany_docisk <= 0:
            st.success("✅ Tarcie jest tak duże, że ładunek nie przesunie się do przodu. Wymagane są jednak minimum 2 pasy do zabezpieczenia przed podskakiwaniem.")
            ilosc_pasow = 2
        else:
            # Każdy pas daje STF 500 daN * 2 (po obu stronach) * wsp. bezpieczeństwa
            ilosc_pasow = max(2, int((wymagany_docisk / 500) + 1))
            
        st.info(f"📊 Przyjęty współczynnik tarcia (μ): **{wsp_tarcia}**")
        st.metric(label="Minimalna liczba pasów do założenia", value=f"{ilosc_pasow} szt.")
        
        if not maty:
            st.error("🚨 Brak mat antypoślizgowych zmusza Cię do założenia gigantycznej ilości pasów! Jeśli podłożysz maty gumowe, liczba pasów drastycznie spadnie.")