"""Un événement sans bases reste sélectionnable et persistable, sans géométrie."""
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.AlgorithmeCadranFinal import AlgorithmeCadranFinal
from src.ProjectPersistence import chargerProjetJsonV1, sauvegarderProjetJsonV1
from src.layerManager import LayerManager


EVENEMENT = "28 Septembre 1066: Débarquement de Guillaume le Conquérant"
PROJET = Path("projets/CadranFinal_Solutions.json")


@pytest.fixture
def moteur():
    layers = LayerManager()
    return AlgorithmeCadranFinal(layers), layers


def selectionner(moteur, layers, segment):
    # Même sélection logique que le callback de la combo de l'interface.
    layers.segmentActif = segment
    moteur.setSegment(segment, layers)
    return moteur.getScenario()


def reconstruire(scenario, layers):
    layer = layers.getLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    scenario.construireRepresentationCarte(layer)
    return layer


def test_selection_sans_bases_ne_calcule_ni_ne_trace_la_geometrie(moteur, monkeypatch):
    m, layers = moteur
    assert EVENEMENT in m.getListeSegments()
    valide = m.segment_actif
    assert layers.getListeObjetsGraphiquesVisible(valide)
    scenario = selectionner(m, layers, EVENEMENT)
    assert m.dataset.base1 == m.dataset.base2 == ""
    for identifiant, module in scenario.modules.items():
        if identifiant == "segment":
            continue
        for methode in ("setup", "calculer", "construireRepresentationCarte"):
            monkeypatch.setattr(module, methode, Mock(side_effect=AssertionError(identifiant)))
    layer = layers.getLayer(scenario.getDescriptionLisible(), segment=EVENEMENT)
    layer.objets.append(object())  # Un ancien résultat ne doit pas survivre.
    m.calculerModules(setup=True)
    assert reconstruire(scenario, layers).objets == []
    assert layers.getListeObjetsGraphiquesVisible() == []
    assert scenario.modules["segment"].dateDataset == "28/09/1066"
    assert len(m.ordreModules) == 6  # L'ordre global n'est jamais tronqué.
    selectionner(m, layers, valide)
    assert layers.getListeObjetsGraphiquesVisible()


def test_reprise_du_meme_scenario_apres_retablissement_des_bases(moteur):
    m, layers = moteur
    scenario = m.getScenario()
    layer = reconstruire(scenario, layers)
    avant = [o.getGraphicalSignature() for o in layer.objets]
    bases = m.dataset.base1, m.dataset.base2
    m.dataset.base1 = m.dataset.base2 = ""
    m.calculerModules()
    assert reconstruire(scenario, layers).objets == []
    m.dataset.base1, m.dataset.base2 = bases
    m.calculerModules()
    assert scenario.ordreModules == m.ordreModules
    assert [o.getGraphicalSignature() for o in reconstruire(scenario, layers).objets] == avant


@pytest.mark.parametrize("bases", [("", "Rocamadour"), ("Ville absente", "Rocamadour")])
def test_autres_erreurs_de_base_ne_sont_pas_masquees(moteur, bases):
    m, _ = moteur
    m.dataset.base1, m.dataset.base2 = bases
    m.getScenario().modules["stylet"].choixBase = "Base 1"
    with pytest.raises(KeyError) as erreur:
        m.calculerModules()
    assert erreur.value.args == (bases[0],)


def test_erreur_hors_bases_reste_visible(moteur):
    m, _ = moteur
    m.getScenario().modules["stylet"].octave = "invalide"
    with pytest.raises(KeyError, match="invalide"):
        m.calculerModules()


def test_projet_reel_selection_sauvegarde_rechargement_et_retour(tmp_path):
    empreinte = sha256(PROJET.read_bytes()).hexdigest()
    m, layers = chargerProjetJsonV1(PROJET)
    valide = m.segment_actif
    # Tous les scénarios avec bases conservent le pipeline graphique complet.
    for segment, scenarios in m._scenarios.items():
        bases = [m.dataset.getValeurPourSegment(segment, cle) for cle in ("Base1", "Base2")]
        for scenario in scenarios.values():
            assert scenario.ordreModules == (m.ordreModules if any(bases) else ["segment"])
    scenario = selectionner(m, layers, EVENEMENT)
    assert reconstruire(scenario, layers).objets == []
    destination = tmp_path / "cadran_sans_bases.json"
    snapshot = sauvegarderProjetJsonV1(destination, m, layers)
    assert snapshot["active_segment"] == EVENEMENT
    recharge, layers_recharges = chargerProjetJsonV1(destination)
    assert recharge.segment_actif == EVENEMENT
    assert layers_recharges.getListeObjetsGraphiquesVisible() == []
    assert sauvegarderProjetJsonV1(tmp_path / "second.json", recharge, layers_recharges) == snapshot
    assert json.loads(destination.read_text(encoding="utf-8")) == snapshot
    scenario_valide = selectionner(recharge, layers_recharges, valide)
    recharge.calculerModules()
    assert reconstruire(scenario_valide, layers_recharges).objets
    assert layers_recharges.getListeObjetsGraphiquesVisible()
    assert sha256(PROJET.read_bytes()).hexdigest() == empreinte


def test_ihm_cadran_final_peut_afficher_evenement_sans_bases(moteur):
    import tkinter as tk
    from src.IHMAlgorithme import IHMAlgorithme
    m, layers = moteur
    selectionner(m, layers, EVENEMENT)
    root = tk.Tk()
    root.withdraw()
    try:
        ihm = IHMAlgorithme(root, "config/AlgorithmeCadranFinal.csv", m, layers)
        ihm.reconstruire_interface()
        root.update_idletasks()
        assert layers.getListeObjetsGraphiquesVisible() == []
    finally:
        root.destroy()
