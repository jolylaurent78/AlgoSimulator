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
# Variables output pour les autres modules
        self.dateObservationJD = None
        self.coordObservation = None
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

        self.lieuObservation = Soleil.tableauObservation.get(self.lettreSeg, "-")


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
    
    def calculer(self):
        pass

