"""Raster PDF export for the independent map-print preview."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import unicodedata

import cv2
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from src.map_print import (
    PrintSettings,
    PrintViewport,
    compute_map_area_mm,
    get_page_size_mm,
    render_map_for_print,
)


DEFAULT_PRINT_DPI = 300
REFERENCE_PREVIEW_DPI = 96
PDF_TITLE_FONT = "Helvetica-Bold"
PDF_TITLE_FONT_SIZE = 11.0
PDF_TITLE_MIN_FONT_SIZE = 0.5


class PdfExportError(RuntimeError):
    """Raised when the PDF backend cannot write a requested export."""


def mm_to_pixels(value_mm: float, dpi: int = DEFAULT_PRINT_DPI) -> int:
    """Convert a physical size in millimetres to a rounded raster dimension."""
    if dpi <= 0:
        raise ValueError("dpi must be strictly positive.")
    return max(1, round(value_mm / 25.4 * dpi))


def sanitize_pdf_filename(title: str) -> str:
    """Return a portable PDF filename derived from the print title."""
    normalized = unicodedata.normalize("NFKD", str(title)).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
    return f"{cleaned or 'carte'}.pdf"


def fit_pdf_title(text: str, max_width_pt: float) -> tuple[float, tuple[str, ...]]:
    """Fit the complete title in at most two lines by reducing its font size."""
    text = " ".join(str(text).split())
    if not text:
        return PDF_TITLE_FONT_SIZE, ()
    font_size = PDF_TITLE_FONT_SIZE
    while font_size >= PDF_TITLE_MIN_FONT_SIZE:
        lines = _wrap_title(text, max_width_pt, font_size)
        if len(lines) <= 2:
            return font_size, tuple(lines)
        font_size -= 0.25
    return PDF_TITLE_MIN_FONT_SIZE, tuple(_wrap_title(text, max_width_pt, PDF_TITLE_MIN_FONT_SIZE))


def export_map_pdf(
    output_path: str | Path,
    settings: PrintSettings,
    viewport: PrintViewport,
    layer_manager,
    segment,
    show_labels: bool,
    dpi: int = DEFAULT_PRINT_DPI,
) -> Path:
    """Export the selected preview state as a one-page, raster PDF.

    The function intentionally has no Tk dependency so it can be used by the
    dialog and tested independently.
    """
    if not isinstance(dpi, int) or dpi <= 0:
        raise ValueError("dpi must be a strictly positive integer.")
    output = Path(output_path)
    page_width_mm, page_height_mm = get_page_size_mm(settings)
    map_width_mm, map_height_mm = compute_map_area_mm(settings)
    raster_width = mm_to_pixels(map_width_mm, dpi)
    raster_height = mm_to_pixels(map_height_mm, dpi)
    label_scale = dpi / REFERENCE_PREVIEW_DPI

    try:
        raster = render_map_for_print(
            layer_manager,
            segment,
            settings.selected_modules,
            viewport,
            raster_width,
            raster_height,
            show_labels=show_labels,
            label_scale=label_scale,
            stroke_scale=label_scale,
        )
        encoded_png = encode_bgr_png(raster)

        page_width_pt, page_height_pt = page_width_mm * mm, page_height_mm * mm
        map_width_pt, map_height_pt = map_width_mm * mm, map_height_mm * mm
        margin_pt = settings.margin_mm * mm
        canvas = Canvas(str(output), pagesize=(page_width_pt, page_height_pt))
        _draw_pdf_title(canvas, settings.title, page_width_pt, page_height_pt, margin_pt)
        image_buffer = BytesIO(encoded_png)
        canvas.drawImage(ImageReader(image_buffer), margin_pt, margin_pt, map_width_pt, map_height_pt)
        canvas.showPage()
        canvas.save()
    except PdfExportError:
        raise
    except (OSError, cv2.error) as error:
        raise PdfExportError(f"Impossible d'exporter le PDF : {error}") from error
    return output


def encode_bgr_png(raster) -> bytes:
    """Encode an OpenCV BGR raster as a standards-compliant PNG image."""
    success, encoded_png = cv2.imencode(".png", raster)
    if not success:
        raise PdfExportError("Impossible d'encoder l'image de la carte en PNG.")
    return encoded_png.tobytes()


def _draw_pdf_title(canvas: Canvas, title: str, page_width_pt: float, page_height_pt: float, margin_pt: float) -> None:
    available_width = page_width_pt - 2 * margin_pt
    font_size, lines = fit_pdf_title(title, available_width)
    if not lines:
        return
    canvas.setFont(PDF_TITLE_FONT, font_size)
    leading = font_size * 1.1
    baseline = page_height_pt - margin_pt - font_size
    for line in lines:
        canvas.drawString(margin_pt, baseline, line)
        baseline -= leading


def _wrap_title(text: str, max_width_pt: float, font_size: float) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if pdfmetrics.stringWidth(candidate, PDF_TITLE_FONT, font_size) <= max_width_pt:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        fragments = _break_title_word(word, max_width_pt, font_size)
        lines.extend(fragments[:-1])
        current = fragments[-1]
    if current:
        lines.append(current)
    return lines


def _break_title_word(word: str, max_width_pt: float, font_size: float) -> list[str]:
    fragments: list[str] = []
    current = ""
    for character in word:
        if current and pdfmetrics.stringWidth(current + character, PDF_TITLE_FONT, font_size) > max_width_pt:
            fragments.append(current)
            current = character
        else:
            current += character
    return fragments or [word]
