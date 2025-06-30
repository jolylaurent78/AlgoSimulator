
from src.data_loader import villes_dict
from src.affichage_objets import SegmentEntreVilles, PointGraphique

class UniteDecodageSS:
    def __init__(self, nomSource: str, nomMilieu: str, nomDestination: str):
        self.nomSource = nomSource
        self.nomMilieu = nomMilieu
        self.nomDestination = nomDestination
        
        self.villeSource = villes_dict[nomSource]
        self.villeMilieu = villes_dict[nomMilieu]
        self.villeDestination = villes_dict[nomDestination]

        self.segmentA = SegmentEntreVilles(self.villeSource, self.villeMilieu)
        self.segmentB = SegmentEntreVilles(self.villeMilieu, self.villeDestination)        
        self.azimutSegmentA = self.segmentA.getAzimutCarte()
        self.azimutSegmentB = self.segmentB.getAzimutCarte()
        self.distanceSegment = self.segmentA.distanceSegment()+self.segmentB.distanceSegment()

    def construireRepresentationCarte(self):
        """
        Retourne la liste des objets graphiques à afficher pour visualiser ce segment.
        """
        pointS = PointGraphique(self.villeSource, afficherNom = True)
        pointM = PointGraphique(self.villeMilieu, afficherNom = True)
        pointD = PointGraphique(self.villeDestination, afficherNom = True)
        pointS.setNom("S")
        pointM.setNom("M")
        pointD.setNom("D")                
        return [pointS, pointM, pointD, self.segmentA, self.segmentB]

    def getAttributsSegment(self):
        """
        Retourne les caractéristiques géométriques du segment :
        - longueur en kilomètres
        - azimut (degrés, 0 = nord, sens horaire)
        """
        azA = self.azimutSegmentA
        azOppA = (azA + 180) % 360
        azB = self.azimutSegmentB
        azOppB = (azB + 180) % 360

        delta = (azOppA - azB) % 360
        deltaOpp = (360 - delta) % 360

        return [
            (0, "Longueur", f"{self.distanceSegment:.02f} km"),
            (1, f"Azimut SM", f"{azA:.02f}° - {azOppA:.02f}°"),
            (1, f"Azimut MD", f"{azB:.02f}° - {azOppB:.02f}°"),
            (2, f"Delta", f"{delta:.02f}° - {deltaOpp:.02f}°")
        ]

    def calculIndex(self):
        """
        Exemple d’algorithme de décodage.
        Convertit l’azimut en colonne, et la longueur en ligne.
        - Azimut ∈ [0, 360] → 12 segments → index colonne = azimut // 30
        - Longueur ∈ [0, 120 km] → 12 intervalles → index ligne = longueur // 10
        """
        indexMot = int(self.azimutSegmentA / 24)
        enigme = int(self.distanceSegment / 91.5)

        return (enigme, indexMot)
