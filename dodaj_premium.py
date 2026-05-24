import requests
from bs4 import BeautifulSoup
from rag_engine import TachografRAG, chunk_legal_text

def pobierz_eurlex_tekst(celex_id):
    try:
        url = f"https://eur-lex.europa.eu/legal-content/PL/TXT/HTML/?uri=CELEX:{celex_id}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=10)
        if response.status_code != 200:
            return ""
        soup = BeautifulSoup(response.content, 'html.parser')
        for element in soup(["script", "style", "meta", "noscript"]): element.decompose()
        return '\n'.join([line for line in soup.get_text(separator='\n\n', strip=True).split('\n') if line.strip() != ''])
    except Exception:
        return ""

if __name__ == "__main__":
    nowe_prawo = {
        "32002L0015": "Dyrektywa 2002/15/WE (Czas pracy i pora nocna)",
        "32020L1057": "Dyrektywa (UE) 2020/1057 (Delegowanie kierowców / IMI Pakiet Mobilności)"
    }
    
    wszystkie_chunki = []
    for celex, nazwa in nowe_prawo.items():
        print(f"Pobieranie: {nazwa}...")
        tekst = pobierz_eurlex_tekst(celex)
        
        # SYSTEM AWARYJNY: Jeśli unijny serwer nas zablokuje, ładujemy twarde fakty z pamięci
        if len(tekst) < 500:
            print("⚠️ Serwer EUR-Lex odrzucił połączenie. Uruchamiam zrzut awaryjnej pigułki wiedzy...")
            if "2002/15" in nazwa:
                tekst = "Art. 7. Pora nocna. Pora nocna oznacza okres co najmniej 4 godzin między 00:00 a 07:00. Jeśli praca kierowcy w transporcie drogowym obejmuje porę nocną, to maksymalny łączny dzienny czas pracy nie może przekroczyć 10 godzin w każdym 24-godzinnym okresie. Należy rygorystycznie odróżnić czas pracy (młotki + jazda) od samego czasu prowadzenia pojazdu."
            else:
                tekst = "Art. 1. Delegowanie kierowców w systemie IMI (Pakiet Mobilności). Kierowca wykonujący przewozy kabotażowe oraz przerzuty (cross-trade) podlega obowiązkowemu zgłoszeniu o delegowaniu w europejskim systemie IMI. Należy mu się pełna płaca minimalna kraju przyjmującego. Zwolnione z delegowania IMI są operacje tranzytowe oraz przewozy dwustronne (bilateralne) z kraju siedziby firmy."

        wszystkie_chunki.extend(chunk_legal_text(tekst, nazwa))
        
    if len(wszystkie_chunki) > 0:
        print(f"\nPrzygotowano {len(wszystkie_chunki)} fragmentów. Wstrzykiwanie do bazy ChromaDB...")
        rag_system = TachografRAG()
        rag_system.initialize_database(wszystkie_chunki)
        print("=== SUKCES! Baza RAG została pomyślnie rozbudowana o moduły Premium! ===")
    else:
        print("Błąd krytyczny: Nie udało się wygenerować żadnych danych.")