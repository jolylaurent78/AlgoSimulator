import csv
import math
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil, positionAstre, calculLeverAstre, calculLeverSoleil, calculCoucherSoleil, ASTRES
from src.calculAstronomique import MyJulianDate, decalage2Notes, decalage2Jours, getIndexesPourNote, convertirHeureLocaleVersUTC, heureSymetrique

# Affichage des objects graphiques
from src.affichage_objets import *

# Gestion des coordonnées / projection
from src.carte_config import lambert93_to_gps, pixels_to_lambert93

# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager

class AlgorithmeLumiereStyletInitial(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("config/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
            return [
                ("soleil", "default", Soleil())
            ]

    def appliquerParametresDepuisStructure(self):
        pass

    def getLargeurHauteurIHM(self):
        return 495, 600


#
# Gestion de l'objet Soleil: Gère l'observation.
# Pas de calcul à proprement parlé, juste l'initialsation de la lettre Dominicale et lieu d'observation'
#
class Soleil(ModuleAlgo):
    def getEntreesModules(self):
        return ["dataset.date"]

    def __init__(self):
# Variables input des autres modules
        self.dateDataset = ""
# Affiché
        self.lettreSeg = None
        self.lieuObservation = None
        self.heureLeverSoleilStrasbourg = None
        self.azimutLeverSoleil = None        
        self.rotationCarte = None
        self.tableauAzimut = []        

# Variables output pour les autres modules
        self.dateObservationJD = None
        self.coordObservation = None
        self.stylet = None
        self.heureSentinelle = None
        self.sensCarte = None
        super().__init__()


    # Les magniudes sont dans le sens inverse .. A, B, C => On prendra le décalage avec un principe note+2 C=>E
    tableauObservation = {
        "C": "Roncevaux",
        "B": "Bourges",
        "A": "Cherbourg",
        "G": "Dieppe",
        "F": "Bourges",
        "E": "Cherbourg",
        "D": "Dieppe"
    }
    tableauObservationDecale = {
        "C": "Cherbourg",
        "B": "Dieppe",
        "A": "Bourges",
        "G": "Cherbourg",
        "F": "Dieppe",
        "E": "Epernay",
        "D": "Bourges"
    }

    tableauHeures = ["09:43", "11:36", "11:42", "12:00", "10:22", "08:00", "08:12", "10:55" ]
    
    def setup(self):
        """
        Initialise la valeur par défaut de lieuObservation à partir de la lettre dominicale.
        Ce champ dépend d’un calcul mais doit être défini manuellement par l'utilisateur,
        donc on le prépare ici à titre d’initialisation.
        """

        # On calcule la déclinaison du soleil pour savoir si nous sommes au Printemps / Ete ou Automne / Hivers
        self.dateSegmentJD = MyJulianDate.fromString(self.dateDataset)
        self.lettreSeg = self.dateSegmentJD.lettreDominicale()

        # On calcule l'heure de lever et de coucher du soleil à Strasbourg pour savoir si Zeta est visible à cette date
        villeStrasbourg = villes_dict["Strasbourg"]
        coord_strasbourg = villeStrasbourg.getCoordonneesGPS()
        self.heureLeverSoleilStrasbourgJD = calculLeverSoleil(coord_strasbourg, self.dateSegmentJD)
        self.heureLeverSoleilStrasbourg = self.heureLeverSoleilStrasbourgJD.toString("HH:MM:SS")
        _, self.azimutLeverSoleil = positionSoleil(coord_strasbourg, self.heureLeverSoleilStrasbourgJD)
        self.rotationCarte = 90 - self.azimutLeverSoleil

        # On initialise le lieu d'observation
        self.lieuObservation = Soleil.tableauObservation.get(self.lettreSeg, "-")

        # On calcule d'abord l'azimut du soleil pour le tableau des 7 heures + Joker'
        date_str = "15/08/1066"
        coordCarnac = villes_dict["Carnac"].getCoordonneesGPS()
        (lat, lon) = coordCarnac

        for heureStr in Soleil.tableauHeures:
            heureLocale = heureStr + ":00"
            # On pase en heure UTC
            heureUTC = convertirHeureLocaleVersUTC(heureLocale, lon)
            # Création des objets date-heure
            date_am = MyJulianDate.fromString(date_str, heureUTC)
            # Calcul des positions
            _, az_am = positionSoleil((lat, lon), date_am)
            self.tableauAzimut.append((heureLocale, az_am))

         # On calcule ensuite l'axe du midi solaire Coetquidan - GF'
        self.pointCoetquidan = PointGraphique(villes_dict["Coetquidan"])
        self.pointGolfeJuan = PointGraphique(villes_dict["Golfe-Juan"])
        px1, py1 = self.pointCoetquidan.coordonneesPixelAbs()
        px2, py2 = self.pointGolfeJuan.coordonneesPixelAbs()
        ligneMidi = Ligne(px1, py1, px2, py2)
        self.azimutMidi = ligneMidi.azimut()

        self.tableauLignesHoraires = []
        for heureLocal, azimut in self.tableauAzimut:
            delta_am = (180 - azimut) % 360
            azimut_corrige_am = (self.azimutMidi + delta_am) % 360
            azimut_corrige_sym = (self.azimutMidi - delta_am) % 360
            ligneAM = Ligne.depuisPointEtAzimut(self.pointCoetquidan.coordonneesPixelAbs(), azimut_corrige_am)
            lignePM = Ligne.depuisPointEtAzimut(self.pointCoetquidan.coordonneesPixelAbs(), azimut_corrige_sym)
            self.tableauLignesHoraires.append((heureLocal, ligneAM, lignePM))
       

    def getValeursLieuObservation(self):
        ville1 = Soleil.tableauObservation.get(self.lettreSeg, "-")
        ville2 = Soleil.tableauObservationDecale.get(self.lettreSeg, "-")

        # On gère le cas Roncevaux en rajoutant "Gérardmer si présent"
        if ville1 ==  Soleil.tableauObservation.get("C"):
            solution = [ville1, "Gérardmer", ville2]
        elif ville2 == Soleil.tableauObservation.get("C"):
            solution = [ville1, ville2, "Gérardmer"]
        else:
            solution =[ville1, ville2]

        # Si la date du segment est le 18/05/1152, on rajoute Lampouy
        if self.dateDataset == "18/05/1152":
            solution.append("Lampouy")

        return solution
    

    # On calcule automatiquement l'heure de la sentinelle en fonction du stylet initial
    def calculer(self):
        # on skip tant que le stylet n'est pas défini
        if self.stylet is None:
            return

        self.pointStylet = PointGraphique(self.stylet)
        px, py = self.pointStylet.coordonneesPixelAbs()
        distMin = None
        heureMin = None
        sens = None
        for heureLocale, ligneAM, lignePM in self.tableauLignesHoraires:
            distAM = ligneAM.distanceAuPoint(px, py)
            distPM = lignePM.distanceAuPoint(px, py)
            if distMin is None:
                distMin = distAM
                heureMin = heureLocale
                sens = "AM"
            if distMin>distAM:
                distMin = distAM
                heureMin = heureLocale  
                sens = "AM"
            if distMin>distPM:
                distMin = distPM
                heureMin = heureLocale   
                sens = "PM"                            
            distMin = distAM if distMin>distAM else distMin

        self.heureSentinelle = heureMin
        self.sensCarte = sens