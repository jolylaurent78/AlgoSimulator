import math
from types import SimpleNamespace

import pytest

import src.AlgorithmeLumiereStyletInitial as lumiere
from src.AlgorithmeLumiereStyletInitial import HeureDateObservation, Observation, Soleil, Stylet


class DateFictive:
    def __init__(self, lettre="C", texte="04:24:04"):
        self.lettre = lettre
        self.texte = texte

    def lettreDominicale(self):
        return self.lettre

    def toString(self, format_date):
        return self.texte


class VilleFictive:
    def __init__(self, coordonnees=(43.0, -1.3), pixels=(10.0, 20.0)):
        self.coordonnees = coordonnees
        self.pixels = pixels

    def getCoordonneesGPS(self):
        return self.coordonnees


class PointFictif:
    def __init__(self, ville):
        self.ville = ville

    def coordonneesPixelAbs(self):
        return self.ville.pixels

    def distance(self, autre):
        return 100.0


class SentinelleHeureFictive(dict):
    def __init__(self, chemin):
        super().__init__(
            {
                "C": {"HeureLocale": "09:42"},
                "B": {"HeureLocale": "10:20"},
                "D": {"HeureLocale": "10:10"},
                "E": {"HeureLocale": "11:20"},
                "F": {"HeureLocale": "12:20"},
                "J": {"HeureLocale": "11:00"},
                "L": {"HeureLocale": "08:10"},
            }
        )


def test_observation_initialise_lettre_lieu_et_rotation(monkeypatch):
    date = DateFictive(lettre="C")
    monkeypatch.setattr(lumiere, "MyJulianDate", SimpleNamespace(fromString=lambda valeur: date))
    monkeypatch.setattr(lumiere, "villes_dict", {"Strasbourg": VilleFictive((48.5, 7.7))})
    monkeypatch.setattr(lumiere, "calculLeverSoleil", lambda *args: DateFictive(texte="04:24:04"))
    monkeypatch.setattr(lumiere, "positionSoleil", lambda *args: (0.0, 68.74))
    monkeypatch.setattr(
        lumiere,
        "LieuxObservation",
        SimpleNamespace(
            getDefautLieuObservation=lambda lettre: "Roncevaux",
            getListeLieuxObservation=lambda lettre, date: ["Roncevaux", "Gérardmer"],
        ),
    )
    module = Observation()
    module.dateDataset = "15/08/778"

    module.setup()

    assert module.lettreDom == "C"
    assert module.lieuObservation == "Roncevaux"
    assert module.heureLeverSoleilStrasbourg == "04:24:04"
    assert module.azimutLeverSoleil == pytest.approx(68.74)
    assert module.rotationCarte == pytest.approx(21.26)
    assert module.getValeursLieuObservation() == ["Roncevaux", "Gérardmer"]


@pytest.mark.parametrize(
    ("calendrier", "choix", "ampm", "attendu"),
    [
        ("Standard", "=", "AM", ("C", "09:42")),
        ("Standard", "+2", "AM", ("C", "11:20")),
        ("Déclinaison", "-2", "AM", ("F", "10:10")),
        ("Standard", "Clef", "PM", ("C", "11:40")),
        ("Déclinaison", "11:00", "PM", ("F", "13:00")),
    ],
)
def test_heure_date_applique_calendrier_choix_et_ampm(monkeypatch, calendrier, choix, ampm, attendu):
    monkeypatch.setattr(lumiere, "Sentinelle", SentinelleHeureFictive)
    module = HeureDateObservation()
    module.lettreDomObservation = "C"
    module.lettreDeclDataset = "F"
    module.choixCalendrier = calendrier
    module.choixHeure = choix
    module.heureAMPM = ampm

    module.calculer()

    assert (module.lettreChoix, module.heureLocale) == attendu


class SentinelleStyletFictive(SentinelleHeureFictive):
    def __init__(self, chemin):
        super().__init__(chemin)
        self.resultat = (True, "09:42", "AM", 12.0, 175.47)

    def surLigneHoraire(self, x, y):
        return self.resultat


def installer_soleil_fictif(monkeypatch):
    monkeypatch.setattr(lumiere, "Sentinelle", SentinelleStyletFictive)
    monkeypatch.setattr(lumiere, "PointGraphique", PointFictif)
    monkeypatch.setattr(
        lumiere,
        "villes_dict",
        {"Roncevaux": VilleFictive((43.0, -1.3)), "Bourges": VilleFictive((47.0, 2.0))},
    )
    monkeypatch.setattr(lumiere, "convertirHeureLocaleVersUTC", lambda heure, lon: f"UTC {heure}")


@pytest.mark.parametrize(
    ("ampm", "choix", "attendue"),
    [("AM", "Même heure", "09:42"), ("AM", "Symétrique", "14:18"), ("PM", "Même heure", "14:18")],
)
def test_soleil_utilise_lheure_stylet_ou_sa_symetrique(monkeypatch, ampm, choix, attendue):
    installer_soleil_fictif(monkeypatch)
    module = Soleil()
    module.stylet = "Roncevaux"
    module.choixHeure = choix
    module.lieuObservationObservation = "Roncevaux"
    module.heureLocaleHeuredate = "11:20"
    module.sentinelle.resultat = (True, "09:42", ampm, 12.0, 175.47)

    module.calculer()

    assert module.validite == "Valide"
    assert module.heureSentinelle == attendue
    assert module.heureObservation == attendue
    assert module.heureUTC == f"UTC {attendue}"


def test_soleil_source_manuelle_et_point_invalide(monkeypatch):
    installer_soleil_fictif(monkeypatch)
    module = Soleil()
    module.stylet = "Roncevaux"
    module.lieuObservationObservation = "Roncevaux"
    module.heureLocaleHeuredate = "11:20"
    module.sourceHeure = "Manuel"
    module._sourceHeureInitiale = False
    module.sentinelle.resultat = (False, None, None, None, None)

    module.calculer()

    assert module.validite == "Unvalide"
    assert module.heureSentinelle is None
    assert module.heureObservation == "11:20"
    assert module.heureUTC == "UTC 11:20"


def preparer_stylet(monkeypatch):
    monkeypatch.setattr(lumiere, "PointGraphique", PointFictif)
    monkeypatch.setattr(
        lumiere,
        "villes_dict",
        {
            "Metz": VilleFictive(),
            "Roncevaux": VilleFictive((43.0, -1.3)),
        },
    )
    monkeypatch.setattr(lumiere, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(lumiere, "positionSoleil", lambda *args: (45.0, 120.0))
    module = Stylet()
    module.setup()
    module.dateDataset = "15/08/778"
    module.lettreDomObservation = "C"
    module.lieuObservationObservation = "Roncevaux"
    module.rotationCarteObservation = 10.0
    module.styletSoleil = "Roncevaux"
    module.heureUTCSoleil = "09:47:18"
    return module


@pytest.mark.parametrize(
    ("octave", "facteur"),
    [("x1", 1.0), ("x2", 2.0), ("/2", 0.5), ("/4", 0.25), ("/8", 0.125)],
)
def test_stylet_applique_la_formule_de_hauteur_et_les_octaves(monkeypatch, octave, facteur):
    module = preparer_stylet(monkeypatch)
    module.octave = octave

    module.calculer()

    hauteur_attendue = 100.0 / 2 ** (-5 / 12) * 2 ** (-12 / 12)
    assert module.hauteurStylet == pytest.approx(hauteur_attendue)
    assert module.distanceStylet == pytest.approx(facteur * hauteur_attendue)
    assert module.formuleDistance == "100 / 2**-5/12 * 2**-12/12"


@pytest.mark.parametrize(
    ("sens", "axe", "formule"),
    [("Endroit", 130.0, "120.00+10.00"), ("Envers", 230.0, "360-120.00-10.00")],
)
def test_stylet_applique_le_sens_de_carte_a_laxe(monkeypatch, sens, axe, formule):
    module = preparer_stylet(monkeypatch)
    module.sensCarte = sens

    module.calculer()

    assert module.hauteurSoleil == pytest.approx(45.0)
    assert module.azimutSoleil == pytest.approx(120.0)
    assert module.axeCarte == pytest.approx(axe)
    assert module.formuleAxeCarte == formule
    assert module.getValeursOctave() == ("x1", "x2", "/2", "/4", "/8")


def test_stylet_sans_heure_utc_reinitialise_les_resultats_dependants():
    module = Stylet()
    module.heureUTCSoleil = None
    module.distanceMetz = 123.0
    module.hauteurStylet = 45.0
    module.formuleAxeCarte = "ancienne formule"

    module.calculer()

    assert (module.distanceMetz, module.hauteurStylet, module.formuleAxeCarte) == (None, None, None)
