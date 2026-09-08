import math

import pytest

import src.AlgorithmeSegment as algorithme_segment
from src.AlgorithmeSegment import AxeTerre, PlaneteAnnee, PlaneteChemin, SegmentChemin, cadranSolaire


class VilleFictive:
    def __init__(self, nom, coordonnees=(49.92, 1.0)):
        self.nom = nom
        self._coordonnees = coordonnees

    def getCoordonneesGPS(self):
        return self._coordonnees


class PointFictif:
    def __init__(self, ville):
        self.ville = ville


class LigneFictive:
    azimuts = {
        ("Forbach", "Dieppe"): 279.71,
        ("Forbach", "Bourges"): 233.24,
    }

    def __init__(self, depart, arrivee):
        self.depart = depart
        self.arrivee = arrivee

    def getAzimutCarte(self):
        return self.azimuts[(self.depart.ville.nom, self.arrivee.ville.nom)]


class LigneAzimutFictive:
    def __init__(self, centre, azimut):
        self.centre = centre
        self.azimut = azimut


class SentinelleFictive(dict):
    def __init__(self, chemin):
        super().__init__(
            {
                "A": {"AzimutGeant": 200.0},
                "B": {"AzimutGeant": 270.0},
                "C": {"AzimutGeant": 300.0},
                "D": {"AzimutGeant": 280.0},
                "E": {"AzimutGeant": 260.0},
                "F": {"AzimutGeant": 240.0},
                "G": {"AzimutGeant": 220.0},
            }
        )


def installer_geometrie_fictive(monkeypatch, azimut_ligne_1=279.71):
    villes = {
        "Dieppe": VilleFictive("Dieppe"),
        "Forbach": VilleFictive("Forbach"),
        "Bourges": VilleFictive("Bourges"),
    }
    LigneFictive.azimuts[("Forbach", "Dieppe")] = azimut_ligne_1
    monkeypatch.setattr(algorithme_segment, "villes_dict", villes)
    monkeypatch.setattr(algorithme_segment, "PointGraphique", PointFictif)
    monkeypatch.setattr(algorithme_segment, "LigneEntreVilles", LigneFictive)


def test_segment_chemin_expose_les_deux_angles_et_convertit_le_choix():
    module = SegmentChemin()
    module.angle = 46.47610107307804

    assert module.getValeursChoixAngleStr() == ("46.48°", "133.52°")

    module.choixAngleStr = "133.52°"
    module.calculer()

    assert module.choixAngle == pytest.approx(133.52)


def test_cadran_choisit_le_lieu_par_defaut_et_calcule_les_dates(monkeypatch):
    class DateFictive:
        def __init__(self, valeur):
            self.valeur = valeur

        def toString(self, format_date):
            assert format_date == "JJ/MM/AAAA"
            return self.valeur

    monkeypatch.setattr(
        algorithme_segment,
        "villes_dict",
        {"Dieppe": VilleFictive("Dieppe", (49.9225, 1.0))},
    )
    monkeypatch.setattr(
        algorithme_segment,
        "trouverDatesPourDeclinaison",
        lambda declinaison, annee: (DateFictive("24/04/1066"), DateFictive("08/08/1066")),
    )
    module = cadranSolaire()
    module.lettreSegmentDataset = "G"
    module.choixAngleSegment = 133.52

    module.setup()
    module.calculer()

    assert module.lieuObservation == "Dieppe"
    assert module.getValeursLieuObservation() == ["Dieppe", "Cherbourg"]
    assert module.latitude == pytest.approx(49.9225)
    assert module.declinaison == pytest.approx(14.716826834017965)
    assert (module.datePrintemps, module.dateEte) == ("24/04/1066", "08/08/1066")


@pytest.mark.parametrize(
    ("azimut_ligne_1", "azimut_cible"),
    [
        (279.71, 279.71),
        (99.71, 279.71),
        (80.0, 280.0),
    ],
    ids=["direct", "symetrique", "oppose"],
)
def test_planete_selectionne_lazimut_dans_la_fenetre_et_la_planete(monkeypatch, azimut_ligne_1, azimut_cible):
    installer_geometrie_fictive(monkeypatch, azimut_ligne_1)
    monkeypatch.setattr(algorithme_segment, "Sentinelle", SentinelleFictive)
    monkeypatch.setattr(algorithme_segment, "LigneAzimut", LigneAzimutFictive)
    module = PlaneteChemin()
    module.extremite1Dataset = "Dieppe"
    module.milieuSegmentDataset = "Forbach"
    module.extremite2Dataset = "Bourges"

    module.setup()
    module.calculer()

    assert module.azimutLigne1 == pytest.approx(azimut_ligne_1)
    assert module.azimutCible == pytest.approx(azimut_cible)
    assert module.planete == "Uranus"
    assert PlaneteChemin.tableauPlanete["DE"] == "Uranus"


@pytest.mark.parametrize(
    ("choix", "angle_analyse"),
    [("=", 46.47), ("complémentaire", 133.53)],
)
def test_planete_annee_calcule_langle_direct_ou_complementaire(monkeypatch, choix, angle_analyse):
    installer_geometrie_fictive(monkeypatch)
    module = PlaneteAnnee()
    module.extremite1 = "Dieppe"
    module.milieuSegment = "Forbach"
    module.extremite2 = "Bourges"
    module.choixAngle = choix

    module.calculer()

    assert module.angle == pytest.approx(46.47)
    assert module.angleAnalyse == pytest.approx(angle_analyse)
    assert module.getValeursChoixAngle() == ("=", "complémentaire")
    assert module.getValeursBorneMin()[0] == 700
    assert module.getValeursPeriode() == [100, 200, 300, 400]


@pytest.mark.parametrize(
    ("sens", "azimut_attendu"),
    [("Bon sens", 233.24), ("Sens Inverse", 126.76)],
)
def test_axe_terre_conserve_le_libelle_et_applique_le_sens(monkeypatch, sens, azimut_attendu):
    installer_geometrie_fictive(monkeypatch)
    module = AxeTerre()
    module.milieuSegment = "Forbach"
    module.extremite2 = "Bourges"
    module.sensCarte = sens

    module.calculer()

    assert module.axeTerreStr == "Forbach -> Bourges"
    assert module.axeTerre == pytest.approx(233.24)
    assert module.azimut == pytest.approx(azimut_attendu)
    assert module.getValeursSensCarte() == ("Bon sens", "Sens Inverse")
