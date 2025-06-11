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

class AlgorithmeLumiereStyletInitial(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
            return [
                ("soleil", "default", Soleil()),
                ("stylet", "default", Stylet())
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
        return ["dataset.date",
                "dataset.note",
                "dataset.stylet"]

    def __init__(self):
# Variables input des autres modules
        self.dateDataset = ""
        self.noteDataset = ""
        self.styletDataset = ""
# Affiché
        self.choixNote = None
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
    
    def getValeursChoixNote(self):
        return [self.choix, self.choix_plus2, self.choix_moins2]
    
    def getValeursChoixHeure(self):
        return ["Même heure", "Symétrique"]

    def getValeursLieuObservation(self):
        ville1 = Soleil.tableauObservation.get(self.choix, "-")
        ville2 = Soleil.tableauObservation.get(self.choix_plus2, "-")
        ville3 = Soleil.tableauObservation.get(self.choix_moins2, "-")
        solutions = [ville1]
        # on évite les doublons!
        if ville2 not in solutions:
            solutions.append(ville2)
        if ville3 not in solutions:
            solutions.append(ville3)
         # On gère le cas Roncevaux en rajoutant "Gérardmer si présent"
        if "Roncevaux" in solutions:
            solutions.append("Gérardmer")  # ou la ville que tu veux

        # Si la date du segment est le 18/05/1152, on rajoute Lampouy
        if self.dateDataset == "18/05/1152":
            solutions.append("Lampouy")

        return solutions

    def setup(self):
        """
        Initialise la valeur par défaut de lieuObservation à partir de la lettre dominicale.
        Ce champ dépend d’un calcul mais doit être défini manuellement par l'utilisateur,
        donc on le prépare ici à titre d’initialisation.
        """

        # On calcule la déclinaison du soleil pour savoir si nous sommes au Printemps / Ete ou Automne / Hivers
        self.dateSegmentJD = MyJulianDate.fromString(self.dateDataset)

        self.choix, self.choix_plus2, self.choix_moins2 = decalageGamme(self.noteDataset)
        self.choixNote = self.choix

        # On calcule l'heure de lever et de coucher du soleil à Strasbourg pour savoir si Zeta est visible à cette date
        villeStrasbourg = villes_dict["Strasbourg"]
        coord_strasbourg = villeStrasbourg.getCoordonneesGPS()
        self.heureLeverSoleilStrasbourgJD = calculLeverSoleil(coord_strasbourg, self.dateSegmentJD)
        self.heureLeverSoleilStrasbourg = self.heureLeverSoleilStrasbourgJD.toString("HH:MM:SS")
        _, self.azimutLeverSoleil = positionSoleil(coord_strasbourg, self.heureLeverSoleilStrasbourgJD)
        self.rotationCarte = 90 - self.azimutLeverSoleil

        # On initialise le lieu d'observation
        self.lieuObservation = Soleil.tableauObservation.get(self.noteDataset, "-")

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

        self.choixHeure = "Même heure"
        self.stylet = self.styletDataset

    

    # On calcule automatiquement l'heure de la sentinelle en fonction du stylet initial
    def calculer(self):
        # on skip tant que le stylet n'est pas défini
        if self.stylet is None:
            return

        self.pointStylet = PointGraphique(villes_dict[self.stylet])
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

        distance = self.pointStylet.pixelsVersMetres()*distMin/1000
        if distance<20:
            self.heureAMPM = sens
            self.validite = "Valide"
            symetrique = (sens == "PM" and self.choixHeure == "Même heure") or  (sens == "AM" and self.choixHeure == "Symétrique")
            self.heureSentinelle = heureSymetrique(heureMin) if symetrique else heureMin

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
                "soleil.choixNote",
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
        self.choixNoteSoleil = ""
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
    """   
    def getRegles(self):
        return [
            ["Si l'heure du stylet est AM, carte à l'envers et  si PM, carte à l'endroit", "sensCarte", self._regleSensCarte]
        ]
        
    def _regleSensCarte(self):

        if self.heureAMPMSoleil == "PM":
            return "Endroit"
        else:
            return "Envers"
    """

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
            (noteLongueurStr, noteLongueur) = Stylet.tableauGamme.get(self.choixNoteSoleil, ("-", 0))           
            self.formuleDistance =f"{float(self.distanceMetz):.0f} / {faLongueurStr} * {noteLongueurStr}"
            self.hauteurStylet = self.distanceMetz / faLongueur * noteLongueur

            #On calcule la position du soleil
            coordObservation = villes_dict[self.lieuObservationSoleil].getCoordonneesGPS()
            (lat, lon) = coordObservation
            heureObservationJD = MyJulianDate.fromString(self.dateDataset, self.heureUTCSoleil)
            self.hauteurSoleil, self.azimutSoleil = positionSoleil((lat, lon), heureObservationJD)
            self.distanceStylet =  self.hauteurStylet / math.tan(math.radians(self.hauteurSoleil))

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