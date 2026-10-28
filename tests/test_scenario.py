from src.AlgorithmeManager import ModuleAlgo, Scenario, TypeScenario
from src.affichage_objets import ObjetGraphique
from src.layerManager import LayerManager


class FakeModule(ModuleAlgo):
    pass


class FakeGraphicalModule(ModuleAlgo):
    def __init__(self, calls, objet):
        self.calls = calls
        self.objet = objet

    def construireRepresentationCarte(self):
        self.calls.append("graphique")
        return [self.objet]


class FakeEmptyModule(ModuleAlgo):
    def __init__(self, calls):
        self.calls = calls

    def construireRepresentationCarte(self):
        self.calls.append("vide")
        return []


class FakeSolutionModule(ModuleAlgo):
    def resultat(self):
        return "solution"


def creer_scenario(quadruplets=(), type_scenario=TypeScenario.DEFAULT, modules=None, ordre_modules=None):
    return Scenario(
        nom="Scenario test",
        quadruplets=list(quadruplets),
        modules=modules or {"m1": FakeModule(), "m2": FakeModule()},
        ordreModules=ordre_modules or ["m1", "m2"],
        segment="segment-test",
        layerManager=LayerManager(),
        type_scenario=type_scenario,
    )


def test_construction_initialise_les_attributs_et_parametres_dict():
    quadruplets = [("m1", "foo", "Foo", 10), ("m2", "bar", "Bar", 20)]

    scenario = creer_scenario(quadruplets)

    assert scenario.nom == "Scenario test"
    assert scenario.segment == "segment-test"
    assert scenario.type_scenario is TypeScenario.DEFAULT
    assert set(scenario.modules) == {"m1", "m2"}
    assert scenario.ordreModules == ["m1", "m2"]
    assert scenario.solutionScenario is False
    assert scenario.parametres_dict == {"m1.foo": 10, "m2.bar": 20}
    assert scenario.getListeParametres() == [("m1", "foo"), ("m2", "bar")]


def test_get_parametre_retourne_la_valeur_ou_none():
    scenario = creer_scenario([("m1", "foo", "Foo", 10)])

    assert scenario.getParametre("m1", "foo") == 10
    assert scenario.getParametre("m1", "inconnu") is None


def test_set_parametre_existant_met_a_jour_dict_et_quadruplet():
    scenario = creer_scenario([("m1", "foo", "Foo", 10)])

    scenario.setParametre("m1", "foo", 42)

    assert scenario.parametres_dict["m1.foo"] == 42
    assert scenario.parametres == [("m1", "foo", "Foo", 42)]


def test_set_parametre_nouveau_ajoute_un_quadruplet_avec_attribut_comme_shortlabel():
    scenario = creer_scenario()

    scenario.setParametre("m1", "nouveau", 42)

    assert scenario.parametres_dict["m1.nouveau"] == 42
    assert scenario.parametres == [("m1", "nouveau", "nouveau", 42)]


def test_solution_est_modifiable_et_lisible():
    scenario = creer_scenario()

    scenario.setSolution(True)

    assert scenario.getSolution() is True


def test_description_lisible_default_et_utilisateur_est_le_nom():
    assert creer_scenario(type_scenario=TypeScenario.DEFAULT).getDescriptionLisible() == "Scenario test"
    assert creer_scenario(type_scenario=TypeScenario.UTILISATEUR).getDescriptionLisible() == "Scenario test"


def test_description_lisible_automatique_sans_parametre():
    assert creer_scenario(type_scenario=TypeScenario.AUTOMATIQUE).getDescriptionLisible() == "Automatique"


def test_description_lisible_automatique_avec_parametres():
    scenario = creer_scenario(
        [("m", "foo", "F", 10), ("m", "bar", "B", 20)],
        type_scenario=TypeScenario.AUTOMATIQUE,
    )

    assert scenario.getDescriptionLisible() == "F = 10, B = 20"


def test_generer_tooltip_scenario_sans_et_avec_parametres():
    assert creer_scenario().genererTooltipScenario() == []

    scenario = creer_scenario([("m1", "foo", "Foo", 10)])
    assert scenario.genererTooltipScenario() == ["Paramètres du scénario:", "- FooM1 = 10"]


def test_construire_representation_carte_vide_layer_et_annote_les_objets():
    calls = []
    objet = ObjetGraphique(nom="objet test")
    modules = {
        "graphique": FakeGraphicalModule(calls, objet),
        "vide": FakeEmptyModule(calls),
    }
    scenario = creer_scenario(modules=modules, ordre_modules=["graphique", "vide"])
    layer_manager = LayerManager()
    layer = layer_manager.creerLayer(scenario.getDescriptionLisible(), segment=scenario.segment)
    layer.inclureObjetDansLayer(ObjetGraphique(nom="ancien"))

    scenario.construireRepresentationCarte(layer)

    assert calls == ["graphique", "vide"]
    assert layer.getListeObjetsGraphiques() == [objet]
    assert objet.tags["module"] == "graphique"
    assert objet.tooltips_scenario == scenario.genererTooltipScenario()


def test_get_solution_algorithme_gere_module_et_methode_absents():
    scenario = creer_scenario(modules={"solution": FakeSolutionModule(), "valeur": FakeModule()})
    scenario.modules["valeur"].resultat = "non callable"

    assert scenario.getSolutionAlgorithme("solution", "resultat") == "solution"
    assert scenario.getSolutionAlgorithme("absent", "resultat") is None
    assert scenario.getSolutionAlgorithme("valeur", "resultat") is None
