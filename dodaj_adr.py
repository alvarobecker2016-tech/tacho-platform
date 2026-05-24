import requests
from bs4 import BeautifulSoup
from rag_engine import TachografRAG, chunk_legal_text

def pobierz_eurlex_tekst(celex_id):
    print(f"Pobieranie dyrektywy ADR {celex_id} z EUR-Lex...")
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
    celex_adr = "32008L0068" # Dyrektywa UE 2008/68/WE (Towary niebezpieczne)
    
    try:
        tekst_adr = pobierz_eurlex_tekst(celex_adr)
        print("Pobrano przepisy ADR. Liczba znaków:", len(tekst_adr))
        
        print("Tnę przepisy na fragmenty...")
        chunki_adr = chunk_legal_text(tekst_adr, "Dyrektywa UE 2008/68/WE (ADR)")
        
        print(f"Przygotowano {len(chunki_adr)} paragrafów. Ładowanie do bazy...")
        rag_system = TachografRAG()
        rag_system.initialize_database(chunki_adr)
        
        print("\n=== SUKCES! ===")
        print("Baza wiedzy zaktualizowana. Twoja baza ChromaDB ma teraz przepisy o tachografach ORAZ o ADR!")
        
    except Exception as e:
        print("Wystąpił błąd:", e)