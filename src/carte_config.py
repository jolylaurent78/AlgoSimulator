# carte_config.py
import numpy as np
import cv2
from pyproj import Transformer
from PIL import ImageTk, Image
import json
import os

from src.configGlobale import ConfigGlobale  

class CarteConfig:
    def __init__(self, json_path):
        self.load_from_json(json_path)

    def load_from_json(self, json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if config.get("projection") != "lambert93":
            raise ValueError("Seule la projection 'lambert93' est supportée pour le moment.")

        self.A = np.array(config["A"])
        self.offset = np.array(config["offset"])

        self.A_inv = np.linalg.inv(self.A)

        self.proj_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
        self.proj_wgs84 = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

        # Chargement image associée
        image_dir = os.path.dirname(json_path)
        image_file = config["image_file"]
        image_path = os.path.join(image_dir, image_file)

        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image non trouvée : {image_path}")

        self.img = img
        h_img, w_img = img.shape[:2]
        self.image_size = (w_img, h_img)

        # Description pour affichage dans le menu
        self.description = config.get("description", os.path.basename(json_path))

        # Calibration future (liste de noms de villes)
        self.calibration_villes = config.get("calibration_villes", [])

        print(f"[✅] Carte chargée : {self.description} ({w_img}x{h_img})")

    def getImageCarte(self):
        return self.img

    def lambert93_to_pixels(self, x, y):
        v = np.array([x, y])
        result = self.A @ v + self.offset
        return float(result[0]), float(result[1])

    def pixels_to_lambert93(self, px, py):
        vp = np.array([px, py]) - self.offset
        result = self.A_inv @ vp
        return float(result[0]), float(result[1])

    def lambert93_to_gps(self, x, y):
        lon, lat = self.proj_wgs84.transform(x, y)
        return lon, lat

    def gps_to_lambert93(self, lon, lat):
        x, y = self.proj_l93.transform(lon, lat)
        return x, y


    def calibrer(self, liste_points_lambert, liste_points_pixel):
        """
        Calcule la matrice A et l'offset à partir de points cliqués.

        liste_points_lambert : liste de (x_lambert, y_lambert)
        liste_points_pixel : liste de (px, py) correspondants
        """

        assert len(liste_points_lambert) == len(liste_points_pixel), "Nombre de points incohérent"
        assert len(liste_points_lambert) >= 3, "Au moins 3 points nécessaires pour calibration"

        # On construit la matrice du système
        N = len(liste_points_lambert)

        M = np.zeros((2*N, 6))
        b = np.zeros((2*N, 1))

        for i, (lambert, pixel) in enumerate(zip(liste_points_lambert, liste_points_pixel)):
            x_lamb, y_lamb = lambert
            px, py = pixel

            # Equation pour px
            M[2*i, 0] = x_lamb
            M[2*i, 1] = y_lamb
            M[2*i, 2] = 1
            M[2*i, 3] = 0
            M[2*i, 4] = 0
            M[2*i, 5] = 0
            b[2*i, 0] = px

            # Equation pour py
            M[2*i+1, 0] = 0
            M[2*i+1, 1] = 0
            M[2*i+1, 2] = 0
            M[2*i+1, 3] = x_lamb
            M[2*i+1, 4] = y_lamb
            M[2*i+1, 5] = 1
            b[2*i+1, 0] = py

        # Résolution par moindres carrés
        X, residuals, rank, s = np.linalg.lstsq(M, b, rcond=None)

        # On extrait A et offset
        a11 = X[0, 0]
        a12 = X[1, 0]
        offset_x = X[2, 0]

        a21 = X[3, 0]
        a22 = X[4, 0]
        offset_y = X[5, 0]

        self.A = np.array([[a11, a12], [a21, a22]])
        self.offset = np.array([offset_x, offset_y])
        self.A_inv = np.linalg.inv(self.A)

        print(f"[✅] Calibration effectuée :")
        print(f"A =\n{self.A}")
        print(f"offset = {self.offset}")

    def afficherCalibration(self):
        """
        Affiche les coefficients de calibration (matrice A et offset).
        """
        print(f"[DEBUG] Calibration courante de la carte :")
        print(f"A =\n{self.A}")
        print(f"offset = {self.offset}")


    def sauvegarderCalibrationDansJson(self, json_path, image_file, calibration_villes):
        """
        Sauvegarde le calibrage courant (A, offset) dans un fichier .json.

        json_path : chemin complet du fichier json à créer.
        image_file : nom du fichier image associé (ex: "899.jpg")
        calibration_villes : liste des villes de calibration
        """
        import json

        data = {
            "image_file": image_file,
            "projection": "lambert93",
            "description": "Calibration automatique — A METTRE A JOUR",
            "A": self.A.tolist(),
            "offset": self.offset.tolist(),
            "calibration_villes": calibration_villes
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"[✅] Calibration sauvegardée dans : {json_path}")


# === Instance globale ===
# On recharge la dernière carte utilisée (si existe)
cfg = ConfigGlobale()
dernier_json = cfg.get("Carte", "lastCarte", défaut="data/carto/899.json")
carteConfig = CarteConfig(dernier_json)


# === Fonctions utilitaires ===

def charger_icone(chemin, taille=(16, 16)):
    img = Image.open(chemin)
    img = img.resize(taille, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img)

def hexVersBGR(hex_color: str) -> tuple[int, int, int]:
    """
    Convertit une couleur hexadécimale "#rrggbb" en tuple BGR (OpenCV).
    """
    if hex_color.startswith("#") and len(hex_color) == 7:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return (b, g, r)
    return (0, 0, 0)

def bgrVersHex(bgr: tuple[int, int, int]) -> str:
    b, g, r = bgr
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)