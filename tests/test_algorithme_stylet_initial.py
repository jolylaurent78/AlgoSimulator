from types import SimpleNamespace

import pytest

import src.AlgorithmeStyletInitial as stylet
from src.AlgorithmeStyletInitial import Candidats, Carte, Etoile, Planete, SentinelleAlgo, Soleil


class DateFictive:
    def __init__(self, jour="Sam", texte="15/08/778", lettre="C", decalage=None):
        self.jour = jour
        self.texte = texte
        self.lettre = lettre
        self.decalage = decalage or self

    def jourSemaine(self):
        return self.jour

    def lettreDominicale(self):
        return self.lettre

    def date6Mois(self):
        return self.decalage

    def toString(self, format_date):
        return self.texte


class VilleFictive:
    def __init__(self, coordonnees):
        self.coordonnees = coordonnees

    def getCoordonneesGPS(self):
        return self.coordonnees


@pytest.mark.parametrize(
    ("heures", "visibilite", "date_attendue"),
    [((10, 9, 11), "Non visible", "14/02/778"), ((8, 9, 11), "Visible", "15/08/778")],
    ids=["zeta_dans_le_jour", "zeta_hors_du_jour"],
)
def test_soleil_choisit_la_date_observation_selon_visibilite(monkeypatch, heures, visibilite, date_attendue):
    date_decalee = DateFictive(texte="14/02/778")
    date_segment = DateFictive(texte="15/08/778", decalage=date_decalee)
    monkeypatch.setattr(stylet, "MyJulianDate", SimpleNamespace(fromString=lambda valeur: date_segment))
    monkeypatch.setattr(stylet, "villes_dict", {"Strasbourg": VilleFictive((48.5, 7.7))})
    monkeypatch.setattr(stylet, "calculLeverAstre", lambda *args: heures[0])
    monkeypatch.setattr(stylet, "calculLeverSoleil", lambda *args: heures[1])
    monkeypatch.setattr(stylet, "calculCoucherSoleil", lambda *args: heures[2])
    monkeypatch.setattr(
        stylet,
        "LieuxObservation",
        SimpleNamespace(
            getDefautLieuObservation=lambda lettre: "Roncevaux",
            getListeLieuxObservation=lambda lettre, date: ["Roncevaux", "Gérardmer"],
        ),
    )
    module = Soleil()
    module.dateDataset = "15/08/778"

    module.setup()

    assert module.visibiliteZeta == visibilite
    assert module.dateObservationJD is (date_decalee if visibilite == "Non visible" else date_segment)
    assert module.dateObservation.endswith(date_attendue)
    assert module.lieuObservation == "Roncevaux"
    assert module.getValeursLieuObservation() == ["Roncevaux", "Gérardmer"]


def test_soleil_calculer_expose_les_coordonnees_du_lieu(monkeypatch):
    monkeypatch.setattr(stylet, "villes_dict", {"Roncevaux": VilleFictive((43.02, -1.32))})
    module = Soleil()
    module.lieuObservation = "Roncevaux"

    module.calculer()

    assert module.coordObservation == pytest.approx((43.02, -1.32))


def test_carte_calculer_rotation_et_lever_zeta(monkeypatch):
    lever_soleil = DateFictive(texte="06:34:16")
    lever_zeta = DateFictive(texte="18:27:43")
    monkeypatch.setattr(stylet, "villes_dict", {"Strasbourg": VilleFictive((48.5, 7.7))})
    monkeypatch.setattr(stylet, "calculLeverSoleil", lambda *args: lever_soleil)
    monkeypatch.setattr(stylet, "positionSoleil", lambda *args: (0.0, 106.96))
    monkeypatch.setattr(stylet, "calculLeverAstre", lambda *args: lever_zeta)
    monkeypatch.setattr(stylet, "positionAstre", lambda *args: (0.0, 144.62))
    module = Carte()
    module.dateObservationJDSoleil = DateFictive()
    module.coordObservationSoleil = (43.02, -1.32)

    module.setup()
    module.calculer()

    assert module.heure == "06:34:16"
    assert module.azimut == pytest.approx(106.96)
    assert module.rotation == pytest.approx(-16.96)
    assert module.heureLeverZetaJD is lever_zeta
    assert module.heureLeverZeta == "18:27:43"
    assert module.azimutZeta == pytest.approx(144.62)


def test_planete_setup_choix_et_regles_locales():
    module = Planete()
    module.dateObservationJDSoleil = DateFictive(jour="Sam")
    module.heureLeverZetaJDCarte = DateFictive(jour="Sam")

    module.setup()

    assert module.nom == "Neptune"
    assert module.getValeursNom() == ["Neptune", "Lune"]
    assert module.getValeursSensCarte() == ["Endroit", "Envers"]
    assert module._regle_carte_toujours_endroit() == "Endroit"

    module.nom = "Neptune"
    assert module._regle_zeta_selon_planete() == "Endroit"
    module.nom = "Lune"
    assert module._regle_zeta_selon_planete() == "Envers"
    module.sensZeta = "Endroit"
    module.nom = "Saturne"
    assert module._regle_zeta_selon_planete() == "Endroit"


@pytest.mark.parametrize(
    ("sens_carte", "sens_zeta", "axe_attendu"),
    [
        ("Endroit", "Endroit", 140.0),
        ("Endroit", "Envers", 80.0),
        ("Envers", "Endroit", 280.0),
        ("Envers", "Envers", 220.0),
    ],
)
def test_planete_applique_les_sens_dans_laxe_final(monkeypatch, sens_carte, sens_zeta, axe_attendu):
    monkeypatch.setattr(stylet, "positionAstre", lambda *args: (20.0, 100.0))
    module = Planete()
    module.nom = "Neptune"
    module.coordObservationSoleil = (43.02, -1.32)
    module.heureLeverZetaJDCarte = DateFictive()
    module.azimutZetaCarte = 30.0
    module.rotationCarte = 10.0
    module.sensCarte = sens_carte
    module.sensZeta = sens_zeta

    module.calculer()

    assert module.hauteur == pytest.approx(20.0)
    assert module.axeFinal == pytest.approx(axe_attendu)


def test_planete_invisible_ne_produit_pas_daxe(monkeypatch):
    monkeypatch.setattr(stylet, "positionAstre", lambda *args: (0.0, 100.0))
    module = Planete()
    module.nom = "Neptune"
    module.coordObservationSoleil = (0.0, 0.0)
    module.heureLeverZetaJDCarte = DateFictive()

    module.calculer()

    assert module.axeFinal is None
    assert module.axeFinalCalcul == "La planète Neptune est invisible à cette heure"


def test_etoile_setup_choix_et_origine_bourges_exclue():
    module = Etoile()
    module.lettreObsSoleil = "C"
    module.lettreSegSoleil = "B"

    module.setup()

    assert (module.nom, module.origineTrait) == ("GammaMajor", "Gérardmer")
    assert module.getValeursNom() == ["GammaMajor", "AlphaMajor"]
    assert module.getValeursOrigineTrait() == ["Dieppe"]

    module.lettreObsSoleil = "B"
    module.setup()
    assert module.origineTrait == "Dieppe"


def test_etoile_regle_zeta_conserve_la_valeur_hors_choix():
    module = Etoile()
    module.lettreObsSoleil = "C"

    module.nom = "GammaMajor"
    assert module._regle_zeta_selon_etoile() == "Endroit"
    module.nom = "AlphaMajor"
    assert module._regle_zeta_selon_etoile() == "Envers"
    module.sensZeta = "Endroit"
    module.nom = "BetaMajor"
    assert module._regle_zeta_selon_etoile() == "Endroit"


@pytest.mark.parametrize(
    ("sens_carte", "sens_zeta", "axe_attendu"),
    [("Endroit", "Envers", 60.0), ("Envers", "Endroit", 300.0)],
)
def test_etoile_applique_les_sens_dans_laxe_final(monkeypatch, sens_carte, sens_zeta, axe_attendu):
    monkeypatch.setattr(stylet, "positionAstre", lambda *args: (42.0, 80.0))
    module = Etoile()
    module.nom = "AlphaMajor"
    module.coordObservationSoleil = (43.02, -1.32)
    module.heureLeverZetaJDCarte = DateFictive()
    module.azimutZetaCarte = 30.0
    module.rotationCarte = 10.0
    module.sensCarte = sens_carte
    module.sensZeta = sens_zeta

    module.calculer()

    assert module.axeFinal == pytest.approx(axe_attendu)


def test_etoile_invisible_ne_produit_pas_daxe(monkeypatch):
    monkeypatch.setattr(stylet, "positionAstre", lambda *args: (-1.0, 80.0))
    module = Etoile()
    module.nom = "AlphaMajor"
    module.coordObservationSoleil = (0.0, 0.0)
    module.heureLeverZetaJDCarte = DateFictive()

    module.calculer()

    assert module.axeFinal is None
    assert module.axeFinalCalcul == "L'étoile AlphaMajor est invisible à cette heure"


class PointGeometrieFictive:
    visible = True

    def __init__(self, *args):
        if len(args) == 1:
            self.coordonnees = args[0].coordonnees
        else:
            self.coordonnees = args[1:]

    def coordonneesPixelAbs(self):
        return self.coordonnees

    def estVisibledansImage(self):
        return self.visible


class LigneGeometrieFictive:
    @staticmethod
    def depuisPointEtAzimut(point, azimut):
        return LigneGeometrieFictive()

    def intersection(self, autre):
        return 10.0, 20.0

    @staticmethod
    def barycentreTriangle(*lignes):
        return 15.0, 25.0


class SentinelleCandidatFictive:
    def __init__(self, chemin):
        self.resultat = (True, "09:42", "AM", 12.0, 175.47)
        self.inclure_lampouy = None

    def surLigneHoraire(self, x, y, inclure_lampouy):
        self.inclure_lampouy = inclure_lampouy
        return self.resultat

    def getOrigineStylet(self):
        return PointGeometrieFictive(VilleFictive((5.0, 5.0)))


def installer_geometrie_candidat(monkeypatch, visible=True):
    PointGeometrieFictive.visible = visible
    monkeypatch.setattr(stylet, "PointGraphique", PointGeometrieFictive)
    monkeypatch.setattr(stylet, "Ligne", LigneGeometrieFictive)
    monkeypatch.setattr(stylet, "Sentinelle", SentinelleCandidatFictive)
    monkeypatch.setattr(stylet, "carteConfig", SimpleNamespace(pixels_to_lambert93=lambda x, y: (x, y)))
    monkeypatch.setattr(
        stylet,
        "villes_dict",
        {"Bourges": VilleFictive((1.0, 1.0)), "Gérardmer": VilleFictive((2.0, 2.0))},
    )


def candidat_pret():
    module = Candidats()
    module.axeFinalPlanete = 213.98
    module.axeFinalEtoile = 228.68
    module.origineTraitEtoile = "Gérardmer"
    return module


def test_candidats_signale_un_axe_manquant():
    module = Candidats.__new__(Candidats)
    module.axeFinalPlanete = None
    module.axeFinalEtoile = 228.68

    module.calculer()

    assert module.selection == "L'un des axes est manquant"


def test_candidats_signale_lintersection_hors_image(monkeypatch):
    installer_geometrie_candidat(monkeypatch, visible=False)
    module = candidat_pret()

    module.calculer()

    assert module.selection == "Point non visile"


def test_candidats_signale_une_ligne_horaire_trop_lointaine(monkeypatch):
    installer_geometrie_candidat(monkeypatch)
    module = candidat_pret()
    module.sentinelle.resultat = (False, "09:42", "AM", 21.0, 175.47)

    module.calculer()

    assert module.selection == "Trop loin d'une ligne horaire"


@pytest.mark.parametrize(("date", "inclure_lampouy"), [("15/08/778", False), ("18/05/1152", True)])
def test_candidats_valide_le_point_et_transmet_la_regle_lampouy(monkeypatch, date, inclure_lampouy):
    installer_geometrie_candidat(monkeypatch)
    module = candidat_pret()
    module.dateDataset = date

    module.calculer()

    assert module.selection == "Sélectionné"
    assert (module.heureSentinelle, module.ampm, module.distKM, module.azimutHeure) == (
        "09:42",
        "AM",
        12.0,
        175.47,
    )
    assert module.sentinelle.inclure_lampouy is inclure_lampouy
    assert isinstance(module.pointIntersection, PointGeometrieFictive)


@pytest.mark.parametrize(
    ("selection", "heure", "ampm", "attendu"),
    [
        ("Sélectionné", "09:42", "AM", ("09:42", "AM")),
        ("Trop loin d'une ligne horaire", "09:42", "AM", ("", "")),
    ],
)
def test_sentinelle_algo_propage_ou_efface_letat_du_candidat(monkeypatch, selection, heure, ampm, attendu):
    monkeypatch.setattr(stylet, "Sentinelle", SentinelleCandidatFictive)
    module = SentinelleAlgo()
    module.selectionCandidats = selection
    module.heureSentinelleCandidats = heure
    module.ampmCandidats = ampm

    module.calculer()

    assert (module.heure, module.sensCadran) == attendu
