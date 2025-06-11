import cv2
import numpy as np
import math
from typing import Any

# Gestion des coordonnées / projection
from src.carte_config import lambert93_to_pixels, pixels_to_lambert93, image_size, lambert93_to_gps

# Gestion des layers graphiques
from src.layerManager import Layer

COULEURS = {
    "BLUE": (255, 0, 0),
    "GREEN": (0, 255, 0),
    "RED": (0, 0, 255),
    "YELLOW": (0, 255, 255),
    "CYAN": (255, 255, 0),
    "MAGENTA": (255, 0, 255),
    "WHITE": (255, 255, 255),
    "BLACK": (0, 0, 0),
    "GRAY": (127, 127, 127),
    "ORANGE": (0, 128, 255),
    "PINK": (203, 192, 255)
}



class ObjetGraphique:
    def __init__(self, nom=None, couleur=None, epaisseur=None, style=None, afficherNom = None, layer=None, tags: dict[str, Any] = None, tooltips: list[str] = None):
        self.nom = nom                          # Nom symbolique
        self._couleur = couleur                  # Couleur d’affichage
        self._epaisseur = epaisseur              # Épaisseur du trait ou point
        self.style = style                      # "plein" ou "dash"

        self.afficherNom = afficherNom
        self.layer = layer

        self.pointReference = None              # Coordonnée (x, y) en pixels image absolus
        self.etatSelection = False              # ✅ État de sélection
        self._etatVisible = True                 # ✅ Visible par défaut

        self.tags = tags or {}
        self.tooltips = tooltips or []
        self.tooltips_scenario = []

    def copie(self):
        raise NotImplementedError(f"copie() non implémenté pour {self.__class__.__name__}")

    def setNom(self, nom: str):
        self.nom = nom

    def getNom(self):
        return self.nom

    # Pour les attributs de l'objet, on prend ceux du layer ou ceux de l'objet si ils sont surchargés
    def setVisible(self, visible: bool):
        self._etatVisible = visible

    def estVisible(self) -> bool:
        return self._etatVisible and (self.layer.visible if self.layer else True)

    def setCouleur(self, couleur: tuple[int, int, int]):
        self._couleur = couleur

    def getCouleur(self):
        return self._couleur if self._couleur is not None else (self.layer.couleur if self.layer else (0, 0, 0))

    def setEpaisseur(self, epaisseur: int):
        self._epaisseur = epaisseur

    def getEpaisseur(self):
        return self._epaisseur if self._epaisseur is not None else (self.layer.epaisseur if self.layer else 1)

    def setStyle(self, style: str | None):
        self.style = style

    def getStyle(self):
        return self.style if self.style is not None else (self.layer.style if self.layer else "plein")

    # Accesseur pour les attributs propriétaires
    def setLayer(self, layer):
        self.layer = layer

    def getLayer(self):
        return self.layer

    def setSelection(self, etat: bool):
        self.etatSelection = etat

    def estSelectionne(self) -> bool:
        return self.etatSelection

    def ajouterTag(self, cle: str, valeur: Any):
        self.tags[cle] = valeur

    def afficher(self, canvas, transformerAffichagePixel):
        """
        Méthode à surcharger : dessine l'objet sur le canvas avec la fonction de transformation fournie.
        """
        raise NotImplementedError("La méthode afficher() doit être surchargée.")

    def estVisibledansImage(self):
        """
        Retourne True si le point de référence est dans les dimensions de l’image.
        """
        if self.pointReference is None:
            return True
        w, h = image_size
        x, y = self.pointReference
        return 0 <= x <= w and 0 <= y <= h

    def coordonneesPixelAbs(self) -> tuple[float, float]:
        """
        Retourne les coordonnées en pixels absolus (image source) du point de référence.
        """
        return self.pointReference

    def distanceDepuis(self, x, y):
        """
        Méthode générique à surcharger : retourne la distance (en pixels) entre un point (x, y) et l'objet.
        """
        raise NotImplementedError("La méthode distance() doit être surchargée dans les sous-classes.")


    def afficherTexte(self, canvas, texte: str, x: int, y: int, fontScale=0.5, thickness=1):
        """
        Affiche du texte centré horizontalement sur x, avec y correspondant au haut du texte.
        """
        fontFace = cv2.FONT_HERSHEY_SIMPLEX
        (text_width, text_height), baseline = cv2.getTextSize(texte, fontFace, fontScale, thickness)

        # Centrage horizontal : x - moitié largeur
        x_text = int(x - text_width / 2)
        # Alignement vertical : y + hauteur (car OpenCV place à partir du bas)
        y_text = int(y + text_height)

        couleur = self.getCouleur()
        cv2.putText(canvas, texte, (x_text, y_text), fontFace, fontScale, couleur, thickness, cv2.LINE_AA)

    def getTooltipComplet(self) -> list[str]:
        lignes = []

        if self.nom:
            lignes.append(str(self.nom))  # sécurité

        if self.tooltips:
            lignes.extend(str(l) for l in self.tooltips)

        if self.tooltips_scenario:
            lignes.append("")  # séparation visuelle
            lignes.extend(str(l) for l in self.tooltips_scenario)

        return lignes


class PointGraphique(ObjetGraphique):
    def __init__(
        self, source,
        x_l93=None, y_l93=None, lat = None, lon = None,
        nom=None,
        couleur=None, epaisseur=None, style="plein", afficherNom=False,  layer=None,
        tags: dict[str, Any] = None, tooltips: list[str] = None
    ):
        """
        Trois façons de créer un point :
        - source = PointGraphique (copie)
        - source = (nom, x_l93, y_l93)
        - source = nom (str), avec x_l93 et y_l93 fournis séparément
        """
        super().__init__(nom=nom, couleur=couleur, epaisseur=epaisseur, style=style, afficherNom = afficherNom, layer=layer, tags=tags, tooltips=tooltips)

        if isinstance(source, PointGraphique):
            self.nom = source.nom
            self.x_l93 = source.x_l93
            self.y_l93 = source.y_l93
            self.lat = source.lat
            self.lon = source.lon

        elif isinstance(source, tuple) and len(source) == 3:
            self.nom, self.x_l93, self.y_l93 = source
            self.lat = lat
            self.lon = lon

        elif isinstance(source, str) and x_l93 is not None and y_l93 is not None:
            self.nom = source
            self.x_l93 = x_l93
            self.y_l93 = y_l93
            self.lat = lat
            self.lon = lon
        else:
            raise ValueError("Format de PointGraphique non reconnu : coordonnées Lambert93 requises")

        # Coordonnées image en pixels absolus
        self.pointReference = lambert93_to_pixels(self.x_l93, self.y_l93)

        # On génère les coordonnées GPS si elles ne sont pas définies
        if self.lat is None and self.lon is None:
            self.lon, self.lat = lambert93_to_gps(self.x_l93, self.y_l93)
            self.lat, self.lon = lambert93_to_gps(self.x_l93, self.y_l93)

    @classmethod
    def depuisIntersectionLignes(
        cls, ligne1: "LigneGraphique", ligne2: "LigneGraphique",
        lat = None, lon = None,
        nom=None,
        couleur=None, epaisseur=None, afficherNom=False, style=None, layer=None,
        tags: dict[str, Any] = None, tooltips: list[str] = None
    ):
        """
        Crée un PointGraphique à l'intersection de deux LigneGraphique.
        Retourne None si les lignes sont parallèles ou hors image.
        """
        pt_l93 = ligne1.intersectionLigne(ligne2)
        if pt_l93 is None:
            return None

        x_l93, y_l93 = pt_l93
        return cls(nom or "Intersection", x_l93, y_l93, lat, lon,
                couleur=couleur, epaisseur=epaisseur, afficherNom=afficherNom, style=style, layer=layer,
                tags=tags, tooltips=tooltips
        )


    @classmethod
    def depuisDeuxPoints(cls, p1: "PointGraphique", p2: "PointGraphique",
        nom=None, couleur=None, epaisseur=None, style="plein", afficherNom=False, layer=None, tags=None, tooltips=None):

        # On récupère les coordonnées Lambert des deux points
        x1_l93, y1_l93 = p1.coordonneesLambert()
        x2_l93, y2_l93 = p2.coordonneesLambert()

        # Calcul du centre
        x_centre = (x1_l93 + x2_l93) / 2
        y_centre = (y1_l93 + y2_l93) / 2

        # Création du nouveau PointGraphique centré
        return cls(
            nom or "CentreDeuxPoints",
            x_centre,
            y_centre,
            couleur=couleur,
            epaisseur=epaisseur,
            style=style,
            afficherNom=afficherNom,
            layer=layer,
            tags=tags,
            tooltips=tooltips
        )

    def copie(self):
        return PointGraphique(self.nom, self.x_l93, self.y_l93, lat=lat, lon=lon,
            couleur=self._couleur, epaisseur=self._epaisseur, style=self.style, afficherNom=self.afficherNom, layer=self.layer,
            tags=self.tags, tooltips=self.tooltips
        )

    def coordonneesLambert(self) -> tuple[float, float]:
        """
        Retourne les coordonnées Lambert93 du point sous forme de tuple (x_l93, y_l93)
        """
        return self.x_l93, self.y_l93

    def getCoordonneesGPS(self) -> tuple[float, float]:
        """
        Retourne les coordonnées GPS sous forme de tuple lat, lon
        """
 #       return (self.lon, self.lat)
        return (self.lat, self.lon)


    def distance(self, autre: "PointGraphique") -> float:
        """
        Distance (km) entre deux points en Lambert93.
        """
        dx = self.x_l93 - autre.x_l93
        dy = self.y_l93 - autre.y_l93
        return (dx**2 + dy**2)**0.5 / 1000


    def pixelsVersMetres(self) -> float:
        """
        Calcule la conversion locale d’un déplacement de (dx, dy) pixels en mètres
        autour du point (px, py).
        """
        px, py = self.pointReference
        x1_l93, y1_l93 = pixels_to_lambert93(px, py)
        x2_l93, y2_l93 = pixels_to_lambert93(px + 1, py)
        return math.hypot(x2_l93 - x1_l93, y2_l93 - y1_l93)


    def distanceDepuis(self, x_pix: float, y_pix: float) -> float:
        """
        Calcule la distance en pixels entre un point donné et le bord du disque représentant le point graphique.
        Si le curseur est dans le disque, retourne 0.
        """
        px, py = self.coordonneesPixelAbs()
        d = math.hypot(px - x_pix, py - y_pix)
        rayon_visuel = self.getEpaisseur()  # rayon en pixels affiché
        return 0 if d <= rayon_visuel else d - rayon_visuel


    def distanceLigne(self, ligneGraphique: "LigneGraphique") -> float:
        """
        Distance orthogonale (en mètres) entre ce point et une ligne graphique.
        """
        if ligneGraphique.lignePixelImage is None:
            return None

        # Coordonnées pixels de ce point
        px, py = self.pointReference
        A, B, C = ligneGraphique.lignePixelImage.A, ligneGraphique.lignePixelImage.B, ligneGraphique.lignePixelImage.C
        denom = math.sqrt(A**2 + B**2)
        if denom == 0:
            return None

        # Distance en pixels
        d_pix = abs(A * px + B * py + C) / denom

        # Convertir 1 pixel horizontal en mètres via la transformation inverse
        x1_l93, y1_l93 = pixels_to_lambert93(px, py)
        x2_l93, y2_l93 = pixels_to_lambert93(px + 1, py)
        m_par_pixel = math.hypot(x2_l93 - x1_l93, y2_l93 - y1_l93)

        return d_pix * m_par_pixel

    def afficher(self, canvas, transformerAffichagePixel):
        """
        Affiche le point sur le canvas en pixels écran.
        """
        if not self.estVisible():
            return

        px, py = self.coordonneesPixelAbs()
        x, y = transformerAffichagePixel(px, py)
        if x is None or y is None:
            return

        couleur = self.getCouleur()
        epaisseur = self.getEpaisseur()

        if self.estSelectionne():
            cv2.circle(canvas, (int(x), int(y)), epaisseur + 2, (255, 255, 255), -1, cv2.LINE_AA)  # halo blanc
            cv2.circle(canvas, (int(x), int(y)), epaisseur + 1, couleur, -1, cv2.LINE_AA)     # surcouche
        else:
            cv2.circle(canvas, (int(x), int(y)), epaisseur, couleur, -1, cv2.LINE_AA)

        if self.afficherNom and self.nom:
            self.afficherTexte(canvas, self.nom, int(x), int(y))


class SymboleWiki(PointGraphique):
    _iconeCache = {}  # dictionnaire statique partagé

    def __init__(self, source, x_l93: float, y_l93: float, icone_path: str,
                 nom=None, afficherNom=False, layer=None, tags=None, tooltips=None, url=None):
        super().__init__(
            source=nom,
            nom=nom,
            x_l93=x_l93,
            y_l93=y_l93,
            afficherNom=afficherNom,
            layer=layer,
            tags=tags,
            tooltips=tooltips,
        )
        self.url = source

        self.icone_path = icone_path
        # Chargement ou récupération depuis le cache
        if icone_path not in SymboleWiki._iconeCache:
            icone = cv2.imread(icone_path, cv2.IMREAD_UNCHANGED)
            if icone is None or icone.shape[2] != 4:
                raise ValueError(f"Image invalide ou sans canal alpha : {icone_path}")
            SymboleWiki._iconeCache[icone_path] = icone
        self.icone = SymboleWiki._iconeCache[icone_path]

    def copie(self):
        return SymboleWiki(
            x_l93=self.x_l93,
            y_l93=self.y_l93,
            icone_path=self.icone_path,
            nom=self.nom,
            afficherNom=self.afficherNom,
            layer=self.layer,
            tags=self.tags.copy(),
            tooltips=list(self.tooltips)
        )

    def afficher(self, canvas, transformerAffichagePixel):
        if not self.estVisible():
            return

        px, py = self.coordonneesPixelAbs()
        x, y = transformerAffichagePixel(px, py)
        if x is None or y is None:
            return

        # Taille de l'icône
        h, w = self.icone.shape[:2]
        x0 = int(x - w / 2)
        y0 = int(y - h / 2)

        # Vérification bordures
        if x0 < 0 or y0 < 0 or x0 + w > canvas.shape[1] or y0 + h > canvas.shape[0]:
            return  # Icône sort du cadre

        # Fusion avec alpha : blending progressif
        alpha_s = self.icone[:, :, 3] / 255.0  # [0,1]
        alpha_l = 1.0 - alpha_s

        for c in range(3):  # BGR
            canvas[y0:y0 + h, x0:x0 + w, c] = (
                alpha_s * self.icone[:, :, c] +
                alpha_l * canvas[y0:y0 + h, x0:x0 + w, c]
            ).astype(np.uint8)

        # Affichage du texte éventuel
        if self.afficherNom and self.nom:
            self.afficherTexte(canvas, self.nom, x, y + h // 2 + 5)


class Cercle:
    def __init__(self, centre_pix: tuple[float, float], rayon_pix: float):
        self.centre = centre_pix      # (x, y) en pixels image absolus
        self.rayon = rayon_pix        # rayon en pixels

    def contient(self, x_pix, y_pix) -> bool:
        dx = x_pix - self.centre[0]
        dy = y_pix - self.centre[1]
        return math.hypot(dx, dy) <= self.rayon

class CercleGraphique(ObjetGraphique):
    def __init__(self, ville: PointGraphique, rayon_km: float,
        nom=None,
        couleur=None, epaisseur=None, layer=None, style=None,
        tags: dict[str, Any] = None, tooltips: list[str] = None
    ):

        super().__init__(nom=nom,
            couleur=couleur, epaisseur=epaisseur, layer=layer, style=style,
            tags=tags,tooltips=tooltips)
        self.ville = ville
        self.rayon_km = rayon_km

        centre, rayon_px = self.getCentreEtRayonPixels()
        self.cercle = Cercle(centre, rayon_px)
        self.pointReference = self.cercle.centre


    @staticmethod
    def depuisTroisPoints(v1: PointGraphique, v2: PointGraphique, v3: PointGraphique,
        nom=None,
        couleur=None, epaisseur=None, layer=None, style=None,
        tags: dict[str, Any] = None, tooltips: list[str] = None) -> "CercleGraphique | None":

        def calculCentreEtRayon(p1, p2, p3):
            (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
            temp = x2**2 + y2**2
            bc = (x1**2 + y1**2 - temp) / 2.0
            cd = (temp - x3**2 - y3**2) / 2.0
            det = (x1 - x2)*(y2 - y3) - (x2 - x3)*(y1 - y2)
            if abs(det) < 1e-10:
                return None
            cx = (bc*(y2 - y3) - cd*(y1 - y2)) / det
            cy = ((x1 - x2)*cd - (x2 - x3)*bc) / det
            r = math.hypot(cx - x1, cy - y1)
            return cx, cy, r

        p1 = v1.coordonneesPixelAbs()
        p2 = v2.coordonneesPixelAbs()
        p3 = v3.coordonneesPixelAbs()

        result = calculCentreEtRayon(p1, p2, p3)
        if result is None:
            print("⚠️ Les trois villes sont alignées : cercle impossible.")
            return None

        cx_pix, cy_pix, rayon_pix = result
        x_l93, y_l93 = pixels_to_lambert93(cx_pix, cy_pix)
        centre = PointGraphique("Centre", x_l93, y_l93)

        x_edge_l93, y_edge_l93 = pixels_to_lambert93(cx_pix + rayon_pix, cy_pix)
        rayon_m = math.hypot(x_edge_l93 - x_l93, y_edge_l93 - y_l93)
        rayon_km = rayon_m / 1000

        return CercleGraphique(
            centre, rayon_km,
            nom=nom,
            couleur=couleur, epaisseur=epaisseur, layer=layer, style=style,
            tags=tags, tooltips=tooltips
        )


    def copie(self):
        return CercleGraphique(ville=self.ville.copie(),rayon_km=self.rayon_km,
            nom=self.nom,
            couleur=self._couleur,epaisseur=self._epaisseur,layer=self.layer,style=self.style,
            tooltips=self.tooltips,tags=self.tags
        )

    def getCentreEtRayonPixels(self):
        """
        Retourne (px_centre, py_centre), rayon_px
        à partir du centre Lambert93 et du rayon en km.
        """
        x_l93, y_l93 = self.ville.coordonneesLambert()
        px_centre, py_centre = lambert93_to_pixels(x_l93, y_l93)

        x_edge_l93 = x_l93 + self.rayon_km * 1000
        px_edge, py_edge = lambert93_to_pixels(x_edge_l93, y_l93)
        rayon_px = math.hypot(px_edge - px_centre, py_edge - py_centre)

        return (int(px_centre), int(py_centre)), int(rayon_px)




    def afficher(self, canvas, transformerAffichagePixel):
        if not self.estVisible():
            return

        px, py = self.coordonneesPixelAbs()
        rayon_px = self.cercle.rayon

        centre_aff = transformerAffichagePixel(px, py)
        edge_aff = transformerAffichagePixel(px + rayon_px, py)

        couleur = self.getCouleur()
        epaisseur = self.getEpaisseur()

        if centre_aff and edge_aff and None not in centre_aff and None not in edge_aff:
            x, y = int(centre_aff[0]), int(centre_aff[1])
            rayon_affiche = int(math.hypot(edge_aff[0] - x, edge_aff[1] - y))
            if self.estSelectionne():
                cv2.circle(canvas, (x, y), rayon_affiche, (255, 255, 255), epaisseur + 2, cv2.LINE_AA)  # halo
                cv2.circle(canvas, (x, y), rayon_affiche, couleur, epaisseur + 1, cv2.LINE_AA)     # surcouche
            else:
                cv2.circle(canvas, (x, y), rayon_affiche, couleur, epaisseur, cv2.LINE_AA)


    def getCentre(self) -> PointGraphique:
        x_l93, y_l93 = pixels_to_lambert93(*self.pointReference)
        return PointGraphique("Centre", x_l93, y_l93)


    def distanceDepuis(self, x_pix: float, y_pix: float) -> float:
        """
        Distance en pixels entre le point (x, y) et le contour du cercle.
        Pratique si on sélectionne par clic près du tracé.
        """
        cx, cy = self.cercle.centre
        r = self.cercle.rayon
        return abs(math.hypot(x_pix - cx, y_pix - cy) - r)


    def intersectionLigne(self, ligneGraphique: "LigneGraphique") -> list[tuple[float, float]]:
        """
        Retourne les points d’intersection avec une LigneGraphique, en coordonnées Lambert93.
        """
        if ligneGraphique.lignePixelImage is None:
            return []

        points_px = ligneGraphique.lignePixelImage.intersections_avec_cercle(self.cercle)
        return [pixels_to_lambert93(px, py) for px, py in points_px]

    def estVisibledansImage(self) -> bool:
        """
        Retourne True si au moins une partie du cercle (en pixels absolus) est dans les dimensions de l'image source.
        """

        w_img, h_img = image_size
        px, py = self.coordonnéesPixelAbs()
        r = self.cercle.rayon

        # Rectangle englobant
        x0 = px - r
        y0 = py - r
        x1 = px + r
        y1 = py + r

        return not (x1 < 0 or x0 > w_img or y1 < 0 or y0 > h_img)


class ArcOriente(CercleGraphique):
    def __init__(self, ville: PointGraphique, rayon_km: float, azimut_depart_deg: float, rotation_deg: float,
        nom=None,
        couleur=None, epaisseur=None, style=None, layer=None,
        tags: dict[str, Any] = None, tooltips: list[str] = None):

        # Appel du constructeur parent avec le centre (PointGraphique) et le rayon en km
        super().__init__(
            ville=ville,
            rayon_km=rayon_km,
            nom=nom,
            couleur=couleur,
            epaisseur=epaisseur,
            layer=layer,
            tags=tags,
            tooltips=tooltips
        )
        self.azimut_depart = azimut_depart_deg % 360
        self.rotation = rotation_deg
        self.style = style  # "Arrow" ou None

    def copie(self):
        return ArcOriente(
            ville=self.ville,
            azimut_depart_deg=self.azimut_depart,
            rotation_deg=self.rotation,
            nom=self.nom,
            couleur=self._couleur,
            epaisseur=self._epaisseur,
            style=self.style,
            layer=self.layer,
            tooltips=self.tooltips
        )

    def afficher(self, canvas, transformerAffichagePixel):
        if not self.estVisible():
            return

        def azimutVersOpenCV(azimut_boussole):
            """
            Convertit un angle azimutal (0° = Nord, sens horaire)
            en angle compatible avec OpenCV (0° = Est, sens horaire, -180° à +180°).
            """
            angle_opencv = (azimut_boussole - 90) % 360
            if angle_opencv > 180:
                angle_opencv -= 360

            return angle_opencv

        def azimutBoussoleVersTrigonometrie(azimut_deg):
            """
            Convertit un azimut boussole (0°=Nord, horaire) en angle trigo
            (0°=Est, antihoraire) compatible avec sin/cos en radians.
            """
            return math.radians((90 - azimut_deg) % 360)


        if not self.estVisible():
            return

        # On convertit les angles... 0° = Nord pour moi 0° = Est pour OpenCV avec des angles de -180° à + 180°
        #◘ On fait la rotation à 90°
        angle_debutOpenCV = azimutVersOpenCV(self.azimut_depart)
        angle_finOpenCV = azimutVersOpenCV(self.azimut_depart + self.rotation)

        # OpenCV ne comprend pas angle_deb et angle_fin.. il va toujours du plus petit ves le plus grand
        if (self.rotation>0) and (angle_finOpenCV<angle_debutOpenCV):
            angle_finOpenCV += 360
        if (self.rotation < 0) and (angle_finOpenCV > angle_debutOpenCV):
            angle_finOpenCV -= 360

        px, py = self.coordonneesPixelAbs()
        rayon_px = self.cercle.rayon


        centre_aff = transformerAffichagePixel(px, py)
        edge_aff = transformerAffichagePixel(px + rayon_px, py)

        couleur = self.getCouleur()
        epaisseur = self.getEpaisseur()

        if centre_aff and edge_aff and None not in centre_aff and None not in edge_aff:
            x, y = int(centre_aff[0]), int(centre_aff[1])
            rayon_affiche = int(math.hypot(edge_aff[0] - x, edge_aff[1] - y))

            if self.estSelectionne():
                cv2.ellipse(
                    canvas,
                    (int(x), int(y)),
                    (int(rayon_affiche), int(rayon_affiche)),
                    0,
                    angle_debutOpenCV,
                    angle_finOpenCV,
                    (255, 255, 255),
                    epaisseur+2,
                    lineType=cv2.LINE_AA
                )
                cv2.ellipse(
                    canvas,
                    (int(x), int(y)),
                    (int(rayon_affiche), int(rayon_affiche)),
                    0,
                    angle_debutOpenCV,
                    angle_finOpenCV,
                    couleur,
                    epaisseur+1,
                    lineType=cv2.LINE_AA
                )

            else:
                cv2.ellipse(
                    canvas,
                    (int(x), int(y)),
                    (int(rayon_affiche), int(rayon_affiche)),
                    0,
                    angle_debutOpenCV,
                    angle_finOpenCV,
                    couleur,
                    epaisseur,
                    lineType=cv2.LINE_AA
                )



        # Si demandé : ajouter flèche à la fin de l’arc
        if self.style == "Arrow":
            # Angle final de l’arc en degrés boussole
            angle_arc_deg = (self.azimut_depart + self.rotation) % 360
            angle_rad = azimutBoussoleVersTrigonometrie(angle_arc_deg)  # en radians trigonométriques

            # Position du point terminal de l'arc
            x_edge = x + rayon_affiche * math.cos(angle_rad)
            y_edge = y - rayon_affiche * math.sin(angle_rad)

            # Vecteur tangente à l'arc (perpendiculaire au rayon)
            angle_tangent = angle_rad + math.pi / 2 if self.rotation > 0 else angle_rad - math.pi / 2

            # Deux petits segments en V (flèche)
            longueur = 15  # pixels
            for sign in [-1, 1]:
                branche_angle = angle_tangent + sign * math.radians(30)
                x_tip = x_edge + longueur * math.cos(branche_angle)
                y_tip = y_edge - longueur * math.sin(branche_angle)

                cv2.line(canvas, (int(x_edge), int(y_edge)), (int(x_tip), int(y_tip)), couleur, epaisseur)


        # On affiche le texte
        if self.nom:
            # 1. Angle central de l’arc
            angle_central = (((angle_debutOpenCV + angle_finOpenCV) / 2) + 0) % 360
            angle_central_rad = math.radians(angle_central)

            # On doit transformer la distance du texte de pixel brut à pixel affiché
            # Conversion des deux points
            pt0 = transformerAffichagePixel(x, y)
            pt1 = transformerAffichagePixel(x+150, y+150)
            decalage_affichage = math.hypot(pt1[0] - pt0[0], pt1[1] - pt0[1])



            x_text = x + (rayon_affiche + decalage_affichage) * math.cos(angle_central_rad)
            y_text = y + (rayon_affiche + decalage_affichage) * math.sin(angle_central_rad)

            # 3. Affichage
            self.afficherTexte(canvas, self.nom, x_text, y_text)



    def distanceDepuis(self, x_pix: float, y_pix: float) -> float:
        """
        Distance en pixels entre le point (x, y) et le cercle support.
        L'arc étant un segment du cercle, on utilise l'approximation du contour.
        """
        cx, cy = self.cercle.centre
        r = self.cercle.rayon
        return abs(math.hypot(x_pix - cx, y_pix - cy) - r)



class Ligne:
    def __init__(self, x1, y1, x2, y2):
        self.pt1 = (x1, y1)
        self.pt2 = (x2, y2)

        dx = x2 - x1
        dy = y2 - y1

        # Équation cartésienne Ax + By + C = 0
        self.A = dy
        self.B = -dx
        self.C = dx * y1 - dy * x1


    @classmethod
    def depuisPointEtVecteur(cls, point: tuple[float, float], vecteur: tuple[float, float]) -> "Ligne":
        """
        Construit une droite à partir d’un point (x, y) et d’un vecteur directeur (dx, dy),
        tous exprimés en pixels image absolus.
        """
        x, y = point
        dx, dy = vecteur
        if dx == 0 and dy == 0:
            raise ValueError("Vecteur nul : impossible de construire une droite")

        # On prend un second point arbitraire sur la ligne
        x2 = x + dx
        y2 = y + dy

        return cls(x, y, x2, y2)

    @classmethod
    def depuisPointEtAzimut(cls, point: tuple[float, float], azimut_deg: float, longueur: float = 1000.0) -> "Ligne":
        """
        Construit une droite à partir d’un point (x, y) et d’un azimut (en degrés boussole),
        avec un vecteur directeur de longueur spécifiée (en pixels image absolus).
        """
        angle_rad = math.radians(azimut_deg)
        dx = math.sin(angle_rad) * longueur
        dy = -math.cos(angle_rad) * longueur

        return cls.depuisPointEtVecteur(point, (dx, dy))

    @staticmethod
    def barycentreTriangle(l1: "Ligne", l2: "Ligne", l3: "Ligne") -> tuple[float, float] | None:
        """
        Calcule le centre de gravité (intersection des médianes) du triangle formé
        par les intersections deux à deux des 3 lignes.
        """
        A = l1.intersection(l2)
        B = l2.intersection(l3)
        C = l3.intersection(l1)

        if not A or not B or not C:
            return None

        x = (A[0] + B[0] + C[0]) / 3
        y = (A[1] + B[1] + C[1]) / 3
        return (x, y)



    def azimut(self) -> float:
        """
        Retourne l’azimut (en degrés boussole) de la droite, basé sur ses coefficients A et B.
        Convention : 0° = nord, 90° = est, 180° = sud, 270° = ouest
        """
        dx = -self.B
        dy = self.A

        if dx == 0 and dy == 0:
            raise ValueError("Vecteur nul, azimut indéfini")

        az = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
        return az


    def distanceAuPoint(self, x: float, y: float) -> float:
        """
        Calcule la distance (en pixels) entre cette ligne et un point (x, y).
        """
        numerateur = abs(self.A * x + self.B * y + self.C)
        denominateur = math.hypot(self.A, self.B)
        if denominateur == 0:
            raise ValueError("Ligne dégénérée, A = B = 0")
        return numerateur / denominateur


    def projection(self, px: float, py: float) -> tuple[float, float]:
        """
        Calcule la projection orthogonale du point (px, py) sur cette ligne.
        Retourne un tuple (px_proj, py_proj) en pixels absolus.
        """
        x1, y1 = self.pt1
        x2, y2 = self.pt2

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            # Cas pathologique : ligne réduite à un point
            return x1, y1

        # Vecteur de la ligne
        vx, vy = dx, dy

        # Vecteur du point vers pt1
        wx = px - x1
        wy = py - y1

        # Projection scalaire
        facteur = (vx * wx + vy * wy) / (vx ** 2 + vy ** 2)

        proj_x = x1 + facteur * vx
        proj_y = y1 + facteur * vy

        return proj_x, proj_y

    def orthogonale(self, point: "PointGraphique") -> "Ligne":
        """
        Retourne une nouvelle droite orthogonale à celle-ci, passant par le PointGraphique donné.
        La direction est arbitraire mais cohérente (vecteur normal au segment d’origine).
        """
        x1, y1 = self.pt1
        x2, y2 = self.pt2
        px, py = point.coordonnéesPixelAbs()

        dx = x2 - x1
        dy = y2 - y1

        # Vecteur orthogonal
        ortho_dx = -dy
        ortho_dy = dx

        # Second point arbitraire dans la direction orthogonale
        p2x = px + ortho_dx
        p2y = py + ortho_dy

        return Ligne((px, py), (p2x, p2y))


    def intersection(self, autre: "Ligne"):
        """
        Calcule l'intersection avec une autre ligne.
        Retourne (x, y) ou None si les droites sont parallèles.
        """
        D = self.A * autre.B - autre.A * self.B

        if abs(D) < 1e-10:
            return None  # lignes parallèles

        Dx = -self.C * autre.B + autre.C * self.B
        Dy = -self.A * autre.C + autre.A * self.C

        x = Dx / D
        y = Dy / D
        return (x, y)

    def intersections_avec_cercle(self, cercle: "Cercle") -> list[tuple[float, float]]:
        """
        Calcule les points d'intersection entre cette ligne (infinie) et un cercle.
        Toutes les coordonnées sont en pixels absolus.
        Retourne une liste de 0, 1 ou 2 points (x, y).
        """
        # Centre et rayon du cercle
        cx, cy = cercle.centre
        r = cercle.rayon

        # Coefficients de la droite : A*x + B*y + C = 0
        A, B, C = self.A, self.B, self.C

        # Projection du centre du cercle sur la droite
        d = A * cx + B * cy + C
        denom = A**2 + B**2
        if denom == 0:
            return []

        # Point projeté sur la droite (le plus proche du centre)
        x0 = cx - A * d / denom
        y0 = cy - B * d / denom

        # Distance du centre du cercle à la ligne
        dist = abs(d) / math.sqrt(denom)

        if dist > r:
            return []  # aucune intersection
        elif abs(dist - r) < 1e-6:
            return [(x0, y0)]  # tangente
        else:
            # Deux points d'intersection
            delta = math.sqrt(r**2 - dist**2)
            dx = -B * delta / math.sqrt(denom)
            dy = A * delta / math.sqrt(denom)
            p1 = (x0 + dx, y0 + dy)
            p2 = (x0 - dx, y0 - dy)
            return [p1, p2]


    def __repr__(self):
        return f"Ligne(({self.pt1[0]}, {self.pt1[1]}) → ({self.pt2[0]}, {self.pt2[1]}))"

    def longueur(self):
        """Retourne la longueur (euclidienne) de la ligne"""
        x1, y1 = self.pt1
        x2, y2 = self.pt2
        return math.hypot(x2 - x1, y2 - y1)

    def angleAvec(self, autre: "Ligne") -> float:
        """
        Calcule l'angle (en degrés, <= 180°) entre cette ligne et une autre ligne.
        """
        # Vecteur directeur de la première ligne
        dx1 = self.pt2[0] - self.pt1[0]
        dy1 = self.pt2[1] - self.pt1[1]

        # Vecteur directeur de la deuxième ligne
        dx2 = autre.pt2[0] - autre.pt1[0]
        dy2 = autre.pt2[1] - autre.pt1[1]

        # Produit scalaire
        dot = dx1 * dx2 + dy1 * dy2

        # Normes des vecteurs
        norm1 = math.hypot(dx1, dy1)
        norm2 = math.hypot(dx2, dy2)

        if norm1 == 0 or norm2 == 0:
            raise ValueError("Impossible de calculer l'angle avec un vecteur nul.")

        # Cosinus de l'angle
        cos_theta = dot / (norm1 * norm2)
        # Clamp (sécurité contre arrondis)
        cos_theta = max(min(cos_theta, 1), -1)

        # Angle en radians
        theta_rad = math.acos(cos_theta)

        # Conversion en degrés
        theta_deg = math.degrees(theta_rad)

        # On retourne un angle <= 180°
        return min(theta_deg, 180.0 - theta_deg + 180.0) if theta_deg > 180 else theta_deg


class LigneGraphique(ObjetGraphique):
    def __init__(self, point_px: tuple[float, float], vecteur_px: tuple[float, float],
        nom=None,
        couleur=None, epaisseur=None,  style=None, layer=None,
        tags: dict[str, Any] = None, tooltips: list[str] = None):

        super().__init__(nom=nom,
            couleur=couleur, epaisseur=epaisseur, style=style, layer=layer,
            tags=tags, tooltips=tooltips
        )

        self.pointReference = point_px
        self.vecteur = vecteur_px

        if image_size is None:
            raise ValueError("image_size doit être défini.")

        w_img, h_img = image_size
        px, py = point_px
        vx, vy = vecteur_px

        if vx == 0 and vy == 0:
            raise ValueError("Vecteur nul : direction indéfinie")

        facteur = 3_000_000
        x1 = px - facteur * vx
        y1 = py - facteur * vy
        x2 = px + facteur * vx
        y2 = py + facteur * vy

        ligne_longue = Ligne(x1, y1, x2, y2)

        # Bords de l'image pour crop
        bords = [
            Ligne(0, 0, 0, h_img),
            Ligne(w_img, 0, w_img, h_img),
            Ligne(0, 0, w_img, 0),
            Ligne(0, h_img, w_img, h_img)
        ]

        intersections = []
        for bord in bords:
            pt = ligne_longue.intersection(bord)
            if pt:
                x, y = pt
                tol = 1e-3
                if -tol <= x <= w_img + tol and -tol <= y <= h_img + tol:
                    intersections.append((x, y))

        if len(intersections) >= 2:
            pt1, pt2 = intersections[:2]
            self.lignePixelImage = Ligne(pt1[0], pt1[1], pt2[0], pt2[1])
        else:
            self.lignePixelImage = None

    def copie(self):
        return LigneGraphique(
            point_px=self.pointReference,
            vecteur_px=self.vecteur,
            nom=self.nom,
            couleur=self._couleur,
            epaisseur=self._epaisseur,
            layer=self.layer,
            tooltips=self.tooltips
        )


    def afficher(self, canvas, transformerAffichage):
        if not self.estVisible():
            return

        if self.lignePixelImage is None:
            return

        pt1 = transformerAffichage(*self.lignePixelImage.pt1)
        pt2 = transformerAffichage(*self.lignePixelImage.pt2)

        if pt1 is None or pt2 is None or None in pt1 or None in pt2:
            return

        x1, y1 = map(int, pt1)
        x2, y2 = map(int, pt2)

        couleur = self.getCouleur()
        epaisseur = self.getEpaisseur()

        if self.estSelectionne():
            cv2.line(canvas, (x1, y1), (x2, y2), (255, 255, 255), epaisseur + 2, cv2.LINE_AA)  # halo blanc
            cv2.line(canvas, (x1, y1), (x2, y2), couleur, epaisseur + 1, cv2.LINE_AA)      # surcouche
        else:
            cv2.line(canvas, (x1, y1), (x2, y2), couleur, epaisseur, cv2.LINE_AA)


    def estVisibledansImage(self) -> bool:
        """
        Retourne True si la ligne graphique possède un segment défini à l'intérieur
        de l'image source (en pixels absolus), autrement dit si elle coupe l'image.
        """

        # Si aucune intersection n'a pu être calculée, la ligne ne traverse pas l'image
        if self.lignePixelImage is None:
            return False

        # Sinon, on a bien un segment visible
        return True


    def distanceDepuis(self, x_pix: float, y_pix: float) -> float:
        """
        Calcule la distance en pixels entre un point donné et la ligne graphique.
        Retourne float('inf') si la ligne n'est pas visible (hors image).
        """
        if self.lignePixelImage is None:
            return float('inf')

        A = self.lignePixelImage.A
        B = self.lignePixelImage.B
        C = self.lignePixelImage.C

        denom = math.hypot(A, B)
        if denom == 0:
            return float('inf')

        # Formule de la distance point-droite : |Ax + By + C| / sqrt(A^2 + B^2)
        return abs(A * x_pix + B * y_pix + C) / denom


    def getAzimutCarte(self) -> float:
        """
        Retourne l’azimut (en degrés) de la ligne graphique sur la carte,
        en convention boussole : 0° = nord, 90° = est, 180° = sud, etc.
        """
        dx, dy = self.vecteur
        if dx == 0 and dy == 0:
            raise ValueError("Vecteur nul, azimut indéfini")
        azimut = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
        return azimut


    def intersectionLigne(self, autre: "LigneGraphique"):
        if self.lignePixelImage is None or autre.lignePixelImage is None:
            return None

        pt = self.lignePixelImage.intersection(autre.lignePixelImage)
        if pt is None:
            return None

        return pixels_to_lambert93(*pt)

    def intersectionCercle(self, cercleGraphique: CercleGraphique) -> list[PointGraphique]:
        points_px = self.lignePixelImage.intersections_avec_cercle(cercleGraphique.cercle)
        resultats = []

        for i, (px, py) in enumerate(points_px):
            x_l93, y_l93 = pixels_to_lambert93(px, py)
            nom = f"Inter-{self.nom}-{i+1}" if self.nom else None
            pt = PointGraphique(nom or "Intersection", x_l93, y_l93, layer=self.layer)
            resultats.append(pt)

        return resultats

    def projectionPointGraphique(self, point: "PointGraphique") -> "PointGraphique":
        """
        Calcule la projection orthogonale d’un PointGraphique sur cette ligne,
        et retourne un nouveau PointGraphique (en Lambert93) à la position projetée.
        """
        if self.lignePixelImage is None:
            return None

        px, py = point.coordonneesPixelAbs()
        proj_px, proj_py = self.lignePixelImage.projection(px, py)

        x_l93, y_l93 = pixels_to_lambert93(proj_px, proj_py)
        nom = f"Proj({point.nom})" if point.nom else "Projection"

        return PointGraphique(nom, x_l93, y_l93, layer=self.layer)

    def orthogonale(self, point: "PointGraphique") -> "LigneEntreVilles":
        """
        Retourne une vraie droite orthogonale à self, passant par le PointGraphique donné.
        """
        px, py = point.coordonneesPixelAbs()

        dx, dy = self.vecteur
        norme = math.hypot(dx, dy)
        if norme == 0:
            raise ValueError("Vecteur nul : impossible de construire une orthogonale.")

        # Vecteur orthogonal unitaire
        ortho_dx = dy / norme
        ortho_dy = -dx / norme   # <-- C'est ici qu'on tient compte de l'inversion de l'axe Y


        # On construit une LigneGraphique
        return LigneGraphique(
            point_px=(px, py),
            vecteur_px=(ortho_dx, ortho_dy),
            nom=f"Ortho vraie de {point.nom}",
            layer=self.layer
        )


    def parallele(self, point: "PointGraphique") -> "LigneAzimut":
        """
        Crée une LigneAzimut parallèle à cette ligne, passant par le PointGraphique donné.
        """

        dx, dy = self.vecteur
        if dx == 0 and dy == 0:
            raise ValueError("Impossible de construire une parallèle : vecteur nul")

        azimut_deg = (math.degrees(math.atan2(dx, -dy)) + 360) % 360

        return LigneAzimut(
            ville=point,
            azimut_deg=azimut_deg,
            nom=f"Parallèle_{point.nom}_à_{self.nom}",
            layer=self.layer)


    def pointsLateraux(self, point: "PointGraphique", distance_m: float) -> tuple["PointGraphique", "PointGraphique"]:
        """
        Calcule deux points situés orthogonalement à la ligne à la distance donnée (en mètres Lambert93),
        à partir du PointGraphique donné (position centrale).
        """
        # Coordonnées Lambert du point de départ
        x0_l93, y0_l93 = point.coordonneesLambert()

        # Vecteur directeur (en pixels image)
        dx, dy = self.vecteur
        norme = math.hypot(dx, dy)
        if norme == 0:
            raise ValueError("Impossible de créer des points latéraux avec un vecteur nul")

        # Vecteur orthogonal unitaire en L93 (car dx/dy sont en pixels image, mais direction OK)
        # On ne convertit pas, on réutilise la direction uniquement
        vx_ortho = dy / norme
        vy_ortho = dx / norme

        # Déplacement en Lambert93
        x1_l93 = x0_l93 + distance_m * vx_ortho * 1000
        y1_l93 = y0_l93 + distance_m * vy_ortho * 1000
        x2_l93 = x0_l93 - distance_m * vx_ortho * 1000
        y2_l93 = y0_l93 - distance_m * vy_ortho * 1000

        # Création des points projetés
        p1 = PointGraphique(x_l93=x1_l93, y_l93=y1_l93, nom=f"{point.nom}_+{int(distance_m)}m", source="custom", layer=self.layer)
        p2 = PointGraphique(x_l93=x2_l93, y_l93=y2_l93, nom=f"{point.nom}_-{int(distance_m)}m", source="custom", layer=self.layer)

        return p1, p2

    def parallelesDecalees(self, distance: float) -> tuple["LigneAzimut", "LigneAzimut"]:
        """
        Crée deux lignes azimutales parallèles à cette ligne, décalées orthogonalement
        de la distance donnée (en pixels image), en utilisant self.pointReference.
        """
        from affichage_objets import LigneAzimut

        # On récupère le point de référence en tant que PointGraphique
        px, py = self.pointReference
        x_l93, y_l93 = pixels_to_lambert93(px, py)
        point_ref = PointGraphique(x_l93=x_l93, y_l93=y_l93, nom=f"{self.nom}_ref", source="custom")

        # Points décalés latéralement
        p1, p2 = self.pointsLateraux(point_ref, distance)

        # Azimut de la ligne (style boussole, sens horaire)
        dx, dy = self.vecteur
        azimut = (math.degrees(math.atan2(dx, -dy)) + 360) % 360

        # Création des deux lignes azimutales
        ligne1 = LigneAzimut(ville=p1, azimut_deg=azimut, nom=f"{self.nom}_+d", layer=self.layer)
        ligne2 = LigneAzimut(ville=p2, azimut_deg=azimut, nom=f"{self.nom}_+d", layer=self.layer)
        return ligne1, ligne2


class LigneEntreVilles(LigneGraphique):
    def __init__(self, ville1, ville2, nom=None, couleur=None, epaisseur=None, layer=None, tags: dict[str, Any] = None, tooltips: list[str] = None):
        x1_l93, y1_l93 = ville1.coordonneesLambert()
        x2_l93, y2_l93 = ville2.coordonneesLambert()
        px1, py1 = lambert93_to_pixels(x1_l93, y1_l93)
        px2, py2 = lambert93_to_pixels(x2_l93, y2_l93)
        pref_x, pref_y = (px1+px2)/2, (py1+py2)/2
        vx = px2 - px1
        vy = py2 - py1
        norme = (vx ** 2 + vy ** 2) ** 0.5
        if norme == 0:
            raise ValueError("Villes identiques : vecteur nul")

        vx /= norme
        vy /= norme

        super().__init__(point_px=(pref_x, pref_y), vecteur_px=(vx, vy), nom=nom, couleur=couleur, epaisseur=epaisseur, layer=layer, tags=tags, tooltips=tooltips)



from math import radians, cos, sin
class LigneAzimut(LigneGraphique):
    def __init__(self, ville, azimut_deg, nom=None, couleur=None, epaisseur=None, layer=None, tags: dict[str, Any] = None,tooltips: list[str] = None):
        x_l93, y_l93 = ville.coordonneesLambert()
        px, py = lambert93_to_pixels(x_l93, y_l93)

        angle_rad = math.radians(azimut_deg)
        vx = math.sin(angle_rad)
        vy = -math.cos(angle_rad)

        super().__init__(point_px=(px, py), vecteur_px=(vx, vy), nom=nom, couleur=couleur, epaisseur=epaisseur, layer=layer, tags=tags, tooltips=tooltips)



class LigneVerticale(LigneGraphique):
    def __init__(self, ville, nom=None, couleur=None, epaisseur=None, layer=None, tags: dict[str, Any] = None, tooltips: list[str] = None):
        x_l93, y_l93 = ville.coordonneesLambert()
        px, _ = lambert93_to_pixels(x_l93, y_l93)

        super().__init__(point_px=(px, 0), vecteur_px=(0, 1), nom=nom, couleur=couleur, epaisseur=epaisseur, layer=layer, tags=tags, tooltips=tooltips)



class LigneHorizontale(LigneGraphique):
    def __init__(self, ville, nom=None, couleur=None, epaisseur=None, layer=None, tags: dict[str, Any] = None, tooltips: list[str] = None):
        x_l93, y_l93 = ville.coordonneesLambert()
        _, py = lambert93_to_pixels(x_l93, y_l93)

        super().__init__(point_px=(0, py), vecteur_px=(1, 0), nom=nom, couleur=couleur, epaisseur=epaisseur, layer=layer, tags=tags, tooltips=tooltips)

