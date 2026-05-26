import base64
from openai import OpenAI

class TachografRAG:
    def __init__(self):
        self.client = OpenAI()

    def load_existing_database(self):
        return True

    def ask(self, user_query):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Jesteś Pocket DGSA & Tacho - asystentem prawnym kierowcy ciężarówki. Odpowiadaj rzeczowo, konkretnie i zwięźle w języku użytkownika. Podawaj proste interpretacje przepisów Unii Europejskiej (Pakiet Mobilności, Rozporządzenie 561/2006)."},
                    {"role": "user", "content": user_query}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"🚨 Błąd silnika AI (ask): {str(e)}"

    def generate_defense_statement(self, user_query, jezyk_pism):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"Jesteś prawnikiem w transporcie międzynarodowym. Wygeneruj oficjalne pismo obronne/wyjaśniające do organu kontrolnego w języku: {jezyk_pism}. Używaj formalnego słownictwa."},
                    {"role": "user", "content": user_query}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"🚨 Błąd generowania oświadczenia: {str(e)}"

    def calculate_penalty(self, user_query):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Jesteś audytorem od taryfikatorów kar ITD/BAG. Oszacuj potencjalną wysokość kary. Podaj podstawę prawną i widełki kwotowe."},
                    {"role": "user", "content": user_query}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"🚨 Błąd kalkulatora kar: {str(e)}"

    def read_image(self, image_bytes):
        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # --- POTĘŻNY PROMPT PRAWNICZY DLA AUDYTU TACHO ---
            system_prompt = (
                "Jesteś surowym inspektorem ITD i wybitnym Prawnikiem Transportowym (Pocket DGSA). "
                "UWAGA: Ze względów bezpieczeństwa RODO, KATEGORYCZNIE ZAMASKUJ imię i nazwisko kierowcy oraz numer karty (zastąp je tekstem [DANE UKRYTE]). "
                "Twoim zadaniem NIE JEST zrobienie suchego streszczenia. Oczekuję brutalnego AUDYTU PRAWNEGO wg Rozporządzenia 561/2006 WE.\n\n"
                "Zwróć odpowiedź w 4 wyraźnych punktach:\n"
                "1️⃣ FAKTY: Krótkie podsumowanie czasów z wydruku (jazda, praca, odpoczynek).\n"
                "2️⃣ WYKRYTE NARUSZENIA: Przeanalizuj wpisy chronologicznie z lupą! Szukaj bezlitośnie błędów. Np. czy odpoczynek został przerwany nagłą 1-2 minutową jazdą (częsty błąd podjazdu pod rampę lub przestawienia auta)? Czy są jakieś błędy? Wypisz je wyraźnie, traktując każdy błąd jak mandat.\n"
                "3️⃣ POTENCJALNE KARY: Jeśli wykryłeś naruszenie (np. ten nieszczęsny przerwany odpoczynek), oszacuj kwotę kary według taryfikatorów ITD lub niemieckiego BAG.\n"
                "4️⃣ Twoja LINIA OBRONY: Daj kierowcy gotowe koło ratunkowe. Podyktuj mu DOKŁADNIE co ma zapisać długopisem na rewersie tego konkretnego wydruku (np. powołanie na Art. 12 / 561/2006 WE z powodu braku miejsca na parkingu, czy polecenia służb), aby uniknąć mandatu."
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Przeprowadź audyt prawny tego wydruku tacho. Znajdź wykroczenia i przygotuj linię obrony z artykułami:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2500,
                temperature=0.1
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"🚨 Błąd techniczny skanera AI: {str(e)}"