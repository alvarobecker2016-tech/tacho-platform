import streamlit as st
import os
from openai import OpenAI
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
import auth_db
from pdf_generator import create_defense_pdf

st.set_page_config(page_title="Pocket DGSA", page_icon="🛣️", layout="wide", initial_sidebar_state="collapsed")

UI = {
    "🇵🇱 PL": {"sub": "Profesjonalny System Prawny", "log_tab": "LOGOWANIE", "reg_tab": "REJESTRACJA", "email": "Adres Email / ID", "pass": "Hasło", "btn_log": "WEJDŹ DO SYSTEMU", "type": "Rodzaj profilu:", "type_drv": "Kierowca Indywidualny", "type_cmp": "Firma Transportowa", "name": "Imię i Nazwisko", "cmp_name": "Nazwa Firmy", "btn_reg": "ZAREJESTRUJ PROFIL", "err_log": "Błędny identyfikator lub hasło.", "err_reg": "Użytkownik już istnieje.", "ok_reg": "Konto utworzone.", "req_f": "Wypełnij wymagane pola.", "ready": "GOTOWY DO TRASY", "desc": "Wpisz problem lub użyj przycisku '📎'.", "chat_ph": "Napisz problem...", "attach": "📎 Mikrofon / Aparat / Pliki", "logout": "WYLOGUJ", "cfg": "WYBÓR ORGANU:"},
    "🇬🇧 EN": {"sub": "Professional Legal System", "log_tab": "LOGIN", "reg_tab": "REGISTER", "email": "Email / ID", "pass": "Password", "btn_log": "ENTER SYSTEM", "type": "Profile type:", "type_drv": "Independent Driver", "type_cmp": "Transport Company", "name": "Full Name", "cmp_name": "Company Name", "btn_reg": "CREATE ACCOUNT", "err_log": "Invalid ID or password.", "err_reg": "User exists.", "ok_reg": "Account created.", "req_f": "Fill required fields.", "ready": "READY FOR THE ROAD", "desc": "Type your problem or use '📎'.", "chat_ph": "Describe problem...", "attach": "📎 Mic / Camera", "logout": "LOGOUT", "cfg": "SELECT AUTHORITY:"},
    "🇩🇪 DE": {"sub": "Professionelles Rechtssystem", "log_tab": "ANMELDUNG", "reg_tab": "REGISTRIERUNG", "email": "E-Mail / ID", "pass": "Passwort", "btn_log": "ANMELDEN", "type": "Profiltyp:", "type_drv": "Einzelfahrer", "type_cmp": "Firma", "name": "Name", "cmp_name": "Firmenname", "btn_reg": "KONTO ERSTELLEN", "err_log": "Falsche Daten.", "err_reg": "Existiert bereits.", "ok_reg": "Erstellt.", "req_f": "Pflichtfelder.", "ready": "BEREIT FÜR DIE FAHRT", "desc": "Problem eingeben oder '📎' nutzen.", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ABMELDEN", "cfg": "BEHÖRDE:"}
}

st.markdown("""
<style>
header {visibility: hidden;}
footer {visibility: hidden;}
.block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; background-color: #000000; }
.stButton>button { border-radius: 8px; font-weight: bold; border: none; transition: all 0.2s; text-transform: uppercase; letter-spacing: 1px; }
.stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(211, 47, 47, 0.4); }
.welcome-container { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 5vh; margin-bottom: 2vh; text-align: center; }
.highway-logo-container { width: 140px; height: 140px; border-radius: 50%; border: 3px solid #D32F2F; box-shadow: 0 0 25px rgba(211, 47, 47, 0.3); margin-bottom: 1.5rem; background-color: transparent; }
.welcome-text { font-size: 2.8rem; font-weight: 800; color: #FFFFFF; letter-spacing: 1px; background: -webkit-linear-gradient(45deg, #FFFFFF, #D32F2F); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.stChatInputContainer input { color: #000000 !important; }
.paywall-box { background-color: #111111; border: 2px solid #D32F2F; border-radius: 10px; padding: 2rem; text-align: center; margin-top: 2rem; }
</style>
""", unsafe_allow_html=True)

auth_db.init_db()

if "lang" not in st.session_state:
    st.session_state.lang = "🇬🇧 EN"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if not st.session_state.logged_in:
    
    col_empty, col_lang = st.columns([7, 3])
    with col_lang:
        wybrany_jezyk = st.selectbox("🌐", list(UI.keys()), index=list(UI.keys()).index(st.session_state.lang), label_visibility="collapsed")
        st.session_state.lang = wybrany_jezyk

    t = UI.get(st.session_state.lang, UI["🇬🇧 EN"])

    st.markdown(f"""
    <div class='welcome-container'>
        <div class='highway-logo-container'></div>
        <div class='welcome-text'>POCKET DGSA & TACHO</div>
        <p style='color: #888888; font-size: 1.1rem; margin-top: 5px;'>{t['sub']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_log, tab_reg = st.tabs([t['log_tab'], t['reg_tab']])
        with tab_log:
            log_user = st.text_input(t['email'])
            log_pass = st.text_input(t['pass'], type="password")
            st.divider()
            if st.button(t['btn_log'], type="primary", use_container_width=True):
                user_info = auth_db.verify_login(log_user, log_pass)
                if user_info:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_info
                    st.rerun()
                else:
                    st.error(t['err_log'])
                    
        with tab_reg:
            typ_konta = st.radio(t['type'], [t['type_drv'], t['type_cmp']])
            reg_user = st.text_input(t['email'] + " ")
            reg_pass = st.text_input(t['pass'] + " ", type="password")
            reg_name = st.text_input(t['name'])
            reg_comp = st.text_input(t['cmp_name']) if typ_konta == t['type_cmp'] else t['type_drv']
            st.divider()
            if st.button(t['btn_reg'], use_container_width=True):
                if reg_user and reg_pass and reg_name:
                    if auth_db.register_user(reg_user, reg_pass, reg_name, reg_comp):
                        st.success(t['ok_reg'])
                    else:
                        st.error(t['err_reg'])
                else:
                    st.warning(t['req_f'])
    st.stop()

t = UI.get(st.session_state.lang, UI["🇬🇧 EN"])

@st.cache_resource
def get_rag_system():
    rag = TachografRAG()
    if rag.load_existing_database(): return rag
    return None

rag_system = get_rag_system()

def classify_intent(text):
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini", temperature=0.0,
            messages=[
                {"role": "system", "content": "Jesteś routerem AI. Zwróć jedno słowo: OBRONA, KARY, ADR, PASY lub OGOLNE."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip().upper()
    except: return "OGOLNE"

user_info = st.session_state.user_data
imie_uzytkownika = user_info['full_name'].split()[0]
kredyty_kierowcy = user_info.get('credits', 0)
czy_premium = user_info.get('is_premium', False)

col_space, col_lang = st.columns([8, 2])
with col_lang:
    nowy_jezyk = st.selectbox("🌐", list(UI.keys()), index=list(UI.keys()).index(st.session_state.lang), label_visibility="collapsed", key="logged_in_lang")
    if nowy_jezyk != st.session_state.lang:
        st.session_state.lang = nowy_jezyk
        st.rerun()

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white;'>Panel</h2>", unsafe_allow_html=True)
    st.divider()
    st.success(f"👤 **{user_info['full_name']}**")
    st.info(f"🏢 {user_info['company_name']}")
    st.divider()
    st.markdown(f"**{t['cfg']}**")
    jezyk_pism = st.selectbox("", ["Niemiecki (BAG)", "Polski (ITD)", "Angielski (DVSA)", "Francuski (DREAL)", "Hiszpański (Guardia Civil)"], label_visibility="collapsed")
    
    st.divider()
    if st.button(t['logout'], use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

if "messages" not in st.session_state: st.session_state.messages = []
if "show_adr" not in st.session_state: st.session_state.show_adr = False
if "show_pasy" not in st.session_state: st.session_state.show_pasy = False

if not st.session_state.messages and not st.session_state.show_adr and not st.session_state.show_pasy:
    st.markdown(f"""
    <div class='welcome-container'>
        <div class='highway-logo-container'></div>
        <div class='welcome-text'>{t['ready']}, {imie_uzytkownika.upper()}?</div>
        <p style='color: #707070; margin-top: 10px;'>{t['desc']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if czy_premium:
            st.success("👑 KONTO PREMIUM - Nielimitowany dostęp", icon="✅")
        else:
            st.warning(f"🪙 Pozostało darmowych pytań: **{kredyty_kierowcy}**", icon="⚠️")

if not czy_premium and kredyty_kierowcy <= 0:
    st.markdown("""
    <div class='paywall-box'>
        <h2 style='color: #D32F2F;'>🛑 WYCZERPAŁEŚ DARMOWY LIMIT</h2>
        <p style='color: #FFFFFF; font-size: 1.2rem;'>Zużyłeś wszystkie darmowe żetony. Odblokuj pełen dostęp, aby dalej generować pisma i unikać mandatów.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💳 KUP PAKIET 24H - 2.99€", type="primary", use_container_width=True):
            st.info("Trwa podpinanie płatności Stripe...")
        if st.button("👑 KUP SUBSKRYPCJĘ MIESIĘCZNĄ - 14.99€", use_container_width=True):
            st.info("Trwa podpinanie płatności Stripe...")
    st.stop() 

if st.session_state.show_adr:
    with st.expander("🛑 KALKULATOR ADR", expanded=True):
        if "adr_loads" not in st.session_state: st.session_state.adr_loads = []
        c1, c2, c3 = st.columns([2, 1, 1])
        wybrany_un = c1.selectbox("Kod UN", options=list(TABELA_A.keys()))
        ilosc = c2.number_input("Ilość / Quantity", min_value=1, value=100)
        if c3.button("➕"):
            st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
        if st.session_state.adr_loads:
            wynik = oblicz_1136(st.session_state.adr_loads)
            if "error" not in wynik:
                st.table([{"UN": i['un'], "Qty": i['ilosc'], "Pts": int(i['punkty'])} for i in wynik["szczegoly"]])
                st.info(f"Total: {int(wynik['suma_punktow'])} / 1000")
            if st.button("RESET", type="secondary"):
                st.session_state.adr_loads = []
                st.rerun()

if st.session_state.show_pasy:
    with st.expander("⛓️ EN-12195", expanded=True):
        c1, c2 = st.columns(2)
        waga = c1.number_input("Waga / Weight (kg)", value=2500, step=100)
        stf = c1.number_input("STF (daN)", value=500, step=50)
        tarcie = c2.selectbox("Tarcie / Friction", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
        kat = c2.slider("Alfa (10-90)", 10, 90, 60)
        if st.button("OBLICZ / CALCULATE", type="primary"):
            wynik = oblicz_pasy_docisk(waga, WSPOLCZYNNIKI_TARCIA[tarcie], stf, kat)
            if "error" not in wynik:
                st.success(f"Pasów / Straps: {wynik['pasy']}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("pdf_bytes"):
            st.download_button("⬇️ PDF", data=message["pdf_bytes"], file_name="Oswiadczenie_Kierowcy.pdf", mime="application/pdf", key=str(hash(message["content"])))

with st.popover(t['attach']):
    tab_cam, tab_gal, tab_audio = st.tabs(["📸 CAMERA", "📁 FILES", "🎤 AUDIO"])
    
    with tab_cam:
        zdjecie_kamera = st.camera_input("Zrób zdjęcie z aplikacji", label_visibility="collapsed")
        if zdjecie_kamera and st.button("ANALIZUJ", type="primary", use_container_width=True, key="btn_cam"):
            with st.spinner("Skanowanie paragonu..."):
                nowe_kredyty = auth_db.use_credit(user_info['username'])
                if nowe_kredyty is not None: st.session_state.user_data['credits'] = nowe_kredyty
                
                # ZMIANA: Wynik ląduje jako odpowiedź Asystenta!
                odczyt_ocr = rag_system.read_image(zdjecie_kamera.read())
                st.session_state.messages.append({"role": "user", "content": "📸 *Wysłano zdjęcie wydruku do analizy*"})
                st.session_state.messages.append({"role": "assistant", "content": odczyt_ocr})
                st.rerun()

    with tab_gal:
        uploaded_file = st.file_uploader("Wgraj z urządzenia", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if uploaded_file and st.button("ANALIZUJ", type="primary", use_container_width=True, key="btn_gal"):
            with st.spinner("Skanowanie paragonu..."):
                nowe_kredyty = auth_db.use_credit(user_info['username'])
                if nowe_kredyty is not None: st.session_state.user_data['credits'] = nowe_kredyty
                
                # ZMIANA: Wynik ląduje jako odpowiedź Asystenta!
                odczyt_ocr = rag_system.read_image(uploaded_file.read())
                st.session_state.messages.append({"role": "user", "content": "📁 *Wysłano plik wydruku do analizy*"})
                st.session_state.messages.append({"role": "assistant", "content": odczyt_ocr})
                st.rerun()
                
    with tab_audio:
        st.warning("🔜")

if user_query := st.chat_input(t['chat_ph']):
    st.session_state.messages.append({"role": "user", "content": user_query})
    
    nowe_kredyty = auth_db.use_credit(user_info['username'])
    if nowe_kredyty is not None:
        st.session_state.user_data['credits'] = nowe_kredyty
        
    with st.chat_message("user"):
        st.markdown(user_query)
        
    with st.chat_message("assistant"):
        if not rag_system:
            st.error("Offline")
        else:
            with st.spinner("..."):
                intencja = classify_intent(user_query)
                pdf_bytes_to_save = None
                
                if "OBRONA" in intencja:
                    response = rag_system.generate_defense_statement(user_query, jezyk_pism)
                    pdf_bytes_to_save = create_defense_pdf(response, user_info['full_name'], user_info['company_name'])
                    st.markdown(response)
                    st.download_button("⬇️ PDF", data=pdf_bytes_to_save, file_name="Oswiadczenie.pdf", mime="application/pdf")
                elif "KARY" in intencja:
                    response = rag_system.calculate_penalty(user_query)
                    st.markdown(response)
                elif "ADR" in intencja:
                    st.session_state.show_adr = True
                    st.session_state.show_pasy = False
                    st.rerun()
                elif "PASY" in intencja:
                    st.session_state.show_pasy = True
                    st.session_state.show_adr = False
                    st.rerun()
                else:
                    response = rag_system.ask(user_query)
                    st.markdown(response)
                    
            st.session_state.messages.append({"role": "assistant", "content": response, "pdf_bytes": pdf_bytes_to_save})
            st.rerun()