import requests
from bs4 import BeautifulSoup
import pdfplumber
import io

def pobierz_eurlex_tekst(celex_id):
    print(f"Pobieranie dokumentu {celex_id} z EUR-Lex...")
    url = f"https://eur-lex.europa.eu/legal-content/PL/TXT/HTML/?uri=CELEX:{celex_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    for element in soup(["script", "style", "meta", "noscript"]):
        element.decompose()
    tekst = soup.get_text(separator='\n\n', strip=True)
    tekst = '\n'.join([line for line in tekst.split('\n') if line.strip() != ''])
    return tekst

def pobierz_isap_tekst(pdf_url):
    print(f"Pobieranie i analizowanie PDF z ISAP: {pdf_url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(pdf_url, headers=headers)
    response.raise_for_status()
    pdf_file = io.BytesIO(response.content)
    tekst_calkowity = ""
    with pdfplumber.open(pdf_file) as pdf:
        for strona in pdf.pages:
            strona_tekst = strona.extract_text()
            if strona_tekst:
                tekst_calkowity += strona_tekst + "\n\n"
    return tekst_calkowity

if __name__ == "__main__":
    celex_tachografy = "32014R0165" 
    try:
        tekst_ue = pobierz_eurlex_tekst(celex_tachografy)
        with open("ue_rozporzadzenie_165_2014.txt", "w", encoding="utf-8") as f:
            f.write(tekst_ue)
        print("Pobrano przepisy UE. Liczba znaków:", len(tekst_ue))
    except Exception as e:
        print("Błąd pobierania EUR-Lex:", e)

    url_isap_ustawa = "https://isap.sejm.gov.pl/isap.nsf/download.xsp/WDU20180001480/U/D20181480Lj.pdf"
    try:
        tekst_pl = pobierz_isap_tekst(url_isap_ustawa)
        with open("pl_ustawa_o_tachografach.txt", "w", encoding="utf-8") as f:
            f.write(tekst_pl)
        print("Pobrano ustawę z ISAP. Liczba znaków:", len(tekst_pl))
    except Exception as e:
        print("Błąd pobierania ISAP:", e)