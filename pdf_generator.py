import io
import os
import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import datetime

def normalize_chars(text):
    """Zastępuje polskie znaki na wypadek braku odpowiedniej czcionki"""
    if not text:
        return ""
    replacements = {'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
                    'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'}
    for pl, ascii_char in replacements.items():
        text = text.replace(pl, ascii_char)
    return text

def create_defense_pdf(statement_text, full_name, company_name):
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        except Exception:
            pass 
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Roboto', font_path))
        style_normal = ParagraphStyle('RobotoNormal', parent=styles['Normal'], fontName='Roboto', fontSize=11, leading=15)
        style_title = ParagraphStyle('RobotoTitle', parent=styles['Title'], fontName='Roboto', fontSize=16, spaceAfter=20, alignment=1)
    else:
        statement_text = normalize_chars(statement_text)
        full_name = normalize_chars(full_name)
        company_name = normalize_chars(company_name)
        style_normal = styles['Normal']
        style_title = styles['Title']

    story = []
    
    # Nagłówek
    story.append(Paragraph("<b>OSWIADCZENIE KIEROWCY / WYJASNIENIE (ART. 12)</b>", style_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Kierowca:</b> {full_name}", style_normal))
    
    # LOGIKA B2C: Ukrywa Przewoźnika, jeśli to kierowca niezależny
    if company_name and company_name.strip() != "" and company_name != "Kierowca Indywidualny":
        story.append(Paragraph(f"<b>Przewoznik:</b> {company_name}", style_normal))
    else:
        story.append(Paragraph(f"<b>Status:</b> Kierowca Niezalezny", style_normal))
        
    story.append(Paragraph(f"<b>Data wydruku:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", style_normal))
    story.append(Spacer(1, 20))
    
    # Czysty tekst bez gwiazdek Markdown
    for line in statement_text.split('\n'):
        line_clean = line.replace('**', '').replace('*', '').strip()
        if line_clean:
            story.append(Paragraph(line_clean, style_normal))
            story.append(Spacer(1, 6))
            
    # Podpis
    story.append(Spacer(1, 40))
    story.append(Paragraph("...................................................................", style_normal))
    story.append(Paragraph("(Czytelny podpis kierowcy)", style_normal))

    doc.build(story)
    return buffer.getvalue()