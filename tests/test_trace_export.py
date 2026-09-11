import json
from types import SimpleNamespace

import pytest

import src.affichage_objets as geometrie
from src.AlgorithmeManager import TypeScenario
from src.affichage_objets import (
    ArcOriente,
    CercleGraphique,
    LigneAzimut,
    LigneEntreVilles,
    LigneGraphique,
    LigneHorizontale,
    LigneVerticale,
    PointGraphique,
    SegmentEntreVilles,
    SymboleWiki,
)
from src.layerManager import LayerManager
from src.trace_export import (
    TraceExportError,
    construire_document_traces,
    convertir_objet_graphique,
    ecrire_document_traces,
    nom_fichier_traces_par_defaut,
)


class CarteFictive:
    image_size = (500, 500)

    def lambert93_to_pixels(self, x, y):
        return x, y

    def pixels_to_lambert93(self, x, y):
        return x, y

    def lambert93_to_gps(self, x, y):
        return x / 1000, y / 1000


class ScenarioFictif:
    def __init__(self, nom, segment, type_scenario):
        self.nom = nom
        self.segment = segment
        self._type_scenario = type_scenario

    def getDescriptionLisible(self):
        return self.nom

    def getTypeScenario(self):
        return self._type_scenario


class MoteurFictif:
    segment_actif = "30/05/1431"

    def __init__(self, scenarios):
        self._scenarios = {scenario.nom: scenario for scenario in scenarios}

    def getScenarioNomLisible(self, label, segment):
        return self._scenarios[label]

    def getScenariosDict(self, segment, type_scenario=None):
        if type_scenario is None:
            return self._scenarios
        return {
            nom: scenario for nom, scenario in self._scenarios.items()
            if scenario.getTypeScenario() is type_scenario
        }


@pytest.fixture
def carte(monkeypatch):
    monkeypatch.setattr(geometrie, "carteConfig", CarteFictive())


def etiqueter(objet, module="ombre", level="construction"):
    objet.ajouterTag("module", module)
    objet.ajouterTag("level", level)
    return objet


def creer_contexte(type_scenario=TypeScenario.DEFAULT, nom="Beauvoir"):
    scenario = ScenarioFictif(nom, MoteurFictif.segment_actif, type_scenario)
    moteur = MoteurFictif([scenario])
    layers = LayerManager()
    layer = layers.creerLayer(nom, segment=scenario.segment)
    return moteur, layers, scenario, layer


def test_conversion_explicite_de_tous_les_types_natifs_sans_pixels(monkeypatch, carte):
    monkeypatch.setattr(SymboleWiki, "_iconeCache", {})
    monkeypatch.setattr(geometrie.cv2, "imread", lambda chemin, mode: SimpleNamespace(shape=(1, 1, 4)))
    point_a = PointGraphique("A", 10, 20)
    point_b = PointGraphique("B", 30, 40)
    objets = [
        point_a,
        SymboleWiki("source-wiki", 11, 21, "icone-bridge.png", nom="symbole"),
        CercleGraphique(point_a, 0.01),
        ArcOriente(point_a, 0.02, 45, -90),
        LigneEntreVilles(point_a, point_b),
        LigneAzimut(point_a, 75),
        LigneVerticale(point_a),
        LigneHorizontale(point_a),
        SegmentEntreVilles(point_a, point_b),
    ]

    traces = [convertir_objet_graphique(objet) for objet in objets]

    assert [trace["geometry"]["type"] for trace in traces] == [
        "point", "symbol", "circle", "arc", "line_between_points", "line_image_azimuth",
        "vertical_image_line", "horizontal_image_line", "segment",
    ]
    assert traces[1]["geometry"] == {"type": "symbol", "x_l93": 11, "y_l93": 21, "source": "source-wiki"}
    assert traces[3]["geometry"]["type"] == "arc"
    assert not any(
        cle in trace["geometry"] or cle in trace["graphics"]
        for trace in traces
        for cle in ("pointReference", "vecteur", "lignePixelImage", "cercle", "icone_path")
    )


def test_export_scenario_filtre_module_et_ignore_filtres_visuels(carte):
    moteur, layers, scenario, layer = creer_contexte()
    layer.setVisible(False)
    layers.setFiltreTag("module", "stylet")
    layer.inclureObjetDansLayer(
        etiqueter(PointGraphique("export", 10, 20), "ombre", "design"),
        etiqueter(PointGraphique("exclu", 30, 40), "stylet", "construction"),
    )

    document = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)

    assert document["scope"] == {"type": "scenario", "scenario": "Beauvoir"}
    assert [trace["geometry"] for trace in document["modules"][0]["traces"]] == [
        {"type": "point", "x_l93": 10, "y_l93": 20}
    ]


def test_aggregation_automatique_deduplique_apres_conversion_et_trie(carte):
    auto_1 = ScenarioFictif("Auto B", MoteurFictif.segment_actif, TypeScenario.AUTOMATIQUE)
    auto_2 = ScenarioFictif("Auto A", MoteurFictif.segment_actif, TypeScenario.AUTOMATIQUE)
    moteur = MoteurFictif([auto_1, auto_2])
    layers = LayerManager()
    layer_1 = layers.creerLayer(auto_1.nom, segment=auto_1.segment)
    layer_2 = layers.creerLayer(auto_2.nom, segment=auto_2.segment)
    layer_1.inclureObjetDansLayer(etiqueter(PointGraphique("doublon 1", 10, 20)))
    layer_2.inclureObjetDansLayer(
        etiqueter(PointGraphique("doublon 2", 10, 20)),
        etiqueter(LigneVerticale(PointGraphique("ancre", 10, 20))),
    )

    document_1 = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "automatic_aggregation")
    document_2 = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "automatic_aggregation")

    assert document_1 == document_2
    assert document_1["scope"] == {"type": "automatic_aggregation"}
    assert [trace["geometry"] for trace in document_1["modules"][0]["traces"]] == [
        {"type": "point", "x_l93": 10, "y_l93": 20},
        {"type": "vertical_image_line", "x_l93": 10, "y_l93": 20},
    ]


def test_export_ecrit_un_json_stable_et_un_nom_windows_compatible(tmp_path, carte):
    moteur, layers, scenario, layer = creer_contexte()
    layer.inclureObjetDansLayer(etiqueter(PointGraphique("P", 10, 20)))
    document = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)
    chemin = tmp_path / nom_fichier_traces_par_defaut(moteur, [("ombre", "Ombre")])

    ecrire_document_traces(document, chemin)

    assert json.loads(chemin.read_text(encoding="utf-8")) == document
    assert chemin.name == "MoteurFictif_30-05-1431_ombre.traces.json"
    assert document["schema_version"] == 2
    assert document["modules"][0]["id"] == "ombre"


def test_export_refuse_une_ligne_graphique_brute_avec_son_contexte(carte):
    moteur, layers, scenario, layer = creer_contexte()
    layer.inclureObjetDansLayer(etiqueter(LigneGraphique((10, 20), (1, 0))))

    with pytest.raises(TraceExportError, match="LigneGraphique.*module 'ombre'.*Beauvoir"):
        construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)


def test_export_refuse_un_scenario_automatique_isole(carte):
    moteur, layers, scenario, layer = creer_contexte(TypeScenario.AUTOMATIQUE, "Auto")

    with pytest.raises(TraceExportError, match="AUTOMATIQUE"):
        construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)


def test_trace_transporte_les_informations_graphiques_effectives_sans_runtime(carte):
    moteur, layers, scenario, layer = creer_contexte()
    layer.setCouleur((1, 2, 3))
    layer.setEpaisseur(4)
    layer.setStyle("dash")
    objet = etiqueter(LigneAzimut(PointGraphique("Ancre", 10, 20), 75, nom="ligne"), level="design")
    objet.setVisible(False)
    objet.setTooltips(["outil"])
    objet.tooltips_scenario = ["scénario"]
    layer.inclureObjetDansLayer(objet)

    document = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)

    graphics = document["modules"][0]["traces"][0]["graphics"]
    assert graphics == {
        "name": "ligne",
        "color_bgr": [1, 2, 3],
        "width": 4,
        "style": "dash",
        "show_name": None,
        "visible": False,
        "tags": {"module": "ombre", "level": "design"},
        "tooltips": ["outil"],
        "scenario_tooltips": ["scénario"],
    }
    assert not {"pointReference", "vecteur", "lignePixelImage", "cercle", "layer", "etatSelection"} & set(graphics)


def test_deduplication_conserve_les_metadonnees_de_la_premiere_occurrence(carte):
    moteur, layers, scenario, layer = creer_contexte()
    premier = etiqueter(PointGraphique("premier", 10, 20, couleur=(0, 0, 255), epaisseur=1))
    premier.setTooltips(["A"])
    second = etiqueter(PointGraphique("second", 10, 20, couleur=(255, 0, 0), epaisseur=5))
    second.setTooltips(["B"])
    layer.inclureObjetDansLayer(premier, second)

    document = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)

    assert document["modules"][0]["traces"] == [{
        "geometry": {"type": "point", "x_l93": 10, "y_l93": 20},
        "graphics": {
            "name": "premier", "color_bgr": [0, 0, 255], "width": 1, "style": "plein",
            "show_name": False, "visible": True, "tags": {"module": "ombre", "level": "construction"},
            "tooltips": ["A"], "scenario_tooltips": [],
        },
    }]


def test_export_multi_modules_ne_fusionne_pas_les_geometries_entre_modules(carte):
    moteur, layers, scenario, layer = creer_contexte()
    layer.inclureObjetDansLayer(
        etiqueter(PointGraphique("lumière", 10, 20), module="lumiere"),
        etiqueter(PointGraphique("ombre", 10, 20), module="ombre"),
        etiqueter(PointGraphique("ombre doublon", 10, 20), module="ombre"),
    )

    document = construire_document_traces(
        moteur, layers, [("lumiere", "Lumière"), ("ombre", "Ombre")], "scenario", scenario.nom,
    )

    assert [module["id"] for module in document["modules"]] == ["lumiere", "ombre"]
    assert [len(module["traces"]) for module in document["modules"]] == [1, 1]
    assert document["modules"][0]["traces"][0]["geometry"] == document["modules"][1]["traces"][0]["geometry"]


def test_nom_fichier_multi_modules_est_stable(carte):
    moteur, _, _, _ = creer_contexte()

    assert nom_fichier_traces_par_defaut(moteur, [("lumiere", "Lumière"), ("ombre", "Ombre")]) == (
        "MoteurFictif_30-05-1431_traces.traces.json"
    )


def test_geometries_differentes_restent_des_traces_distinctes(carte):
    moteur, layers, scenario, layer = creer_contexte()
    premier = etiqueter(PointGraphique("premier", 10, 20, couleur=(0, 0, 255)))
    second = etiqueter(PointGraphique("second", 11, 20, couleur=(0, 0, 255)))
    layer.inclureObjetDansLayer(premier, second)

    document = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "scenario", scenario.nom)

    assert [trace["geometry"]["x_l93"] for trace in document["modules"][0]["traces"]] == [10, 11]


def test_aggregation_auto_garde_les_metadonnees_de_la_premiere_occurrence(carte):
    auto_b = ScenarioFictif("Auto B", MoteurFictif.segment_actif, TypeScenario.AUTOMATIQUE)
    auto_a = ScenarioFictif("Auto A", MoteurFictif.segment_actif, TypeScenario.AUTOMATIQUE)
    moteur = MoteurFictif([auto_b, auto_a])
    layers = LayerManager()
    layer_b = layers.creerLayer(auto_b.nom, segment=auto_b.segment)
    layer_a = layers.creerLayer(auto_a.nom, segment=auto_a.segment)
    objet_b = etiqueter(PointGraphique("B", 10, 20, couleur=(255, 0, 0)))
    objet_b.setTooltips(["B"])
    objet_a = etiqueter(PointGraphique("A", 10, 20, couleur=(0, 0, 255)))
    objet_a.setTooltips(["A"])
    layer_b.inclureObjetDansLayer(objet_b)
    layer_a.inclureObjetDansLayer(objet_a)

    document = construire_document_traces(moteur, layers, [("ombre", "Ombre")], "automatic_aggregation")

    assert document["modules"][0]["traces"][0]["graphics"]["name"] == "A"
    assert document["modules"][0]["traces"][0]["graphics"]["tooltips"] == ["A"]
