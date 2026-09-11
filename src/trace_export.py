"""Export explicite des objets graphiques natifs vers le format Traces."""

import json
import re
from pathlib import Path

from src.AlgorithmeManager import TypeScenario
from src.affichage_objets import (
    ArcOriente,
    Cercle,
    CercleGraphique,
    Ligne,
    LigneAzimut,
    LigneEntreVilles,
    LigneGraphique,
    LigneHorizontale,
    LigneVerticale,
    PointGraphique,
    SegmentEntreVilles,
    SymboleWiki,
)


class TraceExportError(ValueError):
    """Erreur de contrat rencontrée pendant la construction d'un document Traces."""


def convertir_geometrie(objet):
    """Convertit explicitement la géométrie native d'un objet graphique."""
    if isinstance(objet, ArcOriente):
        return {
            "type": "arc",
            "center_x_l93": objet.pointCentre.x_l93,
            "center_y_l93": objet.pointCentre.y_l93,
            "radius_km": objet.rayon_km,
            "start_azimuth_deg": objet.azimut_depart,
            "rotation_deg": objet.rotation,
        }
    if isinstance(objet, SymboleWiki):
        return {
            "type": "symbol",
            "x_l93": objet.x_l93,
            "y_l93": objet.y_l93,
            "source": objet.url,
        }
    if isinstance(objet, CercleGraphique):
        return {
            "type": "circle",
            "center_x_l93": objet.pointCentre.x_l93,
            "center_y_l93": objet.pointCentre.y_l93,
            "radius_km": objet.rayon_km,
        }
    if isinstance(objet, LigneEntreVilles):
        return {
            "type": "line_between_points",
            "x1_l93": objet.x1_l93,
            "y1_l93": objet.y1_l93,
            "x2_l93": objet.x2_l93,
            "y2_l93": objet.y2_l93,
        }
    if isinstance(objet, LigneAzimut):
        return {
            "type": "line_image_azimuth",
            "x_l93": objet.x_l93,
            "y_l93": objet.y_l93,
            "azimuth_deg": objet.azimut_deg,
        }
    if isinstance(objet, LigneVerticale):
        return {"type": "vertical_image_line", "x_l93": objet.x_l93, "y_l93": objet.y_l93}
    if isinstance(objet, LigneHorizontale):
        return {"type": "horizontal_image_line", "x_l93": objet.x_l93, "y_l93": objet.y_l93}
    if isinstance(objet, SegmentEntreVilles):
        return {
            "type": "segment",
            "x1_l93": objet.x1_l93,
            "y1_l93": objet.y1_l93,
            "x2_l93": objet.x2_l93,
            "y2_l93": objet.y2_l93,
        }
    if isinstance(objet, PointGraphique):
        return {"type": "point", "x_l93": objet.x_l93, "y_l93": objet.y_l93}
    if isinstance(objet, (LigneGraphique, Ligne, Cercle)):
        raise TraceExportError(f"Objet technique non exportable : {type(objet).__name__}")
    raise TraceExportError(f"Type d'objet graphique non supporté : {type(objet).__name__}")


def informations_graphiques(objet) -> dict:
    """Retourne les propriétés de présentation effectives, sans données runtime."""
    return {
        "name": objet.nom,
        "color_bgr": list(objet.getCouleur()),
        "width": objet.getEpaisseur(),
        "style": objet.getStyle(),
        "show_name": objet.afficherNom,
        "visible": objet._etatVisible,
        "tags": dict(objet.tags),
        "tooltips": list(objet.tooltips),
        "scenario_tooltips": list(objet.tooltips_scenario),
    }


def convertir_objet_graphique(objet):
    """Convertit un objet exportable en géométrie native et informations graphiques."""
    return {"geometry": convertir_geometrie(objet), "graphics": informations_graphiques(objet)}


def cle_geometrie(trace: dict) -> tuple:
    """Clé canonique exacte de la seule géométrie native."""
    geometrie = trace["geometry"]
    return tuple((cle, geometrie[cle]) for cle in sorted(geometrie))


def dedupliquer_et_trier(traces: list[dict]) -> list[dict]:
    traces_par_cle = {}
    for trace in traces:
        traces_par_cle.setdefault(cle_geometrie(trace), trace)
    return [traces_par_cle[cle] for cle in sorted(traces_par_cle)]


def scenarios_du_scope(moteur_algo, scope_type: str, scenario_lisible: str | None = None):
    """Résout le scope sans déclencher de calcul ni reconstruire de représentation."""
    segment = moteur_algo.segment_actif
    if scope_type == "scenario":
        if scenario_lisible is None:
            raise TraceExportError("Un scénario DEFAULT ou UTILISATEUR doit être sélectionné.")
        scenario = moteur_algo.getScenarioNomLisible(scenario_lisible, segment)
        if scenario.getTypeScenario() not in (TypeScenario.DEFAULT, TypeScenario.UTILISATEUR):
            raise TraceExportError("Un scénario AUTOMATIQUE doit être exporté via son agrégation.")
        return [scenario]
    if scope_type == "automatic_aggregation":
        return sorted(
            moteur_algo.getScenariosDict(segment, TypeScenario.AUTOMATIQUE).values(),
            key=lambda scenario: scenario.getDescriptionLisible(),
        )
    raise TraceExportError(f"Scope Traces inconnu : {scope_type}")


def collecter_objets_module(layer_manager, scenarios, module_id: str):
    """Collecte les objets bruts des layers associés aux scénarios fournis."""
    objets = []
    for scenario in scenarios:
        nom_layer = scenario.getDescriptionLisible()
        layer = layer_manager.getLayer(nom_layer, segment=scenario.segment)
        if layer is None:
            raise TraceExportError(
                f"Layer introuvable pour le scénario '{nom_layer}' du segment '{scenario.segment}'."
            )
        objets.extend(
            (scenario, objet)
            for objet in layer.getListeObjetsGraphiques()
            if objet.tags.get("module") == module_id
        )
    return objets


def construire_document_traces(
    moteur_algo,
    layer_manager,
    modules: list[tuple[str, str]],
    scope_type: str,
    scenario_lisible: str | None = None,
) -> dict:
    """Construit le document d'échange Traces à partir des objets déjà présents dans les layers."""
    if not modules:
        raise TraceExportError("Sélectionnez au moins un objet à exporter.")
    scenarios = scenarios_du_scope(moteur_algo, scope_type, scenario_lisible)
    modules_exportes = []
    for module_id, module_label in modules:
        traces = []
        for scenario, objet in collecter_objets_module(layer_manager, scenarios, module_id):
            try:
                traces.append(convertir_objet_graphique(objet))
            except TraceExportError as erreur:
                raise TraceExportError(
                    f"{erreur} (module '{module_id}', scénario '{scenario.getDescriptionLisible()}')."
                ) from erreur
        modules_exportes.append({
            "id": module_id,
            "label": module_label,
            "traces": dedupliquer_et_trier(traces),
        })

    scope = {"type": scope_type}
    if scope_type == "scenario":
        scope["scenario"] = scenario_lisible
    return {
        "schema_version": 2,
        "source": "AlgoSimulator",
        "algorithm": type(moteur_algo).__name__,
        "segment": moteur_algo.segment_actif,
        "scope": scope,
        "modules": modules_exportes,
    }


def ecrire_document_traces(document: dict, chemin) -> None:
    """Écrit un document Traces avec un JSON stable et lisible."""
    with Path(chemin).open("w", encoding="utf-8", newline="\n") as fichier:
        json.dump(document, fichier, ensure_ascii=False, indent=2)
        fichier.write("\n")


def nom_fichier_traces_par_defaut(moteur_algo, modules: list[tuple[str, str]]) -> str:
    nom_algorithme = type(moteur_algo).__name__.removeprefix("Algorithme") or type(moteur_algo).__name__
    segment = re.sub(r'[<>:"/\\|?*]', "-", str(moteur_algo.segment_actif))
    suffixe = modules[0][0] if len(modules) == 1 else "traces"
    return f"{nom_algorithme}_{segment}_{suffixe}.traces.json"
