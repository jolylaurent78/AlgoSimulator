"""Passage des orientations de grille Lambert-93 aux directions de la carte active."""
import math
import numpy as np

from src.carte_config import carteConfig
from src.affichage_objets import LigneAzimut, PointGraphique


def azimutGrilleVersImage(theta, matrice):
    """Transforme un vecteur directeur ; aucun offset ne doit lui être ajouté."""
    radians = math.radians(theta)
    vecteur = np.asarray(matrice) @ np.array([math.sin(radians), math.cos(radians)])
    if not np.isfinite(vecteur).all() or np.linalg.norm(vecteur) == 0:
        raise ValueError("Direction image invalide")
    return math.degrees(math.atan2(vecteur[0], -vecteur[1])) % 360


class LigneAzimutGrille(LigneAzimut):
    """Ligne ancrée en Lambert, dont l'orientation de grille survit au recalibrage."""
    def __init__(self, ville, orientation_grille, **kwargs):
        self.orientation_grille = orientation_grille
        super().__init__(ville, 0, **kwargs)

    def _calculerCachesPixels(self):
        self.azimut_deg = azimutGrilleVersImage(self.orientation_grille, carteConfig.A)
        return super()._calculerCachesPixels()

    def copie(self):
        copie = LigneAzimutGrille(
            PointGraphique("Ancrage", self.x_l93, self.y_l93), self.orientation_grille,
            nom=self.nom, couleur=self._couleur, epaisseur=self._epaisseur,
            layer=self.layer, tags=self.tags, tooltips=self.tooltips,
        )
        copie.setStyle(self.style)
        return self._copyPrintLabelTo(copie)
