#!/usr/bin/env python3
"""
Generator certyfikatów GSA - wersja 2.0 (300 DPI, jakość druku)
Nakłada tekst na oryginalne obrazy PNG i generuje PDF gotowy do druku.

Rozdzielczość: 3508 x 2480 px @ 300 DPI (A4 landscape)
Rozmiar pliku: ~1-1.5 MB (doskonała jakość druku)
"""

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import io
import os

# Ścieżki do zasobów
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, 'templates')
FONTS_DIR = os.path.join(SCRIPT_DIR, 'fonts')

# Czcionki
FONT_REGULAR = os.path.join(FONTS_DIR, 'Montserrat-Regular.ttf')
FONT_BOLD = os.path.join(FONTS_DIR, 'Montserrat-Bold.ttf')
FONT_SEMIBOLD = os.path.join(FONTS_DIR, 'Montserrat-SemiBold.ttf')

# Rozmiar obrazu certyfikatu: 3508 x 2480 px @ 300 DPI (A4 landscape)
IMG_W = 3508
IMG_H = 2480
DPI = 300

# Skala względem oryginalnego 2000x1414: 3508/2000 = 1.754
SCALE = 3508 / 2000


def _s(val):
    """Skaluje wartość z oryginalnych 2000px do 3508px."""
    return int(val * SCALE)


# Konfiguracja pozycji tekstu (przeskalowana do 300 DPI)
TEXT_CONFIG_WITH_LOGO = {
    'name_y': _s(635),
    'name_size': _s(72),
    'subtitle_y': _s(738),
    'subtitle_size': _s(40),
    'draw_subtitle': True,
    'course_y': _s(800),
    'course_size': _s(58),
    'location_y': _s(952),
    'location_size': _s(44),
    'cover_rects': [],
}

TEXT_CONFIG_NO_LOGO = {
    'name_y': _s(555),
    'name_size': _s(72),
    'subtitle_y': _s(694),
    'subtitle_size': _s(40),
    'draw_subtitle': False,
    'course_y': _s(770),
    'course_size': _s(52),
    'location_y': _s(989),
    'location_size': _s(44),
    'cover_rects': [(_s(720), _s(975), _s(1010), _s(1030))],
}

# Kolory tekstu
NAME_COLOR = (20, 20, 20)
SUBTITLE_COLOR = (60, 60, 60)
COURSE_COLOR = (20, 20, 20)
LOCATION_COLOR = (20, 20, 20)

# Definicje certyfikatów
CERT_CONFIGS = {
    '1': {
        'template': '1.png',
        'name': 'Certyfikat_TP_PLTP',
        'text_config': TEXT_CONFIG_WITH_LOGO,
    },
    '2': {
        'template': '2_blank.png',
        'name': 'Certyfikat_GYM',
        'text_config': TEXT_CONFIG_WITH_LOGO,
    },
    '3': {
        'template': '3.png',
        'name': 'Certyfikat_GYM_v2',
        'text_config': TEXT_CONFIG_NO_LOGO,
    },
    '4': {
        'template': '4.png',
        'name': 'Certyfikat_TP',
        'text_config': TEXT_CONFIG_NO_LOGO,
    },
}


def draw_centered_text(draw, text, y, font, color, img_width=IMG_W):
    """Rysuje tekst wycentrowany poziomo."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (img_width - text_width) / 2
    draw.text((x, y), text, font=font, fill=color)


def _scaled_font(font_path, base_size, text, max_w=None):
    """Zwraca czcionkę o odpowiednim rozmiarze, skalując w dół jeśli tekst za długi."""
    if max_w is None:
        max_w = int(IMG_W * 0.85)
    size = base_size
    tmp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while size > 30:
        f = ImageFont.truetype(font_path, size)
        bb = tmp_draw.textbbox((0, 0), text, font=f)
        if (bb[2] - bb[0]) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(font_path, 30)


def generate_certificate(
    cert_type,
    imie_nazwisko,
    nazwa_kursu,
    miasto,
    data_ukonczenia,
    output_path=None
):
    """
    Generuje certyfikat jako PDF w jakości druku (300 DPI, ~1 MB).

    Args:
        cert_type: '1', '2', '3' lub '4'
        imie_nazwisko: Imię i nazwisko kursanta
        nazwa_kursu: Nazwa kursu (może zawierać miasto po przecinku)
        miasto: Miasto kursu
        data_ukonczenia: Data ukończenia (np. "11.07.2026")
        output_path: Ścieżka do zapisu PDF (opcjonalna)

    Returns:
        bytes: Zawartość pliku PDF
    """
    config = CERT_CONFIGS[str(cert_type)]
    tc = config['text_config']
    template_path = os.path.join(TEMPLATES_DIR, config['template'])

    def _extract_city(s):
        parts = s.rsplit(',', 1)
        if len(parts) == 2 and not any(c.isdigit() for c in parts[1]):
            return parts[1].strip()
        return ''

    def _strip_city(s):
        parts = s.rsplit(',', 1)
        if len(parts) == 2 and not any(c.isdigit() for c in parts[1]):
            return parts[0].strip()
        return s.strip()

    miasto_kursu = _extract_city(nazwa_kursu)
    if not miasto_kursu:
        miasto_kursu = miasto.strip() if miasto else 'Wrocław'
    nazwa_kursu_clean = _strip_city(nazwa_kursu)

    # Wczytaj obraz tła (już w 300 DPI: 3508x2480)
    img = Image.open(template_path).convert('RGB')

    # Upewnij się że obraz ma właściwy rozmiar
    if img.size != (IMG_W, IMG_H):
        img = img.resize((IMG_W, IMG_H), Image.LANCZOS)

    draw = ImageDraw.Draw(img)

    # Zakryj wbite teksty białym prostokątem
    for rect in tc.get('cover_rects', []):
        draw.rectangle(rect, fill=(255, 255, 255))

    # Załaduj czcionki
    font_name = _scaled_font(FONT_SEMIBOLD, tc['name_size'], imie_nazwisko)
    font_subtitle = ImageFont.truetype(FONT_REGULAR, tc['subtitle_size'])
    font_course = _scaled_font(FONT_REGULAR, tc['course_size'], nazwa_kursu_clean)
    font_location = ImageFont.truetype(FONT_BOLD, tc['location_size'])

    # Narysuj imię i nazwisko
    draw_centered_text(draw, imie_nazwisko, tc['name_y'], font_name, NAME_COLOR)

    # Narysuj 'Ukończył(-a) kurs' tylko jeśli nie ma go w szablonie
    if tc.get('draw_subtitle', True):
        draw_centered_text(draw, 'Ukończył(-a) kurs', tc['subtitle_y'], font_subtitle, SUBTITLE_COLOR)

    # Narysuj nazwę kursu (bez miasta)
    draw_centered_text(draw, nazwa_kursu_clean, tc['course_y'], font_course, COURSE_COLOR)

    # Narysuj miejsce wydania (zawsze Wrocław) i datę
    location_text = f'Wrocław, {data_ukonczenia}'
    draw_centered_text(draw, location_text, tc['location_y'], font_location, LOCATION_COLOR)

    # Konwertuj do PDF w jakości druku:
    # - JPEG quality=100 (maksymalna jakość, brak artefaktów)
    # - subsampling=0 (brak subsamplingu koloru - lepsza ostrość)
    # - ReportLab do osadzenia w PDF z metadanymi DPI
    jpeg_buf = io.BytesIO()
    img.save(jpeg_buf, format='JPEG', quality=100, dpi=(DPI, DPI), subsampling=0, optimize=False)
    jpeg_buf.seek(0)

    pdf_buf = io.BytesIO()
    c = rl_canvas.Canvas(pdf_buf, pagesize=landscape(A4))
    c.drawImage(ImageReader(jpeg_buf), 0, 0, width=297*mm, height=210*mm, preserveAspectRatio=False)
    c.save()
    pdf_bytes = pdf_buf.getvalue()

    # Zapisz do pliku jeśli podano ścieżkę
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes


def generate_all_certificates(
    imie_nazwisko,
    nazwa_kursu,
    miasto,
    data_ukonczenia,
    output_dir=None
):
    """Generuje wszystkie 4 certyfikaty dla kursanta."""
    results = {}
    safe_name = imie_nazwisko.strip().replace(' ', '_').replace('/', '-')

    for cert_type, config in CERT_CONFIGS.items():
        cert_name = config['name']
        filename = f"{safe_name}_{cert_name}.pdf"

        if output_dir:
            output_path = os.path.join(output_dir, filename)
        else:
            output_path = None

        pdf_bytes = generate_certificate(
            cert_type=cert_type,
            imie_nazwisko=imie_nazwisko,
            nazwa_kursu=nazwa_kursu,
            miasto=miasto,
            data_ukonczenia=data_ukonczenia,
            output_path=output_path
        )

        results[cert_name] = {
            'bytes': pdf_bytes,
            'path': output_path,
            'filename': filename
        }

    return results


if __name__ == '__main__':
    print("Generowanie testowych certyfikatów (300 DPI, JPEG q=100)...")

    output_dir = '/tmp/gsa_test_300dpi'
    os.makedirs(output_dir, exist_ok=True)

    results = generate_all_certificates(
        imie_nazwisko="Jan Kowalski",
        nazwa_kursu="Kurs Trenera Personalnego",
        miasto="Wrocław",
        data_ukonczenia="11.07.2026",
        output_dir=output_dir
    )

    for name, data in results.items():
        size_mb = len(data['bytes']) / 1024 / 1024
        print(f"  ✓ {data['filename']} ({size_mb:.2f} MB) → {data['path']}")

    print(f"\nGotowe! Pliki zapisane w: {output_dir}")
