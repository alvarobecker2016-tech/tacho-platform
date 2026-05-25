import streamlit as st
import os
from openai import OpenAI
from rag_engine import TachografRAG
from adr_calculator import oblicz_1136, TABELA_A
from cargo_calculator import oblicz_pasy_docisk, WSPOLCZYNNIKI_TARCIA
import auth_db
from pdf_generator import create_defense_pdf

st.set_page_config(page_title="Pocket DGSA", page_icon="🛣️", layout="wide", initial_sidebar_state="collapsed")

# --- PEŁNY SŁOWNIK GLOBALNY (44 JĘZYKI) - USUNIĘTO SŁOWO B2B ---
UI = {
    "🇵🇱 PL": {"sub": "Profesjonalny System Prawny", "log_tab": "LOGOWANIE", "reg_tab": "REJESTRACJA", "email": "Adres Email / ID", "pass": "Hasło", "btn_log": "WEJDŹ DO SYSTEMU", "type": "Rodzaj profilu:", "type_drv": "Kierowca Indywidualny", "type_cmp": "Firma Transportowa", "name": "Imię i Nazwisko", "cmp_name": "Nazwa Firmy", "btn_reg": "ZAREJESTRUJ PROFIL", "err_log": "Błędny identyfikator lub hasło.", "err_reg": "Użytkownik już istnieje.", "ok_reg": "Konto utworzone.", "req_f": "Wypełnij wymagane pola.", "ready": "GOTOWY DO TRASY", "desc": "Wpisz problem lub użyj przycisku '📎'.", "chat_ph": "Napisz problem...", "attach": "📎 Mikrofon / Aparat / Pliki", "logout": "WYLOGUJ", "cfg": "WYBÓR ORGANU:"},
    "🇬🇧 EN": {"sub": "Professional Legal System", "log_tab": "LOGIN", "reg_tab": "REGISTER", "email": "Email / ID", "pass": "Password", "btn_log": "ENTER SYSTEM", "type": "Profile type:", "type_drv": "Independent Driver", "type_cmp": "Transport Company", "name": "Full Name", "cmp_name": "Company Name", "btn_reg": "CREATE ACCOUNT", "err_log": "Invalid ID or password.", "err_reg": "User exists.", "ok_reg": "Account created.", "req_f": "Fill required fields.", "ready": "READY FOR THE ROAD", "desc": "Type your problem or use '📎'.", "chat_ph": "Describe problem...", "attach": "📎 Mic / Camera", "logout": "LOGOUT", "cfg": "SELECT AUTHORITY:"},
    "🇩🇪 DE": {"sub": "Professionelles Rechtssystem", "log_tab": "ANMELDUNG", "reg_tab": "REGISTRIERUNG", "email": "E-Mail / ID", "pass": "Passwort", "btn_log": "ANMELDEN", "type": "Profiltyp:", "type_drv": "Einzelfahrer", "type_cmp": "Firma", "name": "Name", "cmp_name": "Firmenname", "btn_reg": "KONTO ERSTELLEN", "err_log": "Falsche Daten.", "err_reg": "Existiert bereits.", "ok_reg": "Erstellt.", "req_f": "Pflichtfelder.", "ready": "BEREIT FÜR DIE FAHRT", "desc": "Problem eingeben oder '📎' nutzen.", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ABMELDEN", "cfg": "BEHÖRDE:"},
    "🇺🇦 UA": {"sub": "Професійна правова система", "log_tab": "ВХІД", "reg_tab": "РЕЄСТРАЦІЯ", "email": "Email / ID", "pass": "Пароль", "btn_log": "УВІЙТИ", "type": "Профіль:", "type_drv": "Водій", "type_cmp": "Компанія", "name": "ПІБ", "cmp_name": "Компанія", "btn_reg": "СТВОРИТИ", "err_log": "Помилка.", "err_reg": "Існує.", "ok_reg": "Створено.", "req_f": "Заповніть.", "ready": "ГОТОВИЙ ДО РЕЙСУ", "desc": "Напишіть або додайте '📎'.", "chat_ph": "Проблема...", "attach": "📎 Камера", "logout": "ВИЙТИ", "cfg": "ОРГАН:"},
    "🇪🇸 ES": {"sub": "Sistema Legal Profesional", "log_tab": "ACCESO", "reg_tab": "REGISTRO", "email": "Correo / ID", "pass": "Contraseña", "btn_log": "ENTRAR", "type": "Perfil:", "type_drv": "Conductor", "type_cmp": "Empresa", "name": "Nombre", "cmp_name": "Empresa", "btn_reg": "CREAR CUENTA", "err_log": "Error.", "err_reg": "Existe.", "ok_reg": "Creado.", "req_f": "Rellenar.", "ready": "LISTO PARA LA RUTA", "desc": "Escriba o use '📎'.", "chat_ph": "Problema...", "attach": "📎 Cámara", "logout": "SALIR", "cfg": "AUTORIDAD:"},
    "🇷🇴 RO": {"sub": "Sistem Juridic Profesional", "log_tab": "AUTENTIFICARE", "reg_tab": "ÎNREGISTRARE", "email": "Email / ID", "pass": "Parolă", "btn_log": "INTRĂ", "type": "Profil:", "type_drv": "Șofer", "type_cmp": "Companie", "name": "Nume", "cmp_name": "Companie", "btn_reg": "CREARE CONT", "err_log": "Eroare.", "err_reg": "Există.", "ok_reg": "Creat.", "req_f": "Completează.", "ready": "GATA DE DRUM", "desc": "Scrie sau folosește '📎'.", "chat_ph": "Problema...", "attach": "📎 Cameră", "logout": "DECONECTARE", "cfg": "AUTORITATEA:"},
    "🇧🇬 BG": {"sub": "Професионална Правна Система", "log_tab": "ВХОД", "reg_tab": "РЕГИСТРАЦИЯ", "email": "Имейл / ID", "pass": "Парола", "btn_log": "ВЛЕЗ", "type": "Профил:", "type_drv": "Шофьор", "type_cmp": "Компания", "name": "Име", "cmp_name": "Компания", "btn_reg": "СЪЗДАЙ", "err_log": "Грешка.", "err_reg": "Съществува.", "ok_reg": "Създаден.", "req_f": "Попълнете.", "ready": "ГОТОВ ЗА ПЪТ", "desc": "Напишете проблема...", "chat_ph": "Проблем...", "attach": "📎 Камера", "logout": "ИЗХОД", "cfg": "ОРГАН:"},
    "🇹🇷 TR": {"sub": "Profesyonel Hukuk Sistemi", "log_tab": "GİRİŞ", "reg_tab": "KAYIT", "email": "E-posta / ID", "pass": "Şifre", "btn_log": "GİRİŞ YAP", "type": "Profil:", "type_drv": "Sürücü", "type_cmp": "Şirket", "name": "Ad Soyad", "cmp_name": "Şirket", "btn_reg": "KAYDOL", "err_log": "Hata.", "err_reg": "Mevcut.", "ok_reg": "Oluşturuldu.", "req_f": "Doldurun.", "ready": "YOLA HAZIR", "desc": "Yazın veya '📎' kullanın.", "chat_ph": "Sorun...", "attach": "📎 Kamera", "logout": "ÇIKIŞ", "cfg": "YETKİLİ:"},
    "🇷🇺 RU": {"sub": "Правовая Система", "log_tab": "ВХОД", "reg_tab": "РЕГИСТРАЦИЯ", "email": "Email / ID", "pass": "Пароль", "btn_log": "ВОЙТИ", "type": "Профиль:", "type_drv": "Водитель", "type_cmp": "Компания", "name": "ФИО", "cmp_name": "Компания", "btn_reg": "СОЗДАТЬ", "err_log": "Ошибка.", "err_reg": "Существует.", "ok_reg": "Создан.", "req_f": "Заполните.", "ready": "ГОТОВ К РЕЙСУ", "desc": "Опишите проблему...", "chat_ph": "Проблема...", "attach": "📎 Камера", "logout": "ВЫЙТИ", "cfg": "ОРГАН:"},
    "🇫🇷 FR": {"sub": "Système Juridique", "log_tab": "CONNEXION", "reg_tab": "INSCRIPTION", "email": "E-mail / ID", "pass": "Mot de passe", "btn_log": "ENTRER", "type": "Profil:", "type_drv": "Chauffeur", "type_cmp": "Entreprise", "name": "Nom", "cmp_name": "Entreprise", "btn_reg": "CRÉER", "err_log": "Erreur.", "err_reg": "Existe.", "ok_reg": "Créé.", "req_f": "Remplir.", "ready": "PRÊT POUR LA ROUTE", "desc": "Écrivez...", "chat_ph": "Problème...", "attach": "📎 Caméra", "logout": "DÉCONNEXION", "cfg": "AUTORITÉ:"},
    "🇮🇹 IT": {"sub": "Sistema Legale", "log_tab": "ACCESSO", "reg_tab": "REGISTRAZIONE", "email": "Email / ID", "pass": "Password", "btn_log": "ENTRA", "type": "Profilo:", "type_drv": "Autista", "type_cmp": "Azienda", "name": "Nome", "cmp_name": "Azienda", "btn_reg": "CREA", "err_log": "Errore.", "err_reg": "Esiste.", "ok_reg": "Creato.", "req_f": "Compila.", "ready": "PRONTO", "desc": "Scrivi...", "chat_ph": "Problema...", "attach": "📎 Fotocamera", "logout": "ESCI", "cfg": "AUTORITÀ:"},
    "🇳🇱 NL": {"sub": "Professioneel Systeem", "log_tab": "LOGIN", "reg_tab": "REGISTRATIE", "email": "Email / ID", "pass": "Wachtwoord", "btn_log": "INKOMEN", "type": "Profiel:", "type_drv": "Chauffeur", "type_cmp": "Bedrijf", "name": "Naam", "cmp_name": "Bedrijf", "btn_reg": "MAAK ACCOUNT", "err_log": "Fout.", "err_reg": "Bestaat al.", "ok_reg": "Gemaakt.", "req_f": "Invullen.", "ready": "KLAAR VOOR VERTREK", "desc": "Schrijf...", "chat_ph": "Probleem...", "attach": "📎 Camera", "logout": "UITLOGGEN", "cfg": "AUTORITEIT:"},
    "🇵🇹 PT": {"sub": "Sistema Legal", "log_tab": "LOGIN", "reg_tab": "REGISTO", "email": "Email / ID", "pass": "Senha", "btn_log": "ENTRAR", "type": "Perfil:", "type_drv": "Motorista", "type_cmp": "Empresa", "name": "Nome", "cmp_name": "Empresa", "btn_reg": "CRIAR CONTA", "err_log": "Erro.", "err_reg": "Existe.", "ok_reg": "Criado.", "req_f": "Preencher.", "ready": "PRONTO PARA A ROTA", "desc": "Escreva...", "chat_ph": "Problema...", "attach": "📎 Câmera", "logout": "SAIR", "cfg": "AUTORIDADE:"},
    "🇨🇿 CS": {"sub": "Profesionální Systém", "log_tab": "PŘIHLÁŠENÍ", "reg_tab": "REGISTRACE", "email": "Email / ID", "pass": "Heslo", "btn_log": "VSTOUPIT", "type": "Typ:", "type_drv": "Řidič", "type_cmp": "Firma", "name": "Jméno", "cmp_name": "Firma", "btn_reg": "VYTVOŘIT ÚČET", "err_log": "Chyba.", "err_reg": "Existuje.", "ok_reg": "Vytvořeno.", "req_f": "Vyplňte.", "ready": "PŘIPRAVEN", "desc": "Napište...", "chat_ph": "Problém...", "attach": "📎 Kamera", "logout": "ODHLÁSIT", "cfg": "ÚŘAD:"},
    "🇸🇰 SK": {"sub": "Profesionálny Systém", "log_tab": "PRIHLÁSENIE", "reg_tab": "REGISTRÁCIA", "email": "Email / ID", "pass": "Heslo", "btn_log": "VSTÚPIŤ", "type": "Typ:", "type_drv": "Vodič", "type_cmp": "Firma", "name": "Meno", "cmp_name": "Firma", "btn_reg": "VYTVORIŤ ÚČET", "err_log": "Chyba.", "err_reg": "Existuje.", "ok_reg": "Vytvorené.", "req_f": "Vyplňte.", "ready": "PRIPRAVENÝ", "desc": "Napíšte...", "chat_ph": "Problém...", "attach": "📎 Kamera", "logout": "ODHLÁSIŤ", "cfg": "ÚRAD:"},
    "🇭🇺 HU": {"sub": "Professzionális Rendszer", "log_tab": "BEJELENTKEZÉS", "reg_tab": "REGISZTRÁCIÓ", "email": "Email / ID", "pass": "Jelszó", "btn_log": "BELÉPÉS", "type": "Típus:", "type_drv": "Sofőr", "type_cmp": "Cég", "name": "Név", "cmp_name": "Cég", "btn_reg": "FIÓK LÉTREHOZÁSA", "err_log": "Hiba.", "err_reg": "Létezik.", "ok_reg": "Létrehozva.", "req_f": "Töltse ki.", "ready": "ÚTRA KÉSZ", "desc": "Írja le...", "chat_ph": "Probléma...", "attach": "📎 Kamera", "logout": "KIJELENTKEZÉS", "cfg": "HATÓSÁG:"},
    "🇭🇷 HR": {"sub": "Profesionalni Sustav", "log_tab": "PRIJAVA", "reg_tab": "REGISTRACIJA", "email": "Email / ID", "pass": "Lozinka", "btn_log": "ULAZ", "type": "Profil:", "type_drv": "Vozač", "type_cmp": "Tvrtka", "name": "Ime", "cmp_name": "Tvrtka", "btn_reg": "STVORI RAČUN", "err_log": "Greška.", "err_reg": "Postoji.", "ok_reg": "Stvoreno.", "req_f": "Ispunite.", "ready": "SPREMAN", "desc": "Upišite...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ODJAVA", "cfg": "TIJELO:"},
    "🇷🇸 SR": {"sub": "Profesionalni Sistem", "log_tab": "PRIJAVA", "reg_tab": "REGISTRACIJA", "email": "Email / ID", "pass": "Lozinka", "btn_log": "ULAZ", "type": "Profil:", "type_drv": "Vozač", "type_cmp": "Firma", "name": "Ime", "cmp_name": "Firma", "btn_reg": "NAPRAVI NALOG", "err_log": "Greška.", "err_reg": "Postoji.", "ok_reg": "Napravljeno.", "req_f": "Popunite.", "ready": "SPREMAN", "desc": "Upišite...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ODJAVA", "cfg": "ORGAN:"},
    "🇸🇮 SL": {"sub": "Profesionalni Sistem", "log_tab": "PRIJAVA", "reg_tab": "REGISTRACIJA", "email": "Email / ID", "pass": "Geslo", "btn_log": "VSTOP", "type": "Profil:", "type_drv": "Voznik", "type_cmp": "Podjetje", "name": "Ime", "cmp_name": "Podjetje", "btn_reg": "USTVARI RAČUN", "err_log": "Napaka.", "err_reg": "Obstaja.", "ok_reg": "Ustvarjeno.", "req_f": "Izpolnite.", "ready": "PRIPRAVLJEN", "desc": "Napišite...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ODJAVA", "cfg": "ORGAN:"},
    "🇬🇷 EL": {"sub": "Επαγγελματικό Σύστημα", "log_tab": "ΣΥΝΔΕΣΗ", "reg_tab": "ΕΓΓΡΑΦΗ", "email": "Email / ID", "pass": "Κωδικός", "btn_log": "ΕΙΣΟΔΟΣ", "type": "Προφίλ:", "type_drv": "Οδηγός", "type_cmp": "Εταιρεία", "name": "Όνομα", "cmp_name": "Εταιρεία", "btn_reg": "ΔΗΜΙΟΥΡΓΙΑ", "err_log": "Σφάλμα.", "err_reg": "Υπάρχει.", "ok_reg": "Δημιουργήθηκε.", "req_f": "Συμπληρώστε.", "ready": "ΕΤΟΙΜΟΣ", "desc": "Γράψτε...", "chat_ph": "Πρόβλημα...", "attach": "📎 Κάμερα", "logout": "ΑΠΟΣΥΝΔΕΣΗ", "cfg": "ΑΡΧΗ:"},
    "🇱🇹 LT": {"sub": "Profesionali Sistema", "log_tab": "PRISIJUNGTI", "reg_tab": "REGISTRUOTIS", "email": "El. paštas / ID", "pass": "Slaptažodis", "btn_log": "ĮEITI", "type": "Profilis:", "type_drv": "Vairuotojas", "type_cmp": "Įmonė", "name": "Vardas", "cmp_name": "Įmonė", "btn_reg": "KURTI", "err_log": "Klaida.", "err_reg": "Yra.", "ok_reg": "Sukurta.", "req_f": "Užpildyti.", "ready": "PASIRUOŠĘS", "desc": "Rašykite...", "chat_ph": "Problema...", "attach": "📎 Kamera", "logout": "ATSIJUNGTI", "cfg": "ĮSTAIGA:"},
    "🇱🇻 LV": {"sub": "Profesionālā Sistēma", "log_tab": "PIETEIKTIES", "reg_tab": "REĢISTRĒTIES", "email": "E-pasts / ID", "pass": "Parole", "btn_log": "IEIET", "type": "Profils:", "type_drv": "Vadītājs", "type_cmp": "Uzņēmums", "name": "Vārds", "cmp_name": "Uzņēmums", "btn_reg": "IZVEIDOT", "err_log": "Kļūda.", "err_reg": "Eksistē.", "ok_reg": "Izveidots.", "req_f": "Aizpildīt.", "ready": "GATAVS", "desc": "Rakstiet...", "chat_ph": "Problēma...", "attach": "📎 Kamera", "logout": "IZIET", "cfg": "IESTĀDE:"},
    "🇪🇪 ET": {"sub": "Professionaalne Süsteem", "log_tab": "LOGI SISSE", "reg_tab": "REGISTREERI", "email": "Email / ID", "pass": "Parool", "btn_log": "SISENEDA", "type": "Profiil:", "type_drv": "Juht", "type_cmp": "Ettevõte", "name": "Nimi", "cmp_name": "Ettevõte", "btn_reg": "LOO KONTO", "err_log": "Viga.", "err_reg": "Olemas.", "ok_reg": "Loodud.", "req_f": "Täida.", "ready": "VALMIS", "desc": "Kirjuta...", "chat_ph": "Probleem...", "attach": "📎 Kaamera", "logout": "LOGI VÄLJA", "cfg": "ASUTUS:"},
    "🇫🇮 FI": {"sub": "Ammattijärjestelmä", "log_tab": "KIRJAUDU", "reg_tab": "REKISTERÖIDY", "email": "Sähköposti / ID", "pass": "Salasana", "btn_log": "KIRJAUDU", "type": "Profiili:", "type_drv": "Kuljettaja", "type_cmp": "Yritys", "name": "Nimi", "cmp_name": "Yritys", "btn_reg": "LUO TILI", "err_log": "Virhe.", "err_reg": "Olemassa.", "ok_reg": "Luotu.", "req_f": "Täytä.", "ready": "VALMIS", "desc": "Kirjoita...", "chat_ph": "Ongelma...", "attach": "📎 Kamera", "logout": "KIRJAUDU ULOS", "cfg": "VIRANOMAINEN:"},
    "🇸🇪 SV": {"sub": "Professionellt System", "log_tab": "LOGGA IN", "reg_tab": "REGISTRERA", "email": "E-post / ID", "pass": "Lösenord", "btn_log": "LOGGA IN", "type": "Profil:", "type_drv": "Förare", "type_cmp": "Företag", "name": "Namn", "cmp_name": "Företag", "btn_reg": "SKAPA KONTO", "err_log": "Fel.", "err_reg": "Finns.", "ok_reg": "Skapad.", "req_f": "Fyll i.", "ready": "REDO", "desc": "Skriv...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "LOGGA UT", "cfg": "MYNDIGHET:"},
    "🇳🇴 NO": {"sub": "Profesjonelt System", "log_tab": "LOGG INN", "reg_tab": "REGISTRER", "email": "E-post / ID", "pass": "Passord", "btn_log": "LOGG INN", "type": "Profil:", "type_drv": "Sjåfør", "type_cmp": "Selskap", "name": "Navn", "cmp_name": "Selskap", "btn_reg": "OPPRETT KONTO", "err_log": "Feil.", "err_reg": "Finnes.", "ok_reg": "Opprettet.", "req_f": "Fyll ut.", "ready": "KLAR", "desc": "Skriv...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "LOGG UT", "cfg": "MYNDIGHET:"},
    "🇩🇰 DA": {"sub": "Professionelt System", "log_tab": "LOG IND", "reg_tab": "REGISTRER", "email": "E-mail / ID", "pass": "Adgangskode", "btn_log": "LOG IND", "type": "Profil:", "type_drv": "Chauffør", "type_cmp": "Virksomhed", "name": "Navn", "cmp_name": "Virksomhed", "btn_reg": "OPRET KONTO", "err_log": "Fejl.", "err_reg": "Findes.", "ok_reg": "Oprettet.", "req_f": "Udfyld.", "ready": "KLAR", "desc": "Skriv...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "LOG UD", "cfg": "MYNDIGHED:"},
    "🇧🇾 BE": {"sub": "Прафесійная Сістэма", "log_tab": "УВАХОД", "reg_tab": "РЭГІСТРАЦЫЯ", "email": "Email / ID", "pass": "Пароль", "btn_log": "УВАЙСЦІ", "type": "Профіль:", "type_drv": "Кіроўца", "type_cmp": "Кампанія", "name": "Імя", "cmp_name": "Кампанія", "btn_reg": "СТВАРЫЦЬ", "err_log": "Памылка.", "err_reg": "Існуе.", "ok_reg": "Створаны.", "req_f": "Запоўніце.", "ready": "ГАТОВЫ", "desc": "Апішыце...", "chat_ph": "Праблема...", "attach": "📎 Камера", "logout": "ВЫЙСЦІ", "cfg": "ОРГАН:"},
    "🇬🇪 KA": {"sub": "პროფესიონალური სისტემა", "log_tab": "შესვლა", "reg_tab": "რეგისტრაცია", "email": "ელ.ფოსტა / ID", "pass": "პაროლი", "btn_log": "შესვლა", "type": "პროფილი:", "type_drv": "მძღოლი", "type_cmp": "კომპანია", "name": "სახელი", "cmp_name": "კომპანია", "btn_reg": "შექმნა", "err_log": "შეცდომა.", "err_reg": "არსებობს.", "ok_reg": "შეიქმნა.", "req_f": "შეავსეთ.", "ready": "მზადაა", "desc": "დაწერეთ...", "chat_ph": "პრობლემა...", "attach": "📎 კამერა", "logout": "გასვლა", "cfg": "ორგანო:"},
    "🇦🇿 AZ": {"sub": "Peşəkar Sistem", "log_tab": "GİRİŞ", "reg_tab": "QEYDİYYAT", "email": "Email / ID", "pass": "Şifrə", "btn_log": "GİR", "type": "Profil:", "type_drv": "Sürücü", "type_cmp": "Şirkət", "name": "Ad", "cmp_name": "Şirkət", "btn_reg": "YARAT", "err_log": "Xəta.", "err_reg": "Mövcuddur.", "ok_reg": "Yaradıldı.", "req_f": "Doldurun.", "ready": "HAZIR", "desc": "Yazın...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ÇIXIŞ", "cfg": "QURUM:"},
    "🇰🇿 KK": {"sub": "Кәсіби жүйе", "log_tab": "КІРУ", "reg_tab": "ТІРКЕЛУ", "email": "Email / ID", "pass": "Құпия сөз", "btn_log": "КІРУ", "type": "Профиль:", "type_drv": "Жүргізуші", "type_cmp": "Компания", "name": "Аты", "cmp_name": "Компания", "btn_reg": "ЖАСАУ", "err_log": "Қате.", "err_reg": "Бар.", "ok_reg": "Жасалды.", "req_f": "Толтырыңыз.", "ready": "ДАЙЫН", "desc": "Жазыңыз...", "chat_ph": "Мәселе...", "attach": "📎 Камера", "logout": "ШЫҒУ", "cfg": "ОРГАН:"},
    "🇺🇿 UZ": {"sub": "Professional Tizim", "log_tab": "KIRISH", "reg_tab": "RO'YXAT", "email": "Email / ID", "pass": "Parol", "btn_log": "KIRISH", "type": "Profil:", "type_drv": "Haydovchi", "type_cmp": "Kompaniya", "name": "Ism", "cmp_name": "Kompaniya", "btn_reg": "YARATISH", "err_log": "Xato.", "err_reg": "Mavjud.", "ok_reg": "Yaratildi.", "req_f": "To'ldiring.", "ready": "TAYYOR", "desc": "Yozing...", "chat_ph": "Muammo...", "attach": "📎 Kamera", "logout": "CHIQISH", "cfg": "TASHKILOT:"},
    "🇹🇯 TG": {"sub": "Системаи Профессионалӣ", "log_tab": "ВУРУД", "reg_tab": "БАҚАЙДГИРӢ", "email": "Email / ID", "pass": "Рамз", "btn_log": "ВУРУД", "type": "Профил:", "type_drv": "Ронанда", "type_cmp": "Ширкат", "name": "Ном", "cmp_name": "Ширкат", "btn_reg": "СОХТАН", "err_log": "Хато.", "err_reg": "Мавҷуд аст.", "ok_reg": "Сохта шуд.", "req_f": "Пур кунед.", "ready": "ТАЙЁР", "desc": "Нависед...", "chat_ph": "Мушкилот...", "attach": "📎 Камера", "logout": "ХУРУҶ", "cfg": "МАҚОМОТ:"},
    "🇰🇬 KY": {"sub": "Кесиптик система", "log_tab": "КИРҮҮ", "reg_tab": "КАТТОО", "email": "Email / ID", "pass": "Сыр сөз", "btn_log": "КИРҮҮ", "type": "Профиль:", "type_drv": "Айдоочу", "type_cmp": "Компания", "name": "Аты", "cmp_name": "Компания", "btn_reg": "ТҮЗҮҮ", "err_log": "Ката.", "err_reg": "Бар.", "ok_reg": "Түзүлдү.", "req_f": "Толтуруңуз.", "ready": "ДАЯР", "desc": "Жазыңыз...", "chat_ph": "Көйгөй...", "attach": "📎 Камера", "logout": "ЧЫГУУ", "cfg": "ОРГАН:"},
    "🇲🇰 MK": {"sub": "Професионален систем", "log_tab": "НАЈАВА", "reg_tab": "РЕГИСТРАЦИЈА", "email": "Email / ID", "pass": "Лозинка", "btn_log": "ВЛЕЗ", "type": "Профил:", "type_drv": "Возач", "type_cmp": "Компанија", "name": "Име", "cmp_name": "Компанија", "btn_reg": "КРЕИРАЈ", "err_log": "Грешка.", "err_reg": "Постои.", "ok_reg": "Креирано.", "req_f": "Пополнете.", "ready": "ПОДГОТВЕН", "desc": "Пишете...", "chat_ph": "Проблем...", "attach": "📎 Камера", "logout": "ОДЈАВА", "cfg": "ОРГАН:"},
    "🇦🇱 SQ": {"sub": "Sistem Profesional", "log_tab": "HYRJE", "reg_tab": "REGJISTROHU", "email": "Email / ID", "pass": "Fjalëkalim", "btn_log": "HYR", "type": "Profili:", "type_drv": "Shofer", "type_cmp": "Kompani", "name": "Emri", "cmp_name": "Kompani", "btn_reg": "KRIJO", "err_log": "Gabim.", "err_reg": "Ekziston.", "ok_reg": "U krijua.", "req_f": "Plotëso.", "ready": "GATI", "desc": "Shkruaj...", "chat_ph": "Problemi...", "attach": "📎 Kamera", "logout": "DIL", "cfg": "AUTORITETI:"},
    "🇧🇦 BS": {"sub": "Profesionalni Sistem", "log_tab": "PRIJAVA", "reg_tab": "REGISTRACIJA", "email": "Email / ID", "pass": "Lozinka", "btn_log": "ULAZ", "type": "Profil:", "type_drv": "Vozač", "type_cmp": "Firma", "name": "Ime", "cmp_name": "Firma", "btn_reg": "NAPRAVI", "err_log": "Greška.", "err_reg": "Postoji.", "ok_reg": "Napravljeno.", "req_f": "Popunite.", "ready": "SPREMAN", "desc": "Upišite...", "chat_ph": "Problem...", "attach": "📎 Kamera", "logout": "ODJAVA", "cfg": "ORGAN:"},
    "🇮🇷 FA": {"sub": "سیستم حرفه‌ای", "log_tab": "ورود", "reg_tab": "ثبت نام", "email": "ایمیل", "pass": "رمز عبور", "btn_log": "ورود", "type": "نمایه:", "type_drv": "راننده", "type_cmp": "شرکت", "name": "نام", "cmp_name": "شرکت", "btn_reg": "ایجاد", "err_log": "خطا", "err_reg": "موجود", "ok_reg": "ایجاد شد", "req_f": "پر کنید", "ready": "آماده", "desc": "بنویسید...", "chat_ph": "مشکل...", "attach": "📎 دوربین", "logout": "خروج", "cfg": "سازمان:"},
    "🇵🇰 UR": {"sub": "پیشہ ورانہ نظام", "log_tab": "لاگ ان", "reg_tab": "رجسٹر", "email": "ای میل", "pass": "پاس ورڈ", "btn_log": "داخل ہوں", "type": "پروفائل:", "type_drv": "ڈرائیور", "type_cmp": "کمپنی", "name": "نام", "cmp_name": "کمپنی", "btn_reg": "بنائیں", "err_log": "غلطی", "err_reg": "موجود", "ok_reg": "بن گیا", "req_f": "پر کریں", "ready": "تیار", "desc": "لکھیں...", "chat_ph": "مسئلہ...", "attach": "📎 کیمرہ", "logout": "لاگ آؤٹ", "cfg": "اتھارٹی:"},
    "🇮🇳 HI": {"sub": "पेशेवर कानूनी प्रणाली", "log_tab": "लॉग इन", "reg_tab": "पंजीकरण", "email": "ईमेल / आईडी", "pass": "पासवर्ड", "btn_log": "दर्ज करें", "type": "प्रोफ़ाइल:", "type_drv": "ड्राइवर", "type_cmp": "कंपनी", "name": "पूरा नाम", "cmp_name": "कंपनी", "btn_reg": "खाता बनाएँ", "err_log": "त्रुटि।", "err_reg": "मौजूद है।", "ok_reg": "बनाया गया।", "req_f": "भरें।", "ready": "तैयार", "desc": "समस्या लिखें...", "chat_ph": "समस्या...", "attach": "📎 कैमरा", "logout": "लॉग आउट", "cfg": "प्राधिकरण:"},
    "🇵🇭 TL": {"sub": "Propesyonal na Legal System", "log_tab": "LOGIN", "reg_tab": "REGISTER", "email": "Email / ID", "pass": "Password", "btn_log": "IPASOK", "type": "Profile:", "type_drv": "Drayber", "type_cmp": "Kumpanya", "name": "Pangalan", "cmp_name": "Kumpanya", "btn_reg": "GUMAWA", "err_log": "Mali.", "err_reg": "Umiiral na.", "ok_reg": "Nagawa na.", "req_f": "Punan.", "ready": "HANDA", "desc": "Isulat...", "chat_ph": "Problema...", "attach": "📎 Camera", "logout": "LOGOUT", "cfg": "AWTORIDAD:"},
    "🇸🇦 AR": {"sub": "نظام قانوني احترافي", "log_tab": "تسجيل الدخول", "reg_tab": "تسجيل", "email": "البريد الإلكتروني", "pass": "كلمة المرور", "btn_log": "دخول", "type": "النوع:", "type_drv": "سائق", "type_cmp": "شركة", "name": "الاسم", "cmp_name": "الشركة", "btn_reg": "إنشاء", "err_log": "خطأ", "err_reg": "موجود", "ok_reg": "تم", "req_f": "املأ", "ready": "جاهز", "desc": "اكتب...", "chat_ph": "مشكلة...", "attach": "📎 كاميرا", "logout": "خروج", "cfg": "السلطة:"},
    "🇨🇳 ZH": {"sub": "专业法律系统", "log_tab": "登录", "reg_tab": "注册", "email": "电子邮件 / ID", "pass": "密码", "btn_log": "进入", "type": "资料:", "type_drv": "司机", "type_cmp": "公司", "name": "姓名", "cmp_name": "公司", "btn_reg": "创建", "err_log": "错误.", "err_reg": "已存在.", "ok_reg": "已创建.", "req_f": "填满.", "ready": "准备", "desc": "写...", "chat_ph": "问题...", "attach": "📎 相机", "logout": "登出", "cfg": "机构:"},
    "🇻🇳 VN": {"sub": "Hệ thống Pháp lý", "log_tab": "ĐĂNG NHẬP", "reg_tab": "ĐĂNG KÝ", "email": "Email / ID", "pass": "Mật khẩu", "btn_log": "VÀO", "type": "Hồ sơ:", "type_drv": "Tài xế", "type_cmp": "Công ty", "name": "Tên", "cmp_name": "Công ty", "btn_reg": "TẠO", "err_log": "Lỗi.", "err_reg": "Tồn tại.", "ok_reg": "Đã tạo.", "req_f": "Điền.", "ready": "SẴN SÀNG", "desc": "Viết...", "chat_ph": "Vấn đề...", "attach": "📎 Camera", "logout": "ĐĂNG XUẤT", "cfg": "CƠ QUAN:"}
}

# --- CSS: CZERŃ, BIEL I CZERWIEŃ ---
st.markdown("""
<style>
header {visibility: hidden;}
footer {visibility: hidden;}
.block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; background-color: #000000; }
.stButton>button { border-radius: 8px; font-weight: bold; border: none; transition: all 0.2s; text-transform: uppercase; letter-spacing: 1px; }
.stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(211, 47, 47, 0.4); }
.welcome-container { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 5vh; margin-bottom: 3vh; text-align: center; }
.highway-logo-container { width: 140px; height: 140px; border-radius: 50%; border: 3px solid #D32F2F; box-shadow: 0 0 25px rgba(211, 47, 47, 0.3); margin-bottom: 1.5rem; background-color: transparent; }
.welcome-text { font-size: 2.8rem; font-weight: 800; color: #FFFFFF; letter-spacing: 1px; background: -webkit-linear-gradient(45deg, #FFFFFF, #D32F2F); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
.stChatInputContainer input { color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

auth_db.init_db()

# --- DOMYŚLNY JĘZYK: ANGIELSKI ---
if "lang" not in st.session_state:
    st.session_state.lang = "🇬🇧 EN"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if not st.session_state.logged_in:
    
    # 1. NAJPIERW SELEKTOR JĘZYKA W PRAWYM GÓRNYM ROGU (Dyskretny)
    col_empty, col_lang = st.columns([7, 3])
    with col_lang:
        wybrany_jezyk = st.selectbox("🌐", list(UI.keys()), index=list(UI.keys()).index(st.session_state.lang), label_visibility="collapsed")
        st.session_state.lang = wybrany_jezyk

    t = UI[st.session_state.lang]

    # 2. POTEM CENTRALNE KÓŁKO I TEKST
    st.markdown(f"""
    <div class='welcome-container'>
        <div class='highway-logo-container'></div>
        <div class='welcome-text'>POCKET DGSA & TACHO</div>
        <p style='color: #888888; font-size: 1.1rem; margin-top: 5px;'>{t['sub']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. NA SAMYM DOLE FORMULARZ LOGOWANIA
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

# --- PO ZALOGOWANIU ---
t = UI[st.session_state.lang]

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

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white;'>Panel</h2>", unsafe_allow_html=True)
    st.divider()
    st.success(f"👤 **{user_info['full_name']}**")
    st.info(f"🏢 {user_info['company_name']}")
    st.divider()
    
    st.markdown("**🌐 APP LANGUAGE:**")
    nowy_jezyk = st.selectbox("", list(UI.keys()), index=list(UI.keys()).index(st.session_state.lang), label_visibility="collapsed")
    if nowy_jezyk != st.session_state.lang:
        st.session_state.lang = nowy_jezyk
        st.rerun()

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
    tab_skan, tab_audio = st.tabs(["📸 OCR", "🎤 AUDIO"])
    with tab_skan:
        uploaded_file = st.file_uploader("", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
        if uploaded_file and st.button("ANALIZUJ / ANALYZE", type="primary", use_container_width=True):
            with st.spinner("..."):
                odczyt_ocr = rag_system.read_image(uploaded_file.read())
                st.session_state.messages.append({"role": "user", "content": f"[SKAN DOKUMENTU]\n{odczyt_ocr}\n\nAudyt / Audit:"})
                st.rerun()
    with tab_audio:
        st.warning("🔜")

if user_query := st.chat_input(t['chat_ph']):
    st.session_state.messages.append({"role": "user", "content": user_query})
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