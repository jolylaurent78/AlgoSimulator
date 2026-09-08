from pathlib import Path

import pytest

from src.ProjectPersistence import chargerProjetJsonV1


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURE_LAC_TREMELIN = Path(__file__).parent / "fixtures" / "cadran_final_roncevaux_lac_tremelin_reference.json"
SEGMENT_RONCEVAUX = "15 Aout 778 : Bataille de Roncevaux"


def test_chargement_golden_lac_tremelin_restitue_le_pipeline_cadran_final_reel():
    moteur, _ = chargerProjetJsonV1(FIXTURE_LAC_TREMELIN)
    scenario = moteur.getScenario()
    modules = scenario.modules

    assert moteur.segment_actif == SEGMENT_RONCEVAUX
    assert moteur.scenario_actif == "Lac Trémelin"
    assert set(modules) == {"segment", "stylet", "lumiere", "ombre", "candidat"}

    segment = modules["segment"]
    assert (segment.dateDataset, segment.lettreDom, segment.lieuObservation) == ("15/08/778", "C", "Roncevaux")

    stylet = modules["stylet"]
    assert (
        stylet.styletDataset,
        stylet.base1Dataset,
        stylet.base2Dataset,
        stylet.choixBase,
        stylet.base,
        stylet.choixCalendrier,
        stylet.lettreChoix,
        stylet.P2M2,
        stylet.lettre,
        stylet.octave,
    ) == ("Roncevaux", "Saint-Amour", "Rocamadour", "Base 2", "Rocamadour", "Standard", "C", "+2", "E", "/4")
    assert stylet.distanceRef == pytest.approx(891.2, abs=0.1)
    assert stylet.hauteur == pytest.approx(250.1, abs=0.1)
    assert stylet.azimutMidi == pytest.approx(13.56, abs=0.01)

    lumiere = modules["lumiere"]
    assert (
        lumiere.choixCalendrier,
        lumiere.lettreChoix,
        lumiere.choixHeure,
        lumiere.heureAMPM,
        lumiere.dateSegmentDataset,
        lumiere.heureLocale,
        lumiere.heureUTC,
    ) == ("Standard", "C", "+2", "PM", "25/07/778", "15:59", "16:04:18")
    assert lumiere.azimut == pytest.approx(263.21, abs=0.01)
    assert lumiere.hauteur == pytest.approx(35.58, abs=0.01)
    assert lumiere.deltaMidi == pytest.approx(-83.21, abs=0.01)
    assert lumiere.distance == pytest.approx(349.5, abs=0.1)

    ombre = modules["ombre"]
    assert (
        ombre.choixCalendrier,
        ombre.lettreChoix,
        ombre.choixHeure,
        ombre.heureLocale,
        ombre.sensCarte,
    ) == ("Standard", "C", "=", "09:42", "Endroit")
    assert ombre.azimutMidiLocale == pytest.approx(177.91, abs=0.01)
    assert [heure for heure, _ in ombre.listeCandidatsHeure] == ["09:42", "14:18"]
