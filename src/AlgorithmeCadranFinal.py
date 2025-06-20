import math

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import Sentinelle, LieuxObservation

# Librairie calcul astronomique
from src.calculAstronomique import positionSoleil, calculZenithSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC, heureSymetrique, decalageGamme

# Affichage des objects graphiques
from src.affichage_objets import *


# Base de données des villes
from src.data_loader import villes_dict

# Gestion des layers graphiques
from src.layerManager import LayerManager

class AlgorithmeCadranFinal(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
        return [
            ("segment", "Segment", Segment()),
            ("stylet", "stylet", StyletFinal()),
            ("lumiere", "lumiere", LumiereFinal()),
            ("ombre", "ombre", LigneHoraireFinal()),
            ("candidat", "candidat", CandidatFinal()),
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
    HEURE_LAMPOUY = "10:26"

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
        return "=", "+2", "-2"

    def getValeursOctave(self):
        return "x1", "x2", "/2", "/4", "/8"
    
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
        tabDec = {"=":0,"+2":2,"-2":1}
        listeNotes = decalageGamme(self.lettreChoix, False) # On décale sans susbtition Fa/Sol
        self.lettre = listeNotes[tabDec[self.P2M2]] 

        longFA = StyletFinal.tableauGamme["F"]
        longNote = StyletFinal.tableauGamme[self.lettre]
        self.hauteur = StyletFinal.tableauOctave[self.octave] * self.distanceRef / longFA * longNote

        # On calcule l'azimut de Midi
        (x1, y1) = villes_dict["Bourges"].getCoordonneesPixel()
        (x2, y2) = villes_dict[self.base].getCoordonneesPixel()
        self.azimutMidi = Ligne(x1, y1, x2, y2).azimut()

    COULEUR_TRAIT_MIDI = (255, 145, 34)
    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []   

        # On rajoute le stylet Initial
        pointStylet = PointGraphique(villes_dict[self.styletDataset],
            nom = f"Stylet : {self.styletDataset}",
            epaisseur = 4, 
            couleur = (0,0,128),
            tooltips= [f"Stylet Initial {self.styletDataset}"],
            tags = {"level" : "design"}
        )
       
        # On rajoute Bourges , la base du stylet et son axe Midi
        pointBourges = PointGraphique(villes_dict["Bourges"], 
            nom = "Ouverture",
            epaisseur = 4,
            couleur = StyletFinal.COULEUR_TRAIT_MIDI,
            tooltips = ["Extremité du stylet"],
            tags = {"level" : "design"}
            )
        pointBase = PointGraphique(villes_dict[self.base],
            nom = "Base stylet",
            epaisseur = 4,
            couleur = StyletFinal.COULEUR_TRAIT_MIDI,
            tooltips = ["Extremité du stylet"],
            tags = {"level" : "design"}
            )
        ligneMidi = LigneEntreVilles(pointBourges, pointBase,
            nom = "Axe Midi",
            epaisseur = 1,
            couleur = StyletFinal.COULEUR_TRAIT_MIDI,
            tooltips = ["Axe Midi Bourges - {self.base}"],
            tags = {"level" : "design"}
            )
        listeObjets.append(pointBourges)
        listeObjets.append(pointBase)
        listeObjets.append(ligneMidi)
        listeObjets.append(pointStylet)
        return listeObjets
    

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
    
    HEURE_LAMPOUY = "10:26"
    def getValeursChoixHeure(self):
        list =["=", "+2", "-2", "11:00"] 
        if self.dateDataset == "18/05/1152":
            list.append(LumiereFinal.HEURE_LAMPOUY)
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
        self.heureUTC =""
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
            self.heureLocale = self.sentinelle["J"]["HeureLocale"]
        elif self.choixHeure == LumiereFinal.HEURE_LAMPOUY:
            self.heureLocale = LumiereFinal.HEURE_LAMPOUY
        else:
            tabDec = {"=":0,"+2":2,"-2":1}
            listeNotes = decalageGamme(self.lettreChoix, False) # On décale sans susbtition Fa/Sol
            choixNote = listeNotes[tabDec[self.choixHeure]] 
            self.heureLocale = self.sentinelle[choixNote]["HeureLocale"]

        # On prend l'heure du matin ou de l'apres midi      
        self.heureLocale = heureSymetrique(self.heureLocale) if self.heureAMPM == "PM" else self.heureLocale

        # On passe en UTC
        self.heureUTC = convertirHeureLocaleVersUTC(self.heureLocale, lon)
        heureObservationJD = MyJulianDate.fromString(self.dateSegmentDataset, self.heureUTC)
        # On calcule l'angle entre la droite de Midi Solaire et la droite Stylet - ST Cyr
        self.hauteur, self.azimut = positionSoleil(coordObs,heureObservationJD)

        # delta & distance
        self.deltaMidi = 180 - self.azimut
        self.distance = self.hauteurStylet / math.tan(radians(self.hauteur))

    COULEUR_TRAIT_CANDIDAT = (36, 28, 237)
    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []   

        # On crée le cercle autour de Bourges
        centre = villes_dict["Bourges"]
        cercleLumiere= CercleGraphique(
            centre,
            self.distance,
            nom = f"Cercle Lumiere",
            couleur = LumiereFinal.COULEUR_TRAIT_CANDIDAT,
            tooltips = [f"Heure {self.heureLocale }", 
                        f"Hauteur Soleil ={self.hauteur:.2f}°",
                        f"Hauteur stylet ={self.hauteurStylet:.2f}km", 
                        f"Distance : {self.distance:2f}km"
                        ],
            tags = {"level" : "construction"}
        ) 
        listeObjets.append(cercleLumiere)  

        # On ajoute l'axe de lumière
        deltaAzimutSoleil = self.azimut - 180
        ligneLumiere1 = LigneAzimut(centre, (self.azimutMidiStylet + deltaAzimutSoleil) % 360,
            nom = f"Ligne Lumiere",
            couleur = LumiereFinal.COULEUR_TRAIT_CANDIDAT,
            tooltips = [f"Heure {self.heureLocale }", 
                        f"Azimut %Sud Soleil ={deltaAzimutSoleil:.2f}°",
                        ],
            tags = {"level" : "construction"} 
            )
        listeObjets.append(ligneLumiere1)  
        ligneLumiere2 = LigneAzimut(centre, (self.azimutMidiStylet - deltaAzimutSoleil) % 360,
            nom = f"Ligne Lumiere",
            couleur = LumiereFinal.COULEUR_TRAIT_CANDIDAT,
            tooltips = [f"Heure {self.heureLocale }", 
                        f"Azimut %Sud Soleil ={deltaAzimutSoleil:.2f}°",
                        ],
            tags = {"level" : "construction"} 
            )
        listeObjets.append(ligneLumiere2)  
        return listeObjets
    
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
        list =["=", "+2", "-2", "11:00"] 
        if self.dateDataset == "18/05/1152":
            list.append(LumiereFinal.HEURE_LAMPOUY)
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
        self.azimutMidiLocale = None

        self.heureLocale = ""
        self.listeCandidatsHeure = []
        self.sensCarte = "Endroit"

    def setup(self):
        self.pointBourges = PointGraphique(villes_dict["Bourges"])        
        self.lettreChoix = self.lettreDomSegment  
        
    def calculer(self):
        self.lettreChoix = self.lettreDomSegment if self.choixCalendrier == "Standard" else self.lettreDeclDataset

        # On prend en compte les heures de substitution
        if self.choixHeure == "11:00":
            self.heureLocale = self.sentinelleLumiere["J"]["HeureLocale"]
        elif self.choixHeure == LumiereFinal.HEURE_LAMPOUY:
            self.heureLocale = LumiereFinal.HEURE_LAMPOUY
        else:
            tabDec = {"=":0,"+2":2,"-2":1}
            listeNotes = decalageGamme(self.lettreChoix, False) # On décale sans susbtition Fa/Sol
            choixNote = listeNotes[tabDec[self.choixHeure]] 
            self.heureLocale = self.sentinelleLumiere[choixNote]["HeureLocale"]

        #On calcule l'écart d'azimut entre Midi solaire et Midi locale à Carnac
        coordObs = villes_dict["Carnac"].getCoordonneesGPS()
        (lat, lon) = coordObs
        # On calcule l'heure de Midi solaire et l'écart d'azimut
        heureMidiUTC = convertirHeureLocaleVersUTC("12:00", lon)
        jourObservationJD = MyJulianDate.fromString(self.dateSegmentDataset, heureMidiUTC)
        _, self.azimutMidiLocale = positionSoleil(coordObs,jourObservationJD)     

        #On crée les lignes horaires
        self.listeLigneHoraire = []
        self.listeCandidatsHeure = []
        self.pointBase = PointGraphique(villes_dict[self.baseStylet])
        # On crée les lignes horaires
        tableauNotes = ["C", "B", "A", "G", "F", "E", "D", "J"]
        for note in tableauNotes:
            heureLocaleAM =self.sentinelleLumiere[note]["HeureLocale"]
            # Les lignes horaires sont positionnées sur l'axe de Midi local
            deltaAzimutMidiLocale = 180 - self.azimutMidiLocale
            deltaAzimutMidiLocale = deltaAzimutMidiLocale if self.sensCarte == "Endroit" else -deltaAzimutMidiLocale
            delta_azimutSenstinelle = 180 - self.sentinelleLumiere[note]["AzimutCalibre"]
            azimutAM = self.azimutMidiStylet - delta_azimutSenstinelle + deltaAzimutMidiLocale
            azimutPM = self.azimutMidiStylet + delta_azimutSenstinelle + deltaAzimutMidiLocale
            ligneHoraireAM = LigneAzimut(self.pointBase, azimutAM)        
            heureLocalePM = heureSymetrique(heureLocaleAM)
            ligneHorairePM = LigneAzimut(self.pointBase, azimutPM)
 
            if self.heureLocale == heureLocaleAM:
                self.listeCandidatsHeure.append((heureLocaleAM, ligneHoraireAM))
                self.listeCandidatsHeure.append((heureLocalePM, ligneHorairePM)) 
                candidat = True
            else:
                candidat = False

            self.listeLigneHoraire.append((heureLocaleAM, - delta_azimutSenstinelle + deltaAzimutMidiLocale, "AM", candidat, ligneHoraireAM ))              
            self.listeLigneHoraire.append((heureLocalePM, delta_azimutSenstinelle + deltaAzimutMidiLocale, "PM", candidat, ligneHorairePM ))   


    COULEUR_TRAIT_HEURE = (255, 193, 132)
    COULEUR_TRAIT_CANDIDAT = (164, 82, 0) 
    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        listeObjets = []   

        for heureLocale, azimut, ampm, candidat, ligneGraphique in self.listeLigneHoraire:
            heureLocaleSymetrique = heureSymetrique(heureLocale)
            ligneGraphique.setNom(f"Ligne Horaire {heureLocale}")
            couleur = LigneHoraireFinal.COULEUR_TRAIT_CANDIDAT if candidat else LigneHoraireFinal.COULEUR_TRAIT_HEURE
            ligneGraphique.setCouleur(couleur)                

            ligneGraphique.setTooltips([f"Heure Locale {ampm}: {heureLocale}", f"Azimut % Midi : {azimut}"])
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
        ligneAM = LigneAzimut(villes_dict["Bourges"], self.azimutMidiStylet - (180 -self.azimutLumiere))
        lignePM = LigneAzimut(villes_dict["Bourges"], self.azimutMidiStylet + (180 -self.azimutLumiere))
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

                        #Si nous avons un pt3, on calcle le barycentre
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
                epaisseur = 2,
                nom ="Candidat",
                tooltips=[],
                tags = {"level" : "construction"}
            ) 
            listeObjets.append(cercleCandidat)
        return listeObjets