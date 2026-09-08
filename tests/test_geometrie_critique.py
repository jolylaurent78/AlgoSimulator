from types import SimpleNamespace

import numpy as np
import pytest

import src.affichage_objets as geometrie
from src.affichage_objets import Cercle, CercleGraphique, Ligne
from src.carte_config import CarteConfig


def assert_points_proches(points, attendus):
    assert len(points) == len(attendus)
    for x_attendu, y_attendu in attendus:
        assert any(x == pytest.approx(x_attendu) and y == pytest.approx(y_attendu) for x, y in points)


def test_longueur_et_distance_dune_ligne_sont_euclidiennes():
    assert Ligne(0, 0, 0, 0).longueur() == 0
    assert Ligne(0, 0, 3, 4).longueur() == 5
    assert Ligne(3, 4, 0, 0).longueur() == 5
    assert Ligne(0, 0, 10, 0).distanceAuPoint(4, 3) == 3


@pytest.mark.parametrize(
    ("ligne", "point", "attendu"),
    [
        (Ligne(0, 0, 10, 0), (4, 3), (4, 0)),
        (Ligne(0, 0, 0, 10), (3, 4), (0, 4)),
        (Ligne(0, 0, 10, 10), (4, 4), (4, 4)),
        (Ligne(0, 0, 10, 10), (4, 6), (5, 5)),
    ],
)
def test_projection_orthogonale_sur_droite_infinie(ligne, point, attendu):
    assert ligne.projection(*point) == pytest.approx(attendu)


def test_intersection_de_droites_est_symetrique_et_non_limitee_aux_segments():
    horizontale = Ligne(0, 0, 1, 0)
    verticale_hors_segment = Ligne(2, -1, 2, 1)
    diagonale = Ligne(0, 0, 10, 10)
    autre_diagonale = Ligne(0, 10, 10, 0)

    assert horizontale.intersection(verticale_hors_segment) == pytest.approx((2, 0))
    assert horizontale.intersection(verticale_hors_segment) == verticale_hors_segment.intersection(horizontale)
    assert diagonale.intersection(autre_diagonale) == pytest.approx((5, 5))


@pytest.mark.parametrize(
    ("ecart", "intersection_attendue"),
    [
        (0.0, None),
        (1e-11, None),
        (1e-9, "hors_tolerance"),
    ],
)
def test_paralleles_et_quasi_paralleles_respectent_la_tolerance_reelle(ecart, intersection_attendue):
    horizontale = Ligne(0, 0, 1, 0)
    presque_parallele = Ligne(0, 1, 1, 1 + ecart)

    resultat = horizontale.intersection(presque_parallele)

    if intersection_attendue is None:
        assert resultat is None
    else:
        assert resultat == pytest.approx((-1 / ecart, 0))


@pytest.mark.parametrize(
    ("ligne", "azimut"),
    [
        (Ligne(0, 0, 0, -1), 0),
        (Ligne(0, 0, 1, 0), 90),
        (Ligne(0, 0, 0, 1), 180),
        (Ligne(0, 0, -1, 0), 270),
    ],
)
def test_azimut_ligne_utilise_la_convention_boussole_des_pixels(ligne, azimut):
    assert ligne.azimut() == pytest.approx(azimut)
    assert Ligne.depuisPointEtAzimut((0, 0), azimut).azimut() == pytest.approx(azimut)


def test_ligne_degeneree_a_des_contrats_explicites():
    degeneree = Ligne(2, 3, 2, 3)

    assert degeneree.projection(8, 9) == (2, 3)
    assert degeneree.intersections_avec_cercle(Cercle((0, 0), 5)) == []
    with pytest.raises(ValueError, match="Vecteur nul"):
        degeneree.azimut()
    with pytest.raises(ValueError, match="Ligne dégénérée"):
        degeneree.distanceAuPoint(0, 0)
    with pytest.raises(ValueError, match="Vecteur nul"):
        Ligne.depuisPointEtVecteur((0, 0), (0, 0))


def test_cercle_contient_centre_bord_et_exterieur():
    cercle = Cercle((0, 0), 5)

    assert cercle.contient(0, 0)
    assert cercle.contient(3, 4)
    assert not cercle.contient(3, 5)


def test_cercle_de_rayon_nul_est_reduit_a_un_point_de_tangence():
    cercle = Cercle((0, 0), 0)

    assert cercle.contient(0, 0)
    assert Ligne(-1, 0, 1, 0).intersections_avec_cercle(cercle) == [(0, 0)]


@pytest.mark.parametrize(
    ("ligne", "attendus"),
    [
        (Ligne(-10, 0, 10, 0), [(-5, 0), (5, 0)]),
        (Ligne(-10, 5, 10, 5), [(0, 5)]),
        (Ligne(-10, 6, 10, 6), []),
    ],
)
def test_intersections_droite_infinie_cercle_secante_tangente_ou_exterieure(ligne, attendus):
    points = ligne.intersections_avec_cercle(Cercle((0, 0), 5))

    assert_points_proches(points, attendus)


class FauxPoint:
    def __init__(self, _nom, x, y):
        self.x = x
        self.y = y


def cercle_graphique_factice(centre, rayon):
    return SimpleNamespace(cercle=Cercle(centre, rayon))


@pytest.mark.parametrize(
    ("centre_droit", "rayon_droit", "attendus"),
    [
        ((8, 0), 5, [(4, -3), (4, 3)]),
        ((10, 0), 5, [(5, 0)]),
        ((2, 0), 3, [(5, 0)]),
        ((11, 0), 5, []),
        ((1, 0), 1, []),
        ((0, 0), 5, []),
    ],
)
def test_intersections_cercle_cercle_couvrent_secantes_tangences_et_cas_sans_solution(
    monkeypatch, centre_droit, rayon_droit, attendus
):
    monkeypatch.setattr(geometrie, "PointGraphique", FauxPoint)
    monkeypatch.setattr(
        geometrie,
        "carteConfig",
        SimpleNamespace(pixels_to_lambert93=lambda x, y: (x, y)),
    )
    gauche = cercle_graphique_factice((0, 0), 5)
    droite = cercle_graphique_factice(centre_droit, rayon_droit)

    points = CercleGraphique.intersectionCercle(gauche, droite)

    assert_points_proches([(point.x, point.y) for point in points], attendus)


def test_transformation_affine_lambert_pixels_est_inversible_sans_carte_reelle():
    configuration = CarteConfig.__new__(CarteConfig)
    configuration.A = np.array([[2.0, 0.0], [0.0, -3.0]])
    configuration.offset = np.array([10.0, 20.0])
    configuration.A_inv = np.linalg.inv(configuration.A)

    pixels = configuration.lambert93_to_pixels(4, 5)

    assert pixels == pytest.approx((18, 5))
    assert configuration.pixels_to_lambert93(*pixels) == pytest.approx((4, 5))
