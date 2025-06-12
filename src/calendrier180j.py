import csv
from collections import OrderedDict

from math import pow

# Librairie calcul astronomique
from src.calculAstronomique import trouverSolsticeEteAvecAlmanac, declinaisonSoleil, longitudeEcliptiqueSoleil
from src.calculAstronomique import MyJulianDate, convertirHeureLocaleVersUTC

# Base de données des villes
from src.data_loader import villes_dict
        
from math import pow

class Calendrier180j(list):
    def __init__(self, annee):
        super().__init__()
        self.patternNotes = ['F', 'G', 'A', 'B', 'C', 'B', 'A', 'G', 'F', 'E', 'D', 'C', 'D', 'E']
        self.freqRel = {
            'C': 1.0,
            'D': pow(2, -1/12),
            'E': pow(2, -3/12),
            'F': pow(2, -5/12),
            'G': pow(2, -7/12),
            'A': pow(2, -9/12),
            'B': pow(2, -10/12),
        }
        jd_solstice, self.declMax = trouverSolsticeEteAvecAlmanac(annee)
        # self.declMax = 23.556
        self.totalRange = (self.declMax * 4 / 180)
        self.buildDeclinaisonTable()

    def computeDeclinaisonFromFreq(self, declPrec, prevNote, note):
        """
        Retourne decl = declPrec - deltaDecl (comme ton Excel).
        """

        if note == 'C' and prevNote == 'B':    
            deltaFreq = abs(self.freqRel[prevNote] - 0.5 * self.freqRel[note])
        elif note == 'B' and prevNote == 'C':   
            deltaFreq = abs(0.5* self.freqRel[prevNote] - self.freqRel[note])
        else:
            deltaFreq = abs(self.freqRel[prevNote] - self.freqRel[note])

        deltaDecl = deltaFreq * self.totalRange * len(self.patternNotes)
        decl = declPrec - deltaDecl
        return decl




    def buildDeclinaisonTable(self):
        lenPattern = len(self.patternNotes)
        ligneCentre = 89

        # Ligne 89
        prevNote = self.patternNotes[0]
        note = prevNote
        declPrec = self.declMax
        self.append({
            'declinaison': declPrec,
            'note': note,
            'saison': 'solstice_ete'
        })

        # Lignes 90 → 179
        indexPattern = 1
        for i in range(ligneCentre + 1, 180):
            note = self.patternNotes[indexPattern % lenPattern]
            decl = self.computeDeclinaisonFromFreq(declPrec, prevNote, note)

            self.append({
                'declinaison': decl,
                'note': note,
                'saison': 'ete_automne'
            })

            prevNote = note
            declPrec = decl
            indexPattern += 1

        # Lignes 88 → 0
        cycleNumberDown = 0  # plus nécessaire ici mais je le laisse
        indexPatternDown = 1
        prevNote = self.patternNotes[0]
        declPrec = self.declMax
        for i in range(ligneCentre - 1, -1, -1):
            note = self.patternNotes[indexPatternDown % lenPattern]
            decl = float(self.computeDeclinaisonFromFreq(declPrec, prevNote, note))

            self.insert(0, {
                'declinaison': decl,
                'note': note,
                'saison': 'hiver_printemps'
            })

            prevNote = note
            declPrec = decl
            indexPatternDown += 1

    def lettreCalendrier(self, date: str) -> str:
        """
        Renvoie la lettre (note) associée à la déclinaison du soleil
        pour le JJ/MM/1066 donné.
        """
        def saisonPourDate(dateJD):
            longitude = longitudeEcliptiqueSoleil(dateJD)  # TA fonction existante
            if 90 <= longitude < 270:
                return "ete_automne"
            else:
                return "hiver_printemps"

        # 1. Calculer déclinaison du soleil à cette date
        jourMois =date[:5]
        dateJD = MyJulianDate.fromString(jourMois + "/1066")
        decl_sun = float(declinaisonSoleil(dateJD))
        saison = saisonPourDate(dateJD)

        # On filtre les lignes de la bonne saison + solstices
        lignes_candidats = [ligne for ligne in self if ligne['saison'] == saison or ligne['saison'] == 'solstice_ete']


        # Chercher la ligne la plus proche
        ligne_proche = min(lignes_candidats, key=lambda ligne: abs(ligne['declinaison'] - decl_sun))


        # 3. Retourner la lettre (note)
        return ligne_proche['note']



if __name__ == "__main__":
    calendrier = Calendrier180j(1066)

    # Exemple d'affichage :
    print(calendrier.lettreCalendrier("15/06"))    
    print(calendrier.lettreCalendrier("30/05"))
    print(calendrier.lettreCalendrier("19/07"))


