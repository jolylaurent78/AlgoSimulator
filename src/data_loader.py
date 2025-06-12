import pandas as pd

# Gestion des coordonnées / projection
from src.carte_config import carteConfig

# Affichage des objects graphiques
from src.affichage_objets import *

class VillesDict(dict):
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.recharger()

    @staticmethod
    def dms_to_decimal(dms_str):
        parts = dms_str.strip().split()
        deg, min_, sec, dir_ = int(parts[0]), int(parts[1]), int(parts[2]), parts[3].upper()
        decimal = deg + min_ / 60 + sec / 3600
        return -decimal if dir_ in ['S', 'W'] else decimal

    def recharger(self):
        df = pd.read_csv(self.csv_path)
        self.clear()  # vide le dict actuel
        for _, row in df.iterrows():
            nom = row["Nom"]
            lat = self.dms_to_decimal(row["Latitude"])
            lon = self.dms_to_decimal(row["Longitude"])
            x_l93, y_l93 = carteConfig.gps_to_lambert93(lon, lat)
            self[nom] = PointGraphique(nom, x_l93, y_l93, lat=lat, lon=lon)


villes_dict = VillesDict("data/villes_database.csv")
