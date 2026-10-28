"""Persistance JSON V1 des projets La Chouette.

Ce module contient le writer et le loader JSON V1, sans modifier le modèle
métier existant ni le workflow projet de l'application.
"""

from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from src.AlgorithmeBaseCadran import AlgorithmeBaseCadran
from src.AlgorithmeCadranFinal import AlgorithmeCadranFinal
from src.AlgorithmeLumiereStyletInitial import AlgorithmeLumiereStyletInitial
from src.AlgorithmeManager import AlgorithmeManager, Scenario, TypeScenario
from src.AlgorithmeSegment import AlgorithmeSegment
from src.AlgorithmeStyletInitial import AlgorithmeStyletInitial
from src.calculAstronomique import MyJulianDate
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.layerManager import LayerManager


FORMAT_PROJET = "chouette-or-project"
SCHEMA_VERSION = 1
_TYPES_PARAMETRES_PERSISTANTS = {"input", "input_multiple"}
_TYPES_CACHES_PERSISTANTS = {"cache"}
_ALGORITHMES_SUPPORTES = {
    "AlgorithmeSegment": AlgorithmeSegment,
    "AlgorithmeStyletInitial": AlgorithmeStyletInitial,
    "AlgorithmeLumiereStyletInitial": AlgorithmeLumiereStyletInitial,
    "AlgorithmeBaseCadran": AlgorithmeBaseCadran,
    "AlgorithmeCadranFinal": AlgorithmeCadranFinal,
}


def _lire_parametres_persistants_csv(
    csv_path: str | Path,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Retourne les couples persistants et les couples cache du CSV.

    Les commentaires et lignes vides suivent la convention des CSV IHM. Les
    doublons éventuels sont dédupliqués tout en conservant l'ordre du fichier.
    """
    with Path(csv_path).open("r", encoding="utf-8", newline="") as fichier:
        lignes = (ligne for ligne in fichier if ligne.strip() and not ligne.lstrip().startswith("#"))
        lecteur = csv.DictReader(lignes)
        champs = lecteur.fieldnames or []
        manquants = {"Type", "Module", "Attribut"} - set(champs)
        if manquants:
            raise ValueError(f"CSV de persistance incomplet ({csv_path}) : colonnes manquantes {sorted(manquants)}")

        parametres: list[tuple[str, str]] = []
        caches: list[tuple[str, str]] = []
        vus_parametres: set[tuple[str, str]] = set()
        vus_caches: set[tuple[str, str]] = set()
        for ligne in lecteur:
            type_champ = ligne.get("Type", "").strip().lower()
            if type_champ not in _TYPES_PARAMETRES_PERSISTANTS | _TYPES_CACHES_PERSISTANTS:
                continue

            module = ligne.get("Module", "").strip()
            attribut = ligne.get("Attribut", "").strip()
            if not module or not attribut:
                raise ValueError(f"CSV de persistance invalide ({csv_path}) : Module/Attribut vide pour {type_champ}")

            cle = (module, attribut)
            if type_champ in _TYPES_PARAMETRES_PERSISTANTS and cle not in vus_parametres:
                parametres.append(cle)
                vus_parametres.add(cle)
            elif type_champ in _TYPES_CACHES_PERSISTANTS and cle not in vus_caches:
                caches.append(cle)
                vus_caches.add(cle)

    return parametres, caches


def _valeur_json(valeur: Any, contexte: str) -> Any:
    """Convertit uniquement les conteneurs Python non natifs réellement utiles.

    Les paramètres actuellement fournis par les cinq CSV sont des primitives.
    Le support de tuple est conservé pour rester explicite si un choix IHM en
    fournit un un jour, sans introduire de sérialiseur générique d'objets.
    """
    if valeur is None or isinstance(valeur, (str, int, float, bool)):
        return valeur
    if isinstance(valeur, MyJulianDate):
        return {"__persist_type__": "MyJulianDate", "jd": float(valeur)}
    if isinstance(valeur, tuple):
        return [_valeur_json(element, contexte) for element in valeur]
    if isinstance(valeur, list):
        return [_valeur_json(element, contexte) for element in valeur]
    if isinstance(valeur, dict):
        if not all(isinstance(cle, str) for cle in valeur):
            raise TypeError(f"Valeur non JSON-native pour {contexte} : clé de dictionnaire non textuelle")
        return {cle: _valeur_json(element, contexte) for cle, element in valeur.items()}
    raise TypeError(
        f"Valeur non JSON-native pour {contexte} : {type(valeur).__name__}. "
        "Ajouter une conversion explicite si ce cas devient un paramètre IHM réel."
    )


def _valeur_cache_depuis_json(valeur: Any) -> Any:
    """Restaure les valeurs non natives explicitement supportées dans un cache."""
    if isinstance(valeur, list):
        return [_valeur_cache_depuis_json(element) for element in valeur]
    if isinstance(valeur, dict):
        if set(valeur) == {"__persist_type__", "jd"} and valeur["__persist_type__"] == "MyJulianDate":
            return MyJulianDate.fromJD(valeur["jd"])
        return {cle: _valeur_cache_depuis_json(element) for cle, element in valeur.items()}
    return valeur


def _snapshot_dataset(dataset: Any) -> dict[str, list[dict[str, Any]]]:
    """Sérialise la source logique du dataset, dans son ordre courant."""
    try:
        evenements = dataset.evenements
    except AttributeError as erreur:
        raise TypeError("Le dataset doit exposer 'evenements' pour PERSIST-V1") from erreur

    events = []
    for nom_evenement, valeurs in evenements.items():
        event = {"event": _valeur_json(nom_evenement, "dataset.event")}
        event.update({cle: _valeur_json(valeur, f"dataset.{nom_evenement}.{cle}") for cle, valeur in valeurs.items()})
        events.append(event)
    return {"events": events}


def _snapshot_parametres_scenario(scenario: Any, parametres_csv: list[tuple[str, str]]) -> dict[str, dict[str, Any]]:
    """Lit les choix directement dans les modules du scénario."""
    resultat: dict[str, dict[str, Any]] = {}
    for module_id, attribut in parametres_csv:
        # Le dataset est exporté une seule fois depuis ``dataset.evenements``.
        # Ses projections actives (dataset.base1, dataset.date, etc.) ne sont
        # pas des paramètres de scénario et ne doivent donc pas être dupliquées
        # ici, même si un CSV historique les marque comme input.
        if module_id == "dataset":
            continue
        module = scenario.modules.get(module_id)
        if module is None:
            raise ValueError(
                f"Scénario '{scenario.nom}' : module CSV '{module_id}' introuvable dans les modules du scénario"
            )
        if not hasattr(module, attribut):
            raise ValueError(
                f"Scénario '{scenario.nom}' : attribut CSV '{module_id}.{attribut}' introuvable"
            )
        resultat.setdefault(module_id, {})[attribut] = _valeur_json(
            getattr(module, attribut), f"{scenario.nom}.{module_id}.{attribut}"
        )
    return resultat


def _snapshot_layer(scenario: Any, layer_manager: Any) -> dict[str, Any]:
    layer = layer_manager.getLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    if layer is None:
        raise ValueError(
            f"Scénario '{scenario.nom}' : layer '{scenario.getDescriptionLisible()}' introuvable pour le segment "
            f"'{scenario.segment}'"
        )

    return {
        "color": _valeur_json(layer.getCouleur(), f"layer {scenario.nom}.color"),
        "thickness": _valeur_json(layer.getEpaisseur(), f"layer {scenario.nom}.thickness"),
        "visible": _valeur_json(layer.estVisible(), f"layer {scenario.nom}.visible"),
    }


def construireSnapshotProjetJsonV1(
    moteurAlgo: Any,
    layerManager: Any,
    csv_path: str | Path | None = None,
) -> dict[str, Any]:
    """Construit le snapshot PERSIST-V1, sans l'écrire sur disque."""
    if csv_path is None:
        csv_path = Path("config") / f"{type(moteurAlgo).__name__}.csv"
    parametres_csv, caches_csv = _lire_parametres_persistants_csv(csv_path)

    segments = []
    for segment, scenarios_segment in moteurAlgo._scenarios.items():
        scenarios = []
        for scenario in scenarios_segment.values():
            type_scenario = scenario.getTypeScenario()
            if type_scenario == TypeScenario.AUTOMATIQUE:
                continue
            if type_scenario not in (TypeScenario.DEFAULT, TypeScenario.UTILISATEUR):
                raise ValueError(f"Type de scénario non supporté : {type_scenario!r}")

            scenarios.append(
                {
                    "name": _valeur_json(scenario.nom, "scenario.name"),
                    "type": type_scenario.value,
                    "segment": _valeur_json(scenario.segment, "scenario.segment"),
                    "solution": _valeur_json(scenario.getSolution(), "scenario.solution"),
                    "parameters": _snapshot_parametres_scenario(scenario, parametres_csv),
                    "cached_results": _snapshot_parametres_scenario(scenario, caches_csv),
                    "layer_preferences": _snapshot_layer(scenario, layerManager),
                }
            )

        # Un segment qui ne porte que des scénarios automatiques n'a aucun état
        # persistant à écrire.
        if scenarios:
            segments.append({"segment": _valeur_json(segment, "segment"), "scenarios": scenarios})

    return {
        "format": FORMAT_PROJET,
        "schema_version": SCHEMA_VERSION,
        "algorithm": type(moteurAlgo).__name__,
        "dataset": _snapshot_dataset(moteurAlgo.dataset),
        "rules": _valeur_json(moteurAlgo.regles_actives, "rules"),
        "active_segment": _valeur_json(moteurAlgo.segment_actif, "active_segment"),
        "active_scenario": _valeur_json(moteurAlgo.scenario_actif, "active_scenario"),
        "segments": segments,
    }


def sauvegarderProjetJsonV1(
    chemin: str | Path,
    moteurAlgo: Any,
    layerManager: Any,
    csv_path: str | Path | None = None,
) -> dict[str, Any]:
    """Écrit un projet JSON V1 et retourne le snapshot écrit."""
    snapshot = construireSnapshotProjetJsonV1(moteurAlgo, layerManager, csv_path)
    with Path(chemin).open("w", encoding="utf-8", newline="\n") as fichier:
        json.dump(snapshot, fichier, ensure_ascii=False, indent=2)
        fichier.write("\n")
    return snapshot


def _construire_dataset_depuis_snapshot(dataset_json: Any) -> ListeSegmentsDataSet:
    """Reconstruit le dataset V1 sans relire le CSV mÃ©tier."""
    if not isinstance(dataset_json, dict) or not isinstance(dataset_json.get("events"), list):
        raise ValueError("Projet JSON V1 invalide : 'dataset.events' doit Ãªtre une liste.")
    if not dataset_json["events"]:
        raise ValueError("Projet JSON V1 invalide : 'dataset.events' ne peut pas Ãªtre vide.")

    evenements = OrderedDict()
    for evenement in dataset_json["events"]:
        if not isinstance(evenement, dict) or "event" not in evenement:
            raise ValueError("Projet JSON V1 invalide : chaque Ã©vÃ©nement doit contenir 'event'.")
        nom = evenement["event"]
        if not isinstance(nom, str) or not nom:
            raise ValueError("Projet JSON V1 invalide : le nom d'un Ã©vÃ©nement doit Ãªtre une chaÃ®ne non vide.")
        if nom in evenements:
            raise ValueError(f"Projet JSON V1 invalide : Ã©vÃ©nement dupliquÃ© '{nom}'.")
        evenements[nom] = {cle: valeur for cle, valeur in evenement.items() if cle != "event"}

    # Les attributs runtime sont volontairement laissÃ©s Ã  leur Ã©tat initial :
    # ListeSegmentsDataSet.calculer() les alimente Ã  partir de l'Ã©vÃ©nement actif.
    dataset = ListeSegmentsDataSet.__new__(ListeSegmentsDataSet)
    dataset.evenements = evenements
    dataset.segment = next(iter(evenements))
    dataset.lettreSegment = None
    dataset.date = None
    dataset.dateSegment = None
    dataset.lettreDecl = None
    dataset.stylet = None
    dataset.base1 = None
    dataset.base2 = None
    dataset.extremite1 = None
    dataset.milieuSegment = None
    dataset.extremite2 = None
    return dataset


def _vider_layers(layer_manager: LayerManager) -> None:
    """Retire les layers provisoires crÃ©Ã©s durant l'initialisation du moteur."""
    for segment in list(layer_manager.getListeSegments()):
        for nom_layer in list(layer_manager.getNomsLayers(segment)):
            layer_manager.supprimerLayer(nom_layer, segment=segment)


def _restaurer_parametres_scenario(scenario: Scenario, parametres: Any) -> None:
    if not isinstance(parametres, dict):
        raise ValueError(f"ScÃ©nario '{scenario.nom}' : 'parameters' doit Ãªtre un objet.")

    for module_id, attributs in parametres.items():
        module = scenario.modules.get(module_id)
        if module is None:
            raise ValueError(f"ScÃ©nario '{scenario.nom}' : module JSON '{module_id}' introuvable.")
        if not isinstance(attributs, dict):
            raise ValueError(f"ScÃ©nario '{scenario.nom}' : paramÃ¨tres du module '{module_id}' invalides.")
        for attribut, valeur in attributs.items():
            if not hasattr(module, attribut):
                raise ValueError(
                    f"ScÃ©nario '{scenario.nom}' : attribut JSON '{module_id}.{attribut}' introuvable."
                )
            setattr(module, attribut, valeur)


def _restaurer_caches_scenario(
    scenario: Scenario,
    caches_csv: list[tuple[str, str]],
    caches: Any,
) -> None:
    if not isinstance(caches, dict):
        raise ValueError(f"Scénario '{scenario.nom}' : 'cached_results' doit être un objet.")

    caches_autorises = set(caches_csv)
    for module_id, attributs in caches.items():
        module = scenario.modules.get(module_id)
        if module is None:
            raise ValueError(f"Scénario '{scenario.nom}' : module cache JSON '{module_id}' introuvable.")
        if not isinstance(attributs, dict):
            raise ValueError(f"Scénario '{scenario.nom}' : caches du module '{module_id}' invalides.")
        for attribut in attributs:
            if not hasattr(module, attribut):
                raise ValueError(
                    f"Scénario '{scenario.nom}' : attribut cache JSON '{module_id}.{attribut}' introuvable."
                )
            if (module_id, attribut) not in caches_autorises:
                raise ValueError(
                    f"Scénario '{scenario.nom}' : cache JSON '{module_id}.{attribut}' non déclaré Type=cache."
                )

    caches_restaures = {
        module_id: {
            attribut: _valeur_cache_depuis_json(valeur)
            for attribut, valeur in attributs.items()
        }
        for module_id, attributs in caches.items()
    }
    _restaurer_parametres_scenario(scenario, caches_restaures)


def _restaurer_preferences_layer(scenario: Scenario, layer_manager: LayerManager, preferences: Any) -> None:
    if not isinstance(preferences, dict):
        raise ValueError(f"ScÃ©nario '{scenario.nom}' : 'layer_preferences' doit Ãªtre un objet.")
    manquantes = {"color", "thickness", "visible"} - set(preferences)
    if manquantes:
        raise ValueError(f"ScÃ©nario '{scenario.nom}' : prÃ©fÃ©rences layer manquantes {sorted(manquantes)}.")

    layer = layer_manager.getLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    if layer is None:
        raise ValueError(f"ScÃ©nario '{scenario.nom}' : layer reconstruit introuvable.")
    couleur = preferences["color"]
    layer.setCouleur(tuple(couleur) if isinstance(couleur, list) else couleur)
    layer.setEpaisseur(preferences["thickness"])
    layer.setVisible(preferences["visible"])


def _valider_entete_snapshot(snapshot: Any) -> type[AlgorithmeManager]:
    if not isinstance(snapshot, dict):
        raise ValueError("Projet JSON V1 invalide : la racine doit Ãªtre un objet.")
    if snapshot.get("format") != FORMAT_PROJET:
        raise ValueError(f"Format de projet JSON inconnu : {snapshot.get('format')!r}.")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Version de schÃ©ma JSON non supportÃ©e : {snapshot.get('schema_version')!r}.")
    nom_algorithme = snapshot.get("algorithm")
    try:
        return _ALGORITHMES_SUPPORTES[nom_algorithme]
    except KeyError as erreur:
        raise ValueError(f"Algorithme JSON non supportÃ© : {nom_algorithme!r}.") from erreur


def lireMetaDonneesProjetJsonV1(chemin: str | Path) -> dict[str, Any]:
    """Lit et valide l'en-tête d'un projet V1 sans le reconstruire."""
    with Path(chemin).open("r", encoding="utf-8") as fichier:
        snapshot = json.load(fichier)

    _valider_entete_snapshot(snapshot)
    return {
        "format": snapshot["format"],
        "schema_version": snapshot["schema_version"],
        "algorithm": snapshot["algorithm"],
    }


def chargerProjetJsonV1(
    chemin: str | Path,
    layerManager: LayerManager | None = None,
) -> tuple[AlgorithmeManager, LayerManager]:
    """Charge un projet PERSIST-V1 et retourne ``(moteurAlgo, layerManager)``.

    Le moteur est construit avec le snapshot du dataset, jamais avec le CSV
    courant. Les scÃ©narios JSON sont les seuls scÃ©narios persistants recrÃ©Ã©s.
    """
    with Path(chemin).open("r", encoding="utf-8") as fichier:
        snapshot = json.load(fichier)

    classe_algorithme = _valider_entete_snapshot(snapshot)
    _, caches_csv = _lire_parametres_persistants_csv(
        Path("config") / f"{classe_algorithme.__name__}.csv"
    )
    dataset = _construire_dataset_depuis_snapshot(snapshot.get("dataset"))
    if not isinstance(snapshot.get("segments"), list):
        raise ValueError("Projet JSON V1 invalide : 'segments' doit Ãªtre une liste.")
    if not isinstance(snapshot.get("rules"), dict):
        raise ValueError("Projet JSON V1 invalide : 'rules' doit Ãªtre un objet.")

    layer_manager = layerManager or LayerManager()

    # Les cinq constructeurs actuels ne font que fournir le dataset CSV puis
    # appeler AlgorithmeManager.__init__. On appelle donc explicitement cette
    # initialisation commune aprÃ¨s avoir installÃ© le dataset du snapshot.
    moteur = classe_algorithme.__new__(classe_algorithme)
    moteur.dataset = dataset
    AlgorithmeManager.__init__(moteur, layer_manager)
    moteur._scenarios.clear()
    _vider_layers(layer_manager)
    # Le premier passage ne sert qu'Ã  laisser setup() Ã©tablir les valeurs par
    # dÃ©faut. Les rÃ¨gles du projet sont appliquÃ©es uniquement au recalcul final,
    # aprÃ¨s restauration des choix persistants.
    moteur.regles_actives = {}

    enregistrements: list[tuple[Scenario, dict[str, Any]]] = []
    segments_vus: set[str] = set()
    for bloc_segment in snapshot["segments"]:
        if not isinstance(bloc_segment, dict):
            raise ValueError("Projet JSON V1 invalide : chaque bloc de segment doit Ãªtre un objet.")
        segment = bloc_segment.get("segment")
        scenarios_json = bloc_segment.get("scenarios")
        if not isinstance(segment, str) or segment not in dataset.evenements:
            raise ValueError(f"Projet JSON V1 invalide : segment inconnu '{segment}'.")
        if segment in segments_vus:
            raise ValueError(f"Projet JSON V1 invalide : bloc de segment dupliquÃ© '{segment}'.")
        if not isinstance(scenarios_json, list):
            raise ValueError(f"Projet JSON V1 invalide : scenarios du segment '{segment}' invalides.")
        segments_vus.add(segment)
        moteur._scenarios[segment] = {}
        moteur.dataset.segment = segment
        moteur.dataset.calculer()

        for scenario_json in scenarios_json:
            if not isinstance(scenario_json, dict):
                raise ValueError(f"Projet JSON V1 invalide : scÃ©nario invalide dans '{segment}'.")
            nom = scenario_json.get("name")
            type_json = scenario_json.get("type")
            if not isinstance(nom, str) or not nom:
                raise ValueError(f"Projet JSON V1 invalide : nom de scÃ©nario invalide dans '{segment}'.")
            if type_json not in (TypeScenario.DEFAULT.value, TypeScenario.UTILISATEUR.value):
                raise ValueError(f"ScÃ©nario '{nom}' : type non supportÃ© '{type_json}'.")
            if scenario_json.get("segment") != segment:
                raise ValueError(f"ScÃ©nario '{nom}' : segment incohÃ©rent.")
            if nom in moteur._scenarios[segment]:
                raise ValueError(f"ScÃ©nario '{nom}' dupliquÃ© dans le segment '{segment}'.")

            scenario = Scenario(
                nom=nom,
                quadruplets=[],
                modules=moteur.genererModulesDepuisTemplates(),
                ordreModules=moteur.ordreModules,
                segment=segment,
                layerManager=layer_manager,
                type_scenario=TypeScenario(type_json),
            )
            moteur._scenarios[segment][nom] = scenario

            # setup() installe les valeurs par dÃ©faut nÃ©cessaires ; les choix
            # persistants sont restaurÃ©s ensuite et ne sont pas rÃ©initialisÃ©s.
            moteur.calculerModules(nom_scenario=nom, segment=segment, setup=True)
            _restaurer_parametres_scenario(scenario, scenario_json.get("parameters"))
            scenario.setSolution(scenario_json.get("solution"))
            enregistrements.append((scenario, scenario_json))

    moteur.regles_actives = snapshot["rules"]

    # DeuxiÃ¨me passe : calcul normal avec les paramÃ¨tres et rÃ¨gles restaurÃ©s,
    # puis reconstruction graphique et application des prÃ©fÃ©rences du layer.
    for scenario, scenario_json in enregistrements:
        moteur.dataset.segment = scenario.segment
        moteur.dataset.calculer()
        moteur.calculerModules(nom_scenario=scenario.nom, segment=scenario.segment)
        _restaurer_caches_scenario(scenario, caches_csv, scenario_json.get("cached_results", {}))
        layer = layer_manager.getLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
        scenario.construireRepresentationCarte(layer)
        _restaurer_preferences_layer(scenario, layer_manager, scenario_json.get("layer_preferences"))

    segment_actif = snapshot.get("active_segment")
    scenario_actif = snapshot.get("active_scenario")
    if segment_actif not in dataset.evenements:
        raise ValueError(f"Ã‰tat actif invalide : segment '{segment_actif}' introuvable dans le dataset.")
    if segment_actif not in moteur._scenarios or scenario_actif not in moteur._scenarios[segment_actif]:
        raise ValueError(
            f"Ã‰tat actif invalide : scÃ©nario '{scenario_actif}' introuvable pour le segment '{segment_actif}'."
        )

    moteur.segment_actif = segment_actif
    moteur.scenario_actif = scenario_actif
    moteur.dataset.segment = segment_actif
    moteur.dataset.calculer()
    layer_manager.segmentActif = segment_actif
    layer_manager.recalculerCoordonneesPixelAbsTous()
    return moteur, layer_manager
