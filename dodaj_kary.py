import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag_engine import TachografRAG

def main():
    print("\n--- Rozpoczynam ładowanie Taryfikatorów Kar i Klasyfikacji UE ---")
    
    pliki = {
        "data/kary_pl.pdf": "Taryfikator ITD (Ustawa o transporcie drogowym - Załącznik 3)",
        "data/kary_ue.pdf": "Rozporządzenie 2016/403 (Klasyfikacja wagi naruszeń UE)"
    }
    
    wszystkie_chunki = []
    # Zmniejszamy chunk_size, bo kary to często krótkie tabelki i konkretne kwoty
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)

    for sciezka, nazwa_zrodla in pliki.items():
        if os.path.exists(sciezka):
            print(f"Czytam: {nazwa_zrodla}...")
            try:
                loader = PyPDFLoader(sciezka)
                pages = loader.load()
                chunki = text_splitter.split_documents(pages)
                for chunk in chunki:
                    chunk.metadata["source"] = nazwa_zrodla
                wszystkie_chunki.extend(chunki)
            except Exception as e:
                print(f"Błąd przy czytaniu {sciezka}: {e}")
        else:
            print(f"BŁĄD: Nie znaleziono {sciezka}. Pomijam.")

    gotowe_do_bazy = []
    for doc in wszystkie_chunki:
        gotowe_do_bazy.append({
            "text": doc.page_content,
            "metadata": {"source": doc.metadata.get("source", "Taryfikator")}
        })
    
    try:
        rag_system = TachografRAG()
        rag_system.initialize_database(gotowe_do_bazy)
        print("\n=== ABSOLUTNY SUKCES ===")
        print("Taryfikatory i ryzyko utraty licencji wgrane do bazy!")
    except Exception as e:
        print(f"\n[X] WYSTĄPIŁ BŁĄD KRYTYCZNY: {e}")

if __name__ == "__main__":
    main()