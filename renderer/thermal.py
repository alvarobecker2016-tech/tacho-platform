import cv2
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime, timedelta

class SyntheticTachoGenerator:
    def __init__(self, font_path="fonts/receipt.ttf"):
        self.font_path = font_path
        self.width = 600
        self.bg_color = (240, 245, 235) # Lekko pożółkły papier termiczny
        self.text_color = (30, 30, 30)  # Wyblakły czarny/szary
        
        # Sprawdzamy czy czcionka istnieje
        if not os.path.exists(self.font_path):
            print(f"⚠️ UWAGA: Nie znaleziono czcionki w {self.font_path}. Używam domyślnej.")
            self.font = ImageFont.load_default()
        else:
            self.font = ImageFont.truetype(self.font_path, 28)
            self.font_large = ImageFont.truetype(self.font_path, 36)

    def generate_random_scenario(self) -> list:
        """Generuje logiczny, losowy dzień pracy kierowcy"""
        events = []
        # Losowy start między 04:00 a 10:00
        current_time = datetime.strptime(f"{random.randint(4,10):02d}:00", "%H:%M")
        
        symbols = ['x', 'o', 'h', 'X'] # Praca, Jazda, Przerwa, Gotowość
        
        for _ in range(random.randint(5, 12)): # Od 5 do 12 zdarzeń w ciągu dnia
            symbol = random.choice(symbols)
            # Losowy czas trwania od 15 min do 4 godzin
            duration = timedelta(minutes=random.randint(15, 240)) 
            
            time_str = current_time.strftime("%H:%M")
            events.append(f"{time_str}   {symbol}")
            
            current_time += duration
            if current_time.hour >= 23: break # Koniec doby
            
        return events

    def create_synthetic_receipt(self, output_path: str):
        """Rysuje paragon, dodaje szum termiczny i zapisuje jako plik"""
        events = self.generate_random_scenario()
        
        # Obliczamy wysokość paragonu na podstawie ilości zdarzeń
        height = 300 + (len(events) * 40)
        
        # 1. Tworzymy idealny cyfrowy obraz (Pillow)
        img_pil = Image.new('RGB', (self.width, height), color=self.bg_color)
        draw = ImageDraw.Draw(img_pil)
        
        # Rysujemy nagłówek
        draw.text((self.width//2 - 100, 30), "TACHOGRAPH VDO", font=self.font_large, fill=self.text_color)
        draw.text((self.width//2 - 80, 80), "24h Driver Card", font=self.font, fill=self.text_color)
        draw.text((50, 130), "-"*40, font=self.font, fill=self.text_color)
        
        # Rysujemy zdarzenia (Oś czasu)
        y_pos = 160
        for event in events:
            draw.text((50, y_pos), event, font=self.font, fill=self.text_color)
            y_pos += 40
            
        draw.text((50, y_pos), "-"*40, font=self.font, fill=self.text_color)
        draw.text((self.width//2 - 50, y_pos + 30), "END OF DAY", font=self.font, fill=self.text_color)

        # 2. Konwersja do OpenCV, by dodać "Brud i Szum"
        img_cv = np.array(img_pil)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

        # A) Thermal Blur (Rozmycie typowe dla tanich drukarek termicznych)
        if random.random() > 0.3:
            img_cv = cv2.GaussianBlur(img_cv, (3, 3), 0)

        # B) Złe oświetlenie (Cienie z jednej strony)
        shadow = np.zeros_like(img_cv, dtype=np.float32)
        gradient = np.linspace(0.5, 1.2, self.width) # Ciemniej po lewej, jaśniej po prawej
        for i in range(self.width):
            shadow[:, i] = img_cv[:, i] * gradient[i]
        img_cv = np.clip(shadow, 0, 255).astype(np.uint8)

        # C) Szum matrycy telefonu (Salt & Pepper / ISO noise)
        noise = np.random.normal(0, 15, img_cv.shape).astype(np.uint8)
        img_cv = cv2.add(img_cv, noise)

        # Zapisz gotowy syntetyczny wydruk
        cv2.imwrite(output_path, img_cv)
        print(f"🏭 Wygenerowano syntetyczny wydruk: {output_path}")
        return output_path
