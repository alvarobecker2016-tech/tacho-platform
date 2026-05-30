# =========================================================
# POCKET DGSA & TACHO - ENTERPRISE FRONTEND v6
# =========================================================
import streamlit as st
import uuid
import bleach
import os
from openai import OpenAI

# --- Silniki i Moduły ---
from rag_engine import TachografRAG
from audit_pipeline import AuditPipeline
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
from pdf_generator import create_defense_pdf
import auth_db
from i18n_manager import get_i18n_manager, LANGUAGE_META

# =========================================================
# KONFIGURACJA STRONY
# =========================================================
st.set_page_config(page_title="Pocket DGSA", page_icon="🛣️", layout="wide", initial_sidebar_state="collapsed")

# =========================================================
# INICJALIZACJA SYSTEMÓW (Z CACHE)
# =========================================================
@st.cache_resource
def get_systems():
    rag = TachografRAG()
    rag.load_existing_database()
    return rag, AuditPipeline(), get_i18n_manager(), OpenAI()

rag_system, audit_system, i18n, client = get_systems()
auth_db.init_db()

# =========================================================
# ZARZĄDZANIE STANEM (SESSION STATE)
# =========================================================
DEFAULT_SESSION = {
    "lang": "pl",
    "logged_in": False,
    "user_data": None,
    "messages": [],
    "audit_running": False,
    "current_audit_id": None,
    "credits_locked": False,
    "show_adr": False,
    "show_pasy": False,
    "file_bytes": None,  # Zabezpieczenie plików przed resetem karty
    "cam_bytes": None    # Zabezpieczenie zdjęć aparatu przed resetem karty
}

for key, value in DEFAULT_SESSION.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =========================================================
# CSS I WSPARCIE RTL (Kraje Arabskie)
# =========================================================
if i18n.is_rtl(st.session_state.lang):
    st.markdown("<style>body, .stTextInput, .stTextArea { direction: rtl; text-align: right; }</style>", unsafe_allow_html=True)

st.markdown("""
<style>
header {visibility: hidden;} footer {visibility: hidden;}
.block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; background-color: #000000; }
.stButton>button { border-radius: 8px; font-weight: bold; border: none; text-transform: uppercase; letter-spacing: 1px; }
.welcome-container { display: flex; flex-direction: column; align-items: center; margin-top: 5vh; text-align: center;}
.highway-logo-container { width: 140px; height: 140px; border-radius: 50%; border: 3px solid #D32F2F; box-shadow: 0 0 25px rgba(211, 47, 47, 0.3); margin-bottom: 1.5rem; }
.welcome-text { font-size: 2.8rem; font-weight: 800; color: #FFFFFF; background: -webkit-linear-gradient(45deg, #FFFFFF, #D32F2F); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.audit-box { background: #111111; border-radius: 10px; padding: 20px; border: 1px solid #333333; margin-top: 15px; }
.paywall-box { background-color: #111111; border: 2px solid #D32F2F; border-radius: 10px; padding: 2rem; text-align: center; margin-top: 2rem; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.stChatInputContainer input { color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# SYSTEMY BEZPIECZEŃSTWA (PRO)
# =========================================================
def sanitize_html(content):
    if not isinstance(content, str): return ""
    # Chroni przed XSS, zachowuje dozwolone tagi
    clean_text = bleach.clean(content, tags=["b", "i", "strong", "em", "p", "br", "ul", "li"], strip=True)
    return clean_text

def secure_use_credit(username):
    if st.session_state.credits_locked: return False
    st.session_state.credits_locked = True
    try:
        nowe_kredyty = auth_db.use_credit(username)
        if nowe_kredyty is not None: st.session_state.user_data['credits'] = nowe_kredyty
        return True
    finally:
        st.session_state.credits_locked = False

def create_audit_trace():
    audit_id = str(uuid.uuid4())
    st.session_state.current_audit_id = audit_id
    return audit_id

def classify_intent(text):
    text_upper = text.upper()
    if "ADR" in text_upper: return "ADR"
    if "PASY" in text_upper: return "PASY"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", temperature=0.0,
            messages=[
                {"role": "system", "content": "Jesteś routerem AI. Zwróć JEDNO słowo: OBRONA, KARY lub OGOLNE."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip().upper()
    except: return "OGOLNE"

# =========================================================
# RENDEROWANIE RAPORTU AUDYTU (HTML) - ZABEZPIECZONY DTO
# =========================================================
def render_audit_report(report_data):
    # KRYTYCZNE ZABEZPIECZENIE: Sprawdzenie czy mamy do czynienia z early_exit / errorem
    status = report_data.get("status")
    if status not in ["COMPLIANT", "NON_COMPLIANT"]:
        msg = report_data.get("message", "Wystąpił nieoczekiwany błąd podczas analizy wydruku.")
        return f"<div class='audit-box' style='border-left: 5px solid #ffcc00;'>⚠️ <b>ANALIZA ZATRZYMANA ({status})</b><br>{msg}</div>"
    
    # BEZPIECZNE POBIERANIE KLUCZY DTO
    c_status = report_data.get('compliance_status', 'UNKNOWN')
    conf_score = report_data.get('confidence_score', 0.0)
    
    # Zamiana znaków nowej linii z AI na <br> by zachować układ w HTML
    summary_raw = str(report_data.get('summary', ''))
    summary_html = sanitize_html(summary_raw).replace('\n', '<br>')
    
    violations = report_data.get('violations', [])
    
    html = f"""
    <div class='audit-box'>
        <h3 style='color: #fff; margin-top: 0;'>📑 RAPORT COMPLIANCE AI</h3>
        <p style='color: #aaa;'>Status: <strong style='color: {"#ff4c4c" if c_status == "NON_COMPLIANT" else "#4CAF50"};'>{c_status}</strong> | Pewność: {int(conf_score*100)}%</p>
        <div style='color: #ddd;'>{summary_html}</div>
    </div>
    """
    
    if not violations:
        html += "<div class='audit-box' style='border-left: 5px solid #4CAF50; color: #a5d6a7;'>✅ <b>BRAK NARUSZEŃ</b> - System nie odnotował przekroczeń limitów na przetworzonej osi czasu.</div>"
    else:
        for v in violations:
            article = str(v.get('article', ''))
            reg = str(v.get('regulation', ''))
            desc = str(v.get('description', ''))
            fine = v.get('estimated_fine_eur', 'N/A')
            defense = str(v.get('defense_strategy', ''))
            
            html += f"""
            <div class='audit-box' style='border-left: 6px solid #D32F2F;'>
                <h4 style="color: #ff4c4c; margin-top: 0;">🚨 {sanitize_html(article)} ({sanitize_html(reg)})</h4>
                <p style="color: #eee;">{sanitize_html(desc)}</p>
                <div style="background: #2e0000; padding: 8px; border-radius: 4px; display: inline-block; color: #ff9800; font-weight: bold;">
                    💸 Kara (Szac.): {fine} EUR
                </div>
            """
            
            if v.get('defense_possible') and defense:
                html += f"""
                <div style="background: #002200; border-left: 4px solid #4CAF50; padding: 12px; margin-top: 15px;">
                    <p style="color: #81c784; margin: 0;"><strong>🛡️ KROKI ZARADCZE / OBRONA:</strong><br>{sanitize_html(defense).replace('\n', '<br>')}</p>
                </div>
                """
            html += "</div>"
    return html

# =========================================================
# EKRAN LOGOWANIA
# =========================================================
lang = st.session_state.lang

if not st.session_state.logged_in:
    col_empty, col_lang = st.columns([7, 3])
    with col_lang:
        available_languages = list(LANGUAGE_META.keys())
        wybrany_jezyk = st.selectbox("🌐", available_languages, index=available_languages.index(lang),
            format_func=lambda x: f"{LANGUAGE_META[x]['flag']} {LANGUAGE_META[x]['name']}", label_visibility="collapsed")
        if wybrany_jezyk != lang:
            st.session_state.lang = wybrany_jezyk
            st.rerun()

    st.markdown(f"""
    <div class='welcome-container'>
        <div class='highway-logo-container'></div>
        <div class='welcome-text'>POCKET DGSA & TACHO</div>
        <p style='color: #888888; font-size: 1.1rem;'>{i18n.t(lang, 'dashboard.sub')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_log, tab_reg = st.tabs([i18n.t(lang, 'login.title'), "REJESTRACJA"])
        with tab_log:
            log_user = st.text_input(i18n.t(lang, 'login.email'))
            log_pass = st.text_input(i18n.t(lang, 'login.password'), type="password")
            if st.button(i18n.t(lang, 'login.button'), type="primary", use_container_width=True):
                user_info = auth_db.verify_login(log_user, log_pass)
                if user_info:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_info
                    st.rerun()
                else: st.error("Błąd logowania.")
                    
        with tab_reg:
            typ_konta = st.radio("Typ:", ["Kierowca", "Firma"])
            reg_user = st.text_input(i18n.t(lang, 'login.email') + " ")
            reg_pass = st.text_input(i18n.t(lang, 'login.password') + " ", type="password")
            reg_name = st.text_input("Imię i Nazwisko")
            reg_comp = st.text_input("Firma") if typ_konta == "Firma" else "Kierowca"
            if st.button("ZAREJESTRUJ", use_container_width=True):
                if reg_user and reg_pass and reg_name:
                    if auth_db.register_user(reg_user, reg_pass, reg_name, reg_comp): st.success("Konto utworzone!")
                    else: st.error("Użytkownik istnieje.")
    st.stop()

# =========================================================
# ZALOGOWANY INTERFEJS (PRO)
# =========================================================
user_info = st.session_state.user_data
kredyty_kierowcy = user_info.get('credits', 0)
czy_premium = user_info.get('is_premium', False)

col_space, col_lang = st.columns([8, 2])
with col_lang:
    available_languages = list(LANGUAGE_META.keys())
    nowy_jezyk = st.selectbox("🌐", available_languages, index=available_languages.index(lang),
        format_func=lambda x: f"{LANGUAGE_META[x]['flag']} {LANGUAGE_META[x]['name']}", label_visibility="collapsed", key="in_app_lang")
    if nowy_jezyk != lang:
        st.session_state.lang = nowy_jezyk
        st.rerun()

with st.sidebar:
    st.success(f"👤 {user_info['full_name']}")
    st.info(f"🏢 {user_info['company_name']}")
    st.divider()
    jezyk_pism = st.selectbox("Organ Kontrolny:", ["Niemiecki (BALM)", "Polski (ITD)", "Angielski (DVSA)", "Francuski (DREAL)", "Hiszpański (Guardia Civil)"])
    st.divider()
    if st.button("WYLOGUJ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

# --- EKRAN STARTOWY / PAYWALL ---
if not st.session_state.messages and not st.session_state.show_adr and not st.session_state.show_pasy:
    st.markdown(f"<div class='welcome-container'><div class='highway-logo-container'></div><div class='welcome-text'>{i18n.t(lang, 'dashboard.ready')}</div></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if czy_premium: st.success("👑 KONTO PREMIUM - Nielimitowany dostęp", icon="✅")
        else: st.warning(f"🪙 Pozostało audytów: **{kredyty_kierowcy}**", icon="⚠️")

if not czy_premium and kredyty_kierowcy <= 0:
    st.markdown("<div class='paywall-box'><h2 style='color: #D32F2F;'>🛑 WYCZERPAŁEŚ LIMIT</h2><p style='color: #FFFFFF;'>Odblokuj pełen dostęp.</p></div>", unsafe_allow_html=True)
    st.stop() 

# --- KALKULATORY BIZNESOWE ---
if st.session_state.show_adr:
    with st.expander("🛑 KALKULATOR ADR 1.1.3.6", expanded=True):
        if "adr_loads" not in st.session_state: st.session_state.adr_loads = []
        c1, c2, c3 = st.columns([2, 1, 1])
        wybrany_un = c1.selectbox("Kod UN", options=list(TABELA_A.keys()))
        ilosc = c2.number_input("Ilość / Quantity", min_value=1, value=100)
        if c3.button("➕ DODAJ"): st.session_state.adr_loads.append({"un": wybrany_un, "ilosc": ilosc})
        if st.session_state.adr_loads:
            wynik = oblicz_1136(st.session_state.adr_loads)
            if "error" not in wynik:
                st.table([{"UN": i['un'], "Qty": i['ilosc'], "Pts": int(i['punkty'])} for i in wynik["szczegoly"]])
                st.info(f"Suma punktów: {int(wynik['suma_punktow'])} / 1000")
            if st.button("RESET", type="secondary"): 
                st.session_state.adr_loads = []
                st.rerun()

if st.session_state.show_pasy:
    with st.expander("⛓️ KALKULATOR PASÓW (EN-12195)", expanded=True):
        c1, c2 = st.columns(2)
        waga = c1.number_input("Waga / Weight (kg)", value=2500, step=100)
        stf = c1.number_input("STF napinacza (daN)", value=500, step=50)
        tarcie = c2.selectbox("Materiał / Tarcie", options=list(WSPOLCZYNNIKI_TARCIA.keys()))
        kat = c2.slider("Kąt mocowania (Alfa)", 10, 90, 60)
        if st.button("OBLICZ PASY", type="primary"):
            wynik = oblicz_pasy_docisk(waga, WSPOLCZYNNIKI_TARCIA[tarcie], stf, kat)
            if "error" not in wynik: st.success(f"Wymagana minimalna liczba pasów: {wynik['pasy']}")

# --- HISTORIA CZATU ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)
        if message.get("pdf_bytes"):
            st.download_button("⬇️ Pobierz Dokument PDF", data=message["pdf_bytes"], file_name="Oswiadczenie.pdf", mime="application/pdf", key=str(uuid.uuid4()))

# --- INPUT ZDJĘĆ / PLIKÓW (Z ZABEZPIECZENIEM PRZED RESETEM SESJI) ---
with st.popover(i18n.t(lang, 'chat.attach')):
    tab_cam, tab_gal = st.tabs(["📸 APARAT", "📁 PLIKI"])
    
    with tab_cam:
        zdjecie_kamera = st.camera_input("Zrób zdjęcie", label_visibility="collapsed")
        
        # Zapisz do sesji, by nie zniknęło po przełączeniu okna na telefonie
        if zdjecie_kamera is not None:
            st.session_state.cam_bytes = zdjecie_kamera.getvalue()
            
        if st.session_state.get("cam_bytes") and st.button("SKANUJ ZDJĘCIE (ENTERPRISE AI)", type="primary", use_container_width=True):
            if secure_use_credit(user_info['username']):
                with st.spinner("Przetwarzanie w silniku Compliance AI..."):
                    audit_id = create_audit_trace()
                    raport_json = audit_system.run(st.session_state.cam_bytes)
                    html_raport = render_audit_report(raport_json)
                    st.session_state.messages.append({"role": "user", "content": "📸 *Zlecono audyt ze zdjęcia*"})
                    st.session_state.messages.append({"role": "assistant", "content": html_raport, "audit_id": audit_id})
                    st.session_state.cam_bytes = None # Czyść po udanym przetworzeniu
                    st.rerun()

    with tab_gal:
        uploaded_file = st.file_uploader("Wgraj z urządzenia", type=["jpg", "png"], label_visibility="collapsed")
        
        # Zapisz do sesji, by nie zniknęło po przełączeniu okna
        if uploaded_file is not None:
            st.session_state.file_bytes = uploaded_file.getvalue()
            
        if st.session_state.get("file_bytes") and st.button("SKANUJ PLIK (ENTERPRISE AI)", type="primary", use_container_width=True):
            if secure_use_credit(user_info['username']):
                with st.spinner("Przetwarzanie w silniku Compliance AI..."):
                    audit_id = create_audit_trace()
                    raport_json = audit_system.run(st.session_state.file_bytes)
                    html_raport = render_audit_report(raport_json)
                    st.session_state.messages.append({"role": "user", "content": "📁 *Zlecono audyt z pliku*"})
                    st.session_state.messages.append({"role": "assistant", "content": html_raport, "audit_id": audit_id})
                    st.session_state.file_bytes = None # Czyść po udanym przetworzeniu
                    st.rerun()

# --- INPUT TEKSTOWY (RAG ENGINE & ROUTER) ---
if user_query := st.chat_input(i18n.t(lang, 'chat.placeholder')):
    audit_id = create_audit_trace()
    st.session_state.messages.append({"role": "user", "content": sanitize_html(user_query), "audit_id": audit_id})
    secure_use_credit(user_info['username'])
        
    with st.chat_message("user"):
        st.markdown(sanitize_html(user_query))
        
    with st.chat_message("assistant"):
        with st.spinner("Analiza prawna..."):
            intencja = classify_intent(user_query)
            pdf_bytes_to_save = None
            
            if intencja == "ADR":
                st.session_state.show_adr = True
                st.session_state.show_pasy = False
                st.rerun()
            elif intencja == "PASY":
                st.session_state.show_pasy = True
                st.session_state.show_adr = False
                st.rerun()
            elif intencja == "OBRONA":
                response = rag_system.generate_defense_statement(user_query, jezyk_pism)
                pdf_bytes_to_save = create_defense_pdf(response, user_info['full_name'], user_info['company_name'])
                st.markdown(response)
                st.download_button("⬇️ Pobierz Dokument PDF", data=pdf_bytes_to_save, file_name="Obrona.pdf", mime="application/pdf")
            else:
                response = rag_system.ask(user_query)
                st.markdown(response)
                
        st.session_state.messages.append({"role": "assistant", "content": response, "pdf_bytes": pdf_bytes_to_save, "audit_id": audit_id})
        st.rerun()
