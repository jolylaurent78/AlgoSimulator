# carte_config.py
import numpy as np
import cv2
from pyproj import Transformer
from PIL import ImageTk, Image

# Coefficients de la transformation affine : Xp = a * X + b * Y + c
# On représente ça sous forme matricielle : [Xp, Yp, 1] = M . [X, Y, 1]
A = np.array([
    [0.0058835, -0.0000535],
    [-0.0000422, -0.0058932]
])
offset = np.array([44.20, 42058.48])

# Inverse exacte de A
A_inv = np.linalg.inv(A)

# Initialisation du transformateur WGS84 -> Lambert93 et inversement
proj_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
proj_wgs84 = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def lambert93_to_pixels(x, y):
    v = np.array([x, y])
    result = A @ v + offset
    return float(result[0]), float(result[1])

def pixels_to_lambert93(px, py):
    vp = np.array([px, py]) - offset
    result = A_inv @ vp
    return float(result[0]), float(result[1])

def lambert93_to_gps(x: float, y: float) -> tuple[float, float]:
    """
    Convertit des coordonnées Lambert93 (mètres) en (longitude, latitude) WGS84.
    Retourne un tuple (lon, lat).
    """
    lon, lat = proj_wgs84.transform(x, y)
    return lon, lat

def gps_to_lambert93(lon: float, lat: float) -> tuple[float, float]:
    """
    Convertit des coordonnées GPS (longitude, latitude) en Lambert93 (x, y en mètres).
    """
    x, y = proj_l93.transform(lon, lat)
    return x, y

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

image_path = "data/carto/899.jpg"
img = cv2.imread(image_path)
if img is None:
    raise FileNotFoundError(f"Image non trouvée : {image_path}")
h_img, w_img = img.shape[:2]
image_size = (w_img, h_img)