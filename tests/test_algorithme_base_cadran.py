from types import SimpleNamespace

import pytest

import src.AlgorithmeBaseCadran as base_cadran
from src.CadranNationalSentinelles import SentinelleNationale
from src.AlgorithmeBaseCadran import CandidatBase, CercleDistance, CercleHoraire, Partition, Segment


def test_ancien_choix_lampouy_base_charge_sans_dependre_azimut(tmp_path):
    import json
    from src.ProjectPersistence import _restaurer_parametres_scenario
    module=CercleHoraire.__new__(CercleHoraire)
    module.dateDataset='18/05/1152';module.heureSubstitution='='
    scenario=SimpleNamespace(nom='Le Goulet',modules={'cercleHoraire':module})
    fichier=tmp_path/'ancien.json'
    for ancien in ('138.5°','138°','138.0°'):
        fichier.write_text(json.dumps({'cercleHoraire':{'heureSubstitution':ancien}}),encoding='utf-8')
        avant=fichier.read_bytes()
        _restaurer_parametres_scenario(scenario,json.loads(fichier.read_text(encoding='utf-8')))
        assert module.heureSubstitution=='Lampouy'
        assert module.getValeursHeureSubstitution()==['=','+2','-2','Clef','Clef 2','11:00','Lampouy']
        assert fichier.read_bytes()==avant
    assert base_cadran.normaliserSubstitutionLampouy('138.5°','20/03/1815')=='138.5°'


def test_sauvegarde_substitution_lampouy_base_sans_azimut(tmp_path,monkeypatch):
    import json
    import src.ProjectPersistence as persistance
    module=CercleHoraire.__new__(CercleHoraire)
    module.dateDataset='18/05/1152';module.heureSubstitution='='
    scenario=SimpleNamespace(nom='Le Goulet',modules={'cercleHoraire':module})
    persistance._restaurer_parametres_scenario(scenario,{'cercleHoraire':{'heureSubstitution':'138.5°'}})
    monkeypatch.setattr(persistance,'construireSnapshotProjetJsonV1',lambda *args:
        {'parameters':persistance._snapshot_parametres_scenario(scenario,[('cercleHoraire','heureSubstitution')])})
    sortie=tmp_path/'nouveau.json'
    persistance.sauvegarderProjetJsonV1(sortie,None,None)
    assert json.loads(sortie.read_text(encoding='utf-8'))['parameters']=={
        'cercleHoraire':{'heureSubstitution':'Lampouy'}}


def test_substitution_lampouy_base_relit_azimut_au_recalcul(tmp_path,monkeypatch):
    from unittest.mock import Mock
    from src.ReferentielSentinelles import HeureMoyenneLocale
    installer_geometrie_base(monkeypatch)
    fichier=tmp_path/'sentinelle.csv'
    entete='Nom,Note,Azimut,AzimutGeant,Ville\n'
    fichier.write_text(entete+'Lampouy,L,138,139,\n',encoding='utf-8')
    reference=SimpleNamespace(chemin_csv=fichier,rechercherLigneHoraire=lambda *_:
        SimpleNamespace(heure_locale=HeureMoyenneLocale(32400.),ampm='AM'))
    monkeypatch.setattr(base_cadran,'Sentinelle',lambda *_:reference)
    monkeypatch.setattr(base_cadran,'positionSoleil',Mock(side_effect=AssertionError('Aucun DE406 pour cette substitution')))
    module=CercleHoraire()
    module.dateDataset='18/05/1152';module.styletDataset='Roncevaux'
    module.heureSubstitution='Lampouy'
    module.heureSentinelle='09:00:00';module.heureSentinelleSecondes=32400.
    module.calculer()
    assert module.azimutSoleil==138. and module.angleHoraire==42.
    fichier.write_text(entete+'Lampouy,L,137,139,\n',encoding='utf-8')
    module.calculer()
    assert module.heureSubstitution=='Lampouy' and module.noteHoraire=='L'
    assert module.azimutSoleil==137. and module.angleHoraire==43.
    assert module.heureSentinelleSecondes==32400.
    module.heureAMPM='PM';module.calculer()
    assert module.angleHoraire==-43. and module.heureSentinelleSecondes==32400.


class DateFictive:
    def __init__(self, lettre="C", texte="04:48:38"):
        self.lettre = lettre
        self.texte = texte

    def lettreDominicale(self):
        return self.lettre

    def toString(self, format_date):
        return self.texte

    def __add__(self, valeur):
        return DateFictive(self.lettre, "10:43:20")


class VilleFictive:
    def __init__(self, coordonnees=(47.0, 2.0), pixels=(10.0, 20.0)):
        self.coordonnees = coordonnees
        self.pixels = pixels

    def getCoordonneesGPS(self):
        return self.coordonnees


class PointFictif:
    def __init__(self, *args, **kwargs):
        self.nom = args[0] if args and isinstance(args[0], str) else "point"
        self.ville = args[0] if args and not isinstance(args[0], str) else None
        self.pixels = self.ville.pixels if self.ville else tuple(args[1:]) or (0.0, 0.0)

    @staticmethod
    def depuisDeuxPoints(point1, point2, nom=None):
        return PointFictif("centre", 0.0, 0.0)

    def coordonneesPixelAbs(self):
        return self.pixels

    def coordonneesLambert(self):
        return self.pixels

    def distance(self, autre):
        return 100.0


class LigneFictive:
    def __init__(self, *args, **kwargs):
        self.azimut = kwargs.get("azimut", 100.0)

    def getAzimutCarte(self):
        return self.azimut

    def pointsLateraux(self, centre, longueur):
        return PointFictif("p1", 1.0, 1.0), PointFictif("p2", 2.0, 2.0)

    def pointsEquidistants(self, point, distance):
        return PointFictif("nord"), PointFictif("sud")


class LigneAzimutFictive(LigneFictive):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.azimut = args[1] if len(args) > 1 else kwargs.get("azimut", 0.0)


class CercleFictif:
    def __init__(self, centre=None, rayon=None):
        self.centre = centre or PointFictif("centre")
        self.rayon = rayon or 100.0

    @classmethod
    def depuisTroisPoints(cls, *points, **kwargs):
        return cls()

    def getCentre(self):
        return self.centre

    def getRayonKm(self):
        return self.rayon

    def intersectionLigne(self, ligne):
        return [PointFictif("intersection")]


class SentinelleFictive(dict):
    def __init__(self, chemin):
        super().__init__(
            {
                "F": {"HeureLocale": "10:00"},
                "D": {"HeureLocale": "10:10"},
                "A": {"HeureLocale": "10:25"},
                "C": {"HeureLocale": "10:40"},
                "J": {"HeureLocale": "11:00"},
                "L": {"HeureLocale": "08:10", "AzimutCalibre": 42.0},
            }
        )

    def surLigneHoraire(self, x, y):
        return True, "09:42", "AM", 12.0, 175.47


def villes_fictives():
    return {
        "Bourges": VilleFictive(),
        "Roncevaux": VilleFictive((43.0, -1.3)),
        "Carnac": VilleFictive((47.6, -3.0)),
        "Carignan": VilleFictive(),
        "Metz": VilleFictive(),
    }


def installer_geometrie_base(monkeypatch):
    monkeypatch.setattr(base_cadran, "villes_dict", villes_fictives())
    monkeypatch.setattr(base_cadran, "PointGraphique", PointFictif)
    monkeypatch.setattr(base_cadran, "LigneEntreVilles", LigneFictive)
    monkeypatch.setattr(base_cadran, "LigneAzimut", LigneAzimutFictive)
    monkeypatch.setattr(base_cadran, "CercleGraphique", CercleFictif)


def test_segment_setup_et_calendrier_standard_ou_declinaison(monkeypatch):
    date = DateFictive(lettre="C")
    monkeypatch.setattr(base_cadran, "MyJulianDate", SimpleNamespace(fromString=lambda valeur: date))
    module = Segment()
    module.dateDataset = "15/08/778"
    module.lettreDeclDataset = "F"

    module.setup()
    assert module.dateSegmentJD is date
    assert module.getValeursChoixCalendrier() == ["Standard", "Déclinaison"]
    assert (module.lettreDom, module.lettreChoix, module.choixCalendrier) == ("C", "C", "Standard")

    module.calculer()
    assert module.lettreChoix == "C"
    module.choixCalendrier = "Déclinaison"
    module.calculer()
    assert module.lettreChoix == "F"


@pytest.mark.parametrize(
    ("substitution", "ampm", "heure_attendue", "angle_attendu"),
    [
        ("=", "AM", "10:25:04", 40.0),
        ("+2", "AM", "11:42:00", 40.0),
        ("-2", "AM", "08:14:46", 40.0),
        ("11:00", "AM", "10:56:00", 40.0),
        ("=", "PM", "13:34:56", 40.0),
    ],
)
def test_cercle_horaire_applique_substitution_ampm_et_signe(monkeypatch, substitution, ampm, heure_attendue, angle_attendu):
    installer_geometrie_base(monkeypatch)
    sentinelle = SentinelleNationale()
    monkeypatch.setattr(base_cadran, "Sentinelle", lambda *_: sentinelle)
    monkeypatch.setattr(base_cadran, "convertirHeureLocaleVersUTC", lambda heure, longitude: f"UTC {heure}")
    monkeypatch.setattr(base_cadran, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(base_cadran, "positionSoleil", lambda *args: (0.0, 140.0 if ampm == "AM" else 220.0))
    module = CercleHoraire()
    module.styletDataset = "Roncevaux"
    module.lettreChoixSegment = "F"
    module.dateDataset = "15/08/778"
    module.choixCalendrierSegment = "Déclinaison"
    module.heureSubstitution = substitution
    module.heureAMPM = ampm

    module.calculer()

    assert module.getValeursHeureAMPM() == ["AM", "PM"]
    assert module.getValeursCercleAMPM() == ["AM", "PM"]
    assert module.getValeursHeureSubstitution() == ["=", "+2", "-2", "Clef", "Clef 2", "11:00"]
    assert module.heureSentinelle == heure_attendue
    assert module.angleHoraire == pytest.approx(angle_attendu)


@pytest.mark.parametrize(
    ("symetrie", "notes_attendues"),
    [
        ("Flip vertical", ["A", "F", "A", "F"]),
        ("Flip horizontal", ["A", "F", "F", "A"]),
    ],
)
def test_partition_repartit_les_notes_selon_la_symetrie(monkeypatch, symetrie, notes_attendues):
    installer_geometrie_base(monkeypatch)
    monkeypatch.setattr(base_cadran, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(base_cadran, "calculLeverSoleil", lambda *args: DateFictive(texte="04:48:38"))
    monkeypatch.setattr(base_cadran, "convertirHeureLocaleVersUTC", lambda heure, longitude, inverse=False: "10:55:39" if not inverse else "04:43:20")
    monkeypatch.setattr(base_cadran, "positionSoleil", lambda *args: (0.0, 143.02))
    module = Partition()
    module.pointBourges = PointFictif(villes_fictives()["Bourges"])
    module.styletCerclehoraire = "Roncevaux"
    module.coordPointChoixCerclehoraire = (1.0, 2.0)
    module.dateSegmentDataset = "25/07/778"
    module.lettreChoixSegment = "F"
    module.lieuObservation = "Roncevaux"
    module.P2M2 = "+2"
    module.typeSymetrie = symetrie

    module.calculer()

    assert module.getValeursP2M2() == ("=", "+2", "-2", "Clef", "Clef 2")
    assert module.getValeursTypeSymetrie() == ("Flip vertical", "Flip horizontal")
    assert module.lettrePartition == "A"
    assert [nom for _, nom in module.listeNotesPartition[:4]] == notes_attendues
    assert module.candidats


@pytest.mark.parametrize(("choix", "lettre"), [("=", "F"), ("+2", "A"), ("-2", "D"), ("Clef", "C")])
def test_partition_associe_la_note_de_partition_au_choix(monkeypatch, choix, lettre):
    installer_geometrie_base(monkeypatch)
    monkeypatch.setattr(base_cadran, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(base_cadran, "calculLeverSoleil", lambda *args: DateFictive())
    monkeypatch.setattr(base_cadran, "convertirHeureLocaleVersUTC", lambda *args, **kwargs: "10:00")
    monkeypatch.setattr(base_cadran, "positionSoleil", lambda *args: (0.0, 143.0))
    module = Partition()
    module.pointBourges = PointFictif(villes_fictives()["Bourges"])
    module.styletCerclehoraire = "Roncevaux"
    module.coordPointChoixCerclehoraire = (1.0, 2.0)
    module.dateSegmentDataset = "25/07/778"
    module.lettreChoixSegment = "F"
    module.lieuObservation = "Roncevaux"
    module.P2M2 = choix

    module.calculer()

    assert module.lettrePartition == lettre


@pytest.mark.parametrize(
    ("centre", "octave", "heure_attendue", "facteur"),
    [("Ouverture", "x1", "12:00", 1.0), ("Stylet", "x2", "10:25", 2.0), ("Stylet", "/2", "10:25", 0.5)],
)
def test_cercle_distance_choisit_centre_heure_et_octave(monkeypatch, centre, octave, heure_attendue, facteur):
    installer_geometrie_base(monkeypatch)
    monkeypatch.setattr(base_cadran, "convertirHeureLocaleVersUTC", lambda heure, longitude: f"UTC {heure}")
    monkeypatch.setattr(base_cadran, "MyJulianDate", SimpleNamespace(fromString=lambda *args: DateFictive()))
    monkeypatch.setattr(base_cadran, "positionSoleil", lambda *args: (45.0, 0.0))
    module = CercleDistance()
    module.pointBourges = PointFictif(villes_fictives()["Bourges"])
    module.styletCerclehoraire = "Roncevaux"
    module.heureSentinelleCerclehoraire = "10:25"
    module.dateDataset = "15/08/778"
    module.lettreChoixSegment = "F"
    module.centreCercle = centre
    module.P2M2 = "+2"
    module.octave = octave

    module.calculer()

    hauteur_attendue = 100.0 / CercleDistance.tableauGamme["F"][1] * CercleDistance.tableauGamme["A"][1]
    assert module.getValeursCentreCercle() == ("Ouverture", "Stylet")
    assert module.getValeursP2M2() == ("=", "+2", "-2", "Clef", "Clef 2")
    assert module.getValeursOctave() == ("x1", "x2", "/2")
    assert module.heureReference == heure_attendue
    assert module.lettreHauteur == "A"
    assert module.distanceClef == pytest.approx(100.0)
    assert module.hauteurStylet == pytest.approx(hauteur_attendue)
    assert module.distanceRef == pytest.approx(facteur * hauteur_attendue)
    assert module.centre is (module.pointBourges if centre == "Ouverture" else module.pointStylet)


class PointCandidatFictif(PointFictif):
    def __init__(self, *args, distance=0.0):
        self.nom = args[0] if args else "point"
        self.distance_vers_autre = distance

    def distance(self, autre):
        return self.distance_vers_autre

    @staticmethod
    def depuisDeuxPoints(point1, point2, nom=None):
        return PointCandidatFictif("candidat")


class LigneCandidatFictive:
    def __init__(self, projections=None, intersections=None):
        self.projections = projections or []
        self.intersections = intersections or {}

    def projectionPointGraphique(self, point):
        return self.projections.pop(0)

    def intersectionCercle(self, cercle):
        return self.intersections.get(cercle.nom, [])


class CercleCandidatFictif:
    intersections_directes = []

    def __init__(self, centre=None, rayon=None, nom="distance"):
        self.nom = nom

    @classmethod
    def depuisTroisPoints(cls, *args, **kwargs):
        return cls(nom="horaire")

    def intersectionCercle(self, autre):
        return self.intersections_directes


def installer_candidat_base(monkeypatch):
    monkeypatch.setattr(base_cadran, "villes_dict", {"Bourges": VilleFictive(), "Roncevaux": VilleFictive()})
    monkeypatch.setattr(base_cadran, "PointGraphique", PointCandidatFictif)
    monkeypatch.setattr(base_cadran, "CercleGraphique", CercleCandidatFictif)


def candidat_base_pret():
    module = CandidatBase()
    module.pointBourges = PointCandidatFictif("Bourges")
    module.styletCerclehoraire = "Roncevaux"
    module.coordPointChoixCerclehoraire = (1.0, 2.0)
    module.centreCercledistance = PointCandidatFictif("centre")
    module.distanceRefCercledistance = 100.0
    return module


def test_candidat_base_retient_lintersection_directe_proche(monkeypatch):
    installer_candidat_base(monkeypatch)
    point = PointCandidatFictif("intersection", distance=10.0)
    projection = PointCandidatFictif("projection")
    CercleCandidatFictif.intersections_directes = [point]
    module = candidat_base_pret()
    module.candidatsPartition = [LigneCandidatFictive(projections=[projection])]

    module.calculer(methode="historique")

    assert len(module.listeCandidats) == 1


@pytest.mark.parametrize(("distance", "nombre_attendu"), [(10.0, 1), (20.0, 0)])
def test_candidat_base_approche_les_cercles_non_intersectes(monkeypatch, distance, nombre_attendu):
    installer_candidat_base(monkeypatch)
    CercleCandidatFictif.intersections_directes = []
    point_horaire = PointCandidatFictif("horaire", distance=distance)
    point_distance = PointCandidatFictif("distance")
    module = candidat_base_pret()
    module.candidatsPartition = [
        LigneCandidatFictive(intersections={"horaire": [point_horaire], "distance": [point_distance]})
    ]

    module.calculer(methode="historique")

    assert len(module.listeCandidats) == nombre_attendu
