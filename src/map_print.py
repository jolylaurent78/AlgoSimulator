"""Headless raster rendering primitives for the future map printing workflow.

This module deliberately owns its selection and viewport state.  In
particular, it does not use ``LayerManager.filtreActif``: screen filters and
print filters are two separate user experiences.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, isfinite, pi, sin
from typing import Iterable, Sequence

import cv2
import numpy as np

from src.affichage_objets import CercleGraphique, LigneGraphique, ObjetGraphique
from src.carte_config import carteConfig


PAPER_SIZES_MM = {"A4": (210.0, 297.0)}
DEFAULT_PREVIEW_ZOOM_STEP = 1.15
DEFAULT_MIN_VIEWPORT_PX = 32.0
DEFAULT_TITLE_HEIGHT_MM = 6.0
DEFAULT_TITLE_GAP_MM = 2.0
LABEL_FONT_FACE = cv2.FONT_HERSHEY_SIMPLEX
LABEL_FONT_SCALE = 0.4
LABEL_THICKNESS = 1
LABEL_PADDING_PX = 2
LABEL_OFFSET_PX = 8.0
LABEL_INSET_PX = 5.0
LABEL_COLLISION_GAP_PX = 3.0
LABEL_CIRCLE_ANCHOR_TOLERANCE_PX = 1.0
LABEL_BACKGROUND_ALPHA = 0.3
LABEL_COLOR_DARKEN_FACTOR = 0.5
LINE_ORIGIN_DISTANCE_WEIGHT = 0.35
LINE_LABEL_PARAMETERS = (0.10, 0.18, 0.25, 0.75, 0.82, 0.90)
CIRCLE_LABEL_ANGLES = tuple(index * pi / 4 for index in range(8))


class PrintSettingsError(ValueError):
    """Raised when a print setting is not supported by this version."""


class PrintViewportError(ValueError):
    """Raised when a viewport cannot describe a valid source-map area."""


@dataclass(frozen=True)
class PrintLabelPlacement:
    """A non-persisted label rectangle in output raster coordinates."""

    text: str
    x: float
    y: float
    width: float
    height: float
    color: tuple[int, int, int] = (0, 0, 0)
    origin_distance: float = 0.0
    render_scale: float = 1.0

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.x, self.y, self.x + self.width, self.y + self.height


class _PrintStrokeScaledObject:
    """Delegate an existing graphical object while scaling only its draw width."""

    def __init__(self, source, stroke_scale: float):
        self._source = source
        self._stroke_scale = stroke_scale

    def __getattr__(self, name):
        definition = getattr(type(self._source), name, None)
        if callable(definition):
            return definition.__get__(self, type(self._source))
        return getattr(self._source, name)

    def getEpaisseur(self):
        return max(1, round(self._source.getEpaisseur() * self._stroke_scale))

    def afficher(self, canvas, transform):
        return type(self._source).afficher(self, canvas, transform)


@dataclass(frozen=True)
class PrintSettings:
    """Settings independent from UI, PDF backend, and output DPI."""

    paper_format: str = "A4"
    orientation: str = "portrait"
    title: str = ""
    selected_modules: tuple[str, ...] = ()
    margin_mm: float = 5.0

    def __post_init__(self) -> None:
        if self.paper_format not in PAPER_SIZES_MM:
            raise PrintSettingsError(f"Format papier non pris en charge : {self.paper_format!r}")
        if self.orientation not in ("portrait", "landscape"):
            raise PrintSettingsError(f"Orientation non prise en charge : {self.orientation!r}")
        if not isinstance(self.margin_mm, (int, float)) or not isfinite(self.margin_mm) or self.margin_mm < 0:
            raise PrintSettingsError("La marge doit être un nombre fini supérieur ou égal à zéro.")
        object.__setattr__(self, "selected_modules", tuple(self.selected_modules))


@dataclass(frozen=True)
class PrintViewport:
    """A rectangle in absolute source-map pixels, independent from Tk state."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(isinstance(value, (int, float)) and isfinite(value) for value in values):
            raise PrintViewportError("Les coordonnées du viewport doivent être des nombres finis.")
        if self.width <= 0 or self.height <= 0:
            raise PrintViewportError("La largeur et la hauteur du viewport doivent être strictement positives.")

    @classmethod
    def full_map(cls, image_size: tuple[int, int]) -> "PrintViewport":
        image_width, image_height = _validate_image_size(image_size)
        return cls(0, 0, image_width, image_height)

    def validate(self, image_size: tuple[int, int]) -> "PrintViewport":
        image_width, image_height = _validate_image_size(image_size)
        if self.x < 0 or self.y < 0:
            raise PrintViewportError("Le viewport ne peut pas commencer hors de la carte.")
        if self.x >= image_width or self.y >= image_height:
            raise PrintViewportError("L'origine du viewport doit être dans la carte.")
        if self.x + self.width > image_width or self.y + self.height > image_height:
            raise PrintViewportError("Le viewport doit rester entièrement dans la carte.")
        return self

    def clamped(self, image_size: tuple[int, int]) -> "PrintViewport":
        """Return the nearest valid viewport while retaining its size when possible."""
        image_width, image_height = _validate_image_size(image_size)
        width = min(self.width, image_width)
        height = min(self.height, image_height)
        x = min(max(self.x, 0), image_width - width)
        y = min(max(self.y, 0), image_height - height)
        return PrintViewport(x, y, width, height)

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


def get_available_print_modules(moteur_algo) -> tuple[tuple[str, str], ...]:
    """Read printable module identifiers and labels from the business engine."""
    return tuple(moteur_algo.getModulesAvecAffichage())


def get_page_size_mm(settings: PrintSettings) -> tuple[float, float]:
    """Return width and height in mm for the configured paper orientation."""
    width, height = PAPER_SIZES_MM[settings.paper_format]
    return (width, height) if settings.orientation == "portrait" else (height, width)


def compute_map_area_mm(
    settings: PrintSettings,
    title_height_mm: float = DEFAULT_TITLE_HEIGHT_MM,
    title_gap_mm: float = DEFAULT_TITLE_GAP_MM,
) -> tuple[float, float]:
    """Return the future page's drawable map area, before PDF composition."""
    if title_height_mm < 0 or title_gap_mm < 0:
        raise ValueError("La hauteur et l'espacement du titre ne peuvent pas être négatifs.")
    page_width, page_height = get_page_size_mm(settings)
    map_width = page_width - 2 * settings.margin_mm
    map_height = page_height - 2 * settings.margin_mm - title_height_mm - title_gap_mm
    if map_width <= 0 or map_height <= 0:
        raise ValueError("Les marges et le titre ne laissent aucune zone de carte.")
    return map_width, map_height


def get_printable_objects(layer_manager, segment, selected_modules: Sequence[str]) -> list:
    """Select visible objects of visible layers in one segment, locally for print.

    ``filtreActif`` is intentionally neither read nor written here.  The
    explicit walk over the segment's layers is what keeps print independent of
    the filters used by the interactive map.
    """
    selected = set(selected_modules)
    if not selected:
        return []

    objects = []
    for layer in _get_segment_layers(layer_manager, segment):
        if not _is_visible(layer):
            continue
        for obj in _get_layer_objects(layer):
            if not _is_visible(obj):
                continue
            if getattr(obj, "tags", {}).get("module") in selected:
                objects.append(obj)
    return objects


def deduplicate_print_objects(objects: Iterable) -> list:
    """Keep the first object for every supported graphical print signature.

    The signature deliberately excludes names, tooltips, layers, scenarios and
    print labels.  If duplicate objects have different print labels, the first
    object's label is deterministically retained.
    Unsupported primitives have no signature and are retained unchanged.
    """
    unique = []
    signatures = set()
    for obj in objects:
        signature_getter = getattr(obj, "getGraphicalSignature", None)
        signature = signature_getter() if callable(signature_getter) else None
        if signature is None:
            unique.append(obj)
            continue
        if signature not in signatures:
            signatures.add(signature)
            unique.append(obj)
    return unique


def clip_line_to_rect(
    point1: tuple[float, float],
    point2: tuple[float, float],
    rect: tuple[float, float, float, float],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Clip a segment to ``(left, top, right, bottom)`` with Liang-Barsky."""
    left, top, right, bottom = rect
    x1, y1 = point1
    x2, y2 = point2
    dx, dy = x2 - x1, y2 - y1
    parameters = ((-dx, x1 - left), (dx, right - x1), (-dy, y1 - top), (dy, bottom - y1))
    lower, upper = 0.0, 1.0
    for p, q in parameters:
        if p == 0:
            if q < 0:
                return None
            continue
        ratio = q / p
        if p < 0:
            if ratio > upper:
                return None
            lower = max(lower, ratio)
        else:
            if ratio < lower:
                return None
            upper = min(upper, ratio)
    return (x1 + lower * dx, y1 + lower * dy), (x1 + upper * dx, y1 + upper * dy)


def circle_intersects_rect(
    center_x: float,
    center_y: float,
    radius: float,
    rect: tuple[float, float, float, float],
    tolerance: float = 1e-6,
) -> bool:
    """Return whether a circle's circumference intersects a rectangle.

    This deliberately tests the circumference rather than the filled disk:
    a viewport fully contained inside a much larger circle is not visible.
    """
    left, top, right, bottom = rect
    nearest_x = min(max(center_x, left), right)
    nearest_y = min(max(center_y, top), bottom)
    minimum_distance = hypot(center_x - nearest_x, center_y - nearest_y)
    maximum_distance = max(
        hypot(center_x - corner_x, center_y - corner_y)
        for corner_x, corner_y in ((left, top), (left, bottom), (right, top), (right, bottom))
    )
    return minimum_distance - tolerance <= radius <= maximum_distance + tolerance


def compute_print_label_placements(
    objects: Iterable,
    viewport: PrintViewport,
    output_width_px: int,
    output_height_px: int,
    label_scale: float = 1.0,
) -> list[PrintLabelPlacement]:
    """Compute deterministic, non-persisted raster placements for supported labels."""
    if output_width_px <= 0 or output_height_px <= 0:
        raise ValueError("Les dimensions de sortie doivent être strictement positives.")
    if not isinstance(label_scale, (int, float)) or not isfinite(label_scale) or label_scale <= 0:
        raise ValueError("label_scale must be a finite positive number.")
    scale_x = output_width_px / viewport.width
    scale_y = output_height_px / viewport.height

    def source_to_raster(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] - viewport.x) * scale_x, (point[1] - viewport.y) * scale_y

    labelled = [obj for obj in objects if _get_print_label(obj)]
    ordered = [obj for obj in labelled if isinstance(obj, CercleGraphique)]
    ordered.extend(obj for obj in labelled if isinstance(obj, LigneGraphique))

    placements: list[PrintLabelPlacement] = []
    for obj in ordered:
        text = _get_print_label(obj)
        candidates = _label_candidates_for_object(
            obj, text, viewport, output_width_px, output_height_px, source_to_raster, label_scale,
        )
        candidates = [
            constrained
            for candidate in candidates
            if (constrained := _constrain_placement_to_raster(
                candidate, output_width_px, output_height_px, label_scale,
            )) is not None
        ]
        if not candidates:
            continue
        scored = [
            (score_print_label_candidate(candidate, placements, output_width_px, output_height_px, label_scale), index, candidate)
            for index, candidate in enumerate(candidates)
        ]
        valid = [item for item in scored if item[0] != float("inf")]
        if valid:
            placements.append(min(valid, key=lambda item: (item[0], item[1]))[2])
    return placements


def score_print_label_candidate(
    placement: PrintLabelPlacement,
    placed: Sequence[PrintLabelPlacement],
    raster_width: int,
    raster_height: int,
    label_scale: float = 1.0,
) -> float:
    """Score one valid candidate: collisions dominate, then centre and edge preference."""
    left, top, right, bottom = placement.bounds
    inset = LABEL_INSET_PX * label_scale
    collision_gap = LABEL_COLLISION_GAP_PX * label_scale
    if left < inset or top < inset or right > raster_width - inset or bottom > raster_height - inset:
        return float("inf")
    collision_penalty = 0.0
    for other in placed:
        if _rectangles_overlap(_expand_bounds(placement.bounds, collision_gap), other.bounds):
            collision_penalty += 1_000_000.0
    center_x, center_y = (left + right) / 2, (top + bottom) / 2
    distance_center = hypot(center_x - raster_width / 2, center_y - raster_height / 2)
    distance_edge = min(left, top, raster_width - right, raster_height - bottom)
    return (
        collision_penalty
        + 120.0 / (distance_center + 1.0)
        + distance_edge * 0.08
        - placement.origin_distance * LINE_ORIGIN_DISTANCE_WEIGHT
    )


def get_print_label_text_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return a slightly darker BGR variant of the associated object color."""
    return tuple(max(0, round(component * LABEL_COLOR_DARKEN_FACTOR)) for component in color)


def draw_print_label_placements(raster: np.ndarray, placements: Iterable[PrintLabelPlacement]) -> None:
    """Draw compact labels with semi-transparent pale backing in place on a BGR raster."""
    for placement in placements:
        x1, y1, x2, y2 = (round(value) for value in placement.bounds)
        region = raster[y1:y2 + 1, x1:x2 + 1]
        backing = np.full_like(region, 255)
        cv2.addWeighted(backing, LABEL_BACKGROUND_ALPHA, region, 1 - LABEL_BACKGROUND_ALPHA, 0, dst=region)
        font_scale = LABEL_FONT_SCALE * placement.render_scale
        thickness = max(1, round(LABEL_THICKNESS * placement.render_scale))
        padding = round(LABEL_PADDING_PX * placement.render_scale)
        (_, text_height), _ = cv2.getTextSize(placement.text, LABEL_FONT_FACE, font_scale, thickness)
        cv2.putText(
            raster,
            placement.text,
            (x1 + padding, y1 + padding + text_height),
            LABEL_FONT_FACE,
            font_scale,
            get_print_label_text_color(placement.color),
            thickness,
            cv2.LINE_AA,
        )


def _get_print_label(obj) -> str | None:
    getter = getattr(obj, "getPrintLabel", None)
    text = getter() if callable(getter) else None
    return text if isinstance(text, str) and text else None


def _label_candidates_for_object(
    obj,
    text: str,
    viewport: PrintViewport,
    output_width_px: int,
    output_height_px: int,
    source_to_raster,
    label_scale: float,
) -> list[PrintLabelPlacement]:
    if isinstance(obj, LigneGraphique):
        return _line_label_candidates(obj, text, viewport, source_to_raster, label_scale)
    if isinstance(obj, CercleGraphique):
        return _circle_label_candidates(
            obj, text, viewport, output_width_px, output_height_px, source_to_raster, label_scale,
        )
    return []


def _line_label_candidates(
    line: LigneGraphique,
    text: str,
    viewport: PrintViewport,
    source_to_raster,
    label_scale: float,
) -> list[PrintLabelPlacement]:
    endpoints = _line_source_endpoints(line)
    if endpoints is None:
        return []
    visible = clip_line_to_rect(
        *endpoints,
        (viewport.x, viewport.y, viewport.x + viewport.width, viewport.y + viewport.height),
    )
    if visible is None:
        return []
    point1, point2 = (source_to_raster(point) for point in visible)
    dx, dy = point2[0] - point1[0], point2[1] - point1[1]
    length = hypot(dx, dy)
    if length == 0:
        return []
    normal = (-dy / length, dx / length)
    reference_x, reference_y = source_to_raster(line.pointReference)
    color = tuple(line.getCouleur())
    candidates = []
    for parameter in LINE_LABEL_PARAMETERS:
        anchor_x = point1[0] + parameter * dx
        anchor_y = point1[1] + parameter * dy
        for direction in (1, -1):
            candidates.append(_placement_at_center(
                text,
                anchor_x + direction * normal[0] * LABEL_OFFSET_PX * label_scale,
                anchor_y + direction * normal[1] * LABEL_OFFSET_PX * label_scale,
                color,
                hypot(anchor_x - reference_x, anchor_y - reference_y),
                label_scale,
            ))
    return candidates


def _circle_label_candidates(
    circle: CercleGraphique,
    text: str,
    viewport: PrintViewport,
    output_width_px: int,
    output_height_px: int,
    source_to_raster,
    label_scale: float,
) -> list[PrintLabelPlacement]:
    if not circle_intersects_rect(
        circle.pointReference[0],
        circle.pointReference[1],
        circle.cercle.rayon,
        (viewport.x, viewport.y, viewport.x + viewport.width, viewport.y + viewport.height),
    ):
        return []
    center_x, center_y = source_to_raster(circle.pointReference)
    radius_x = circle.cercle.rayon * output_width_px / viewport.width
    radius_y = circle.cercle.rayon * output_height_px / viewport.height
    candidates = []
    color = tuple(circle.getCouleur())
    for angle in CIRCLE_LABEL_ANGLES:
        direction_x, direction_y = cos(angle), sin(angle)
        anchor_x = center_x + direction_x * radius_x
        anchor_y = center_y + direction_y * radius_y
        if not _anchor_is_near_raster(
            anchor_x, anchor_y, output_width_px, output_height_px, label_scale,
        ):
            continue
        candidates.append(_placement_at_center(
            text,
            anchor_x + direction_x * LABEL_OFFSET_PX * label_scale,
            anchor_y + direction_y * LABEL_OFFSET_PX * label_scale,
            color,
            label_scale=label_scale,
        ))
    return candidates


def _line_source_endpoints(line: LigneGraphique) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if line.distance is None:
        if line.lignePixelImage is None:
            return None
        return line.lignePixelImage.pt1, line.lignePixelImage.pt2
    x, y = line.pointReference
    vx, vy = line.vecteur
    return (x, y), (x + vx * line.distance, y + vy * line.distance)


def _anchor_is_near_raster(
    x: float,
    y: float,
    raster_width: int,
    raster_height: int,
    label_scale: float,
) -> bool:
    tolerance = LABEL_CIRCLE_ANCHOR_TOLERANCE_PX * label_scale
    return -tolerance <= x <= raster_width + tolerance and -tolerance <= y <= raster_height + tolerance


def _placement_at_center(
    text: str,
    center_x: float,
    center_y: float,
    color: tuple[int, int, int],
    origin_distance: float = 0.0,
    label_scale: float = 1.0,
) -> PrintLabelPlacement:
    font_scale = LABEL_FONT_SCALE * label_scale
    thickness = max(1, round(LABEL_THICKNESS * label_scale))
    padding = round(LABEL_PADDING_PX * label_scale)
    (text_width, text_height), baseline = cv2.getTextSize(text, LABEL_FONT_FACE, font_scale, thickness)
    width = text_width + 2 * padding
    height = text_height + baseline + 2 * padding
    return PrintLabelPlacement(
        text, center_x - width / 2, center_y - height / 2, width, height, color, origin_distance, label_scale,
    )


def _constrain_placement_to_raster(
    placement: PrintLabelPlacement,
    raster_width: int,
    raster_height: int,
    label_scale: float = 1.0,
) -> PrintLabelPlacement | None:
    inset = LABEL_INSET_PX * label_scale
    if placement.width + 2 * inset > raster_width or placement.height + 2 * inset > raster_height:
        return None
    x = min(max(placement.x, inset), raster_width - inset - placement.width)
    y = min(max(placement.y, inset), raster_height - inset - placement.height)
    return PrintLabelPlacement(
        placement.text,
        x,
        y,
        placement.width,
        placement.height,
        placement.color,
        placement.origin_distance,
        placement.render_scale,
    )


def _expand_bounds(bounds: tuple[float, float, float, float], amount: float) -> tuple[float, float, float, float]:
    left, top, right, bottom = bounds
    return left - amount, top - amount, right + amount, bottom + amount


def _rectangles_overlap(
    first: tuple[float, float, float, float], second: tuple[float, float, float, float],
) -> bool:
    left1, top1, right1, bottom1 = first
    left2, top2, right2, bottom2 = second
    return left1 < right2 and left2 < right1 and top1 < bottom2 and top2 < bottom1


def render_map_for_print(
    layer_manager,
    segment,
    selected_modules: Sequence[str],
    viewport: PrintViewport,
    output_width_px: int,
    output_height_px: int,
    show_labels: bool = True,
    label_scale: float = 1.0,
    stroke_scale: float = 1.0,
) -> np.ndarray:
    """Render a map viewport and selected objects into an independent BGR raster."""
    if not isinstance(output_width_px, int) or output_width_px <= 0:
        raise ValueError("output_width_px doit être un entier strictement positif.")
    if not isinstance(output_height_px, int) or output_height_px <= 0:
        raise ValueError("output_height_px doit être un entier strictement positif.")

    if not isinstance(stroke_scale, (int, float)) or not isfinite(stroke_scale) or stroke_scale <= 0:
        raise ValueError("stroke_scale must be a finite positive number.")
    viewport.validate(carteConfig.image_size)
    source = carteConfig.img
    if source is None or source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("carteConfig.img doit être une image BGR à trois canaux.")

    # warpAffine performs the crop-and-resize in one exact source->raster map;
    # the same transform is passed to every existing ObjetGraphique renderer.
    scale_x = output_width_px / viewport.width
    scale_y = output_height_px / viewport.height
    transform_matrix = np.array(
        [[scale_x, 0.0, -viewport.x * scale_x], [0.0, scale_y, -viewport.y * scale_y]],
        dtype=np.float32,
    )
    raster = cv2.warpAffine(
        source,
        transform_matrix,
        (output_width_px, output_height_px),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    def source_to_raster(source_x: float, source_y: float) -> tuple[float, float]:
        return ((source_x - viewport.x) * scale_x, (source_y - viewport.y) * scale_y)

    objects = deduplicate_print_objects(get_printable_objects(layer_manager, segment, selected_modules))
    for obj in objects:
        drawable = _PrintStrokeScaledObject(obj, stroke_scale) if isinstance(obj, ObjetGraphique) else obj
        drawable.afficher(raster, source_to_raster)
    if show_labels:
        placements = compute_print_label_placements(
            objects, viewport, output_width_px, output_height_px, label_scale=label_scale,
        )
        draw_print_label_placements(raster, placements)
    return raster


def compute_objects_bounds(objects: Iterable) -> tuple[float, float, float, float] | None:
    """Return (min_x, min_y, max_x, max_y) from reliable object display frames.

    Objects whose ``cadreAffichage`` is absent or returns no two points are
    skipped.  This lets auto-fit stay usable with heterogeneous future objects.
    """
    bounds: tuple[float, float, float, float] | None = None
    for obj in objects:
        # LigneGraphique uses ``distance is None`` for an infinite line.  Its
        # current cadreAffichage() only returns its reference point, not the
        # clipped line span, so using it would produce a misleading auto-fit.
        if getattr(obj, "distance", object()) is None and hasattr(obj, "lignePixelImage"):
            continue
        frame = getattr(obj, "cadreAffichage", None)
        if not callable(frame):
            continue
        try:
            first, second = frame()
            x1, y1 = first
            x2, y2 = second
        except (TypeError, ValueError):
            continue
        if not all(isinstance(value, (int, float)) and isfinite(value) for value in (x1, y1, x2, y2)):
            continue
        left, right = sorted((float(x1), float(x2)))
        top, bottom = sorted((float(y1), float(y2)))
        if bounds is None:
            bounds = left, top, right, bottom
        else:
            bounds = min(bounds[0], left), min(bounds[1], top), max(bounds[2], right), max(bounds[3], bottom)
    return bounds


def fit_viewport_to_aspect(
    viewport: PrintViewport,
    target_aspect_ratio: float,
    image_size: tuple[int, int],
) -> PrintViewport:
    """Expand a viewport around its centre to match a target width/height ratio.

    At a source-map limit, the result uses the largest ratio-correct rectangle
    that fits.  In the rare case where the requested ratio cannot contain the
    original viewport inside the source image, this necessarily crops one axis.
    """
    if not isinstance(target_aspect_ratio, (int, float)) or not isfinite(target_aspect_ratio) or target_aspect_ratio <= 0:
        raise PrintViewportError("Le ratio cible doit être strictement positif.")
    image_width, image_height = _validate_image_size(image_size)
    viewport = viewport.clamped((image_width, image_height))
    center_x, center_y = viewport.center

    if viewport.aspect_ratio < target_aspect_ratio:
        width = viewport.height * target_aspect_ratio
        height = viewport.height
    else:
        width = viewport.width
        height = viewport.width / target_aspect_ratio

    if width > image_width or height > image_height:
        scale = min(image_width / width, image_height / height)
        width *= scale
        height *= scale

    x = min(max(center_x - width / 2, 0), image_width - width)
    y = min(max(center_y - height / 2, 0), image_height - height)
    return PrintViewport(x, y, width, height)


def zoom_viewport_at(
    viewport: PrintViewport,
    relative_x: float,
    relative_y: float,
    zoom_factor: float,
    image_size: tuple[int, int],
    *,
    min_size_px: float = DEFAULT_MIN_VIEWPORT_PX,
) -> PrintViewport:
    """Zoom a viewport around a normalized cursor position without changing its ratio.

    ``zoom_factor`` greater than one zooms in.  ``relative_x`` and
    ``relative_y`` are normally in ``[0, 1]`` and express the cursor position
    in the current preview map area.
    """
    if not isinstance(zoom_factor, (int, float)) or not isfinite(zoom_factor) or zoom_factor <= 0:
        raise PrintViewportError("Le facteur de zoom doit être strictement positif.")
    if not all(isinstance(value, (int, float)) and isfinite(value) for value in (relative_x, relative_y)):
        raise PrintViewportError("La position de zoom doit être finie.")
    if min_size_px <= 0:
        raise PrintViewportError("La taille minimale du viewport doit être strictement positive.")

    image_width, image_height = _validate_image_size(image_size)
    viewport = viewport.clamped((image_width, image_height))
    relative_x = min(max(relative_x, 0.0), 1.0)
    relative_y = min(max(relative_y, 0.0), 1.0)

    min_scale = max(min_size_px / viewport.width, min_size_px / viewport.height)
    new_width = min(max(viewport.width / zoom_factor, viewport.width * min_scale), image_width)
    new_height = new_width / viewport.aspect_ratio
    if new_height > image_height:
        new_height = image_height
        new_width = new_height * viewport.aspect_ratio

    cursor_x = viewport.x + relative_x * viewport.width
    cursor_y = viewport.y + relative_y * viewport.height
    return PrintViewport(
        cursor_x - relative_x * new_width,
        cursor_y - relative_y * new_height,
        new_width,
        new_height,
    ).clamped((image_width, image_height))


def viewport_from_screen_state(
    pan_x: float,
    pan_y: float,
    zoom_factor: float,
    frame_width: float,
    frame_height: float,
    image_size: tuple[int, int],
    target_aspect_ratio: float,
) -> PrintViewport:
    """Make an independent print viewport from one snapshot of screen state."""
    if not all(
        isinstance(value, (int, float)) and isfinite(value)
        for value in (pan_x, pan_y, zoom_factor, frame_width, frame_height)
    ):
        raise PrintViewportError("L'état écran doit contenir des nombres finis.")
    if zoom_factor <= 0 or frame_width <= 0 or frame_height <= 0:
        raise PrintViewportError("Le zoom et les dimensions de la vue écran doivent être strictement positifs.")

    image_width, image_height = _validate_image_size(image_size)
    width = min(image_width, frame_width / zoom_factor)
    height = min(image_height, frame_height / zoom_factor)
    viewport = PrintViewport(pan_x, pan_y, width, height).clamped((image_width, image_height))
    return fit_viewport_to_aspect(viewport, target_aspect_ratio, (image_width, image_height))


def compute_auto_fit_viewport(
    layer_manager,
    segment,
    selected_modules: Sequence[str],
    *,
    image_size: tuple[int, int] | None = None,
    margin_ratio: float = 0.05,
    target_aspect_ratio: float | None = None,
) -> PrintViewport:
    """Fit visible printable objects, with margin; use the full map if none fit."""
    if margin_ratio < 0:
        raise ValueError("margin_ratio ne peut pas être négatif.")
    image_size = image_size or carteConfig.image_size
    image_width, image_height = _validate_image_size(image_size)
    bounds = compute_objects_bounds(get_printable_objects(layer_manager, segment, selected_modules))
    if bounds is None:
        viewport = PrintViewport.full_map((image_width, image_height))
    else:
        left, top, right, bottom = bounds
        width = max(right - left, 1.0)
        height = max(bottom - top, 1.0)
        padding_x = width * margin_ratio
        padding_y = height * margin_ratio
        viewport = PrintViewport(
            left - padding_x,
            top - padding_y,
            width + 2 * padding_x,
            height + 2 * padding_y,
        ).clamped((image_width, image_height))
    if target_aspect_ratio is not None:
        viewport = fit_viewport_to_aspect(viewport, target_aspect_ratio, (image_width, image_height))
    return viewport


def _validate_image_size(image_size: tuple[int, int]) -> tuple[int, int]:
    if len(image_size) != 2:
        raise PrintViewportError("image_size doit contenir largeur et hauteur.")
    width, height = image_size
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)) or width <= 0 or height <= 0:
        raise PrintViewportError("Les dimensions de carte doivent être strictement positives.")
    return width, height


def _get_segment_layers(layer_manager, segment) -> Iterable:
    """Use LayerManager's public accessors, retaining its layer insertion order."""
    get_names = getattr(layer_manager, "getNomsLayers", None)
    get_layer = getattr(layer_manager, "getLayer", None)
    if callable(get_names) and callable(get_layer):
        return (get_layer(name, segment=segment) for name in get_names(segment=segment))
    layers_by_segment = getattr(layer_manager, "_layers", {})
    return layers_by_segment.get(segment, {}).values()


def _get_layer_objects(layer) -> Iterable:
    getter = getattr(layer, "getListeObjetsGraphiques", None)
    return getter() if callable(getter) else getattr(layer, "objets", ())


def _is_visible(item) -> bool:
    visible = getattr(item, "estVisible", None)
    return bool(visible()) if callable(visible) else bool(getattr(item, "visible", True))
