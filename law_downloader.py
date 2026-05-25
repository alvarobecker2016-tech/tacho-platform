import os
import requests

def pobierz_z_eurlex():
    print("\n--- Uruchamiam Automatycznego Pobieracza Prawa (EUR-Lex) ---")

    # 1. Upewniamy się, że folder 'data' istnieje
    if not os.path.exists("data"):
        os.makedirs("data")

    # 2. Słownik z najważniejszymi rozporządzeniami 
    # (Klucz: nazwa pliku na Twoim dysku, Wartość: numer CELEX z EUR-Lex)
    ustawy = {
        "rozp_561_2006_czas_pracy.pdf": "32006R0561",
        "rozp_165_2014_tachografy.pdf": "32014R0165",
        "rozp_1054_2020_pakiet_mobilnosci.pdf": "32020R1054"
    }

    # 3. Oficjalny link do pobierania PDF z EUR-Lex w języku polskim (PL)
    base_url = "https://eur-lex.europa.eu/legal-content/PL/TXT/PDF/?uri=CELEX:"

    # 4. Pętla pobierająca każdy plik ze słownika
    for nazwa_pliku, celex in ustawy.items():
        url = base_url + celex
        sciezka_zapisu = os.path.join("data", nazwa_pliku)
        
        print(f"\nPobieranie: {nazwa_pliku} (CELEX: {celex})...")
        
        try:
            # Używamy nagłówka 'User-Agent', aby serwer UE widział nas jako normalną przeglądarkę, a nie bota atakującego serwer
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers)
            
            # Jeśli serwer odpowiedział kodem 200 (OK), zapisujemy plik
            if response.status_code == 200:
                with open(sciezka_zapisu, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Sukces! Zapisano bezpośrednio w: {sciezka_zapisu}")
            else:
                print(f"❌ Błąd pobierania. Serwer zwrócił kod: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Wystąpił krytyczny błąd podczas pobierania {nazwa_pliku}: {e}")

    print("\n--- Zakończono operację! Twój system jest gotowy na wektoryzację nowej wiedzy. ---")

if __name__ == "__main__":
    pobierz_z_eurlex()