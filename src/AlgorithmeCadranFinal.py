from math import tan, radians, hypot, atan2, degrees, isfinite
from dataclasses import dataclass

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import LieuxObservation
from src.CadranNationalSentinelles import SentinelleNationale as Sentinelle
from src.ReferentielSentinelles import HeureMoyenneLocale, ContexteObservation
from src.ReferentielLampouyFinal import CHOIX_LAMPOUY as CHOIX_LAMPOUY_HISTORIQUE, ReferentielLampouyFinal

CHOIX_LAMPOUY = "Lampouy"


def formaterDecalageHoraire(secondes):
    """Minutes totales et secondes ; arrondi réservé à l'affichage."""
    minutes, reste = divmod(int(secondes + .5), 60)
    return f"{minutes:02d}:{reste:02d}"


def longitudesMeridiensHoraires(longitude, secondes_lumiere, secondes_ombre):
    """Écart circulaire en secondes TML et méridiens normalisés sur [-180, 180[."""
    decalage = abs((secondes_lumiere - secondes_ombre + 43200) % 86400 - 43200)
    normaliser = lambda angle: (angle + 180) % 360 - 180
    est, ouest = normaliser(longitude + decalage / 240), normaliser(longitude - decalage / 240)
    meridiens = [("Est", est)]
    if abs(normaliser(est - ouest)) > 1e-10:
        meridiens.append(("Ouest", ouest))
    return decalage, meridiens

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC
from src.substitutionsMusicales import _noteSourceClef2, noteAvecSubstitution as noteAvecSubstitutionCadranFinal

# Affichage des objects graphiques
from src.affichage_objets import ObjetGraphique, PointGraphique, Ligne, LigneEntreVilles, LigneAzimut, CercleGraphique


# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager
from src.carte_config import carteConfig


class AlgorithmeCadranFinal(AlgorithmeManager):

    def __init__(self, layerManager: LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
        return [
            ("segment", "Segment", Segment()),
            ("stylet", "stylet", StyletFinal()),
            ("styletlumiere", "Stylet", StyletLumiere()),
            ("lumiere", "Lumière", LumiereFinal()),
            ("ombre", "Ombre", LigneHoraireFinal()),
            ("candidat", "Candidat", CandidatFinal()),
        ]

    def appliquerParametresDepuisStructure(self):
        pass

    def calculerModules(self, nom_scenario=None, segment=None, setup=False):
        scenario = self.getScenario(nom_scenario, segment)
        if self.dataset.base1 or self.dataset.base2:
            scenario.ordreModules = self.ordreModules
            return super().calculerModules(nom_scenario, segment, setup)

        # Sans bases, seul l'événement reste actif. La reconstruction du calque
        # efface les anciens objets sans appeler les représentations géométriques.
        scenario.ordreModules = ["segment"]
        self.injecterEntreesDansModuleObjet("segment", nom_scenario, segment)
        if setup:
            scenario.modules["segment"].setup()
        self.appliquerReglesSurModule("segment", nom_scenario, segment)
        scenario.modules["segment"].calculer()

    def getLargeurHauteurIHM(self):
        return 495, 600


#
# Gestion de l'objet Soleil: Gère l'observation.
# Pas de calcul à proprement parlé, juste l'initialsation de la lettre Dominicale et lieu d'observation'
#
class Segment(ModuleAlgo):

    def getEntreesModules(self):
        return ["dataset.date",
                ]

    def __init__(self):
        # Variables input des autres modules
        self.dateDataset = ""
        self.lettreDom = ""
        self.lettreChoix = ""
        self.lieuObservation = ""

        # Affiché
        super().__init__()

    def getValeursLieuObservation(self):
        return LieuxObservation.getListeLieuxObservation(self.lettreDom, self.dateDataset)

    def setup(self):
        # On calcule la déclinaison du soleil pour savoir si nous sommes au Printemps / Ete ou Automne / Hivers
        self.dateSegmentJD = MyJulianDate.fromString(self.dateDataset)
        self.lettreDom = self.dateSegmentJD.lettreDominicale()
        self.choixCalendrier = "Standard"

        # On initialise le lieu d'observation
        self.lieuObservation = LieuxObservation.getDefautLieuObservation(self.lettreDom)


class StyletFinal(ModuleAlgo):
    def getEntreesModules(self):
        return ["dataset.stylet",
                "dataset.base1",
                "dataset.base2",
                "dataset.lettreDecl",
                "segment.lettreDom",
                ]

    def getValeursChoixBase(self):
        return "Base 1", "Base 2"

    def getValeursP2M2(self):
        return "=", "+2", "-2", "Clef", "Clef 2"

    def getValeursOctave(self):
        return "x1", "x2", "x4", "/2", "/4", "/8"

    def getValeursChoixCalendrier(self):
        return ["Standard", "Déclinaison"]

    tableauGamme = {
        "C": 2**(-12/12),
        "B": 2**(-10/12),
        "A": 2**(-9/12),
        "G": 2**(-7/12),
        "F": 2**(-5/12),
        "E": 2**(-3/12),
        "D": 2**(-1/12)
    }
    tableauOctave = {
        "x1": 1,
        "x2": 2,
        "x4": 4,
        "/2": 0.5,
        "/4": 0.25,
        "/8": 0.125
    }

    def __init__(self):
        # Variables input des autres modules
        self.styletDataset = ""
        self.lettreDeclDataset = ""
        self.base1Dataset = ""
        self.base2Dataset = ""
        self.lettreDomSegment = ""

        # Affiché
        self.choixCalendrier = "Standard"
        self.lettreChoix = ""
        self.choixBase = "Base 1"
        self.base = ""
        self.distanceRef = None
        self.P2M2 = "="
        self.lettre = None
        self.hauteur = None
        self.octave = "x1"
        self.azimutMidi = None
        super().__init__()

    def setup(self):
        self.lettreChoix = self.lettreDomSegment
        pointMetz = PointGraphique(villes_dict["Metz"])
        pointStylet = PointGraphique(villes_dict[self.styletDataset])
        self.distanceRef = pointMetz.distance(pointStylet)

    def calculer(self):
        self.base = self.base1Dataset if self.choixBase == "Base 1" else self.base2Dataset
        self.lettreChoix = self.lettreDomSegment if self.choixCalendrier == "Standard" else self.lettreDeclDataset

        # On sélectionne la hauteur du stylet
        self.lettre = noteAvecSubstitutionCadranFinal(self.lettreChoix, self.P2M2)

        longFA = StyletFinal.tableauGamme["F"]
        longNote = StyletFinal.tableauGamme[self.lettre]
        self.hauteur = StyletFinal.tableauOctave[self.octave] * self.distanceRef / longFA * longNote

        # On calcule l'azimut de Midi
        (x1, y1) = villes_dict[self.base].getCoordonneesPixel()
        (x2, y2) = villes_dict["Bourges"].getCoordonneesPixel()
        self.azimutMidi = Ligne(x1, y1, x2, y2).azimut()

class StyletLumiere(ModuleAlgo):
    """Consommateur graphique des résultats de stylet et lumière."""

    COULEUR_POINT_STYLET = (0, 0, 128)
    COULEUR_TRAIT_MIDI = (255, 145, 34)

    def getEntreesModules(self):
        return [
            "stylet.styletDataset",
            "stylet.base",
            "stylet.azimutMidi",
            "stylet.hauteur",
            "lumiere.distance",
            "lumiere.heureLocale",
            "lumiere.hauteur",
        ]

    def __init__(self):
        self.styletDatasetStylet = ""
        self.baseStylet = ""
        self.azimutMidiStylet = None
        self.hauteurStylet = None
        self.distanceLumiere = None
        self.heureLocaleLumiere = ""
        self.hauteurLumiere = None
        super().__init__()

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        pointStylet = PointGraphique(
            villes_dict[self.styletDatasetStylet],
            nom=f"Stylet : {self.styletDatasetStylet}",
            epaisseur=4,
            couleur=self.COULEUR_POINT_STYLET,
            tooltips=[f"Stylet Initial {self.styletDatasetStylet}"],
            tags={"level": "design"},
        )
        pointBourges = PointGraphique(
            villes_dict["Bourges"],
            nom="Ouverture",
            epaisseur=4,
            couleur=self.COULEUR_TRAIT_MIDI,
            tooltips=["Extremité du stylet"],
            tags={"level": "design"},
        )
        pointBase = PointGraphique(
            villes_dict[self.baseStylet],
            nom="Base stylet",
            epaisseur=4,
            couleur=self.COULEUR_TRAIT_MIDI,
            tooltips=["Extremité du stylet"],
            tags={"level": "design"},
        )
        ligneMidi = LigneEntreVilles(
            pointBourges,
            pointBase,
            nom="Axe Midi",
            epaisseur=1,
            couleur=self.COULEUR_TRAIT_MIDI,
            tooltips=[
                f"Axe Midi Bourges - {self.baseStylet}",
                f"Azimut Midi: {self.azimutMidiStylet:.02f}° / {self.azimutMidiStylet - 360:.02f}°",
            ],
            tags={"level": "design"},
        )
        cercleLumiere = CercleGraphique(
            villes_dict["Bourges"],
            self.distanceLumiere,
            nom="Cercle Lumiere",
            couleur=LumiereFinal.COULEUR_TRAIT_CANDIDAT,
            tooltips=[
                f"Heure {self.heureLocaleLumiere}",
                f"Hauteur Soleil ={self.hauteurLumiere:.2f}°",
                f"Hauteur stylet ={self.hauteurStylet:.2f}km",
                f"Distance : {self.distanceLumiere:2f}km",
            ],
            tags={"level": "construction"},
        )
        cercleLumiere.setPrintLabel(self.heureLocaleLumiere)
        return [pointBourges, pointBase, ligneMidi, pointStylet, cercleLumiere]


class LumiereFinal(ModuleAlgo):
    def getEntreesModules(self):
        return ["segment.lieuObservation",
                "segment.lettreDom",
                "dataset.lettreDecl",
                "dataset.date",
                "dataset.dateSegment",
                "stylet.choixCalendrier",
                "stylet.hauteur",
                "stylet.azimutMidi",
                ]

    def getValeursChoixCalendrier(self):
        return ["Standard", "Déclinaison"]

    def getValeursChoixHeure(self):
        list = ["=", "+2", "-2", "Clef", "Clef 2", "11:00"]
        if self.dateDataset == "18/05/1152":
            list.append(CHOIX_LAMPOUY)
        return list

    def getValeursHeureAMPM(self):
        return ["AM", "PM"]

    def getRegles(self):
        return [
            ["Si le stylet est standard, la lumière est est déclinaison", "choixCalendrier", self._regleChoixCalendrier]
        ]

    def _regleChoixCalendrier(self):
        if self.choixCalendrierStylet == "Standard":
            return "Déclinaison"
        else:
            return "Standard"

    def __init__(self):
        # Import des classes précédentes
        self.dateDataset = ""
        self.dateSegmentDataset = ""
        self.lettreDeclDataset = ""
        self.lieuObservationSegment = ""
        self.lettreDomSegment = ""
        self.hauteurStylet = None
        self.azimutMidiStylet = None
        self.choixCalendrierStylet = ""

        # Input User
        self.choixHeure = "="
        self.lettreChoix = ""
        self.heureAMPM = "AM"
        self.choixCalendrier = "Standard"

        # Calculé
        self.heureLocale = ""
        self.heureUTC = ""
        self.heureLocaleSecondes = None
        self.dateObservationUT1 = None
        self.noteHoraire = None
        self.brancheReference = None
        self.directionReference = None
        self.horaireLampouy = False
        self.referenceLampouy = None
        self.azimut = None
        self.hauteur = None
        self.deltaMidi = None
        self.distance = None

        self.sentinelle = Sentinelle("data/sentinelle.csv")
        super().__init__()

    def setup(self):
        self.lettreChoix = self.lettreDomSegment

    def calculer(self):
        self.lettreChoix = self.lettreDomSegment if self.choixCalendrier == "Standard" else self.lettreDeclDataset
        # Les coords d'observation du soleil le jour donnée
        coordObs = villes_dict[self.lieuObservationSegment].getCoordonneesGPS()
        (lat, lon) = coordObs

        # On prend en compte les heures de substitution
        if self.choixHeure == "11:00":
            choixNote = "J"
        elif self.choixHeure in ("=", "+2", "-2", "Clef", "Clef 2"):
            choixNote = noteAvecSubstitutionCadranFinal(self.lettreChoix, self.choixHeure)
        elif self.choixHeure in (CHOIX_LAMPOUY, CHOIX_LAMPOUY_HISTORIQUE):
            choixNote = "L"
        else:
            raise ValueError(f"Heure inconnue : {self.choixHeure}")

        self.noteHoraire = choixNote
        self.horaireLampouy = choixNote == "L"
        self.referenceLampouy = None
        if self.horaireLampouy:
            self.referenceLampouy = ReferentielLampouyFinal.charger()
            self.directionReference = self.referenceLampouy.directionPourPeriode(self.heureAMPM)
            heure = self.directionReference.heure_locale
            self.brancheReference = "directe" if self.directionReference is self.referenceLampouy.directe else "miroir"
        else:
            heure = self.sentinelle.heurePourNote(choixNote, self.heureAMPM)
            self.directionReference = self.sentinelle.directionPourNote(choixNote, self.heureAMPM)
            self.brancheReference = ("directe" if self.directionReference is self.sentinelle.par_note[choixNote].directe else "miroir")
        self.heureLocale = heure.toString()
        self.heureLocaleSecondes = heure.secondes
        contexte = ContexteObservation(self.lieuObservationSegment, lat, lon, self.dateSegmentDataset)
        self.dateObservationUT1 = contexte.versUT1(heure)
        self.heureUTC = HeureMoyenneLocale(((float(self.dateObservationUT1) + .5) % 1) * 86400).toString()

        # On calcule l'angle entre la droite de Midi Solaire et la droite Stylet - ST Cyr
        self.hauteur, self.azimut = positionSoleil(coordObs, self.dateObservationUT1)

        # delta & distance
        self.deltaMidi = 180 - self.azimut
        self.distance = self.hauteurStylet / tan(radians(self.hauteur))

    COULEUR_TRAIT_CANDIDAT = (36, 28, 237)

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        centre = villes_dict["Bourges"]
        # On ajoute l'axe de lumière
        deltaAzimutSoleil = self.azimut - 180
        ligneLumiere1 = LigneAzimut(
            centre,
            (self.azimutMidiStylet + deltaAzimutSoleil) % 360,
            nom="Ligne Lumiere",
            couleur=LumiereFinal.COULEUR_TRAIT_CANDIDAT,
            tooltips=[f"Heure {self.heureLocale}",
                      f"Azimut %Sud Soleil ={deltaAzimutSoleil:.2f}°",
                      ],
            tags={"level" : "construction"}
            )
        ligneLumiere1.setPrintLabel(self.heureLocale)
        listeObjets.append(ligneLumiere1)
        ligneLumiere2 = LigneAzimut(
            centre,
            (self.azimutMidiStylet - deltaAzimutSoleil) % 360,
            nom="Ligne Lumiere",
            couleur=LumiereFinal.COULEUR_TRAIT_CANDIDAT,
            tooltips=[f"Heure {self.heureLocale}",
                      f"Azimut %Sud Soleil ={deltaAzimutSoleil:.2f}°",
                      ],
            tags={"level" : "construction"}
            )
        ligneLumiere2.setPrintLabel(self.heureLocale)
        listeObjets.append(ligneLumiere2)
        if self.horaireLampouy:
            for ligne in listeObjets:
                ligne.setTooltips(ligne.tooltips + [
                    f"Référence fixe : Lampouy, {self.referenceLampouy.contexte.date}, {self.brancheReference}",
                    f"Azimut de calibration : {self.directionReference.azimut:.6f}°"])
        return listeObjets


@dataclass(frozen=True)
class LigneHoraireReference:
    note: str
    repere: str
    branche: str
    ampm: str
    heure_locale: HeureMoyenneLocale
    azimut_solaire: float
    ecart_image: float
    candidat: bool
    ligne: ObjetGraphique


class LigneHoraireFinal(ModuleAlgo):
    def getEntreesModules(self):
        return ["segment.lieuObservation",
                "segment.lettreDom",
                "dataset.dateSegment",
                "dataset.lettreDecl",
                "dataset.date",
                "stylet.azimutMidi",
                "stylet.base",
                "lumiere.sentinelle",
                "lumiere.heureAMPM",
                "lumiere.choixCalendrier",
                "lumiere.heureLocaleSecondes",
                ]

    def getValeursChoixCalendrier(self):
        return ["Standard", "Déclinaison"]

    def getValeursChoixHeure(self):
        list = ["=", "+2", "-2", "Clef", "Clef 2", "11:00"]
        if self.dateDataset == "18/05/1152":
            list.append(CHOIX_LAMPOUY)
        return list

    def getValeursSensCarte(self):
        return ["Endroit", "Envers"]

    def getValeursAfficherMeridiensHoraires(self):
        return ["Non", "Oui"]

    def getRegles(self):
        return [
            ["Le sens de la carte est lié à l'heure AM/PM de la lumière", "sensCarte", self._regleSensCarte],
            ["Si la lumiere est standard, l'ombre est déclinaison", "choixCalendrier", self._regleChoixCalendrier]
        ]

    def _regleSensCarte(self):
        if self.heureAMPMLumiere == "AM":
            return "Endroit"
        else:
            return "Envers"

    def _regleChoixCalendrier(self):
        if self.choixCalendrierLumiere == "Standard":
            return "Déclinaison"
        else:
            return "Standard"

    def __init__(self):
        # Import des classes précédentes
        self.lieuObservationSegment = ""
        self.lettreDomSegment = ""
        self.dateSegmentDataset = ""
        self.lettreDeclDataset = ""
        self.dateDataset = ""
        self.azimutMidiStylet = None
        self.baseStylet = None
        self.sentinelleLumiere = None
        self.heureAMPMLumiere = None
        self.choixCalendrierLumiere = ""
        self.heureLocaleSecondesLumiere = None

        # calculé
        self.choixCalendrier = "Standard"
        self.lettreChoix = ""
        self.choixHeure = "="
        self._azimutMidiReference = None
        self._dateMidiReferenceUT1 = None
        self._azimutMidiLampouy = None
        self.referenceLampouy = None

        self.heureLocale = ""
        self.listeCandidatsHeure = []
        self.lignesHorairesReference = []
        self.noteHoraire = None
        self.heureLocaleSecondes = None
        self.sensCarte = "Endroit"
        self.afficherMeridiensHoraires = "Non"

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])
        self.lettreChoix = self.lettreDomSegment

    def calculer(self):
        self.lettreChoix = self.lettreDomSegment if self.choixCalendrier == "Standard" else self.lettreDeclDataset

        # On prend en compte les heures de substitution
        if self.choixHeure == "11:00":
            self.noteHoraire = "J"
        elif self.choixHeure in ("=", "+2", "-2", "Clef", "Clef 2"):
            self.noteHoraire = noteAvecSubstitutionCadranFinal(self.lettreChoix, self.choixHeure)
        elif self.choixHeure in (CHOIX_LAMPOUY, CHOIX_LAMPOUY_HISTORIQUE):
            self.noteHoraire = "L"
        else:
            raise ValueError(f"Heure inconnue : {self.choixHeure}")
        self.referenceLampouy = None
        if self.dateDataset == "18/05/1152" or self.noteHoraire == "L":
            self.referenceLampouy = ReferentielLampouyFinal.charger()
        heure_am = (self.referenceLampouy.directe.heure_locale if self.noteHoraire == "L" else
                    self.sentinelleLumiere.heurePourNote(self.noteHoraire, "AM"))
        self.heureLocale = heure_am.toString()
        self.heureLocaleSecondes = heure_am.secondes

        # Même contexte que les directions nationales : Carnac, 15/08/1066 julien.
        midi = self.sentinelleLumiere.referentiel.moteur.directionPourHeure(HeureMoyenneLocale(12 * 3600))
        self._azimutMidiReference = midi.azimut
        self._dateMidiReferenceUT1 = midi.jd_ut1
        self._azimutMidiLampouy = None
        if self.referenceLampouy is not None:
            self._azimutMidiLampouy = self.referenceLampouy.azimut_midi

        # On crée les lignes horaires
        self.listeLigneHoraire = []
        self.listeCandidatsHeure = []
        self.lignesHorairesReference = []
        self.pointBase = PointGraphique(villes_dict[self.baseStylet])
        # On crée les lignes horaires et on rajoute Lampouy si nous sommes le 18/05/1152
        tableauNotes = ["C", "B", "A", "G", "F", "E", "D", "J"]
        if self.dateDataset == "18/05/1152":
            tableauNotes.append("L")

        for note in tableauNotes:
            # L'axe du stylet est déjà un angle image. Aucune conversion
            # Lambert ni substitution de l'axe national n'a lieu ici.
            candidat = note == self.noteHoraire  # identité du repère, pas son heure arrondie
            for ampm in ("AM", "PM"):
                if note == "L":
                    direction = self.referenceLampouy.directionPourPeriode(ampm)
                    heure, azimut = direction.heure_locale, direction.azimut
                    repere = "Lampouy"
                    branche = "directe" if direction is self.referenceLampouy.directe else "miroir"
                else:
                    heure = self.sentinelleLumiere.heurePourNote(note, ampm)
                    ref = self.sentinelleLumiere.par_note[note]
                    direction = self.sentinelleLumiere.directionPourNote(note, ampm)
                    azimut = direction.azimut
                    repere = ref.identifiant
                    branche = "directe" if direction is ref.directe else "miroir"
                midi_reference = self._azimutMidiLampouy if note == "L" else self._azimutMidiReference
                ecart = azimut - midi_reference
                if self.sensCarte == "Envers":
                    ecart = -ecart
                ligne = LigneAzimut(self.pointBase, self.azimutMidiStylet + ecart)
                metadata = LigneHoraireReference(note, repere, branche, ampm, heure, azimut, ecart, candidat, ligne)
                self.lignesHorairesReference.append(metadata)
                self.listeLigneHoraire.append((heure.toString(), ecart, ampm, candidat, ligne))
                if candidat:
                    self.listeCandidatsHeure.append((heure.toString(), ligne))

    COULEUR_TRAIT_HEURE = (255, 193, 132)
    COULEUR_TRAIT_CANDIDAT = (164, 82, 0)

    def construireMeridiensHoraires(self):
        if (self.afficherMeridiensHoraires != "Oui" or self.heureLocaleSecondesLumiere is None
                or self.heureLocaleSecondes is None):
            return []
        _, longitude = villes_dict[self.lieuObservationSegment].getCoordonneesGPS()
        decalage, meridiens = longitudesMeridiensHoraires(
            longitude, self.heureLocaleSecondesLumiere, self.heureLocaleSecondes)
        objets = []
        for sens, longitude_meridien in meridiens:
            # En Lambert-93 (projection conique), un méridien est une droite.
            # Deux points GPS définissent sa direction réelle ; la primitive
            # existante étend et découpe ensuite cette droite aux bords de carte.
            sud, nord = [PointGraphique("Méridien", *carteConfig.gps_to_lambert93(longitude_meridien, latitude))
                         for latitude in (0., 89.)]
            ligne = LigneEntreVilles(sud, nord, nom=f"Méridien {sens}", couleur=(125, 150, 125), epaisseur=1,
                tooltips=[f"Longitude : {longitude_meridien:.8f}°",
                          f"Décalage horaire : {formaterDecalageHoraire(decalage)}"],
                tags={"level": "design"})
            ligne.setPrintLabel(f"Méridien {sens}")
            objets.append(ligne)
        return objets

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        for metadata in self.lignesHorairesReference:
            heureLocale = metadata.heure_locale.toString()
            ligneGraphique = metadata.ligne
            legende = f"{metadata.repere}/{metadata.note} {metadata.branche} {heureLocale}"
            ligneGraphique.setNom(legende)
            ligneGraphique.setPrintLabel(f"{metadata.note} {metadata.branche} {heureLocale}")
            couleur = LigneHoraireFinal.COULEUR_TRAIT_CANDIDAT if metadata.candidat else LigneHoraireFinal.COULEUR_TRAIT_HEURE
            ligneGraphique.setCouleur(couleur)

            moment = "matin" if metadata.ampm == "AM" else "après-midi"
            ligneGraphique.setTooltips([legende, f"Branche solaire : {moment}",
                                       f"Azimut image : {self.azimutMidiStylet + metadata.ecart_image:.6f}°"])
            if metadata.note == "L":
                ligneGraphique.setTooltips(ligneGraphique.tooltips + [
                    f"Référence fixe : Lampouy, {self.referenceLampouy.contexte.date}",
                    f"Azimut de calibration : {metadata.azimut_solaire:.6f}°"])
            ligneGraphique.ajouterTag("level", "design")
            listeObjets.append(ligneGraphique)
        listeObjets.extend(self.construireMeridiensHoraires())
        return listeObjets


@dataclass(frozen=True)
class CandidatPondere:
    a: tuple
    b: tuple | None
    c: tuple | None
    q: tuple
    m: tuple
    g: tuple | None
    p: tuple
    distance_aq: float
    angle: float
    poids: float
    methode: str
    distance_pa: float
    distance_p_droite: float


def calculerCandidatPondere(a, intersections_b, origine_ombre, direction_ombre, direction_lumiere):
    """Géométrie métrique en Lambert-93 ; distances retournées en kilomètres."""
    def unitaire(v):
        norme = hypot(*v)
        if norme == 0:
            raise ValueError("Direction nulle")
        return v[0] / norme, v[1] / norme

    u, v = unitaire(direction_lumiere), unitaire(direction_ombre)
    # Projection par la normale : pas de soustraction de deux grands produits.
    n = (-v[1], v[0])
    h = (a[0] - origine_ombre[0]) * n[0] + (a[1] - origine_ombre[1]) * n[1]
    q = (a[0] - h * n[0], a[1] - h * n[1])
    distance_aq = abs(h) / 1000
    if distance_aq > 30:
        return None
    m = ((a[0] + q[0]) / 2, (a[1] + q[1]) / 2)
    det = u[0] * v[1] - u[1] * v[0]
    angle = degrees(atan2(abs(det), abs(u[0] * v[0] + u[1] * v[1])))
    poids = min(1.0, (angle / 45) ** 2)
    b = min(intersections_b, key=lambda p: hypot(p[0]-a[0], p[1]-a[1]), default=None)
    c = g = None
    methode = "milieu (droites parallèles)" if det == 0 else "milieu (C absent)"
    p = m
    if det != 0:
        delta = (origine_ombre[0]-a[0], origine_ombre[1]-a[1])
        numerateur = delta[0] * v[1] - delta[1] * v[0]
        s = numerateur / det
        candidat_c = (a[0] + s * u[0], a[1] + s * u[1])
        if all(isfinite(x) for x in candidat_c):
            c = candidat_c
            if b is not None:
                g = tuple((a[i] + b[i] + c[i]) / 3 for i in (0, 1))
                # t*C est évalué via (t/det)*numérateur : limite stable en angle nul.
                poids_s = (poids / det) * numerateur
                p = tuple(m[i] + poids * (a[i] - m[i] + (b[i]-a[i])/3)
                          + poids_s * u[i]/3 for i in (0, 1))
                methode = "barycentre pondéré selon l’angle"
    if b is None:
        methode = "milieu (B absent" + (", C absent)" if c is None else ")")
    distance_pa = hypot(p[0]-a[0], p[1]-a[1])/1000
    distance_p_droite = abs((p[0]-origine_ombre[0])*n[0] + (p[1]-origine_ombre[1])*n[1])/1000
    return CandidatPondere(a, b, c, q, m, g, p, distance_aq, angle, poids, methode,
                           distance_pa, distance_p_droite)


class CandidatFinal(ModuleAlgo):

    RAYON_CANDIDAT = 20

    def getEntreesModules(self):
        return ["segment.lieuObservation",
                "stylet.lettre",
                "stylet.azimutMidi",
                "lumiere.azimut",
                "lumiere.distance",
                "lumiere.heureLocale",
                "ombre.listeCandidatsHeure",
                ]

    def __init__(self):
        # Import des classes précédentes
        self.lieuObservationSegment = ""
        self.lettreStylet = ""
        self.azimutMidiStylet = None
        self.azimutLumiere = None
        self.distanceLumiere = None
        self.heureLocaleLumiere = None
        self.listeCandidatsHeureOmbre = None

    def construireRepresentationCarte(self, methode="ponderee") -> list[ObjetGraphique]:
        if methode == "historique":
            return self.construireRepresentationCarteHistorique()
        if methode != "ponderee":
            raise ValueError(f"Méthode de candidat inconnue : {methode}")
        return self.construireRepresentationCartePonderee()

    def calculerGeometriesPonderees(self):
        """Une décision par A et droite horaire ; aucun filtre sur la position de C."""
        resultats = []
        cercle = CercleGraphique(villes_dict["Bourges"], self.distanceLumiere)
        for signe in (-1, 1):
            lumiere = LigneAzimut(villes_dict["Bourges"], self.azimutMidiStylet + signe * (180 - self.azimutLumiere))
            u = tuple(carteConfig.A_inv @ lumiere.vecteur)
            for heure, ombre in self.listeCandidatsHeureOmbre:
                origine = carteConfig.pixels_to_lambert93(*ombre.pointReference)
                v = tuple(carteConfig.A_inv @ ombre.vecteur)
                bs = [p.coordonneesLambert() for p in ombre.intersectionCercle(cercle)] if ombre.lignePixelImage is not None else []
                for a in lumiere.intersectionCercle(cercle):
                    geometrie = calculerCandidatPondere(a.coordonneesLambert(), bs, origine, v, u)
                    if geometrie is not None:
                        resultats.append((signe, heure, geometrie))
        return resultats

    def construireRepresentationCartePonderee(self):
        objets = []
        for _, heure, g in self.calculerGeometriesPonderees():
            centre = PointGraphique("Centre pondéré", *g.p)
            ecart = abs(centre.distance(villes_dict["Bourges"]) - self.distanceLumiere)
            objets.append(CercleGraphique(centre, self.RAYON_CANDIDAT, epaisseur=2, nom="Candidat",
                tooltips=[f"Méthode : {g.methode}", f"Ombre : {heure}",
                          f"A–Q : {g.distance_aq:.6f} km", f"Angle : {g.angle:.6f}°", f"Poids : {g.poids:.9f}",
                          f"P–A : {g.distance_pa:.6f} km", f"P–droite horaire : {g.distance_p_droite:.6f} km",
                          f"Écart radial au rayon nominal : {ecart:.6f} km"], tags={"level": "construction"}))
        return objets

    def construireRepresentationCarteHistorique(self) -> list[ObjetGraphique]:
        listeObjets = []
        triplets = []

        # On trouve les 4 points de lumière possible
        cercleLumiere = CercleGraphique(villes_dict["Bourges"], self.distanceLumiere)
        ligneAM = LigneAzimut(villes_dict["Bourges"], self.azimutMidiStylet - (180 - self.azimutLumiere))
        lignePM = LigneAzimut(villes_dict["Bourges"], self.azimutMidiStylet + (180 - self.azimutLumiere))
        lignesLumiere = [ligneAM, lignePM]
        for ligneLumiere in lignesLumiere:
            ptsCercleLumiere = ligneLumiere.intersectionCercle(cercleLumiere)
            for heure, ligneHeure in self.listeCandidatsHeureOmbre:
                ptsCercleHeure = ligneHeure.intersectionCercle(cercleLumiere)
                ptsInter = ligneHeure.intersectionLigne(ligneLumiere)

                # Si pas d'intersection ou pas dans l'image, on garde un pt3 None
                pt3 = None
                if ptsInter is not None:
                    pt3x_l93, pt3y_l93 = ptsInter
                    pt3 = PointGraphique("Lumière x Horaire", pt3x_l93, pt3y_l93)
                    if not pt3.estVisibledansImage():
                        pt3 = None

                for pt1 in ptsCercleLumiere:
                    pt1x_l93, pt1y_l93 = pt1.coordonneesLambert()

                    for pt2 in ptsCercleHeure:
                        pt2x_l93, pt2y_l93 = pt2.coordonneesLambert()
                        distance12 = pt1.distance(pt2)
                        triplet_valide = False

                        # Si nous avons un pt3, on calcle le barycentre
                        if pt3:
                            xb_l93 = (pt1x_l93+pt2x_l93+pt3x_l93)/3
                            yb_l93 = (pt1y_l93+pt2y_l93+pt3y_l93)/3
                            ptb = PointGraphique("Barycentre", xb_l93, yb_l93)

                            # On vérifie les distanes
                            if all(p.distance(ptb) <= CandidatFinal.RAYON_CANDIDAT for p in [pt1, pt2, pt3]):
                                triplets.append(ptb)
                                triplet_valide = True

                        # Secours : chaque point doit être à 20 km maximum de leur milieu.
                        if not triplet_valide and distance12 <= 2 * CandidatFinal.RAYON_CANDIDAT:
                            xb_l93 = (pt1x_l93 + pt2x_l93) / 2
                            yb_l93 = (pt1y_l93 + pt2y_l93) / 2
                            ptb = PointGraphique("Barycentre", xb_l93, yb_l93)
                            triplets.append(ptb)

        for pt in triplets:
            cercleCandidat = CercleGraphique(
                pt,
                CandidatFinal.RAYON_CANDIDAT,
                epaisseur=2,
                nom="Candidat",
                tooltips=[],
                tags={"level" : "construction"}
            )
            listeObjets.append(cercleCandidat)
        return listeObjets
