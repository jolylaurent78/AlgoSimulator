"""Méthode expérimentale : admissibilité métrique séparée du choix du centre."""
from hashlib import sha256
from math import cos, sin, radians, tan, dist, isfinite
from pathlib import Path

import numpy as np
import pytest

from src.AlgorithmeCadranFinal import CandidatFinal, calculerCandidatPondere


def triangle(angle, hauteur=20000, bs=None):
    return calculerCandidatPondere(
        (100000., hauteur), [(110000., 0.), (0., 0.)] if bs is None else bs,
        (0., 0.), (1., 0.), (cos(radians(angle)), sin(radians(angle))),
    )


@pytest.mark.parametrize("angle", [0, 1e-12, 1e-8, 5, 10, 15, 30, 45, 60, 90, 135, 180])
def test_angle_non_oriente_et_ponderation(angle):
    g = triangle(angle)
    aigu = min(angle % 180, 180 - angle % 180)
    assert g.angle == pytest.approx(aigu, abs=1e-12)
    assert g.poids == pytest.approx(min(1, (aigu/45)**2))
    assert g.q == (100000., 0.)
    assert g.m == (100000., 10000.)
    assert g.distance_aq == 20
    assert g.b == (110000., 0.)
    assert all(isfinite(x) for x in g.p)
    if aigu <= 1e-8:
        assert g.p == pytest.approx(g.m, abs=1e-4)
    else:
        assert g.c == pytest.approx((100000-20000/tan(radians(angle)), 0.), abs=1e-7)
        attendu = tuple((1-g.poids)*g.m[i]+g.poids*g.g[i] for i in (0, 1))
        assert g.p == pytest.approx(attendu, abs=1e-7)
        if aigu >= 45:
            assert g.p == pytest.approx(g.g, abs=1e-7)


def test_projection_orthogonale_oblique_en_metres():
    a = (700000., 6630000.)
    origine = (700000., 6600000.)
    g = calculerCandidatPondere(a, [], origine, (3., 4.), (1., 0.))
    assert g.q == pytest.approx((714400., 6619200.))
    aq = np.subtract(a, g.q)
    assert np.dot(aq, (3., 4.)) == pytest.approx(0, abs=1e-7)
    assert g.distance_aq == pytest.approx(18)
    assert g.p == g.m  # B absent, sans empêcher la décision d'admissibilité.
    assert g.distance_p_droite == pytest.approx(9)


@pytest.mark.parametrize(("hauteur", "admis"), [(30000, True), (30000.001, False), (29999.999, True)])
def test_limite_admissibilite_30_km(hauteur, admis):
    assert (triangle(15, hauteur) is not None) is admis


def test_parallelisme_sans_c_et_absence_de_b_signales():
    parallele = triangle(0)
    assert parallele.c is parallele.g is None
    assert parallele.p == parallele.m
    assert "parallèles" in parallele.methode
    sans_b = triangle(15, bs=[])
    assert sans_b.c is not None
    assert sans_b.g is None
    assert sans_b.p == sans_b.m
    assert "B absent" in sans_b.methode
    deux_absents = triangle(0, bs=[])
    assert "B absent, C absent" in deux_absents.methode


def test_c_lointain_sans_filtre_geographique_et_limite_stable():
    g = triangle(1e-8)
    assert dist(g.a, g.c) > 1e12
    assert "pondéré" in g.methode
    assert g.p == pytest.approx(g.m, abs=1e-4)


def test_b_le_plus_proche_independant_de_l_ordre():
    bs = [(0., 0.), (110000., 0.)]
    assert triangle(30, bs=bs).b == triangle(30, bs=bs[::-1]).b == (110000., 0.)


def test_directions_non_orientees_et_origine_eloignee_invariantes():
    g = triangle(20)
    inverse = calculerCandidatPondere(g.a, [g.b], (500000., 0.), (-1., 0.),
                                      (-cos(radians(20)), -sin(radians(20))))
    assert inverse.angle == pytest.approx(g.angle)
    assert inverse.p == pytest.approx(g.p, abs=1e-7)


def test_direction_nulle_refusee():
    with pytest.raises(ValueError, match="Direction nulle"):
        calculerCandidatPondere((0., 0.), [], (0., 0.), (0., 0.), (1., 0.))


def test_pipeline_reel_calibration_et_infos_sans_ecriture():
    from src.ProjectPersistence import chargerProjetJsonV1
    from src.carte_config import carteConfig
    fichier = Path('tests/fixtures/cadran_final_roncevaux_lac_tremelin_reference.json')
    empreinte = sha256(fichier.read_bytes()).hexdigest()
    moteur, _ = chargerProjetJsonV1(fichier)
    c = moteur.getScenario().modules['candidat']
    geometries = c.calculerGeometriesPonderees()
    affiches = c.construireRepresentationCarte()
    assert geometries and len(affiches) == len(geometries)
    for cercle, (_, _, g) in zip(affiches, geometries):
        assert cercle.pointCentre.coordonneesLambert() == g.p
        assert cercle.getRayonKm() == 20
        assert cercle.tags == {"level": "construction"}
        assert len(cercle.tooltips) == 8
        assert g.distance_aq <= 30
        assert g.b is not None
        assert 0 <= g.angle <= 90
    assert len(c.construireRepresentationCarte(methode='historique')) == 2
    assert [p.pointCentre.coordonneesLambert() for p in c.construireRepresentationCarteHistorique()] == [
        p.pointCentre.coordonneesLambert() for p in c.construireRepresentationCarte(methode='historique')]
    # La direction métrique est celle de la carte, pas son azimut pixel réinterprété.
    ombre = c.listeCandidatsHeureOmbre[0][1]
    v = carteConfig.A_inv @ ombre.vecteur
    for _, heure, g in geometries:
        if heure == c.listeCandidatsHeureOmbre[0][0]:
            assert np.dot(np.subtract(g.a, g.q), v) == pytest.approx(0, abs=1e-5)
    with pytest.raises(ValueError, match='Méthode'):
        c.construireRepresentationCarte(methode='inconnue')
    assert sha256(fichier.read_bytes()).hexdigest() == empreinte
