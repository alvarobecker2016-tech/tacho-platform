import requests
from bs4 import BeautifulSoup
from rag_engine import TachografRAG, chunk_legal_text

def pobierz_eurlex_tekst(celex_id):
    print(f"Łączenie z bazą EUR-Lex (CELEX: {celex_id})...")
    url = f"https://eur-lex.europa.eu/legal-content/PL/TXT/HTML/?uri=CELEX:{celex_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    for element in soup(["script", "style", "meta", "noscript"]):
        element.decompose()
        
    tekst = soup.get_text(separator='\n\n', strip=True)
    tekst = '\n'.join([line for line in tekst.split('\n') if line.strip() != ''])
    return tekst

if __name__ == "__main__":
    celex_561 = "32006R0561" # Rozporządzenie 561/2006 (Czas pracy)
    
    try:
        tekst_561 = pobierz_eurlex_tekst(celex_561)
        print("Pobrano Rozporządzenie 561/2006. Liczba znaków:", len(tekst_561))
        
        print("Tnę przepisy na fragmenty...")
        chunki_561 = chunk_legal_text(tekst_561, "Rozporządzenie (WE) nr 561/2006 (Czas jazdy i odpoczynku)")
        
        print(f"Przygotowano {len(chunki_561)} paragrafów. Ładowanie wektorów do bazy ChromaDB...")
        rag_system = TachografRAG()
        rag_system.initialize_database(chunki_561)
        
        print("\n=== SUKCES! ===")
        print("Baza wiedzy zaktualizowana! Agent zna teraz przepisy o czasie pracy kierowców (561/2006).")
        
    except Exception as e:
        print("Wystąpił błąd podczas pobierania lub przetwarzania:", e)