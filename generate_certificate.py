#!/usr/bin/env python3
"""
GSA Certificate Generator v5.0
Nakłada tekst bezpośrednio na oficjalne szablony PDF.

Podejście:
- Zamiast redakcji (która zostawia widoczną białą ramkę), używamy draw_rect
  z dokładnym bbox placeholdera — przykrywa stary tekst bez artefaktów.
- Tekst jest wektorowy — perfekcyjna ostrość przy każdym druku.
- Polskie znaki obsługiwane przez fitz.TextWriter + Montserrat.
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
BLUE_COLOR = (0.0, 0.62, 0.84)   # Niebieski kolor imienia (#0ea8da)
DARK_COLOR = (0.15, 0.15, 0.15)  # Ciemny kolor daty i numeru

# Dokładne bboxes placeholderów (z analizy szablonu):
# [Imię i nazwisko]: (262.2, 239.3, 580.0, 286.0) — size 38.3pt, kolor #0ea8da
# [Numer]: (120.7, 481.9, 179.8, 498.5) — size 13.8pt
# Wrocław, [data]: (354.4, 411.6, 487.8, 431.7) — size 16.8pt
PLACEHOLDER_NAME = fitz.Rect(262.2, 239.3, 580.0, 286.0)
PLACEHOLDER_NUMBER = fitz.Rect(120.7, 481.9, 179.8, 498.5)
PLACEHOLDER_DATE = fitz.Rect(354.4, 411.6, 487.8, 431.7)


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
    Generuje certyfikat PDF nakładając tekst na oficjalny szablon.

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

    # Załaduj czcionkę
    font_reg = fitz.Font(fontfile=FONT_REGULAR)

    # --- Krok 1: Przykryj placeholdery białymi prostokątami (bez ramki) ---
    # Używamy draw_rect zamiast redakcji — brak artefaktów, czyste krawędzie
    page.draw_rect(PLACEHOLDER_NAME, color=None, fill=(1, 1, 1), width=0)
    page.draw_rect(PLACEHOLDER_NUMBER, color=None, fill=(1, 1, 1), width=0)
    page.draw_rect(PLACEHOLDER_DATE, color=None, fill=(1, 1, 1), width=0)

    # --- Krok 2: Wstaw imię i nazwisko (wycentrowane, niebieskie) ---
    name_font_size = 36.0
    name_tw_width = font_reg.text_length(full_name, fontsize=name_font_size)

    # Skaluj w dół jeśli imię za długie (max 75% szerokości strony)
    max_name_width = page_width * 0.75
    while name_tw_width > max_name_width and name_font_size > 18:
        name_font_size -= 1.0
        name_tw_width = font_reg.text_length(full_name, fontsize=name_font_size)

    name_x = (page_width - name_tw_width) / 2
    name_y = 276  # baseline

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

    # --- Krok 4: Wstaw numer certyfikatu (lewy dolny róg) ---
    tw_dark.append((121, 494), cert_number, font=font_reg, fontsize=13.8)

    tw_dark.write_text(page)

    # Zapisz do bytes — wektorowy PDF, perfekcyjna jakość druku
    buf = io.BytesIO()
    doc.save(buf, garbage=4, deflate=True, clean=True)
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
    print("Test generowania certyfikatów v5.0 (wektorowy, bez artefaktów)...")

    result_tp = generate_certificate(
        cert_type="TP",
        full_name="Małgorzata Wiśniewska",
        cert_number="11642/GSA/2026/TP",
        date_str="2026-07-21"
    )
    with open("/tmp/test_v5_TP.pdf", "wb") as f:
        f.write(result_tp["pdf_bytes"])
    print(f"TP: {result_tp['filename']} ({len(result_tp['pdf_bytes'])/1024:.0f} KB)")

    result_gym = generate_certificate(
        cert_type="GYM",
        full_name="Małgorzata Wiśniewska",
        cert_number="11642/GSA/2026/GYM",
        date_str="2026-07-21"
    )
    with open("/tmp/test_v5_GYM.pdf", "wb") as f:
        f.write(result_gym["pdf_bytes"])
    print(f"GYM: {result_gym['filename']} ({len(result_gym['pdf_bytes'])/1024:.0f} KB)")

    # Test z długim imieniem
    result_long = generate_certificate(
        cert_type="TP",
        full_name="Małgorzata Wiśniewska-Kowalska",
        cert_number="11643/GSA/2026/TP",
        date_str="2026-07-21"
    )
    with open("/tmp/test_v5_long.pdf", "wb") as f:
        f.write(result_long["pdf_bytes"])
    print(f"Long name: {result_long['filename']} ({len(result_long['pdf_bytes'])/1024:.0f} KB)")

    print("Gotowe!")
