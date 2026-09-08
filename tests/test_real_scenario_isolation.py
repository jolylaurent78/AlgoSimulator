from pathlib import Path

import pytest

import src.AlgorithmeSegment as segment_module
from src.AlgorithmeSegment import AlgorithmeSegment, PlaneteAnnee
from src.ProjectPersistence import chargerProjetJsonV1
from src.calculAstronomique import MyJulianDate
from src.layerManager import LayerManager


FIXTURE_SEGMENT = Path(__file__).parent / "fixtures" / "segment_guerande_reference.json"


class FauxDate:
    def __init__(self, valeur):
        self.valeur = valeur

    def toString(self, _format):
        return self.valeur


class FauxSentinelle(dict):
    def __init__(self, _chemin):
        azimuts_geant = {
            "A": 171.5, "B": 170.0, "C": 308.5, "D": 286.5,
            "E": 256.0, "F": 218.0, "G": 179.0,
        }
        super().__init__({note: {"AzimutGeant": azimut} for note, azimut in azimuts_geant.items()})


@pytest.fixture
def frontieres_rapides(monkeypatch):
    monkeypatch.setattr(segment_module, "Sentinelle", FauxSentinelle)
    monkeypatch.setattr(
        segment_module,
        "trouverDatesPourDeclinaison",
        lambda *_args: (FauxDate("24/04/1066"), FauxDate("08/08/1066")),
    )


def normaliser_liste_annees(liste):
    return tuple(
        (annee, float(jd), sens, azimut_terre, azimut_planete, erreur)
        for annee, jd, sens, azimut_terre, azimut_planete, erreur in liste
    )


def snapshot_metier(moteur):
    scenario = moteur.getScenario()
    modules = scenario.modules
    segment = modules["segment"]
    cadran = modules["cadran"]
    planete = modules["planete"]
    axe = modules["axeterre"]
    annee = modules["annee"]
    return {
        "segment_actif": moteur.segment_actif,
        "scenario_actif": moteur.scenario_actif,
        "dataset": (
            moteur.dataset.date,
            moteur.dataset.lettreSegment,
            moteur.dataset.extremite1,
            moteur.dataset.milieuSegment,
            moteur.dataset.extremite2,
        ),
        "segment": (segment.choixAngleStr, segment.choixAngle, segment.angle),
        "cadran": (cadran.lieuObservation, cadran.declinaison, cadran.datePrintemps, cadran.dateEte),
        "planete": (
            planete.extremite1, planete.milieuSegment, planete.extremite2,
            planete.planete, planete.azimutCible, planete.azimutLigne1,
        ),
        "axeterre": (axe.sensCarte, axe.axeTerreStr, axe.azimut),
        "annee": (
            annee.choixAngle, annee.angleAnalyse, annee.listeAnneesSelection,
            normaliser_liste_annees(annee.listeAnnees),
        ),
    }


def recalculer_actif(moteur):
    moteur.calculerModules(setup=True)


def test_planete_annee_reinitialise_listes_selection_et_centres(monkeypatch):
    module = PlaneteAnnee()
    module.borneMin = 1200
    module.periode = 2
    module.azimutAxeterre = 10
    module.angleAnalyse = 5
    module.planetePlanete = "Mars"
    appels = []

    def trouver_date(azimut, annee, planete, jd_centre=None):
        appels.append((azimut, annee, planete, jd_centre))
        return MyJulianDate(1 if azimut < 180 else 2, 1, int(annee))

    monkeypatch.setattr(segment_module, "trouverDatePourAzimut", trouver_date)
    monkeypatch.setattr(
        segment_module,
        "azimutHeliocentrique",
        lambda jd, _planete, _annee: 15 if jd.enTuple()[2] == 1 else 185,
    )

    assert module.calculerAnnees(init=True) is False
    assert module.listeAnnees == []
    assert module.listeAnneesSelection is None
    assert module.jd_centre_direct is None
    assert module.jd_centre_oppose is None
    module.calculerAnnees(init=False)
    premier_resultat = normaliser_liste_annees(module.listeAnnees)
    assert len(premier_resultat) == 2

    module.listeAnneesSelection = 1
    module.calculerAnnees(init=True)
    module.calculerAnnees(init=False)

    assert normaliser_liste_annees(module.listeAnnees) == premier_resultat
    assert module.listeAnneesSelection is None
    assert appels[0][3] is None and appels[1][3] is None
    assert appels[2][3] is None and appels[3][3] is None


def test_moteur_reel_scenario_a_b_a_est_deterministe_et_egal_au_temoin(frontieres_rapides):
    moteur, layers = chargerProjetJsonV1(FIXTURE_SEGMENT)
    scenario_a = moteur.getScenario()
    scenario_b = moteur.creerScenarioUnitaireAutomatique(
        "Sens inverse",
        [("axeterre", "sensCarte", "Sens", "Sens Inverse")],
        scenario_a,
        layers,
    )

    moteur.appliquerScenario(scenario_a.getDescriptionLisible())
    recalculer_actif(moteur)
    a1 = snapshot_metier(moteur)
    moteur.appliquerScenario(scenario_b.getDescriptionLisible())
    recalculer_actif(moteur)
    b1 = snapshot_metier(moteur)
    moteur.appliquerScenario(scenario_a.getDescriptionLisible())
    recalculer_actif(moteur)
    a2 = snapshot_metier(moteur)
    moteur.appliquerScenario(scenario_b.getDescriptionLisible())
    recalculer_actif(moteur)
    b2 = snapshot_metier(moteur)

    temoin, _ = chargerProjetJsonV1(FIXTURE_SEGMENT)
    recalculer_actif(temoin)

    assert a1 == a2 == snapshot_metier(temoin)
    assert b1 == b2
    assert a1["axeterre"] != b1["axeterre"]


@pytest.mark.integration
def test_moteur_reel_isole_segments_et_scenarios_avec_dataset_production(frontieres_rapides):
    layers = LayerManager()
    moteur = AlgorithmeSegment(layers)
    segment_a, segment_b = moteur.getListeSegments()[:2]
    scenario_a_defaut = moteur.getScenario()
    scenario_a_alterne = moteur.creerScenarioUnitaireAutomatique(
        "A inverse",
        [("axeterre", "sensCarte", "Sens", "Sens Inverse")],
        scenario_a_defaut,
        layers,
    )

    moteur.appliquerScenario(scenario_a_defaut.getDescriptionLisible())
    recalculer_actif(moteur)
    a_defaut_avant = snapshot_metier(moteur)
    moteur.appliquerScenario(scenario_a_alterne.getDescriptionLisible())
    recalculer_actif(moteur)
    a_alterne_avant = snapshot_metier(moteur)

    moteur.setSegment(segment_b, layers)
    recalculer_actif(moteur)
    b = snapshot_metier(moteur)
    moteur.setSegment(segment_a, layers)
    recalculer_actif(moteur)
    a_defaut_apres_retour = snapshot_metier(moteur)
    assert moteur.scenario_actif == scenario_a_defaut.nom
    moteur.appliquerScenario(scenario_a_alterne.getDescriptionLisible())
    recalculer_actif(moteur)
    a_alterne_apres_retour = snapshot_metier(moteur)

    assert a_defaut_avant == a_defaut_apres_retour
    assert a_alterne_avant == a_alterne_apres_retour
    assert b["segment_actif"] == segment_b
    assert b["dataset"] != a_defaut_avant["dataset"]
    assert a_alterne_apres_retour["axeterre"] != a_defaut_avant["axeterre"]
