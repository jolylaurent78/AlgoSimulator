import pandas as pd
import os
from src.utils import cheminRelatif

# Gestion des coordonnées / projection
from src.carte_config import carteConfig

# Affichage des objects graphiques
from src.affichage_objets import PointGraphique, SymboleWiki


class VillesDict(dict):
    def __init__(self, csv_path, afficherIcone=False):
        self.csv_path = cheminRelatif(csv_path)
        self.recharger(afficherIcone)

    @staticmethod
    def dms_to_decimal(dms_str):
        parts = dms_str.strip().split()
        deg, min_, sec, dir_ = int(parts[0]), int(parts[1]), int(parts[2]), parts[3].upper()
        decimal = deg + min_ / 60 + sec / 3600
        return -decimal if dir_ in ['S', 'W'] else decimal

    def recharger(self, afficherIcone=False):
        df = pd.read_csv(self.csv_path, skipinitialspace=True)
        self.clear()  # vide le dict actuel
        for _, row in df.iterrows():
            # On igore les lignes vides
            if all(value is None or str(value).strip() == '' for value in row.values):
                continue

            nom = row["Nom"]
            lat = self.dms_to_decimal(row["Latitude"])
            lon = self.dms_to_decimal(row["Longitude"])
            icone = row["Icone"]
            x_l93, y_l93 = carteConfig.gps_to_lambert93(lon, lat)

            icone = icone if icone is not None else "defaut.png"
            icone_path = cheminRelatif(os.path.join("images", icone))
            if not os.path.exists(icone_path):
                icone_path = cheminRelatif(os.path.join("images", "defaut.png"))

            if afficherIcone:
                self[nom] = SymboleWiki(nom, x_l93, y_l93, icone_path=icone_path, nom=nom)
            else:
                self[nom] = PointGraphique(nom, x_l93, y_l93)


villes_dict = VillesDict("data/villes_database.csv")
villes_POI = VillesDict("data/villes_database.csv", afficherIcone=True)
