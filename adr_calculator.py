# Mini-Baza Danych (Wyciąg z Tabeli A ADR)
# W przyszłości możesz tu dopisać kolejne numery UN
TABELA_A = {
    "1203": {"nazwa": "PALIWO SILNIKOWE (BENZYNA)", "kategoria": 2},
    "1942": {"nazwa": "AZOTAN AMONU", "kategoria": 3},
    "1202": {"nazwa": "OLEJ NAPĘDOWY (DIESEL)", "kategoria": 3},
    "1965": {"nazwa": "GAZY WĘGLOWODOROWE SKROPLONE (LPG)", "kategoria": 2},
    "1090": {"nazwa": "ACETON", "kategoria": 2},
    "0027": {"nazwa": "PROCH CZARNY", "kategoria": 1},
    "0074": {"nazwa": "DIAZODINITROFENOL", "kategoria": 0} # Kat. 0 - brak zwolnienia
}

def oblicz_1136(lista_ladunkow):
    """
    Funkcja przyjmuje listę słowników, np:
    [{"un": "1203", "ilosc": 200}, {"un": "1942", "ilosc": 100}]
    I zwraca pełny, twardy raport matematyczny.
    """
    
    # Mnożniki zgodnie z przepisem 1.1.3.6.4 ADR
    mnozniki_adr = {
        0: float('inf'),  # Nieskończoność - od razu przekracza limit 1000
        1: 50, 
        2: 3, 
        3: 1, 
        4: 0
    }
    
    suma_punktow = 0
    szczegoly = []
    
    for ladunek in lista_ladunkow:
        un = str(ladunek["un"]).strip()
        ilosc = float(ladunek["ilosc"])
        
        if un not in TABELA_A:
            return {"error": f"Brak danych dla UN {un}. Dodaj go do bazy w kodzie."}
            
        dane_un = TABELA_A[un]
        mnoznik = mnozniki_adr[dane_un["kategoria"]]
        punkty = ilosc * mnoznik
        suma_punktow += punkty
        
        szczegoly.append({
            "un": un,
            "nazwa": dane_un["nazwa"],
            "kategoria": dane_un["kategoria"],
            "ilosc": ilosc,
            "mnoznik": mnoznik,
            "punkty": punkty
        })
        
    zwolniony = suma_punktow <= 1000
    
    return {
        "status": "SUKCES",
        "suma_punktow": suma_punktow,
        "zwolniony": zwolniony,
        "szczegoly": szczegoly
    }