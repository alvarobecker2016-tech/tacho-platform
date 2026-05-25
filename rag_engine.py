import os
import re
import base64
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

class TachografRAG:
    def __init__(self, persist_directory="./chroma_db_prawdziwa"):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vectorstore = None
        self.chain = None
        
    def initialize_database(self, processed_chunks):
        print("Inicjalizacja bazy wektorowej ChromaDB...")
        documents = [Document(page_content=c["text"], metadata=c["metadata"]) for c in processed_chunks]
        self.vectorstore = Chroma.from_documents(documents=documents, embedding=self.embeddings, persist_directory=self.persist_directory)
        self._build_rag_chain()

    def load_existing_database(self):
        if os.path.exists(self.persist_directory):
            print("Ładowanie istniejącej bazy ChromaDB...")
            self.vectorstore = Chroma(persist_directory=self.persist_directory, embedding_function=self.embeddings)
            self._build_rag_chain()
            return True
        return False

    def _build_rag_chain(self):
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})
        
        # WAŻNE: Zmieniamy temperaturę na 0.0 (AI staje się bezlitosnym, logicznym robotem bez fantazji)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        
        # 1. Nasz potężny System Prompt (Kaganiec na AI)
        template = """Jesteś wybitnym ekspertem ds. europejskiego prawa transportowego i głównym doradcą DGSA.
Twoim zadaniem jest odpowiadanie na pytania użytkowników WYŁĄCZNIE na podstawie dostarczonego poniżej KONTEKSTU z bazy danych (przepisów ADR, Pakietu Mobilności, rozporządzeń 561/2006, 165/2014 itp.).

ZASADY BEZWZGLĘDNE:
1. BRAK ZGADYWANIA: Jeśli w dostarczonym kontekście NIE MA odpowiedzi na pytanie, powiedz wprost: "Zgodnie z wgraną bazą wiedzy nie posiadam obecnie artykułu, który o tym mówi". Pod żadnym pozorem nie używaj wiedzy spoza dostarczonego kontekstu.
2. PRECYZJA: Opieraj się na konkretnych artykułach, punktach, przepisach szczególnych (SP) i kodach (np. UN 1203). Rozpisuj skomplikowane procesy na czytelne punkty.
3. CYTOWANIE: Na samym końcu swojej odpowiedzi ZAWSZE dodaj nową linijkę i wypisz źródła, z których skorzystałeś, używając formatu: [ŹRÓDŁO: nazwa dokumentu z metadanych].

KONTEKST PRAWNY (Dokumenty z Twojej bazy RAG):
{context}

ZAPYTANIE UŻYTKOWNIKA (lub dane z dokumentu):
{question}
ODPOWIEDŹ:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # 2. Naprawiamy formatowanie i tłumaczymy brzydkie nazwy plików na ładne nazwy ustaw
        def format_docs(docs): 
            slownik_zrodel = {
                "data/t1.pdf": "Umowa ADR 2023 (Tom I)",
                "data/t2.pdf": "Umowa ADR 2023 (Tom II)",
                "data/r1.pdf": "Rozporządzenie (WE) nr 561/2006 (Czas Pracy)",
                "data/r2.pdf": "Rozporządzenie (UE) nr 165/2014 (Tachografy)",
                "data/r3.pdf": "Pakiet Mobilności (Rozporządzenie 1054/2020)",
                "data/r4.pdf": "Europejskie Prawo Transportowe"
            }
            
            wyniki = []
            for doc in docs:
                surowe_zrodlo = doc.metadata.get('source', 'Nieznane źródło')
                ladne_zrodlo = slownik_zrodel.get(surowe_zrodlo, surowe_zrodlo)
                wyniki.append(f"Tekst: {doc.page_content}\nŹródło: {ladne_zrodlo}")
                
            return "\n\n=== KOLEJNY PRZEPIS ===\n\n".join(wyniki)
        
        self.chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt | llm | StrOutputParser()
        )

    def ask(self, question: str) -> str:
        if not self.chain: raise ValueError("Brak bazy!")
        return self.chain.invoke(question)

    # Funkcja: Oczy agenta (Rozpoznawanie obrazu)
    def read_image(self, image_bytes):
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        chat = ChatOpenAI(model="gpt-4o-mini", max_tokens=1000)
        
        msg = chat.invoke([
            HumanMessage(content=[
                {"type": "text", "text": "Odczytaj dokładnie wszystkie dane, liczby, daty i kody z tego dokumentu transportowego (np. wydruku z tachografu lub certyfikatu). Zwróć tylko czysty, odczytany tekst bez zbędnych komentarzy."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ])
        ])
        return msg.content

# Część wykonawcza (na potrzeby wektoryzacji z terminala)
def chunk_legal_text(raw_text, source_title):
    pattern = r'(?=Art\.\s*\d+[a-z]*\.)'
    raw_chunks = re.split(pattern, raw_text)
    
    results = []
    for c in raw_chunks:
        clean_c = c.strip()
        if clean_c:
            typ_tekstu = 'Artykuł' if clean_c.startswith('Art.') else 'Sekcja'
            gotowy_tekst = f"[ŹRÓDŁO: {source_title}]\n[{typ_tekstu}]\n---\n{clean_c}"
            
            results.append({
                "text": gotowy_tekst,
                "metadata": {"source": source_title}
            })
            
    return results