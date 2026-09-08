from pathlib import Path

import pytest

from src.ProjectPersistence import chargerProjetJsonV1


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURE_RONCEVAUX = Path(__file__).parent / "fixtures" / "stylet_initial_roncevaux_reference.json"
SEGMENT_RONCEVAUX = "15 Aout 778 : Bataille de Roncevaux"


def test_chargement_golden_roncevaux_restitue_le_pipeline_metier_reel():
    moteur, _ = chargerProjetJsonV1(FIXTURE_RONCEVAUX)
    scenario = moteur.getScenario()
    modules = scenario.modules

    assert moteur.segment_actif == SEGMENT_RONCEVAUX
    assert moteur.scenario_actif == "Roncevaux"
    assert set(modules) == {"soleil", "carte", "planete", "etoile", "candidats", "sentinelle"}
    assert set(moteur.regles_actives) == {"planete.sensZeta", "planete.sensCarte", "etoile.sensZeta"}

    soleil = modules["soleil"]
    assert soleil.dateDataset == "15/08/778"
    assert soleil.lettreSeg == "C"
    assert soleil.visibiliteZeta == "Non visible"
    assert soleil.dateObservation == "Sam 14/02/778"
    assert soleil.lettreObs == "C"
    assert soleil.lieuObservation == "Roncevaux"
    assert soleil.coordObservation == pytest.approx((43.020277777777764, -1.3238888888888884))

    carte = modules["carte"]
    assert carte.heure == "06:34:16"
    assert carte.azimut == pytest.approx(106.96, abs=0.01)
    assert carte.rotation == pytest.approx(-16.96, abs=0.01)
    assert carte.heureLeverZeta == "18:27:43"
    assert carte.azimutZeta == pytest.approx(144.62, abs=0.01)

    planete = modules["planete"]
    assert (planete.nom, planete.sensCarte, planete.sensZeta) == ("Neptune", "Endroit", "Endroit")
    assert planete.azimut == pytest.approx(86.32, abs=0.01)
    assert planete.hauteur == pytest.approx(19.89, abs=0.01)
    assert planete.axeFinal == pytest.approx(213.98, abs=0.01)
    assert planete.axeFinalCalcul == "86.32 +144.62 -16.96"

    etoile = modules["etoile"]
    assert (etoile.nom, etoile.sensCarte, etoile.sensZeta, etoile.origineTrait) == (
        "AlphaMajor",
        "Endroit",
        "Envers",
        "Gérardmer",
    )
    assert etoile.azimut == pytest.approx(30.26, abs=0.01)
    assert etoile.hauteur == pytest.approx(42.63, abs=0.01)
    assert etoile.axeFinal == pytest.approx(228.68, abs=0.01)
    assert etoile.axeFinalCalcul == "30.26 -144.62 -16.96"

    candidats = modules["candidats"]
    assert (candidats.heureSentinelle, candidats.ampm, candidats.distKM, candidats.selection) == (
        "09:42",
        "AM",
        12,
        "Sélectionné",
    )
    assert candidats.villeSolution == "Roncevaux"
    assert candidats.pointIntersection is not None

    sentinelle = modules["sentinelle"]
    assert (sentinelle.heure, sentinelle.sensCadran) == ("09:42", "AM")
