"""Tk preview window built on the headless :mod:`src.map_print` engine."""

from __future__ import annotations

from dataclasses import replace
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from PIL import Image, ImageTk

from src.carte_config import carteConfig
from src.map_print import (
    DEFAULT_PREVIEW_ZOOM_STEP,
    DEFAULT_TITLE_GAP_MM,
    DEFAULT_TITLE_HEIGHT_MM,
    PAPER_SIZES_MM,
    PrintSettings,
    compute_auto_fit_viewport,
    compute_map_area_mm,
    fit_viewport_to_aspect,
    get_available_print_modules,
    get_page_size_mm,
    render_map_for_print,
    zoom_viewport_at,
)
from src.map_print_pdf import PdfExportError, export_map_pdf, sanitize_pdf_filename


MARGIN_PRESETS_MM = {
    "Minimales": 3.0,
    "Étroites": 5.0,
    "Normales": 10.0,
    "Larges": 20.0,
}
RESIZE_DEBOUNCE_MS = 80


class MapPrintDialog(tk.Toplevel):
    """Interactive preview whose state never modifies the main map view."""

    def __init__(self, parent, moteur_algo, layer_manager):
        super().__init__(parent)
        self.title("Imprimer / Exporter la carte")
        self.geometry("1100x750")
        self.minsize(850, 550)
        self.moteur_algo = moteur_algo
        self.layer_manager = layer_manager
        self.modules = get_available_print_modules(moteur_algo)
        self.module_vars = {module_id: tk.BooleanVar(value=True) for module_id, _ in self.modules}
        self.settings = PrintSettings(
            title=str(moteur_algo.segment_actif),
            selected_modules=tuple(module_id for module_id, _ in self.modules),
        )
        self.viewport = self._auto_fit_viewport()
        self.show_labels_var = tk.BooleanVar(value=True)
        self.image_preview_ref = None
        self._map_rect: tuple[float, float, float, float] | None = None
        self._drag_last: tuple[int, int] | None = None
        self._resize_after_id = None

        self._build_ui()
        self.after_idle(self.redraw_preview)

    def _build_ui(self) -> None:
        content = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        content.pack(fill="both", expand=True)
        controls = ttk.Frame(content, padding=12)
        preview = ttk.Frame(content, padding=8)
        content.add(controls, weight=0)
        content.add(preview, weight=1)

        parameters = ttk.Frame(controls)
        parameters.pack(fill="x", anchor="n")

        ttk.Label(parameters, text="Format", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.paper_format_var = tk.StringVar(value=self.settings.paper_format)
        format_box = ttk.Combobox(
            parameters, textvariable=self.paper_format_var, values=tuple(PAPER_SIZES_MM), state="readonly", width=14,
        )
        format_box.pack(anchor="w", fill="x", pady=(2, 14))
        format_box.bind("<<ComboboxSelected>>", self._on_paper_format_changed)

        ttk.Label(parameters, text="Orientation", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.orientation_var = tk.StringVar(value=self.settings.orientation)
        ttk.Radiobutton(parameters, text="Portrait", value="portrait", variable=self.orientation_var,
                        command=self._on_orientation_changed).pack(anchor="w")
        ttk.Radiobutton(parameters, text="Paysage", value="landscape", variable=self.orientation_var,
                        command=self._on_orientation_changed).pack(anchor="w", pady=(0, 14))

        ttk.Label(parameters, text="Titre", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.title_var = tk.StringVar(value=self.settings.title)
        title_entry = ttk.Entry(parameters, textvariable=self.title_var, width=28)
        title_entry.pack(anchor="w", fill="x", pady=(2, 14))
        self.title_var.trace_add("write", lambda *_: self._on_title_changed())

        ttk.Label(parameters, text="Modules", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        for module_id, label in self.modules:
            ttk.Checkbutton(parameters, text=label.capitalize(), variable=self.module_vars[module_id],
                            command=self._on_modules_changed).pack(anchor="w")
        ttk.Label(parameters, text="Labels", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(14, 0))
        ttk.Checkbutton(parameters, text="Afficher", variable=self.show_labels_var,
                        command=self._on_labels_changed).pack(anchor="w")
        ttk.Label(parameters, text="Marges", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(14, 0))
        self.margin_preset_var = tk.StringVar(value="Étroites")
        margin_box = ttk.Combobox(
            parameters, textvariable=self.margin_preset_var, values=tuple(MARGIN_PRESETS_MM), state="readonly", width=14,
        )
        margin_box.pack(anchor="w", fill="x", pady=(2, 2))
        margin_box.bind("<<ComboboxSelected>>", self._on_margin_changed)
        ttk.Label(parameters, text="Les marges minimales dépendent de l'imprimante.", foreground="#666666",
                  wraplength=210).pack(anchor="w")

        ttk.Frame(controls).pack(fill="both", expand=True)
        actions = ttk.Frame(controls)
        actions.pack(fill="x", anchor="sw")
        ttk.Button(actions, text="Imprimer...", command=self._export_pdf).pack(side="left")
        ttk.Button(actions, text="Annuler", command=self.destroy).pack(side="left", padx=(6, 0))

        self.preview_canvas = tk.Canvas(preview, background="#808080", highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)
        self.preview_canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.preview_canvas.bind("<B1-Motion>", self._on_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self.preview_canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.preview_canvas.bind("<Button-4>", lambda event: self._zoom_event(event, 1))
        self.preview_canvas.bind("<Button-5>", lambda event: self._zoom_event(event, -1))

    def _selected_modules(self) -> tuple[str, ...]:
        return tuple(module_id for module_id, _ in self.modules if self.module_vars[module_id].get())

    def _map_aspect_ratio(self) -> float:
        width, height = compute_map_area_mm(self.settings)
        return width / height

    def _auto_fit_viewport(self):
        return compute_auto_fit_viewport(
            self.layer_manager,
            self.moteur_algo.segment_actif,
            self.settings.selected_modules,
            target_aspect_ratio=self._map_aspect_ratio(),
        )

    def _sync_settings(self, **changes) -> None:
        changes.setdefault("selected_modules", self._selected_modules())
        self.settings = replace(self.settings, **changes)

    def _on_paper_format_changed(self, _event=None) -> None:
        self._sync_settings(paper_format=self.paper_format_var.get())
        self.viewport = fit_viewport_to_aspect(self.viewport, self._map_aspect_ratio(), carteConfig.image_size)
        self.redraw_preview()

    def _on_orientation_changed(self) -> None:
        self._sync_settings(orientation=self.orientation_var.get())
        self.viewport = fit_viewport_to_aspect(self.viewport, self._map_aspect_ratio(), carteConfig.image_size)
        self.redraw_preview()

    def _on_title_changed(self) -> None:
        self._sync_settings(title=self.title_var.get())
        self.redraw_preview()

    def _on_modules_changed(self) -> None:
        self._sync_settings()
        self.redraw_preview()

    def _on_labels_changed(self) -> None:
        self.redraw_preview()

    def _on_margin_changed(self, _event=None) -> None:
        self._sync_settings(margin_mm=MARGIN_PRESETS_MM[self.margin_preset_var.get()])
        self.viewport = fit_viewport_to_aspect(self.viewport, self._map_aspect_ratio(), carteConfig.image_size)
        self.redraw_preview()

    def _export_pdf(self) -> None:
        """Ask for a destination and export the current independent preview state."""
        initial_directory = getattr(self.master, "dossiers", {}).get("exports", "")
        output_path = filedialog.asksaveasfilename(
            parent=self,
            title="Exporter la carte en PDF",
            initialdir=initial_directory,
            initialfile=sanitize_pdf_filename(self.settings.title),
            defaultextension=".pdf",
            filetypes=(("Document PDF", "*.pdf"),),
        )
        if not output_path:
            return
        try:
            export_map_pdf(
                output_path,
                self.settings,
                self.viewport,
                self.layer_manager,
                self.moteur_algo.segment_actif,
                show_labels=self.show_labels_var.get(),
            )
        except PdfExportError as error:
            messagebox.showerror("Export PDF impossible", str(error), parent=self)

    def _on_canvas_resize(self, _event) -> None:
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(RESIZE_DEBOUNCE_MS, self._render_after_resize)

    def _render_after_resize(self) -> None:
        self._resize_after_id = None
        self.redraw_preview()

    def _page_layout(self) -> tuple[float, float, float, float, float, float, float, float] | None:
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        if canvas_width < 10 or canvas_height < 10:
            return None
        page_width_mm, page_height_mm = self._page_size_mm()
        scale = min((canvas_width - 32) / page_width_mm, (canvas_height - 32) / page_height_mm)
        if scale <= 0:
            return None
        page_width = page_width_mm * scale
        page_height = page_height_mm * scale
        page_x = (canvas_width - page_width) / 2
        page_y = (canvas_height - page_height) / 2
        margin = self.settings.margin_mm * scale
        title_height = DEFAULT_TITLE_HEIGHT_MM * scale
        title_gap = DEFAULT_TITLE_GAP_MM * scale
        map_x = page_x + margin
        map_y = page_y + margin + title_height + title_gap
        map_width = page_width - 2 * margin
        map_height = page_height - 2 * margin - title_height - title_gap
        return page_x, page_y, page_width, page_height, map_x, map_y, map_width, map_height

    def _page_size_mm(self) -> tuple[float, float]:
        return get_page_size_mm(self.settings)

    def redraw_preview(self) -> None:
        if not self.winfo_exists():
            return
        self.preview_canvas.delete("all")
        layout = self._page_layout()
        if layout is None:
            return
        page_x, page_y, page_width, page_height, map_x, map_y, map_width, map_height = layout
        self.preview_canvas.create_rectangle(page_x, page_y, page_x + page_width, page_y + page_height,
                                             fill="white", outline="#c0c0c0")
        margin_scale = page_width / self._page_size_mm()[0]
        title_font, title_text = fit_preview_title(
            self.preview_canvas,
            self.settings.title,
            page_width - 2 * self.settings.margin_mm * margin_scale,
        )
        self.preview_canvas.create_text(page_x + self.settings.margin_mm * margin_scale,
                                        page_y + self.settings.margin_mm * margin_scale,
                                        text=title_text, anchor="nw", font=title_font, fill="black")
        self._map_rect = map_x, map_y, map_width, map_height
        output_width, output_height = max(1, round(map_width)), max(1, round(map_height))
        raster = render_map_for_print(
            self.layer_manager,
            self.moteur_algo.segment_actif,
            self.settings.selected_modules,
            self.viewport,
            output_width,
            output_height,
            show_labels=self.show_labels_var.get(),
        )
        image = Image.fromarray(raster[:, :, ::-1])
        self.image_preview_ref = ImageTk.PhotoImage(image)
        self.preview_canvas.create_image(map_x, map_y, anchor="nw", image=self.image_preview_ref)
        self.preview_canvas.create_rectangle(map_x, map_y, map_x + map_width, map_y + map_height, outline="#a0a0a0")

    def _event_in_map(self, event) -> bool:
        if self._map_rect is None:
            return False
        map_x, map_y, map_width, map_height = self._map_rect
        return map_x <= event.x <= map_x + map_width and map_y <= event.y <= map_y + map_height

    def _on_drag_start(self, event) -> None:
        self._drag_last = (event.x, event.y) if self._event_in_map(event) else None

    def _on_drag(self, event) -> None:
        if self._drag_last is None or self._map_rect is None:
            return
        previous_x, previous_y = self._drag_last
        map_x, map_y, map_width, map_height = self._map_rect
        delta_x = event.x - previous_x
        delta_y = event.y - previous_y
        self.viewport = replace(
            self.viewport,
            x=self.viewport.x - delta_x * self.viewport.width / map_width,
            y=self.viewport.y - delta_y * self.viewport.height / map_height,
        ).clamped(carteConfig.image_size)
        self._drag_last = (event.x, event.y)
        self.redraw_preview()

    def _on_drag_end(self, _event) -> None:
        self._drag_last = None

    def _on_mouse_wheel(self, event) -> None:
        self._zoom_event(event, 1 if event.delta > 0 else -1)

    def _zoom_event(self, event, direction: int) -> None:
        if not self._event_in_map(event) or self._map_rect is None:
            return
        map_x, map_y, map_width, map_height = self._map_rect
        factor = DEFAULT_PREVIEW_ZOOM_STEP if direction > 0 else 1 / DEFAULT_PREVIEW_ZOOM_STEP
        self.viewport = zoom_viewport_at(
            self.viewport,
            (event.x - map_x) / map_width,
            (event.y - map_y) / map_height,
            factor,
            carteConfig.image_size,
        )
        self.redraw_preview()


def open_map_print_dialog(parent, moteur_algo, layer_manager) -> MapPrintDialog:
    """Open and return the PRINT-001B preview window."""
    return MapPrintDialog(parent, moteur_algo, layer_manager)


def fit_preview_title(canvas, text: str, max_width_px: float, normal_size: int = 11, minimum_size: int = 7):
    """Fit a preview-only title without changing the full PrintSettings value."""
    for size in range(normal_size, minimum_size - 1, -1):
        font = tkfont.Font(root=canvas, family="Helvetica", size=size, weight="bold")
        if font.measure(text) <= max_width_px:
            return font, text
    font = tkfont.Font(root=canvas, family="Helvetica", size=minimum_size, weight="bold")
    ellipsis = "…"
    if font.measure(ellipsis) > max_width_px:
        return font, ""
    visible = text
    while visible and font.measure(visible + ellipsis) > max_width_px:
        visible = visible[:-1]
    return font, visible + ellipsis if visible != text else text
