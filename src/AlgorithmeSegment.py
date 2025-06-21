import csv
import math
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import Sentinelle, LieuxObservation


# Librairie calcul astronomique
from src.calculAstronomique import trouverDatesPourDeclinaison, azimutHeliocentrique, trouverDatePourAzimut
from src.calculAstronomique import MyJulianDate, decalage2Notes, decalage2Jours, getIndexesPourNote, convertirHeureLocaleVersUTC, heureSymetrique, decalageGamme

# Affichage des objects graphiques
from src.affichage_objets import *

# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager

class AlgorithmeSegment(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
            return [
                ("segment", "Segment", SegmentChemin()),
                ("cadran", "Cadran", cadranSolaire()),
                ("planete", "Planete", PlaneteChemin()),
            ]

    def appliquerParametresDepuisStructure(self):
        pass

    def getLargeurHauteurIHM(self):
        return 550, 600


#
# Gestion de l'objet Soleil: Gère l'observation.
# Pas de calcul à proprement parlé, juste l'initialsation de la lettre Dominicale et lieu d'observation'
#
class SegmentChemin(ModuleAlgo):

    def getEntreesModules(self):
        return ["dataset.date",
                "dataset.extremite1",
                "dataset.milieuSegment",
                "dataset.extremite2",
                ]

    def getValeursChoixAngleStr(self):
        return f"{self.angle:.2f}°", f"{180-self.angle:.2f}°"
    
    def __init__(self):
# Variables input des autres modules
        self.dateDataset = ""
        self.extremite1Dataset = None
        self.extremite2Dataset = None
        self.milieuSegmentDataset = None   
# Affiché
        self.choixAngleStr = ""
        self.choixAngle = None
        self.angle = None
        self.ligne1 = None
        self.ligne2 = None

        self.listePts = []
        self.listeLignes = []
        super().__init__()
  
    def setup(self):
        self.pointExtremite1 = villes_dict[self.extremite1Dataset]
        self.pointMilieuSegment = villes_dict[self.milieuSegmentDataset]
        self.pointExtremite2 = villes_dict[self.extremite2Dataset]
        self.listePts = [self.pointExtremite1, self.pointMilieuSegment, self.pointExtremite2]

        self.ligne1 = LigneEntreVilles(self.pointExtremite1, self.pointMilieuSegment)
        self.ligne2 = LigneEntreVilles(self.pointExtremite2, self.pointMilieuSegment)
        self.listeLignes = [self.ligne1, self.ligne2]
    
        azimut1 = self.ligne1.getAzimutCarte()
        azimut2 = self.ligne2.getAzimutCarte()   
        self.angle = (azimut1 - azimut2) % 180
        self.choixAngleStr = f"{self.angle:.2f}°"

    def calculer(self):
        self.choixAngle = float(self.choixAngleStr[:-1])




    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        for pt in self.listePts:
            pt.setEpaisseur(4)
            pt.ajouterTag("level", "design")
            listeObjets.append(pt)
    
        for ligne in self.listeLignes:
            ligne.ajouterTag("level", "design")
            listeObjets.append(ligne)
      

        return listeObjets
    

class cadranSolaire(ModuleAlgo):

    def getEntreesModules(self):
        return ["dataset.date",
                "dataset.lettreSegment",
                "segment.choixAngle",
                ]

    def getValeursChoixAngleStr(self):
        return f"{self.angle:.2f}°", f"{float(180-self.angle):.2f}°"

    def getValeursLieuObservation(self):
        return LieuxObservation.getListeLieuxObservation(self.lettreSegmentDataset, self.dateDataset)
    
    def __init__(self):
# Variables input des autres modules
        self.dateDataset = None
        self.lettreSegmentDataset = None        
        self.choixAngleSegment = None
# Affiché
        self.lieuObservation = None
        self.latitude = None
        self.declinaison = None
        self.datePrintemps = ""
        self.dateEte = ""        

        super().__init__()
  
    def setup(self):
        # On initialise le lieu d'observation qui dépend de la lettre dominicale
        self.lieuObservation = LieuxObservation.getDefautLieuObservation(self.lettreSegmentDataset)

    def calculer(self):
        self.latitude, _ = villes_dict[self.lieuObservation].getCoordonneesGPS()

        # On calcule la déclinaison
        cosAngle = math.cos(radians(self.choixAngleSegment/2))
        cosLat = math.cos(radians(self.latitude))
        self.declinaison = math.degrees(math.asin(cosAngle*cosLat))

        datePrintempsJD, dateEteJD = trouverDatesPourDeclinaison(self.declinaison, 1066)
        self.datePrintemps = datePrintempsJD.toString("JJ/MM/AAAA")
        self.dateEte = dateEteJD.toString("JJ/MM/AAAA")



class PlaneteChemin(ModuleAlgo):

    def getEntreesModules(self):
        return ["dataset.date",
                "dataset.extremite1",
                "dataset.milieuSegment",
                "dataset.extremite2",
                ]

    def getValeursChoixSegment(self):
        return "=","1<->2","2<->3","1->2 2->3 3->1"

    def getValeursChoixAngle(self):
        return "=","symetrique", "complémentaire", "les deux"
    
    def getValeursBorneMin(self):
        return list(range(700, 1900, 100))
       
    def getValeursPeriode(self):
        return list(range(100, 500, 100))
    
    def getValeursListeAnnees(self):
        return (50, "Année"), (80, "Jour"), (80, "Sens"), (80,"Az Terre"), (80,"Az Planete"), (80,"Erreur")
    
    tableauPlanete = {
        "CD" : "Neptune",
        "DE" : "Uranus",
        "EF" : "Saturne",
        "FG" : "Jupiter",
        "GA" : "Mars",
        "AB" : "Pluton",
    }

    def __init__(self):
# Variables input des autres modules
        self.dateDataset = ""
        self.extremite1Dataset = None
        self.extremite2Dataset = None
        self.milieuSegmentDataset = None   
# Affiché
        self.choixSegment = "="
        self.sentinelle = Sentinelle("data/sentinelle.csv")      
        self.azimutCible = None
        self.azimutLigne1 = None
        self.planete = None

        self.extremite1 = None
        self.extremite2 = None
        self.milieuSegment = None  
        self.listeLignes = []

        self.axeTerreStr = ""
        self.axeTerre = None
        self.angle = None
        self.angleAnalyse = None    
        self.choixAngle = "="    

        self.borneMin = 1000
        self.periode = 100     
        self.annee = None   
        self.listeAnnees = []

        super().__init__()
  
    def setup(self):
        pass

    def calculer(self):
        # On recalcule le segment
        if self.choixSegment =="=":
            self.extremite1 = self.extremite1Dataset
            self.extremite2 = self.extremite2Dataset
            self.milieuSegment = self.milieuSegmentDataset
        elif self.choixSegment =="1<->2":  
            self.extremite1 = self.milieuSegmentDataset
            self.extremite2 = self.extremite2Dataset
            self.milieuSegment = self.extremite1Dataset         
        elif self.choixSegment =="2<->3":  
            self.extremite1 = self.extremite1Dataset
            self.extremite2 = self.milieuSegmentDataset
            self.milieuSegment = self.extremite2Dataset
        else:
            self.milieuSegment = self.extremite1Dataset  
            self.extremite2 = self.milieuSegmentDataset 
            self.extremite1 = self.extremite2Dataset
         
        pointExtremite1 = PointGraphique(villes_dict[self.extremite1])
        pointExtremite2 = PointGraphique(villes_dict[self.extremite2])
        pointMilieuSegment = PointGraphique(villes_dict[self.milieuSegment])
        self.listePts = [pointExtremite1, pointMilieuSegment, pointExtremite2]

        # On recalcule la ligne de choix de la planète
        self.ligne1 = LigneEntreVilles(pointMilieuSegment, pointExtremite1,)
        self.ligne2 = LigneEntreVilles(pointMilieuSegment, pointExtremite2)
        self.listeLignes=[self.ligne1, self.ligne2] 

        # Centre de l'abbaque
        self.lignesSentinelle = []
        self.centre = villes_dict[self.milieuSegment]

        # On calule l'azimut cible
        self.azimutLigne1= self.ligne1.getAzimutCarte()
        self.azimutLigne2= self.ligne2.getAzimutCarte()
        # On ne considèfre que des azimuts orientés vers le sud >90
        self.azimutLigne1= self.azimutLigne1 + 180 if self.azimutLigne1 <=90 else self.azimutLigne1
        # si l'azimut est inférieur à l'aziùut de Si, on prend le symétriqe
        self.azimutCible= 360 - self.azimutLigne1 if self.azimutLigne1 < self.sentinelle["B"]["AzimutGeant"] else self.azimutLigne1        

        listeNotes = ["C", "D", "E", "F", "G", "A", "B"]        
        previousNote = None
        previousAzimut = None
        for note in listeNotes:
            azimut = self.sentinelle[note]["AzimutGeant"]
            ligne = LigneAzimut(self.centre, azimut)
            self.lignesSentinelle.append((note, azimut, ligne))
          
            if (previousNote is not None) and (azimut < self.azimutCible <= previousAzimut):
                self.planete =  PlaneteChemin.tableauPlanete[f"{previousNote}{note}"]
            previousNote = note
            previousAzimut = azimut

        # On calcule l'axe de la Terre et son azimut
        self.axeTerreStr = self.milieuSegment + " -> " + self.extremite2
        self.axeTerre = self.azimutLigne2

        # On calcule l'angle et l'angle complémtentaire pour la recherche de l'année
        self.angle = (self.azimutLigne1 - self.azimutLigne2) % 180

        if self.choixAngle == "=":
            self.angleAnalyse = self.angle
        elif self.choixAngle == "symetrique":    
            self.angleAnalyse = (- self.angle) % 360
        elif self.choixAngle == "complémentaire":    
            self.angleAnalyse = 180 - self.angle
        else:
            self.angleAnalyse = 360 - (180 - self.angle) 



    def calculerAnnees(self, init):
        
        def testerAnnee(annee : int, 
                        azimut : float, 
                        jd_centre: float, 
                        delta_azimut:float, 
                        sens: str, 
                        planete:str, 
                        marge_erreur:float
                    ):
            jd_direct = trouverDatePourAzimut(azimut, annee, planete="Terre", jd_centre=jd_centre)

            az_planete = azimutHeliocentrique(jd_direct, planete, annee)
            az_cible1 = (azimut + delta_azimut) % 360
            az_cible2 = (azimut - delta_azimut) % 360

            if abs((az_planete - az_cible1 + 180) % 360 - 180) <= marge_erreur or \
                abs((az_planete - az_cible2 + 180) % 360 - 180) <= marge_erreur:
                erreurCible = min(abs(az_cible1 -az_planete)  , abs(az_cible2 -az_planete))
                self.listeAnnees.append((annee, jd_direct, sens, f"{azimut:.2f}°", f"{az_planete:.2f}°", f"{erreurCible:.2f}°"))
                # print(f"Année: {annee} - Jour: {jd_direct.toString("JJ/MM/AAAA")} - Sens: {sens} - Az Terre: {azimut} - Az Planete {az_planete}")
            y, m, d = jd_direct.enTuple()
            return MyJulianDate(d, m, y+1)        
        
        if init:
            self.listeAnnees = []
            self.jd_centre_direct = None
            self.jd_centre_oppose = None
            self.annee = float(self.borneMin)

            return False

        else:
            self.jd_centre_direct = testerAnnee(self.annee, 
                                                self.axeTerre, 
                                                self.jd_centre_direct, 
                                                self.angleAnalyse, 
                                                "Identique", 
                                                self.planete, 
                                                3
                                            )
            
            self.jd_centre_oppose = testerAnnee(self.annee,
                                                (self.axeTerre + 180) % 360, 
                                                self.jd_centre_oppose, 
                                                self.angleAnalyse, 
                                                "Opposé", 
                                                self.planete, 
                                                3
                                            )
            self.annee += 1

        return True if self.annee> float(self.borneMin) + float(self.periode) else False



    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []

        # On trace les extrémités et les 2 lignes 
        for pt in self.listePts:
            pt.setEpaisseur(4)
            pt.setCouleur((21, 0, 136))
            pt.ajouterTag("level", "design")
            listeObjets.append(pt)

        for ligne in self.listeLignes:
            ligne.ajouterTag("level", "design")
            ligne.setCouleur((21, 0, 136))
            listeObjets.append(ligne)
        
        # On rajoute une ligne si l'azimut cible est symétrique à l'azimut de la ligne pour la représentation visuelle
        if self.azimutLigne1 != self.azimutCible:
            ligneCible = LigneAzimut(self.centre, self.azimutCible,
                nom = f"Ligne Cible pour sélection planète",
                couleur = (21, 0, 136),
                tags = {"level" : "design"},
                )
            listeObjets.append(ligneCible)  
        
        azimutPrevious = None
        notePrevious = ""
        distance = 150                
        for note, azimut, ligne in self.lignesSentinelle:
            ligne.setCouleur((255, 193, 132))
            ligne.setTooltips([f"Note: {note}", f"Azimut: {azimut}"])
            listeObjets.append(ligne)
            if azimutPrevious is not None:
                arc = ArcOriente(self.centre, distance, 
                    azimutPrevious, azimut-azimutPrevious,
                    nom  = PlaneteChemin.tableauPlanete[f"{notePrevious}{note}"],
                    tags = {"level" : "design"},
                    )
                arc.setAfficherNom(True)
                listeObjets.append(arc)
            azimutPrevious = azimut
            notePrevious = note
            distance+=20
        return listeObjets

