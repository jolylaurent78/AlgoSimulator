import json
from pathlib import Path

import pytest

from src.ProjectPersistence import (
    FORMAT_PROJET,
    SCHEMA_VERSION,
    chargerProjetJsonV1,
    construireSnapshotProjetJsonV1,
    sauvegarderProjetJsonV1,
)


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURES_DIR = Path(__file__).parent / "fixtures"

ROUNDTRIP_CASES = (
    pytest.param("segment_guerande_reference.json", "AlgorithmeSegment", "default", True, False, id="segment"),
    pytest.param(
        "stylet_initial_roncevaux_reference.json",
        "AlgorithmeStyletInitial",
        "default",
        False,
        True,
        id="stylet-initial",
    ),
    pytest.param(
        "lumiere_stylet_initial_bourges_reference.json",
        "AlgorithmeLumiereStyletInitial",
        "default",
        True,
        False,
        id="lumiere-stylet-initial",
    ),
    pytest.param(
        "base_cadran_roncevaux_rocamadour_reference.json",
        "AlgorithmeBaseCadran",
        "utilisateur",
        True,
        False,
        id="base-cadran",
    ),
    pytest.param(
        "cadran_final_roncevaux_lac_tremelin_reference.json",
        "AlgorithmeCadranFinal",
        "utilisateur",
        True,
        False,
        id="cadran-final",
    ),
)


def _snapshot_contractuel(moteur, layer_manager):
    """Extrait l'etat durable du snapshot sans les caches de calcul runtime."""
    snapshot = construireSnapshotProjetJsonV1(moteur, layer_manager)
    segments = []
    for segment in snapshot["segments"]:
        scenarios = []
        for scenario in segment["scenarios"]:
            scenarios.append(
                {
                    cle: scenario[cle]
                    for cle in (
                        "name",
                        "type",
                        "segment",
                        "solution",
                        "parameters",
                        "layer_preferences",
                    )
                }
            )
        segments.append({"segment": segment["segment"], "scenarios": scenarios})

    return {
        "algorithm": snapshot["algorithm"],
        "dataset": snapshot["dataset"],
        "rules": snapshot["rules"],
        "active_segment": snapshot["active_segment"],
        "active_scenario": snapshot["active_scenario"],
        "segments": segments,
    }


@pytest.mark.parametrize(
    ("fixture_name", "algorithm_name", "scenario_type", "solution", "rules_non_vides"),
    ROUNDTRIP_CASES,
)
def test_roundtrip_json_v1_des_fixtures_reelles(
    fixture_name, algorithm_name, scenario_type, solution, rules_non_vides, tmp_path
):
    moteur_original, layers_originaux = chargerProjetJsonV1(FIXTURES_DIR / fixture_name)
    etat_avant = _snapshot_contractuel(moteur_original, layers_originaux)

    assert etat_avant["algorithm"] == algorithm_name
    scenario_actif = next(
        scenario
        for segment in etat_avant["segments"]
        for scenario in segment["scenarios"]
        if scenario["name"] == etat_avant["active_scenario"]
    )
    assert scenario_actif["type"] == scenario_type
    assert scenario_actif["solution"] is solution
    assert bool(etat_avant["rules"]) is rules_non_vides

    chemin_export = tmp_path / f"{algorithm_name}.json"
    sauvegarderProjetJsonV1(chemin_export, moteur_original, layers_originaux)

    moteur_restaure, layers_restaures = chargerProjetJsonV1(chemin_export)
    assert _snapshot_contractuel(moteur_restaure, layers_restaures) == etat_avant


def test_export_emis_respecte_la_structure_json_v1(tmp_path):
    moteur, layers = chargerProjetJsonV1(
        FIXTURES_DIR / "base_cadran_roncevaux_rocamadour_reference.json"
    )
    chemin_export = tmp_path / "base-cadran.json"

    sauvegarderProjetJsonV1(chemin_export, moteur, layers)

    projet = json.loads(chemin_export.read_text(encoding="utf-8"))
    assert {
        "format",
        "schema_version",
        "algorithm",
        "dataset",
        "rules",
        "active_segment",
        "active_scenario",
        "segments",
    } <= projet.keys()
    assert projet["format"] == FORMAT_PROJET
    assert projet["schema_version"] == SCHEMA_VERSION
    assert projet["algorithm"] == "AlgorithmeBaseCadran"
    assert projet["dataset"]["events"]
    assert projet["active_segment"]
    assert projet["active_scenario"]
    assert projet["segments"]

    scenario = projet["segments"][0]["scenarios"][0]
    assert {
        "name",
        "type",
        "segment",
        "solution",
        "parameters",
        "layer_preferences",
    } <= scenario.keys()
    assert isinstance(scenario["parameters"], dict)
    assert set(scenario["layer_preferences"]) == {"color", "thickness", "visible"}


def test_roundtrip_conserve_une_preference_layer_invisible(tmp_path):
    moteur, layers = chargerProjetJsonV1(FIXTURES_DIR / "stylet_initial_roncevaux_reference.json")
    scenario = moteur.getScenario()
    layer = layers.getLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    layer.setVisible(False)

    chemin_export = tmp_path / "stylet-invisible.json"
    sauvegarderProjetJsonV1(chemin_export, moteur, layers)

    moteur_restaure, layers_restaures = chargerProjetJsonV1(chemin_export)
    scenario_restaure = moteur_restaure.getScenario()
    layer_restaure = layers_restaures.getLayer(
        scenario_restaure.getDescriptionLisible(), segment=scenario_restaure.segment
    )
    assert layer_restaure.estVisible() is False
