import csv
from collections import OrderedDict

# Librairie calcul astronomique
from src.calculAstronomique import calculHeurePourAzimutSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC

# Affichage des objects graphiques
from src.affichage_objets import *

# Base de données des villes
from src.data_loader import villes_dict

class Sentinelle(dict):
    COULEUR_TRAIT_MIDI = (255, 145, 34)
    COULEUR_TRAIT_HEURE = (255, 193, 132)
    COULEUR_TRAIT_CANDIDAT = (164, 82, 0)

    #
    # Fonctions d'initialisation
    # 
    def __init__(self, chemin_csv):
        self.fichierSentinelles = OrderedDict()  # { "S1" : {"Angle": ..., "Ville": ...} }
        self.chargerFichier(chemin_csv)

        # On calcule les azimuts et on initialise les points graphiques cles 
        self.pointCoetquidan = PointGraphique(villes_dict["Coetquidan"])
        self.pointGolfeJuan = PointGraphique(villes_dict["Golfe-Juan"])
        self.azimutMidi = self.completerAzimutPrecis()

        # On calcule les heures locales
        self.calculerHeureSentinelle()

        # On crée le dictionnaire
        self.creerDictSentinelles()
   
    #
    # Chargement des données initiales à partir du csv..
    def chargerFichier(self, chemin_csv):
        with open(chemin_csv, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                cle = row["Nom"]
                self.fichierSentinelles[cle] = {
                    "Note": row["Note"],
                    "Azimut": row["Azimut"],
                    "Ville": row["Ville"],
                    "AzimutCalibre": None,
                    "HeureLocale": None
                }

    # Calcul de l'angle précis 
    def completerAzimutPrecis(self):
        # On prépare l'axe de référence : Coetquidan -> Golfe-Juan

        px1, py1 = self.pointCoetquidan.coordonneesPixelAbs()
        px2, py2 = self.pointGolfeJuan.coordonneesPixelAbs()

        ligneMidi = Ligne(px1, py1, px2, py2)
        azimutMidi = ligneMidi.azimut()
        
        # On complète AzimutPrecis pour chaque sentinelle
        for cle, sentinelle in self.fichierSentinelles.items():
            ville = sentinelle["Ville"]
            if ville is None or ville == "":
                # Pas de ville : on garde l'azimut de base
                sentinelle["AzimutCalibre"] = float(sentinelle["Azimut"])
            else:
                # Ville renseignée : on calcule l'angle
                ville = sentinelle["Ville"].strip()
                pointVille = PointGraphique(villes_dict[ville])
                pxV, pyV = pointVille.coordonneesPixelAbs()
                ligneVersVille = Ligne(px1, py1, pxV, pyV)
                sentinelle["AzimutCalibre"] = 180-float(ligneVersVille.angleAvec(ligneMidi))
        return azimutMidi
    
    def calculerHeureSentinelle(self):
        villeCarnac = villes_dict["Carnac"]
        coordCarnac = villeCarnac.getCoordonneesGPS()
        (lat, lon) = coordCarnac
        dateObsSentinelleJD = MyJulianDate.fromString("15/08/1066")

        def arrondirHeureHHMM(heure_hms: str) -> str:
            """
            Prend une heure au format 'HH:MM:SS' et retourne 'HH:MM' arrondi :
            - Si secondes < 30 → minute inférieure
            - Si secondes >= 30 → minute supérieure (avec gestion dépassement)
            """
            hh, mm, ss = map(int, heure_hms.split(":"))

            if ss >= 30:
                mm += 1
                if mm == 60:
                    mm = 0
                    hh += 1
                    if hh == 24:
                        hh = 0

            return f"{hh:02d}:{mm:02d}"

        for cle, sentinelle in self.fichierSentinelles.items():
            heureSentinelleJD = calculHeurePourAzimutSoleil((lat, lon), dateObsSentinelleJD, sentinelle["AzimutCalibre"], precision_deg=0.2)
            heureLocale = convertirHeureLocaleVersUTC(heureSentinelleJD.toString("HH:MM:SS"), lon, inverse=True )
            sentinelle["HeureLocale"] = arrondirHeureHHMM(heureLocale)

    def creerDictSentinelles(self):
        # On construit un dictionnaire : clé = Note, valeur = {HeureLocale, AzimutCalibre}
        dict_notes = {}

        for cle, sentinelle in self.fichierSentinelles.items():
            note = sentinelle["Note"].strip()
            dict_notes[note] = {
                "HeureLocale": sentinelle["HeureLocale"],
                "AzimutCalibre": sentinelle["AzimutCalibre"]
            }

        # On met à jour le dict interne (puisque Sentinelle hérite de dict)
        self.clear()
        self.update(dict_notes)

        return dict_notes
    
    def getOrigineStylet(self):
        return self.pointCoetquidan

    def getAzimut(self, heureLocale: str):
        """
        Retourne l'azimut associé à une heure locale donnée (au format 'HH:MM').
        Si aucune correspondance n'est trouvée, retourne None.
        """
        for note, valeurs in self.items():
            if valeurs["HeureLocale"] == heureLocale:
                return valeurs["AzimutCalibre"]

        # Si non trouvé
        return None

    #
    # Fonctions d'affichage
    # 
  
    def afficherLigneMidi(self, tagLevel:str):
        ligneMidi = LigneEntreVilles(self.pointCoetquidan, self.pointGolfeJuan,
            nom="Axe Midi solaire",
            couleur=Sentinelle.COULEUR_TRAIT_MIDI,
            epaisseur = 1,
            tags={"level": tagLevel}
            )
        return ligneMidi
        
    def afficherLigneHoraire(self, note:str, am_pm:str, tagLevel:str, selectionne=False):
        heurelocale = self[note]["HeureLocale"]
        azimutCalibre = self[note]["AzimutCalibre"]
        rotation = (180 - azimutCalibre) % 360
        azimut = self.azimutMidi + rotation if am_pm=="AM" else self.azimutMidi - rotation

        couleurAffichage = Sentinelle.COULEUR_TRAIT_CANDIDAT if selectionne else Sentinelle.COULEUR_TRAIT_HEURE
        
        ligne= LigneAzimut(
            self.pointCoetquidan,
            azimut,
            nom=f"Ligne Horaire {heurelocale} AM",
            couleur=couleurAffichage,  # bleu clair
            epaisseur=1,
            tooltips=[f"Heure AM : {heurelocale}", f"Δ azimut = {rotation:.2f}°"],
            tags={"level": tagLevel}
        )
        return ligne

    #
    # Fonctions de calcul
    # 
    def surLigneHoraire(self, px, py):
        distMin = None
        candidatHeure = None

        for note, valeurs in self.items():
            heureLocale = valeurs["HeureLocale"]
            azimut = valeurs["AzimutCalibre"]

            delta = (180 - azimut) % 360
            azimut_corrige_am = (self.azimutMidi + delta) % 360
            azimut_corrige_sym = (self.azimutMidi - delta) % 360

            ligneAM = Ligne.depuisPointEtAzimut(self.pointCoetquidan.coordonneesPixelAbs(), azimut_corrige_am)
            lignePM = Ligne.depuisPointEtAzimut(self.pointCoetquidan.coordonneesPixelAbs(), azimut_corrige_sym)
            distAM = ligneAM.distanceAuPoint(px, py)
            distPM = lignePM.distanceAuPoint(px, py)

            if distMin is None:
                distMin = distAM
                candidatHeure = heureLocale
                ampm = "AM"
                azimutHeure = azimut_corrige_am            
            elif distMin>distAM:
                distMin = distAM
                candidatHeure = heureLocale
                ampm = "AM"
                azimutHeure = azimut_corrige_am
            if distMin>distPM:
                distMin = distPM
                candidatHeure = heureLocale
                ampm = "PM"
                azimutHeure = azimut_corrige_sym

        distKM = int(self.pointCoetquidan.pixelsVersMetres()*distMin/1000)
        selection = distKM<20

        return selection, candidatHeure, ampm, distKM, azimutHeure        


class LieuxObservation:

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

    @staticmethod
    def getListeLieuxObservation(note:str, date:str=""):
        ville1 = LieuxObservation.tableauObservation.get(note, "-")
        ville2 = LieuxObservation.tableauObservationDecale.get(note, "-")
        solutions = [ville1, ville2]

         # On gère le cas Roncevaux en rajoutant "Gérardmer si présent"
        if "Roncevaux" in solutions:
            solutions.append("Gérardmer")  # ou la ville que tu veux

        # Si la date du segment est le 18/05/1152, on rajoute Lampouy
        if date == "18/05/1152":
            solutions.append("Lampouy")

        return solutions
    
    @staticmethod
    def getDefautLieuObservation(note:str):
        return LieuxObservation.tableauObservation.get(note, "-") 

if __name__ == "__main__":
    sentinelle = Sentinelle("data/sentinelle.csv")
    for nom, infos in sentinelle.fichierSentinelles.items():
        print(f"{nom} → Azimut: {infos['Azimut']} | Ville: {infos['Ville']} | AzimutCalibre: {infos['AzimutCalibre']:.2f} | HeureLocale: {infos['HeureLocale']}")
