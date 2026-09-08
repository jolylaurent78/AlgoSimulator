from pathlib import Path

import pytest

from src.ProjectPersistence import chargerProjetJsonV1


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURE_GUERANDE = Path(__file__).parent / "fixtures" / "segment_guerande_reference.json"
SEGMENT_GUERANDE = "12 Avril 1365 : Traité de Guérande"


@pytest.fixture
def projet_guerande():
    return chargerProjetJsonV1(FIXTURE_GUERANDE)


def test_chargement_golden_guerande_restitue_modules_et_cache(projet_guerande):
    moteur, _ = projet_guerande
    scenario = moteur.getScenario()
    modules = scenario.modules

    assert moteur.segment_actif == SEGMENT_GUERANDE
    assert moteur.scenario_actif == "08/08 1365"
    assert set(modules) == {"segment", "cadran", "planete", "axeterre", "annee"}

    segment = modules["segment"]
    assert (segment.extremite1Dataset, segment.milieuSegmentDataset, segment.extremite2Dataset) == (
        "Dieppe",
        "Forbach",
        "Bourges",
    )
    assert segment.angle == pytest.approx(46.48, abs=0.01)
    assert segment.choixAngleStr == "133.52°"
    assert segment.choixAngle == pytest.approx(133.52)

    cadran = modules["cadran"]
    assert cadran.lieuObservation == "Dieppe"
    assert cadran.latitude == pytest.approx(49.92, abs=0.01)
    assert cadran.declinaison == pytest.approx(14.72, abs=0.01)
    assert (cadran.datePrintemps, cadran.dateEte) == ("24/04/1066", "08/08/1066")

    planete = modules["planete"]
    assert planete.azimutLigne1 == pytest.approx(279.71, abs=0.01)
    assert planete.azimutCible == pytest.approx(279.71, abs=0.01)
    assert planete.planete == "Uranus"

    axe = modules["axeterre"]
    assert axe.axeTerreStr == "Forbach -> Bourges"
    assert axe.axeTerre == pytest.approx(233.24, abs=0.01)
    assert axe.sensCarte == "Bon sens"
    assert axe.azimut == pytest.approx(233.24, abs=0.01)

    annee = modules["annee"]
    assert annee.angle == pytest.approx(46.48, abs=0.01)
    assert annee.choixAngle == "complémentaire"
    assert annee.angleAnalyse == pytest.approx(133.52, abs=0.01)
    assert annee.borneMin == "1300"
    assert annee.periode == 100
    assert annee.listeAnneesSelection == 6

    entree_1365 = next(entree for entree in annee.listeAnnees if entree[0] == 1365.0)
    assert float(entree_1365[1]) == pytest.approx(2219751.125, abs=1e-6)
    assert entree_1365[2:] == ["Opposé", "53.24°", "283.22°", "3.51°"]


def test_cycle_astronomique_reel_1365_depuis_le_golden(projet_guerande):
    moteur, _ = projet_guerande
    annee = moteur.getScenario().modules["annee"]
    annee.listeAnnees = []
    annee.listeAnneesSelection = None

    assert annee.calculerAnnees(init=True) is False
    annee.annee = 1365

    termine = annee.calculerAnnees(init=False)

    assert termine is False
    assert annee.annee == 1366
    assert len(annee.listeAnnees) == 1
    entree = annee.listeAnnees[0]
    assert entree[0] == 1365
    assert float(entree[1]) == pytest.approx(2219751.125, abs=1e-6)
    assert entree[2:] == ("Opposé", "53.24°", "283.22°", "3.51°")
