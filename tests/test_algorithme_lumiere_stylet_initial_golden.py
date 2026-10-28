from pathlib import Path

import pytest

from src.ProjectPersistence import chargerProjetJsonV1


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURE_BOURGES = Path(__file__).parent / "fixtures" / "lumiere_stylet_initial_bourges_reference.json"
SEGMENT_RONCEVAUX = "15 Aout 778 : Bataille de Roncevaux"


def test_chargement_golden_bourges_restitue_le_pipeline_lumiere_reel():
    moteur, _ = chargerProjetJsonV1(FIXTURE_BOURGES)
    scenario = moteur.getScenario()
    modules = scenario.modules

    assert moteur.segment_actif == SEGMENT_RONCEVAUX
    assert moteur.scenario_actif == "Bourges"
    assert set(modules) == {"observation", "heuredate", "soleil", "stylet"}

    observation = modules["observation"]
    assert observation.dateDataset == "15/08/778"
    assert observation.lettreDom == "C"
    assert observation.lieuObservation == "Roncevaux"
    assert observation.heureLeverSoleilStrasbourg == "04:24:04"
    assert observation.azimutLeverSoleil == pytest.approx(68.74, abs=0.01)
    assert observation.rotationCarte == pytest.approx(21.26, abs=0.01)

    heuredate = modules["heuredate"]
    assert (
        heuredate.choixCalendrier,
        heuredate.lettreChoix,
        heuredate.choixHeure,
        heuredate.heureAMPM,
        heuredate.heureLocale,
    ) == ("Standard", "C", "=", "AM", "09:43:00")

    soleil = modules["soleil"]
    assert (
        soleil.stylet,
        soleil.validite,
        soleil.heureSentinelle,
        soleil.choixHeure,
        soleil.sourceHeure,
        soleil.heureObservation,
        soleil.heureUTC,
    ) == ("Roncevaux", "Valide", "09:43:00", "Même heure", "Stylet", "09:43:00", "09:48:18")

    stylet = modules["stylet"]
    assert stylet.distanceMetz == pytest.approx(891.2, abs=0.01)
    assert stylet.hauteurStylet == pytest.approx(594.8, abs=0.01)
    assert stylet.formuleDistance == "891 / 2**-5/12 * 2**-12/12"
    # Nouvelle heure S1 directe et décalage de longitude exact, sans modifier
    # la formule de hauteur ou la rotation de carte constatées ci-dessus.
    assert stylet.hauteurSoleil == pytest.approx(47.71811181208787, abs=0.01)
    assert stylet.distanceStylet == pytest.approx(540.8839876654071, abs=0.01)
    assert stylet.azimutSoleil == pytest.approx(124.2877338306546, abs=0.01)
    assert stylet.sensCarte == "Envers"
    assert stylet.formuleAxeCarte == "360-124.29-21.26"
    assert stylet.axeCarte == pytest.approx(214.4550991545608, abs=0.01)
    assert stylet.dateObservationUT1Soleil == soleil.dateObservationUT1
    assert stylet.octave == "x1"
