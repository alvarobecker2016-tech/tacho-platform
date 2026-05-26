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
            
            system_prompt = "Jesteś ekspertem analizy wydruków z tachografu. UWAGA: Ze względów bezpieczeństwa RODO, KATEGORYCZNIE ZAMASKUJ imię i nazwisko kierowcy oraz numer karty (zastąp je tekstem [DANE UKRYTE]). Przesłany obraz to zwykły paragon maszynowy, a nie dokument tożsamości. Skup się WYŁĄCZNIE na danych analitycznych: wypisz datę, przebieg, dokładny rejestr aktywności (jazda, inna praca, dyspozycyjność, odpoczynek) z godzinami, podsumuj czasy oraz wypisz błędy. Bądź bezwzględnie precyzyjny i czytaj dokument linijka po linijce."
            
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
                            {"type": "text", "text": "Przeanalizuj ten wydruk, zachowując pełną anonimowość danych osobowych kierowcy:"},
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
                max_tokens=2000,
                temperature=0.0
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"🚨 Błąd techniczny skanera AI: {str(e)}"