import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag_engine import TachografRAG

def main():
    print("\n--- Rozpoczynam ładowanie Prawa UE (r1 - r4) ---")
    
    # Lista Twoich nowych plików
    pliki = ["data/r1.pdf", "data/r2.pdf", "data/r3.pdf", "data/r4.pdf"]
    wszystkie_chunki = []
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for plik in pliki:
        if os.path.exists(plik):
            print(f"Czytam plik {plik}...")
            loader = PyPDFLoader(plik)
            pages = loader.load()
            chunki = text_splitter.split_documents(pages)
            wszystkie_chunki.extend(chunki)
        else:
            print(f"BŁĄD: Nie znaleziono {plik}. Pomijam.")

    print(f"\nSukces! Przygotowano łącznie {len(wszystkie_chunki)} fragmentów z prawa UE.")
    print("Trwa tłumaczenie formatu dla bazy wektorowej...")
    
    # Tłumaczenie obiektów na słowniki (tak jak poprzednio)
    gotowe_do_bazy = []
    for doc in wszystkie_chunki:
        gotowe_do_bazy.append({
            "text": doc.page_content,
            "metadata": {"source": doc.metadata.get("source", "Rozporządzenie UE")}
        })
    
    print("Trwa ładowanie i wektoryzacja w OpenAI... To potrwa kilka minut. Proszę czekać.")
    
    try:
        rag_system = TachografRAG()
        rag_system.initialize_database(gotowe_do_bazy)
        
        print("\n=== ABSOLUTNY SUKCES ===")
        print("Przepisy UE (Pakiet Mobilności, Czas Pracy, Tacho) zostały dodane do bazy ChromaDB!")
    except Exception as e:
        print(f"\n[X] WYSTĄPIŁ BŁĄD KRYTYCZNY:")
        print(f"Szczegóły błędu: {e}")

if __name__ == "__main__":
    main()