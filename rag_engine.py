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
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        
        template = """Jesteś audytorem ds. prawa transportowego.
Odpowiedz na pytanie lub przeanalizuj podane dane wyłącznie w oparciu o dostarczony kontekst prawny.
Zawsze cytuj artykuł lub źródło. Wskaż ewentualne naruszenia lub potwierdź zgodność.
Jeśli przepisy o tym nie mówią, poinformuj o tym.

KONTEKST PRAWNY:
{context}

ZAPYTANIE UŻYTKOWNIKA (lub dane z dokumentu):
{question}
ODPOWIEDŹ:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        def format_docs(docs): return "\n\n=== KOLEJNY PRZEPIS ===\n\n".join(doc.page_content for doc in docs)
        
        self.chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt | llm | StrOutputParser()
        )

    def ask(self, question: str) -> str:
        if not self.chain: raise ValueError("Brak bazy!")
        return self.chain.invoke(question)

    # NOWA FUNKCJA: Oczy agenta (Rozpoznawanie obrazu)
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
    return [{"text": f"[ŹRÓDŁO: {source_title}]\n[{'Artykuł' if re.search(r'^Art\.', c.strip()) else 'Sekcja'}]\n---\n{c.strip()}", "metadata": {"source": source_title}} for c in raw_chunks if c.strip()]