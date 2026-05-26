import json
import os
from pathlib import Path
from typing import Dict
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
DEFAULT_LANGUAGE = "en"
TRANSLATIONS_DIR = "i18n"

RTL_LANGUAGES = {"ar", "fa", "ur"}

# =========================================================
# LANGUAGE METADATA (44 Języki)
# =========================================================
LANGUAGE_META = {
    "pl": {"flag": "🇵🇱", "name": "Polski"},
    "en": {"flag": "🇬🇧", "name": "English"},
    "de": {"flag": "🇩🇪", "name": "Deutsch"},
    "ua": {"flag": "🇺🇦", "name": "Українська"},
    "es": {"flag": "🇪🇸", "name": "Español"},
    "fr": {"flag": "🇫🇷", "name": "Français"},
    "it": {"flag": "🇮🇹", "name": "Italiano"},
    "nl": {"flag": "🇳🇱", "name": "Nederlands"},
    "ro": {"flag": "🇷🇴", "name": "Română"},
    "bg": {"flag": "🇧🇬", "name": "Български"},
    "tr": {"flag": "🇹🇷", "name": "Türkçe"},
    "ru": {"flag": "🇷🇺", "name": "Русский"},
    "pt": {"flag": "🇵🇹", "name": "Português"},
    "cs": {"flag": "🇨🇿", "name": "Čeština"},
    "sk": {"flag": "🇸🇰", "name": "Slovenčina"},
    "hu": {"flag": "🇭🇺", "name": "Magyar"},
    "hr": {"flag": "🇭🇷", "name": "Hrvatski"},
    "sr": {"flag": "🇷🇸", "name": "Српски"},
    "sl": {"flag": "🇸🇮", "name": "Slovenščina"},
    "el": {"flag": "🇬🇷", "name": "Ελληνικά"},
    "lt": {"flag": "🇱🇹", "name": "Lietuvių"},
    "lv": {"flag": "🇱🇻", "name": "Latviešu"},
    "et": {"flag": "🇪🇪", "name": "Eesti"},
    "fi": {"flag": "🇫🇮", "name": "Suomi"},
    "sv": {"flag": "🇸🇪", "name": "Svenska"},
    "no": {"flag": "🇳🇴", "name": "Norsk"},
    "da": {"flag": "🇩🇰", "name": "Dansk"},
    "be": {"flag": "🇧🇾", "name": "Беларуская"},
    "ka": {"flag": "🇬🇪", "name": "ქართული"},
    "az": {"flag": "🇦🇿", "name": "Azərbaycan"},
    "kk": {"flag": "🇰🇿", "name": "Қазақ"},
    "uz": {"flag": "🇺🇿", "name": "Oʻzbek"},
    "tg": {"flag": "🇹🇯", "name": "Тоҷикӣ"},
    "ky": {"flag": "🇰🇬", "name": "Кыргызча"},
    "mk": {"flag": "🇲🇰", "name": "Македонски"},
    "sq": {"flag": "🇦🇱", "name": "Shqip"},
    "bs": {"flag": "🇧🇦", "name": "Bosanski"},
    "fa": {"flag": "🇮🇷", "name": "فارسی"},
    "ur": {"flag": "🇵🇰", "name": "اردو"},
    "hi": {"flag": "🇮🇳", "name": "हिन्दी"},
    "tl": {"flag": "🇵🇭", "name": "Tagalog"},
    "ar": {"flag": "🇸🇦", "name": "العربية"},
    "zh": {"flag": "🇨🇳", "name": "中文"},
    "vn": {"flag": "🇻🇳", "name": "Tiếng Việt"}
}

# =========================================================
# SEEDER DANYCH - Automatyczne tworzenie plików JSON
# =========================================================
def ensure_translation_files():
    Path(TRANSLATIONS_DIR).mkdir(exist_ok=True)
    
    # Przykładowe pliki startowe z nową strukturą zagnieżdżoną
    EXAMPLES = {
        "en": {
            "login": {"title": "LOGIN", "email": "Email / ID", "password": "Password", "button": "ENTER SYSTEM", "type": "Profile type:", "type_drv": "Independent Driver", "type_cmp": "Transport Company", "name": "Full Name", "cmp_name": "Company Name", "btn_reg": "CREATE ACCOUNT"},
            "dashboard": {"sub": "Professional Legal System", "ready": "READY FOR THE ROAD", "desc": "Describe your problem or use camera.", "logout": "LOGOUT", "cfg": "SELECT AUTHORITY:"},
            "chat": {"placeholder": "Describe your problem...", "attach": "📎 Camera / Files"}
        },
        "pl": {
            "login": {"title": "LOGOWANIE", "email": "Adres Email / ID", "password": "Hasło", "button": "WEJDŹ DO SYSTEMU", "type": "Rodzaj profilu:", "type_drv": "Kierowca Indywidualny", "type_cmp": "Firma Transportowa", "name": "Imię i Nazwisko", "cmp_name": "Nazwa Firmy", "btn_reg": "ZAREJESTRUJ PROFIL"},
            "dashboard": {"sub": "Profesjonalny System Prawny", "ready": "GOTOWY DO TRASY", "desc": "Wpisz problem lub użyj kamery.", "logout": "WYLOGUJ", "cfg": "WYBÓR ORGANU:"},
            "chat": {"placeholder": "Napisz problem transportowy...", "attach": "📎 Kamera / Pliki"}
        },
        "de": {
            "login": {"title": "ANMELDUNG", "email": "E-Mail / ID", "password": "Passwort", "button": "SYSTEM BETRETEN", "type": "Profiltyp:", "type_drv": "Einzelfahrer", "type_cmp": "Firma", "name": "Name", "cmp_name": "Firmenname", "btn_reg": "KONTO ERSTELLEN"},
            "dashboard": {"sub": "Professionelles Rechtssystem", "ready": "BEREIT FÜR DIE FAHRT", "desc": "Problem beschreiben oder Kamera nutzen.", "logout": "ABMELDEN", "cfg": "BEHÖRDE:"},
            "chat": {"placeholder": "Transportproblem beschreiben...", "attach": "📎 Kamera / Dateien"}
        }
    }
    
    for lang, data in EXAMPLES.items():
        path = Path(TRANSLATIONS_DIR) / f"{lang}.json"
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

# =========================================================
# ENTERPRISE I18N MANAGER
# =========================================================
class I18NManager:
    def __init__(self):
        self.cache: Dict = {}
        ensure_translation_files() # Odpalane przy starcie systemu

    def load_language(self, lang: str) -> Dict:
        if lang in self.cache:
            return self.cache[lang]

        file_path = Path(TRANSLATIONS_DIR) / f"{lang}.json"
        
        # Fallback do angielskiego, jeśli plik języka jeszcze nie istnieje
        if not file_path.exists():
            file_path = Path(TRANSLATIONS_DIR) / f"{DEFAULT_LANGUAGE}.json"

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.cache[lang] = data
        return data

    def t(self, lang: str, key: str) -> str:
        translations = self.load_language(lang)
        keys = key.split(".")
        value = translations

        try:
            for k in keys:
                value = value[k]
            return value
        except Exception:
            # Fallback
            fallback = self.load_language(DEFAULT_LANGUAGE)
            try:
                value = fallback
                for k in keys:
                    value = value[k]
                return value
            except Exception:
                return f"[{key}]"

    def is_rtl(self, lang: str) -> bool:
        return lang in RTL_LANGUAGES

    def get_language_meta(self, lang: str) -> Dict:
        return LANGUAGE_META.get(lang, LANGUAGE_META[DEFAULT_LANGUAGE])

# =========================================================
# MAGIA STREAMLITA - CACHE'OWANIE SYSTEMU TŁUMACZEŃ
# =========================================================
@st.cache_resource
def get_i18n_manager():
    return I18NManager()