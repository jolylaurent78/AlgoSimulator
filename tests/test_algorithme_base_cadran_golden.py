from pathlib import Path

import pytest

from src.ProjectPersistence import chargerProjetJsonV1


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURE_ROCAMADOUR = Path(__file__).parent / "fixtures" / "base_cadran_roncevaux_rocamadour_reference.json"
SEGMENT_RONCEVAUX = "15 Aout 778 : Bataille de Roncevaux"


def test_chargement_golden_rocamadour_restitue_le_pipeline_base_cadran_reel():
    moteur, _ = chargerProjetJsonV1(FIXTURE_ROCAMADOUR)
    scenario = moteur.getScenario()
    modules = scenario.modules

    assert moteur.segment_actif == SEGMENT_RONCEVAUX
    assert moteur.scenario_actif == "Rocamadour"
    assert set(modules) == {"segment", "cercleHoraire", "partition", "cercleDistance", "candidatBase"}

    segment = modules["segment"]
    assert (
        segment.dateDataset,
        segment.lettreDom,
        segment.lettreDeclDataset,
        segment.choixCalendrier,
        segment.lettreChoix,
    ) == ("15/08/778", "C", "F", "Déclinaison", "F")

    cercle_horaire = modules["cercleHoraire"]
    assert (
        cercle_horaire.stylet,
        cercle_horaire.heureStylet,
        cercle_horaire.styletAMPM,
        cercle_horaire.heureAMPM,
        cercle_horaire.heureSubstitution,
        cercle_horaire.lieuObservation,
        cercle_horaire.dateDataset,
        cercle_horaire.heureSentinelle,
        cercle_horaire.cercleAMPM,
    ) == ("Roncevaux", "09:42", "AM", "AM", "=", "Carnac", "15/08/778", "10:25", "AM")
    assert cercle_horaire.angleHoraire == pytest.approx(38.62, abs=0.01)

    partition = modules["partition"]
    assert (
        partition.dateSegmentDataset,
        partition.lieuObservation,
        partition.leverSoleilUTC,
        partition.leverSoleilLocale,
        partition.leverlLocaleP6,
        partition.heureUTCCarnac,
        partition.lettreDeclDataset,
        partition.P2M2,
        partition.lettrePartition,
        partition.typeSymetrie,
    ) == (
        "25/07/778",
        "Roncevaux",
        "04:48:38",
        "04:43:20",
        "10:43:20",
        "10:55:39",
        "F",
        "+2",
        "A",
        "Flip vertical",
    )
    assert partition.azimutSoleil == pytest.approx(143.02, abs=0.01)
    assert partition.candidats

    cercle_distance = modules["cercleDistance"]
    assert (
        cercle_distance.centreCercle,
        cercle_distance.lettreDeclDataset,
        cercle_distance.P2M2,
        cercle_distance.lettreHauteur,
        cercle_distance.octave,
        cercle_distance.lieuObservation,
        cercle_distance.dateDataset,
        cercle_distance.heureReference,
    ) == ("Stylet", "F", "+2", "A", "/2", "Carnac", "15/08/778", "10:25")
    assert cercle_distance.distanceClef == pytest.approx(891.2, abs=0.1)
    assert cercle_distance.hauteurStylet == pytest.approx(707.3, abs=0.1)
    assert cercle_distance.hauteurSoleil == pytest.approx(50.04, abs=0.01)
    assert cercle_distance.distanceRef == pytest.approx(296.4, abs=0.1)

    assert modules["candidatBase"].listeCandidats
