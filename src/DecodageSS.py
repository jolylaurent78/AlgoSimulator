
from src.data_loader import villes_dict
from src.affichage_objets import SegmentEntreVilles, CercleGraphique

class UniteDecodageSS:
    def __init__(self, nomSource: str, nomDestination: str):
        self.villeSource = villes_dict[nomSource]
        self.villeDestination = villes_dict[nomDestination]

        self.segment = SegmentEntreVilles(self.villeSource, self.villeDestination)
        self.azimutSegment = self.segment.getAzimutCarte()
        self.distanceSegment = self.segment.distanceSegment()

    def construireRepresentationCarte(self):
        """
        Retourne la liste des objets graphiques à afficher pour visualiser ce segment.
        """
        cercle = CercleGraphique(self.villeSource, 200)  # Cercle arbitraire pour illustration
        return [self.segment, cercle]

    def getAttributsSegment(self):
        """
        Retourne les caractéristiques géométriques du segment :
        - longueur en kilomètres
        - azimut (degrés, 0 = nord, sens horaire)
        """

        return [
            ("Longueur", f"{self.distanceSegment:.02f} km"),
            ("Azimut", f"{self.azimutSegment:.02f}°")
        ]

    def calculIndex(self):
        """
        Exemple d’algorithme de décodage.
        Convertit l’azimut en colonne, et la longueur en ligne.
        - Azimut ∈ [0, 360] → 12 segments → index colonne = azimut // 30
        - Longueur ∈ [0, 120 km] → 12 intervalles → index ligne = longueur // 10
        """
        indexMot = int(self.azimutSegment / 24)
        enigme = int(self.distanceSegment / 91.5)

        return (enigme, indexMot)
