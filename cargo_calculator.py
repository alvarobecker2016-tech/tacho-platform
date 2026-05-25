import math

def oblicz_pasy_docisk(waga_kg, tarcie_mu, stf_dan, kat_alfa):
    """
    Kalkulator mocowania ładunku przez docisk (EN 12195-1).
    Kierunek wzdłużny (najbardziej narażony na hamowanie, współczynnik cx = 0.8).
    """
    cx = 0.8  # Przyspieszenie przy hamowaniu do przodu
    cz = 1.0  # Przyspieszenie pionowe
    
    fg = waga_kg  # Siła ciężkości w daN (~kg)
    kat_rad = math.radians(kat_alfa)
    sin_a = math.sin(kat_rad)
    
    if sin_a <= 0 or tarcie_mu <= 0 or stf_dan <= 0:
        return {"error": "Parametry (kąt, tarcie, STF) muszą być większe od 0."}
        
    # Wzór na liczbę pasów dociskowych
    licznik = (cx - tarcie_mu * cz) * fg
    
    if licznik <= 0:
        return {
            "pasy": 0, 
            "wiadomosc": "Samo tarcie utrzymuje ładunek przed przesunięciem do przodu. Wymagane są jedynie pasy zabezpieczające przed przechyleniem na boki."
        }
        
    mianownik = tarcie_mu * stf_dan * sin_a
    n = licznik / mianownik
    
    return {
        "pasy": math.ceil(n),
        "dokladnie": round(n, 2),
        "wiadomosc": f"Aby ładunek nie poleciał do przodu podczas ostrego hamowania, musisz użyć minimum {math.ceil(n)} pasów dociskowych."
    }

# Słownik typowych współczynników tarcia (drewno, plastik, metal)
WSPOLCZYNNIKI_TARCIA = {
    "Drewno na drewnie (0.4)": 0.4,
    "Drewno na ryflowanej blasze (0.2)": 0.2,
    "Paleta na antypoślizgowej macie (0.6)": 0.6,
    "Stal na stali (0.1) - Bardzo ślisko!": 0.1,
    "Beton na drewnie (0.5)": 0.5
}