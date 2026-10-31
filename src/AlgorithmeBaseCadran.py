from math import radians, tan
import logging
import re

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import LieuxObservation, Sentinelle as LectureSentinelles
from src.CadranNationalSentinelles import SentinelleNationale as Sentinelle, SelectionHoraire
from src.ReferentielSentinelles import HeureMoyenneLocale, ContexteObservation

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil, calculLeverSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC
from src.substitutionsMusicales import noteAvecSubstitution

# Affichage des objects graphiques
from src.affichage_objets import ObjetGraphique, PointGraphique, LigneEntreVilles, LigneAzimut, LigneGraphique, CercleGraphique


# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager
from src.carte_config import carteConfig
from src.GeometrieCandidatsBase import CercleMetrique, ResultatCandidatBase, chercherCandidatsBasePonderes, ecartDroiteCercle, TOL_METRES


CHOIX_LAMPOUY = "Lampouy"


def normaliserSubstitutionLampouy(valeur, date):
    """Les anciens choix en degrés du 18 mai désignaient tous Lampouy."""
    if (date == "18/05/1152" and isinstance(valeur, str)
            and re.fullmatch(r"\d+(?:[.,]\d+)?°", valeur)):
        return CHOIX_LAMPOUY
    return valeur


class AlgorithmeBaseCadran(AlgorithmeManager):

    def __init__(self, layerManager: LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
        return [
            ("segment", "Segment", Segment()),
            ("cercleHoraire", "Heure", CercleHoraire()),
            ("partition", "Partition", Partition()),
            ("cercleDistance", "Distance", CercleDistance()),
            ("candidatBase", "Candidat", CandidatBase())
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
                "dataset.lettreDecl"]

    def __init__(self):
        # Variables input des autres modules
        self.dateDataset = ""
        self.lettreDom = ""
        self.lettreChoix = ""
        self.lettreDeclDataset = ""


# Affiché
        self.choixCalendrier = None
        super().__init__()

    def getValeursChoixCalendrier(self):
        return ["Standard", "Déclinaison"]

    def setup(self):
        # On calcule la déclinaison du soleil pour savoir si nous sommes au Printemps / Ete ou Automne / Hivers
        self.dateSegmentJD = MyJulianDate.fromString(self.dateDataset)
        self.lettreDom = self.dateSegmentJD.lettreDominicale()
        self.lettreChoix = self.lettreDom
        self.choixCalendrier = "Standard"

    def calculer(self):
        self.lettreChoix = self.lettreDom if self.choixCalendrier == "Standard" else self.lettreDeclDataset


class CercleHoraire(ModuleAlgo):
    def getEntreesModules(self):
        return ["segment.choixCalendrier",
                "dataset.stylet",
                "dataset.sentinelleStylet",
                "dataset.date",
                "segment.lettreChoix"]

    def getValeursHeureAMPM(self):
        return ["AM", "PM"]

    def getValeursCercleAMPM(self):
        return ["AM", "PM"]

    def getValeursHeureSubstitution(self):
        liste = ["=", "+2", "-2", "Clef", "Clef 2", "11:00"]
        if self.dateDataset == "18/05/1152":
            liste.append(CHOIX_LAMPOUY)
        return liste

    def __init__(self):
        # Variables input des autres modules
        self.choixCalendrierSegment = None
        self.styletDataset = None
        self.sentinelleStyletDataset = ""
        self.diagnosticAffectation = ""
        self.lettreChoixSegment = None
        self.dateDataset = None

        # Variable IHM
        self.stylet = None
        self.heureStylet = None
        self.styletAMPM = None
        self.heureSentinelle = None
        self.lieuObservation = "Carnac"
        self.heureAMPM = "AM"
        self.heureSubstitution = "="
        self.angleHoraire = None
        self.cercleAMPM = "AM"
        self.cercleHoraire = None
        self.sentinelle = Sentinelle("data/sentinelle.csv")
        self.selectionHoraire = None
        self.heureStyletSecondes = None
        self.heureSentinelleSecondes = None
        self.horaireLampouy = False
        self.noteHoraire = None
        self.brancheReference = None
        self.dateObservationUT1 = None
        self.heureUTC = None
        self.azimutSoleil = None
# Output
        self.coordPointChoix = (0, 0)

    def calculer(self):
        # On initialise la valeur du stylet avec celui défini par le segment par défaut
        self.heureSubstitution = normaliserSubstitutionLampouy(self.heureSubstitution, self.dateDataset)
        self.stylet = self.styletDataset

        # On récupère l'heure associée au stylet
        self.pointStylet = PointGraphique(villes_dict[self.stylet])
        px, py = self.pointStylet.coordonneesPixelAbs()

        code = self.sentinelleStyletDataset
        if code is None or code == "":
            self.diagnosticAffectation = f"Stylet {self.stylet} sans SentinelleStylet : recherche automatique de compatibilité"
            logging.getLogger(__name__).warning(self.diagnosticAffectation)
            self.selectionHoraire = self.sentinelle.rechercherLigneHoraire(px, py)
        else:
            if not isinstance(code, str) or re.fullmatch(r"S[1-7]M?", code) is None:
                raise ValueError(f"SentinelleStylet invalide pour {self.stylet} : {code!r} (attendu S1 à S7 ou S1M à S7M)")
            ref = self.sentinelle.referentiel.get(code[:2])
            branche = "miroir" if code.endswith("M") else "directe"
            direction = self.sentinelle.directionPourNote(ref.note, branche)
            ligne = self.sentinelle.afficherLigneHoraire(ref.note, branche, "construction")
            distance = int(self.pointStylet.distanceLigne(ligne))
            self.selectionHoraire = SelectionHoraire(
                distance < 20, ref.identifiant, ref.note, branche, direction.branche,
                direction.heure_locale, direction.azimut, ligne.orientation_grille,
                ligne.getAzimutCarte(), distance)
            self.diagnosticAffectation = f"Stylet {self.stylet} affecté explicitement à {code} ({ref.note}, {branche})"
        self.heureStylet = self.selectionHoraire.heure_locale.toString()
        self.heureStyletSecondes = self.selectionHoraire.heure_locale.secondes
        self.styletAMPM = self.selectionHoraire.ampm

        # On a deux cas: Si lampouy, on suppose que l'angle est l'angle des aligmenets de Lampouy
        self.horaireLampouy = self.heureSubstitution not in ("=", "+2", "-2", "Clef", "Clef 2", "11:00")
        if self.horaireLampouy:
            if self.heureSubstitution != CHOIX_LAMPOUY:
                raise ValueError(f"Substitution angulaire inconnue : {self.heureSubstitution}")
            # Lecture fraîche avec le lecteur existant, sans recalibration horaire.
            lecture = LectureSentinelles.__new__(LectureSentinelles)
            lecture.fichierSentinelles = {}
            lecture.chargerFichier(self.sentinelle.chemin_csv)
            azimutSoleil = float(lecture.fichierSentinelles["Lampouy"]["Azimut"])
            self.noteHoraire = "L"
            self.brancheReference = "historique_" + self.heureAMPM
            # Substitution d'angle uniquement : préserver l'heure antérieure,
            # comme dans le mécanisme historique, sans lui substituer celle de L.
            self.dateObservationUT1 = None  # l'angle est imposé, pas calculé à cette heure
            self.heureUTC = None
        else:
            # On prend en compte les heures de substitution
            if self.heureSubstitution == "11:00":
                choixNote = "J"
            else:
                if self.choixCalendrierSegment == "Standard":
                    noteDepart = self.selectionHoraire.note
                else:
                    noteDepart = self.lettreChoixSegment
                # Le Joker reste hors de la gamme, même avec +2 ou -2.
                if noteDepart == "J":
                    choixNote = noteDepart
                else:
                    choixNote = noteAvecSubstitution(noteDepart, self.heureSubstitution)
            self.noteHoraire = choixNote
            direction = self.sentinelle.directionPourNote(choixNote, "AM")
            self.brancheReference = ("directe" if direction is self.sentinelle.par_note[choixNote].directe else "miroir")
            heure = self.sentinelle.heurePourNote(choixNote, "AM")
            if self.heureAMPM == "PM":
                # Convention propre aux bases ; le miroir national reste astronomique.
                heure = HeureMoyenneLocale((86400 - heure.secondes) % 86400)
                self.brancheReference = "symetrie_tml"

            # On se place au lieu d'observation
            coordObs = villes_dict[self.lieuObservation].getCoordonneesGPS()
            (lat, lon) = coordObs
            contexte = ContexteObservation(self.lieuObservation, lat, lon, self.dateDataset)
            self.dateObservationUT1 = contexte.versUT1(heure)
            self.heureUTC = HeureMoyenneLocale(((float(self.dateObservationUT1) + .5) % 1) * 86400).toString()
            # On calcule l'angle entre la droite de Midi Solaire et la droite Stylet - ST Cyr
            _, azimutSoleil = positionSoleil((lat, lon), self.dateObservationUT1)
            self.heureSentinelle = heure.toString()
            self.heureSentinelleSecondes = heure.secondes
        self.azimutSoleil = azimutSoleil
        self.angleHoraire = 180-azimutSoleil
        if self.horaireLampouy and self.heureAMPM == "PM":
            self.angleHoraire = -self.angleHoraire  # seule la substitution angulaire historique
        elif not self.horaireLampouy:
            self.angleHoraire = abs(180 - azimutSoleil)  # le côté dépend uniquement de cercleAMPM

        # On crée la ligne Bourges - Stylet
        self.pointBourges = PointGraphique(villes_dict["Bourges"])
        ligneStyletBourges = LigneEntreVilles(villes_dict["Bourges"],
                                              villes_dict[self.stylet],
                                              nom=f"Axe Bourges - {self.stylet}"
                                              )

        # On trouve le centre entre Bourges et le Stylet
        centre = PointGraphique.depuisDeuxPoints(
            self.pointBourges,
            self.pointStylet,
            nom="Centre {self.stylet}- Bourges"
            )

        # On trouve les 2 points qui se situent à une certaine distance du centre.
        distanceBourgesStylet = self.pointBourges.distance(self.pointStylet)
        Lcercle = (distanceBourgesStylet/2) / tan(radians(self.angleHoraire/2))
        pt1, pt2 = ligneStyletBourges.pointsLateraux(centre, Lcercle)

        # On en choisit qui sera le 3ime point pour créer le cercle incrit par Bourges, Stylet et ce point.
        self.pointChoix = pt1 if self.cercleAMPM == "PM" else pt2
        self.coordPointChoix = self.pointChoix.coordonneesLambert()

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        # On rajoute Bourges et le stylet
        self.pointBourges.setEpaisseur(4)
        self.pointBourges.ajouterTag("level", "design")
        listeObjets.append(self.pointBourges)
        self.pointStylet.setEpaisseur(4)
        self.pointStylet.ajouterTag("level", "design")
        listeObjets.append(self.pointStylet)

        # On crée le cercle passant par les 3 points
        self.pointChoix.setCouleur((0, 0, 200))
        self.pointChoix.setEpaisseur(4)
        self.pointChoix.ajouterTag("level", "design")

        cercleHoraire = CercleGraphique.depuisTroisPoints(
            self.pointBourges, self.pointStylet, self.pointChoix,
            nom=f"Cercle horaire {self.cercleAMPM}",
            couleur=(0, 0, 200),
            tooltips=[f"CercleHoraire {self.cercleAMPM} ={self.angleHoraire:.2f}°"],
            tags={"level" : "construction"}
        )
        listeObjets.append(self.pointChoix)
        listeObjets.append(cercleHoraire)
        return listeObjets


class Partition(ModuleAlgo):
    MAX_NOTE_PARTITON = 11
    DISTANCE_FA_SOL = 91.5

    def getEntreesModules(self):
        return ["dataset.dateSegment",
                "dataset.lettreDecl",
                "dataset.date",
                "segment.lettreDom",
                "segment.lettreChoix",
                "cercleHoraire.stylet",
                "cercleHoraire.coordPointChoix",
                ]

    def getValeursLieuObservation(self):
        return LieuxObservation.getListeLieuxObservation(self.lettreDomSegment, self.dateDataset)

    def getValeursP2M2(self):
        return "=", "+2", "-2", "Clef", "Clef 2"

    def getValeursTypeSymetrie(self):
        return "Flip vertical", "Flip horizontal"

    def __init__(self):
        # Variables input des autres modules
        self.dateSegmentDataset = ""
        self.dateDataset = ""
        self.lettreDomSegment = ""
        self.lieuObservation = ""
        self.lettreDeclDataset = ""
        self.lettreChoixSegment = ""
        self.styletCerclehoraire = None
        self.coordPointChoixCerclehoraire = None

# Variables calculées/affichées
        self.leverSoleilUTC = None
        self.leverSoleilLocale = None
        self.leverlLocaleP6 = None
        self.heureUTCCarnac = None
        self.azimutSoleil = None
        self.P2M2 = "+2"
        self.lettrePartition = ""
        self.typeSymetrie = "Flip vertical"
        self.candidats = []

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])
        # On initialise le lieu d'observation
        self.lieuObservation = LieuxObservation.getDefautLieuObservation(self.lettreDomSegment)

    def calculer(self):
        # On recalcule les points graphiques
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])
        (x_l93, y_l93) = self.coordPointChoixCerclehoraire
        self.pointChoix = PointGraphique("3 points", x_l93, y_l93)

        # On calcule l'heure de lever  du soleil dans la ville d'observation (ex: Roncevaux)
        self.dateSegmentJD = MyJulianDate.fromString(self.dateSegmentDataset)
        coordObs = villes_dict[self.lieuObservation].getCoordonneesGPS()
        self.heureLeverSoleilJD = calculLeverSoleil(coordObs, self.dateSegmentJD)
        self.leverSoleilUTC = self.heureLeverSoleilJD.toString("HH:MM:SS")

        # On convertit en heure locale
        (_, lon) = coordObs
        self.leverSoleilLocale = convertirHeureLocaleVersUTC(self.leverSoleilUTC, lon, inverse=True)

        # On rajoute 6 heures
        leverlLocaleJD = MyJulianDate.fromString(self.dateSegmentDataset, self.leverSoleilLocale)+6/24
        self.leverlLocaleP6 = leverlLocaleJD.toString("HH:MM:SS")
        (latCarnac, lonCarnac) = villes_dict["Carnac"].getCoordonneesGPS()
        self.heureUTCCarnac = convertirHeureLocaleVersUTC(self.leverlLocaleP6, lonCarnac)

        # On calcule la position du soleil
        heureObsJD = MyJulianDate.fromString(self.dateSegmentDataset, self.heureUTCCarnac)
        _, self.azimutSoleil = positionSoleil((latCarnac, lonCarnac), heureObsJD)

        self.lettrePartition = noteAvecSubstitution(self.lettreChoixSegment, self.P2M2)

        # On doit calculer ici les lignes candidates
        self.pointCarignan = PointGraphique(villes_dict["Carignan"], epaisseur=4, afficherNom=True)
        self.pointMetz = PointGraphique(villes_dict["Metz"])
        self.ligneMetzCarignan = LigneEntreVilles(self.pointCarignan, self.pointMetz, nom="Axe Carignan - Metz")
        self.ligneMetzCarignanSymetrique = LigneAzimut(self.pointCarignan,
                                                       360-self.ligneMetzCarignan.getAzimutCarte(),
                                                       nom="Axe symetrique Carignan - Metz")

        self.listeLignesPartitions = []
        self.listeNotesPartition = []
        self.candidats = []

        def filtrageLignePartition(cercle: CercleGraphique, lignePartition: LigneGraphique, note: str, azimut: float):
            listePts = cercle.intersectionLigne(lignePartition)
            # Si elle a des intersections, on la rajoute
            # Le contrôle métrique évite qu'un arrondi du cache pixel élimine
            # une ligne admissible à la limite des 30 km.
            if listePts != [] or ecartDroiteCercle(
                    carteConfig.pixels_to_lambert93(*lignePartition.pointReference),
                    tuple(carteConfig.A_inv @ lignePartition.vecteur),cercleMetrique) <= 30 + TOL_METRES/1000:
                self.listeLignesPartitions.append((lignePartition, note, azimut))
                # Si elle est candidats, on al rajoute à la liste des lignes éligibles
                if note == self.lettrePartition:
                    self.candidats.append(lignePartition)

        # On recree le cercle pour filtrage
        cercleHeure = CercleGraphique.depuisTroisPoints(self.pointBourges, self.pointStylet, self.pointChoix)
        centre = cercleHeure.getCentre()
        rayon = cercleHeure.getRayonKm()
        # On crée un cercle de filtrage plus grand pour garder les lignes de partition qui frolent le cercle
        cercleFiltrage = CercleGraphique(centre, rayon+30)
        cercleMetrique = CercleMetrique(centre.coordonneesLambert(),rayon*1000)

        # On initialise les 2 lignes de partitions pour le Sol
        for azimut in [self.azimutSoleil, 360 - self.azimutSoleil]:
            lignePartition = LigneAzimut(self.pointCarignan, azimut)
            filtrageLignePartition(cercleFiltrage, lignePartition, "G", azimut)

        # On itère tous les 91.5km en rajoutant les 4 lignes
        note = ["C", "D", "E", "F", "G", "A", "B"]
        for i in range(1, Partition.MAX_NOTE_PARTITON+1):
            ptList = [0] * 4
            ptList[0], ptList[1] = self.ligneMetzCarignan.pointsEquidistants(self.pointCarignan, i*Partition.DISTANCE_FA_SOL)
            ptList[2], ptList[3] = self.ligneMetzCarignanSymetrique.pointsEquidistants(self.pointCarignan, i*Partition.DISTANCE_FA_SOL)
            indexNord = (4 + i) % len(note)
            indexSud = (4 - i) % len(note)

            for j in range(0, 4):
                if self.typeSymetrie == "Flip vertical":
                    nom = note[indexNord] if j in [0, 2] else note[indexSud]
                else:
                    nom = note[indexNord] if j in [0, 3] else note[indexSud]

                self.listeNotesPartition.append((ptList[j], nom))
                azimut = 360 - self.azimutSoleil if j in [0, 1] else self.azimutSoleil
                lignePartition = LigneAzimut(ptList[j], azimut, nom=f"{nom}")
                filtrageLignePartition(cercleFiltrage, lignePartition, nom, azimut)

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        # Le centre de l'axe
        self.pointCarignan.setNom("G")
        listeObjets.append(self.pointCarignan)

        # On crée la ligne Carigan - Metz
        self.ligneMetzCarignan.setTooltips(["Axe Carignan - Metz"])
        self.ligneMetzCarignan.ajouterTag("level", "design")
        listeObjets.append(self.ligneMetzCarignan)

        # On rajoute sa symétrique
        self.ligneMetzCarignanSymetrique.setTooltips(["Axe symétrique Carignan - Metz"])
        self.ligneMetzCarignan.ajouterTag("level", "design")
        listeObjets.append(self.ligneMetzCarignanSymetrique)

        def couleurPartition(note: str, choixNote: str):
            couleur = (164, 82, 0) if note == choixNote else (255, 193, 132)
            return couleur

        def niveauPartition(note: str, choixNote: str):
            return "construction" if note == choixNote else "design"

        # On parcourt a liste de notes, on rajoute les attributs graphiques et on les ajoutes dans la liste finale
        for pt, nom in self.listeNotesPartition:
            pt.setNom(nom)
            pt.setEpaisseur(4)
            pt.ajouterTag("level", "design")
            pt.setAfficherNom(True)
            listeObjets.append(pt)

        # On parcourt les lignes des partitions
        for ligne, note, azimut in self.listeLignesPartitions:
            ligne.setTooltips([f"Partiton {note}", f"Azimut {azimut:.02}"])
            ligne.ajouterTag("level", niveauPartition(note, self.lettrePartition))
            ligne.setCouleur(couleurPartition(note, self.lettrePartition))
            listeObjets.append(ligne)

        return listeObjets


class CercleDistance(ModuleAlgo):
    def getEntreesModules(self):
        return ["dataset.date",
                "dataset.lettreDecl",
                "segment.lettreDom",
                "segment.lettreChoix",
                "cercleHoraire.heureSentinelle",
                "cercleHoraire.heureSentinelleSecondes",
                "cercleHoraire.stylet"
                ]

    def getValeursCentreCercle(self):
        return "Ouverture", "Stylet"

    def getValeursP2M2(self):
        return "=", "+2", "-2", "Clef", "Clef 2"

    def getValeursOctave(self):
        return "x1", "x2", "/2"

    tableauGamme = {
        "C": ("2**-12/12", 2**(-12/12)),
        "B": ("2**-10/12", 2**(-10/12)),
        "A": ("2**-9/12", 2**(-9/12)),
        "G": ("2**-7/12", 2**(-7/12)),
        "F": ("2**-5/12", 2**(-5/12)),
        "E": ("2**-3/12", 2**(-3/12)),
        "D": ("2**-1/12", 2**(-1/12)),
    }
    tableauOctave = {
        "x1": 1,
        "x2": 2,
        "/2": 0.5
    }

    def __init__(self):
        # Variables input des autres modules
        self.dateDataset = ""
        self.lettreDeclDataset = ""
        self.lettreDomSegment = ""
        self.lettreChoixSegment = ""
        self.heureSentinelleCerclehoraire = ""
        self.heureSentinelleSecondesCerclehoraire = None
        self.heureReferenceSecondes = None
        self.dateObservationUT1 = None
        self.styletCerclehoraire = ""

        # variables calculées / affichage
        self.centreCercle = "Ouverture"
        self.centre = None
        self.heureReference = ""
        self.hauteurSoleil = None
        self.distanceClef = None
        self.P2M2 = "+2"
        self.lettreHauteur = ""
        self.hauteurStylet = None
        self.distanceRef = None
        self.octave = "x1"
        self.lieuObservation = "Carnac"

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])

    def calculer(self):
        # On crée les points de référence
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])

        # heure de référence
        self.heureReference = "12:00" if self.centreCercle == "Ouverture" else self.heureSentinelleCerclehoraire
        self.centre = self.pointBourges if self.centreCercle == "Ouverture" else self.pointStylet
        # On calculde la distance de référence % Metz ou % Carignan
        self.distanceClef = self.pointStylet.distance(PointGraphique(villes_dict["Metz"]))

        # On sélectionne la hauteur du stylet
        self.lettreHauteur = noteAvecSubstitution(self.lettreChoixSegment, self.P2M2)

        _, longFA = CercleDistance.tableauGamme["F"]
        _, longNote = CercleDistance.tableauGamme[self.lettreHauteur]
        self.hauteurStylet = self.distanceClef / longFA * longNote

        # On calcule la position du soleil
        (lat, lon) = villes_dict[self.lieuObservation].getCoordonneesGPS()
        if self.centreCercle == "Ouverture":
            heure = HeureMoyenneLocale(12 * 3600)  # midi moyen explicite, sans recours à S5
        elif self.heureSentinelleSecondesCerclehoraire is not None:
            heure = HeureMoyenneLocale(self.heureSentinelleSecondesCerclehoraire)
        else:
            texte = self.heureReference
            heure = HeureMoyenneLocale.depuisTexte(texte if texte.count(":") == 2 else texte + ":00")
        self.heureReferenceSecondes = heure.secondes
        self.dateObservationUT1 = ContexteObservation(self.lieuObservation, lat, lon, self.dateDataset).versUT1(heure)
        self.hauteurSoleil, _ = positionSoleil((lat, lon), self.dateObservationUT1)

        # On calcule la distance
        self.distanceRef = self.hauteurStylet * CercleDistance.tableauOctave[self.octave] / tan(radians(self.hauteurSoleil))

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        cercleDistance = CercleGraphique(
            self.centre,
            self.distanceRef,
            nom=f"Cercle Distance {self.lettreHauteur}",
            couleur=(0, 128, 0),
            tooltips=[f"CercleHoraire {self.lettreHauteur}",
                      f"Hauteur stylet ={self.hauteurStylet:.2f}km",
                      f"Distance : {self.distanceRef:2f}km"
                      ],
            tags={"level" : "construction"}
        )
        listeObjets.append(cercleDistance)

        return listeObjets


class CandidatBase(ModuleAlgo):

    RAYON_CANDIDAT = 20

    def getEntreesModules(self):
        return ["partition.candidats",
                "cercleDistance.distanceRef",
                "cercleDistance.centre",
                "cercleHoraire.stylet",
                "cercleHoraire.coordPointChoix"
                ]

    def __init__(self):
        self.coordPointChoixCerclehoraire = None
        self.styletCerclehoraire = None
        self.centreCercledistance = None
        self.distanceRefCercledistance = None
        self.candidatsPartition = None

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])

    def calculer(self, methode="ponderee"):
        self.methodeCandidats = methode
        self.geometriesCandidats = []
        self.diagnosticsCandidats = []
        if methode == "historique":
            return self.calculerHistorique()
        if methode != "ponderee":
            raise ValueError(f"Méthode de candidats BaseCadran inconnue : {methode}")
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])
        self.pointChoix = PointGraphique("3 points", *self.coordPointChoixCerclehoraire)
        # Conserver la construction existante ; travailler ensuite exclusivement
        # avec ses données normatives Lambert, jamais avec le cache du cercle pixel.
        horaire = CercleGraphique.depuisTroisPoints(self.pointBourges,self.pointStylet,self.pointChoix)
        self.listeCandidats = []
        if horaire is None:
            self.diagnosticsCandidats = [ResultatCandidatBase(rejet="cercle horaire dégénéré")]
            return
        cercle_h = CercleMetrique(horaire.pointCentre.coordonneesLambert(),horaire.getRayonKm()*1000)
        cercle_d = CercleMetrique(self.centreCercledistance.coordonneesLambert(),self.distanceRefCercledistance*1000)
        partitions = [(carteConfig.pixels_to_lambert93(*ligne.pointReference),
                       tuple(carteConfig.A_inv @ ligne.vecteur)) for ligne in self.candidatsPartition]
        self.geometriesCandidats,self.diagnosticsCandidats = chercherCandidatsBasePonderes(cercle_h,cercle_d,partitions)
        self.listeCandidats = [PointGraphique("Centre pondéré",*g.p) for g in self.geometriesCandidats]

    def calculerHistorique(self):
        # On crée les points de référence
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])
        (x_l93, y_l93) = self.coordPointChoixCerclehoraire
        self.pointChoix = PointGraphique("3 points", x_l93, y_l93)

        # On commence par calculer l'intersection entre les 2 cercles distance / horaire
        cercleHoraire = CercleGraphique.depuisTroisPoints(self.pointBourges, self.pointStylet, self.pointChoix)
        cercleDistance = CercleGraphique(self.centreCercledistance, self.distanceRefCercledistance)
        listePoints = cercleDistance.intersectionCercle(cercleHoraire)

        self.listeCandidats = []

        # Pas de points d'intersection, on calcule l'intersection entre les lignes partitions et les deux cercles.
        if len(listePoints) == 0:
            for ligne in self.candidatsPartition:
                listePoints1 = ligne.intersectionCercle(cercleHoraire)
                listePoints2 = ligne.intersectionCercle(cercleDistance)
                # On regarde ensuite la distance entre les deux points. Si ils sont assez proches l'un de l'autre,
                # c'est que les 2 cercles sont en fait assez proches sans se toucher
                distMin = 1000
                for p1 in listePoints1:
                    for p2 in listePoints2:
                        d = p1.distance(p2)
                        if d < distMin:
                            distMin = d
                            p1_ref = p1
                            p2_ref = p2
                if distMin < 20:
                    centreCandidat = PointGraphique.depuisDeuxPoints(p1_ref, p2_ref)
                    self.listeCandidats.append(centreCandidat)

        # On parcourt la liste des points
        for pt in listePoints:
            for ligne in self.candidatsPartition:
                ptProj = ligne.projectionPointGraphique(pt)
                dist = pt.distance(ptProj)
                if dist < 20:
                    centreCandidat = PointGraphique.depuisDeuxPoints(ptProj, pt)
                    self.listeCandidats.append(centreCandidat)

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []
        for index,pt in enumerate(self.listeCandidats):
            tooltips = []
            if getattr(self,"methodeCandidats","historique") == "ponderee":
                g = self.geometriesCandidats[index]
                def afficher(d):
                    return "indéterminée" if d is None else f"{d:.6f} km"
                tooltips = [f"Centre P (Lambert-93 m) : {g.p[0]:.3f}, {g.p[1]:.3f}",
                            f"Méthode : {g.methode}",
                            f"AB : {afficher(g.ab)} ; AC : {afficher(g.ac)} ; BC : {afficher(g.bc)}",
                            f"Segment retenu : {g.segment} ; d_min : {afficher(g.d_min)}",
                            "Angle indéterminé (secours AB)" if g.angle is None else f"Angle intérieur : {g.angle:.9f}°",
                            f"Poids t : {g.poids:.12f}",
                            f"P–cercle horaire : {afficher(g.contraintes[0])}",
                            f"P–cercle distance : {afficher(g.contraintes[1])}",
                            f"P–partition : {afficher(g.contraintes[2])}"]
                if g.traitement == "ponderee_intersections_cercles":
                    tooltips += ["Type : ponderee_intersections_cercles (cas 2, segment AB imposé)",
                                 f"Cercle non sécant : {g.cercle_non_secant}"]
                    for nom in ('a','b','c','m','g'):
                        point = getattr(g,nom)
                        tooltips.append(f"{nom.upper()} (m) : indéterminé" if point is None else
                                        f"{nom.upper()} (m) : {point[0]:.3f}, {point[1]:.3f}")
                if g.traitement == "secours_non_secant":
                    tooltips = [f"Centre P (Lambert-93 m) : {g.p[0]:.3f}, {g.p[1]:.3f}",
                                "Type : secours_non_secant", f"Cercle non sécant : {g.cercle_non_secant}",
                                f"A (m) : {g.a[0]:.3f}, {g.a[1]:.3f}", f"Q (m) : {g.q[0]:.3f}, {g.q[1]:.3f}",
                                f"AQ : {afficher(g.distance_aq)}", "Accepté : les trois contraintes sont à 20 km maximum",
                                f"P–cercle horaire : {afficher(g.contraintes[0])}",
                                f"P–cercle distance : {afficher(g.contraintes[1])}",
                                f"P–partition : {afficher(g.contraintes[2])}"]
            cercleCandidat = CercleGraphique(
                pt,
                CandidatBase.RAYON_CANDIDAT,
                epaisseur=2,
                nom="Candidat",
                tooltips=tooltips,
                tags={"level" : "construction"}
            )
            listeObjets.append(cercleCandidat)
        return listeObjets
