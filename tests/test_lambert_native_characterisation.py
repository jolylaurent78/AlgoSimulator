"""Caractérisation du contrat Lambert natif et de la géométrie image actuelle.

Ces tests figent volontairement les conversions et calculs pixels existants.
Ils ne prescrivent pas qu'un calcul géométrique futur doive passer en Lambert.
"""

from types import SimpleNamespace

import pytest

import src.affichage_objets as geometrie
import src.AlgorithmeCadranFinal as cadran_final
from src.affichage_objets import (
    ArcOriente,
    CercleGraphique,
    LigneAzimut,
    LigneEntreVilles,
    LigneGraphique,
    LigneHorizontale,
    LigneVerticale,
    PointGraphique,
    SegmentEntreVilles,
    SymboleWiki,
)
from src.AlgorithmeCadranFinal import LigneHoraireFinal


class CarteAffineFictive:
    """Carte affine simple, inversible et maîtrisée pour les tests de géométrie."""

    def __init__(self, scale=1.0, offset=(0.0, 0.0), image_size=(500, 500)):
        self.scale = scale
        self.offset = offset
        self.image_size = image_size

    def lambert93_to_pixels(self, x, y):
        return self.scale * x + self.offset[0], self.scale * y + self.offset[1]

    def pixels_to_lambert93(self, x, y):
        return (x - self.offset[0]) / self.scale, (y - self.offset[1]) / self.scale

    def lambert93_to_gps(self, x, y):
        return x / 1000, y / 1000


class CarteAffineGeneraleFictive:
    """Transformation avec cisaillement pour distinguer Lambert et pixels."""

    image_size = (500, 500)

    def lambert93_to_pixels(self, x, y):
        return 2 * x + 0.5 * y + 10, -0.25 * x + 1.5 * y + 20

    def pixels_to_lambert93(self, px, py):
        x_image = px - 10
        y_image = py - 20
        determinant = 3.125
        return (
            (1.5 * x_image - 0.5 * y_image) / determinant,
            (0.25 * x_image + 2 * y_image) / determinant,
        )

    def lambert93_to_gps(self, x, y):
        return x / 1000, y / 1000


@pytest.fixture
def carte(monkeypatch):
    configuration = CarteAffineFictive()
    monkeypatch.setattr(geometrie, "carteConfig", configuration)
    return configuration


def assert_ligne_pixels(ligne, pt1, pt2):
    assert ligne.lignePixelImage is not None
    assert ligne.lignePixelImage.pt1 == pytest.approx(pt1)
    assert ligne.lignePixelImage.pt2 == pytest.approx(pt2)


def test_ligne_graphique_conserve_son_contrat_pixel_ligne_et_segment(carte):
    ligne = LigneGraphique((50, 40), (1, 0), nom="infinie")
    segment = LigneGraphique((10, 20), (0, 1), distance=25, nom="segment")

    assert ligne.pointReference == (50, 40)
    assert ligne.vecteur == (1, 0)
    assert ligne.distance is None
    assert_ligne_pixels(ligne, (0, 40), (500, 40))

    assert segment.pointReference == (10, 20)
    assert segment.vecteur == (0, 1)
    assert segment.distance == 25
    assert not hasattr(segment, "lignePixelImage")
    assert segment.cadreAffichage() == ((10, 20), (10, 45))


def test_ligne_graphique_refuse_vecteur_nul_pour_une_ligne_infinie(carte):
    with pytest.raises(ValueError, match="Vecteur nul"):
        LigneGraphique((10, 10), (0, 0))


def test_copie_ligne_graphique_conserve_les_attributs_dun_segment(carte):
    layer = SimpleNamespace(visible=True)
    original = LigneGraphique(
        (10, 20), (1, 0), distance=30, nom="segment", couleur=(1, 2, 3),
        epaisseur=4, style="dash", layer=layer, tags={"origine": "test"},
        tooltips=["info"],
    )

    copie = original.copie()

    assert copie.pointReference == (10, 20)
    assert copie.vecteur == (1, 0)
    assert copie.nom == "segment"
    assert copie.getCouleur() == (1, 2, 3)
    assert copie.getEpaisseur() == 4
    assert copie.layer is layer
    assert copie.tooltips == ["info"]
    assert copie.distance == 30
    assert copie.style == "dash"
    assert copie.tags == {"origine": "test"}
    assert not hasattr(copie, "lignePixelImage")


@pytest.mark.parametrize(
    ("point", "vecteur", "attendu"),
    [
        ((50, 40), (1, 0), ((0, 40), (100, 40))),
        ((50, 40), (0, 1), ((50, 0), (50, 80))),
        ((50, 40), (1, 1), ((10, 0), (90, 80))),
        ((10, 10), (1, -1), ((0, 20), (20, 0))),
    ],
)
def test_crop_to_image_fige_les_intersections_avec_les_bords(carte, point, vecteur, attendu):
    carte.image_size = (100, 80)
    ligne = LigneGraphique(point, vecteur)

    assert_ligne_pixels(ligne, *attendu)


def test_crop_to_image_ligne_hors_image_et_tolerance_de_bord(carte):
    carte.image_size = (100, 80)
    hors_image = LigneGraphique((50, -1), (1, 0))
    juste_dans_la_tolerance = LigneGraphique((-0.0005, 40), (0, 1))
    hors_tolerance = LigneGraphique((-0.002, 40), (0, 1))

    assert hors_image.lignePixelImage is None
    assert_ligne_pixels(juste_dans_la_tolerance, (-0.0005, 0), (-0.0005, 80))
    assert hors_tolerance.lignePixelImage is None


def test_crop_to_image_par_un_coin_rejoint_un_autre_bord_sans_degenerescence(carte):
    carte.image_size = (100, 80)

    ligne = LigneGraphique((0, 0), (1, 1))

    assert_ligne_pixels(ligne, (0, 0), (80, 80))
    assert ligne.lignePixelImage.pt1 != ligne.lignePixelImage.pt2


def test_crop_to_image_tangent_a_un_coin_ne_cree_pas_de_segment(carte):
    carte.image_size = (100, 80)

    ligne = LigneGraphique((0, 0), (1, -1))

    assert ligne.lignePixelImage is None


def test_recalcul_des_caches_preserve_les_donnees_lambert_des_objets_natifs(carte):
    point_a = PointGraphique("A", 10, 10)
    point_b = PointGraphique("B", 30, 10)
    point = PointGraphique("P", 20, 30)
    cercle = CercleGraphique(point, 0.01)
    entre_villes = LigneEntreVilles(point_a, point_b)
    azimut = LigneAzimut(point_a, 90)
    segment = SegmentEntreVilles(point_a, point_b)

    donnees_natives = {
        "point": point.coordonneesLambert(),
        "cercle": (cercle.pointCentre.coordonneesLambert(), cercle.rayon_km),
        "entre_villes": (entre_villes.x1_l93, entre_villes.y1_l93, entre_villes.x2_l93, entre_villes.y2_l93),
        "azimut": (azimut.x_l93, azimut.y_l93, azimut.azimut_deg),
        "segment": (segment.x1_l93, segment.y1_l93, segment.x2_l93, segment.y2_l93),
    }
    assert cercle.cercle.centre == (20, 30)
    assert cercle.cercle.rayon == 10
    assert entre_villes.pointReference == (20, 10)
    assert segment.distance == 20
    assert "lignePixelImage" not in segment.__dict__

    carte.scale = 2
    carte.offset = (100, 200)
    for objet in (point, cercle, entre_villes, azimut, segment):
        objet.recalculerCoordonneesPixelAbs()

    assert point.coordonneesLambert() == donnees_natives["point"]
    assert (cercle.pointCentre.coordonneesLambert(), cercle.rayon_km) == donnees_natives["cercle"]
    assert (entre_villes.x1_l93, entre_villes.y1_l93, entre_villes.x2_l93, entre_villes.y2_l93) == donnees_natives["entre_villes"]
    assert (azimut.x_l93, azimut.y_l93, azimut.azimut_deg) == donnees_natives["azimut"]
    assert (segment.x1_l93, segment.y1_l93, segment.x2_l93, segment.y2_l93) == donnees_natives["segment"]

    assert point.pointReference == (140, 260)
    assert cercle.cercle.centre == (140, 260)
    assert cercle.cercle.rayon == 20
    assert entre_villes.pointReference == (140, 220)
    assert entre_villes.vecteur == pytest.approx((1, 0))
    assert azimut.pointReference == (120, 220)
    assert azimut.vecteur == pytest.approx((1, 0))
    assert segment.pointReference == (120, 220)
    assert segment.distance == pytest.approx(40)
    assert "lignePixelImage" not in segment.__dict__


def test_constructeur_et_recalcul_produisent_les_memes_caches_a_calibration_inchangee(carte):
    point_a = PointGraphique("A", 10, 10)
    point_b = PointGraphique("B", 30, 10)
    point = PointGraphique("P", 20, 30)
    cercle = CercleGraphique(point, 0.01)
    ligne_villes = LigneEntreVilles(point_a, point_b)
    ligne_azimut = LigneAzimut(point_a, 90)
    segment = SegmentEntreVilles(point_a, point_b)

    caches_avant = (
        point.pointReference,
        (cercle.pointReference, cercle.cercle.centre, cercle.cercle.rayon),
        (ligne_villes.pointReference, ligne_villes.vecteur, ligne_villes.lignePixelImage.pt1, ligne_villes.lignePixelImage.pt2),
        (ligne_azimut.pointReference, ligne_azimut.vecteur, ligne_azimut.lignePixelImage.pt1, ligne_azimut.lignePixelImage.pt2),
        (segment.pointReference, segment.vecteur, segment.distance),
    )
    assert "lignePixelImage" not in segment.__dict__

    for objet in (point, cercle, ligne_villes, ligne_azimut, segment):
        objet.recalculerCoordonneesPixelAbs()

    assert caches_avant == (
        point.pointReference,
        (cercle.pointReference, cercle.cercle.centre, cercle.cercle.rayon),
        (ligne_villes.pointReference, ligne_villes.vecteur, ligne_villes.lignePixelImage.pt1, ligne_villes.lignePixelImage.pt2),
        (ligne_azimut.pointReference, ligne_azimut.vecteur, ligne_azimut.lignePixelImage.pt1, ligne_azimut.lignePixelImage.pt2),
        (segment.pointReference, segment.vecteur, segment.distance),
    )
    assert "lignePixelImage" not in segment.__dict__


def test_sous_classes_ligne_verticale_et_horizontale_restent_des_notions_image(carte):
    point = PointGraphique("P", 10, 20)
    verticale = LigneVerticale(point)
    horizontale = LigneHorizontale(point)

    assert verticale.pointReference == (10, 0)
    assert verticale.vecteur == (0, 1)
    assert_ligne_pixels(verticale, (10, 0), (10, 500))
    assert horizontale.pointReference == (0, 20)
    assert horizontale.vecteur == (1, 0)
    assert_ligne_pixels(horizontale, (0, 20), (500, 20))

    carte.scale = 2
    carte.offset = (100, 200)
    verticale.recalculerCoordonneesPixelAbs()
    horizontale.recalculerCoordonneesPixelAbs()

    assert (verticale.x_l93, verticale.y_l93) == (10, 20)
    assert (horizontale.x_l93, horizontale.y_l93) == (10, 20)
    assert verticale.pointReference == (120, 0)
    assert verticale.vecteur == (0, 1)
    assert_ligne_pixels(verticale, (120, 0), (120, 500))
    assert horizontale.pointReference == (0, 240)
    assert horizontale.vecteur == (1, 0)
    assert_ligne_pixels(horizontale, (0, 240), (500, 240))

    caches_apres_recalibrage = (
        verticale.pointReference, verticale.vecteur,
        verticale.lignePixelImage.pt1, verticale.lignePixelImage.pt2,
        horizontale.pointReference, horizontale.vecteur,
        horizontale.lignePixelImage.pt1, horizontale.lignePixelImage.pt2,
    )
    verticale.recalculerCoordonneesPixelAbs()
    horizontale.recalculerCoordonneesPixelAbs()
    assert caches_apres_recalibrage == (
        verticale.pointReference, verticale.vecteur,
        verticale.lignePixelImage.pt1, verticale.lignePixelImage.pt2,
        horizontale.pointReference, horizontale.vecteur,
        horizontale.lignePixelImage.pt1, horizontale.lignePixelImage.pt2,
    )


def test_lignes_verticale_et_horizontale_conservent_lorientation_image_avec_cisaillement(monkeypatch):
    monkeypatch.setattr(geometrie, "carteConfig", CarteAffineGeneraleFictive())
    point = PointGraphique("P", 4, 6)

    verticale = LigneVerticale(point)
    horizontale = LigneHorizontale(point)

    assert (verticale.x_l93, verticale.y_l93) == (4, 6)
    assert verticale.pointReference == (21, 0)
    assert verticale.vecteur == (0, 1)
    assert_ligne_pixels(verticale, (21, 0), (21, 500))

    assert (horizontale.x_l93, horizontale.y_l93) == (4, 6)
    assert horizontale.pointReference == (0, 28)
    assert horizontale.vecteur == (1, 0)
    assert_ligne_pixels(horizontale, (0, 28), (500, 28))


def test_recalibrage_final_conserve_les_objets_natifs_sous_transformation_affine(monkeypatch, carte):
    point_a = PointGraphique("A", 0, 0)
    point_b = PointGraphique("B", 10, 0)
    point = PointGraphique("P", 4, 6)
    cercle = CercleGraphique(point, 0.01)
    arc = ArcOriente(point, 0.01, 45, -90)
    ligne_villes = LigneEntreVilles(point_a, point_b)
    ligne_azimut = LigneAzimut(point_a, 90)
    verticale = LigneVerticale(point)
    horizontale = LigneHorizontale(point)
    segment = SegmentEntreVilles(point_a, point_b)
    objets = (point, cercle, arc, ligne_villes, ligne_azimut, verticale, horizontale, segment)
    caches_simples = tuple(objet.pointReference for objet in objets)
    donnees_natives = (
        point.coordonneesLambert(),
        (cercle.pointCentre.coordonneesLambert(), cercle.rayon_km),
        (arc.pointCentre.coordonneesLambert(), arc.rayon_km, arc.azimut_depart, arc.rotation),
        (ligne_villes.x1_l93, ligne_villes.y1_l93, ligne_villes.x2_l93, ligne_villes.y2_l93),
        (ligne_azimut.x_l93, ligne_azimut.y_l93, ligne_azimut.azimut_deg),
        (verticale.x_l93, verticale.y_l93),
        (horizontale.x_l93, horizontale.y_l93),
        (segment.x1_l93, segment.y1_l93, segment.x2_l93, segment.y2_l93),
    )

    monkeypatch.setattr(geometrie, "carteConfig", CarteAffineGeneraleFictive())
    for objet in objets:
        objet.recalculerCoordonneesPixelAbs()

    assert tuple(objet.pointReference for objet in objets) != caches_simples
    assert donnees_natives == (
        point.coordonneesLambert(),
        (cercle.pointCentre.coordonneesLambert(), cercle.rayon_km),
        (arc.pointCentre.coordonneesLambert(), arc.rayon_km, arc.azimut_depart, arc.rotation),
        (ligne_villes.x1_l93, ligne_villes.y1_l93, ligne_villes.x2_l93, ligne_villes.y2_l93),
        (ligne_azimut.x_l93, ligne_azimut.y_l93, ligne_azimut.azimut_deg),
        (verticale.x_l93, verticale.y_l93),
        (horizontale.x_l93, horizontale.y_l93),
        (segment.x1_l93, segment.y1_l93, segment.x2_l93, segment.y2_l93),
    )
    assert point.pointReference == (21, 28)
    assert cercle.cercle.centre == (21, 28)
    assert arc.cercle.centre == (21, 28)
    assert cercle.cercle.rayon == arc.cercle.rayon == 20
    assert ligne_villes.pointReference == pytest.approx((20, 18.75))
    assert ligne_azimut.pointReference == (10, 20)
    assert ligne_azimut.vecteur == pytest.approx((1, 0))
    assert verticale.pointReference == (21, 0)
    assert verticale.vecteur == (0, 1)
    assert horizontale.pointReference == (0, 28)
    assert horizontale.vecteur == (1, 0)
    assert segment.pointReference == (10, 20)
    assert "lignePixelImage" not in segment.__dict__
    assert_ligne_pixels(ligne_villes, (0, 21.25), (170, 0))
    assert_ligne_pixels(ligne_azimut, (0, 20), (500, 20))
    assert_ligne_pixels(verticale, (21, 0), (21, 500))
    assert_ligne_pixels(horizontale, (0, 28), (500, 28))


@pytest.mark.parametrize(
    ("vecteur", "azimut"),
    [((0, -1), 0), ((1, 0), 90), ((0, 1), 180), ((-1, 0), 270), ((1, -1), 45), ((1, 1), 135)],
)
def test_get_azimut_carte_utilise_la_convention_image(carte, vecteur, azimut):
    ligne = LigneGraphique((50, 50), vecteur)

    assert ligne.getAzimutCarte() == pytest.approx(azimut)


@pytest.mark.parametrize(
    ("premier", "second", "angle"),
    [
        (((0, 0), (1, 0)), ((3, 4), (4, 4)), 0),
        (((0, 0), (1, 0)), ((0, 0), (0, 1)), 90),
        (((0, 0), (1, 1)), ((0, 0), (1, 0)), 45),
        (((0, 0), (1, 0)), ((0, 0), (-1, 0)), 180),
        (((0, 0), (2, 1)), ((0, 0), (-1, 2)), 90),
    ],
)
def test_angle_avec_fige_angles_pixels_explicites(carte, premier, second, angle):
    ligne_1 = geometrie.Ligne(*premier[0], *premier[1])
    ligne_2 = geometrie.Ligne(*second[0], *second[1])

    assert ligne_1.angleAvec(ligne_2) == pytest.approx(angle)


def test_intersections_ligne_graphique_et_cercle_graphique_repassent_par_le_pixel(carte):
    horizontale = LigneGraphique((50, 40), (1, 0))
    verticale = LigneGraphique((60, 50), (0, 1))
    cercle = CercleGraphique(PointGraphique("centre", 50, 40), 0.01)

    assert horizontale.intersectionLigne(verticale) == pytest.approx((60, 40))
    assert [(point.x_l93, point.y_l93) for point in horizontale.intersectionCercle(cercle)] == [
        pytest.approx((60, 40)), pytest.approx((40, 40)),
    ]
    assert cercle.intersectionLigne(horizontale) == [pytest.approx((60, 40)), pytest.approx((40, 40))]


def test_intersection_de_deux_cercles_graphiques_reconvertit_les_points_lambert(carte):
    gauche = CercleGraphique(PointGraphique("gauche", 45, 40), 0.01)
    droite = CercleGraphique(PointGraphique("droite", 55, 40), 0.01)

    points = gauche.intersectionCercle(droite)

    assert sorted((point.x_l93, point.y_l93) for point in points) == [
        pytest.approx((50, 31.3397459622)), pytest.approx((50, 48.6602540378)),
    ]


def test_projection_ligne_graphique_suit_la_chaine_lambert_pixel_lambert(carte):
    ligne = LigneGraphique((50, 40), (1, 0))
    deja_sur_la_ligne = PointGraphique("sur", 25, 40)
    a_projeter = PointGraphique("hors", 70, 75)

    assert ligne.projectionPointGraphique(deja_sur_la_ligne).coordonneesLambert() == pytest.approx((25, 40))
    assert ligne.projectionPointGraphique(a_projeter).coordonneesLambert() == pytest.approx((70, 40))


def test_distances_lambert_et_selection_pixel_restent_distinguees(carte):
    origine = PointGraphique("origine", 20, 30, epaisseur=1)
    autre = PointGraphique("autre", 20, 1030)
    cercle = CercleGraphique(origine, 0.01)
    ligne = LigneGraphique((0, 20), (1, 0))

    assert origine.distance(autre) == pytest.approx(1)
    assert origine.distanceDepuis(22, 30) == pytest.approx(1)
    assert cercle.distanceDepuis(32, 30) == pytest.approx(2)
    assert ligne.distanceDepuis(20, 27) == pytest.approx(7)


def test_conversion_locale_et_distance_ligne_suivent_la_calibration(carte):
    carte.scale = 2
    point_a = PointGraphique("A", 10, 10)
    point_b = PointGraphique("B", 80, 90)
    ligne = LigneGraphique((0, 40), (1, 0))

    assert point_a.pixelsVersMetres() == pytest.approx(0.5)
    assert point_b.pixelsVersMetres() == pytest.approx(0.5)
    assert PointGraphique("P", 20, 30).distanceLigne(ligne) == pytest.approx(0.01)


def test_distance_segment_est_lambert_et_exprimee_en_kilometres(carte):
    segment = SegmentEntreVilles(PointGraphique("A", 10, 10), PointGraphique("B", 40, 10))

    assert segment.distance == pytest.approx(30)
    assert segment.distanceSegment() == pytest.approx(0.03)


def test_points_equidistants_et_lateraux_conservent_leur_geometrie_pixel(carte):
    horizontale = LigneGraphique((50, 50), (1, 0))
    verticale = LigneGraphique((50, 50), (0, 1))
    diagonale = LigneGraphique((50, 50), (1, 1))
    centre = PointGraphique("centre", 50, 50)

    est, ouest = horizontale.pointsEquidistants(centre, 0.01)
    bas, haut = verticale.pointsEquidistants(centre, 0.01)
    diagonal_plus, diagonal_moins = diagonale.pointsEquidistants(centre, 0.01)
    lateral_1, lateral_2 = horizontale.pointsLateraux(centre, 0.01)
    lateral_vertical_1, lateral_vertical_2 = verticale.pointsLateraux(centre, 0.01)
    diagonal_1, diagonal_2 = diagonale.pointsLateraux(centre, 0.01)

    assert est.coordonneesLambert() == pytest.approx((60, 50))
    assert ouest.coordonneesLambert() == pytest.approx((40, 50))
    assert bas.coordonneesLambert() == pytest.approx((50, 60))
    assert haut.coordonneesLambert() == pytest.approx((50, 40))
    assert diagonal_plus.coordonneesLambert() == pytest.approx((57.0710678119, 57.0710678119))
    assert diagonal_moins.coordonneesLambert() == pytest.approx((42.9289321881, 42.9289321881))
    assert lateral_1.coordonneesLambert() == pytest.approx((50, 40))
    assert lateral_2.coordonneesLambert() == pytest.approx((50, 60))
    assert lateral_vertical_1.coordonneesLambert() == pytest.approx((60, 50))
    assert lateral_vertical_2.coordonneesLambert() == pytest.approx((40, 50))
    assert diagonal_1.coordonneesLambert() == pytest.approx((57.0710678119, 42.9289321881))
    assert diagonal_2.coordonneesLambert() == pytest.approx((42.9289321881, 57.0710678119))


def test_orthogonale_et_parallele_restent_definies_dans_le_repere_pixel(carte):
    ligne = LigneGraphique((50, 50), (1, 0), nom="axe")
    point = PointGraphique("P", 20, 30)

    orthogonale = ligne.orthogonale(point)
    parallele = ligne.parallele(point)

    assert isinstance(orthogonale, LigneAzimut)
    assert (orthogonale.x_l93, orthogonale.y_l93, orthogonale.azimut_deg) == pytest.approx((20, 30, 0))
    assert orthogonale.pointReference == (20, 30)
    assert orthogonale.vecteur == pytest.approx((0, -1))
    assert isinstance(parallele, LigneAzimut)
    assert (parallele.x_l93, parallele.y_l93, parallele.azimut_deg) == pytest.approx((20, 30, 90))


def test_orthogonale_et_parallele_restent_pixels_sous_transformation_affine_generale(monkeypatch):
    monkeypatch.setattr(geometrie, "carteConfig", CarteAffineGeneraleFictive())
    ligne = LigneEntreVilles(PointGraphique("A", 0, 0), PointGraphique("B", 10, 0))
    point = PointGraphique("Ancre", 4, 6)

    orthogonale = ligne.orthogonale(point)
    parallele = ligne.parallele(point)

    assert ligne.vecteur == pytest.approx((0.9922778767, -0.1240347346))
    assert isinstance(orthogonale, LigneAzimut)
    assert (orthogonale.x_l93, orthogonale.y_l93) == (4, 6)
    assert orthogonale.azimut_deg == pytest.approx(352.874983651)
    assert orthogonale.pointReference == pytest.approx((21, 28))
    assert orthogonale.vecteur == pytest.approx((-0.1240347346, -0.9922778767))
    assert ligne.vecteur[0] * orthogonale.vecteur[0] + ligne.vecteur[1] * orthogonale.vecteur[1] == pytest.approx(0, abs=1e-12)

    assert isinstance(parallele, LigneAzimut)
    assert (parallele.x_l93, parallele.y_l93) == (4, 6)
    assert parallele.azimut_deg == pytest.approx(82.874983651)
    assert parallele.vecteur == pytest.approx(ligne.vecteur)


def test_copie_des_lignes_natives_conserve_type_definition_et_proprietes(carte):
    ville1 = PointGraphique("A", 10, 10)
    ville2 = PointGraphique("B", 30, 10)
    layer = SimpleNamespace(visible=True)
    lignes = [
        LigneEntreVilles(ville1, ville2, nom="entre", couleur=(1, 2, 3), epaisseur=4,
                          layer=layer, tags={"type": "entre"}, tooltips=["entre"]),
        LigneAzimut(ville1, 75, nom="azimut", couleur=(1, 2, 3), epaisseur=4,
                     layer=layer, tags={"type": "azimut"}, tooltips=["azimut"]),
        SegmentEntreVilles(ville1, ville2, nom="segment", couleur=(1, 2, 3), epaisseur=4,
                            layer=layer, tags={"type": "segment"}, tooltips=["segment"]),
    ]
    for ligne in lignes:
        ligne.setStyle("dash")

    copies = [ligne.copie() for ligne in lignes]

    for original, copie in zip(lignes, copies):
        assert type(copie) is type(original)
        assert copie.nom == original.nom
        assert copie.getCouleur() == (1, 2, 3)
        assert copie.getEpaisseur() == 4
        assert copie.style == "dash"
        assert copie.layer is layer
        assert copie.tags == original.tags
        assert copie.tooltips == original.tooltips

    copie_entre, copie_azimut, copie_segment = copies
    assert (copie_entre.x1_l93, copie_entre.y1_l93, copie_entre.x2_l93, copie_entre.y2_l93) == (10, 10, 30, 10)
    assert (copie_azimut.x_l93, copie_azimut.y_l93, copie_azimut.azimut_deg) == (10, 10, 75)
    assert (copie_segment.x1_l93, copie_segment.y1_l93, copie_segment.x2_l93, copie_segment.y2_l93) == (10, 10, 30, 10)
    assert copie_segment.ville1 is ville1
    assert copie_segment.ville2 is ville2
    assert "lignePixelImage" not in copie_segment.__dict__


def test_copie_des_lignes_verticale_et_horizontale_conserve_ancrage_et_proprietes(carte):
    point = PointGraphique("P", 10, 20)
    layer = SimpleNamespace(visible=True)
    lignes = [
        LigneVerticale(point, nom="verticale", couleur=(1, 2, 3), epaisseur=4,
                        layer=layer, tags={"type": "verticale"}, tooltips=["verticale"]),
        LigneHorizontale(point, nom="horizontale", couleur=(1, 2, 3), epaisseur=4,
                          layer=layer, tags={"type": "horizontale"}, tooltips=["horizontale"]),
    ]
    for ligne in lignes:
        ligne.setStyle("dash")

    copies = [ligne.copie() for ligne in lignes]

    for original, copie in zip(lignes, copies):
        assert type(copie) is type(original)
        assert (copie.x_l93, copie.y_l93) == (10, 20)
        assert copie.nom == original.nom
        assert copie.getCouleur() == (1, 2, 3)
        assert copie.getEpaisseur() == 4
        assert copie.style == "dash"
        assert copie.layer is layer
        assert copie.tags == original.tags
        assert copie.tooltips == original.tooltips

    copie_verticale, copie_horizontale = copies
    assert copie_verticale.pointReference == (10, 0)
    assert copie_verticale.vecteur == (0, 1)
    assert_ligne_pixels(copie_verticale, (10, 0), (10, 500))
    assert copie_horizontale.pointReference == (0, 20)
    assert copie_horizontale.vecteur == (1, 0)
    assert_ligne_pixels(copie_horizontale, (0, 20), (500, 20))


def test_copie_point_et_cercle_conserve_type_definition_et_caches(carte):
    layer = SimpleNamespace(visible=True)
    point = PointGraphique(
        "P", 10, 20, lat=1.5, lon=2.5, nom="point", couleur=(1, 2, 3), epaisseur=4,
        style="dash", afficherNom=True, layer=layer, tags={"type": "point"}, tooltips=["point"],
    )
    cercle = CercleGraphique(
        point, 0.01, nom="cercle", couleur=(1, 2, 3), epaisseur=4, style="dash",
        layer=layer, tags={"type": "cercle"}, tooltips=["cercle"],
    )

    copie_point = point.copie()
    copie_cercle = cercle.copie()

    assert type(copie_point) is PointGraphique
    assert copie_point.coordonneesLambert() == (10, 20)
    assert copie_point.getCoordonneesGPS() == (1.5, 2.5)
    assert copie_point.style == "dash"
    assert copie_point.layer is layer
    assert copie_point.tags == {"type": "point"}
    assert copie_point.tooltips == ["point"]
    assert type(copie_cercle) is CercleGraphique
    assert copie_cercle.pointCentre is not cercle.pointCentre
    assert copie_cercle.pointCentre.coordonneesLambert() == (10, 20)
    assert copie_cercle.rayon_km == 0.01
    assert copie_cercle.style == "dash"
    assert copie_cercle.layer is layer
    assert copie_cercle.tags == {"type": "cercle"}
    assert copie_cercle.tooltips == ["cercle"]

    carte.scale = 2
    carte.offset = (100, 200)
    copie_point.recalculerCoordonneesPixelAbs()
    copie_cercle.recalculerCoordonneesPixelAbs()
    assert copie_point.pointReference == (120, 240)
    assert copie_cercle.cercle.centre == (120, 240)
    assert copie_cercle.cercle.rayon == 20


def test_paralleles_decalees_retourne_deux_lignes_azimutales_sans_import_absolu(carte):
    ligne = LigneGraphique((50, 50), (1, 0), nom="axe")

    parallele_1, parallele_2 = ligne.parallelesDecalees(0.01)

    assert isinstance(parallele_1, LigneAzimut)
    assert isinstance(parallele_2, LigneAzimut)
    assert (parallele_1.x_l93, parallele_1.y_l93, parallele_1.azimut_deg) == pytest.approx((50, 40, 90))
    assert (parallele_2.x_l93, parallele_2.y_l93, parallele_2.azimut_deg) == pytest.approx((50, 60, 90))


def test_cercle_graphique_depuis_trois_points_fige_le_pipeline_pixel(carte):
    cercle = CercleGraphique.depuisTroisPoints(
        PointGraphique("A", 20, 20), PointGraphique("B", 40, 20), PointGraphique("C", 20, 40),
    )

    assert cercle.pointCentre.coordonneesLambert() == pytest.approx((30, 30))
    assert cercle.rayon_km == pytest.approx(0.01414213562373095)
    assert cercle.cercle.centre == (30, 30)
    assert cercle.cercle.rayon == 14


def test_cercle_graphique_depuis_trois_points_alignes_retourne_none(carte):
    cercle = CercleGraphique.depuisTroisPoints(
        PointGraphique("A", 20, 20), PointGraphique("B", 30, 30), PointGraphique("C", 40, 40),
    )

    assert cercle is None


def test_cercle_graphique_est_visible_dans_hors_ou_partiellement_dans_limage(carte):
    dedans = CercleGraphique(PointGraphique("Dedans", 250, 250), 0.01)
    partiellement_dedans = CercleGraphique(PointGraphique("Partiel", -5, 250), 0.01)
    dehors = CercleGraphique(PointGraphique("Dehors", -11, 250), 0.01)

    assert dedans.estVisibledansImage()
    assert partiellement_dedans.estVisibledansImage()
    assert not dehors.estVisibledansImage()


def test_arc_oriente_conserve_ses_parametres_metier_et_regenere_son_cache(carte):
    arc = ArcOriente(PointGraphique("centre", 20, 30), 0.01, 45, -90, style="Arrow")

    assert (arc.azimut_depart, arc.rotation, arc.style) == (45, -90, "Arrow")
    assert arc.cercle.centre == (20, 30)
    assert arc.cercle.rayon == 10

    carte.scale = 2
    carte.offset = (100, 200)
    arc.recalculerCoordonneesPixelAbs()

    assert (arc.azimut_depart, arc.rotation) == (45, -90)
    assert arc.cercle.centre == (140, 260)
    assert arc.cercle.rayon == 20


def test_copie_arc_oriente_conserve_definition_et_regenere_son_cache(carte):
    layer = SimpleNamespace(visible=True)
    arc = ArcOriente(
        PointGraphique("Centre", 10, 20), 0.01, 45, -90,
        nom="arc", couleur=(1, 2, 3), epaisseur=4, style="Arrow", layer=layer,
        tags={"type": "arc"}, tooltips=["arc"],
    )

    copie = arc.copie()

    assert type(copie) is ArcOriente
    assert copie.pointCentre is arc.pointCentre
    assert (copie.pointCentre.coordonneesLambert(), copie.rayon_km) == ((10, 20), 0.01)
    assert (copie.azimut_depart, copie.rotation) == (45, -90)
    assert copie.nom == "arc"
    assert copie.getCouleur() == (1, 2, 3)
    assert copie.getEpaisseur() == 4
    assert copie.style == "Arrow"
    assert copie.layer is layer
    assert copie.tags == {"type": "arc"}
    assert copie.tooltips == ["arc"]

    carte.scale = 2
    carte.offset = (100, 200)
    copie.recalculerCoordonneesPixelAbs()
    assert copie.cercle.centre == (120, 240)
    assert copie.cercle.rayon == 20


def test_copie_symbole_wiki_conserve_source_position_et_proprietes(monkeypatch, carte):
    monkeypatch.setattr(SymboleWiki, "_iconeCache", {})
    monkeypatch.setattr(
        geometrie.cv2,
        "imread",
        lambda chemin, mode: SimpleNamespace(shape=(1, 1, 4)),
    )
    layer = SimpleNamespace(visible=True)
    symbole = SymboleWiki(
        "https://example.test/wiki", 10, 20, "icone-test-lambert-native.png",
        nom="symbole", afficherNom=True, layer=layer,
        tags={"type": "symbole"}, tooltips=["symbole"],
    )

    copie = symbole.copie()

    assert type(copie) is SymboleWiki
    assert copie.url == "https://example.test/wiki"
    assert copie.icone_path == "icone-test-lambert-native.png"
    assert copie.coordonneesLambert() == (10, 20)
    assert copie.nom == "symbole"
    assert copie.afficherNom
    assert copie.layer is layer
    assert copie.tags == {"type": "symbole"}
    assert copie.tooltips == ["symbole"]

    carte.scale = 2
    carte.offset = (100, 200)
    copie.recalculerCoordonneesPixelAbs()
    assert copie.pointReference == (120, 240)


def test_ligne_horaire_final_conserve_point_lambert_azimut_et_objets_habilles(carte, monkeypatch):
    base = PointGraphique("Base", 25, 35)
    observation = PointGraphique("Carnac", 10, 10)
    notes = {note: {"HeureLocale": heure, "AzimutCalibre": azimut} for note, heure, azimut in [
        ("C", "09:42", 170.0), ("B", "10:00", 160.0), ("A", "10:20", 150.0), ("G", "11:00", 140.0),
        ("F", "11:20", 130.0), ("E", "11:40", 120.0), ("D", "12:00", 110.0), ("J", "12:20", 100.0),
        ("L", "08:30", 138.5),
    ]}
    monkeypatch.setattr(cadran_final, "villes_dict", {"Base": base, "Carnac": observation})
    monkeypatch.setattr(cadran_final, "convertirHeureLocaleVersUTC", lambda _heure, _lon: "UTC")
    monkeypatch.setattr(cadran_final, "MyJulianDate", SimpleNamespace(fromString=lambda *_args: "date"))
    monkeypatch.setattr(cadran_final, "positionSoleil", lambda *_args: (0.0, 180.0))

    module = LigneHoraireFinal()
    module.sentinelleLumiere = notes
    module.lieuObservationSegment = "Carnac"
    module.lettreDomSegment = "C"
    module.lettreDeclDataset = "F"
    module.dateSegmentDataset = "25/07/778"
    module.dateDataset = "25/07/778"
    module.azimutMidiStylet = 100.0
    module.baseStylet = "Base"
    module.heureAMPMLumiere = "AM"
    module.choixCalendrierLumiere = "Standard"
    module.choixHeure = "="
    module.sensCarte = "Endroit"

    module.calculer()

    assert len(module.listeLigneHoraire) == 16
    heure, delta, ampm, candidat, ligne = module.listeLigneHoraire[0]
    assert (heure, delta, ampm, candidat) == ("09:42", -10.0, "AM", True)
    assert isinstance(ligne, LigneAzimut)
    assert (ligne.x_l93, ligne.y_l93, ligne.azimut_deg) == pytest.approx((25, 35, 90))
    assert ligne.pointReference == pytest.approx((25, 35))
    assert ligne.vecteur == pytest.approx((1, 0))

    objets = module.construireRepresentationCarte()

    assert objets[0] is ligne
    assert objets == [item[4] for item in module.listeLigneHoraire]
    assert ligne.nom == "Ligne Horaire 09:42"
    assert ligne.getCouleur() == LigneHoraireFinal.COULEUR_TRAIT_CANDIDAT
    assert ligne.tags["level"] == "design"
    assert (ligne.x_l93, ligne.y_l93, ligne.azimut_deg) == pytest.approx((25, 35, 90))
