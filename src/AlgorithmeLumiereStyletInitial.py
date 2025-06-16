import csv
import math
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import Sentinelle, LieuxObservation


# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil, calculLeverAstre, calculLeverSoleil, calculCoucherSoleil
from src.calculAstronomique import MyJulianDate, decalage2Notes, decalage2Jours, getIndexesPourNote, convertirHeureLocaleVersUTC, heureSymetrique, decalageGamme

# Affichage des objects graphiques
from src.affichage_objets import *

# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager

class AlgorithmeLumiereStyletInitial(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
            return [
                ("soleil", "Soleil", Soleil()),
                ("stylet", "Stylet", Stylet())
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
    HEURE_LAMPOUY = "10:26"

    def getEntreesModules(self):
        return ["dataset.date",
                "dataset.stylet"]

    def __init__(self):
# Variables input des autres modules
        self.dateDataset = ""
        self.styletDataset = ""
# Affiché
        self.lettreDom = None
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
        self.heureAMPM = None
        self.validite = None
        self.choixHeure = None
        self.heureUTC = None

        self.sentinelle = Sentinelle("data/sentinelle.csv")
        super().__init__()
  
    def getValeursChoixHeure(self):
        return ["Même heure", "Symétrique", Soleil.HEURE_LAMPOUY, heureSymetrique(Soleil.HEURE_LAMPOUY)]

    def getValeursLieuObservation(self):
        return LieuxObservation.getListeLieuxObservation(self.lettreDom, self.dateDataset)

    def setup(self):
        """
        Initialise la valeur par défaut de lieuObservation à partir de la lettre dominicale.
        Ce champ dépend d’un calcul mais doit être défini manuellement par l'utilisateur,
        donc on le prépare ici à titre d’initialisation.
        """

        # On calcule la déclinaison du soleil pour savoir si nous sommes au Printemps / Ete ou Automne / Hivers
        self.dateSegmentJD = MyJulianDate.fromString(self.dateDataset)
        self.lettreDom = self.dateSegmentJD.lettreDominicale()

        # On calcule l'heure de lever et de coucher du soleil à Strasbourg pour savoir si Zeta est visible à cette date
        villeStrasbourg = villes_dict["Strasbourg"]
        coord_strasbourg = villeStrasbourg.getCoordonneesGPS()
        self.heureLeverSoleilStrasbourgJD = calculLeverSoleil(coord_strasbourg, self.dateSegmentJD)
        self.heureLeverSoleilStrasbourg = self.heureLeverSoleilStrasbourgJD.toString("HH:MM:SS")
        _, self.azimutLeverSoleil = positionSoleil(coord_strasbourg, self.heureLeverSoleilStrasbourgJD)
        self.rotationCarte = 90 - self.azimutLeverSoleil

        # On initialise le lieu d'observation
        self.lieuObservation = LieuxObservation.getDefautLieuObservation(self.lettreDom)

        self.choixHeure = "Même heure"
        self.stylet = self.styletDataset

    

    # On calcule automatiquement l'heure de la sentinelle en fonction du stylet initial
    def calculer(self):
        # on skip tant que le stylet n'est pas défini
        if self.stylet is None:
            return

        self.pointStylet = PointGraphique(villes_dict[self.stylet])
        px, py = self.pointStylet.coordonneesPixelAbs()
        selection, heure, ampm, distance, self.azimutHeure = self.sentinelle.surLigneHoraire(px, py)

        if selection:
            self.heureAMPM = ampm
            self.validite = "Valide"
            if self.choixHeure  == Soleil.HEURE_LAMPOUY:
                self.heureSentinelle = Soleil.HEURE_LAMPOUY+":00"     
            elif self.choixHeure  == heureSymetrique(Soleil.HEURE_LAMPOUY):
                self.heureSentinelle = heureSymetrique(Soleil.HEURE_LAMPOUY)+":00"    
            else:
                symetrique = (ampm == "PM" and self.choixHeure == "Même heure") or  (ampm == "AM" and self.choixHeure == "Symétrique")
                self.heureSentinelle = heureSymetrique(heure) if symetrique else heure

             # on récupère les coords GPS de la ville d'observation
            (lat, lon) = villes_dict[self.lieuObservation].getCoordonneesGPS()
            self.heureUTC = convertirHeureLocaleVersUTC(self.heureSentinelle, lon)

        else:
            self.heureSentinelle = None
            self.heureAMPM = None
            self.heureUTC = None
            self.validite = "Unvalide"    


class Stylet(ModuleAlgo):
    def getEntreesModules(self):
        return ["dataset.date",
                "soleil.lettreDom",
                "soleil.heureAMPM",
                "soleil.lieuObservation",
                "soleil.rotationCarte",
                "soleil.stylet",
                "soleil.heureSentinelle",
                "soleil.heureUTC",
                "soleil.heureAMPM",
                "soleil.validite"
                ]

    
    def __init__(self):
# Variables input des autres modules
        self.dateDataset = ""
        self.lettreDomSoleil = ""
        self.heureAMPMSoleil = None
        self.lieuObservationSoleil = None
        self.rotationCarteSoleil = None
        self.validiteSoleil = None
        self.styletSoleil = None
        self.heureSentinelleSoleil = None
        self.heureAMPMSoleil = None
        self.heureUTCSoleil = None
# Affiché
        self.distanceMetz = None
        self.formuleDistance = None
        self.hauteurStylet = None
        self.hauteurSoleil = None
        self.azimutSoleil = None
        self.distanceStylet = None
        self.sensCarte = "Endroit"
        self.formuleAxeCarte = None
        self.axeCarte = None
        self.octave = "x1"

        super().__init__()

    RAYON_CANDIDAT = 20
 
    tableauGamme = {
        "C": ("2**-12/12", 2**(-12/12)),
        "B": ("2**-10/12", 2**(-10/12)),
        "A": ("2**-9/12", 2**(-9/12)),
        "G": ("2**-7/12", 2**(-7/12)),
        "F": ("2**-5/12", 2**(-5/12)),
        "E": ("2**-3/12", 2**(-3/12)),
        "D": ("2**-1/12", 2**(-1/12)),
    }

    def getValeursSensCarte(self):
        return ["Endroit", "Envers"]

    def getValeursOctave(self):
        return "x1", "x2", "/2"
    
    def setup(self):
        """
        Initialise la valeur par défaut de lieuObservation à partir de la lettre dominicale.
        Ce champ dépend d’un calcul mais doit être défini manuellement par l'utilisateur,
        donc on le prépare ici à titre d’initialisation.
        """

        # On initialise le point Metz pour le calcul de la distance     
        self.pointMetz = PointGraphique(villes_dict["Metz"])  


    # On calcule automatiquement l'heure de la sentinelle en fonction du stylet initial
    def calculer(self):

        if self.validiteSoleil == "Valide":
            #On calcule la distance % Metz
            pointStylet = PointGraphique(villes_dict[self.styletSoleil])
            self.distanceMetz = self.pointMetz.distance(pointStylet)
            # On calcule la formule en str du calcul de la hauteur
            (faLongueurStr, faLongueur) = Stylet.tableauGamme.get("F", ("-", 0))
            (noteLongueurStr, noteLongueur) = Stylet.tableauGamme.get(self.lettreDomSoleil, ("-", 0))           
            self.formuleDistance =f"{float(self.distanceMetz):.0f} / {faLongueurStr} * {noteLongueurStr}"
            self.hauteurStylet = self.distanceMetz / faLongueur * noteLongueur

            # On prend en compte l'octave
            tableauOctave = {"x1": 1, "x2": 2, "/2": 0.5}

            #On calcule la position du soleil
            coordObservation = villes_dict[self.lieuObservationSoleil].getCoordonneesGPS()
            (lat, lon) = coordObservation
            heureObservationJD = MyJulianDate.fromString(self.dateDataset, self.heureUTCSoleil)
            self.hauteurSoleil, self.azimutSoleil = positionSoleil((lat, lon), heureObservationJD)
            self.distanceStylet =  tableauOctave[self.octave] * self.hauteurStylet / math.tan(math.radians(self.hauteurSoleil))

            # On calcule l'axe final de la lumière
            if self.sensCarte == "Endroit":
                rotationCarteStr = f"+{float(self.rotationCarteSoleil):.2f}" if self.rotationCarteSoleil>=0 else f"{float(self.rotationCarteSoleil):.2f}"
                azimutSoleilStr = f"{float(self.azimutSoleil):.2f}"
                self.formuleAxeCarte = azimutSoleilStr + rotationCarteStr 
                self.axeCarte = self.azimutSoleil + self.rotationCarteSoleil
            else:
                rotationCarteStr = f"-{float(self.rotationCarteSoleil):.2f}" if self.rotationCarteSoleil>=0 else f"{float(-self.rotationCarteSoleil):.2f}"                   
                azimutSoleilStr = f"{float(self.azimutSoleil):.2f}"               
                self.formuleAxeCarte = "360-"+ azimutSoleilStr + rotationCarteStr
                self.axeCarte = 360 - self.azimutSoleil - self.rotationCarteSoleil

        else:
            self.heureSentinelle = None
            self.heureAMPM = None
            self.heureUTC = None
            self.distanceMetz = None      
            self.hauteurStylet = None 
            self.formuleAxeCarte = None


    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []
        if self.validiteSoleil == "Valide":
            villeOrigineTrait = villes_dict[self.styletSoleil]

            #
            # D'abord la construction du level 'Design'
            #
            origineStylet = PointGraphique(
                villeOrigineTrait,
                afficherNom = True,
                tags = {"level" : "design"}
            )
            listeObjets.append(origineStylet)

            if self.sensCarte =="Endroit":
                ligneLumiere= LigneAzimut(
                    villeOrigineTrait,
                    self.azimutSoleil,
                    f"Axe soleil observé",
                    couleur=(94,94,255), # Rouge  clair
                    tooltips = [f"Axe observation={self.azimutSoleil:.2f}°", f"Sens carte: {self.sensCarte}"],
                    tags = {"level" : "design"}
                )
                arcRotationLumiere = ArcOriente(
                    villeOrigineTrait,
                    150,
                    self.azimutSoleil,
                    self.rotationCarteSoleil,
                    nom = "Rotation",
                    epaisseur=1,
                    couleur = (64,64,0),  # LEs arc en rouge
                    style = "Arrow",
                    tooltips = [f"Rotation Carte={self.rotationCarteSoleil:.2f}°",f"Sens carte: {self.sensCarte}"],
                    tags = {"level" : "design"}
                    )
            else:
                ligneLumiere= LigneAzimut(
                    villeOrigineTrait,
                    360-self.azimutSoleil,
                    f"Axe soleil observé symetrique",
                    couleur=(94,94,255), # Rouge  clair
                    tooltips = [f"Axe observation={self.azimutSoleil:.2f}°"],
                    tags = {"level" : "design"}
                )    
                arcRotationLumiere = ArcOriente(
                    villeOrigineTrait,
                    150,
                    360-self.azimutSoleil,
                    -self.rotationCarteSoleil,
                    nom = "Rotation",
                    epaisseur=1,
                    couleur = (64,64,0),  # LEs arc en rouge
                    style = "Arrow",
                    tooltips = [f"Rotation Carte={-self.rotationCarteSoleil:.2f}°",f"Sens carte: {self.sensCarte}"],
                    tags = {"level" : "design"}
                    )         
            listeObjets.append(ligneLumiere)
            listeObjets.append(arcRotationLumiere)

            ligne = LigneAzimut(
                villeOrigineTrait,
                self.axeCarte,
                f"Axe Lumière après rotation",
                epaisseur=1,
                tooltips = [f"Axe apres rotation ={self.axeCarte:.2f}°"],
                tags = {"level" : "construction"}
                )
            listeObjets.append(ligne)

            cercle = CercleGraphique(
                origineStylet,
                self.distanceStylet,
                epaisseur = 1,
                nom ="Ombre du stylet",
                tooltips=[f"Hauteur soleil : {self.hauteurSoleil}", f"Distance  = {self.distanceStylet}km"],
                tags = {"level" : "construction"}
            )        
            listeObjets.append(cercle)

            intersections = cercle.intersectionLigne(ligne)
            px1, py1 = intersections[0]
            px2, py2 = intersections[1]
            pt1 = PointGraphique("intersection 1", px1, py1)
            pt2 = PointGraphique("intersection 2", px2, py2 )
            cercleCandidat1 = CercleGraphique(
                pt1,
                Stylet.RAYON_CANDIDAT,
                epaisseur = 2,
                nom ="Candidat",
                tooltips=[f"Hauteur soleil : {self.hauteurSoleil}", f"Distance  = {self.distanceStylet}km"],
                tags = {"level" : "construction"}
            )   
            listeObjets.append(cercleCandidat1)
            cercleCandidat2 = CercleGraphique(
                pt2,
                Stylet.RAYON_CANDIDAT,
                epaisseur = 2,
                nom ="Candidat",
                tooltips=[f"Hauteur soleil : {self.hauteurSoleil}", f"Distance  = {self.distanceStylet}km"],
                tags = {"level" : "construction"}
            ) 
            listeObjets.append(cercleCandidat2)

        return listeObjets