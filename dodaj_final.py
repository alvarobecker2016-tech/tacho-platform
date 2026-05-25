import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag_engine import TachografRAG

def main():
    print("\n--- Rozpoczynam ładowanie Ostatecznych Filarów (f1 - f4) ---")
    
    # Pliki z przypisanymi dokładnymi nazwami dla AI!
    pliki = {
        "data/f1.pdf": "Dyrektywa 2020/1057 (Delegowanie kierowców i IMI)",
        "data/f2.pdf": "Rozporządzenie 1072/2009 (Kabotaż i Rynek)",
        "data/f3.pdf": "Dyrektywa 96/53/WE (Wymiary, Masy i Naciski)",
        "data/f4.pdf": "Konwencja CMR"
    }
    
    wszystkie_chunki = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for sciezka, nazwa_zrodla in pliki.items():
        if os.path.exists(sciezka):
            print(f"Czytam: {nazwa_zrodla}...")
            try:
                loader = PyPDFLoader(sciezka)
                pages = loader.load()
                chunki = text_splitter.split_documents(pages)
                # Wstrzykujemy dokładną nazwę źródła do metadanych!
                for chunk in chunki:
                    chunk.metadata["source"] = nazwa_zrodla
                wszystkie_chunki.extend(chunki)
            except Exception as e:
                print(f"Błąd przy czytaniu {sciezka}: {e}")
        else:
            print(f"BŁĄD: Nie znaleziono {sciezka}. Pomijam.")

    print(f"\nSukces! Przygotowano {len(wszystkie_chunki)} fragmentów ostatecznej wiedzy.")
    print("Trwa wektoryzacja w OpenAI i zapis do bazy ChromaDB...")
    
    gotowe_do_bazy = []
    for doc in wszystkie_chunki:
        gotowe_do_bazy.append({
            "text": doc.page_content,
            "metadata": {"source": doc.metadata.get("source", "Inne Prawo Transportowe")}
        })
    
    try:
        rag_system = TachografRAG()
        rag_system.initialize_database(gotowe_do_bazy)
        print("\n=== ABSOLUTNY SUKCES ===")
        print("Wszystkie 4 filary zostały wstrzyknięte do mózgu AI!")
    except Exception as e:
        print(f"\n[X] WYSTĄPIŁ BŁĄD KRYTYCZNY: {e}")

if __name__ == "__main__":
    main()