import copy
import json
from types import SimpleNamespace

import pytest

from src.AlgorithmeManager import AlgorithmeManager, Scenario
from src.ProjectPersistence import FORMAT_PROJET, SCHEMA_VERSION, chargerProjetJsonV1


def _evenement(nom):
    return {
        "event": nom,
        "LettreSegment": "C",
        "Extremite1": "Dieppe",
        "MilieuSegment": "Bourges",
        "Extremite2": "Forbach",
        "DateSegment": "15/08/778",
        "Date": "15/08/778",
        "Stylet": "Roncevaux",
        "LettreDecl": "F",
        "Base1": "Saint-Amour",
        "Base2": "Rocamadour",
    }


def snapshot_valide_minimal():
    segment = "Segment A"
    scenario = {
        "name": "Scenario A",
        "type": "default",
        "segment": segment,
        "solution": False,
        "parameters": {},
        "cached_results": {},
        "layer_preferences": {"color": [0, 0, 0], "thickness": 1, "visible": True},
    }
    return {
        "format": FORMAT_PROJET,
        "schema_version": SCHEMA_VERSION,
        "algorithm": "AlgorithmeSegment",
        "dataset": {"events": [_evenement(segment)]},
        "rules": {},
        "active_segment": segment,
        "active_scenario": scenario["name"],
        "segments": [{"segment": segment, "scenarios": [scenario]}],
    }


def ecrire_snapshot(tmp_path, snapshot):
    chemin = tmp_path / "snapshot.json"
    chemin.write_text(json.dumps(snapshot), encoding="utf-8")
    return chemin


@pytest.fixture
def loader_sans_calcul_metier(monkeypatch):
    """Conserve le flux du loader, en neutralisant seulement les calculs métier."""

    def initialiser_manager(moteur, _layer_manager):
        moteur._templates_modules = {
            "module": {"default": {"template": SimpleNamespace(valeur="valeur par défaut")}}
        }
        moteur._scenarios = {}
        moteur.scenario_actif = moteur.dataset.segment
        moteur.segment_actif = moteur.dataset.segment
        moteur.ordreModules = []
        moteur.regles_actives = {}

    monkeypatch.setattr(AlgorithmeManager, "__init__", initialiser_manager)
    monkeypatch.setattr(AlgorithmeManager, "calculerModules", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(Scenario, "construireRepresentationCarte", lambda *_args, **_kwargs: None)


def charger(tmp_path, snapshot):
    return chargerProjetJsonV1(ecrire_snapshot(tmp_path, snapshot))


def test_snapshot_minimal_valide_est_charge_par_le_loader(tmp_path, loader_sans_calcul_metier):
    moteur, _ = charger(tmp_path, snapshot_valide_minimal())

    assert moteur.segment_actif == "Segment A"
    assert moteur.scenario_actif == "Scenario A"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda snapshot: snapshot.__setitem__("segments", [{}]), "segment inconnu"),
        (lambda snapshot: snapshot.__setitem__("segments", [{"segment": "Segment A"}]), "scenarios"),
        (
            lambda snapshot: snapshot.__setitem__(
                "segments",
                [{"segment": "Inconnu", "scenarios": snapshot["segments"][0]["scenarios"]}],
            ),
            "segment inconnu",
        ),
        (
            lambda snapshot: snapshot.__setitem__(
                "segments", snapshot["segments"] * 2
            ),
                "dupliqu",
        ),
    ],
)
def test_loader_refuse_les_blocs_segments_incoherents(
    tmp_path, loader_sans_calcul_metier, mutation, message
):
    snapshot = snapshot_valide_minimal()
    mutation(snapshot)

    with pytest.raises(ValueError, match=message):
        charger(tmp_path, snapshot)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda snapshot: snapshot["segments"][0].__setitem__("scenarios", [None]),
                "invalide",
        ),
        (
            lambda snapshot: snapshot["segments"][0]["scenarios"][0].pop("name"),
                "nom de.*invalide",
        ),
        (
            lambda snapshot: snapshot["segments"][0]["scenarios"][0].__setitem__("type", "inconnu"),
                "type non support",
        ),
        (
            lambda snapshot: snapshot["segments"][0]["scenarios"][0].__setitem__("segment", "Autre"),
                "segment incoh",
        ),
        (
            lambda snapshot: snapshot["segments"][0]["scenarios"].append(
                copy.deepcopy(snapshot["segments"][0]["scenarios"][0])
            ),
                "dupliqu",
        ),
    ],
)
def test_loader_refuse_les_scenarios_incoherents(
    tmp_path, loader_sans_calcul_metier, mutation, message
):
    snapshot = snapshot_valide_minimal()
    mutation(snapshot)

    with pytest.raises(ValueError, match=message):
        charger(tmp_path, snapshot)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda snapshot: snapshot.pop("active_segment"), "tat actif invalide"),
        (lambda snapshot: snapshot.__setitem__("active_scenario", "Inconnu"), "tat actif invalide"),
    ],
)
def test_loader_refuse_un_etat_actif_invalide(
    tmp_path, loader_sans_calcul_metier, mutation, message
):
    snapshot = snapshot_valide_minimal()
    mutation(snapshot)

    with pytest.raises(ValueError, match=message):
        charger(tmp_path, snapshot)


def test_loader_refuse_un_scenario_actif_dun_autre_segment(tmp_path, loader_sans_calcul_metier):
    snapshot = snapshot_valide_minimal()
    autre_segment = "Segment B"
    autre_scenario = copy.deepcopy(snapshot["segments"][0]["scenarios"][0])
    autre_scenario.update({"name": "Scenario B", "segment": autre_segment})
    snapshot["dataset"]["events"].append(_evenement(autre_segment))
    snapshot["segments"].append({"segment": autre_segment, "scenarios": [autre_scenario]})
    snapshot["active_scenario"] = autre_scenario["name"]

    with pytest.raises(ValueError, match="tat actif invalide"):
        charger(tmp_path, snapshot)


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        (None, "parameters"),
        ({"inconnu": {}}, "module JSON"),
        ({"module": []}, "module.*invalides"),
        ({"module": {"inconnu": "x"}}, "attribut JSON"),
    ],
)
def test_loader_refuse_les_parametres_persistes_invalides(
    tmp_path, loader_sans_calcul_metier, parameters, message
):
    snapshot = snapshot_valide_minimal()
    snapshot["segments"][0]["scenarios"][0]["parameters"] = parameters

    with pytest.raises(ValueError, match=message):
        charger(tmp_path, snapshot)


@pytest.mark.parametrize("rules", [None, []])
def test_loader_refuse_des_regles_non_objet(tmp_path, loader_sans_calcul_metier, rules):
    snapshot = snapshot_valide_minimal()
    snapshot["rules"] = rules

    with pytest.raises(ValueError, match="'rules' doit"):
        charger(tmp_path, snapshot)


@pytest.mark.parametrize("preferences", [None, {"color": [0, 0, 0], "visible": True}])
def test_loader_refuse_des_preferences_layer_invalides(
    tmp_path, loader_sans_calcul_metier, preferences
):
    snapshot = snapshot_valide_minimal()
    snapshot["segments"][0]["scenarios"][0]["layer_preferences"] = preferences

    with pytest.raises(ValueError, match="layer_preferences|manquantes"):
        charger(tmp_path, snapshot)


def test_snapshot_legacy_sans_cached_results_reste_chargeable(tmp_path, loader_sans_calcul_metier):
    snapshot = snapshot_valide_minimal()
    del snapshot["segments"][0]["scenarios"][0]["cached_results"]

    moteur, _ = charger(tmp_path, snapshot)
    assert moteur.getScenario().nom == "Scenario A"
