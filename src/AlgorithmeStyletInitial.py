import csv
import math
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo, AlgorithmeManager
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.Sentinelle import Sentinelle

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

class AlgorithmeStyletInitial(AlgorithmeManager):

    def __init__(self, layerManager:LayerManager):
        self.dataset = ListeSegmentsDataSet("data/dataset.csv")  # Créé explicitement ici
        super().__init__(layerManager)

    def chargerStructure(self, structure):
        self.structure_declaree = structure

    def getListeModulesInitiale(self):
            return [
                ("soleil", "default", Soleil()),
                ("carte", "default", Carte()),
                ("planete", "default", Planete()),
                ("etoile", "default", Etoile()),
                ("sentinelle", "default", SentinelleAlgo()),
                ("candidats", "default", Candidats())
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
        self.dateObservation = ""
        self.visibiliteZeta = ""
        self.lieuObservation = None
        self.decalage6mois = None
# Variables output pour les autres modules
        self.dateObservationJD = None
        self.coordObservation = None
        self.lettreObs = None
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
        dateSegment = MyJulianDate.fromString(self.dateDataset)
        self.lettreSeg = dateSegment.lettreDominicale()

        # On calcule l'heure de lever et de coucher du soleil à Strasbourg pour savoir si Zeta est visible à cette date
        villeStrasbourg = villes_dict["Strasbourg"]
        coord_strasbourg = villeStrasbourg.getCoordonneesGPS()
        heureLeverZeta = calculLeverAstre(coord_strasbourg, dateSegment, ASTRES['ZetaPuppis'])
        heureLeverSoleil = calculLeverSoleil(coord_strasbourg, dateSegment)
        heureCoucherSoleil = calculCoucherSoleil(coord_strasbourg, dateSegment)
        if (heureLeverZeta>=heureLeverSoleil) and (heureLeverZeta<=heureCoucherSoleil):
            self.visibiliteZeta = "Non visible"
            self.dateObservationJD = dateSegment.date6Mois()
        else:
            self.visibiliteZeta = "Visible"
            self.dateObservationJD = dateSegment


        self.dateObservation = self.dateObservationJD.jourSemaine() +" " + self.dateObservationJD.toString("JJ/MM/AAAA")
        self.lettreObs = self.dateObservationJD.lettreDominicale()
        self.lieuObservation = Soleil.tableauObservation.get(self.lettreSeg, "-")

        self.decalage6mois = "6 mois plus tard"

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

        ville = villes_dict[self.lieuObservation]
        self.coordObservation = ville.getCoordonneesGPS()

#
# Gestion de l'objet Soleil: Gère l'observation '
#

class Carte(ModuleAlgo):
    def getEntreesModules(self):
        return ["soleil.dateObservationJD", "soleil.coordObservation" ]

    def __init__(self):
# Variables input des autres modules
        self.dateObservationJDSoleil = None
        self.coordObservationSoleil = None

        self.heure = None           # L'heure du lever du soleil à Strasbourg'
        self.azimut = None          # L'azimut du soleil à son lever
        self.heureLeverZeta = None  # Heure lever Zeta Pupis au lieu d'observation (type string pour affichage)
# Variables output pour les autres modules
        self.heureLeverZetaJD = None  # Heure lever Zeta Pupis au lieu d'observation (julian date pour )
        self.rotation = None           # Rotation de la carte
        self.azimutZeta = None      # L'azimut de Zeta Pupis à son lever
        super().__init__()

    def setup(self):
        """
        Initialise la valeur par défaut de lieuObservation à partir de la lettre dominicale.
        Ce champ dépend d’un calcul mais doit être défini manuellement par l'utilisateur,
        donc on le prépare ici à titre d’initialisation.
        """
        # On calcule l'heure de lever du soleil à Strasbourg anisi que son azimut'
        villeStrasbourg = villes_dict["Strasbourg"]
        coord_strasbourg = villeStrasbourg.getCoordonneesGPS()
        self.heureLeverSoleilStrasbourgJD = calculLeverSoleil(coord_strasbourg, self.dateObservationJDSoleil)
        self.heure = self.heureLeverSoleilStrasbourgJD.toString("HH:MM:SS")
        _, self.azimut = positionSoleil(coord_strasbourg, self.heureLeverSoleilStrasbourgJD)
        self.rotation = 90 - self.azimut

    def calculer(self):
        # On calcule l'heure de lever de Zéta Puppis au lieu d'observation'
        lat, lon = self.coordObservationSoleil
        self.heureLeverZetaJD = calculLeverAstre((lat, lon), self.dateObservationJDSoleil, ASTRES['ZetaPuppis'])
        self.heureLeverZeta = self.heureLeverZetaJD.toString("HH:MM:SS")
        _, self.azimutZeta = positionAstre((lat, lon), self.heureLeverZetaJD, ASTRES['ZetaPuppis'])


#
# Gestion de l'axe des planètes
#

class Planete(ModuleAlgo):
    def getEntreesModules(self):
        return [
            "soleil.coordObservation",
            "soleil.dateObservationJD",
            "carte.heureLeverZetaJD",
            "carte.azimutZeta",
            "carte.rotation" ]


    def __init__(self):
# Variable input des autres modules
        self.coordObservationSoleil = None
        self.dateObservationJDSoleil = None
        self.heureLeverZetaJDCarte = None
        self.azimutZetaCarte = None
        self.rotationCarte = None

# Valeurs initialisées à calculer
        self.nom = None
        self.azimut = None
        self.hauteur = None
        self.sensCarte = "Endroit"
        self.sensZeta = "Endroit"
        self.axeFinalCalcul  = None
        self.axeFinal = None
        super().__init__()

    # On travaille à 6 mois d'intervalle, donc en inversé sur le cercle? ..  => On prendra le décalage avec un principe Jour+2
    sensTableauPlanetes = "+2"
    tableauPlanetes = {
        "Lun": "Lune",
        "Mar": "Mars",
        "Mer": "Jupiter",
        "Jeu": "Saturne",
        "Ven": "Uranus",
        "Sam": "Neptune",
        "Dim": "Pluton"
    }

    def setup(self):
        """
        Initialise la planète observée en fonction du jour de la semaine
        """
        self.nom = Planete.tableauPlanetes.get(self.dateObservationJDSoleil.jourSemaine(), "-")
        villeBourges = villes_dict["Bourges"]

    def getValeursNom(self):
        return [
            Planete.tableauPlanetes.get(self.heureLeverZetaJDCarte.jourSemaine(), "-"),
            Planete.tableauPlanetes.get(decalage2Jours(self.heureLeverZetaJDCarte.jourSemaine(), Planete.sensTableauPlanetes), "-")
        ]

    def getValeursSensCarte(self):
        return ["Endroit", "Envers"]

    def getValeursSensZeta(self):
        return ["Endroit", "Envers"]


    def getRegles(self):
        return [
            ["Synchroniser l'Axe de Zéta en fonction du choix de la planète", "sensZeta", self._regle_zeta_selon_planete],
            ["La carte est toujours à l'endroit pour les planètes", "sensCarte", self._regle_carte_toujours_endroit]
        ]

    def _regle_zeta_selon_planete(self):
        """
        Si la planète sélectionnée est le premier choix, Zéta est à l'endroit.
        Si c’est le deuxième choix, Zéta est à l’envers.
        Sinon : on conserve la valeur actuelle.
        """
        valeurs = self.getValeursNom()
        if self.nom == valeurs[0]:
            return "Endroit"
        elif self.nom == valeurs[1]:
            return "Envers"
        else:
            return self.sensZeta

    def _regle_carte_toujours_endroit(self):
        return "Endroit"


    def calculer(self):
        # On calcule lazimut de la plaète à l'heure donnée'
        lat, lon = self.coordObservationSoleil
        self.hauteur, self.azimut = positionAstre((lat, lon), self.heureLeverZetaJDCarte, ASTRES[self.nom])

        if self.hauteur > 0:
            #On prend en compte le sens de la carte:
            # On suppose que l'Est est aligné avec le level du soleil à Strasbourg'
            # ET ensuite on aligne l'axe de la carte % Zeta Puppis
            azimutPlaneteAvecSensCarte = self.azimut if self.sensCarte=="Endroit" else 360-self.azimut
            azimutPlaneteAvecSensCarteStr = f"{float(self.azimut):.2f}" if self.sensCarte=="Endroit" else f"360-{float(self.azimut):.2f}"

            # Si l'axe de Zeta est inversé, on inverse le sens de Zeta'
            azimutZetaAvecSensAxe = self.azimutZetaCarte if self.sensZeta=="Endroit" else -self.azimutZetaCarte
            azimutZetaAvecSensAxeStr = f"{float(self.azimutZetaCarte):.2f}" if self.sensZeta=="Endroit" else f"-{float(self.azimutZetaCarte):.2f}"
            if (azimutZetaAvecSensAxe>=0) and (self.azimut>=0):
                azimutZetaAvecSensAxeStr = "+"+azimutZetaAvecSensAxeStr

            # Si la carte est à l'envers, on inverse le sens de rotation'
            rotationCarteAvecSensCarte = self.rotationCarte if self.sensCarte=="Endroit" else -self.rotationCarte
            rotationCarteAvecSensCarteStr = f"{float(self.rotationCarte):.2f}" if self.sensCarte=="Endroit" else f"-{float(self.rotationCarte):.2f}"
            if (rotationCarteAvecSensCarte>=0) and (self.rotationCarte>=0):
                rotationCarteAvecSensCarteStr = "+"+rotationCarteAvecSensCarteStr

            self.axeFinal = (azimutPlaneteAvecSensCarte + azimutZetaAvecSensAxe + rotationCarteAvecSensCarte) % 360
            self.axeFinalCalcul = azimutPlaneteAvecSensCarteStr + " " + azimutZetaAvecSensAxeStr + " "+ rotationCarteAvecSensCarteStr
        else:
            self.axeFinalCalcul =f"La planète {self.nom} est invisible à cette heure"
            self.axeFinal = None

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        if self.hauteur >0:
            villeBourges = villes_dict["Bourges"]

            #
            # D'abord la construction du level 'Design'
            #
            bourges = PointGraphique(
                villeBourges,
                afficherNom = True,
                tags = {"level" : "design"}
            )
            azimut = self.azimut if self.sensCarte == "Endroit" else 360-self.azimut
            ligneObservation = LigneAzimut(
                bourges,
                azimut,
                f"Axe {self.nom} observé",
                couleur=(255,128,0), # Blue très clair
                tooltips = [f"Axe observation={azimut:.2f}°",f"Sens carte: {self.sensCarte}"],
                tags = {"level" : "design"}
            )

            rotationCarte = self.rotationCarte if self.sensCarte=="Endroit" else -self.rotationCarte
            rotationZeta = self.azimutZetaCarte if self.sensZeta=="Endroit" else -self.azimutZetaCarte
            arcRotationZeta = ArcOriente(
                bourges,
                150,
                azimut,
                rotationZeta,
                nom = "Rotation",
                epaisseur=1,
                couleur = (64,64,0),  # LEs arc en rouge
                style = "Arrow",
                tooltips = [f"Rotation zéta={self.azimutZetaCarte:.2f}°",f"Sens zeta: {self.sensZeta}"],
                tags = {"level" : "design"}
                )
            arcRotationCarte = ArcOriente(
                bourges,
                150,
                azimut+rotationZeta,
                rotationCarte,
                nom = "Rotation",
                epaisseur=1,
                couleur = (255,0,128),
                style = "Arrow",
                tooltips = [f"Rotation Carte={self.rotationCarte:.2f}°",f"Sens carte: {self.sensCarte}"],
                tags = {"level" : "design"}
                )

            ligne = LigneAzimut(
                bourges,
                self.axeFinal,
                f"Axe {self.nom} après rotation",
                epaisseur=1,
                tooltips = [f"Axe apres rotation ={self.axeFinal:.2f}°"],
                tags = {"level" : "construction"}
            )


            return [bourges, ligne, ligneObservation, arcRotationCarte, arcRotationZeta]
        else:
            return []
#
# Gestion de l'axe de la grande ourse
#
class Etoile(ModuleAlgo):
    def getEntreesModules(self):
        return ["soleil.lettreObs",
            "soleil.lettreSeg",
            "carte.heureLeverZetaJD",
            "soleil.coordObservation",
            "carte.azimutZeta",
            "carte.rotation"
        ]

    def __init__(self):
# Variable input des autres modules
        self.heureLeverZetaJDCarte = None
        self.coordObservationSoleil = None
        self.azimutZetaCarte = None
        self.rotationCarte = None
        self.lettreObsSoleil = None
        self.lettreSegSoleil = None


# Valeurs initialisées à calculer
        self.nom = None
        self.azimut = 0
        self.hauteur = 0
        self.sensCarte = "Endroit"
        self.sensZeta = "Endroit"
        self.origineTrait = None
        self.axeFinalCalcul  = None
        self.axeFinal = None
        super().__init__()

    sensTableauGandeOurse = "-2"
    tableauGandeOurse = {
        "A": "AlphaMajor",
        "B": "BetaMajor",
        "C": "GammaMajor",
        "D": "DeltaMajor",
        "E": "EpsilonMajor",
        "F": "ZetaMajor",
        "G": "EtaMajor"
    }

    # Les villes Origine du Trait
    tableauOrigineTrait = {
        "C": "Gérardmer",
        "B": "Bourges",
        "A": "Cherbourg",
        "G": "Dieppe",
        "F": "Bourges",
        "E": "Cherbourg",
        "D": "Dieppe"
    }
    tableauOrigineTraitDecale = {
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
        Initialise l'étoile en fonction de la lettre dominicale
        """
        # Les magniudes sont dans le bon sens .. A, B, C => On prendra le décalage avec un principe note-2 E-2=>C
        self.nom = Etoile.tableauGandeOurse.get(self.lettreObsSoleil, "-")
        self.origineTrait = Etoile.tableauOrigineTrait.get(self.lettreObsSoleil, "-")
        # L'origine du trait ne peut pas être Bourges!'
        if self.origineTrait == "Bourges":
            self.origineTrait = Etoile.tableauOrigineTraitDecale.get(self.lettreObsSoleil, "-")

    def getValeursNom(self):
        return [
            Etoile.tableauGandeOurse.get(self.lettreObsSoleil, "-"),
            Etoile.tableauGandeOurse.get(decalage2Notes(self.lettreObsSoleil, Etoile.sensTableauGandeOurse), "-")
        ]
    def getValeursSensCarte(self):
        return ["Endroit", "Envers"]

    def getValeursSensZeta(self):
        return ["Endroit", "Envers"]

    def getValeursOrigineTrait(self):
            villeStd = Etoile.tableauOrigineTrait.get(self.lettreSegSoleil, "-")
            villeDec = Etoile.tableauOrigineTraitDecale.get(self.lettreSegSoleil, "-")
            tab = []
            if villeStd != "Bourges":
                tab += [villeStd]
            if villeDec != "Bourges":
                tab += [villeDec]
            return tab

    def getRegles(self):
        return [["Synchroniser l'Axe de Zéta en fonction du choix de l'étoile", "sensZeta", self._regle_zeta_selon_etoile]]

    def _regle_zeta_selon_etoile(self):
        """
        Si l’étoile sélectionnée est le premier choix, Zéta est à l'endroit.
        Si c’est le deuxième choix, Zéta est à l’envers.
        Sinon : on conserve la valeur actuelle.
        """
        valeurs = self.getValeursNom()
        if self.nom == valeurs[0]:
            return "Endroit"
        elif self.nom == valeurs[1]:
            return "Envers"
        else:
            return self.sensZeta


    def calculer(self):
        # On calcule lazimut de l'étoile à l'heure donnée'
        lat, lon = self.coordObservationSoleil
        self.hauteur, self.azimut  = positionAstre((lat, lon), self.heureLeverZetaJDCarte, ASTRES[self.nom])

        if self.hauteur>0:
            #On prend en compte le sens de la carte:
            # On suppose que l'Est est aligné avec le level du soleil à Strasbourg'
            # ET ensuite on aligne l'axe de la carte % Zeta Puppis
            azimutEtoileAvecSensCarte = self.azimut if self.sensCarte=="Endroit" else 360-self.azimut
            azimutEtoileAvecSensCarteStr = f"{float(self.azimut):.2f}" if self.sensCarte=="Endroit" else f"360-{float(self.azimut):.2f}"

            # Si l'axe de Zeta est inversé, on inverse le sens de Zeta'
            azimutZetaAvecSensAxe = self.azimutZetaCarte if self.sensZeta=="Endroit" else -self.azimutZetaCarte
            azimutZetaAvecSensAxeStr = f"{float(self.azimutZetaCarte):.2f}" if self.sensZeta=="Endroit" else f"-{float(self.azimutZetaCarte):.2f}"
            if (azimutZetaAvecSensAxe>=0) and (self.azimut>=0):
                azimutZetaAvecSensAxeStr = "+"+azimutZetaAvecSensAxeStr

            # Si la carte est à l'envers, on inverse le sens de rotation'
            rotationCarteAvecSensCarte = self.rotationCarte if self.sensCarte=="Endroit" else -self.rotationCarte
            rotationCarteAvecSensCarteStr = f"{float(self.rotationCarte):.2f}" if self.sensCarte=="Endroit" else f"-{float(self.rotationCarte):.2f}"
            if (rotationCarteAvecSensCarte>=0) and (self.rotationCarte>=0):
                rotationCarteAvecSensCarteStr = "+"+rotationCarteAvecSensCarteStr

            self.axeFinal = (azimutEtoileAvecSensCarte + azimutZetaAvecSensAxe + rotationCarteAvecSensCarte) % 360
            self.axeFinalCalcul = azimutEtoileAvecSensCarteStr + " " + azimutZetaAvecSensAxeStr + " "+ rotationCarteAvecSensCarteStr
        else:
            self.axeFinalCalcul =f"L'étoile {self.nom} est invisible à cette heure"
            self.axeFinal = None

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        if self.hauteur >0:
            villeOrigineTrait = villes_dict[self.origineTrait]

            #
            # D'abord la construction du level 'Design'
            #
            originePG = PointGraphique(
                villeOrigineTrait,
                afficherNom = True,
                tags = {"level" : "design"}
            )
            azimut = self.azimut if self.sensCarte == "Endroit" else 360-self.azimut
            ligneObservation = LigneAzimut(
                villeOrigineTrait,
                azimut,
                f"Axe {self.nom} observé",
                couleur=(94,94,255), # Rouge  clair
                tooltips = [f"Axe observation={azimut:.2f}°",f"Sens carte: {self.sensCarte}"],
                tags = {"level" : "design"}
            )

            rotationCarte = self.rotationCarte if self.sensCarte=="Endroit" else -self.rotationCarte
            rotationZeta = self.azimutZetaCarte if self.sensZeta=="Endroit" else -self.azimutZetaCarte
            arcRotationZeta = ArcOriente(
                villeOrigineTrait,
                150,
                azimut,
                rotationZeta,
                nom = "Rotation",
                epaisseur=1,
                couleur = (64,64,0),  # LEs arc en rouge
                style = "Arrow",
                tooltips = [f"Rotation zéta={self.azimutZetaCarte:.2f}°",f"Sens zeta: {self.sensZeta}"],
                tags = {"level" : "design"}
                )
            arcRotationCarte = ArcOriente(
                villeOrigineTrait,
                150,
                azimut+rotationZeta,
                rotationCarte,
                nom = "Rotation",
                epaisseur=1,
                couleur = (255,0,128),
                style = "Arrow",
                tooltips = [f"Rotation Carte={self.rotationCarte:.2f}°",f"Sens carte: {self.sensCarte}"],
                tags = {"level" : "design"}
                )

            ligne = LigneAzimut(
                villeOrigineTrait,
                self.axeFinal,
                f"Axe {self.nom} après rotation",
                epaisseur=1,
                tooltips = [f"Axe apres rotation ={self.axeFinal:.2f}°"],
                tags = {"level" : "construction"}
            )


            return [originePG, ligne, ligneObservation, arcRotationCarte, arcRotationZeta]

        else:
            return[]


#
# Gestion des candidats
#
class Candidats(ModuleAlgo):
    RAYON_CANDIDAT = 20

    def getEntreesModules(self):
        return ["planete.axeFinal","etoile.axeFinal","etoile.origineTrait" ]

    def __init__(self):
        # Variable input des autres modules
        self.axeFinalPlanete = None
        self.axeFinalEtoile = None
        self.origineTraitEtoile = None
        self.heureSentinelle =None
        self.distKM = None
        self.selection  = None
        self.azimutHeure = None
        self.villeSolution = None

        self.sentinelle=Sentinelle("data/sentinelle.csv")

        super().__init__()

    def calculer(self):
        if self.axeFinalPlanete is None or self.axeFinalEtoile is None:
            self.selection = "L'un des axes est manquant"
            return

        # On reconstruit les lignes graphiques
        lignePlanete = Ligne.depuisPointEtAzimut(
            PointGraphique(villes_dict["Bourges"]).coordonneesPixelAbs(),
            self.axeFinalPlanete
        )

        ligneEtoile = Ligne.depuisPointEtAzimut(
            PointGraphique(villes_dict[self.origineTraitEtoile]).coordonneesPixelAbs(),
            self.axeFinalEtoile
        )

        # On calcule l'intersection.
        x, y = lignePlanete.intersection(ligneEtoile)
        x_l93, y_l93 =pixels_to_lambert93(x, y)
        intersectionPlaneteEtoile = PointGraphique("intersection", x_l93,y_l93)

        # On vérifie que le point est visible
        if not intersectionPlaneteEtoile.estVisibledansImage():
            self.selection = "Point non visile"
            return

        # On calcule la distance avec la ligne horaire la pllus proche
        self.heureSentinelle, distMin, self.azimutHeure = self.sentinelle.surLigneHoraire(x, y)
        self.distKM = int(intersectionPlaneteEtoile.pixelsVersMetres()*distMin/1000)

        if self.distKM >20:
            self.selection = "Trop loin d'une ligne horaire"
            return

        # On calcule finalement le centre des 3 droites
        self.selection = "Sélectionné"
        ligneSentinelle = Ligne.depuisPointEtAzimut(
            self.sentinelle.getOrigineStylet().coordonneesPixelAbs(),
            self.azimutHeure
        )

        # Le centre du triangle
        px, py = Ligne.barycentreTriangle(lignePlanete, ligneEtoile, ligneSentinelle)
        x_l93, y_l93 = pixels_to_lambert93(px, py)
        self.pointIntersection = PointGraphique("intersection", x_l93,y_l93)

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        if self.selection == "Sélectionné":
            return [CercleGraphique(
                self.pointIntersection,
                Candidats.RAYON_CANDIDAT,
                epaisseur = 2,
                nom ="Intersection Axe Planete + Etoile",
                tooltips=[f"Heure : {self.heureSentinelle}", f"Distance Heure = {self.distKM}km"],
                tags = {"level" : "construction"}
            )]

        return []


#
# Gestion de l'axe de la grande ourse
#
class SentinelleAlgo(ModuleAlgo):
    def getEntreesModules(self):
        return ["candidats.selection","candidats.heureSentinelle"]

    def __init__(self):
# Variable input des autres modules
        self.selectionCandidats = None
        self.heureSentinelleCandidats = None

# Valeurs initialisées à calculer
        self.heure = ""
        self.sensCadran = ""
        self.sentinelle=Sentinelle("data/sentinelle.csv")

        super().__init__()


    def calculer(self):
        if self.selectionCandidats == "Sélectionné":
            self.heure = self.heureSentinelleCandidats[:-2]
            self.sensCadran = self.heureSentinelleCandidats[-2:]
        else:
            self.heure = ""
            self.sensCadran = ""

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        objets = []

        # 🔷 Ligne de référence (Midi solaire)
        objets.append(self.sentinelle.afficherLigneMidi("design"))
        objets.append(self.sentinelle.getOrigineStylet())
    
        tableauNotes = ["C", "B", "A", "G", "F", "E", "D", "J"]
        for note in tableauNotes:
            heureLocale = self.sentinelle[note]["HeureLocale"]
            selectionAM = (heureLocale == self.heure) and (self.sensCadran== "AM")
            selectionPM = (heureLocale == self.heure) and (self.sensCadran== "PM") 
            tagLevelAM = "construction" if selectionAM else "design"
            tagLevelPM = "construction" if selectionPM else "design"

            objets.append(self.sentinelle.afficherLigneHoraire(note, "AM", tagLevelAM, selectionAM))
            objets.append(self.sentinelle.afficherLigneHoraire(note, "PM", tagLevelPM, selectionPM))       

        return objets


