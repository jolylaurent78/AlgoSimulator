import json
from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import src.ProjectPersistence as persistence
from src.calculAstronomique import MyJulianDate
from src.layerManager import LayerManager


class FakeModule:
    def __init__(self, foo=1, cache=None):
        self.foo = foo
        self.cache = [] if cache is None else cache
        self.non_cache = "protégé"


class FakeScenario:
    def __init__(self, modules=None):
        self.nom = "Scenario test"
        self.segment = "A"
        self.modules = modules or {"module": FakeModule(), "annee": FakeModule()}

    def getDescriptionLisible(self):
        return "Scenario test"


def ecrire_csv_persistence(tmp_path, lignes):
    chemin = tmp_path / "persistence.csv"
    chemin.write_text("Type,Module,Attribut\n" + lignes, encoding="utf-8")
    return chemin


def test_csv_persistence_classe_types_ordre_commentaires_et_doublons(tmp_path):
    chemin = ecrire_csv_persistence(
        tmp_path,
        "# commentaire\n\n INPUT ,m,un\ninput_multiple,m,deux\nCache,cache,resultat\ndata,m,ignore\nautre,m,ignore2\ninput,m,un\ncache,cache,resultat\n",
    )

    parametres, caches = persistence._lire_parametres_persistants_csv(chemin)

    assert parametres == [("m", "un"), ("m", "deux")]
    assert caches == [("cache", "resultat")]


@pytest.mark.parametrize("colonne", ["Type", "Module", "Attribut"])
def test_csv_persistence_refuse_les_colonnes_obligatoires_absentes(tmp_path, colonne):
    autres = [champ for champ in ("Type", "Module", "Attribut") if champ != colonne]
    chemin = tmp_path / "incomplet.csv"
    chemin.write_text(",".join(autres) + "\n" + ",".join("x" for _ in autres) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="CSV de persistance incomplet"):
        persistence._lire_parametres_persistants_csv(chemin)


@pytest.mark.parametrize("ligne", ["input,,attribut\n", "cache,module,\n"])
def test_csv_persistence_refuse_module_ou_attribut_vide(tmp_path, ligne):
    with pytest.raises(ValueError, match="Module/Attribut vide"):
        persistence._lire_parametres_persistants_csv(ecrire_csv_persistence(tmp_path, ligne))


def test_valeur_json_conserve_primitives_et_convertit_conteneurs():
    valeur = {"tuple": (1, "deux"), "liste": [True, None], "dict": {"x": 1.5}}

    assert persistence._valeur_json(valeur, "test") == {
        "tuple": [1, "deux"], "liste": [True, None], "dict": {"x": 1.5},
    }
    assert persistence._valeur_json(None, "test") is None


def test_valeur_json_encode_explicitement_my_julian_date():
    date = MyJulianDate(12, 10, 1365)

    assert persistence._valeur_json(date, "test") == {"__persist_type__": "MyJulianDate", "jd": float(date)}


def test_valeur_json_refuse_cles_non_textuelles():
    with pytest.raises(TypeError, match="cl.*non textuelle"):
        persistence._valeur_json({1: "invalide"}, "test")


def test_valeur_json_refuse_objet_non_supporte():
    with pytest.raises(TypeError, match="object"):
        persistence._valeur_json(object(), "test")


def test_valeur_cache_depuis_json_restaure_recursivement_my_julian_date_sans_confondre_les_tags_partiels():
    date = MyJulianDate(12, 10, 1365)
    tag = {"__persist_type__": "MyJulianDate", "jd": float(date)}
    valeur = {"liste": [tag, {"__persist_type__": "Autre", "jd": 123}, {**tag, "extra": True}]}

    restauree = persistence._valeur_cache_depuis_json(valeur)

    assert restauree["liste"][0] == date
    assert restauree["liste"][1] == {"__persist_type__": "Autre", "jd": 123}
    assert restauree["liste"][2] == {**tag, "extra": True}


def test_snapshot_dataset_conserve_ordre_noms_et_valeurs_json():
    dataset = SimpleNamespace(evenements=OrderedDict([
        ("B", {"coord": (1, 2), "valeur": "b"}),
        ("A", {"valeur": "a"}),
    ]))

    assert persistence._snapshot_dataset(dataset) == {
        "events": [
            {"event": "B", "coord": [1, 2], "valeur": "b"},
            {"event": "A", "valeur": "a"},
        ],
    }


def test_snapshot_dataset_refuse_labsence_devenements():
    with pytest.raises(TypeError, match="evenements"):
        persistence._snapshot_dataset(object())


def test_reconstruction_dataset_valide_conserve_ordre_et_initialise_runtime():
    dataset = persistence._construire_dataset_depuis_snapshot({
        "events": [{"event": "B", "Date": "01/01"}, {"event": "A", "Base1": "base"}],
    })

    assert list(dataset.evenements) == ["B", "A"]
    assert dataset.segment == "B"
    assert dataset.evenements["A"]["Base1"] == "base"
    assert dataset.date is None
    assert dataset.extremite1 is None
    assert dataset.base1 is None


def test_reconstruction_dataset_refuse_les_structures_invalides():
    cas_invalides = [
        None,
        {},
        {"events": {}},
        {"events": []},
        {"events": ["invalide"]},
        {"events": [{}]},
        {"events": [{"event": 1}]},
        {"events": [{"event": ""}]},
        {"events": [{"event": "A"}, {"event": "A"}]},
    ]

    for dataset_json in cas_invalides:
        with pytest.raises(ValueError):
            persistence._construire_dataset_depuis_snapshot(dataset_json)


def test_validation_entete_valide_retourne_la_classe_supportee():
    snapshot = {
        "format": persistence.FORMAT_PROJET,
        "schema_version": persistence.SCHEMA_VERSION,
        "algorithm": "AlgorithmeSegment",
    }

    assert persistence._valider_entete_snapshot(snapshot) is persistence.AlgorithmeSegment


def test_validation_entete_refuse_racine_format_et_version_invalides():
    valide = {
        "format": persistence.FORMAT_PROJET,
        "schema_version": persistence.SCHEMA_VERSION,
        "algorithm": "AlgorithmeSegment",
    }
    cas_invalides = [None, [], {**valide, "format": "autre"}, {**valide, "schema_version": 99}]

    for snapshot in cas_invalides:
        with pytest.raises(ValueError):
            persistence._valider_entete_snapshot(snapshot)


def test_restauration_parametres_affecte_plusieurs_modules_et_attributs():
    scenario = FakeScenario({"module": FakeModule(foo=1), "annee": FakeModule(foo=2)})

    persistence._restaurer_parametres_scenario(scenario, {"module": {"foo": 10}, "annee": {"foo": 20}})

    assert scenario.modules["module"].foo == 10
    assert scenario.modules["annee"].foo == 20


def test_restauration_parametres_refuse_les_structures_ou_references_invalides():
    scenario = FakeScenario()
    cas_invalides = [
        [],
        {"inconnu": {"foo": 1}},
        {"module": []},
        {"module": {"inconnu": 1}},
    ]

    for parametres in cas_invalides:
        with pytest.raises(ValueError):
            persistence._restaurer_parametres_scenario(scenario, parametres)


def test_snapshot_parametres_regroupe_et_ignore_dataset():
    scenario = FakeScenario({"module": FakeModule(foo=(1, 2))})

    snapshot = persistence._snapshot_parametres_scenario(
        scenario,
        [("module", "foo"), ("dataset", "date")],
    )

    assert snapshot == {"module": {"foo": [1, 2]}}


def test_snapshot_parametres_refuse_references_et_valeurs_invalides():
    scenario = FakeScenario({"module": FakeModule()})
    cas_invalides = [
        [("inconnu", "foo")],
        [("module", "inconnu")],
    ]
    for parametres_csv in cas_invalides:
        with pytest.raises(ValueError):
            persistence._snapshot_parametres_scenario(scenario, parametres_csv)

    scenario.modules["module"].foo = object()
    with pytest.raises(TypeError):
        persistence._snapshot_parametres_scenario(scenario, [("module", "foo")])


def test_restauration_cache_autorise_restaure_et_decode_my_julian_date():
    date = MyJulianDate(12, 10, 1365)
    scenario = FakeScenario({"annee": FakeModule(cache=[])})

    persistence._restaurer_caches_scenario(
        scenario,
        [("annee", "cache")],
        {"annee": {"cache": [{"__persist_type__": "MyJulianDate", "jd": float(date)}]}},
    )

    assert scenario.modules["annee"].cache == [date]


def test_restauration_cache_refuse_les_structures_et_references_invalides():
    scenario = FakeScenario({"annee": FakeModule(cache=[])})
    cas_invalides = [
        [],
        {"inconnu": {"cache": []}},
        {"annee": []},
        {"annee": {"inconnu": []}},
        {"annee": {"non_cache": []}},
    ]

    for caches in cas_invalides:
        with pytest.raises(ValueError):
            persistence._restaurer_caches_scenario(scenario, [("annee", "cache")], caches)


def test_snapshot_layer_lit_preferences_et_refuse_layer_absent():
    scenario = FakeScenario()
    layers = LayerManager()
    layer = layers.creerLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    layer.setCouleur((1, 2, 3))
    layer.setEpaisseur(4)
    layer.setVisible(False)

    assert persistence._snapshot_layer(scenario, layers) == {
        "color": [1, 2, 3], "thickness": 4, "visible": False,
    }

    with pytest.raises(ValueError, match="introuvable"):
        persistence._snapshot_layer(scenario, LayerManager())


def test_restauration_preferences_layer_applique_couleur_epaisseur_et_visibilite():
    scenario = FakeScenario()
    layers = LayerManager()
    layer = layers.creerLayer(scenario.getDescriptionLisible(), segment=scenario.segment)

    persistence._restaurer_preferences_layer(
        scenario, layers, {"color": [4, 5, 6], "thickness": 3, "visible": False},
    )

    assert layer.getCouleur() == (4, 5, 6)
    assert layer.getEpaisseur() == 3
    assert layer.estVisible() is False


def test_restauration_preferences_layer_refuse_les_donnees_invalides_ou_layer_absent():
    scenario = FakeScenario()
    layers = LayerManager()
    layers.creerLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    cas_invalides = [
        [],
        {"thickness": 1, "visible": True},
        {"color": [1, 2, 3], "visible": True},
        {"color": [1, 2, 3], "thickness": 1},
    ]
    for preferences in cas_invalides:
        with pytest.raises(ValueError):
            persistence._restaurer_preferences_layer(scenario, layers, preferences)

    with pytest.raises(ValueError, match="introuvable"):
        persistence._restaurer_preferences_layer(
            scenario, LayerManager(), {"color": [1, 2, 3], "thickness": 1, "visible": True},
        )


def test_sauvegarde_ecrit_snapshot_utf8_exact_avec_nouvelle_ligne(tmp_path):
    snapshot = {"format": "test", "libellé": "Chouette dorée"}
    chemin = tmp_path / "projet.json"

    with patch("src.ProjectPersistence.construireSnapshotProjetJsonV1", return_value=snapshot) as constructeur:
        resultat = persistence.sauvegarderProjetJsonV1(chemin, object(), object(), csv_path="contrat.csv")

    contenu = chemin.read_text(encoding="utf-8")
    constructeur.assert_called_once()
    assert resultat == snapshot
    assert json.loads(contenu) == snapshot
    assert "Chouette dorée" in contenu
    assert contenu.endswith("\n")
