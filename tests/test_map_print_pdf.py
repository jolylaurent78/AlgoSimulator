from io import BytesIO
import re

import numpy as np
import pytest
from PIL import Image
from reportlab.lib.units import mm

import src.map_print as map_print
import src.map_print_pdf as map_print_pdf


@pytest.fixture
def render_capture(monkeypatch):
    calls = []

    def render(*args, **kwargs):
        calls.append((args, kwargs))
        height, width = args[5], args[4]
        return np.full((height, width, 3), (10, 20, 30), dtype=np.uint8)

    monkeypatch.setattr(map_print_pdf, "render_map_for_print", render)
    return calls


def _media_box(pdf_path):
    content = pdf_path.read_bytes().decode("latin-1")
    match = re.search(r"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", content)
    assert match, "The generated PDF must declare its page dimensions."
    return tuple(map(float, match.groups()))


@pytest.mark.parametrize(
    ("orientation", "expected_mm"),
    (("portrait", (210.0, 297.0)), ("landscape", (297.0, 210.0))),
)
def test_export_uses_exact_a4_page_orientation(tmp_path, render_capture, orientation, expected_mm):
    settings = map_print.PrintSettings(orientation=orientation, selected_modules=("stylet",))
    output = map_print_pdf.export_map_pdf(
        tmp_path / f"{orientation}.pdf", settings, map_print.PrintViewport(0, 0, 10, 10), object(), "S", True, dpi=20,
    )

    assert output.exists() and output.stat().st_size > 0
    assert _media_box(output) == pytest.approx(tuple(value * mm for value in expected_mm), abs=.01)


def test_export_uses_preview_viewport_module_selection_and_label_state(tmp_path, render_capture):
    settings = map_print.PrintSettings(selected_modules=("lumiere",), margin_mm=10)
    viewport = map_print.PrintViewport(2, 3, 4, 5)
    map_print_pdf.export_map_pdf(tmp_path / "labels.pdf", settings, viewport, object(), "segment", False, dpi=192)

    args, kwargs = render_capture[0]
    assert args[1] == "segment"
    assert args[2] == ("lumiere",)
    assert args[3] == viewport
    assert kwargs["show_labels"] is False
    assert kwargs["label_scale"] == pytest.approx(2.0)
    assert kwargs["stroke_scale"] == pytest.approx(2.0)
    width_mm, height_mm = map_print.compute_map_area_mm(settings)
    assert args[4:6] == (map_print_pdf.mm_to_pixels(width_mm, 192), map_print_pdf.mm_to_pixels(height_mm, 192))

    map_print_pdf.export_map_pdf(tmp_path / "labels-visible.pdf", settings, viewport, object(), "segment", True, dpi=192)
    assert render_capture[1][1]["show_labels"] is True


def test_bgr_png_encoding_preserves_red_and_blue_channels():
    raster = np.array([[(0, 0, 255), (255, 0, 0)]], dtype=np.uint8)
    encoded_png = map_print_pdf.encode_bgr_png(raster)

    image = Image.open(BytesIO(encoded_png)).convert("RGB")
    assert tuple(np.asarray(image)[0, 0]) == (255, 0, 0)
    assert tuple(np.asarray(image)[0, 1]) == (0, 0, 255)


def test_title_keeps_all_text_in_at_most_two_lines_without_ellipsis():
    title = "Titre très long destiné à vérifier que le texte complet reste présent " * 12
    font_size, lines = map_print_pdf.fit_pdf_title(title, 150)

    assert font_size < map_print_pdf.PDF_TITLE_FONT_SIZE
    assert len(lines) <= 2
    assert " ".join(lines) == " ".join(title.split())
    assert "…" not in " ".join(lines)


def test_export_places_title_and_map_at_the_configured_margins(tmp_path, render_capture, monkeypatch):
    recordings = []

    class RecordingCanvas:
        def __init__(self, path, pagesize):
            self.path = path
            self.pagesize = pagesize
            self.images = []
            self.text = []
            recordings.append(self)

        def setFont(self, *_args):
            pass

        def drawString(self, x, y, text):
            self.text.append((x, y, text))

        def drawImage(self, _image, x, y, width, height):
            self.images.append((x, y, width, height))

        def showPage(self):
            pass

        def save(self):
            pass

    monkeypatch.setattr(map_print_pdf, "Canvas", RecordingCanvas)
    title = "Titre complet à conserver " * 10
    settings = map_print.PrintSettings(title=title, margin_mm=10)
    map_print_pdf.export_map_pdf(
        tmp_path / "layout.pdf", settings, map_print.PrintViewport(0, 0, 10, 10), object(), "S", True, dpi=20,
    )

    canvas = recordings[0]
    map_x, map_y, map_width, map_height = canvas.images[0]
    expected_width, expected_height = map_print.compute_map_area_mm(settings)
    assert (map_x, map_y) == pytest.approx((10 * mm, 10 * mm))
    assert (map_width, map_height) == pytest.approx((expected_width * mm, expected_height * mm))
    assert " ".join(item[2] for item in canvas.text) == " ".join(title.split())


def test_filename_is_sanitized_and_pdf_extension_is_added():
    assert map_print_pdf.sanitize_pdf_filename('  Été: carte/01?  ') == "Ete- carte-01.pdf"
    assert map_print_pdf.sanitize_pdf_filename("") == "carte.pdf"


def test_default_pdf_dpi_and_label_style_constants_match_print_requirements():
    assert map_print_pdf.DEFAULT_PRINT_DPI == 300
    assert map_print.LABEL_BACKGROUND_ALPHA == .3
    assert map_print.LABEL_COLOR_DARKEN_FACTOR == .5
    assert map_print.LABEL_FONT_SCALE == .4
