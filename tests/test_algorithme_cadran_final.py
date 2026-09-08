import math
from types import SimpleNamespace

import pytest

import src.AlgorithmeCadranFinal as cadran
from src.AlgorithmeCadranFinal import CandidatFinal, LigneHoraireFinal, LumiereFinal, Segment, StyletFinal


class DateFictive:
    def __init__(self, lettre="C"):
        self.lettre = lettre

    def lettreDominicale(self):
        return self.lettre


class VilleFictive:
    def __init__(self, coordonnees=(43.0, -1.3), pixels=(10.0, 20.0)):
        self.coordonnees = coordonnees
        self.pixels = pixels

    def getCoordonneesGPS(self):
        return self.coordonnees

    def getCoordonneesPixel(self):
        return self.pixels


class PointFictif:
    def __init__(self, ville, *args, **kwargs):
        self.ville = ville

    def distance(self, autre):
        return 100.0


class LigneFictive:
    def __init__(self, *args):
        self.args = args

    def azimut(self):
        return 13.56


class LigneAzimutFictive:
    def __init__(self, point, azimut, *args, **kwargs):
        self.point = point
        self.azimut = azimut



class SentinelleFictive(dict):
    def __init__(self):
        super().__init__(
            {
                "C": {"HeureLocale": "09:42", "AzimutCalibre": 128.5},
                "B": {"HeureLocale": "11:38", "AzimutCalibre": 170.0},
                "E": {"HeureLocale": "08:01", "AzimutCalibre": 104.0},
                "F": {"HeureLocale": "10:25", "AzimutCalibre": 142.0},
                "G": {"HeureLocale": "12:00", "AzimutCalibre": 179.0},
                "A": {"HeureLocale": "11:42", "AzimutCalibre": 171.5},
                "D": {"HeureLocale": "08:12", "AzimutCalibre": 106.5},
                "J": {"HeureLocale": "10:56", "AzimutCalibre": 153.0},
                "L": {"HeureLocale": "10:09", "AzimutCalibre": 138.5},
            }
        )


def villes_fictives():
    return {
        "Roncevaux": VilleFictive((43.0, -1.3)),
        "Bourges": VilleFictive((47.0, 2.0)),
        "Metz": VilleFictive(),
        "Saint-Amour": VilleFictive(),
        "Rocamadour": VilleFictive(),
        "Carnac": VilleFictive((47.6, -3.0)),
    }


def test_segment_initialise_la_lettre_et_le_lieu(monkeypatch):
    monkeypatch.setattr(cadran, "MyJulianDate", SimpleNamespace(fromString=lambda valeur: DateFictive("C")))
    monkeypatch.setattr(
        cadran,
        "LieuxObservation",
        SimpleNamespace(
            getDefautLieuObservation=lambda lettre: "Roncevaux",
            getListeLieuxObservation=lambda lettre, date: ["Roncevaux", "Gérardmer"],
        ),
    )
    module = Segment()
    module.dateDataset = "15/08/778"

    module.setup()

    assert (module.lettreDom, module.choixCalendrier, module.lieuObservation) == ("C", "Standard", "Roncevaux")
    assert module.getValeursLieuObservation() == ["Roncevaux", "Gérardmer"]


@pytest.mark.parametrize(
    ("base", "calendrier", "choix", "octave", "base_attendue", "lettre_attendue", "facteur"),
    [
        ("Base 1", "Standard", "=", "x1", "Saint-Amour", "C", 1.0),
        ("Base 2", "Standard", "+2", "x2", "Rocamadour", "E", 2.0),
        ("Base 2", "Déclinaison", "-2", "x4", "Rocamadour", "D", 4.0),
        ("Base 1", "Déclinaison", "Clef", "/2", "Saint-Amour", "C", 0.5),
        ("Base 1", "Standard", "=", "/4", "Saint-Amour", "C", 0.25),
        ("Base 1", "Standard", "=", "/8", "Saint-Amour", "C", 0.125),
    ],
)
def test_stylet_final_choisit_base_note_octave_et_axe(monkeypatch, base, calendrier, choix, octave, base_attendue, lettre_attendue, facteur):
    monkeypatch.setattr(cadran, "villes_dict", villes_fictives())
    monkeypatch.setattr(cadran, "PointGraphique", PointFictif)
    monkeypatch.setattr(cadran, "Ligne", LigneFictive)
    module = StyletFinal()
    module.styletDataset = "Roncevaux"
    module.base1Dataset = "Saint-Amour"
    module.base2Dataset = "Rocamadour"
    module.lettreDomSegment = "C"
    module.lettreDeclDataset = "F"
    module.choixBase = base
    module.choixCalendrier = calendrier
    module.P2M2 = choix
    module.octave = octave

    module.setup()
    module.calculer()

    hauteur_base = 100.0 / StyletFinal.tableauGamme["F"] * StyletFinal.tableauGamme[lettre_attendue]
    assert module.getValeursChoixBase() == ("Base 1", "Base 2")
    assert module.getValeursP2M2() == ("=", "+2", "-2", "Clef")
    assert module.getValeursOctave() == ("x1", "x2", "x4", "/2", "/4", "/8")
    assert module.getValeursChoixCalendrier() == ["Standard", "Déclinaison"]
    assert (module.base, module.lettreChoix, module.lettre) == (base_attendue, "C" if calendrier == "Standard" else "F", lettre_attendue)
    assert module.distanceRef == pytest.approx(100.0)
    assert module.hauteur == pytest.approx(facteur * hauteur_base)
    assert module.azimutMidi == pytest.approx(13.56)


@pytest.mark.parametrize(
    ("calendrier_stylet", "regle_attendue"), [("Standard", "Déclinaison"), ("Déclinaison", "Standard")],
)
@pytest.mark.slow
def test_lumiere_final_inverse_le_calendrier_du_stylet(calendrier_stylet, regle_attendue):
    module = LumiereFinal()
    module.choixCalendrierStylet = calendrier_stylet

    assert module.getValeursChoixCalendrier() == ["Standard", "Déclinaison"]
    assert module.getValeursHeureAMPM() == ["AM", "PM"]
    assert module._regleChoixCalendrier() == regle_attendue


@pytest.mark.parametrize(
    ("choix", "ampm", "heure_attendue"),
    [("=", "AM", "09:42"), ("+2", "PM", "15:59"), ("-2", "AM", "11:42"), ("Clef", "AM", "10:25"), ("11:00", "AM", "10:56")],
)
@pytest.mark.slow
def test_lumiere_final_applique_substitution_ampm_utc_et_distance(monkeypatch, choix, ampm, heure_attendue):
    monkeypatch.setattr(cadran, "villes_dict", villes_fictives())
    monkeypatch.setattr(cadran, "convertirHeureLocaleVersUTC", lambda heure, lon: f"UTC {heure}")
    monkeypatch.setattr(cadran, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(cadran, "positionSoleil", lambda *args: (45.0, 263.21))
    module = LumiereFinal()
    module.sentinelle = SentinelleFictive()
    module.lieuObservationSegment = "Roncevaux"
    module.lettreDomSegment = "C"
    module.lettreDeclDataset = "F"
    module.dateSegmentDataset = "25/07/778"
    module.hauteurStylet = 100.0
    module.choixCalendrier = "Standard"
    module.choixHeure = choix
    module.heureAMPM = ampm

    module.calculer()

    assert module.getValeursChoixHeure() == ["=", "+2", "-2", "Clef", "11:00"]
    assert module.lettreChoix == "C"
    assert module.heureLocale == heure_attendue
    assert module.heureUTC == f"UTC {heure_attendue}"
    assert module.deltaMidi == pytest.approx(-83.21)
    assert module.distance == pytest.approx(100.0)


@pytest.mark.parametrize(
    ("ampm", "calendrier", "sens_attendu", "calendrier_attendu"),
    [("AM", "Standard", "Endroit", "Déclinaison"), ("PM", "Déclinaison", "Envers", "Standard")],
)
def test_ligne_horaire_final_regles_et_sens_azimut(monkeypatch, ampm, calendrier, sens_attendu, calendrier_attendu):
    monkeypatch.setattr(cadran, "villes_dict", villes_fictives())
    monkeypatch.setattr(cadran, "PointGraphique", PointFictif)
    monkeypatch.setattr(cadran, "LigneAzimut", LigneAzimutFictive)
    monkeypatch.setattr(cadran, "convertirHeureLocaleVersUTC", lambda heure, lon: "UTC midi")
    monkeypatch.setattr(cadran, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(cadran, "positionSoleil", lambda *args: (0.0, 177.91))
    module = LigneHoraireFinal()
    module.sentinelleLumiere = SentinelleFictive()
    module.lieuObservationSegment = "Roncevaux"
    module.lettreDomSegment = "C"
    module.lettreDeclDataset = "F"
    module.dateSegmentDataset = "25/07/778"
    module.azimutMidiStylet = 13.56
    module.baseStylet = "Rocamadour"
    module.heureAMPMLumiere = ampm
    module.choixCalendrierLumiere = calendrier
    module.choixCalendrier = "Standard"
    module.choixHeure = "="
    module.sensCarte = sens_attendu

    module.calculer()

    assert module.getValeursChoixCalendrier() == ["Standard", "Déclinaison"]
    assert module.getValeursChoixHeure() == ["=", "+2", "-2", "Clef", "11:00"]
    assert module.getValeursSensCarte() == ["Endroit", "Envers"]
    assert module._regleSensCarte() == sens_attendu
    assert module._regleChoixCalendrier() == calendrier_attendu
    assert module.azimutMidiLocale == pytest.approx(177.91)
    assert len(module.listeLigneHoraire) == 16
    assert module.listeCandidatsHeure[0][0] == "09:42"
    assert module.listeCandidatsHeure[1][0] == "14:18"
    premier_delta = module.listeLigneHoraire[0][1]
    assert premier_delta == pytest.approx(-49.41 if sens_attendu == "Endroit" else -53.59, abs=0.01)


class PointCandidatFictif:
    visible = True

    def __init__(self, nom="point", x=0.0, y=0.0):
        self.nom = nom
        self.x = x
        self.y = y

    def coordonneesLambert(self):
        return self.x, self.y

    def distance(self, autre):
        return math.hypot(self.x - autre.x, self.y - autre.y)

    def estVisibledansImage(self):
        return self.visible


class CercleCandidatFictif:
    def __init__(self, *args, **kwargs):
        pass


class LigneLumiereFictive:
    points = []

    def __init__(self, *args, **kwargs):
        pass

    def intersectionCercle(self, cercle):
        return self.points


class LigneHeureFictive:
    def __init__(self, points, intersection):
        self.points = points
        self.intersection = intersection

    def intersectionCercle(self, cercle):
        return self.points

    def intersectionLigne(self, ligne):
        return self.intersection


def preparer_candidat_final(monkeypatch, points_lumiere, points_heure, intersection, visible=True):
    PointCandidatFictif.visible = visible
    LigneLumiereFictive.points = points_lumiere
    monkeypatch.setattr(cadran, "PointGraphique", PointCandidatFictif)
    monkeypatch.setattr(cadran, "CercleGraphique", CercleCandidatFictif)
    monkeypatch.setattr(cadran, "LigneAzimut", LigneLumiereFictive)
    monkeypatch.setattr(cadran, "villes_dict", {"Bourges": VilleFictive()})
    module = CandidatFinal()
    module.azimutMidiStylet = 10.0
    module.azimutLumiere = 200.0
    module.distanceLumiere = 100.0
    module.listeCandidatsHeureOmbre = [("09:42", LigneHeureFictive(points_heure, intersection))]
    return module


def test_candidat_final_cree_un_barycentre_a_trois_points(monkeypatch):
    module = preparer_candidat_final(
        monkeypatch,
        [PointCandidatFictif("p1", 0.0, 0.0)],
        [PointCandidatFictif("p2", 3.0, 0.0)],
        (0.0, 3.0),
    )

    objets = module.construireRepresentationCarte()

    assert len(objets) == 2


@pytest.mark.parametrize(("distance", "visible", "nombre_attendu"), [(8.0, False, 2), (11.0, False, 0)])
def test_candidat_final_fallback_parallelisme_et_point_hors_image(monkeypatch, distance, visible, nombre_attendu):
    module = preparer_candidat_final(
        monkeypatch,
        [PointCandidatFictif("p1", 0.0, 0.0)],
        [PointCandidatFictif("p2", distance, 0.0)],
        (0.0, 3.0),
        visible=visible,
    )

    objets = module.construireRepresentationCarte()

    assert len(objets) == nombre_attendu
