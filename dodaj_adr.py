import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag_engine import TachografRAG

def main():
    print("\n--- Rozpoczynam ładowanie ADR ---")
    
    file_path1 = "data/t1.pdf"
    file_path2 = "data/t2.pdf"
    
    if not os.path.exists(file_path1) or not os.path.exists(file_path2):
        print(f"BŁĄD: Nie znaleziono plików w folderze 'data'. Upewnij się, że nazywają się t1.pdf i t2.pdf")
        return

    print("[1/2] Czytam Tom I...")
    loader1 = PyPDFLoader(file_path1)
    pages1 = loader1.load()
    
    print("[2/2] Czytam Tom II...")
    loader2 = PyPDFLoader(file_path2)
    pages2 = loader2.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    print("Dzielenie tekstu na fragmenty...")
    chunki_tom1 = text_splitter.split_documents(pages1)
    chunki_tom2 = text_splitter.split_documents(pages2)
    
    wszystkie_chunki = chunki_tom1 + chunki_tom2
    
    print(f"\nSukces! Przygotowano łącznie {len(wszystkie_chunki)} fragmentów z CAŁEJ umowy ADR.")
    print("Trwa tłumaczenie formatu dla bazy wektorowej...")
    
    # --- NOWY KOD: Tłumaczenie obiektów Document na słowniki dla RAG Engine ---
    gotowe_do_bazy = []
    for doc in wszystkie_chunki:
        gotowe_do_bazy.append({
            "text": doc.page_content,
            "metadata": {"source": doc.metadata.get("source", "Umowa ADR 2023")}
        })
    
    print("Trwa ładowanie i wektoryzacja w OpenAI... To potrwa kilka minut. Proszę czekać.")
    
    try:
        rag_system = TachografRAG()
        # Wysyłamy nasze przetłumaczone słowniki:
        rag_system.initialize_database(gotowe_do_bazy)
        
        print("\n=== ABSOLUTNY SUKCES ===")
        print("Tysiące stron przepisów ADR zostało wstrzyknięte do bazy ChromaDB.")
    except Exception as e:
        print(f"\n[X] WYSTĄPIŁ BŁĄD KRYTYCZNY:")
        print(f"Szczegóły błędu: {e}")

if __name__ == "__main__":
    main()