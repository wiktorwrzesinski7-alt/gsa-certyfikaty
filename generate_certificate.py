#!/usr/bin/env python3
"""
GSA Certificate Generator v4.0
Generuje certyfikaty w jakości druku 300 DPI.

Podejście:
1. Otwórz szablon PDF i nanieś tekst (imię, data, numer)
2. Wyrenderuj stronę jako obraz 300 DPI (raster)
3. Zapisz obraz jako nowy PDF — pełna jakość druku, ~2-3 MB

Dzięki temu wszystkie elementy (logo, mapa, podpis) są w 300 DPI.
"""

import fitz  # PyMuPDF
import io
import os
from datetime import datetime

# Ścieżki
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, 'templates')
FONTS_DIR = os.path.join(SCRIPT_DIR, 'fonts')

FONT_REGULAR = os.path.join(FONTS_DIR, 'Montserrat-Regular.ttf')
FONT_BOLD = os.path.join(FONTS_DIR, 'Montserrat-Bold.ttf')

# Polskie nazwy miesięcy
POLISH_MONTHS = {
    1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia",
    5: "maja", 6: "czerwca", 7: "lipca", 8: "sierpnia",
    9: "września", 10: "października", 11: "listopada", 12: "grudnia"
}

# Szablony certyfikatów
TEMPLATES = {
    "TP": os.path.join(TEMPLATES_DIR, "PERSONALTRAINER.pdf"),
    "GYM": os.path.join(TEMPLATES_DIR, "GYMINSTRUCTOR.pdf"),
}

# Kolory
BLUE_COLOR = (0.0, 0.62, 0.84)   # Niebieski kolor imienia
DARK_COLOR = (0.15, 0.15, 0.15)  # Ciemny kolor daty i numeru

# Rozdzielczość renderowania (DPI)
RENDER_DPI = 300


def format_date_polish(date_str=None):
    """Formatuje datę jako 'DD miesiąca YYYY r.' po polsku."""
    dt = None
    if date_str:
        for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                pass
    if dt is None:
        dt = datetime.now()
    month = POLISH_MONTHS[dt.month]
    return f"{dt.day} {month} {dt.year} r."


def generate_certificate(
    cert_type: str,
    full_name: str,
    cert_number: str,
    date_str: str = None
) -> dict:
    """
    Generuje certyfikat PDF w jakości druku 300 DPI.

    Args:
        cert_type: "TP" (Personal Trainer) lub "GYM" (Gym Instructor)
        full_name: Imię i nazwisko uczestnika
        cert_number: Numer certyfikatu (np. "11642/GSA/2026/TP")
        date_str: Data (YYYY-MM-DD lub DD.MM.YYYY), domyślnie dzisiaj

    Returns:
        dict z 'pdf_bytes' (bytes) i 'filename' (str)
    """
    template_path = TEMPLATES.get(cert_type)
    if not template_path:
        raise ValueError(f"Nieznany typ certyfikatu: {cert_type}. Użyj 'TP' lub 'GYM'.")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Szablon nie istnieje: {template_path}")

    formatted_date = format_date_polish(date_str)

    # Otwórz szablon PDF
    doc = fitz.open(template_path)
    page = doc[0]
    page_width = page.rect.width   # 842.25
    page_height = page.rect.height  # 595.5

    # Załaduj czcionkę
    font_reg = fitz.Font(fontfile=FONT_REGULAR)

    # --- Krok 1: Usuń placeholdery (precyzyjne prostokąty redakcji) ---
    page.add_redact_annot(fitz.Rect(255, 236, 590, 289), fill=(1, 1, 1))
    page.add_redact_annot(fitz.Rect(115, 479, 250, 501), fill=(1, 1, 1))
    page.add_redact_annot(fitz.Rect(340, 409, 510, 435), fill=(1, 1, 1))
    page.apply_redactions()

    # --- Krok 2: Wstaw imię i nazwisko (wycentrowane, niebieskie) ---
    name_font_size = 36.0
    name_tw = font_reg.text_length(full_name, fontsize=name_font_size)

    max_name_width = page_width * 0.75
    while name_tw > max_name_width and name_font_size > 18:
        name_font_size -= 1.0
        name_tw = font_reg.text_length(full_name, fontsize=name_font_size)

    name_x = (page_width - name_tw) / 2
    name_y = 276

    tw_name = fitz.TextWriter(page.rect, color=BLUE_COLOR)
    tw_name.append((name_x, name_y), full_name, font=font_reg, fontsize=name_font_size)
    tw_name.write_text(page)

    # --- Krok 3: Wstaw datę (wycentrowana) ---
    date_text = f"Wrocław, {formatted_date}"
    date_font_size = 16.8
    date_tw_width = font_reg.text_length(date_text, fontsize=date_font_size)
    date_x = (page_width - date_tw_width) / 2
    date_y = 428

    tw_dark = fitz.TextWriter(page.rect, color=DARK_COLOR)
    tw_dark.append((date_x, date_y), date_text, font=font_reg, fontsize=date_font_size)

    # --- Krok 4: Wstaw numer certyfikatu ---
    tw_dark.append((121, 494), cert_number, font=font_reg, fontsize=13.8)
    tw_dark.write_text(page)

    # --- Krok 5: Wyrenderuj stronę jako obraz 300 DPI ---
    scale = RENDER_DPI / 72.0  # 72 DPI to domyślna rozdzielczość PDF
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    # --- Krok 6: Zapisz obraz jako nowy PDF (A4, 300 DPI) ---
    # Nowy dokument PDF z jedną stroną A4
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=page_width, height=page_height)

    # Wstaw wyrenderowany obraz jako pełnostronicowy obrazek
    img_bytes = pix.tobytes("jpeg", jpg_quality=98)
    img_rect = fitz.Rect(0, 0, page_width, page_height)
    new_page.insert_image(img_rect, stream=img_bytes)

    # Zapisz do bytes
    buf = io.BytesIO()
    new_doc.save(buf, garbage=4, deflate=True, clean=True)
    new_doc.close()
    doc.close()

    # Nazwa pliku
    safe_name = full_name.strip().replace(" ", "_").replace("/", "-")
    cert_label = "PersonalTrainer" if cert_type == "TP" else "GymInstructor"
    filename = f"{safe_name}_{cert_label}.pdf"

    return {
        "pdf_bytes": buf.getvalue(),
        "filename": filename,
        "cert_type": cert_type,
        "full_name": full_name,
        "cert_number": cert_number,
        "date": formatted_date,
    }


def generate_all_certificates(
    full_name: str,
    cert_number_tp: str,
    cert_number_gym: str = None,
    date_str: str = None
) -> list:
    """
    Generuje oba certyfikaty (Personal Trainer + Gym Instructor) jednocześnie.
    """
    results = []

    tp_result = generate_certificate("TP", full_name, cert_number_tp, date_str)
    results.append(tp_result)

    gym_number = cert_number_gym if cert_number_gym else cert_number_tp
    gym_result = generate_certificate("GYM", full_name, gym_number, date_str)
    results.append(gym_result)

    return results


if __name__ == "__main__":
    print("Test generowania certyfikatów v4.0 (300 DPI)...")

    result_tp = generate_certificate(
        cert_type="TP",
        full_name="Małgorzata Wiśniewska",
        cert_number="11642/GSA/2026/TP",
        date_str="2026-07-21"
    )
    with open("/tmp/test_v4_TP.pdf", "wb") as f:
        f.write(result_tp["pdf_bytes"])
    print(f"TP: {result_tp['filename']} ({len(result_tp['pdf_bytes'])/1024:.0f} KB)")

    result_gym = generate_certificate(
        cert_type="GYM",
        full_name="Małgorzata Wiśniewska",
        cert_number="11642/GSA/2026/GYM",
        date_str="2026-07-21"
    )
    with open("/tmp/test_v4_GYM.pdf", "wb") as f:
        f.write(result_gym["pdf_bytes"])
    print(f"GYM: {result_gym['filename']} ({len(result_gym['pdf_bytes'])/1024:.0f} KB)")

    print("Gotowe! Sprawdź /tmp/test_v4_TP.pdf i /tmp/test_v4_GYM.pdf")
