import csv
import math
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.calendrier180j import Calendrier180j
from src.Sentinelle import Sentinelle

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil, positionAstre, calculLeverAstre, calculLeverSoleil, calculCoucherSoleil, ASTRES
from src.calculAstronomique import MyJulianDate, decalage2Notes, decalage2Jours, getIndexesPourNote, convertirHeureLocaleVersUTC, heureSymetrique, decalageGamme

# Affichage des objects graphiques
from src.affichage_objets import *

# Gestion des coordonnées / projection
from src.carte_config import lambert93_to_gps, pixels_to_lambert93

# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager

class AlgorithmeBaseCadran(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
        return [
            ("segment", "default", Segment()),
            ("cercleHoraire", "default", CercleHoraire())
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
                "dataset.date",
                "segment.lettreChoix"]

    def getValeursHeureAMPM(self):
        return ["AM", "PM"]

    def getValeursHeureSubstitution(self):
        liste = ["Non", "11:00"]
        if self.dateDataset=="18/05/1152":
            liste.append("10:05")
        return liste 
         
    def __init__(self):
# Variables input des autres modules
        self.choixCalendrierSegment = None
        self.styletDataset = None
        self.lettreChoixSegment = None
        self.dateDataset = None

# Variable IHM
        self.stylet = None
        self.heureStylet = None
        self.styletAMPM = None
        self.heureSentinelle = None
        self.heureAMPM = "AM"
        self.heureSubstitution = "Non"
        self.angleHoraire = None
        self.sentinelle = Sentinelle("data/sentinelle.csv")

    def setup(self):
        # On initialise la valeur du stylet avec celui défini par le segment par défaut
        self.stylet = self.styletDataset

    def calculer(self):
        # On récupère l'heure associée au stylet
        self.pointStylet = PointGraphique(villes_dict[self.stylet])
        px, py = self.pointStylet.coordonneesPixelAbs()
        selection, self.heureStylet, self.styletAMPM, _, _ = self.sentinelle.surLigneHoraire(px, py)

        # On prend en compte les heures de substitution
        if self.heureSubstitution == "11:00":
            self.heureSentinelle = self.sentinelle["J"]["HeureLocale"]
        elif self.heureSubstitution == "10:05":
            self.heureSentinelle = "10:05"
        else:
            self.heureSentinelle = self.heureStylet if self.choixCalendrierSegment == "Standard" else self.sentinelle[self.lettreChoixSegment]["HeureLocale"]

        # On prend l'heure du matin ou de l'apres midi      
        self.heureSentinelle = heureSymetrique(self.heureSentinelle) if self.heureAMPM == "PM" else self.heureSentinelle

        # On se place à Carnac
        villeCarnac = villes_dict["Carnac"]
        coordCarnac = villeCarnac.getCoordonneesGPS()
        (lat, lon) = coordCarnac
        self.heureUTC = convertirHeureLocaleVersUTC(self.heureSentinelle, lon)
        heureObservationJD = MyJulianDate.fromString(self.dateDataset, self.heureUTC)        
        # On calcule l'angle entre la droite de Midi Solaire et la droite Stylet - ST Cyr
        hauteurSoleil, azimutSoleil = positionSoleil((lat, lon),heureObservationJD)
        self.angleHoraire = 180-azimutSoleil

        self.angleHoraire = self.angleHoraire if self.heureAMPM == "AM" else -self.angleHoraire


    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []    
        self.pointBourges = PointGraphique(villes_dict["Bourges"], epaisseur = 4)
        listeObjets.append(self.pointBourges)
        listeObjets.append(self.pointStylet)

        #On crée la droite Stylet - Bourges
        ligneStyletBourges = LigneEntreVilles(
            villes_dict["Bourges"], villes_dict[self.stylet],
            nom = f"Axe Bourges - {self.stylet}",
            tooltips = [f"Axe Bourges - {self.stylet}"],
            tags = {"level" : "design"},
            )   
        listeObjets.append(ligneStyletBourges)      

        # On trouve le centre entre Bourges et le Stylet
        centre = PointGraphique.depuisDeuxPoints(self.pointBourges, self.pointStylet, nom="Centre {self.stylet}- Bourges")
        # On trouve l'orthogonale à ligneStyletBourges passant par le centre
        orthogonale = ligneStyletBourges.orthogonale(centre)
        orthogonale.ajouterTag("level","design")
        listeObjets.append(orthogonale)

        # On trouve les 2 points qui se situe à une certaine distance du centre.
        distanceBourgesStylet = self.pointBourges.distance(self.pointStylet)
        Lcercle = (distanceBourgesStylet/2) / math.tan(radians(self.angleHoraire/2))
        pt1, pt2 = ligneStyletBourges.pointsLateraux(centre, Lcercle)
        pt1.setEpaisseur(4)
        pt1.ajouterTag("level","design")
        pt2.setEpaisseur(4)
        pt2.ajouterTag("level","design")
        listeObjets.append(pt1)  
        listeObjets.append(pt2)     

        # On crée le cercle passant par les 3 points
        cercleHoraire1 = CercleGraphique.depuisTroisPoints(
            self.pointBourges, self.pointStylet, pt1,
            nom = f"Cercle horaire",
            tooltips = [f"CercleHoraire PM ={self.angleHoraire:.2f}°"],
            tags = {"level" : "construction"}
        ) 
        cercleHoraire2 = CercleGraphique.depuisTroisPoints(
            self.pointBourges, self.pointStylet, pt2,
            nom = f"Cercle horaire",
            tooltips = [f"CercleHoraire AM ={self.angleHoraire:.2f}°"],
            tags = {"level" : "construction"}
        )  
        listeObjets.append(cercleHoraire1)  
        listeObjets.append(cercleHoraire2)           
        return listeObjets