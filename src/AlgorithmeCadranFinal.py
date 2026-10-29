from math import tan, radians
from dataclasses import dataclass

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import LieuxObservation
from src.CadranNationalSentinelles import SentinelleNationale as Sentinelle
from src.ReferentielSentinelles import HeureMoyenneLocale, ContexteObservation

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC, decalageGamme

# Affichage des objects graphiques
from src.affichage_objets import ObjetGraphique, PointGraphique, Ligne, LigneEntreVilles, LigneAzimut, CercleGraphique


# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager


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
        return "=", "+2", "-2", "Clef"

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
        tabDec = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}
        listeNotes = decalageGamme(self.lettreChoix)  # On décale sans susbtition Fa/Sol
        self.lettre = listeNotes[tabDec[self.P2M2]]

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
        list = ["=", "+2", "-2", "Clef", "11:00"]
        if self.dateDataset == "18/05/1152":
            heureLampouy = self.sentinelle["L"]["HeureLocale"]
            list.append(heureLampouy)
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
        elif self.choixHeure in ("=", "+2", "-2", "Clef"):
            tabDec = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}
            listeNotes = decalageGamme(self.lettreChoix)  # On décale sans susbtition Fa/Sol
            choixNote = listeNotes[tabDec[self.choixHeure]]
        elif self.choixHeure == self.sentinelle["L"]["HeureLocale"]:
            choixNote = "L"
        else:
            raise ValueError(f"Heure inconnue : {self.choixHeure}")

        self.noteHoraire = choixNote
        self.horaireLampouy = choixNote == "L"
        heure = self.sentinelle.heurePourNote(choixNote, self.heureAMPM)
        self.heureLocale = heure.toString()
        self.heureLocaleSecondes = heure.secondes
        if self.horaireLampouy:
            self.directionReference = None
            self.brancheReference = "historique_" + self.heureAMPM
            self.heureUTC = convertirHeureLocaleVersUTC(self.heureLocale, lon)
            self.dateObservationUT1 = MyJulianDate.fromString(self.dateSegmentDataset, self.heureUTC)
        else:
            self.directionReference = self.sentinelle.directionPourNote(choixNote, self.heureAMPM)
            self.brancheReference = ("directe" if self.directionReference is self.sentinelle.par_note[choixNote].directe else "miroir")
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
                ]

    def getValeursChoixCalendrier(self):
        return ["Standard", "Déclinaison"]

    def getValeursChoixHeure(self):
        list = ["=", "+2", "-2", "Clef", "11:00"]
        if self.dateDataset == "18/05/1152":
            heureLampouy = self.sentinelleLumiere["L"]["HeureLocale"]
            list.append(heureLampouy)
        return list

    def getValeursSensCarte(self):
        return ["Endroit", "Envers"]

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

        # calculé
        self.choixCalendrier = "Standard"
        self.lettreChoix = ""
        self.choixHeure = "="
        self._azimutMidiReference = None
        self._dateMidiReferenceUT1 = None
        self._azimutMidiLampouy = None

        self.heureLocale = ""
        self.listeCandidatsHeure = []
        self.lignesHorairesReference = []
        self.noteHoraire = None
        self.heureLocaleSecondes = None
        self.sensCarte = "Endroit"

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])
        self.lettreChoix = self.lettreDomSegment

    def calculer(self):
        self.lettreChoix = self.lettreDomSegment if self.choixCalendrier == "Standard" else self.lettreDeclDataset

        # On prend en compte les heures de substitution
        if self.choixHeure == "11:00":
            self.noteHoraire = "J"
        elif self.choixHeure in ("=", "+2", "-2", "Clef"):
            tabDec = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}
            listeNotes = decalageGamme(self.lettreChoix)  # On décale sans susbtition Fa/Sol
            self.noteHoraire = listeNotes[tabDec[self.choixHeure]]
        elif self.choixHeure == self.sentinelleLumiere["L"]["HeureLocale"]:
            self.noteHoraire = "L"
        else:
            raise ValueError(f"Heure inconnue : {self.choixHeure}")
        heure_am = self.sentinelleLumiere.heurePourNote(self.noteHoraire, "AM")
        self.heureLocale = heure_am.toString()
        self.heureLocaleSecondes = heure_am.secondes

        # Même contexte que les directions nationales : Carnac, 15/08/1066 julien.
        midi = self.sentinelleLumiere.referentiel.moteur.directionPourHeure(HeureMoyenneLocale(12 * 3600))
        self._azimutMidiReference = midi.azimut
        self._dateMidiReferenceUT1 = midi.jd_ut1
        self._azimutMidiLampouy = None
        if self.dateDataset == "18/05/1152":
            # Lampouy garde ses azimuts/heures historiques et son propre contexte.
            contexte = ContexteObservation("Carnac", *villes_dict["Carnac"].getCoordonneesGPS(), "20/08/1152")
            _, self._azimutMidiLampouy = positionSoleil(
                contexte.coordonnees, contexte.versUT1(HeureMoyenneLocale(12 * 3600)))

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
                heure = self.sentinelleLumiere.heurePourNote(note, ampm)
                if note == "L":
                    azimut = self.sentinelleLumiere["L"]["AzimutCalibre"]
                    azimut = azimut if ampm == "AM" else (360 - azimut) % 360
                    repere, branche = "Lampouy", "historique_" + ampm
                else:
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
            ligneGraphique.ajouterTag("level", "design")
            listeObjets.append(ligneGraphique)
        return listeObjets


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

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
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

                        # On gère le cas des droites pratiquement parallèles avec pt1 et pt2 < 10km
                        if not triplet_valide and distance12 <= CandidatFinal.RAYON_CANDIDAT/2:
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
