import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag_engine import TachografRAG

def main():
    print("\n--- Rozpoczynam rozbudowę bazy wiedzy EU CORE & LOCAL LAYER ---")
    
    # Słownik definiujący pliki oraz ich profesjonalne nazwy źródłowe do cytowania
    baza_plikow = {
        "data/r1.pdf": "Rozporządzenie UE",
        "data/r2.pdf": "Rozporządzenie UE",
        "data/r3.pdf": "Rozporządzenie UE",
        "data/r4.pdf": "Rozporządzenie UE",
        "data/ue_pakiet.pdf": "Rozporządzenie (UE) 2020/1054 (Pakiet Mobilności)",
        "data/pl_tacho.pdf": "Polska Ustawa o czasie pracy kierowców (Pora Nocna)"
    }
    
    wszystkie_chunki = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)

    for sciezka, pelna_nazwa in baza_plikow.items():
        if os.path.exists(sciezka):
            print(f"Przetwarzam i analizuję: {sciezka} -> {pelna_nazwa}")
            loader = PyPDFLoader(sciezka)
            pages = loader.load()
            chunki = text_splitter.split_documents(pages)
            
            # Wstrzykujemy odpowiednie źródło bezpośrednio do metadanych każdego fragmentu
            for chunk in chunki:
                chunk.metadata["source"] = pelna_nazwa
                
            wszystkie_chunki.extend(chunki)
        else:
            print(f"Informacja: Pomiędzy plikami brakuje {sciezka} (Jeśli to plik r1-r4 i został skasowany, to normalne).")

    if not wszystkie_chunki:
        print("🚨 BŁĄD: Nie znaleziono żadnych plików PDF do wgrania!")
        return

    print(f"\nSukces! Przygotowano łącznie {len(wszystkie_chunki)} fragmentów wiedzy.")
    print("Trwa tłumaczenie formatu dla bazy wektorowej ChromaDB...")
    
    gotowe_do_bazy = []
    for doc in wszystkie_chunki:
        gotowe_do_bazy.append({
            "text": doc.page_content,
            "metadata": doc.metadata
        })
    
    print("Trwa ładowanie i wektoryzacja w OpenAI... To potrwa dłuższą chwilę. Proszę czekać.")
    
    try:
        rag_system = TachografRAG()
        rag_system.initialize_database(gotowe_do_bazy)
        
        print("\n=== ABSOLUTNY SUKCES WDROŻENIA ===")
        print("Pakiet Mobilności oraz Polskie Prawo Krajowe (Pora Nocna) siedzą w bazie danych!")
    except Exception as e:
        print(f"\n[X] WYSTĄPIŁ BŁĄD KRYTYCZNY:")
        print(f"Szczegóły błędu: {e}")

if __name__ == "__main__":
    main()