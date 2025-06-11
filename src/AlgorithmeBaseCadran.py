import csv
import math
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet

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
        return ["dataset.note"]

    def __init__(self):
# Variables input des autres modules
        self.noteDataset = ""
# Affiché
        self.choixNote = None
        super().__init__()

    def getValeursChoixNote(self):
        return [self.choix1, self.choix2, self.choix3]
    
    def setup(self):
        self.choix1, self.choix2, self.choix3 = decalageGamme(self.noteDataset)
        self.choixNote = self.choix1

class CercleHoraire(ModuleAlgo):
    def getEntreesModules(self):
        return ["segment.choixNote",
                "dataset.stylet"]
    
    def __init__(self):
# Variables input des autres modules
        self.choixNoteSegment = None
        self.styletDataset = None
# Variable IHM
        self.stylet = None
        self.angleHoraire = None

    def setup(self):
        # On initialise la valeur du stylet avec celui défini par le segment par défaut
        self.stylet = self.styletDataset

    def calculer(self):
        # On calcule l'angle entre la droite de Midi Solaire et la droite Stylet - ST Cyr
        self.pointCoetquidan = PointGraphique(villes_dict["Coetquidan"])
        self.pointGolfeJuan = PointGraphique(villes_dict["Golfe-Juan"])
        px1, py1 = self.pointCoetquidan.coordonneesPixelAbs()
        px2, py2 = self.pointGolfeJuan.coordonneesPixelAbs()
        ligneMidi = Ligne(px1, py1, px2, py2)
        self.pointStylet = PointGraphique(villes_dict[self.stylet], epaisseur = 4)
        px3, py3 = self.pointStylet.coordonneesPixelAbs()  
        ligneHoraire = Ligne(px1, py1, px3, py3)
        self.angleHoraire = ligneHoraire.angleAvec(ligneMidi)      

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
            tooltips = [f"CercleHoraire ={self.angleHoraire:.2f}°"],
            tags = {"level" : "construction"}
        ) 
        cercleHoraire2 = CercleGraphique.depuisTroisPoints(
            self.pointBourges, self.pointStylet, pt2,
            nom = f"Cercle horaire",
            tooltips = [f"CercleHoraire ={self.angleHoraire:.2f}°"],
            tags = {"level" : "construction"}
        )  
        listeObjets.append(cercleHoraire1)  
        listeObjets.append(cercleHoraire2)           
        return listeObjets