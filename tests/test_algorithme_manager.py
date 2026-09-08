import pytest

from src.AlgorithmeManager import AlgorithmeManager, ModuleAlgo, TypeScenario
from src.layerManager import LayerManager


class FakeDataset:
    def __init__(self):
        self.segment = "A"
        self.valeur = 5
        self.setup_count = 0
        self.calcul_count = 0
        self._values = {"A": {"valeur": 5}, "B": {"valeur": 8}}

    def setup(self):
        self.setup_count += 1

    def calculer(self):
        self.calcul_count += 1
        self.valeur = self._values[self.segment]["valeur"]

    def getValeursSegment(self):
        return list(self._values)

    def getValeurPourSegment(self, segment, attribut):
        return self._values[segment][attribut]


class FakeSource(ModuleAlgo):
    def __init__(self):
        self.valeur = 10
        self.setup_count = 0
        self.calcul_count = 0
        self.last_init = None

    def setup(self):
        self.setup_count += 1

    def calculer(self):
        self.calcul_count += 1

    def methodeTest(self, init):
        self.last_init = init
        return "ok"

    def getValeursValeur(self):
        return [1, 2, 3]


class FakeIntermediaire(ModuleAlgo):
    def __init__(self):
        self.valeurSource = None
        self.resultat = None
        self.setup_count = 0
        self.calcul_count = 0

    def getEntreesModules(self):
        return ["source.valeur"]

    def setup(self):
        self.setup_count += 1

    def calculer(self):
        self.calcul_count += 1
        self.resultat = self.valeurSource * 2


class FakeCible(ModuleAlgo):
    def __init__(self):
        self.resultatIntermediaire = None
        self.resultatFinal = None
        self.setup_count = 0
        self.calcul_count = 0

    def getEntreesModules(self):
        return ["intermediaire.resultat"]

    def setup(self):
        self.setup_count += 1

    def calculer(self):
        self.calcul_count += 1
        self.resultatFinal = self.resultatIntermediaire + 1


class FakeConsommateurDataset(ModuleAlgo):
    def __init__(self):
        self.valeurDataset = None
        self.resultat = None
        self.setup_count = 0
        self.calcul_count = 0

    def getEntreesModules(self):
        return ["dataset.valeur"]

    def setup(self):
        self.setup_count += 1

    def calculer(self):
        self.calcul_count += 1
        self.resultat = self.valeurDataset * 10


class FakeAvecRegle(ModuleAlgo):
    def __init__(self):
        self.valeur = 1
        self.valeurCalculee = None
        self.rule_count = 0
        self.calcul_count = 0

    def regle_valeur_auto(self):
        self.rule_count += 1
        return 42

    def getRegles(self):
        return [("Valeur automatique", "valeur", self.regle_valeur_auto)]

    def calculer(self):
        self.calcul_count += 1
        self.valeurCalculee = self.valeur * 10


class FakeAlgorithmeManager(AlgorithmeManager):
    def __init__(self, layer_manager):
        self.dataset = FakeDataset()
        super().__init__(layer_manager)

    def getListeModulesInitiale(self):
        return [
            ("source", "Source", FakeSource()),
            ("intermediaire", "Intermédiaire", FakeIntermediaire()),
            ("cible", "Cible", FakeCible()),
            ("dataset_consumer", "Dataset", FakeConsommateurDataset()),
            ("regle", "Règle", FakeAvecRegle()),
        ]


class FakeCycleA(ModuleAlgo):
    def __init__(self):
        self.valeur = 1

    def getEntreesModules(self):
        return ["cycle_b.valeur"]


class FakeCycleB(ModuleAlgo):
    def __init__(self):
        self.valeur = 1

    def getEntreesModules(self):
        return ["cycle_a.valeur"]


class FakeCycleManager(AlgorithmeManager):
    def __init__(self, layer_manager):
        self.dataset = FakeDataset()
        super().__init__(layer_manager)

    def getListeModulesInitiale(self):
        return [("cycle_a", "A", FakeCycleA()), ("cycle_b", "B", FakeCycleB())]


class FakeEntreeInconnue(ModuleAlgo):
    def getEntreesModules(self):
        return ["inconnu.valeur"]


class FakeAttributInconnu(ModuleAlgo):
    def getEntreesModules(self):
        return ["source.inconnu"]


class FakeDatasetAttributInconnu(ModuleAlgo):
    def getEntreesModules(self):
        return ["dataset.inconnu"]


class FakeManagerInvalide(AlgorithmeManager):
    modules = []

    def __init__(self, layer_manager):
        self.dataset = FakeDataset()
        super().__init__(layer_manager)

    def getListeModulesInitiale(self):
        return self.modules


@pytest.fixture
def layer_manager():
    return LayerManager()


@pytest.fixture
def fake_manager(layer_manager):
    return FakeAlgorithmeManager(layer_manager)


def scenario_actif(manager):
    return manager.getScenario()


def test_initialisation_prepare_dataset_templates_et_scenario_default(fake_manager):
    scenario = scenario_actif(fake_manager)

    assert fake_manager.dataset.setup_count == 1
    assert fake_manager.dataset.calcul_count == 1
    assert fake_manager.segment_actif == "A"
    assert scenario.getTypeScenario() is TypeScenario.DEFAULT
    assert fake_manager.scenario_actif == scenario.nom


def test_templates_sont_enregistres_et_disponibles(fake_manager):
    templates = fake_manager.getModulesTemplate()

    assert set(templates) == {"source", "intermediaire", "cible", "dataset_consumer", "regle"}
    assert fake_manager.estModuleDisponible("source") is True
    assert fake_manager.estModuleDisponible("dataset") is True
    assert fake_manager.estModuleDisponible("absent") is False
    assert fake_manager.estAttributDisponible("source", "valeur") is True
    assert fake_manager.estAttributDisponible("source", "inconnu") is False
    assert fake_manager.estMethodeDisponible("source", "methodeTest") is True
    assert fake_manager.estMethodeDisponible("source", "valeur") is False


def test_modules_generes_sont_des_deepcopies_des_templates(fake_manager):
    modules = fake_manager.genererModulesDepuisTemplates()
    modules["source"].valeur = 99

    assert modules["source"] is not fake_manager.getModulesTemplate()["source"]
    assert fake_manager.getModulesTemplate()["source"].valeur == 10


def test_graphe_dependances_represente_les_dependants_et_ignore_dataset(fake_manager):
    graphe = fake_manager.graphDependanceModules

    assert graphe["source"] == ["intermediaire"]
    assert graphe["intermediaire"] == ["cible"]
    assert graphe["dataset_consumer"] == []
    assert "dataset" not in graphe


def test_ordre_topologique_respecte_les_dependances(fake_manager):
    ordre = fake_manager.ordreModules

    assert ordre.index("source") < ordre.index("intermediaire") < ordre.index("cible")
    assert ordre.index("dataset_consumer") >= 0
    assert ordre.index("regle") >= 0


def test_cycle_de_dependances_est_refuse(layer_manager):
    with pytest.raises(ValueError, match="Cycle"):
        FakeCycleManager(layer_manager)


@pytest.mark.parametrize(
    "modules",
    [
        [("invalide", "Invalide", FakeEntreeInconnue())],
        [("source", "Source", FakeSource()), ("invalide", "Invalide", FakeAttributInconnu())],
        [("invalide", "Invalide", FakeDatasetAttributInconnu())],
    ],
)
def test_validation_globale_refuse_les_dependances_invalides(layer_manager, modules):
    FakeManagerInvalide.modules = modules

    with pytest.raises(Exception, match="Structure globale invalide"):
        FakeManagerInvalide(layer_manager)


def test_validation_scenario_accepte_le_graphe_complet(fake_manager):
    fake_manager.validerStructureScenario()


def test_validation_scenario_refuse_module_source_absent(fake_manager):
    del scenario_actif(fake_manager).modules["source"]

    with pytest.raises(Exception, match="Structure invalide"):
        fake_manager.validerStructureScenario()


def test_validation_scenario_refuse_attribut_source_ou_dataset_absent(fake_manager):
    del scenario_actif(fake_manager).modules["source"].valeur
    with pytest.raises(Exception, match="Structure invalide"):
        fake_manager.validerStructureScenario()

    fake_manager = FakeAlgorithmeManager(LayerManager())
    del fake_manager.dataset.valeur
    with pytest.raises(Exception, match="Structure invalide"):
        fake_manager.validerStructureScenario()


def test_injection_module_vers_module_propage_la_valeur_source(fake_manager):
    scenario = scenario_actif(fake_manager)

    fake_manager.injecterEntreesDansModuleObjet("intermediaire")

    assert scenario.modules["intermediaire"].valeurSource == 10


def test_calcul_complet_propage_la_chaine_sur_deux_niveaux(fake_manager):
    scenario = scenario_actif(fake_manager)

    fake_manager.calculerModules()

    assert scenario.modules["source"].valeur == 10
    assert scenario.modules["intermediaire"].resultat == 20
    assert scenario.modules["cible"].resultatFinal == 21


def test_calcul_avec_setup_incremente_les_compteurs(fake_manager):
    scenario = scenario_actif(fake_manager)
    avant = {nom: module.setup_count for nom, module in scenario.modules.items() if hasattr(module, "setup_count")}

    fake_manager.calculerModules(setup=True)

    assert all(scenario.modules[nom].setup_count == compte + 1 for nom, compte in avant.items())
    assert all(module.calcul_count >= 2 for module in scenario.modules.values())


def test_injection_dataset_utilise_le_segment_actif_et_son_changement(fake_manager, layer_manager):
    scenario_a = scenario_actif(fake_manager)
    assert scenario_a.modules["dataset_consumer"].resultat == 50

    fake_manager.setSegment("B", layer_manager)
    scenario_b = scenario_actif(fake_manager)

    assert fake_manager.dataset.valeur == 8
    assert scenario_b.modules["dataset_consumer"].valeurDataset == 8
    assert scenario_b.modules["dataset_consumer"].resultat == 80


def test_regles_actives_sont_listes_et_appliquees_avant_calcul(fake_manager):
    scenario = scenario_actif(fake_manager)
    regle = scenario.modules["regle"]

    assert [(module, attribut, nom) for module, attribut, nom, _ in fake_manager.getListeRegles()] == [
        ("regle", "valeur", "Valeur automatique"),
    ]
    assert regle.valeur == 42
    assert regle.valeurCalculee == 420
    assert regle.rule_count == 1


def test_regle_inactive_nest_pas_executee(fake_manager):
    scenario = scenario_actif(fake_manager)
    regle = scenario.modules["regle"]
    fake_manager.regles_actives["regle.valeur"] = "Autre règle"
    regle.valeur = 3
    avant = regle.rule_count

    fake_manager.calculerModules()

    assert regle.rule_count == avant
    assert regle.valeurCalculee == 30


def test_get_parametre_couvre_module_actif_nomme_et_dataset(fake_manager):
    nom = fake_manager.scenario_actif

    assert fake_manager.getParametre("source", "valeur") == 10
    assert fake_manager.getParametre("source", "valeur", nomScenario=nom, segment="A") == 10
    assert fake_manager.getParametre("dataset", "valeur") == 5
    assert fake_manager.getParametre("dataset", "valeur", nomScenario=nom, segment="B") == 8


def test_get_parametre_refuse_segment_explicite_sans_scenario_et_module_absent(fake_manager):
    with pytest.raises(ValueError, match="obligatoire"):
        fake_manager.getParametre("dataset", "valeur", segment="B")
    with pytest.raises(ValueError, match="introuvable"):
        fake_manager.getParametre("absent", "valeur")


def test_set_parametre_recalcule_et_reconstruit_le_layer(fake_manager, layer_manager):
    scenario = scenario_actif(fake_manager)
    intermediaire = scenario.modules["intermediaire"]
    avant = intermediaire.calcul_count

    fake_manager.setParametre("source", "valeur", 7, layer_manager)

    assert scenario.modules["source"].valeur == 7
    assert intermediaire.calcul_count == avant + 1
    assert scenario.modules["cible"].resultatFinal == 15
    assert layer_manager.getLayer(scenario.getDescriptionLisible(), segment="A") is not None


def test_set_parametre_dataset_modifie_directement_le_dataset(fake_manager, layer_manager):
    avant = fake_manager.dataset.calcul_count

    fake_manager.setParametre("dataset", "valeur", 12, layer_manager)

    assert fake_manager.dataset.valeur == 12
    assert fake_manager.dataset.calcul_count == avant


def test_set_parametre_refuse_module_absent(fake_manager, layer_manager):
    with pytest.raises(ValueError, match="introuvable"):
        fake_manager.setParametre("absent", "valeur", 1, layer_manager)


def test_set_parametre_sans_recalcul_ne_declenche_ni_calcul_ni_reconstruction(fake_manager):
    scenario = scenario_actif(fake_manager)
    source = scenario.modules["source"]
    avant = source.calcul_count

    fake_manager.setParametreSansRecalcul("source", "valeur", 7)

    assert source.valeur == 7
    assert source.calcul_count == avant


def test_set_parametre_sans_recalcul_refuse_module_absent(fake_manager):
    with pytest.raises(ValueError, match="introuvable"):
        fake_manager.setParametreSansRecalcul("absent", "valeur", 1)


def test_executer_methode_transmet_init_et_retourne_le_resultat(fake_manager):
    source = scenario_actif(fake_manager).modules["source"]

    assert fake_manager.executerMethode("source", "methodeTest", init=True) == "ok"
    assert source.last_init is True


def test_executer_methode_refuse_module_absent(fake_manager):
    with pytest.raises(ValueError, match="introuvable"):
        fake_manager.executerMethode("absent", "methodeTest", init=False)


def test_get_valeurs_parametre_delegue_au_module(fake_manager):
    assert fake_manager.getValeursParametre("source", "valeur") == [1, 2, 3]


def test_get_valeurs_parametre_refuse_module_absent(fake_manager):
    with pytest.raises(ValueError, match="introuvable"):
        fake_manager.getValeursParametre("absent", "valeur")


def test_creer_scenario_utilisateur_duplique_modules_solution_et_layer(fake_manager, layer_manager):
    base = scenario_actif(fake_manager)
    base.setSolution(True)

    utilisateur = fake_manager.creerScenarioUtilisateur("Utilisateur", base, layer_manager, couleur=(1, 2, 3))
    utilisateur.modules["source"].valeur = 99

    assert utilisateur.getTypeScenario() is TypeScenario.UTILISATEUR
    assert utilisateur.segment == "A"
    assert utilisateur.getSolution() is True
    assert utilisateur.modules["source"] is not base.modules["source"]
    assert base.modules["source"].valeur == 10
    assert layer_manager.getLayer("Utilisateur", segment="A").getCouleur() == (1, 2, 3)


def test_creer_scenario_automatique_applique_parametres_et_ne_change_pas_lactif(fake_manager, layer_manager):
    base = scenario_actif(fake_manager)
    actif_avant = fake_manager.scenario_actif

    auto = fake_manager.creerScenarioUnitaireAutomatique(
        "Auto", [("source", "valeur", "S", 6)], base, layer_manager,
    )

    assert auto.getTypeScenario() is TypeScenario.AUTOMATIQUE
    assert auto.modules["source"].valeur == 6
    assert auto.modules["cible"].resultatFinal == 13
    assert fake_manager.scenario_actif == actif_avant
    assert layer_manager.getLayer("S = 6", segment="A") is not None


def test_scenarios_liste_dict_renommage_et_application_respectent_les_contrats(fake_manager, layer_manager):
    base = scenario_actif(fake_manager)
    utilisateur = fake_manager.creerScenarioUtilisateur("Utilisateur", base, layer_manager)

    assert fake_manager.getScenarioNomLisible("Utilisateur") is utilisateur
    assert set(fake_manager.getScenariosDict(type_scenario=TypeScenario.UTILISATEUR)) == {base.nom, "Utilisateur"}
    fake_manager.renommerScenario("Utilisateur", "Renommé")
    fake_manager.appliquerScenario("Renommé")

    assert fake_manager.scenario_actif == "Renommé"
    assert fake_manager.getListeScenarios(type_scenario=TypeScenario.UTILISATEUR) == ["Renommé"]


def test_set_segment_cree_default_et_replie_le_scenario_actif(fake_manager, layer_manager):
    base = scenario_actif(fake_manager)
    fake_manager.creerScenarioUtilisateur("Utilisateur", base, layer_manager)
    fake_manager.scenario_actif = "Utilisateur"

    fake_manager.setSegment("B", layer_manager)

    assert fake_manager.segment_actif == "B"
    assert fake_manager.dataset.segment == "B"
    assert fake_manager.scenario_actif == "Scénario par défaut"
    assert fake_manager.getScenario().getTypeScenario() is TypeScenario.DEFAULT


def test_suppression_des_scenarios_automatiques_preserve_default_et_user(fake_manager, layer_manager):
    base = scenario_actif(fake_manager)
    utilisateur = fake_manager.creerScenarioUtilisateur("Utilisateur", base, layer_manager)
    auto = fake_manager.creerScenarioUnitaireAutomatique(
        "Auto", [("source", "valeur", "S", 6)], utilisateur, layer_manager,
    )
    layer_auto = auto.getDescriptionLisible()

    supprimes = fake_manager.supprimerTousScenariosAutomatiques(layer_manager)

    assert supprimes == ["Auto"]
    assert fake_manager.aDesScenarioAutomatiques() is False
    assert set(fake_manager.getListeScenarios()) == {base.nom, "Utilisateur"}
    assert layer_manager.getLayer(layer_auto, segment="A") is None


def test_suppression_par_nom_lisible_met_a_jour_actif_et_signale_labsent(fake_manager, layer_manager):
    base = scenario_actif(fake_manager)
    utilisateur = fake_manager.creerScenarioUtilisateur("Utilisateur", base, layer_manager)
    fake_manager.scenario_actif = "Utilisateur"

    fake_manager.supprimerScenarioNomLisible("Utilisateur", layer_manager)

    assert fake_manager.scenario_actif == base.nom
    assert layer_manager.getLayer("Utilisateur", segment="A") is None
    with pytest.raises(ValueError, match="introuvable"):
        fake_manager.supprimerScenarioNomLisible("Utilisateur", layer_manager)
