from types import SimpleNamespace

import cv2
import numpy as np
import pytest

import src.affichage_objets as geometrie
import src.map_print as map_print
from src.affichage_objets import CercleGraphique, LigneAzimut, LigneGraphique, ObjetGraphique, PointGraphique
from src.layerManager import LayerManager


class FakeObject:
    def __init__(self, x=0, y=0, module="stylet", visible=True, frame=None, colour=(0, 0, 255)):
        self.tags = {"module": module}
        self._visible = visible
        self.x = x
        self.y = y
        self._frame = frame if frame is not None else ((x, y), (x, y))
        self.colour = colour

    def estVisible(self):
        return self._visible and (self.layer.visible if hasattr(self, "layer") else True)

    def setLayer(self, layer):
        self.layer = layer

    def cadreAffichage(self):
        return self._frame

    def afficher(self, canvas, transform):
        x, y = transform(self.x, self.y)
        cv2.circle(canvas, (round(x), round(y)), 1, self.colour, -1)


class CarteSignatureFictive:
    image_size = (100, 100)

    def lambert93_to_pixels(self, x, y):
        return x, y

    def pixels_to_lambert93(self, x, y):
        return x, y

    def lambert93_to_gps(self, x, y):
        return x, y


@pytest.fixture
def carte_signature(monkeypatch):
    monkeypatch.setattr(geometrie, "carteConfig", CarteSignatureFictive())


def ligne_signature(point=(20, 30), vecteur=(1, 0), couleur=(1, 2, 3), epaisseur=2, style="plein", **kwargs):
    return LigneGraphique(point, vecteur, couleur=couleur, epaisseur=epaisseur, style=style, **kwargs)


def cercle_signature(centre=(20, 30), rayon_km=.01, couleur=(1, 2, 3), epaisseur=2, style="plein", **kwargs):
    point = PointGraphique("Centre", *centre)
    return CercleGraphique(point, rayon_km, couleur=couleur, epaisseur=epaisseur, style=style, **kwargs)


def context():
    manager = LayerManager()
    visible = manager.creerLayer("Visible", segment="S")
    hidden = manager.creerLayer("Hidden", segment="S")
    hidden.setVisible(False)
    other_segment = manager.creerLayer("Other", segment="T")
    return manager, visible, hidden, other_segment


def test_print_settings_defaults_and_page_sizes():
    settings = map_print.PrintSettings()
    assert settings.paper_format == "A4"
    assert settings.orientation == "portrait"
    assert settings.margin_mm == 5.0
    assert map_print.get_page_size_mm(settings) == (210.0, 297.0)
    assert map_print.get_page_size_mm(map_print.PrintSettings(orientation="landscape")) == (297.0, 210.0)


def test_print_settings_keeps_title_and_modules_immutable():
    settings = map_print.PrintSettings(title="Segment actif", selected_modules=["stylet", "ombre"])
    assert settings.title == "Segment actif"
    assert settings.selected_modules == ("stylet", "ombre")


@pytest.mark.parametrize("kwargs", [{"orientation": "square"}, {"paper_format": "A3"}, {"margin_mm": -1}])
def test_print_settings_rejects_unknown_values(kwargs):
    with pytest.raises(map_print.PrintSettingsError):
        map_print.PrintSettings(**kwargs)


def test_viewport_validation_and_full_map():
    viewport = map_print.PrintViewport(10, 20, 30, 40)
    assert viewport.validate((100, 100)) is viewport
    assert map_print.PrintViewport.full_map((100, 50)) == map_print.PrintViewport(0, 0, 100, 50)


@pytest.mark.parametrize("width,height", [(0, 1), (1, 0), (-1, 1)])
def test_viewport_rejects_non_positive_dimensions(width, height):
    with pytest.raises(map_print.PrintViewportError):
        map_print.PrintViewport(0, 0, width, height)


def test_viewport_clamps_each_edge_and_oversize_viewport():
    assert map_print.PrintViewport(-5, -2, 20, 20).clamped((100, 100)) == map_print.PrintViewport(0, 0, 20, 20)
    assert map_print.PrintViewport(95, 95, 20, 20).clamped((100, 100)) == map_print.PrintViewport(80, 80, 20, 20)
    assert map_print.PrintViewport(-10, 10, 200, 200).clamped((100, 80)) == map_print.PrintViewport(0, 0, 100, 80)


def test_fit_viewport_preserves_center_when_possible_and_ratio():
    fitted = map_print.fit_viewport_to_aspect(map_print.PrintViewport(40, 40, 20, 10), 1.0, (100, 100))
    assert fitted.center == pytest.approx((50, 45))
    assert fitted.aspect_ratio == pytest.approx(1.0)


@pytest.mark.parametrize("viewport", [map_print.PrintViewport(0, 40, 20, 10), map_print.PrintViewport(80, 40, 20, 10)])
def test_fit_viewport_stays_in_bounds_at_horizontal_edges(viewport):
    fitted = map_print.fit_viewport_to_aspect(viewport, 1.0, (100, 100))
    fitted.validate((100, 100))
    assert fitted.aspect_ratio == pytest.approx(1.0)


def test_selection_honours_layers_objects_modules_and_segment_but_not_ui_filter():
    manager, visible, hidden, other = context()
    included = FakeObject(module="stylet")
    local_hidden = FakeObject(module="stylet", visible=False)
    excluded_module = FakeObject(module="ombre")
    visible.inclureObjetDansLayer(included, local_hidden, excluded_module)
    hidden.inclureObjetDansLayer(FakeObject(module="stylet"))
    other.inclureObjetDansLayer(FakeObject(module="stylet"))
    manager.setFiltreTag("module", "ombre")

    assert map_print.get_printable_objects(manager, "S", ["stylet"]) == [included]
    assert manager.filtreActif == {"module": "ombre", "level": "tous"}


def test_selection_collects_multiple_visible_layers_in_order():
    manager = LayerManager()
    first = manager.creerLayer("A", segment="S")
    second = manager.creerLayer("B", segment="S")
    a, b = FakeObject(module="stylet"), FakeObject(module="stylet")
    first.inclureObjetDansLayer(a)
    second.inclureObjetDansLayer(b)
    assert map_print.get_printable_objects(manager, "S", ("stylet",)) == [a, b]


def test_available_modules_come_from_business_engine():
    engine = SimpleNamespace(getModulesAvecAffichage=lambda: [("stylet", "Stylet")])
    assert map_print.get_available_print_modules(engine) == (("stylet", "Stylet"),)


def test_map_area_is_reserved_for_title_and_margins():
    assert map_print.compute_map_area_mm(map_print.PrintSettings()) == (200.0, 279.0)


@pytest.mark.parametrize("margin_mm,expected_width", [(3, 204), (5, 200), (10, 190), (20, 170)])
def test_map_area_uses_the_margin_from_settings(margin_mm, expected_width):
    settings = map_print.PrintSettings(margin_mm=margin_mm)
    width, height = map_print.compute_map_area_mm(settings)
    assert width == expected_width
    assert height == 297 - 2 * margin_mm - map_print.DEFAULT_TITLE_HEIGHT_MM - map_print.DEFAULT_TITLE_GAP_MM


def test_margin_change_changes_the_target_map_aspect_ratio():
    narrow = map_print.compute_map_area_mm(map_print.PrintSettings(margin_mm=3))
    wide = map_print.compute_map_area_mm(map_print.PrintSettings(margin_mm=20))
    assert narrow[0] / narrow[1] != pytest.approx(wide[0] / wide[1])


def test_landscape_map_area_uses_the_same_five_mm_margins():
    assert map_print.compute_map_area_mm(map_print.PrintSettings(orientation="landscape")) == (287.0, 192.0)


def test_compact_title_layout_uses_six_mm_plus_two_mm_gap():
    assert map_print.DEFAULT_TITLE_HEIGHT_MM == 6.0
    assert map_print.DEFAULT_TITLE_GAP_MM == 2.0


def test_print_label_defaults_to_none_and_can_be_set():
    objet = ObjetGraphique()
    assert objet.getPrintLabel() is None
    objet.setPrintLabel("08:01")
    assert objet.getPrintLabel() == "08:01"


def test_line_and_circle_copies_preserve_print_label(carte_signature):
    line = ligne_signature()
    azimuth_line = LigneAzimut(PointGraphique("Ancrage", 20, 30), 45)
    circle = cercle_signature()
    line.setPrintLabel("08:01")
    azimuth_line.setPrintLabel("10:25")
    circle.setPrintLabel("15:59")
    assert line.copie().getPrintLabel() == "08:01"
    assert azimuth_line.copie().getPrintLabel() == "10:25"
    assert circle.copie().getPrintLabel() == "15:59"


@pytest.mark.parametrize(
    "point,vecteur",
    [((20, 30), (1, 0)), ((20, 30), (0, 1)), ((20, 20), (1, 1))],
)
def test_line_label_placements_stay_inside_raster(carte_signature, point, vecteur):
    line = ligne_signature(point, vecteur)
    line.setPrintLabel("08:01")
    placements = map_print.compute_print_label_placements([line], map_print.PrintViewport(0, 0, 100, 100), 100, 100)
    assert len(placements) == 1
    left, top, right, bottom = placements[0].bounds
    assert 0 <= left < right <= 100
    assert 0 <= top < bottom <= 100


def test_line_label_uses_the_visible_segment_even_when_its_anchor_is_outside(carte_signature):
    line = ligne_signature((150, 50), (-1, 0))
    line.setPrintLabel("08:01")
    placements = map_print.compute_print_label_placements([line], map_print.PrintViewport(0, 0, 100, 100), 100, 100)
    assert len(placements) == 1


def test_line_without_viewport_intersection_has_no_label(carte_signature):
    line = ligne_signature((150, 150), (1, 0))
    line.setPrintLabel("08:01")
    assert map_print.compute_print_label_placements([line], map_print.PrintViewport(0, 0, 100, 100), 100, 100) == []


def test_line_label_prefers_an_endpoint_over_the_center(carte_signature):
    line = ligne_signature((20, 50), (1, 0))
    line.setPrintLabel("08:01")
    placement = map_print.compute_print_label_placements([line], map_print.PrintViewport(0, 0, 100, 100), 100, 100)[0]
    label_center_x = (placement.bounds[0] + placement.bounds[2]) / 2
    assert label_center_x < 35 or label_center_x > 65


def test_line_label_prefers_the_end_farthest_from_its_definition_point(carte_signature):
    line = ligne_signature((20, 50), (1, 0))
    line.setPrintLabel("08:01")
    placement = map_print.compute_print_label_placements([line], map_print.PrintViewport(0, 0, 100, 100), 100, 100)[0]
    assert (placement.bounds[0] + placement.bounds[2]) / 2 > 65


def test_label_placement_keeps_the_effective_object_color(carte_signature):
    line = ligne_signature(couleur=(200, 100, 50))
    line.setPrintLabel("08:01")
    placement = map_print.compute_print_label_placements([line], map_print.PrintViewport(0, 0, 100, 100), 100, 100)[0]
    assert placement.color == (200, 100, 50)
    assert map_print.get_print_label_text_color(placement.color) == (100, 50, 25)


def test_circle_label_placements_cover_visible_and_partial_circles(carte_signature):
    full = cercle_signature((50, 50), rayon_km=.02)
    partial = cercle_signature((-5, 50), rayon_km=.02)
    full.setPrintLabel("08:01")
    partial.setPrintLabel("15:59")
    placements = map_print.compute_print_label_placements([full, partial], map_print.PrintViewport(0, 0, 100, 100), 100, 100)
    assert [placement.text for placement in placements] == ["08:01", "15:59"]


@pytest.mark.parametrize(
    "center,radius,expected",
    [
        ((50, 50), 10, True),
        ((-5, 50), 10, True),
        ((150, 50), 10, False),
        ((50, 50), 200, False),
        ((-10, 50), 10, True),
    ],
)
def test_circle_intersects_rect_tests_circumference_not_filled_disk(center, radius, expected):
    assert map_print.circle_intersects_rect(*center, radius, (0, 0, 100, 100)) is expected


def test_circle_outside_viewport_has_no_label_and_cannot_be_clamped_into_a_corner(carte_signature):
    circle = cercle_signature((150, -150), rayon_km=.01)
    circle.setPrintLabel("08:01")

    assert map_print.compute_print_label_placements(
        [circle], map_print.PrintViewport(0, 0, 100, 100), 100, 100,
    ) == []


def test_viewport_inside_a_large_circle_without_visible_circumference_has_no_label(carte_signature):
    circle = cercle_signature((50, 50), rayon_km=.2)
    circle.setPrintLabel("08:01")

    assert map_print.compute_print_label_placements(
        [circle], map_print.PrintViewport(0, 0, 100, 100), 100, 100,
    ) == []


def test_tangent_circle_can_place_a_label_inside_the_raster(carte_signature):
    circle = cercle_signature((-10, 50), rayon_km=.01)
    circle.setPrintLabel("08:01")

    placements = map_print.compute_print_label_placements(
        [circle], map_print.PrintViewport(0, 0, 100, 100), 100, 100,
    )
    assert len(placements) == 1
    left, top, right, bottom = placements[0].bounds
    assert 0 <= left < right <= 100
    assert 0 <= top < bottom <= 100


def test_circle_near_left_edge_places_its_label_towards_that_edge(carte_signature):
    circle = cercle_signature((20, 50), rayon_km=.01)
    circle.setPrintLabel("08:01")
    placement = map_print.compute_print_label_placements([circle], map_print.PrintViewport(0, 0, 100, 100), 100, 100)[0]
    assert placement.bounds[0] == pytest.approx(map_print.LABEL_INSET_PX)


def test_circle_near_right_edge_places_its_label_towards_that_edge(carte_signature):
    circle = cercle_signature((80, 50), rayon_km=.01)
    circle.setPrintLabel("08:01")
    placement = map_print.compute_print_label_placements([circle], map_print.PrintViewport(0, 0, 100, 100), 100, 100)[0]
    assert placement.bounds[2] == pytest.approx(100 - map_print.LABEL_INSET_PX)


def test_label_collisions_are_avoided_when_candidates_are_available(carte_signature):
    lines = [ligne_signature((20, y), (1, 0)) for y in (42, 50)]
    for line in lines:
        line.setPrintLabel("08:01")
    first, second = map_print.compute_print_label_placements(lines, map_print.PrintViewport(0, 0, 100, 100), 100, 100)
    assert not (
        first.bounds[0] < second.bounds[2]
        and second.bounds[0] < first.bounds[2]
        and first.bounds[1] < second.bounds[3]
        and second.bounds[1] < first.bounds[3]
    )


def test_crowded_label_placements_are_deterministic_and_still_returned(carte_signature):
    lines = [ligne_signature((20, 50), (1, 0)) for _ in range(3)]
    for line in lines:
        line.setPrintLabel("08:01")
    viewport = map_print.PrintViewport(0, 0, 100, 100)
    first = map_print.compute_print_label_placements(lines, viewport, 100, 100)
    second = map_print.compute_print_label_placements(lines, viewport, 100, 100)
    assert len(first) == 3
    assert first == second


def test_deduplicate_identical_lines_and_reversed_endpoints(carte_signature):
    first = ligne_signature((20, 30), (1, 0))
    same_line_reversed = ligne_signature((80, 30), (-1, 0))
    first.setPrintLabel("08:01")
    same_line_reversed.setPrintLabel("15:59")
    assert map_print.deduplicate_print_objects([first, same_line_reversed]) == [first]
    assert first.getPrintLabel() == "08:01"


@pytest.mark.parametrize(
    "kwargs",
    [{"couleur": (9, 2, 3)}, {"epaisseur": 3}],
)
def test_deduplicate_keeps_lines_with_different_effective_style(carte_signature, kwargs):
    first = ligne_signature()
    different = ligne_signature(**kwargs)
    assert map_print.deduplicate_print_objects([first, different]) == [first, different]


def test_deduplicate_identical_circles(carte_signature):
    first = cercle_signature()
    assert map_print.deduplicate_print_objects([first, cercle_signature()]) == [first]


def test_deduplicate_keeps_circles_with_different_radius(carte_signature):
    first = cercle_signature(rayon_km=.01)
    different = cercle_signature(rayon_km=.02)
    assert map_print.deduplicate_print_objects([first, different]) == [first, different]


def test_deduplicate_keeps_different_primitives_and_preserves_first_order(carte_signature):
    first_line = ligne_signature()
    circle = cercle_signature()
    duplicate_line = ligne_signature()
    assert map_print.deduplicate_print_objects([first_line, circle, duplicate_line]) == [first_line, circle]


def test_selection_happens_before_deduplication(carte_signature):
    manager, visible, hidden, _ = context()
    first = ligne_signature()
    duplicate = ligne_signature()
    hidden_duplicate = ligne_signature()
    first.ajouterTag("module", "ombre")
    duplicate.ajouterTag("module", "ombre")
    hidden_duplicate.ajouterTag("module", "ombre")
    visible.inclureObjetDansLayer(first, duplicate)
    hidden.inclureObjetDansLayer(hidden_duplicate)
    selected = map_print.get_printable_objects(manager, "S", ["ombre"])
    assert selected == [first, duplicate]
    assert map_print.deduplicate_print_objects(selected) == [first]


def test_compute_bounds_and_auto_fit_margin_and_empty_case():
    manager, visible, _, _ = context()
    first = FakeObject(module="stylet", frame=((10, 20), (20, 30)))
    second = FakeObject(module="stylet", frame=((40, 5), (60, 25)))
    visible.inclureObjetDansLayer(first, second)
    assert map_print.compute_objects_bounds([first, second]) == (10.0, 5.0, 60.0, 30.0)
    fitted = map_print.compute_auto_fit_viewport(manager, "S", ["stylet"], image_size=(100, 100), margin_ratio=.1)
    assert fitted == map_print.PrintViewport(5, 2.5, 60, 30)
    assert map_print.compute_auto_fit_viewport(manager, "S", ["ombre"], image_size=(100, 80)) == map_print.PrintViewport(0, 0, 100, 80)


def test_compute_bounds_skips_infinite_line_frames_that_are_not_reliable():
    infinite_line = FakeObject(module="stylet")
    infinite_line.distance = None
    infinite_line.lignePixelImage = object()
    assert map_print.compute_objects_bounds([infinite_line]) is None


def test_auto_fit_clamps_and_adapts_ratio():
    manager, visible, _, _ = context()
    visible.inclureObjetDansLayer(FakeObject(module="stylet", frame=((-10, 20), (20, 80))))
    viewport = map_print.compute_auto_fit_viewport(
        manager, "S", ["stylet"], image_size=(100, 100), target_aspect_ratio=1.0,
    )
    viewport.validate((100, 100))
    assert viewport.aspect_ratio == pytest.approx(1.0)


def test_zoom_viewport_at_center_keeps_center_and_ratio():
    viewport = map_print.PrintViewport(20, 20, 40, 20)
    zoomed = map_print.zoom_viewport_at(viewport, .5, .5, 2, (100, 100), min_size_px=1)
    assert zoomed.center == pytest.approx(viewport.center)
    assert zoomed.aspect_ratio == pytest.approx(viewport.aspect_ratio)
    assert zoomed.width == pytest.approx(20)


@pytest.mark.parametrize("relative_x", [.1, .9])
def test_zoom_viewport_keeps_cursor_source_location_when_not_clamped(relative_x):
    viewport = map_print.PrintViewport(20, 20, 40, 20)
    before = viewport.x + relative_x * viewport.width
    zoomed = map_print.zoom_viewport_at(viewport, relative_x, .5, 1.5, (100, 100), min_size_px=1)
    after = zoomed.x + relative_x * zoomed.width
    assert after == pytest.approx(before)


def test_zoom_viewport_clamps_and_respects_minimum_size():
    viewport = map_print.PrintViewport(0, 0, 40, 20)
    zoomed_out = map_print.zoom_viewport_at(viewport, 0, 0, .1, (50, 50), min_size_px=1)
    zoomed_in = map_print.zoom_viewport_at(viewport, .5, .5, 100, (100, 100), min_size_px=10)
    zoomed_out.validate((50, 50))
    assert zoomed_out.x == 0
    assert zoomed_in.width >= 20  # 10 px minimum applies to both dimensions.


def test_viewport_from_screen_state_at_zoom_one_adapts_to_print_ratio():
    viewport = map_print.viewport_from_screen_state(10, 20, 1, 40, 20, (100, 100), 1.0)
    assert viewport.center == pytest.approx((30, 30))
    assert viewport.aspect_ratio == pytest.approx(1.0)


def test_viewport_from_screen_state_zoom_and_edges_are_clamped():
    viewport = map_print.viewport_from_screen_state(95, 95, 2, 40, 20, (100, 100), 2.0)
    viewport.validate((100, 100))
    assert viewport.aspect_ratio == pytest.approx(2.0)


def test_viewport_from_screen_state_handles_image_smaller_than_frame():
    viewport = map_print.viewport_from_screen_state(10, 10, 1, 500, 500, (100, 50), 2.0)
    assert viewport == map_print.PrintViewport(0, 0, 100, 50)


@pytest.fixture
def small_map(monkeypatch):
    source = np.zeros((10, 10, 3), dtype=np.uint8)
    for y in range(10):
        for x in range(10):
            source[y, x] = (x, y, 0)
    config = SimpleNamespace(img=source, image_size=(10, 10))
    monkeypatch.setattr(map_print, "carteConfig", config)
    return source


def test_renderer_crops_scales_and_does_not_change_source(small_map):
    manager, visible, _, _ = context()
    visible.inclureObjetDansLayer(FakeObject(3, 4, module="stylet"))
    original = small_map.copy()
    raster = map_print.render_map_for_print(manager, "S", ["stylet"], map_print.PrintViewport(2, 3, 4, 4), 8, 8)
    assert raster.shape == (8, 8, 3)
    assert tuple(raster[0, 0]) == (2, 3, 0)
    assert tuple(raster[2, 2]) == (0, 0, 255)
    assert np.array_equal(small_map, original)


def test_renderer_excludes_object_outside_viewport_and_is_deterministic(small_map):
    manager, visible, _, _ = context()
    visible.inclureObjetDansLayer(FakeObject(8, 8, module="stylet"))
    viewport = map_print.PrintViewport(0, 0, 4, 4)
    first = map_print.render_map_for_print(manager, "S", ["stylet"], viewport, 4, 4)
    second = map_print.render_map_for_print(manager, "S", ["stylet"], viewport, 4, 4)
    assert np.array_equal(first, second)
    assert not np.any(np.all(first == (0, 0, 255), axis=2))


def test_renderer_deduplicates_supported_graphical_signatures(small_map):
    manager, visible, _, _ = context()
    calls = []
    first = FakeObject(2, 2, module="stylet")
    duplicate = FakeObject(2, 2, module="stylet")
    first.getGraphicalSignature = lambda: ("point-for-render-test",)
    duplicate.getGraphicalSignature = lambda: ("point-for-render-test",)
    first.afficher = lambda canvas, transform: calls.append("first")
    duplicate.afficher = lambda canvas, transform: calls.append("duplicate")
    visible.inclureObjetDansLayer(first, duplicate)

    map_print.render_map_for_print(manager, "S", ["stylet"], map_print.PrintViewport(0, 0, 4, 4), 4, 4)

    assert calls == ["first"]


def test_renderer_draws_print_labels_after_the_geometry(monkeypatch):
    source = np.full((100, 100, 3), 127, dtype=np.uint8)
    config = SimpleNamespace(img=source, image_size=(100, 100))
    monkeypatch.setattr(map_print, "carteConfig", config)
    monkeypatch.setattr(geometrie, "carteConfig", config)
    manager, visible, _, _ = context()
    line = ligne_signature((20, 50), (1, 0))
    line.ajouterTag("module", "stylet")
    line.setPrintLabel("08:01")
    visible.inclureObjetDansLayer(line)

    raster_with_labels = map_print.render_map_for_print(
        manager, "S", ["stylet"], map_print.PrintViewport(0, 0, 100, 100), 100, 100,
    )
    raster_without_labels = map_print.render_map_for_print(
        manager, "S", ["stylet"], map_print.PrintViewport(0, 0, 100, 100), 100, 100, show_labels=False,
    )

    assert not np.array_equal(raster_with_labels, raster_without_labels)


def test_renderer_can_scale_graphical_strokes_without_mutating_source(monkeypatch):
    source = np.zeros((100, 100, 3), dtype=np.uint8)
    config = SimpleNamespace(img=source, image_size=(100, 100))
    monkeypatch.setattr(map_print, "carteConfig", config)
    monkeypatch.setattr(geometrie, "carteConfig", config)
    manager, visible, _, _ = context()
    line = ligne_signature((10, 50), (1, 0), couleur=(0, 0, 255), epaisseur=1)
    line.ajouterTag("module", "stylet")
    visible.inclureObjetDansLayer(line)

    normal = map_print.render_map_for_print(
        manager, "S", ["stylet"], map_print.PrintViewport(0, 0, 100, 100), 100, 100,
    )
    enlarged = map_print.render_map_for_print(
        manager, "S", ["stylet"], map_print.PrintViewport(0, 0, 100, 100), 100, 100, stroke_scale=3,
    )

    assert np.count_nonzero(enlarged[:, :, 2]) > np.count_nonzero(normal[:, :, 2])
    assert line.getEpaisseur() == 1


def test_label_backing_is_semi_transparent_and_text_uses_its_object_color():
    raster = np.full((40, 80, 3), 100, dtype=np.uint8)
    placement = map_print.PrintLabelPlacement("08:01", 10, 10, 30, 16, (200, 100, 50))

    map_print.draw_print_label_placements(raster, [placement])

    assert tuple(raster[10, 10]) == (146, 146, 146)
    assert not np.any(np.all(raster == (255, 255, 255), axis=2))
    assert np.any((raster[:, :, 0] > raster[:, :, 1]) & (raster[:, :, 1] > raster[:, :, 2]))
    assert map_print.LABEL_FONT_SCALE == 0.4
