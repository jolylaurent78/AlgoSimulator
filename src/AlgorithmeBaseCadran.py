import math

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import Sentinelle, LieuxObservation

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil, calculLeverSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC, heureSymetrique, decalageGamme

# Affichage des objects graphiques
from src.affichage_objets import *


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
        self.lieuObservation = ""

# Affiché
        self.choixCalendrier = None
        super().__init__()

    def getValeursChoixCalendrier(self):
        return ["Standard", "Déclinaison"]

    def getValeursLieuObservation(self):
        return LieuxObservation.getListeLieuxObservation(self.lettreDom, self.dateDataset)
    
    def setup(self):
        # On calcule la déclinaison du soleil pour savoir si nous sommes au Printemps / Ete ou Automne / Hivers
        self.dateSegmentJD = MyJulianDate.fromString(self.dateDataset)
        self.lettreDom = self.dateSegmentJD.lettreDominicale()
        self.lettreChoix = self.lettreDom       
        self.choixCalendrier = "Standard"

        # On initialise le lieu d'observation
        self.lieuObservation = LieuxObservation.getDefautLieuObservation(self.lettreDom)

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

    def getValeursCercleAMPM(self):
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
        self.cercleAMPM = "AM"
        self.cercleHoraire = None
# Output
        self.coordPointChoix = (0,0)  

    def calculer(self):
        # On initialise la valeur du stylet avec celui défini par le segment par défaut
        self.stylet = self.styletDataset

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

        # On crée la ligne Bourges - Stylet
        self.pointBourges = PointGraphique(villes_dict["Bourges"])
        ligneStyletBourges = LigneEntreVilles(
            villes_dict["Bourges"], 
            villes_dict[self.stylet], 
            nom = f"Axe Bourges - {self.stylet}"
            )   
        
        # On trouve le centre entre Bourges et le Stylet
        centre = PointGraphique.depuisDeuxPoints(
            self.pointBourges, 
            self.pointStylet, 
            nom="Centre {self.stylet}- Bourges"
            )
        
        # On trouve les 2 points qui se situent à une certaine distance du centre.
        distanceBourgesStylet = self.pointBourges.distance(self.pointStylet)
        Lcercle = (distanceBourgesStylet/2) / math.tan(radians(self.angleHoraire/2))
        pt1, pt2 = ligneStyletBourges.pointsLateraux(centre, Lcercle) 

        # On en choisit qui sera le 3ime point pour créer le cercle incrit par Bourges, Stylet et ce point.
        self.pointChoix = pt1 if self.cercleAMPM=="PM" else pt2
        self.coordPointChoix = self.pointChoix.coordonneesLambert()


    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []   

        # On rajoute Bourges et le stylet 
        self.pointBourges.setEpaisseur(4)
        self.pointBourges.ajouterTag("level","design")
        listeObjets.append(self.pointBourges)
        self.pointStylet.setEpaisseur(4)
        self.pointStylet.ajouterTag("level","design")
        listeObjets.append(self.pointStylet)

        # On crée le cercle passant par les 3 points
        self.pointChoix.setCouleur((0,0,200))
        self.pointChoix.setEpaisseur(4)
        self.pointChoix.ajouterTag("level","design")   

        cercleHoraire = CercleGraphique.depuisTroisPoints(
            self.pointBourges, self.pointStylet, self.pointChoix,
            nom = f"Cercle horaire {self.cercleAMPM}",
            couleur = (0,0,200),
            tooltips = [f"CercleHoraire {self.cercleAMPM} ={self.angleHoraire:.2f}°"],
            tags = {"level" : "construction"}
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
                "segment.lettreDom",
                "segment.lieuObservation",
                "segment.lettreChoix",
                "cercleHoraire.stylet",
                "cercleHoraire.coordPointChoix",
               ]

    def getValeursP2M2(self):
        return "+2", "-2"
    
    def __init__(self):
# Variables input des autres modules
        self.dateSegmentDataset = ""
        self.lettreDomSegment = ""
        self.lieuObservationSegment = ""
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
        self.candidats = []

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])

    def calculer(self):
        # On recalcule les points graphiques
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])
        (x_l93, y_l93) = self.coordPointChoixCerclehoraire
        self.pointChoix = PointGraphique("3 points", x_l93, y_l93)        

        # On calcule l'heure de lever  du soleil dans la ville d'observation (ex: Roncevaux)
        self.dateSegmentJD = MyJulianDate.fromString(self.dateSegmentDataset)
        coordObs = villes_dict[self.lieuObservationSegment].getCoordonneesGPS()
        self.heureLeverSoleilJD = calculLeverSoleil(coordObs, self.dateSegmentJD)
        self.leverSoleilUTC = self.heureLeverSoleilJD.toString("HH:MM:SS")
        
        # On convertit en heure locale
        (_, lon) = coordObs
        self.leverSoleilLocale = convertirHeureLocaleVersUTC(self.leverSoleilUTC, lon, inverse = True )

        # On rajoute 6 heures
        leverlLocaleJD = MyJulianDate.fromString(self.dateSegmentDataset, self.leverSoleilLocale)+6/24
        self.leverlLocaleP6 = leverlLocaleJD.toString("HH:MM:SS")
        (latCarnac,lonCarnac) = villes_dict["Carnac"].getCoordonneesGPS()
        self.heureUTCCarnac = convertirHeureLocaleVersUTC(self.leverlLocaleP6, lonCarnac )

        # On calcule la position du soleil
        heureObsJD = MyJulianDate.fromString(self.dateSegmentDataset, self.heureUTCCarnac)
        _, self.azimutSoleil = positionSoleil((latCarnac,lonCarnac), heureObsJD)

        listeNotes = decalageGamme(self.lettreChoixSegment)
        self.lettrePartition = listeNotes[2] if self.P2M2 == "+2" else listeNotes[1]

        # On doit calculer ici les lignes candidates
        self.pointCarignan = PointGraphique(villes_dict["Carignan"], epaisseur = 4, afficherNom=True)
        self.pointMetz = PointGraphique(villes_dict["Metz"])
        self.ligneMetzCarignan = LigneEntreVilles(self.pointCarignan, self.pointMetz, nom = f"Axe Carignan - Metz")
        self.ligneMetzCarignanSymetrique = LigneAzimut(self.pointCarignan, 360-self.ligneMetzCarignan.getAzimutCarte(), nom = f"Axe symetrique Carignan - Metz")

        self.listeLignesPartitions = []
        self.listeNotesPartition = []
        self.candidats = []      

        def filtrageLignePartition(cercle:CercleGraphique, lignePartition: LigneGraphique, note:str, azimut:float):
            listePts = cercle.intersectionLigne(lignePartition)
            # Si elle a des intersections, on la rajoute
            if listePts != []:
                self.listeLignesPartitions.append((lignePartition, note, azimut))
                # Si elle est candidats, on al rajoute à la liste des lignes éligibles
                if note == self.lettrePartition:
                    self.candidats.append(lignePartition)

       # On recree le cercle pour filtrage
        cercleFiltrage = CercleGraphique.depuisTroisPoints(self.pointBourges, self.pointStylet, self.pointChoix)      

        # On initialise les 2 lignes de partitions pour le Sol
        for azimut in [ self.azimutSoleil, 360- self.azimutSoleil]:
            lignePartition = LigneAzimut(self.pointCarignan, azimut)
            filtrageLignePartition(cercleFiltrage, lignePartition, "G", azimut )

        # On itère tous les 91.5km en rajoutant les 4 lignes
        note = ["C", "D", "E", "F", "G", "A", "B"]
        for i in range(1, Partition.MAX_NOTE_PARTITON+1):
            ptList = [0] * 4
            ptList[0], ptList[1] = self.ligneMetzCarignan.pointsEquidistants(self.pointCarignan, i*Partition.DISTANCE_FA_SOL)
            ptList[2], ptList[3] = self.ligneMetzCarignanSymetrique.pointsEquidistants(self.pointCarignan, i*Partition.DISTANCE_FA_SOL)
            indexNord = (4 + i) % len(note)
            indexSud = (4 - i) % len(note)

            for j in range(0,4):
                nom = note[indexNord] if j % 2 ==0 else note[indexSud]
                self.listeNotesPartition.append((ptList[j], nom))                      
                azimut = 360- self.azimutSoleil if j in [0, 1] else self.azimutSoleil
                lignePartition = LigneAzimut(ptList[j], azimut, nom = f"{nom}")
                filtrageLignePartition(cercleFiltrage, lignePartition, nom, azimut)


    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []   

        # Le centre de l'axe
        self.pointCarignan.setNom("G")
        listeObjets.append(self.pointCarignan)
        
        # On crée la ligne Carigan - Metz
        self.ligneMetzCarignan.setTooptips([f"Axe Carignan - Metz"])
        self.ligneMetzCarignan.ajouterTag("level","design")
        listeObjets.append(self.ligneMetzCarignan)

        # On rajoute sa symétrique
        self.ligneMetzCarignanSymetrique.setTooptips( [f"Axe symétrique Carignan - Metz"])
        self.ligneMetzCarignan.ajouterTag("level","design")        
        listeObjets.append(self.ligneMetzCarignanSymetrique)

                  
        def couleurPartition(note:str, choixNote:str):
            couleur = (164, 82, 0) if note == choixNote else (255, 193, 132)
            return couleur
        
        def niveauPartition(note:str, choixNote:str):
            return "construction" if note == choixNote else "design"
        
        # On parcourt a liste de notes, on rajoute les attributs graphiques et on les ajoutes dans la liste finale 
        for pt, nom in self.listeNotesPartition:
            pt.setNom(nom)  
            pt.setEpaisseur(4)
            pt.ajouterTag("level","design")
            pt.setAfficherNom(True)
            listeObjets.append(pt)

        # On parcourt les lignes des partitions
        for ligne, note, azimut in self.listeLignesPartitions:
            ligne.setTooptips([f"Partiton {nom}",f"Azimut {azimut:.02}"])
            ligne.ajouterTag("level",niveauPartition(nom, self.lettrePartition))
            ligne.setCouleur(couleurPartition(nom, self.lettrePartition))
            listeObjets.append(ligne)

        return listeObjets
    
class CercleDistance(ModuleAlgo):
    def getEntreesModules(self):
        return ["dataset.date",
                "dataset.lettreDecl",
                "segment.lettreDom",
                "cercleHoraire.heureSentinelle",
                "segment.lettreChoix",
                "cercleHoraire.stylet"
        ]
    
    def getValeursCentreCercle(self):
        return "Ouverture", "Stylet"

    def getValeursClef(self):
        return "Metz", "Carignan"   
    
    def getValeursP2M2(self):
        return "+2", "-2"

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
        self.lettreDomSegment = ""
        self.heureSentinelleCerclehoraire = ""
        self.lettreDeclDataset = ""
        self.lettreChoixSegment = ""  
        self.styletCerclehoraire = ""

        # variables calculées / affichage
        self.centreCercle = "Ouverture"
        self.centre = None
        self.heureReference = ""
        self.hauteurSoleil = None
        self.clef = "Metz"
        self.distanceClef = None
        self.P2M2 = "+2"
        self.lettreHauteur = ""
        self.hauteurStylet = None
        self.distanceRef = None
        self.octave = "x1"

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])


    def calculer(self):
        # On crée les points de référence
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])    

        # heure de référence 
        self.heureReference = "12:00" if self.centreCercle == "Ouverture" else self.heureSentinelleCerclehoraire
        self.centre = self.pointBourges if self.centreCercle == "Ouverture" else self.pointStylet
        #On calculde la distance de référence % Metz ou % Carignan
        pointMetz = PointGraphique(villes_dict["Metz"])
        pointCarignan = PointGraphique(villes_dict["Carignan"]) 
        self.distanceClef = self.pointStylet.distance(pointMetz) if self.clef == "Metz" else self.pointStylet.distance(pointCarignan)

        # On sélectionne la hauteur du stylet
        listeNotes = decalageGamme(self.lettreChoixSegment)
        self.lettreHauteur = listeNotes[2] if self.P2M2 == "+2" else listeNotes[1]
        _, longFA = CercleDistance.tableauGamme["F"]
        _, longNote = CercleDistance.tableauGamme[self.lettreHauteur]
        self.hauteurStylet = self.distanceClef / longFA * longNote

        # On calcule la position du soleil
        (latCarnac,lonCarnac) = villes_dict["Carnac"].getCoordonneesGPS()
        heureUTCCarnac = convertirHeureLocaleVersUTC(self.heureReference, lonCarnac )
        heureReferenceJD = MyJulianDate.fromString(self.dateDataset, heureUTCCarnac)
        self.hauteurSoleil, _ = positionSoleil((latCarnac,lonCarnac), heureReferenceJD)

        # On calcule la distance 
        self.distanceRef = self.hauteurStylet * CercleDistance.tableauOctave[self.octave] / math.tan(radians(self.hauteurSoleil))

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []   

        cercleDistance = CercleGraphique(
            self.centre,
            self.distanceRef,
            nom = f"Cercle Distance {self.lettreHauteur}",
            couleur = (0,128,0),
            tooltips = [f"CercleHoraire {self.lettreHauteur }", f"Hauteur stylet ={self.hauteurStylet:.2f}km", f"Distance : {self.distanceRef:2f}km"],
            tags = {"level" : "construction"}
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

    def calculer(self):
        # On crée les points de référence
        self.pointStylet = PointGraphique(villes_dict[self.styletCerclehoraire])     
        (x_l93, y_l93) = self.coordPointChoixCerclehoraire
        self.pointChoix = PointGraphique("3 points", x_l93, y_l93)

        # On commence par calculer l'intersection entre les 2 cercles distance / horaire
        cercleHoraire = CercleGraphique.depuisTroisPoints(self.pointBourges, self.pointStylet, self.pointChoix)  
        cercleDistance = CercleGraphique(self.centreCercledistance, self.distanceRefCercledistance)
        listePoints = cercleDistance.intersectionCercle(cercleHoraire)
        
        self.listeCandidats = []
        # Pas de points d'intersection, pas de candidats!
        if len(listePoints)==0:
            return

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
        for pt in self.listeCandidats:
            cercleCandidat = CercleGraphique(
                pt,
                CandidatBase.RAYON_CANDIDAT,
                epaisseur = 2,
                nom ="Candidat",
                tooltips=[],
                tags = {"level" : "construction"}
            ) 
            listeObjets.append(cercleCandidat)
        return listeObjets